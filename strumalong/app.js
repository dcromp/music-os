/* Strum Along: app shell, hash router, YouTube controller and render loop.
 * Spec: docs/STRUMALONG_APP.md ("UI" and "Playback and sync"). Plain ES2020, no build step.
 * Charts are provisional automatic drafts; strum patterns are practice suggestions; beats are
 * estimated and bars approximate. The official YouTube player stays visible with nothing on it. */
(function () {
  "use strict";
  const Core = window.StrumCore;
  const app = document.getElementById("app");
  if (!app) return;
  if (!Core) { app.innerHTML = '<p class="msg error">Strum Along could not start: lib/core.js did not load. Reload to try again.</p><p><a class="btn" href="">Reload</a></p>'; return; }

  // ---------------------------------------------------------------- storage (always guarded)
  const PREFIX = "music-os-strumalong-v1:";
  function load(key, fallback) {
    try {
      const raw = window.localStorage.getItem(PREFIX + key);
      if (raw === null) return fallback;
      const value = JSON.parse(raw);
      return value === null || value === undefined ? fallback : value;
    } catch (_) { return fallback; }
  }
  function save(key, value) { try { window.localStorage.setItem(PREFIX + key, JSON.stringify(value)); } catch (_) { /* private mode / quota */ } }
  const clampInt = (value, limit) => Number.isFinite(value) ? Math.max(-limit, Math.min(limit, Math.round(value))) : 0;

  const settings = (() => {
    const raw = load("settings", {});
    const s = raw && typeof raw === "object" ? raw : {};
    const patterns = {};
    if (s.patterns && typeof s.patterns === "object") for (const [k, v] of Object.entries(s.patterns)) if (typeof v === "string") patterns[k] = v;
    return { quality: s.quality === "full" ? "full" : "core", view: s.view === "sounding" ? "sounding" : "shapes",
      diagrams: s.diagrams !== false, patterns };
  })();
  const saveSettings = () => save("settings", settings);
  let latencyMs = clampInt(Number(load("latency", 0)), 1000);
  const NUDGE_LIMIT_MS = 30000;
  const loadNudge = video => video ? clampInt(Number(load("offset:" + video.video_id, 0)), NUDGE_LIMIT_MS) : 0;

  // ---------------------------------------------------------------- small helpers
  const $ = id => document.getElementById(id);
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = value => String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, c => ESC[c]);
  const validSongId = id => typeof id === "string" && /^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$/.test(id);
  const validVideoId = id => typeof id === "string" && /^[A-Za-z0-9_-]{11}$/.test(id);
  const num = value => typeof value === "number" && Number.isFinite(value);
  function safeUrl(url) {
    try { const parsed = new URL(url, location.href); return /^https?:$/.test(parsed.protocol) ? parsed.href : null; } catch (_) { return null; }
  }
  const watchUrl = (videoId, t) => `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}${t >= 2 ? `&t=${Math.floor(t)}s` : ""}`;
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  function sizeClass(text) {
    const n = String(text || "").length;
    return n <= 2 ? "len-s" : n === 3 ? "len-3" : n === 4 ? "len-4" : n <= 6 ? "len-5" : "len-l";
  }
  function formatNudge(ms) {
    if (!ms) return "0 ms";
    const sign = ms > 0 ? "+" : "−";
    const abs = Math.abs(ms);
    return abs >= 1000 ? `${sign}${(abs / 1000).toFixed(2)} s` : `${sign}${abs} ms`;
  }

  // ---------------------------------------------------------------- data
  let cataloguePromise = null;
  const songPromises = new Map();
  async function fetchJSON(url) {
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) { const error = new Error(`${url}: HTTP ${response.status}`); error.status = response.status; throw error; }
    return response.json();
  }
  function getCatalogue() {
    if (!cataloguePromise) cataloguePromise = fetchJSON("songs/index.json").catch(error => { cataloguePromise = null; throw error; });
    return cataloguePromise;
  }
  function getSong(id) {
    if (!songPromises.has(id)) {
      songPromises.set(id, fetchJSON(`songs/${encodeURIComponent(id)}.json`).catch(error => { songPromises.delete(id); throw error; }));
    }
    return songPromises.get(id);
  }

  // ---------------------------------------------------------------- YouTube IFrame API (loaded once)
  let ytPromise = null;
  function loadYouTube() {
    if (window.YT && typeof window.YT.Player === "function") return Promise.resolve(window.YT);
    if (ytPromise) return ytPromise;
    ytPromise = new Promise((resolve, reject) => {
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        try { if (typeof previous === "function") previous(); } catch (_) { /* ignore */ }
        resolve(window.YT);
      };
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.async = true;
      script.onerror = () => { ytPromise = null; script.remove(); reject(new Error("YouTube API failed to load")); };
      document.head.appendChild(script);
    });
    return ytPromise;
  }

  // ---------------------------------------------------------------- wake lock
  let wakeLock = null;
  async function requestWakeLock() {
    try {
      if (wakeLock || !("wakeLock" in navigator) || document.visibilityState !== "visible") return;
      const lock = await navigator.wakeLock.request("screen");
      wakeLock = lock;
      lock.addEventListener("release", () => { if (wakeLock === lock) wakeLock = null; });
    } catch (_) { wakeLock = null; }
  }
  function releaseWakeLock() {
    const lock = wakeLock; wakeLock = null;
    try { if (lock) lock.release().catch(() => {}); } catch (_) { /* ignore */ }
  }

  // ---------------------------------------------------------------- routing
  let routeGen = 0;
  let S = null;            // current song session (null on the library)
  let resumeRequest = null; // {id, t} set by the library resume chip

  function route() {
    const gen = ++routeGen;
    leaveSong();
    const match = /^#\/song\/([^/?#]+)\/?$/.exec(location.hash || "");
    if (match) {
      let id = "";
      try { id = decodeURIComponent(match[1]); } catch (_) { id = ""; }
      showSong(id, gen);
    } else showLibrary(gen);
    try { window.scrollTo(0, 0); } catch (_) { /* ignore */ }
  }

  // ---------------------------------------------------------------- library
  async function showLibrary(gen) {
    document.title = "Strum Along";
    app.className = "app view-library";
    app.innerHTML = `<header class="lib-head"><h1>Strum Along <span class="sub">· music-os</span></h1>
      <p class="tagline">Provisional automatic chord charts. For personal practice.</p></header>
      <div id="lib-body"><p class="muted">Loading songs…</p></div>`;
    let catalogue;
    try { catalogue = await getCatalogue(); }
    catch (_) {
      if (gen !== routeGen) return;
      $("lib-body").innerHTML = `<p class="msg error">Couldn't load the song list. Check your connection.</p>
        <p><button type="button" class="btn" data-act="reload">Try again</button></p>`;
      return;
    }
    if (gen !== routeGen) return;
    const songs = Array.isArray(catalogue && catalogue.songs) ? catalogue.songs.filter(s => s && validSongId(s.id)) : [];
    const groups = Array.isArray(catalogue && catalogue.groups) ? catalogue.groups.filter(g => g && typeof g.id === "string") : [];
    const known = new Set(groups.map(g => g.id));
    const leftovers = songs.filter(s => !known.has(s.group));
    if (leftovers.length) groups.push({ id: "__other", title: "Other songs", note: "" });
    let html = "";
    const last = load("last", null);
    const lastSong = last && typeof last === "object" ? songs.find(s => s.id === last.id) : null;
    if (lastSong) {
      const t = num(last.t) && last.t >= 5 && (!num(lastSong.duration_seconds) || last.t < lastSong.duration_seconds - 5) ? last.t : 0;
      html += `<a class="resume" href="#/song/${encodeURIComponent(lastSong.id)}" data-act="resume" data-id="${esc(lastSong.id)}" data-t="${t}">
        <span class="resume-icon" aria-hidden="true">▶</span><span>${t ? "Resume" : "Last played:"} <b>${esc(lastSong.title)}</b>${t ? ` at ${Core.formatTime(t)}` : ""}</span></a>`;
    }
    for (const group of groups) {
      const members = songs.filter(s => group.id === "__other" ? !known.has(s.group) : s.group === group.id)
        .sort((a, b) => (num(a.order) ? a.order : 999) - (num(b.order) ? b.order : 999) || String(a.title).localeCompare(String(b.title)));
      if (!members.length) continue;
      html += `<section class="group"><h2>${esc(group.title)}</h2>${group.note ? `<p class="group-note">${esc(group.note)}</p>` : ""}
        <ul class="cards">${members.map(songCard).join("")}</ul></section>`;
    }
    if (!songs.length) html += `<p class="msg">No songs are listed yet.</p>`;
    html += `<footer class="lib-foot"><p>Chords are automatic drafts and may be wrong. Strum patterns are practice suggestions, not the recorded parts. Beats are estimated; bars are approximate.</p></footer>`;
    $("lib-body").innerHTML = html;
  }

  function songCard(s) {
    const chips = (Array.isArray(s.core_shapes) ? s.core_shapes : []).map(c => `<span class="chip">${esc(c)}</span>`).join("");
    const meta = [];
    if (num(s.bpm)) meta.push(`~${Math.round(s.bpm)} BPM`);
    if (s.meter_label) meta.push(esc(s.meter_label));
    const badges = [];
    if (num(s.capo) && s.capo > 0) badges.push(`<span class="badge capo">Capo ${esc(s.capo)}</span>`);
    if (s.playable_embed === false) badges.push(`<span class="badge warn">${/unchecked/i.test(s.embed_note) ? "timing unchecked" : "alternate video"}</span>`);
    return `<li><a class="card" href="#/song/${encodeURIComponent(s.id)}">
      <span class="card-main"><span class="card-title">${esc(s.title)}</span><span class="card-artist">${esc(s.artist)}</span></span>
      ${chips ? `<span class="chips" aria-label="Core shapes">${chips}</span>` : ""}
      <span class="card-meta">${meta.join(" · ")}${badges.length ? ` ${badges.join(" ")}` : ""}</span>
      ${s.embed_note ? `<span class="card-note">${esc(s.embed_note)}</span>` : ""}
    </a></li>`;
  }

  // ---------------------------------------------------------------- song page
  async function showSong(id, gen) {
    app.className = "app view-song";
    app.innerHTML = `<header class="topbar"><a class="back" href="#/">‹ Songs</a><div class="top-title"><h1>Loading…</h1></div></header>
      <p class="muted pad">Loading song…</p>`;
    if (!validSongId(id)) { songError("Song not found.", false); return; }
    let song;
    try { song = await getSong(id); }
    catch (error) {
      if (gen !== routeGen) return;
      if (error && error.status === 404) songError("Song not found.", false);
      else songError("Couldn't load this song. Check your connection.", true);
      return;
    }
    if (gen !== routeGen) return;
    if (!song || !Array.isArray(song.chords)) { songError("This song's chart is missing or damaged.", false); return; }
    startSong(song, gen);
  }

  function songError(message, retry) {
    app.innerHTML = `<header class="topbar"><a class="back" href="#/">‹ Songs</a><div class="top-title"><h1>Strum Along</h1></div></header>
      <p class="msg error">${esc(message)}</p>${retry ? `<p><button type="button" class="btn" data-act="reload">Try again</button></p>` : ""}`;
  }

  function viewFor(song) { return num(song.capo) && song.capo > 0 ? settings.view : "shapes"; }
  function patternsOf(song) {
    const list = song.strumming && Array.isArray(song.strumming.patterns) ? song.strumming.patterns : [];
    return list.filter(p => p && typeof p.id === "string" && Array.isArray(p.strokes) && p.strokes.length);
  }

  function startSong(song, gen) {
    const videos = (Array.isArray(song.videos) ? song.videos : []).filter(v => v && validVideoId(v.video_id));
    // An analysed upload known not to embed (age-restricted) is skipped: start on the first embeddable entry.
    const videoIdx = Math.max(0, videos.findIndex(v => v.embeddable !== false));
    const resume = resumeRequest && resumeRequest.id === song.id && num(resumeRequest.t) ? resumeRequest.t : 0;
    resumeRequest = null;
    const patterns = patternsOf(song);
    const saved = settings.patterns[song.id];
    S = {
      gen, song, videos, videoIdx, video: videos[videoIdx] || null, player: null, ready: false, state: -1, played: false, rate: 1,
      failed: null, cuesHidden: false, ad: false, raf: 0, poll: 0, loadTimer: 0, playTimer: 0, lastSave: 0,
      pt: resume, startAt: resume, timeline: [], patterns,
      patternId: patterns.some(p => p.id === saved) ? saved : patterns[0] ? patterns[0].id : null,
      nudgeMs: 0, msgs: {}, memo: {}, strumCells: [],
    };
    S.nudgeMs = loadNudge(S.video);
    rebuildTimeline();
    document.title = `${song.title || "Song"} · Strum Along`;
    app.innerHTML = songSkeleton(song);
    renderStrumPanel();
    renderViewControls();
    renderSync();
    renderDetails();
    renderLatency();
    updateTransport();
    if (resume > 0) setMsg("info", `Resuming at ${Core.formatTime(resume)}. Press Play when ready.`);
    frame();
    S.poll = window.setInterval(() => { if (S && S.state !== 1) frame(); }, 250);
    if (!S.video) { fail("No embeddable video is listed for this song."); return; }
    noteVideo();
    const session = S;
    S.loadTimer = window.setTimeout(() => {
      if (S !== session || S.ready || S.failed) return;
      // A stalled API script never settles its promise: forget it so the next song page loads it again.
      if (!(window.YT && typeof window.YT.Player === "function")) ytPromise = null;
      setMsg("error", `YouTube is taking a while to load. Check the connection, or reload the page. <button type="button" class="btn small" data-act="reload">Reload</button>`);
    }, 15000);
    loadYouTube().then(YT => { if (S === session) createPlayer(YT); })
      .catch(() => { if (S === session) setMsg("error", `YouTube could not load. Check the connection. <button type="button" class="btn small" data-act="reload">Reload</button>`); });
  }

  function songSkeleton(song) {
    const capo = num(song.capo) && song.capo > 0 ? song.capo : 0;
    return `<header class="topbar">
      <a class="back" href="#/" aria-label="Back to songs">‹ Songs</a>
      <div class="top-title"><h1>${esc(song.title)}</h1><p>${esc(song.artist)}</p></div>
      <span class="top-badges">${capo ? `<span class="badge capo" id="capo-badge">Capo ${capo}</span>` : ""}${levelBadge(song)}<span class="badge prov" title="Automatic chord chart; not reviewed">Provisional</span></span>
    </header>
    <div class="song-grid">
      <div class="col-video">
        <div class="player-frame"><div id="yt-player"></div></div>
        <div id="player-status" class="player-status" role="status" aria-live="polite"></div>
      </div>
      <div class="col-cues">
        <section id="cue-panel" class="panel cue-panel" aria-label="Chord cues">
          <div id="cue-live" class="cue-live">
            <div class="cue-row">
              <div class="cue cue-now"><div class="cue-cap">NOW <span id="now-quick" class="tag quick" hidden>quick</span><span id="cue-note" class="tag note" hidden></span></div>
                <div id="now-chord" class="cue-chord len-s">—</div><div id="now-dots" class="dots" role="img" aria-label=""></div></div>
              <div id="next-col" class="cue cue-next"><div class="cue-cap">NEXT <span id="next-quick" class="tag quick" hidden>quick</span></div>
                <div id="next-chord" class="cue-chord len-s">—</div><div id="next-dots" class="dots" role="img" aria-label=""></div></div>
            </div>
            <div class="cue-foot"><span id="cue-count" class="cue-count"></span><span id="cue-hint" class="cue-hint"></span><button type="button" id="btn-play-cue" class="btn btn-play cue-play" data-act="play" disabled aria-label="Play">▶ Play</button></div>
          </div>
          <div id="cue-cover" class="cue-cover" hidden></div>
        </section>
        <section id="strum-panel" class="panel strum-panel" aria-label="Suggested practice pattern"></section>
        <section id="diagram-panel" class="panel diagram-panel" aria-label="Chord diagrams"${settings.diagrams ? "" : " hidden"}>
          <div id="diagrams" class="diagrams"></div>
        </section>
      </div>
      <div class="col-controls">
        <section class="panel controls" aria-label="Playback controls">
          <div class="transport">
            <button type="button" id="btn-play" class="btn btn-play" data-act="play" disabled>▶ Play</button>
            <button type="button" id="btn-back" class="btn" data-act="back10" disabled aria-label="Back 10 seconds">−10 s</button>
            <button type="button" id="btn-restart" class="btn" data-act="restart" disabled aria-label="Restart from the beginning">Restart</button>
          </div>
          <div class="row">
            <label id="speed-wrap" class="speed" hidden>Speed <select id="sel-speed" aria-label="Playback speed"></select></label>
            <button type="button" id="btn-hide" class="btn" data-act="hide" aria-pressed="false">Hide cues</button>
          </div>
          <div class="row sync" role="group" aria-label="Sync nudge">
            <span class="row-label">Sync</span>
            <button type="button" class="btn" data-act="nudge" data-ms="-50" aria-label="Nudge cues 50 milliseconds later">−50</button>
            <output id="nudge-out" class="nudge-out" aria-live="polite">0 ms</output>
            <button type="button" class="btn" data-act="nudge" data-ms="50" aria-label="Nudge cues 50 milliseconds sooner">+50</button>
            <button type="button" class="btn small" data-act="nudge-reset">Reset</button>
          </div>
          <div id="coarse-sync" class="row sync" role="group" aria-label="Coarse sync for an unchecked video" hidden>
            <span class="row-label">Coarse</span>
            <button type="button" class="btn" data-act="nudge" data-ms="-1000" aria-label="Nudge cues 1 second later">−1 s</button>
            <button type="button" class="btn" data-act="nudge" data-ms="1000" aria-label="Nudge cues 1 second sooner">+1 s</button>
          </div>
          <p class="hint">Sync steps are 50 ms: + shows chord changes sooner, − later. Saved for this video.</p>
          <div class="row view" role="group" aria-label="View">
            <span class="row-label">View</span>
            <span class="seg" role="group" aria-label="Chord detail">
              <button type="button" class="btn" data-act="quality" data-v="core">Simple</button><button type="button" class="btn" data-act="quality" data-v="full">Full</button>
            </span>
            ${capo ? `<span class="seg" role="group" aria-label="Chord names">
              <button type="button" class="btn" data-act="view" data-v="shapes">Capo shapes</button><button type="button" class="btn" data-act="view" data-v="sounding">Sounding</button>
            </span>` : ""}
            <button type="button" id="btn-diagrams" class="btn" data-act="diagrams" aria-pressed="true">Diagrams</button>
          </div>
        </section>
        <details class="panel details" id="details"><summary>Details</summary><div id="details-body"></div></details>
      </div>
    </div>`;
  }

  function levelOf(song) {
    const d = song && song.difficulty;
    const level = d && Number.isInteger(d.level) ? d.level : Number.isInteger(song && song.level) ? song.level : null;
    return level >= 1 && level <= 5 ? { level, label: d && typeof d.label === "string" ? d.label : "" } : null;
  }
  function levelBadge(song) {
    const l = levelOf(song);
    return l ? `<span class="badge level" title="${esc(l.label)}">Level ${l.level}</span>` : "";
  }

  function rebuildTimeline() {
    if (!S) return;
    S.timeline = Core.buildTimeline(S.song, { view: viewFor(S.song), quality: settings.quality });
    S.memo = {};
  }

  // ---------------------------------------------------------------- player
  function createPlayer(YT) {
    const session = S;
    const vars = { playsinline: 1, rel: 0, controls: 1, enablejsapi: 1, fs: 0 };
    if (/^https?:/.test(location.protocol)) vars.origin = location.origin;
    if (session.startAt > 0) vars.start = Math.floor(session.startAt);
    const live = fn => (...args) => { if (S === session) { try { fn(...args); } catch (error) { console.error(error); } } };
    try {
      session.player = new YT.Player("yt-player", {
        width: "100%", height: "100%", videoId: session.video.video_id, playerVars: vars,
        events: {
          onReady: live(onReady),
          onStateChange: live(event => onState(event.data)),
          onError: live(event => onPlayerError(event.data)),
          onAutoplayBlocked: live(() => setMsg("autoplay", "Tap ▶ in the video to start.")),
          onPlaybackRateChange: live(event => {
            const sel = $("sel-speed"); if (sel) sel.value = String(event.data);
            S.rate = num(event.data) && event.data > 0 ? event.data : 1;
            S.memo = {};
            frame();
          }),
        },
      });
    } catch (_) {
      setMsg("error", `The YouTube player could not start. Reload to try again. <button type="button" class="btn small" data-act="reload">Reload</button>`);
    }
  }

  function onReady() {
    S.ready = true;
    window.clearTimeout(S.loadTimer);
    if (S.msgs.error && !S.failed) setMsg("error", null);
    refreshRates();
    updateTransport();
    frame();
  }

  function refreshRates() {
    const wrap = $("speed-wrap"), sel = $("sel-speed");
    if (!S.player) return;
    try { const rate = S.player.getPlaybackRate(); S.rate = num(rate) && rate > 0 ? rate : 1; } catch (_) { /* keep the last rate */ }
    if (!wrap || !sel) return;
    let rates = [];
    try { rates = (S.player.getAvailablePlaybackRates() || []).filter(num); } catch (_) { rates = []; }
    if (rates.length <= 1) { wrap.hidden = true; return; }
    sel.innerHTML = rates.map(r => `<option value="${r}">${r === 1 ? "1× (normal)" : `${r}×`}</option>`).join("");
    sel.value = String(S.rate);
    wrap.hidden = false;
  }

  function onState(code) {
    S.state = code;
    if (code === 1) {
      S.played = true;
      window.clearTimeout(S.playTimer);
      setMsg("autoplay", null);
      setMsg("info", null);
      setMsg("switch", null);
      if (S.msgs.error && !S.failed) setMsg("error", null);
      if ($("speed-wrap") && $("speed-wrap").hidden) refreshRates();
      requestWakeLock();
      startLoop();
    } else {
      stopLoop();
    }
    if (code === 3) window.clearTimeout(S.playTimer);
    if (code === 2) saveLast();
    if (code === 0) saveLast(0);
    // The lock is kept while paused (chords are read during a pause) and released when the song ends.
    if (code === 0) releaseWakeLock();
    updateTransport();
    frame();
  }

  function onPlayerError(code) {
    stopLoop();
    window.clearTimeout(S.playTimer);
    if ([100, 101, 150, 152].includes(code) && S.videoIdx + 1 < S.videos.length) { switchVideo(S.videoIdx + 1, code); return; }
    if (code === 153) { fail("Player configuration error (referrer). This is a page setup problem, not your connection."); return; }
    if (code === 100) { fail("Video unavailable."); return; }
    if ([101, 150, 152].includes(code)) { fail("This video can't play inside the app."); return; }
    setMsg("error", `YouTube reported a playback problem (error ${esc(code)}). <button type="button" class="btn small" data-act="retry">Retry</button>`);
  }

  function switchVideo(index, code) {
    S.videoIdx = index;
    S.video = S.videos[index];
    S.nudgeMs = loadNudge(S.video);
    S.ad = false; S.state = -1; S.pt = 0; S.startAt = 0; S.memo = {};
    setMsg("error", null);
    const who = S.video && S.video.uploader ? `${esc(S.video.uploader)}'s` : "another";
    setMsg("switch", `Playing ${who} official video instead; the analysed upload can't play here.`);
    console.info(`Strum Along: switched video after YouTube error ${code}`);
    noteVideo();
    renderSync(); renderDetails(); updateTransport();
    try { S.player.cueVideoById({ videoId: S.video.video_id, startSeconds: 0 }); }
    catch (_) { fail("This video can't play inside the app."); return; }
    frame();
  }

  function noteVideo() {
    const v = S.video;
    if (!v) { setMsg("video"); return; }
    if (v.timing_checked === false) {
      const advice = /sync|nudge/i.test(v.note || "") ? "" : " Use Sync to line the cues up with what you hear.";
      setMsg("video", `<b>Timing unchecked.</b> ${esc(v.note || "")}${advice}`, "warn");
    } else if (v.kind && v.kind !== "analysed" && v.note) {
      setMsg("video", esc(v.note));
    } else setMsg("video", null);
  }

  // The upload the chart was computed from (its times match the non-synced chord list).
  function analysedVideo() { return S.videos.find(v => v.kind === "analysed") || S.videos[0] || null; }

  function fail(message) {
    stopLoop();
    S.failed = message;
    S.state = -1;
    const video = analysedVideo();
    const link = video ? ` <a href="${esc(watchUrl(video.video_id, 0))}" target="_blank" rel="noopener" data-act="open-yt">Open on YouTube</a>` : "";
    setMsg("error", `${esc(message)}${link}`, "error");
    setMsg("autoplay", null);
    setMsg("video", null);
    setMsg("info", null);
    updateTransport();
    S.memo = {};
    frame();
  }

  function togglePlay() {
    if (!S || !S.player || !S.ready || S.failed) return;
    try {
      if (S.state === 1 || S.state === 3) { S.player.pauseVideo(); return; }
      // Never start audio with the official player off screen (the lower Play button can be reached
      // after scrolling): bring the player, and the "Tap ▶ in the video" hint under it, into view first.
      const f = document.querySelector(".player-frame");
      if (f) {
        const r = f.getBoundingClientRect();
        if (r.top < 0 || r.bottom > window.innerHeight) f.scrollIntoView({ block: "start", behavior: "smooth" });
      }
      S.player.playVideo();
    } catch (_) { return; }
    requestWakeLock();
    const session = S;
    window.clearTimeout(S.playTimer);
    S.playTimer = window.setTimeout(() => {
      if (S === session && S.state !== 1 && S.state !== 3 && !S.failed) setMsg("autoplay", "Tap ▶ in the video to start.");
    }, 2500);
  }

  function seekTo(seconds) {
    if (!S || !S.player || !S.ready || S.failed) return;
    const target = Math.max(0, seconds);
    try { S.player.seekTo(target, true); } catch (_) { return; }
    S.pt = target;
    frame();
  }

  function startLoop() { if (S && !S.raf) S.raf = window.requestAnimationFrame(loop); }
  function stopLoop() { if (S && S.raf) { window.cancelAnimationFrame(S.raf); S.raf = 0; } }
  function loop() {
    if (!S) return;
    S.raf = 0;
    if (S.state !== 1) return;
    frame();
    const now = Date.now();
    if (now - S.lastSave > 5000) { S.lastSave = now; saveLast(); }
    S.raf = window.requestAnimationFrame(loop);
  }

  function saveLast(forceT) {
    if (!S || !S.played) return;
    const t = num(forceT) ? forceT : Math.max(0, Math.floor(S.pt));
    save("last", { id: S.song.id, t });
  }

  function leaveSong() {
    if (!S) return;
    const s = S;
    saveLast();
    S = null;
    if (s.raf) window.cancelAnimationFrame(s.raf);
    window.clearInterval(s.poll);
    window.clearTimeout(s.loadTimer);
    window.clearTimeout(s.playTimer);
    try { if (s.player && typeof s.player.destroy === "function") s.player.destroy(); } catch (_) { /* ignore */ }
    releaseWakeLock();
  }

  // ---------------------------------------------------------------- frame + memoized rendering
  function readPlayerTime() {
    let pt = S.pt;
    if (S.player && S.ready && !S.failed) {
      try {
        const value = S.player.getCurrentTime();
        if (num(value)) pt = value;
      } catch (_) { /* keep last */ }
      // A resumed start is not reported until playback begins.
      if (!S.played && S.startAt > 0 && pt < 0.5) pt = S.startAt;
    }
    return pt;
  }

  function frame() {
    if (!S) return;
    S.pt = readPlayerTime();
    if (S.state === 1 && S.player && S.ready) {
      let duration = 0;
      try { duration = S.player.getDuration(); } catch (_) { duration = 0; }
      S.ad = Core.durationMismatch(duration, Core.expectedDuration(S.song, S.video));
    }
    const t = Core.cueTime(S.pt, S.video && S.video.offset_seconds, S.nudgeMs, latencyMs, S.rate);
    const cue = Core.cueAt(S.timeline, S.song, t);
    renderCue(cue);
    renderStrumStep(t);
    renderDiagrams(cue);
  }

  function cueMode() {
    if (S.failed) return "failed";
    if (S.cuesHidden) return "hidden";
    if (S.ad) return "ad";
    return "live";
  }
  function stateNote() {
    if (!S.video) return "";
    if (S.state === 3) return "Buffering…";
    if (S.state === 2) return "Paused";
    if (S.state === 0) return "Ended";
    if (S.state === -1 || S.state === 5) return S.ready ? "Tap ▶ to start" : "Waiting · loading";
    return "";
  }
  const partKey = p => p ? `${p.idx}:${p.kind}:${p.display}:${p.dotOffset}:${p.active}:${p.dots.length}:${p.more}:${p.quick}:${p.barStart}` : "-";

  // DOM is touched only when a piece of the cue model changes (chord, active dot, count),
  // never every frame. Each sub-part has its own memo key.
  function renderCue(cue) {
    const mode = cueMode();
    const live = $("cue-live"), cover = $("cue-cover");
    if (!live || !cover) return;
    if (S.memo.mode !== mode) {
      S.memo.mode = mode;
      if (mode === "failed") {
        live.hidden = true;
        cover.className = "cue-cover";
        cover.innerHTML = chordListHTML();
        cover.hidden = false;
      } else if (mode === "hidden" || mode === "ad") {
        // Keep the panel's height: the live cue stays in place, invisible, under this cover.
        live.hidden = false;
        live.style.visibility = "hidden";
        cover.className = "cue-cover overlay";
        cover.innerHTML = mode === "hidden"
          ? `<p class="cover-title">Cues hidden</p><p><button type="button" class="btn" data-act="hide">Show cues</button></p>`
          : `<p class="cover-title">Ad or different video, cues paused</p><p class="muted">Cues come back by themselves when the song plays.</p>`;
        cover.hidden = false;
      } else {
        live.hidden = false;
        live.style.visibility = "";
        cover.hidden = true;
        cover.innerHTML = "";
      }
    }
    if (mode === "failed") return;
    const now = cue.now, next = cue.next;
    const nowKey = partKey(now);
    if (S.memo.now !== nowKey) {
      S.memo.now = nowKey;
      setChord($("now-chord"), now ? now.display : "—", Boolean(now && now.kind === "chord"));
      setHidden($("now-quick"), !(now && now.quick));
      setDots($("now-dots"), now, true);
    }
    const nextText = next ? next.display : now && now.kind === "end" ? "" : "End";
    const nextKey = `${partKey(next)}:${nextText}`;
    if (S.memo.next !== nextKey) {
      S.memo.next = nextKey;
      setChord($("next-chord"), nextText, Boolean(next && next.kind === "chord"));
      setHidden($("next-quick"), !(next && next.quick));
      setDots($("next-dots"), next, false);
      $("next-col").classList.toggle("bar-start", Boolean(next && next.barStart === true));
    }
    const count = countText(cue);
    if (S.memo.count !== count) { S.memo.count = count; $("cue-count").textContent = count; }
    const hints = [];
    if (cue.inBeatGrid && cue.approxBars) hints.push("approx bars");
    if (S.song.rhythm && S.song.rhythm.beats_per_bar_assumed) hints.push(`${cue.beatsPerBar} beats/bar assumed`);
    if (S.video && S.video.timing_checked === false) hints.push("timing unchecked");
    const hint = hints.join(" · ");
    if (S.memo.hint !== hint) { S.memo.hint = hint; $("cue-hint").textContent = hint; }
    const note = mode === "live" ? stateNote() : "";
    if (S.memo.note !== note) {
      S.memo.note = note;
      const noteEl = $("cue-note");
      noteEl.textContent = note;
      setHidden(noteEl, !note);
    }
  }

  function setHidden(el, hidden) { if (el && el.hidden !== hidden) el.hidden = hidden; }

  function countText(cue) {
    const now = cue.now;
    if (!now) return "";
    if (!S.played && S.state !== 1 && S.state !== 3 && !S.failed && now.kind !== "empty") {
      return !S.ready ? "Loading video…" : (num(S.song.capo) && S.song.capo > 0 ? `Capo ${S.song.capo} on, then tap ▶` : "Tap ▶ to start");
    }
    if (now.kind === "end") return "End of chart";
    if (now.kind === "empty") return "No chord chart";
    const target = now.idx < 0 ? "first chord" : cue.toEnd ? "end" : "change";
    if (cue.beatsUntilChange !== null) return `${plural(cue.beatsUntilChange, "beat")} to ${target}`;
    // Media seconds / playback rate = wall-clock seconds the player will take.
    if (cue.secondsUntilChange !== null) return `${(cue.secondsUntilChange / S.rate).toFixed(1)} s to ${target}`;
    return "";
  }

  function setChord(el, text, isChord) {
    el.textContent = text;
    el.className = `cue-chord ${isChord ? sizeClass(text) : "word"}`;
  }

  const GLYPH = { past: "◉", active: "●", future: "○" };
  function setDots(el, part, isNow) {
    if (!part || !part.dots.length) {
      // Outside the beat grid: show the hold length in seconds (the count line counts down).
      const seconds = part && part.idx >= 0 && num(part.seconds);
      el.className = seconds ? "dots seconds" : "dots";
      el.textContent = seconds ? `${(part.seconds / S.rate).toFixed(1)} s` : "";
      el.style.removeProperty("--units");
      el.setAttribute("aria-label", seconds ? `${(part.seconds / S.rate).toFixed(1)} seconds` : "");
      return;
    }
    el.className = "dots";
    const bars = new Set(part.barBefore);
    let units = 0.4;
    let html = "";
    if (part.dotOffset > 0) { html += `<span class="dot-more" aria-hidden="true">…</span>`; units += 1.1; }
    part.dots.forEach((dot, j) => {
      if (bars.has(j)) { html += `<span class="bar" aria-hidden="true"></span>`; units += 0.55; }
      html += `<span class="dot ${dot.state}" aria-hidden="true">${GLYPH[dot.state]}</span>`;
      units += 1.1;
    });
    if (part.more > 0) { html += `<span class="dot-more" aria-hidden="true">+${part.more}</span>`; units += 0.45 * (String(part.more).length + 1) + 0.4; }
    el.innerHTML = html;
    // Dots grow to fill the column (capped in CSS) so short holds read from a music stand.
    el.style.setProperty("--units", units.toFixed(2));
    el.setAttribute("aria-label", isNow && part.active >= 0 ? `Beat ${part.active + 1} of ${part.beats}` : plural(part.beats, "beat"));
  }

  function chordListHTML() {
    const items = S.timeline.filter(e => e.label !== "N").map(e => `<li><time>${Core.formatTime(e.s)}</time> <b>${esc(Core.displayLabel(e.label))}</b></li>`);
    const video = analysedVideo();
    const link = video ? `<a class="btn" href="${esc(watchUrl(video.video_id, 0))}" target="_blank" rel="noopener">Open on YouTube</a>` : "";
    return `<p class="cover-title">${esc(S.failed || "Cues unavailable")}</p>${link ? `<p>${link}</p>` : ""}
      <p class="muted">Chord list, not synced. Times are for the analysed recording.</p>
      <ol class="chord-list">${items.join("")}</ol>`;
  }

  // ---------------------------------------------------------------- strum panel
  function renderStrumPanel() {
    const panel = $("strum-panel");
    if (!panel) return;
    const pattern = S.patterns.find(p => p.id === S.patternId);
    if (!pattern) { panel.hidden = true; panel.innerHTML = ""; S.strumCells = []; return; }
    panel.hidden = false;
    const selector = S.patterns.length > 1 ? `<span class="seg" role="group" aria-label="Practice pattern">${S.patterns.map((p, i) => {
      const short = String(p.name || "").split(":")[0].trim() || (i ? "Next" : "Start");
      return `<button type="button" class="btn small" data-act="pattern" data-p="${esc(p.id)}" aria-pressed="${p.id === pattern.id}">${esc(short)}</button>`;
    }).join("")}</span>` : "";
    const counts = Array.isArray(pattern.counts) ? pattern.counts : [];
    const cells = pattern.strokes.map((stroke, i) => `<div class="stroke${stroke === "D" || stroke === "U" ? "" : " rest"}" data-i="${i}">
      <b aria-hidden="true">${Core.strokeGlyph(stroke)}</b><span>${esc(counts[i] !== undefined ? counts[i] : "")}</span></div>`).join("");
    const label = pattern.strokes.map((s, i) => `${counts[i] !== undefined ? counts[i] : i + 1} ${s === "D" ? "down" : s === "U" ? "up" : "skip"}`).join(", ");
    const name = String(pattern.name || "").includes(":") ? String(pattern.name).split(":").slice(1).join(":").trim() : String(pattern.name || "");
    panel.innerHTML = `<div class="strum-head"><h2 class="panel-title">Suggested practice pattern, not the recorded part</h2>${selector}</div>
      <div class="strokes" style="--steps:${pattern.strokes.length}" role="img" aria-label="${esc(label)}">${cells}</div>
      <p class="strum-desc">${name ? `<b>${esc(name)}.</b> ` : ""}${esc(pattern.description || "")}</p>`;
    S.strumCells = Array.from(panel.querySelectorAll(".stroke"));
    S.memo.strum = null;
  }

  function renderStrumStep(t) {
    if (!S.strumCells.length) return;
    const pattern = S.patterns.find(p => p.id === S.patternId);
    const live = cueMode() === "live";
    const step = live ? Core.strumStep(S.song, pattern, t) : null;
    const key = `${S.patternId}:${step}`;
    if (S.memo.strum === key) return;
    S.memo.strum = key;
    S.strumCells.forEach((cell, i) => cell.classList.toggle("on", i === step));
  }

  // ---------------------------------------------------------------- chord diagrams
  function renderDiagrams(cue) {
    if (!settings.diagrams) return;
    const mode = cueMode();
    const nowLabel = mode === "live" && cue.now && cue.now.idx >= 0 ? cue.now.label : null;
    const nextLabel = mode === "live" && cue.next ? cue.next.label : null;
    // Always draw the capo-shape fingering (what the hand holds); the view only changes the caption.
    const capo = num(S.song.capo) && S.song.capo > 0 ? S.song.capo : 0;
    const grip = p => p && p.idx >= 0 && p.kind === "chord" ? Core.shapeLabel(p.sounding, { capo, view: "shapes", quality: settings.quality }) : null;
    const nowGrip = nowLabel ? grip(cue.now) : null, nextGrip = nextLabel ? grip(cue.next) : null;
    const key = `${nowLabel}|${nextLabel}|${nowGrip}|${nextGrip}`;
    if (S.memo.diag === key) return;
    S.memo.diag = key;
    const box = $("diagrams");
    if (!box) return;
    box.innerHTML = diagramHTML(nowLabel, "Now", 132, nowGrip) + diagramHTML(nextLabel, "Next", 104, nextGrip);
  }

  function diagramHTML(label, role, size, gripLabel) {
    if (!label || label === "N" || label === "X") {
      return `<figure class="diagram empty"><figcaption><span class="d-role">${role}</span> <span class="d-name">${label ? esc(Core.displayLabel(label)) : "—"}</span></figcaption></figure>`;
    }
    const lib = window.StrumShapes;
    let shape = null, svg = "";
    try { shape = lib && typeof lib.getShape === "function" ? lib.getShape(gripLabel || label) : null; } catch (_) { shape = null; }
    if (shape && typeof lib.renderShapeSVG === "function") {
      try { svg = String(lib.renderShapeSVG(shape, { size }) || ""); } catch (_) { svg = ""; }
    }
    const capo = num(S.song.capo) && S.song.capo > 0 ? S.song.capo : 0;
    const capoNote = gripLabel && gripLabel !== label ? `<p class="d-note">${esc(gripLabel)} shape, capo ${esc(capo)}</p>`
      : capo > 0 ? `<p class="d-note">Shape with capo ${esc(capo)}</p>` : "";
    return `<figure class="diagram${role === "Now" ? " now" : ""}"><figcaption><span class="d-role">${role}</span> <span class="d-name">${esc(label)}</span></figcaption>
      ${svg ? `<div class="d-svg">${svg}</div>` : `<p class="muted d-missing">No diagram</p>`}
      ${shape && shape.note ? `<p class="d-note">${esc(shape.note)}</p>` : ""}${svg ? capoNote : ""}</figure>`;
  }

  // ---------------------------------------------------------------- controls and details
  function updateTransport() {
    if (!S) return;
    const enabled = Boolean(S.player && S.ready && !S.failed);
    for (const id of ["btn-play", "btn-play-cue", "btn-back", "btn-restart"]) { const b = $(id); if (b) b.disabled = !enabled; }
    const playing = S.state === 1 || S.state === 3;
    for (const id of ["btn-play", "btn-play-cue"]) {
      const play = $(id);
      if (!play) continue;
      play.textContent = playing ? "❚❚ Pause" : "▶ Play";
      play.setAttribute("aria-label", playing ? "Pause" : "Play");
    }
    const hide = $("btn-hide");
    if (hide) { hide.textContent = S.cuesHidden ? "Show cues" : "Hide cues"; hide.setAttribute("aria-pressed", String(S.cuesHidden)); }
  }

  function renderViewControls() {
    for (const b of app.querySelectorAll('[data-act="quality"]')) b.setAttribute("aria-pressed", String(b.dataset.v === settings.quality));
    for (const b of app.querySelectorAll('[data-act="view"]')) b.setAttribute("aria-pressed", String(b.dataset.v === settings.view));
    const d = $("btn-diagrams");
    if (d) { d.setAttribute("aria-pressed", String(settings.diagrams)); d.textContent = settings.diagrams ? "Diagrams on" : "Diagrams off"; }
    const panel = $("diagram-panel");
    if (panel) panel.hidden = !settings.diagrams;
    const badge = $("capo-badge");
    if (badge && S) badge.textContent = viewFor(S.song) === "shapes" ? `Capo ${S.song.capo}` : `Capo ${S.song.capo} · sounding names`;
  }

  function renderSync() {
    const out = $("nudge-out");
    if (out) out.textContent = formatNudge(S.nudgeMs);
    const coarse = $("coarse-sync");
    if (coarse) coarse.hidden = !(S.video && S.video.timing_checked === false);
  }

  function renderLatency() {
    const out = $("latency-out");
    if (out) out.textContent = `${latencyMs} ms`;
  }

  function renderDetails() {
    const body = $("details-body");
    if (!body) return;
    const song = S.song, rhythm = song.rhythm || {}, learning = song.learning || {}, chart = song.chart || {};
    const rows = [];
    const add = (term, html) => { if (html) rows.push(`<dt>${term}</dt><dd>${html}</dd>`); };
    let setup = esc(song.setup_note || "");
    if (num(song.capo) && song.capo > 0) {
      const source = song.capo_source === "suggested" ? "suggested for easier shapes" : "from the practice notes";
      setup += `${setup ? " " : ""}Capo ${esc(song.capo)} (${source}). Capo shapes show what your hand holds; Sounding shows the pitches heard.`;
    }
    add("Setup", setup);
    const level = levelOf(song), difficulty = song.difficulty || {};
    if (level) {
      const why = difficulty.override_reason || difficulty.tier_reason || "";
      add("Level", `<b>Level ${level.level}${level.label ? ` · ${esc(level.label)}` : ""}.</b> ${esc(why)}`);
    }
    add("Skill focus", esc(learning.skill_focus || ""));
    add("Before this", esc(learning.prerequisites || ""));
    add("Chart", `Provisional ${esc(chart.source || "automatic draft")}; not reviewed, and chords may be wrong. Simple view reduces chords to core shapes.`);
    const bpm = num(rhythm.bpm) ? `~${Math.round(rhythm.bpm)} BPM, ` : "";
    const anchored = rhythm.bar_model === "anchored-1" && num(rhythm.bar_confident_pct);
    const barNote = anchored
      ? (rhythm.bar_confident_pct >= 95 ? " Bar lines follow a steady estimated downbeat fitted to the chord changes."
        : rhythm.bar_confident_pct <= 0.5 ? " All bar lines are approx bars: the downbeat is a guess, and a bar may restart at a chord change."
        : ` About ${esc(Math.round(100 - rhythm.bar_confident_pct))}% of the song shows approx bars: the downbeat there is a guess, and a bar may restart at a chord change.`)
      : rhythm.bar_phase_confident ? "" : " Bar lines follow an estimated downbeat (approx bars) and may sit a beat off.";
    add("Beats", `Estimated beat grid: ${bpm}${esc(rhythm.meter_label || "meter unknown")}. Bars are approximate; downbeats are not verified.${rhythm.beats_per_bar_assumed ? ` ${esc(rhythm.beats_per_bar || 4)} beats per bar assumed.` : ""}${barNote}`);
    const corrections = chart.corrections && Array.isArray(chart.corrections) ? chart.corrections : [];
    if (corrections.length) {
      // A "timing" entry summarises the exporter's repetition-consistency moves (docs/STRUMALONG_APP.md, "Timing fix").
      const item = c => c.kind === "timing"
        ? `<li>${esc(c.note || "Some chord changes moved by one beat")}${Array.isArray(c.moves) && c.moves.length
          ? `: ${c.moves.map(m => `${Core.formatTime(m.at)} ${esc(m.from)} → ${esc(m.to)} ${m.shift < 0 ? "earlier" : "later"}`).join(", ")}` : ""}.</li>`
        : `<li>${Core.formatTime(c.start)}–${Core.formatTime(c.end)}: ${esc(c.from)} → ${esc(c.to)}${c.note ? ` (${esc(c.note)})` : ""}</li>`;
      add("Corrections", `<ul>${corrections.map(item).join("")}</ul>`);
    }
    if (song.strumming && song.strumming.note) add("Strumming", esc(song.strumming.note));
    const v = S.video;
    if (v) {
      add("Video", `${esc(v.uploader || "YouTube")}${v.note ? ` · ${esc(v.note)}` : ""}${v.timing_checked === false ? " · <b>timing unchecked</b>" : ""}
        <br><a href="${esc(watchUrl(v.video_id, 0))}" target="_blank" rel="noopener" data-act="open-yt">Open on YouTube</a> <span class="muted">(cues don't follow there)</span>`);
    }
    const sources = learning.sources && Array.isArray(learning.sources) ? learning.sources : [];
    const links = sources.map(s => { const url = safeUrl(s && s.url); return url ? `<li><a href="${esc(url)}" target="_blank" rel="noopener">${esc(s.title || url)}</a></li>` : ""; }).join("");
    if (links) add("Lessons", `<ul>${links}</ul>`);
    add("Audio delay", `<span class="row sync"><button type="button" class="btn small" data-act="latency" data-ms="-25" aria-label="Less audio delay">−25</button>
      <output id="latency-out" class="nudge-out">${latencyMs} ms</output>
      <button type="button" class="btn small" data-act="latency" data-ms="25" aria-label="More audio delay">+25</button></span>
      <span class="muted">For Bluetooth speakers or headphones: delays every song's cues. Use Sync for one video.</span>`);
    body.innerHTML = `<dl>${rows.join("")}</dl>`;
  }

  // ---------------------------------------------------------------- status messages under the player
  const MSG_ORDER = ["error", "switch", "video", "autoplay", "info"];
  function setMsg(slot, html, kind) {
    if (!S) return;
    if (html) S.msgs[slot] = { html, kind: kind || (slot === "error" ? "error" : slot === "autoplay" ? "warn" : "") };
    else delete S.msgs[slot];
    const box = $("player-status");
    if (box) box.innerHTML = MSG_ORDER.filter(k => S.msgs[k]).map(k => `<p class="msg ${S.msgs[k].kind}">${S.msgs[k].html}</p>`).join("");
  }

  // ---------------------------------------------------------------- events
  app.addEventListener("click", event => {
    const target = event.target.closest("[data-act]");
    if (!target || !app.contains(target)) return;
    const act = target.dataset.act;
    if (act === "reload") { location.reload(); return; }
    if (act === "resume") {
      const t = Number(target.dataset.t);
      resumeRequest = { id: target.dataset.id, t: Number.isFinite(t) ? t : 0 };
      return; // the link's hash change does the routing
    }
    if (!S) return;
    switch (act) {
      case "play": togglePlay(); break;
      case "back10": seekTo(S.pt - 10); break;
      case "restart": seekTo(0); break;
      case "hide": S.cuesHidden = !S.cuesHidden; updateTransport(); frame(); break;
      case "nudge": {
        S.nudgeMs = clampInt(S.nudgeMs + Number(target.dataset.ms), NUDGE_LIMIT_MS);
        if (S.video) save("offset:" + S.video.video_id, S.nudgeMs);
        renderSync(); frame(); break;
      }
      case "nudge-reset":
        S.nudgeMs = 0;
        if (S.video) save("offset:" + S.video.video_id, 0);
        renderSync(); frame(); break;
      case "latency":
        latencyMs = clampInt(latencyMs + Number(target.dataset.ms), 1000);
        save("latency", latencyMs);
        renderLatency(); frame(); break;
      case "quality":
        settings.quality = target.dataset.v === "full" ? "full" : "core";
        saveSettings(); rebuildTimeline(); renderViewControls(); frame(); break;
      case "view":
        settings.view = target.dataset.v === "sounding" ? "sounding" : "shapes";
        saveSettings(); rebuildTimeline(); renderViewControls(); frame(); break;
      case "diagrams":
        settings.diagrams = !settings.diagrams;
        saveSettings(); S.memo.diag = null; renderViewControls(); frame(); break;
      case "pattern":
        if (S.patterns.some(p => p.id === target.dataset.p)) {
          S.patternId = target.dataset.p;
          settings.patterns[S.song.id] = S.patternId;
          saveSettings(); renderStrumPanel(); frame();
        }
        break;
      case "retry":
        setMsg("error", null);
        try { S.player.cueVideoById({ videoId: S.video.video_id, startSeconds: Math.max(0, S.pt) }); } catch (_) { /* ignore */ }
        break;
      case "open-yt":
        if (S.video) target.href = watchUrl(S.video.video_id, S.pt);
        try { if (S.player && S.ready && (S.state === 1 || S.state === 3)) S.player.pauseVideo(); } catch (_) { /* ignore */ }
        break;
      default: break;
    }
  });

  app.addEventListener("change", event => {
    if (!S || event.target.id !== "sel-speed") return;
    const rate = Number(event.target.value);
    if (S.player && S.ready && num(rate)) { try { S.player.setPlaybackRate(rate); } catch (_) { /* ignore */ } }
  });

  document.addEventListener("keydown", event => {
    if (!S || event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
    const tag = event.target && event.target.tagName ? event.target.tagName : "";
    if (/^(INPUT|TEXTAREA|SELECT|BUTTON|SUMMARY|A|OUTPUT)$/.test(tag) || (event.target && event.target.isContentEditable)) return;
    if (event.key === " " || event.key === "k") { event.preventDefault(); togglePlay(); }
    else if (event.key === "ArrowLeft" || event.key === "j") { event.preventDefault(); seekTo(S.pt - 10); }
    else if (event.key === "h") { S.cuesHidden = !S.cuesHidden; updateTransport(); frame(); }
  });

  document.addEventListener("visibilitychange", () => {
    if (!S) return;
    if (document.visibilityState === "hidden") {
      // No background play: pause when the page is hidden.
      try { if (S.player && S.ready && (S.state === 1 || S.state === 3)) S.player.pauseVideo(); } catch (_) { /* ignore */ }
      saveLast();
    } else if (S.state === 1) requestWakeLock();
  });
  window.addEventListener("pagehide", () => saveLast());
  window.addEventListener("hashchange", route);
  route();
})();
