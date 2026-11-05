/* Jukebox (Strum Along): app shell, hash router, YouTube controller and render loop.
 * Spec: docs/STRUMALONG_APP.md ("UI" and "Playback and sync"). Plain ES2020, no build step.
 * Charts are provisional automatic drafts; strum patterns are practice suggestions; beats are
 * estimated and bars approximate. The official YouTube player stays visible with nothing on it. */
(function () {
  "use strict";
  const Core = window.StrumCore;
  const RepeatTiming = window.StrumRepeatTiming;
  const Session = window.StrumSession;
  const Library = window.StrumLibrary;
  const CountIn = window.StrumCountIn; // optional: without it, Play just plays
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

  const svgIcon = (body, size, solid) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" ${solid ? 'fill="currentColor"' : 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'} aria-hidden="true">${body}</svg>`;
  const ICON = {
    back: svgIcon('<path d="M15 5l-7 7 7 7"></path>', 18),
    shuffle: svgIcon('<path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"></path>', 16),
    star: svgIcon('<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"></path>', 18),
    rewind: svgIcon('<path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"></path>', 20),
    restart: svgIcon('<path d="M6 5v14M19 5L9 12l10 7z"></path>', 20),
    play: svgIcon('<path d="M7 4l13 8-13 8z"></path>', 22, true),
    pause: svgIcon('<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>', 22, true),
  };

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
    const match = /^#\/(song|ready|resume)\/([^/?#]+)\/?$/.exec(location.hash || "");
    if (match) {
      let id = "";
      try { id = decodeURIComponent(match[2]); } catch (_) { id = ""; }
      // #/ready/<id> is the old get-ready sheet's address; it now opens the song page, which carries the sheet's contents.
      // #/resume/<id> is Home's "Pick up where you left off".
      showSong(id, gen, match[1] === "resume");
    } else showLibrary(gen);
    try { window.scrollTo(0, 0); } catch (_) { /* ignore */ }
  }

  // ---------------------------------------------------------------- library (Jukebox journey, #53)
  // Search and Surprise me on top, the resume chip, then horizontal shelves: favourites, then one per level.
  let libQuery = ""; // kept while moving between the library and a song
  let libGenre = "all"; // "all" | "rock" | "pop": filters search, shelves and Surprise me

  const listedSongs = catalogue => Array.isArray(catalogue && catalogue.songs) ? catalogue.songs.filter(s => s && validSongId(s.id)) : [];
  const genreButtons = () => [["all", "All"], ["rock", "Rock"], ["pop", "Pop"]].map(([g, label]) =>
    `<button type="button" class="pill" data-act="genre" data-genre="${g}" aria-pressed="${libGenre === g}">${label}</button>`).join("");
  const songHref = id => `#/song/${encodeURIComponent(id)}`;

  async function showLibrary(gen) {
    document.title = "Jukebox · Music OS";
    app.className = "app view-library";
    app.innerHTML = `<header class="lib-head"><div class="lib-title">
        <a class="icon-btn" href="./" aria-label="Back to home">${ICON.back}</a>
        <h1 class="eyebrow">Jukebox</h1>
        <button type="button" class="btn-surprise" data-act="surprise">${ICON.shuffle} Surprise me</button></div>
      <input id="lib-search" class="lib-search" type="search" placeholder="Search songs or artists" aria-label="Search songs or artists" autocomplete="off" autocorrect="off" spellcheck="false" value="${esc(libQuery)}">
      <span class="genre-seg" role="group" aria-label="Genre">${genreButtons()}</span></header>
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
    const songs = Library.byGenre(listedSongs(catalogue), libGenre);
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
        html += `<section class="group shelf-group"><div class="shelf-head"><h2>${esc(shelf.title)}</h2>${shelf.note ? `<p class="group-note">${esc(shelf.note)}</p>` : ""}</div>
          <ul class="cards shelf">${shelf.songs.map(songCard).join("")}</ul></section>`;
      }
      if (!songs.length) html += `<p class="msg">${libGenre === "all" ? "No songs are listed yet." : `No ${esc(libGenre)} songs are listed yet.`}</p>`;
    }
    html += `<footer class="lib-foot"><p>Chords are automatic drafts and may be wrong. Strum patterns are practice suggestions, not the recorded parts. Beats are estimated; bars are approximate.</p></footer>`;
    body.innerHTML = html;
  }

  function songCard(s, i) {
    const chips = (Array.isArray(s.core_shapes) ? s.core_shapes : []).map(c => `<span class="chip">${esc(c)}</span>`).join("");
    const badges = [];
    if (num(s.capo) && s.capo > 0) badges.push(`<span class="badge capo">Capo ${esc(s.capo)}</span>`);
    if (s.playable_embed === false) badges.push(`<span class="badge warn">${/unchecked/i.test(s.embed_note) ? "timing unchecked" : "alternate video"}</span>`);
    return `<li><a class="card" href="${songHref(s.id)}">
      <span class="card-art tint-${i % 4}" aria-hidden="true">${esc(String(s.title || "").charAt(0))}</span>
      <span class="card-main"><span class="card-title">${esc(s.title)}</span><span class="card-artist">${esc(s.artist)}</span></span>
      ${chips ? `<span class="chips" aria-label="Core shapes">${chips}</span>` : ""}
      ${badges.length ? `<span class="card-meta">${badges.join(" ")}</span>` : ""}
    </a></li>`;
  }

  // Surprise me: a song at the learner's level.
  async function surpriseMe(lastId) {
    let catalogue;
    try { catalogue = await getCatalogue(); } catch (_) { return; }
    const pick = Library.surprise(Library.byGenre(listedSongs(catalogue), libGenre), { lastId, plays: store.plays() });
    if (pick) location.hash = songHref(pick.id);
  }

  const favouriteLabel = id => store.favourites().includes(id) ? "★ Favourite" : "☆ Favourite";

  // ---------------------------------------------------------------- song page
  async function showSong(id, gen, resuming) {
    app.className = "app view-song";
    app.innerHTML = `<header class="topbar"><a class="icon-btn" href="#/" aria-label="Back to songs">${ICON.back}</a><div class="top-title"><h1>Loading…</h1></div></header>
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
    if (resuming) {
      const point = store.resumePoint([{ id: song.id, duration_seconds: song.recording && song.recording.duration_seconds }]);
      if (point) resumeRequest = { id: song.id, t: point.t };
      history.replaceState(null, "", songHref(song.id));
    }
    startSong(song, gen);
  }

  function songError(message, retry) {
    app.innerHTML = `<header class="topbar"><a class="icon-btn" href="#/" aria-label="Back to songs">${ICON.back}</a><div class="top-title"><h1>Jukebox</h1></div></header>
      <p class="msg error">${esc(message)}</p>${retry ? `<p><button type="button" class="btn" data-act="reload">Try again</button></p>` : ""}`;
  }

  // Render-side state for the song page. Session fields read through it are read-only:
  // every change goes through S.session.
  const SESSION_FIELDS = ["song", "videos", "patterns", "video", "state", "played", "ready", "failed", "ad", "rate", "pt", "timeline", "patternId", "nudgeMs"];
  function pageState(session, gen) {
    const page = { gen, session, cuesHidden: false, breakdownOpen: false, resumeAfterBreakdown: false, known: null, raf: 0, poll: 0, loadTimer: 0, playTimer: 0, msgs: {}, memo: {}, epoch: session.epoch, strumCells: [] };
    for (const key of SESSION_FIELDS) Object.defineProperty(page, key, { get: () => session[key], enumerable: true });
    return page;
  }

  function startSong(song, gen) {
    const resume = resumeRequest && resumeRequest.id === song.id && num(resumeRequest.t) ? resumeRequest.t : 0;
    resumeRequest = null;
    S = pageState(Session.createSession({ song, store, resume }), gen);
    document.title = `${song.title || "Song"} · Jukebox`;
    app.innerHTML = songSkeleton(song);
    renderStrumPanel();
    renderBarLine();
    loadKnownShapes();
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
    const level = levelOf(song);
    const bpm = song.rhythm && num(song.rhythm.bpm) ? Math.round(song.rhythm.bpm) : null;
    const sub = [song.artist, level ? `Level ${level.level}` : "", bpm ? `~${bpm} BPM` : ""].filter(Boolean).join(" · ");
    const fav = store.favourites().includes(song.id);
    return `<header class="topbar">
      <a class="icon-btn" href="#/" aria-label="Back to songs">${ICON.back}</a>
      <div class="top-title"><h1>${esc(song.title)}</h1><p>${esc(sub)}</p></div>
      <button type="button" class="icon-btn fav" data-act="fav" data-id="${esc(song.id)}" aria-pressed="${fav}" aria-label="Favourite">${ICON.star}</button>
    </header>
    <div class="song-grid">
      <div class="col-video">
        <div class="player-frame"><div id="yt-player"></div></div>
        <div id="player-status" class="player-status" role="status" aria-live="polite"></div>
        <button type="button" id="bar-line" class="bar-line" data-act="breakdown" aria-expanded="false" aria-controls="breakdown">
          ${capo ? `<span class="badge capo" id="capo-badge">Capo ${capo}</span>` : `<span id="bar-dot" class="bar-dot"></span>`}
          <span id="bar-text" class="bar-text"></span><span id="bar-action" class="bar-action">Breakdown ›</span>
        </button>
      </div>
      <div class="col-cues">
        <section id="after-panel" class="panel after-panel" aria-label="Song finished" hidden></section>
        <section id="breakdown" class="breakdown" aria-label="Song breakdown" hidden></section>
        <section id="cue-panel" class="cue-panel" aria-label="Chord cues">
          <div id="cue-live" class="cue-live">
            <div class="cue-row">
              <div class="cue cue-now"><div class="cue-cap">NOW <span id="now-quick" class="tag quick" hidden>quick</span><span id="cue-note" class="tag note" hidden></span></div>
                <div id="now-chord" class="cue-chord len-s">—</div><div id="now-sub" class="cue-sub"></div></div>
              <div id="next-col" class="cue cue-next"><div class="cue-cap">NEXT <span id="next-quick" class="tag quick" hidden>quick</span></div>
                <div id="next-chord" class="cue-chord len-s">—</div><div id="next-sub" class="cue-sub"></div></div>
            </div>
            <div id="chord-strip" class="chord-strip" aria-hidden="true"></div>
            <div id="strip-strum" class="strip-strum" hidden></div>
            <div class="cue-foot"><span id="cue-count" class="cue-count"></span><span id="cue-hint" class="cue-hint"></span></div>
          </div>
          <div id="cue-cover" class="cue-cover" hidden></div>
          <div id="count-big" class="count-big" role="status" aria-live="assertive" hidden></div>
        </section>
      </div>
      <div class="col-controls">
        <section class="controls" aria-label="Playback controls">
          <div id="progress-row" class="progress-row" hidden><span id="time-now">0:00</span><span class="progress"><span id="progress-fill" class="progress-fill"></span></span><span id="time-end"></span></div>
          <div class="transport">
            <span id="speed-seg" class="speed-seg" role="group" aria-label="Playback speed" hidden></span>
            <span class="transport-gap"></span>
            <button type="button" id="btn-restart" class="round" data-act="restart" disabled aria-label="Restart from the beginning">${ICON.restart}</button>
            <button type="button" id="btn-back" class="round" data-act="back5" disabled aria-label="Back 5 seconds">${ICON.rewind}</button>
            <button type="button" id="btn-play" class="round play" data-act="play" disabled aria-label="Play">${ICON.play}</button>
          </div>
        </section>
        <details class="panel options" id="options"><summary>Options: sync, view, count-in, all speeds</summary>
          <div class="row">
            <label id="speed-wrap" class="speed" hidden>Speed <select id="sel-speed" aria-label="Playback speed"></select></label>
            <button type="button" id="btn-hide" class="btn" data-act="hide" aria-pressed="false">Hide cues</button>
            ${CountIn ? `<button type="button" id="btn-countin" class="btn" data-act="countin" aria-pressed="false">Count-in off</button>` : ""}
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
          </div>
        </details>
        <details class="panel details" id="details"><summary>Details</summary><div id="details-body"></div></details>
      </div>
    </div>`;
  }

  const mainShapes = song => {
    const shapes = song.difficulty && song.difficulty.main_shapes;
    return Array.isArray(shapes) ? shapes.filter(x => typeof x === "string" && x) : [];
  };

  // ---------------------------------------------------------------- the line under the video and the breakdown
  // One relevant line, setup merged into playing: tapping it opens the breakdown, which never opens by itself.
  function loadKnownShapes() {
    const page = S;
    getCatalogue().then(catalogue => {
      if (S !== page) return;
      page.known = Library.knownShapes(listedSongs(catalogue), store.plays());
      renderBarLine();
      if (page.breakdownOpen) renderBreakdown();
    }).catch(() => {});
  }
  function shapeInfo() { return Library.shapeLine(mainShapes(S.song), S.known); }
  const patternName = pattern => String(pattern.name || "").split(":").slice(1).join(":").trim();

  function renderBarLine() {
    const text = $("bar-text");
    if (!text) return;
    const info = shapeInfo();
    const pattern = S.patterns.find(p => p.id === S.patternId);
    const style = !info.fresh.length && pattern ? patternName(pattern) : "";
    text.textContent = style ? `${info.text} · ${style}` : info.text;
    const dot = $("bar-dot");
    if (dot) dot.classList.toggle("fresh", info.fresh.length > 0);
    $("bar-action").textContent = S.breakdownOpen ? "Hide" : "Breakdown ›";
    $("bar-line").setAttribute("aria-expanded", String(S.breakdownOpen));
  }

  // Looking at the breakdown pauses the song; closing it carries on if it was playing.
  function setBreakdown(open) {
    if (!S || S.breakdownOpen === open) return;
    S.breakdownOpen = open;
    if (open) {
      S.resumeAfterBreakdown = S.session.playing || Boolean(S.count);
      cancelCountIn();
      if (S.session.playing) S.session.pause();
      renderBreakdown();
    }
    setHidden($("breakdown"), !open);
    setHidden($("cue-panel"), open);
    renderBarLine();
    if (!open && S.resumeAfterBreakdown) { S.resumeAfterBreakdown = false; S.session.play(); }
  }

  function renderBreakdown() {
    const box = $("breakdown");
    if (!box) return;
    const song = S.song, capo = num(song.capo) && song.capo > 0 ? song.capo : 0;
    const note = String(song.setup_note || "");
    const tuning = /^[^.(]*tuning/i.exec(note);
    const rest = note.includes(".") ? note.slice(note.indexOf(".") + 1).trim() : "";
    const meter = song.rhythm && song.rhythm.meter_label;
    const facts = [capo ? `Capo ${capo}` : "No capo", tuning && tuning[0].trim(), meter, "Provisional chart"].filter(Boolean);
    const info = shapeInfo();
    const shapes = mainShapes(song);
    const loop = Library.commonLoop(S.timeline);
    const loopNote = !loop ? "" : loop.coverage >= 0.5 ? "This loop repeats through most of the song."
      : `The most repeated run of chords: it comes round ${loop.repeats} times.`;
    const pattern = S.patterns.find(p => p.id === S.patternId);
    box.innerHTML = `<div class="facts">${facts.map(f => `<span class="fact">${esc(f)}</span>`).join("")}</div>
      ${rest ? `<p class="hint">${esc(rest)}</p>` : ""}
      ${shapes.length ? `<section><h2 class="bd-title">Shapes</h2><div class="shape-grid">${shapes.map(l => shapeCard(l, info.fresh.includes(l))).join("")}</div></section>` : ""}
      ${loop ? `<section><h2 class="bd-title">How it goes</h2><div class="chord-strip">${loop.chords.map((c, i) =>
        `<span class="strip-cell${i ? "" : " now"}" style="flex-grow:${Math.max(1, Math.round(c.seconds))}">${esc(Core.displayLabel(c.label))}</span>`).join("")}</div><p class="hint">${esc(loopNote)}</p></section>` : ""}
      ${S.patterns.length ? `<section><h2 class="bd-title">Strum pattern</h2><div class="pattern-list">${S.patterns.map(p =>
        `<button type="button" class="pattern" data-act="pattern" data-p="${esc(p.id)}" aria-pressed="${p.id === S.patternId}"><span>${esc(p.name || "")}</span><span class="pattern-strokes">${esc(p.strokes.join(" "))}</span></button>`).join("")}</div>
        <p class="hint">${esc((pattern && pattern.description) || "")} A practice suggestion, not the recorded part.</p></section>` : ""}
      <button type="button" class="btn-primary" data-act="breakdown">Back to playing</button>`;
  }

  function levelOf(song) {
    const d = song && song.difficulty;
    const level = d && Number.isInteger(d.level) ? d.level : Number.isInteger(song && song.level) ? song.level : null;
    return level >= 1 && level <= 5 ? { level, label: d && typeof d.label === "string" ? d.label : "" } : null;
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
      isMuted: () => yt.isMuted(),
      mute: () => yt.mute(),
      unMute: () => yt.unMute(),
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
            renderSpeedSeg();
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
    renderSpeedSeg(rates);
    if (rates.length <= 1) { wrap.hidden = true; return; }
    sel.innerHTML = rates.map(r => `<option value="${r}">${r === 1 ? "1× (normal)" : `${r}×`}</option>`).join("");
    sel.value = String(S.rate);
    wrap.hidden = false;
  }

  // The two speeds worth a tap while playing; Options keeps every speed YouTube offers.
  const QUICK_RATES = [0.75, 1];
  function renderSpeedSeg(rates) {
    const seg = $("speed-seg");
    if (!seg) return;
    if (rates) {
      const usable = QUICK_RATES.every(r => rates.includes(r));
      seg.innerHTML = usable ? QUICK_RATES.map(r => `<button type="button" data-act="speed" data-r="${r}" aria-label="Playback speed ${r}×">${r}×</button>`).join("") : "";
      seg.hidden = !usable;
    }
    for (const b of seg.querySelectorAll("button")) b.setAttribute("aria-pressed", String(Number(b.dataset.r) === S.rate));
  }

  function onState(code) {
    S.session.stateChange(code);
    // Pausing or ending the video after the count started it cancels the count.
    if (S.count && (code === 0 || (code === 2 && S.count.sawPlaying))) cancelCountIn();
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
    if (S.session.playing || S.count) { cancelCountIn(); if (S.session.playing) S.session.pause(); return; }
    if (S.breakdownOpen) { S.resumeAfterBreakdown = false; setBreakdown(false); }
    // Never start audio with the official player off screen (the lower Play button can be reached
    // after scrolling): bring the player, and the "Tap ▶ in the video" hint under it, into view first.
    const f = document.querySelector(".player-frame");
    if (f) {
      const r = f.getBoundingClientRect();
      if (r.top < 0 || r.bottom > window.innerHeight) f.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    const counting = settings().countIn && CountIn ? startCountIn() : null;
    if (!counting && !S.session.play()) return;
    requestWakeLock();
    if (!counting || counting.playCalled) armPlayHint(); // a pre-roll arms it when it starts the video
  }
  function armPlayHint() {
    const page = S;
    window.clearTimeout(S.playTimer);
    S.playTimer = window.setTimeout(() => {
      if (S === page && !S.session.playing && !S.failed) setMsg("autoplay", "Tap ▶ in the video to start.");
    }, 2500);
  }

  function seekTo(seconds) {
    if (!S) return;
    cancelCountIn();
    if (!S.session.seek(seconds)) return;
    frame();
  }

  // Restart while playing (or counting) with count-in on counts in again from the top; otherwise it just seeks.
  function restart() {
    if (!S) return;
    const rolling = S.session.playing || Boolean(S.count);
    if (!(rolling && settings().countIn && CountIn && S.session.controllable)) { seekTo(0); return; }
    cancelCountIn();
    S.session.pause();
    S.session.seek(0);
    if (!startCountIn()) { S.session.play(); return; }
    requestWakeLock();
  }

  // ---------------------------------------------------------------- count-in (#60)
  // One bar of numbered clicks at the song's tempo that leads into a bar start, then clicks fading out over
  // the first bar of the music. Mid-song the video starts a bar early and the count follows its clock (run-up).
  // When the count would start before the video's 0 (most songs, from the start), it runs on its own clock
  // (pre-roll), starts the video during the count and follows the video's clock once it plays. A video that
  // hasn't played yet on this page is first warmed up: played muted until it really plays, then paused back
  // at the start, so the count's start isn't lost to YouTube's loading delay (founder feedback, 27 October).
  // lib/count-in.js plans the beats; this part owns the clock, the clicks and the big numbers.
  const COUNT_LOOKAHEAD_S = 0.15, COUNT_LATE_S = 0.06, WARM_UP_MAX_MS = 8000;
  let audio = null;
  let startDelay = 0.08; // a warmed-up video's start delay in seconds, learned from each pre-roll on this page
  function unlockAudio() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      if (!audio) audio = new Ctx();
      if (audio.state === "suspended") audio.resume();
      // iOS unlocks Web Audio only for a sound started inside the tap.
      const src = audio.createBufferSource();
      src.buffer = audio.createBuffer(1, 1, 22050);
      src.connect(audio.destination);
      src.start(0);
    } catch (_) { audio = null; }
  }
  function scheduleClick(c, when, accent, gain) {
    if (!audio) return;
    try {
      const osc = audio.createOscillator(), env = audio.createGain();
      osc.frequency.value = accent ? 1600 : 1000;
      env.gain.setValueAtTime(0.0001, when);
      env.gain.exponentialRampToValueAtTime(0.6 * gain, when + 0.003);
      env.gain.exponentialRampToValueAtTime(0.0001, when + 0.07);
      osc.connect(env);
      env.connect(audio.destination);
      osc.start(when);
      osc.stop(when + 0.09);
      c.nodes.push(osc);
    } catch (_) { /* no click; the numbers still show */ }
  }
  function showCount(n) {
    const el = $("count-big");
    if (!el) return;
    el.textContent = n ? String(n) : "";
    el.hidden = !n;
  }
  function startCountIn() {
    const { t, pt } = S.session.tick();
    const plan = CountIn.plan(S.song, t);
    if (!plan) return null;
    cancelCountIn();
    unlockAudio();
    const shift = t - pt; // chart time minus player time (video offset, sync nudge, audio delay)
    const c = { plan, shift, rate: S.rate || 1, next: 0, raf: 0, timers: [], nodes: [], t0: performance.now(),
      preroll: plan.startAt - shift < 0, playCalled: false, sawPlaying: false, warming: false, wasMuted: false };
    S.count = c;
    if (c.preroll) {
      if (pt > 0.05) S.session.seek(0);
      if (!S.played || S.state === -1 || S.state === 5) {
        // Warm up inside the tap (which also lets iOS start the video later), muted.
        c.warming = true;
        c.wasMuted = S.session.muted();
        S.session.setMuted(true);
        if (!S.session.play()) { S.session.setMuted(c.wasMuted); S.count = null; return null; }
        c.playCalled = true; // armPlayHint covers a blocked start
      }
    } else {
      if (!S.session.seek(plan.startAt - shift) || !S.session.play()) { S.count = null; return null; }
      c.playCalled = true;
    }
    updateTransport();
    frame();
    c.raf = window.requestAnimationFrame(countLoop);
    return c;
  }
  // Chart time for the count: the video's clock once it plays; before that, a pre-roll's own clock.
  function countClock(c) {
    if (S.state === 1 && c.playCalled && !c.warming) {
      const { t } = S.session.tick();
      if (c.preroll && !c.sawPlaying) {
        // Learn how late the video really started, for the next pre-roll on this page.
        const own = c.plan.startAt + (performance.now() - c.t0) / 1000 * c.rate;
        startDelay = Math.max(0, Math.min(1.5, startDelay + 0.7 * (own - t) / c.rate));
      }
      c.sawPlaying = true;
      return t;
    }
    if (c.preroll && !c.sawPlaying) return c.plan.startAt + (performance.now() - c.t0) / 1000 * c.rate;
    return null; // a run-up waiting for the video to start
  }
  function countLoop() {
    const c = S && S.count;
    if (!c) return;
    c.raf = 0;
    if (c.warming) {
      const waited = performance.now() - c.t0;
      if (S.state === 1 || waited > WARM_UP_MAX_MS) {
        if (S.state !== 1) { cancelCountIn(); return; } // never started: the "Tap ▶ in the video" hint stays
        // Warm: back to the start, sound back on, and start the count on its own clock from now.
        S.session.pause();
        S.session.seek(0);
        S.session.setMuted(c.wasMuted);
        Object.assign(c, { warming: false, playCalled: false, t0: performance.now() });
        window.clearTimeout(S.playTimer);
        updateTransport();
        frame();
      }
      c.raf = window.requestAnimationFrame(countLoop);
      return;
    }
    const t = countClock(c);
    if (t !== null) {
      if (c.preroll && !c.playCalled && t >= c.shift - startDelay * c.rate) {
        c.playCalled = true;
        if (!S.session.play()) { cancelCountIn(); return; }
        armPlayHint();
      }
      const r = CountIn.due(c.plan.clicks, c.next, t, COUNT_LOOKAHEAD_S, COUNT_LATE_S);
      c.next = r.next;
      for (const { click, delay } of r.fire) {
        const wait = delay / c.rate;
        if (audio) scheduleClick(c, audio.currentTime + wait, click.n === 1, click.gain);
        c.timers.push(window.setTimeout(() => showCount(click.n), wait * 1000));
      }
      if (r.done) {
        c.timers.push(window.setTimeout(() => { if (S && S.count === c) { S.count = null; showCount(0); updateTransport(); } }, 400));
        return;
      }
    }
    c.raf = window.requestAnimationFrame(countLoop);
  }
  function cancelCountIn(page) {
    const p = page || S;
    const c = p && p.count;
    if (!c) return;
    p.count = null;
    if (c.raf) window.cancelAnimationFrame(c.raf);
    for (const id of c.timers) window.clearTimeout(id);
    for (const osc of c.nodes) { try { osc.stop(0); } catch (_) { /* already stopped */ } }
    if (c.warming) { p.session.pause(); p.session.setMuted(c.wasMuted); }
    if (p === S) { showCount(0); updateTransport(); frame(); }
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
    cancelCountIn();
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
    renderChordStrip(cue);
    renderStrumStep(t);
    renderProgress();
  }

  function cueMode() {
    if (S.failed) return "failed";
    if (S.cuesHidden) return "hidden";
    if (S.ad) return "ad";
    return "live";
  }
  function stateNote() {
    if (!S.video) return "";
    if (S.count && S.count.warming) return "Getting the video ready…";
    if (S.count && S.state !== 1) return "Count-in";
    if (S.state === 3) return "Buffering…";
    if (S.state === 2) return "Paused";
    if (S.state === 0) return "Ended";
    if (S.state === -1 || S.state === 5) return !S.ready ? "Waiting · loading" : S.played ? "Tap ▶ to start" : ""; // before the first play, the line under the cues says it
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
      $("now-sub").textContent = holdText(now, cue.beatsPerBar);
    }
    const nextText = next ? next.display : now && now.kind === "end" ? "" : "End";
    const nextKey = `${partKey(next)}:${nextText}`;
    if (S.memo.next !== nextKey) {
      S.memo.next = nextKey;
      setChord($("next-chord"), nextText, Boolean(next && next.kind === "chord"));
      setHidden($("next-quick"), !(next && next.quick));
    }
    const nextSub = changeText(cue);
    if (S.memo.nextSub !== nextSub) { S.memo.nextSub = nextSub; $("next-sub").textContent = nextSub; }
    const count = countText(cue);
    if (S.memo.count !== count) { S.memo.count = count; $("cue-count").textContent = count; }
    const hints = ["provisional chart"];
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
    box.innerHTML = `<h2 class="after-title">Nice one</h2>
      <p class="hint">${esc(page.song.title)} · played ${count === 1 ? "once" : `${count} times`} on this phone</p>
      <div class="row"><button type="button" class="btn btn-play" data-act="again">Again</button>
        <button type="button" class="btn" data-act="fav" data-id="${esc(page.song.id)}" aria-pressed="${store.favourites().includes(page.song.id)}">${favouriteLabel(page.song.id)}</button>
        <button type="button" class="btn" data-act="surprise">Surprise me</button></div>
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
    return "";
  }

  // Under NOW: how long this chord lasts, in whole bars when it fills them.
  function holdText(part, beatsPerBar) {
    if (!part || part.idx < 0) return "";
    if (num(part.beats) && part.beats > 0) return part.beats % beatsPerBar === 0 ? plural(part.beats / beatsPerBar, "bar") : plural(part.beats, "beat");
    return num(part.seconds) ? `${(part.seconds / S.rate).toFixed(1)} s` : "";
  }
  // Under NEXT: how soon it comes.
  function changeText(cue) {
    if (cue.beatsUntilChange !== null) return `in ${plural(cue.beatsUntilChange, "beat")}`;
    // Media seconds / playback rate = wall-clock seconds the player will take.
    if (cue.secondsUntilChange !== null) return `in ${(cue.secondsUntilChange / S.rate).toFixed(1)} s`;
    return "";
  }

  function setChord(el, text, isChord) {
    el.textContent = text;
    el.className = `cue-chord ${isChord ? sizeClass(text) : "word"}`;
  }

  // The chords coming up, each as wide as it lasts. Redrawn only when the chord changes.
  const STRIP_CHORDS = 6;
  function renderChordStrip(cue) {
    const box = $("chord-strip");
    if (!box) return;
    const from = cue.now && cue.now.idx >= 0 ? cue.now.idx : cue.next ? cue.next.idx : -1;
    const started = Boolean(cue.now && cue.now.idx >= 0);
    const key = `${from}:${started}`;
    if (S.memo.strip === key) return;
    S.memo.strip = key;
    box.innerHTML = from < 0 ? "" : S.timeline.slice(from, from + STRIP_CHORDS).map((e, i) =>
      `<span class="strip-cell${i === 0 && started ? " now" : ""}" style="flex-grow:${Math.max(1, Math.round(e.e - e.s))}">${e.label === "N" ? "–" : esc(Core.displayLabel(e.label))}</span>`).join("");
  }

  function renderProgress() {
    const total = Core.expectedDuration(S.song, S.video);
    const row = $("progress-row");
    if (!row || !total || S.ad) return;
    const shown = Math.max(0, Math.min(total, Math.floor(S.pt)));
    if (S.memo.progress === shown) return;
    S.memo.progress = shown;
    row.hidden = false;
    $("time-now").textContent = Core.formatTime(shown);
    $("time-end").textContent = Core.formatTime(total);
    $("progress-fill").style.width = `${(shown / total * 100).toFixed(1)}%`;
  }

  function chordListHTML() {
    const items = S.timeline.filter(e => e.label !== "N").map(e => `<li><time>${Core.formatTime(e.s)}</time> <b>${esc(Core.displayLabel(e.label))}</b></li>`);
    const video = analysedVideo();
    const link = video ? `<a class="btn" href="${esc(watchUrl(video.video_id, 0))}" target="_blank" rel="noopener">Open on YouTube</a>` : "";
    return `<p class="cover-title">${esc(S.failed ? failText(S.failed) : "Cues unavailable")}</p>${link ? `<p>${link}</p>` : ""}
      <p class="muted">Chord list, not synced. Times are for the analysed recording.</p>
      <ol class="chord-list">${items.join("")}</ol>`;
  }

  // ---------------------------------------------------------------- strum
  // One line of strokes under the cues (the live step lights up); the pattern choice lives in the breakdown.
  function renderStrumPanel() {
    const row = $("strip-strum");
    if (!row) return;
    const pattern = S.patterns.find(p => p.id === S.patternId);
    if (!pattern) { row.hidden = true; row.innerHTML = ""; S.strumCells = []; return; }
    row.hidden = false;
    const counts = Array.isArray(pattern.counts) ? pattern.counts : [];
    const count = i => counts[i] !== undefined ? counts[i] : i + 1;
    const label = pattern.strokes.map((s, i) => `${count(i)} ${s === "D" ? "down" : s === "U" ? "up" : "skip"}`).join(", ");
    row.setAttribute("role", "img");
    row.setAttribute("aria-label", `Suggested practice pattern, not the recorded part: ${label}`);
    row.innerHTML = pattern.strokes.map((stroke, i) => `<span class="stroke${stroke === "D" || stroke === "U" ? "" : " rest"}" data-i="${i}" aria-hidden="true"><small>${esc(count(i))}</small>${stroke === "D" || stroke === "U" ? Core.strokeGlyph(stroke) : "·"}</span>`).join("");
    S.strumCells = Array.from(row.querySelectorAll(".stroke"));
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

  // ---------------------------------------------------------------- shape diagrams
  function shapeCard(label, isNew) {
    const lib = window.StrumShapes;
    let shape = null, svg = "";
    try { shape = lib && typeof lib.getShape === "function" ? lib.getShape(label) : null; } catch (_) { shape = null; }
    if (shape && typeof lib.renderShapeSVG === "function") {
      try { svg = String(lib.renderShapeSVG(shape, { size: 96 }) || ""); } catch (_) { svg = ""; }
    }
    return `<figure class="diagram${isNew ? " fresh" : ""}"><figcaption class="d-name">${esc(label)}${isNew ? " · new" : ""}</figcaption>
      ${svg ? `<div class="d-svg">${svg}</div>` : `<p class="muted d-missing">No diagram</p>`}
      ${shape && shape.note ? `<p class="d-note">${esc(shape.note)}</p>` : ""}</figure>`;
  }

  // ---------------------------------------------------------------- controls and details
  function updateTransport() {
    if (!S) return;
    const enabled = S.session.controllable;
    for (const id of ["btn-play", "btn-back", "btn-restart"]) { const b = $(id); if (b) b.disabled = !enabled; }
    const playing = S.state === 1 || S.state === 3 || Boolean(S.count);
    const play = $("btn-play");
    if (play && play.getAttribute("aria-label") !== (playing ? "Pause" : "Play")) {
      play.innerHTML = playing ? ICON.pause : ICON.play;
      play.setAttribute("aria-label", playing ? "Pause" : "Play");
    }
    const hide = $("btn-hide");
    if (hide) { hide.textContent = S.cuesHidden ? "Show cues" : "Hide cues"; hide.setAttribute("aria-pressed", String(S.cuesHidden)); }
  }

  function renderViewControls() {
    const { quality, view, countIn } = settings();
    const ci = $("btn-countin");
    if (ci) { ci.setAttribute("aria-pressed", String(countIn)); ci.textContent = countIn ? "Count-in on" : "Count-in off"; }
    for (const b of app.querySelectorAll('[data-act="quality"]')) b.setAttribute("aria-pressed", String(b.dataset.v === quality));
    for (const b of app.querySelectorAll('[data-act="view"]')) b.setAttribute("aria-pressed", String(b.dataset.v === view));
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
    if (act === "genre") {
      libGenre = target.dataset.genre;
      target.parentNode.querySelectorAll("[data-act=genre]").forEach(b => b.setAttribute("aria-pressed", String(b === target)));
      getCatalogue().then(catalogue => { if (!S && $("lib-search")) renderLibrary(catalogue); }).catch(() => {});
      return;
    }
    if (act === "fav") {
      const on = store.toggleFavourite(target.dataset.id);
      for (const b of app.querySelectorAll("[data-act=fav]")) {
        b.setAttribute("aria-pressed", String(on));
        if (!b.classList.contains("icon-btn")) b.textContent = favouriteLabel(target.dataset.id);
      }
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
      case "back5": seekTo(S.pt - 5); break;
      case "speed": S.session.setRate(Number(target.dataset.r)); break;
      case "breakdown": setBreakdown(!S.breakdownOpen); break;
      case "restart": restart(); break;
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
        S.session.setQuality(target.dataset.v); renderViewControls(); if (S.breakdownOpen) renderBreakdown(); frame(); break;
      case "view":
        S.session.setView(target.dataset.v); renderViewControls(); if (S.breakdownOpen) renderBreakdown(); frame(); break;
      case "countin":
        store.setCountIn(!settings().countIn); renderViewControls(); break;
      case "pattern":
        if (S.session.setPattern(target.dataset.p)) { renderStrumPanel(); renderBarLine(); renderBreakdown(); frame(); }
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
    else if (event.key === "ArrowLeft" || event.key === "j") { event.preventDefault(); seekTo(S.pt - 5); }
    else if (event.key === "h") { S.cuesHidden = !S.cuesHidden; updateTransport(); frame(); }
  });

  document.addEventListener("visibilitychange", () => {
    if (!S) return;
    if (document.visibilityState === "hidden") {
      // No background play: pause when the page is hidden.
      cancelCountIn();
      if (S.session.playing) S.session.pause();
      saveLast();
    } else if (S.state === 1) requestWakeLock();
  });
  window.addEventListener("pagehide", () => saveLast());
  window.addEventListener("hashchange", route);
  route();
})();
