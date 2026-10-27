/* Strum Along: app shell, hash router, YouTube controller and render loop.
 * Spec: docs/STRUMALONG_APP.md ("UI" and "Playback and sync"). Plain ES2020, no build step.
 * Charts are provisional automatic drafts; strum patterns are practice suggestions; beats are
 * estimated and bars approximate. The official YouTube player stays visible with nothing on it. */
(function () {
  "use strict";
  const Core = window.StrumCore;
  const RepeatTiming = window.StrumRepeatTiming;
  const Session = window.StrumSession;
  const Library = window.StrumLibrary;
  const app = document.getElementById("app");
  if (!app) return;
  if (!Core) { app.innerHTML = '<p class="msg error">Strum Along could not start: lib/core.js did not load. Reload to try again.</p><p><a class="btn" href="">Reload</a></p>'; return; }
  if (!Session) { app.innerHTML = '<p class="msg error">Strum Along could not start: lib/session.js did not load. Reload to try again.</p><p><a class="btn" href="">Reload</a></p>'; return; }
  if (!Library) { app.innerHTML = '<p class="msg error">Strum Along could not start: lib/library.js did not load. Reload to try again.</p><p><a class="btn" href="">Reload</a></p>'; return; }

  // ---------------------------------------------------------------- practice session + storage adapter
  // Playback, resume and persistence rules live in lib/session.js; app.js only renders.
  const store = Session.createStore({
    getItem: key => window.localStorage.getItem(key),
    setItem: (key, value) => window.localStorage.setItem(key, value),
  });
  const settings = () => store.settings();

  // ---------------------------------------------------------------- small helpers
  const $ = id => document.getElementById(id);
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = value => String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, c => ESC[c]);
  const validSongId = id => typeof id === "string" && /^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$/.test(id);
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
    const match = /^#\/(song|ready)\/([^/?#]+)\/?$/.exec(location.hash || "");
    if (match) {
      let id = "";
      try { id = decodeURIComponent(match[2]); } catch (_) { id = ""; }
      if (match[1] === "ready") showReady(id, gen); else showSong(id, gen);
    } else showLibrary(gen);
    try { window.scrollTo(0, 0); } catch (_) { /* ignore */ }
  }

  // ---------------------------------------------------------------- library (Jukebox journey, #53)
  // Search and Surprise me on top, the resume chip, then horizontal shelves: favourites, then one per level.
  let libQuery = ""; // kept while moving between the library and a song

  const listedSongs = catalogue => Array.isArray(catalogue && catalogue.songs) ? catalogue.songs.filter(s => s && validSongId(s.id)) : [];
  const readyHref = id => `#/ready/${encodeURIComponent(id)}`;

  async function showLibrary(gen) {
    document.title = "Strum Along";
    app.className = "app view-library";
    app.innerHTML = `<header class="lib-head"><div class="lib-title"><h1>Strum Along <span class="sub">· music-os</span></h1>
        <button type="button" class="btn" data-act="surprise">🎲 Surprise me</button></div>
      <p class="tagline">Provisional automatic chord charts. For personal practice.</p>
      <input id="lib-search" class="lib-search" type="search" placeholder="Search songs or artists" aria-label="Search songs or artists" autocomplete="off" autocorrect="off" spellcheck="false" value="${esc(libQuery)}"></header>
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
    renderLibrary(catalogue);
  }

  function renderLibrary(catalogue) {
    const body = $("lib-body");
    if (!body) return;
    const songs = listedSongs(catalogue);
    let html = "";
    if (libQuery.trim()) {
      const found = Library.search(songs, libQuery);
      html += found.length ? `<ul class="cards results">${found.map(songCard).join("")}</ul>`
        : `<p class="msg">No song matches “${esc(libQuery.trim())}”.</p>`;
    } else {
      const resumePoint = store.resumePoint(songs);
      if (resumePoint) {
        const { song: lastSong, t } = resumePoint;
        html += `<a class="resume" href="#/song/${encodeURIComponent(lastSong.id)}" data-act="resume" data-id="${esc(lastSong.id)}" data-t="${t}">
          <span class="resume-icon" aria-hidden="true">${t ? "▶" : "↻"}</span><span>${t ? "Resume" : "Play again:"} <b>${esc(lastSong.title)}</b>${t ? ` at ${Core.formatTime(t)}` : ""}</span></a>`;
      }
      for (const shelf of Library.shelves({ groups: catalogue && catalogue.groups, songs }, store.favourites())) {
        html += `<section class="group shelf-group"><h2>${esc(shelf.title)}</h2>${shelf.note ? `<p class="group-note">${esc(shelf.note)}</p>` : ""}
          <ul class="cards shelf">${shelf.songs.map(songCard).join("")}</ul></section>`;
      }
      if (!songs.length) html += `<p class="msg">No songs are listed yet.</p>`;
    }
    html += `<footer class="lib-foot"><p>Chords are automatic drafts and may be wrong. Strum patterns are practice suggestions, not the recorded parts. Beats are estimated; bars are approximate.</p></footer>`;
    body.innerHTML = html;
  }

  function songCard(s) {
    const chips = (Array.isArray(s.core_shapes) ? s.core_shapes : []).map(c => `<span class="chip">${esc(c)}</span>`).join("");
    const badges = [];
    if (num(s.capo) && s.capo > 0) badges.push(`<span class="badge capo">Capo ${esc(s.capo)}</span>`);
    if (s.playable_embed === false) badges.push(`<span class="badge warn">${/unchecked/i.test(s.embed_note) ? "timing unchecked" : "alternate video"}</span>`);
    return `<li><a class="card" href="${readyHref(s.id)}">
      <span class="card-main"><span class="card-title">${esc(s.title)}</span><span class="card-artist">${esc(s.artist)}</span></span>
      ${chips ? `<span class="chips" aria-label="Core shapes">${chips}</span>` : ""}
      ${badges.length ? `<span class="card-meta">${badges.join(" ")}</span>` : ""}
    </a></li>`;
  }

  // Surprise me: a song at the learner's level, opened on its get-ready sheet.
  async function surpriseMe(lastId) {
    let catalogue;
    try { catalogue = await getCatalogue(); } catch (_) { return; }
    const pick = Library.surprise(listedSongs(catalogue), { lastId, plays: store.plays() });
    if (pick) location.hash = readyHref(pick.id);
  }

  const favouriteLabel = id => store.favourites().includes(id) ? "★ Favourite" : "☆ Favourite";

  // ---------------------------------------------------------------- get-ready sheet
  // What you need before pressing Play: capo, the core shapes, and the first practice pattern.
  async function showReady(id, gen) {
    app.className = "app view-ready";
    app.innerHTML = `<header class="topbar"><a class="back" href="#/">‹ Songs</a><div class="top-title"><h1>Loading…</h1></div></header>
      <p class="muted pad">Loading song…</p>`;
    if (!validSongId(id)) { songError("Song not found.", false); return; }
    let song;
    try { song = await getSong(id); }
    catch (error) {
      if (gen !== routeGen) return;
      songError(error && error.status === 404 ? "Song not found." : "Couldn't load this song. Check your connection.", !(error && error.status === 404));
      return;
    }
    if (gen !== routeGen) return;
    if (!song || !Array.isArray(song.chords)) { songError("This song's chart is missing or damaged.", false); return; }
    document.title = `${song.title || "Song"} · Strum Along`;
    const capo = num(song.capo) && song.capo > 0 ? song.capo : 0;
    const d = song.difficulty || {};
    const shapes = Array.isArray(d.main_shapes) && d.main_shapes.length ? d.main_shapes : [];
    const pattern = song.strumming && Array.isArray(song.strumming.patterns) ? song.strumming.patterns.find(p => p && Array.isArray(p.strokes) && p.strokes.length) : null;
    const bpm = song.rhythm && num(song.rhythm.bpm) ? Math.round(song.rhythm.bpm) : null;
    const lib = window.StrumShapes;
    const diagram = label => {
      let svg = "";
      try { const shape = lib && lib.getShape(label); svg = shape ? String(lib.renderShapeSVG(shape, { size: 84 }) || "") : ""; } catch (_) { svg = ""; }
      return `<figure class="diagram"><figcaption><span class="d-name">${esc(label)}</span></figcaption>${svg ? `<div class="d-svg">${svg}</div>` : `<p class="muted d-missing">No diagram</p>`}</figure>`;
    };
    app.innerHTML = `<header class="topbar">
      <a class="back" href="#/" aria-label="Back to songs">‹ Songs</a>
      <div class="top-title"><h1>${esc(song.title)}</h1><p>${esc(song.artist)}</p></div>
      <span class="top-badges">${capo ? `<span class="badge capo">Capo ${capo}</span>` : ""}${levelBadge(song)}<span class="badge prov" title="Automatic chord chart; not reviewed">Provisional</span></span>
    </header>
    <div class="ready">
      <p class="ready-meta">${esc([capo ? "" : "No capo", bpm ? `~${bpm} BPM` : ""].filter(Boolean).join(" · "))}</p>
      ${song.setup_note ? `<p class="hint">${esc(song.setup_note)}</p>` : ""}
      ${shapes.length ? `<section class="panel"><h2 class="panel-title">You'll need</h2><div class="diagrams ready-diagrams">${shapes.map(diagram).join("")}</div></section>` : ""}
      ${pattern ? `<section class="panel"><h2 class="panel-title">Strum</h2>${strokeGrid(pattern)}
        <p class="hint">${esc(pattern.name || "")}. A practice suggestion, not the recorded part; switch patterns in the player.</p></section>` : ""}
      <a class="btn btn-play ready-play" href="#/song/${encodeURIComponent(song.id)}">▶ Play</a>
      <p class="row"><button type="button" class="btn" data-act="fav" data-id="${esc(song.id)}" aria-pressed="${store.favourites().includes(song.id)}">${favouriteLabel(song.id)}</button></p>
    </div>`;
  }

  function strokeGrid(pattern) {
    const n = pattern.strokes.length;
    const counts = Array.isArray(pattern.counts) ? pattern.counts : [];
    return `<div class="stroke-grid" style="grid-template-columns:repeat(${n},1fr)" role="img" aria-label="${esc(pattern.strokes.join(" "))}">
      ${pattern.strokes.map(x => `<span class="stroke${x === "D" || x === "U" ? "" : " rest"}">${x === "D" || x === "U" ? esc(x) : "·"}</span>`).join("")}
      ${pattern.strokes.map((_, i) => `<span class="stroke-count">${esc(counts[i] || "")}</span>`).join("")}</div>`;
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

  // Render-side state for the song page. Session fields read through it are read-only:
  // every change goes through S.session.
  const SESSION_FIELDS = ["song", "videos", "patterns", "video", "state", "played", "ready", "failed", "ad", "rate", "pt", "timeline", "patternId", "nudgeMs"];
  function pageState(session, gen) {
    const page = { gen, session, cuesHidden: false, raf: 0, poll: 0, loadTimer: 0, playTimer: 0, msgs: {}, memo: {}, epoch: session.epoch, strumCells: [] };
    for (const key of SESSION_FIELDS) Object.defineProperty(page, key, { get: () => session[key], enumerable: true });
    return page;
  }

  function startSong(song, gen) {
    const resume = resumeRequest && resumeRequest.id === song.id && num(resumeRequest.t) ? resumeRequest.t : 0;
    resumeRequest = null;
    S = pageState(Session.createSession({ song, store, resume }), gen);
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
    const page = S;
    S.loadTimer = window.setTimeout(() => {
      if (S !== page || S.ready || S.failed) return;
      // A stalled API script never settles its promise: forget it so the next song page loads it again.
      if (!(window.YT && typeof window.YT.Player === "function")) ytPromise = null;
      setMsg("error", `YouTube is taking a while to load. Check the connection, or reload the page. <button type="button" class="btn small" data-act="reload">Reload</button>`);
    }, 15000);
    loadYouTube().then(YT => { if (S === page) createPlayer(YT); })
      .catch(() => { if (S === page) setMsg("error", `YouTube could not load. Check the connection. <button type="button" class="btn small" data-act="reload">Reload</button>`); });
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
        <section id="after-panel" class="panel after-panel" aria-label="Song finished" hidden></section>
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
        <section id="diagram-panel" class="panel diagram-panel" aria-label="Chord diagrams"${settings().diagrams ? "" : " hidden"}>
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

  // ---------------------------------------------------------------- player
  // The player adapter: the session module reaches YouTube only through these calls.
  function youTubeAdapter(yt) {
    return {
      currentTime: () => yt.getCurrentTime(),
      duration: () => yt.getDuration(),
      playbackRate: () => yt.getPlaybackRate(),
      availableRates: () => yt.getAvailablePlaybackRates(),
      seekTo: seconds => yt.seekTo(seconds, true),
      cue: (videoId, startSeconds) => yt.cueVideoById({ videoId, startSeconds }),
      play: () => yt.playVideo(),
      pause: () => yt.pauseVideo(),
      setRate: rate => yt.setPlaybackRate(rate),
      destroy: () => { if (typeof yt.destroy === "function") yt.destroy(); },
    };
  }

  function createPlayer(YT) {
    const page = S, session = page.session;
    const vars = { playsinline: 1, rel: 0, controls: 1, enablejsapi: 1, fs: 0 };
    if (/^https?:/.test(location.protocol)) vars.origin = location.origin;
    if (session.startAt > 0) vars.start = Math.floor(session.startAt);
    const live = fn => (...args) => { if (S === page) { try { fn(...args); } catch (error) { console.error(error); } } };
    try {
      session.attach(youTubeAdapter(new YT.Player("yt-player", {
        width: "100%", height: "100%", videoId: session.video.video_id, playerVars: vars,
        events: {
          onReady: live(onReady),
          onStateChange: live(event => onState(event.data)),
          onError: live(event => onPlayerError(event.data)),
          onAutoplayBlocked: live(() => setMsg("autoplay", "Tap ▶ in the video to start.")),
          onPlaybackRateChange: live(event => {
            const sel = $("sel-speed"); if (sel) sel.value = String(event.data);
            S.session.rateChange(event.data);
            frame();
          }),
        },
      })));
    } catch (_) {
      setMsg("error", `The YouTube player could not start. Reload to try again. <button type="button" class="btn small" data-act="reload">Reload</button>`);
    }
  }

  function onReady() {
    S.session.playerReady();
    window.clearTimeout(S.loadTimer);
    if (S.msgs.error && !S.failed) setMsg("error", null);
    refreshRates();
    updateTransport();
    frame();
  }

  function refreshRates() {
    const wrap = $("speed-wrap"), sel = $("sel-speed");
    S.session.refreshRate();
    if (!wrap || !sel) return;
    const rates = S.session.availableRates();
    if (rates.length <= 1) { wrap.hidden = true; return; }
    sel.innerHTML = rates.map(r => `<option value="${r}">${r === 1 ? "1× (normal)" : `${r}×`}</option>`).join("");
    sel.value = String(S.rate);
    wrap.hidden = false;
  }

  function onState(code) {
    S.session.stateChange(code);
    if (code === 1) {
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
    // The lock is kept while paused (chords are read during a pause) and released when the song ends.
    if (code === 0) { releaseWakeLock(); showAfter(); }
    else if (code === 1) setHidden($("after-panel"), true);
    updateTransport();
    frame();
  }

  const FAIL_TEXT = {
    referrer: "Player configuration error (referrer). This is a page setup problem, not your connection.",
    unavailable: "Video unavailable.",
    "no-embed": "This video can't play inside the app.",
  };
  const failText = reason => FAIL_TEXT[reason] || reason;

  function onPlayerError(code) {
    stopLoop();
    window.clearTimeout(S.playTimer);
    const decision = S.session.error(code);
    if (decision.action === "switch") { showSwitch(code); return; }
    if (decision.action === "fail") { fail(decision.reason); return; }
    setMsg("error", `YouTube reported a playback problem (error ${esc(code)}). <button type="button" class="btn small" data-act="retry">Retry</button>`);
  }

  // The session has already moved to the next listed video and cued it.
  function showSwitch(code) {
    setMsg("error", null);
    const who = S.video && S.video.uploader ? `${esc(S.video.uploader)}'s` : "another";
    setMsg("switch", `Playing ${who} official video instead; the analysed upload can't play here.`);
    console.info(`Strum Along: switched video after YouTube error ${code}`);
    noteVideo();
    renderSync(); renderDetails(); updateTransport();
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

  // reason is a session failure code (FAIL_TEXT) or a message.
  function fail(reason) {
    stopLoop();
    S.session.fail(reason);
    const video = analysedVideo();
    const link = video ? ` <a href="${esc(watchUrl(video.video_id, 0))}" target="_blank" rel="noopener" data-act="open-yt">Open on YouTube</a>` : "";
    setMsg("error", `${esc(failText(reason))}${link}`, "error");
    setMsg("autoplay", null);
    setMsg("video", null);
    setMsg("info", null);
    updateTransport();
    frame();
  }

  function togglePlay() {
    if (!S || !S.session.controllable) return;
    if (S.session.playing) { S.session.pause(); return; }
    // Never start audio with the official player off screen (the lower Play button can be reached
    // after scrolling): bring the player, and the "Tap ▶ in the video" hint under it, into view first.
    const f = document.querySelector(".player-frame");
    if (f) {
      const r = f.getBoundingClientRect();
      if (r.top < 0 || r.bottom > window.innerHeight) f.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    if (!S.session.play()) return;
    requestWakeLock();
    const page = S;
    window.clearTimeout(S.playTimer);
    S.playTimer = window.setTimeout(() => {
      if (S === page && !S.session.playing && !S.failed) setMsg("autoplay", "Tap ▶ in the video to start.");
    }, 2500);
  }

  function seekTo(seconds) {
    if (!S || !S.session.seek(seconds)) return;
    frame();
  }

  function startLoop() { if (S && !S.raf) S.raf = window.requestAnimationFrame(loop); }
  function stopLoop() { if (S && S.raf) { window.cancelAnimationFrame(S.raf); S.raf = 0; } }
  function loop() {
    if (!S) return;
    S.raf = 0;
    if (S.state !== 1) return;
    frame(); // the session saves the last-played position every few seconds while playing
    S.raf = window.requestAnimationFrame(loop);
  }

  function saveLast() { if (S) S.session.saveLast(); }

  function leaveSong() {
    if (!S) return;
    const s = S;
    S = null;
    s.session.leave(); // saves the last-played position and destroys the player
    if (s.raf) window.cancelAnimationFrame(s.raf);
    window.clearInterval(s.poll);
    window.clearTimeout(s.loadTimer);
    window.clearTimeout(s.playTimer);
    releaseWakeLock();
  }

  // ---------------------------------------------------------------- frame + memoized rendering
  function frame() {
    if (!S) return;
    const { t, cue } = S.session.tick();
    // A new timeline, rate, video or failure makes every cached render key stale.
    if (S.epoch !== S.session.epoch) { S.epoch = S.session.epoch; S.memo = {}; }
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

  // After the song (Jukebox journey, #53): count the play, then offer Again, favourite, Surprise me
  // and songs that share its chords.
  async function showAfter() {
    const page = S;
    const count = store.recordPlay(page.song.id);
    let others = [];
    try { const songs = listedSongs(await getCatalogue()); others = Library.similar(songs, songs.find(x => x.id === page.song.id), 5); } catch (_) { others = []; }
    const box = $("after-panel");
    if (S !== page || !box || S.state !== 0) return;
    box.innerHTML = `<h2 class="after-title">Nice one 🎸</h2>
      <p class="hint">${esc(page.song.title)} · played ${count === 1 ? "once" : `${count} times`} on this phone</p>
      <div class="row"><button type="button" class="btn btn-play" data-act="again">↻ Again</button>
        <button type="button" class="btn" data-act="fav" data-id="${esc(page.song.id)}" aria-pressed="${store.favourites().includes(page.song.id)}">${favouriteLabel(page.song.id)}</button>
        <button type="button" class="btn" data-act="surprise">🎲 Surprise me</button></div>
      ${others.length ? `<h3 class="after-sub">Another like this</h3><ul class="cards after-list">${others.map(songCard).join("")}</ul>` : ""}`;
    setHidden(box, false);
    box.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
    return `<p class="cover-title">${esc(S.failed ? failText(S.failed) : "Cues unavailable")}</p>${link ? `<p>${link}</p>` : ""}
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
    if (!settings().diagrams) return;
    const mode = cueMode();
    const nowLabel = mode === "live" && cue.now && cue.now.idx >= 0 ? cue.now.label : null;
    const nextLabel = mode === "live" && cue.next ? cue.next.label : null;
    // Always draw the capo-shape fingering (what the hand holds); the view only changes the caption.
    const capo = num(S.song.capo) && S.song.capo > 0 ? S.song.capo : 0;
    const grip = p => p && p.idx >= 0 && p.kind === "chord" ? Core.shapeLabel(p.sounding, { capo, view: "shapes", quality: settings().quality }) : null;
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
    const enabled = S.session.controllable;
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
    const { quality, view, diagrams } = settings();
    for (const b of app.querySelectorAll('[data-act="quality"]')) b.setAttribute("aria-pressed", String(b.dataset.v === quality));
    for (const b of app.querySelectorAll('[data-act="view"]')) b.setAttribute("aria-pressed", String(b.dataset.v === view));
    const d = $("btn-diagrams");
    if (d) { d.setAttribute("aria-pressed", String(diagrams)); d.textContent = diagrams ? "Diagrams on" : "Diagrams off"; }
    const panel = $("diagram-panel");
    if (panel) panel.hidden = !diagrams;
    const badge = $("capo-badge");
    if (badge && S) badge.textContent = S.session.view() === "shapes" ? `Capo ${S.song.capo}` : `Capo ${S.song.capo} · sounding names`;
  }

  function renderSync() {
    const out = $("nudge-out");
    if (out) out.textContent = formatNudge(S.nudgeMs);
    const coarse = $("coarse-sync");
    if (coarse) coarse.hidden = !(S.video && S.video.timing_checked === false);
  }

  function renderLatency() {
    const out = $("latency-out");
    if (out) out.textContent = `${store.latency()} ms`;
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
      const timing = c => RepeatTiming && RepeatTiming.describe(c);
      const item = c => timing(c)
        ? `<li>${esc(timing(c).note)}${timing(c).moves.length
          ? `: ${timing(c).moves.map(m => `${Core.formatTime(m.at)} ${esc(m.from)} → ${esc(m.to)} ${m.direction}`).join(", ")}` : ""}.</li>`
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
      <output id="latency-out" class="nudge-out">${store.latency()} ms</output>
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
    if (act === "surprise") { surpriseMe(S ? S.song.id : null); return; }
    if (act === "fav") {
      const on = store.toggleFavourite(target.dataset.id);
      target.setAttribute("aria-pressed", String(on));
      target.textContent = on ? "★ Favourite" : "☆ Favourite";
      return;
    }
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
      case "again": setHidden($("after-panel"), true); seekTo(0); if (!S.session.playing) togglePlay(); break;
      case "hide": S.cuesHidden = !S.cuesHidden; updateTransport(); frame(); break;
      case "nudge": {
        S.session.nudgeBy(Number(target.dataset.ms));
        renderSync(); frame(); break;
      }
      case "nudge-reset":
        S.session.resetNudge();
        renderSync(); frame(); break;
      case "latency":
        store.setLatency(store.latency() + Number(target.dataset.ms));
        renderLatency(); frame(); break;
      case "quality":
        S.session.setQuality(target.dataset.v); renderViewControls(); frame(); break;
      case "view":
        S.session.setView(target.dataset.v); renderViewControls(); frame(); break;
      case "diagrams":
        store.setDiagrams(!settings().diagrams); S.memo.diag = null; renderViewControls(); frame(); break;
      case "pattern":
        if (S.session.setPattern(target.dataset.p)) { renderStrumPanel(); frame(); }
        break;
      case "retry":
        setMsg("error", null);
        S.session.retry();
        break;
      case "open-yt":
        if (S.video) target.href = watchUrl(S.video.video_id, S.pt);
        if (S.session.playing) S.session.pause();
        break;
      default: break;
    }
  });

  app.addEventListener("input", event => {
    if (event.target.id !== "lib-search") return;
    libQuery = event.target.value;
    getCatalogue().then(catalogue => { if (!S && $("lib-search")) renderLibrary(catalogue); }).catch(() => {});
  });

  app.addEventListener("change", event => {
    if (!S || event.target.id !== "sel-speed") return;
    const rate = Number(event.target.value);
    S.session.setRate(rate);
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
      if (S.session.playing) S.session.pause();
      saveLast();
    } else if (S.state === 1) requestWakeLock();
  });
  window.addEventListener("pagehide", () => saveLast());
  window.addEventListener("hashchange", route);
  route();
})();
