/* Strum Along practice session: playback events in, cue time / resume point / saved settings out.
 * UMD: window.StrumSession in the browser, module.exports under node. No DOM, no timers, no network.
 * Spec: docs/STRUMALONG_APP.md ("Playback and sync", "Persistence").
 *
 * Two adapters keep it testable:
 * - storage: {getItem(key), setItem(key, value)}; localStorage in the app, a Map in tests.
 *   Every access is guarded, so a throwing or missing store just means nothing is remembered.
 * - player: {currentTime(), duration(), playbackRate(), availableRates(), seekTo(s), cue(videoId, s),
 *   play(), pause(), setRate(r), destroy()}; the YouTube IFrame player in the app, a fake in tests.
 *   Every call is guarded too: a throwing player keeps the last known value.
 * Message wording, the render loop, timers and wake lock stay in app.js. */
(function (root, factory) {
  "use strict";
  const core = root && root.StrumCore ? root.StrumCore : typeof require === "function" ? require("./core.js") : null;
  const api = factory(core);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.StrumSession = api;
})(typeof window !== "undefined" ? window : null, function (Core) {
  "use strict";

  const num = value => typeof value === "number" && Number.isFinite(value);
  const clampInt = (value, limit) => num(value) ? Math.max(-limit, Math.min(limit, Math.round(value))) : 0;
  const validVideoId = id => typeof id === "string" && /^[A-Za-z0-9_-]{11}$/.test(id);
  const attempt = (fn, fallback) => { try { return fn(); } catch (_) { return fallback; } };

  // ---------------------------------------------------------------- storage
  // Keys and JSON shapes are the v1 format learners already have saved: do not change them.
  const PREFIX = "music-os-strumalong-v1:";
  const LATENCY_LIMIT_MS = 1000;
  const NUDGE_LIMIT_MS = 30000;
  const RESUME_MIN_S = 5;       // a last-played time under this resumes from the start
  const RESUME_END_GAP_S = 5;   // ... and so does one within this of the recording's end
  const SAVE_EVERY_MS = 5000;   // last-played position while playing
  // The embed's cached currentTime() lags a seekTo() by ~100 ms, so a seek stays pending until the player
  // reports a time this close to it, or for at most this long (#31: quick repeated −10 s presses).
  const SEEK_CAUGHT_UP_S = 0.3;
  const SEEK_PENDING_MAX_MS = 1500;

  function sanitiseSettings(raw) {
    const s = raw && typeof raw === "object" ? raw : {};
    const patterns = {};
    if (s.patterns && typeof s.patterns === "object") for (const [k, v] of Object.entries(s.patterns)) if (typeof v === "string") patterns[k] = v;
    return { quality: s.quality === "full" ? "full" : "core", view: s.view === "sounding" ? "sounding" : "shapes",
      diagrams: s.diagrams !== false, countIn: s.countIn === true, patterns };
  }
  const freeze = s => Object.freeze({ ...s, patterns: Object.freeze({ ...s.patterns }) });

  function mapStorage(map) {
    const m = map || new Map();
    return { getItem: key => m.has(key) ? m.get(key) : null, setItem: (key, value) => { m.set(key, String(value)); } };
  }

  function createStore(storage) {
    function load(key, fallback) {
      try {
        const raw = storage.getItem(PREFIX + key);
        if (raw === null || raw === undefined) return fallback;
        const value = JSON.parse(raw);
        return value === null || value === undefined ? fallback : value;
      } catch (_) { return fallback; }
    }
    function save(key, value) { try { storage.setItem(PREFIX + key, JSON.stringify(value)); } catch (_) { /* private mode / quota */ } }

    function readFavourites() {
      const raw = load("favourites", []);
      return Array.isArray(raw) ? [...new Set(raw.filter(id => typeof id === "string" && id))] : [];
    }
    function readPlays() {
      const raw = load("plays", {});
      const plays = {};
      if (raw && typeof raw === "object" && !Array.isArray(raw)) for (const [k, v] of Object.entries(raw)) if (Number.isInteger(v) && v > 0) plays[k] = v;
      return plays;
    }
    let settings = freeze(sanitiseSettings(load("settings", {})));
    let latency = clampInt(Number(load("latency", 0)), LATENCY_LIMIT_MS);
    function updateSettings(patch) {
      settings = freeze(sanitiseSettings({ ...settings, ...patch, patterns: { ...settings.patterns, ...(patch.patterns || {}) } }));
      save("settings", settings);
      return settings;
    }
    return {
      settings: () => settings,
      setQuality: value => updateSettings({ quality: value }),
      setView: value => updateSettings({ view: value }),
      setDiagrams: on => updateSettings({ diagrams: Boolean(on) }),
      setCountIn: on => updateSettings({ countIn: Boolean(on) }),
      setPattern: (songId, patternId) => updateSettings({ patterns: { [songId]: patternId } }),
      latency: () => latency,
      setLatency(ms) { latency = clampInt(Number(ms), LATENCY_LIMIT_MS); save("latency", latency); return latency; },
      nudge: videoId => videoId ? clampInt(Number(load("offset:" + videoId, 0)), NUDGE_LIMIT_MS) : 0,
      setNudge(videoId, ms) { const value = clampInt(Number(ms), NUDGE_LIMIT_MS); if (videoId) save("offset:" + videoId, value); return value; },
      saveLast: (songId, t) => save("last", { id: songId, t }),
      // Jukebox journey (#53): favourite song ids in the order they were added, and finished-play counts.
      favourites: () => readFavourites(),
      toggleFavourite(songId) {
        const list = readFavourites();
        const on = !list.includes(songId);
        save("favourites", on ? list.concat(songId) : list.filter(id => id !== songId));
        return on;
      },
      plays: () => readPlays(),
      recordPlay(songId) {
        const plays = readPlays();
        plays[songId] = (plays[songId] || 0) + 1;
        save("plays", plays);
        return plays[songId];
      },
      // The library resume chip: the last-played song if it is still listed, and where to resume it
      // (0 means "start over": too near the start or the end of the recording to be worth resuming).
      resumePoint(songs) {
        const last = load("last", null);
        const song = last && typeof last === "object" && Array.isArray(songs) ? songs.find(s => s && s.id === last.id) : null;
        if (!song) return null;
        const t = num(last.t) && last.t >= RESUME_MIN_S && (!num(song.duration_seconds) || last.t < song.duration_seconds - RESUME_END_GAP_S) ? last.t : 0;
        return { song, t };
      },
    };
  }

  // ---------------------------------------------------------------- session (one per song page)
  // YouTube error codes that mean "this upload won't play here": try the next listed video.
  const FALLBACK_ERRORS = [100, 101, 150, 152];
  const NO_EMBED_ERRORS = [101, 150, 152];
  const PLAYING = 1, PAUSED = 2, ENDED = 0, BUFFERING = 3;

  function patternsOf(song) {
    const list = song.strumming && Array.isArray(song.strumming.patterns) ? song.strumming.patterns : [];
    return list.filter(p => p && typeof p.id === "string" && Array.isArray(p.strokes) && p.strokes.length);
  }

  function createSession(options) {
    const { song, store } = options;
    const clock = typeof options.now === "function" ? options.now : Date.now;
    const resume = num(options.resume) && options.resume > 0 ? options.resume : 0;
    const videos = (Array.isArray(song.videos) ? song.videos : []).filter(v => v && validVideoId(v.video_id));
    const patterns = patternsOf(song);
    const savedPattern = store.settings().patterns[song.id];

    let player = null, ready = false, state = -1, played = false, rate = 1, failed = null, ad = false, lastSave = 0;
    let pt = resume, startAt = resume, epoch = 0, timeline = [];
    let pendingSeek = null; // {target, at}
    // An analysed upload known not to embed (age-restricted) is skipped: start on the first embeddable entry.
    let videoIdx = Math.max(0, videos.findIndex(v => v.embeddable !== false));
    let video = videos[videoIdx] || null;
    let nudgeMs = store.nudge(video && video.video_id);
    let patternId = patterns.some(p => p.id === savedPattern) ? savedPattern : patterns[0] ? patterns[0].id : null;

    const capo = num(song.capo) && song.capo > 0 ? song.capo : 0;
    const view = () => capo ? store.settings().view : "shapes";
    // epoch changes whenever cached cue rendering is stale (new timeline, rate, video or failure).
    const invalidate = () => { epoch++; };
    function rebuildTimeline() {
      timeline = Core.buildTimeline(song, { view: view(), quality: store.settings().quality });
      invalidate();
    }
    rebuildTimeline();

    const controllable = () => Boolean(player && ready && !failed);
    const THREW = {};
    function readRate() {
      const value = attempt(() => player.playbackRate(), THREW);
      if (value !== THREW) rate = num(value) && value > 0 ? value : 1; // a throwing player keeps the last rate
    }
    function saveLast(forceT) {
      if (!played) return;
      store.saveLast(song.id, num(forceT) ? forceT : Math.max(0, Math.floor(pt)));
    }
    function readPlayerTime() {
      let t = pt;
      if (controllable()) {
        const value = attempt(() => player.currentTime(), null);
        if (num(value)) t = value;
        if (pendingSeek) {
          const caughtUp = num(value) && Math.abs(value - pendingSeek.target) <= SEEK_CAUGHT_UP_S;
          if (caughtUp || clock() - pendingSeek.at >= SEEK_PENDING_MAX_MS) pendingSeek = null;
          else return pendingSeek.target;
        }
        // A resumed start is not reported until playback begins.
        if (!played && startAt > 0 && t < 0.5) t = startAt;
      }
      return t;
    }
    function fail(reason) {
      failed = reason || "failed";
      state = -1;
      invalidate();
      return failed;
    }
    function switchTo(index) {
      videoIdx = index;
      video = videos[index];
      nudgeMs = store.nudge(video.video_id);
      ad = false; state = -1; pt = 0; startAt = 0; pendingSeek = null;
      invalidate();
      try { player.cue(video.video_id, 0); } catch (_) { fail("no-embed"); return false; }
      return true;
    }

    const session = {
      song, videos, patterns,
      get video() { return video; },
      get videoIdx() { return videoIdx; },
      get state() { return state; },
      get played() { return played; },
      get ready() { return ready; },
      get failed() { return failed; },
      get ad() { return ad; },
      get rate() { return rate; },
      get pt() { return pt; },
      get startAt() { return startAt; },
      get nudgeMs() { return nudgeMs; },
      get timeline() { return timeline; },
      get patternId() { return patternId; },
      get epoch() { return epoch; },
      get playing() { return state === PLAYING || state === BUFFERING; },
      get controllable() { return controllable(); },
      view,

      // ---- player events
      attach(adapter) { player = adapter; },
      playerReady() { ready = true; readRate(); },
      availableRates() {
        if (!player) return [];
        const list = attempt(() => player.availableRates(), []);
        return Array.isArray(list) ? list.filter(num) : [];
      },
      refreshRate() { if (player) readRate(); },
      stateChange(code) {
        state = code;
        if (code === PLAYING) played = true;
        if (code === PAUSED) saveLast();
        if (code === ENDED) saveLast(0);
      },
      rateChange(value) { rate = num(value) && value > 0 ? value : 1; invalidate(); },
      // Decide what a YouTube error means. Returns {action:"switch", video, code} after cueing the next
      // listed video, {action:"fail", reason} ("referrer" | "unavailable" | "no-embed"), or {action:"retry", code}.
      error(code) {
        if (FALLBACK_ERRORS.includes(code) && videoIdx + 1 < videos.length) {
          return switchTo(videoIdx + 1) ? { action: "switch", video, code } : { action: "fail", reason: failed };
        }
        if (code === 153) return { action: "fail", reason: fail("referrer") };
        if (code === 100) return { action: "fail", reason: fail("unavailable") };
        if (NO_EMBED_ERRORS.includes(code)) return { action: "fail", reason: fail("no-embed") };
        return { action: "retry", code };
      },
      fail,
      retry() { if (player && video) attempt(() => player.cue(video.video_id, Math.max(0, pt))); },

      // ---- transport (each returns false when the player refused or isn't usable)
      play() { if (!controllable()) return false; try { player.play(); return true; } catch (_) { return false; } },
      pause() { if (!controllable()) return false; try { player.pause(); return true; } catch (_) { return false; } },
      seek(seconds) {
        if (!controllable()) return false;
        const target = Math.max(0, seconds);
        try { player.seekTo(target); } catch (_) { return false; }
        pt = target;
        pendingSeek = { target, at: clock() };
        return true;
      },
      setRate(value) { if (controllable() && num(value)) attempt(() => player.setRate(value)); },

      // ---- clock: call every frame. Returns the player position, the cue time and the cue model.
      tick() {
        pt = readPlayerTime();
        if (state === PLAYING && player && ready) {
          const duration = attempt(() => player.duration(), 0);
          ad = Core.durationMismatch(duration, Core.expectedDuration(song, video));
          const now = clock();
          if (now - lastSave > SAVE_EVERY_MS) { lastSave = now; saveLast(); }
        }
        const t = Core.cueTime(pt, video && video.offset_seconds, nudgeMs, store.latency(), rate);
        return { pt, t, cue: Core.cueAt(timeline, song, t) };
      },

      // ---- learner settings
      nudgeBy(ms) { nudgeMs = store.setNudge(video && video.video_id, nudgeMs + Number(ms)); return nudgeMs; },
      resetNudge() { nudgeMs = store.setNudge(video && video.video_id, 0); return nudgeMs; },
      setQuality(value) { store.setQuality(value); rebuildTimeline(); },
      setView(value) { store.setView(value); rebuildTimeline(); },
      setPattern(id) {
        if (!patterns.some(p => p.id === id)) return false;
        patternId = id;
        store.setPattern(song.id, id);
        return true;
      },

      saveLast() { saveLast(); },
      leave() {
        saveLast();
        if (player) attempt(() => player.destroy());
        player = null;
      },
    };
    return session;
  }

  return { createStore, createSession, mapStorage, PREFIX, NUDGE_LIMIT_MS, LATENCY_LIMIT_MS };
});
