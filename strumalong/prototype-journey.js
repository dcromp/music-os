/* PROTOTYPE — throwaway. Question: what should the end-user journey through Strum Along be?
 * Users: learners who take lessons outside the app (Strum Along supports them) and returning
 * players who just want to have fun strumming favourite songs and get their rhythm down.
 * Three structurally different journeys, switchable via ?variant=A|B|C (← / → keys or the bar):
 *   A  Jukebox      — song-first: search/shelves, one tap to a short "ready?" sheet, play, "another like this".
 *   B  My chords    — lesson-support: tick the chords you've been taught; library = playable now / one chord away.
 *   C  Groove ladder — rhythm-first: pick a strum pattern rung, rehearse it on a pulse, then songs that use it.
 * Each walks home → get ready → play → after. "Play" hands off to the real player (index.html#/song/<id>);
 * the prototype never embeds YouTube. Real catalogue + song JSON + chord diagrams; all state in memory. */
(function () {
  "use strict";
  const Shapes = window.StrumShapes;
  const app = document.getElementById("app");
  const bar = document.getElementById("proto-bar");
  const VARIANTS = [["A", "Jukebox"], ["B", "My chords"], ["C", "Groove ladder"]];
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = v => String(v == null ? "" : v).replace(/[&<>"']/g, c => ESC[c]);

  // ------------------------------------------------------------ shared in-memory state (kept across variants)
  const st = {
    variant: "A", screen: "home", songId: null, songs: [], byId: new Map(),
    query: "", favourites: new Set(), played: [],                     // A
    known: new Set(), setupDone: false,                                // B
    grooveId: null, pulse: null, pulseIdx: -1, grooveDone: new Set(), // C
    rating: null,
  };
  const GROOVES = ["steady-down", "down-up", "anchor-1-3", "folk-strum", "ring-3", "syncopated"];
  const TEACHABLE = ["E", "Em", "A", "Am", "D", "Dm", "G", "C", "E7", "A7", "D7", "B7", "F", "Bm", "F#m", "B", "C#m", "Cm", "Bb"];

  const song = () => st.byId.get(st.songId);
  const primaryPattern = s => (s.full.strumming && s.full.strumming.patterns || [])[0];
  const missing = s => (s.core_shapes || []).filter(c => !st.known.has(c));

  // ------------------------------------------------------------ pieces
  function strokesHTML(p, live) {
    if (!p) return "";
    const n = p.strokes.length;
    return `<div class="p-strokes" style="grid-template-columns:repeat(${n},1fr)">${p.strokes.map((x, i) =>
      `<span class="${x === "—" ? "rest" : ""}${i === live ? " live" : ""}">${x === "—" ? "·" : esc(x)}</span>`).join("")}</div>
      <div class="p-strokes counts" style="grid-template-columns:repeat(${n},1fr)">${(p.counts || []).map(c => `<span>${esc(c)}</span>`).join("")}</div>`;
  }
  function diagramsHTML(labels, size) {
    return `<div class="p-diagrams">${labels.map(l => {
      const shape = Shapes && Shapes.getShape(l);
      return `<figure>${shape ? Shapes.renderShapeSVG(shape, { size: size || 84 }) : ""}<figcaption>${esc(l)}</figcaption></figure>`;
    }).join("")}</div>`;
  }
  const chips = (labels, needed) => labels.map(c => `<span class="p-chip${needed && needed.includes(c) ? " need" : ""}">${esc(c)}</span>`).join("");
  const capoLine = s => s.capo > 0 ? `Capo ${s.capo}` : "No capo";
  const backBtn = (to, text) => `<button class="p-back" data-go="${to}">‹ ${text}</button>`;
  const realPlayer = s => `index.html#/song/${encodeURIComponent(s.id)}`;

  function playScreen(s, extra) {
    return `${backBtn("prep", "Get ready")}
      <div class="p-head"><h1>${esc(s.title)}</h1><span class="p-muted">${esc(s.artist)}</span></div>
      <div class="p-fake">
        <p><b>The real player takes over here</b> (YouTube + NOW/NEXT cues + strum panel).</p>
        <p><a class="p-btn primary" href="${realPlayer(s)}" target="_blank" rel="noopener">▶ Open the real player</a></p>
        <p class="p-muted">Prototype stand-in: come back and press "Song finished" to see the after-song step.</p>
        ${extra || ""}
      </div>
      <p><button class="p-btn big" data-go="after">Song finished</button></p>`;
  }

  // ------------------------------------------------------------ Variant A: Jukebox
  const A = {
    home() {
      const q = st.query.trim().toLowerCase();
      const matches = q ? st.songs.filter(s => `${s.title} ${s.artist}`.toLowerCase().includes(q)) : [];
      const favs = st.songs.filter(s => st.favourites.has(s.id));
      const last = st.played.length ? st.byId.get(st.played[st.played.length - 1]) : null;
      const shelf = (title, list, note) => list.length ? `<h2>${esc(title)}</h2>${note ? `<p class="p-muted">${esc(note)}</p>` : ""}
        <div class="p-shelf">${list.map(tile).join("")}</div>` : "";
      const byLevel = l => st.songs.filter(s => s.level === l);
      const easy = st.songs.filter(s => s.full.difficulty && s.full.difficulty.changes_per_min < 10);
      return `<div class="p-head"><h1>Strum Along</h1><button class="p-btn" data-act="shuffle">🎲 Surprise me</button></div>
        <input class="p-search" id="q" type="search" placeholder="Search songs or artists" value="${esc(st.query)}" autocomplete="off">
        ${q ? `<div class="p-panel"><ul class="p-list">${matches.map(row).join("") || `<li class="p-muted">No match.</li>`}</ul></div>` : `
        ${last ? `<div class="p-panel"><button class="p-item" data-song="${esc(last.id)}"><span class="grow">↻ <b>Play again:</b> ${esc(last.title)}</span></button></div>` : ""}
        ${shelf("★ Your favourites", favs)}
        ${shelf("Easy to jump into", easy.slice(0, 12), "Few changes a minute — just strum.")}
        ${shelf("Three-chord classics", byLevel(1))}
        ${shelf("Campfire open chords", byLevel(2).concat(byLevel(3)))}
        ${shelf("Barre-chord songs", byLevel(4).concat(byLevel(5)))}`}`;
      function tile(s) {
        return `<button class="p-tile" data-song="${esc(s.id)}"><span class="t">${esc(s.title)}</span><span class="a">${esc(s.artist)}</span>
          <span>${chips(s.core_shapes || [])}</span></button>`;
      }
      function row(s) {
        return `<li><button class="p-item" data-song="${esc(s.id)}"><span class="grow"><span class="t">${esc(s.title)}</span><br><span class="a">${esc(s.artist)}</span></span>${chips(s.core_shapes || [])}</button></li>`;
      }
    },
    prep(s) {
      const p = primaryPattern(s);
      const fav = st.favourites.has(s.id);
      return `${backBtn("home", "Songs")}
        <div class="p-head"><h1>${esc(s.title)}</h1><button class="p-btn" data-act="fav">${fav ? "★" : "☆"}</button></div>
        <p class="p-sub">${esc(s.artist)} · ${capoLine(s)} · ~${Math.round(s.bpm)} BPM</p>
        <div class="p-panel"><h2>You'll need</h2>${diagramsHTML(s.core_shapes || [], 72)}</div>
        <div class="p-panel"><h2>Strum</h2>${strokesHTML(p)}<p class="p-muted">${esc(p && p.name)} — a practice suggestion; change it any time in the player.</p></div>
        <button class="p-btn big primary" data-go="play">▶ Play</button>`;
    },
    play(s) { return playScreen(s); },
    after(s) {
      const shared = st.songs.filter(o => o.id !== s.id && (o.core_shapes || []).every(c => (s.core_shapes || []).includes(c) || ["A", "D", "E", "G", "C", "Em", "Am"].includes(c)) && o.level <= s.level + 1).slice(0, 6);
      return `<div class="p-head"><h1>Nice one 🎸</h1></div><p class="p-sub">${esc(s.title)} · played ${st.played.filter(x => x === s.id).length}×</p>
        <div class="p-row"><button class="p-btn primary" data-go="play">↻ Again</button><button class="p-btn" data-act="fav">${st.favourites.has(s.id) ? "★ Favourite" : "☆ Add to favourites"}</button><button class="p-btn" data-act="shuffle">🎲 Surprise me</button></div>
        <div class="p-panel"><h2>Another like this</h2><p class="p-muted">Same feel, chords you just used.</p><ul class="p-list">
        ${shared.map(o => `<li><button class="p-item" data-song="${esc(o.id)}"><span class="grow"><span class="t">${esc(o.title)}</span> <span class="a">${esc(o.artist)}</span></span>${chips(o.core_shapes || [])}</button></li>`).join("")}</ul></div>
        <button class="p-btn" data-go="home">All songs</button>`;
    },
  };

  // ------------------------------------------------------------ Variant B: My chords (lesson support)
  const B = {
    home() {
      if (!st.setupDone) return B.setup();
      const now = [], one = [], later = [];
      for (const s of st.songs) { const m = missing(s); (m.length === 0 ? now : m.length === 1 ? one : later).push(s); }
      const unlocks = {};
      for (const s of one) { const c = missing(s)[0]; unlocks[c] = (unlocks[c] || 0) + 1; }
      const top = Object.entries(unlocks).sort((a, b) => b[1] - a[1]).slice(0, 3);
      const row = s => `<li><button class="p-item" data-song="${esc(s.id)}"><span class="grow"><span class="t">${esc(s.title)}</span><br><span class="a">${esc(s.artist)} · Level ${s.level}</span></span>${chips(s.core_shapes || [], missing(s))}</button></li>`;
      const week = st.played.length;
      return `<div class="p-head"><h1>My songs</h1><button class="p-btn" data-act="edit-chords">My chords (${st.known.size})</button></div>
        <p class="p-sub">Songs that fit the chords you've learned in your lessons.</p>
        ${top.length ? `<div class="p-note">Next chord to ask your teacher about: ${top.map(([c, n]) => `<b>${esc(c)}</b> (opens ${n} song${n === 1 ? "" : "s"})`).join(", ")}</div>` : ""}
        <div class="p-panel"><h2>Play now · ${now.length}</h2><ul class="p-list">${now.map(row).join("") || `<li class="p-muted">Tick a few chords to see songs.</li>`}</ul></div>
        <div class="p-panel"><h2>One chord away · ${one.length}</h2><p class="p-muted">Dashed chord = not ticked yet.</p><ul class="p-list">${one.map(row).join("")}</ul></div>
        <details class="p-panel"><summary>Everything else · ${later.length}</summary><ul class="p-list">${later.map(row).join("")}</ul></details>
        <div class="p-panel"><h2>For your next lesson</h2><p class="p-muted">${week ? `This session: ${st.played.map(id => esc(st.byId.get(id).title)).join(", ")}.` : "Songs you play show up here so you can show your teacher."}</p></div>`;
    },
    setup() {
      return `<div class="p-head"><h1>Which chords do you know?</h1></div>
        <p class="p-sub">Tick the shapes you've learned so far — in lessons or on your own. You can change this any time.</p>
        <div class="p-row">${TEACHABLE.map(c => `<button class="p-chip big${st.known.has(c) ? " on" : ""}" data-chord="${esc(c)}">${esc(c)}</button>`).join("")}</div>
        <p class="p-muted" style="margin-top:12px">${st.known.size} ticked · ${st.songs.filter(s => !missing(s).length).length} songs playable</p>
        <button class="p-btn big primary" data-act="setup-done">Show my songs</button>`;
    },
    prep(s) {
      const p = primaryPattern(s), m = missing(s);
      return `${backBtn("home", "My songs")}
        <div class="p-head"><h1>${esc(s.title)}</h1><span class="p-muted">Level ${s.level}</span></div>
        <p class="p-sub">${esc(s.artist)} · ${esc(s.full.learning && s.full.learning.skill_focus)}</p>
        ${m.length ? `<div class="p-note">New for you: <b>${m.map(esc).join(", ")}</b>. Worth checking the shape with your teacher.</div>` : ""}
        <ol class="p-panel" style="padding-left:32px">
          <li><b>Tune up.</b> ${esc(s.full.setup_note)}</li>
          <li><b>${capoLine(s)}.</b></li>
          <li><b>Chords</b>${diagramsHTML(s.core_shapes || [], 72)}</li>
          <li><b>Strum:</b> ${esc(p && p.name)}${strokesHTML(p)}<span class="p-muted">${esc(p && p.description)}</span></li>
          <li><b>Start slow</b> — the player can drop to 0.75× speed.</li>
        </ol>
        <button class="p-btn big primary" data-go="play">▶ Play along</button>`;
    },
    play(s) { return playScreen(s); },
    after(s) {
      const opts = [["lost", "Lost it"], ["mostly", "Mostly kept up"], ["nailed", "Nailed it"]];
      const tip = { lost: "Try 0.75× speed, or just play the first chord of each bar.", mostly: "Again at full speed — aim to keep strumming through the changes.", nailed: "Ready for a song with one new chord?" }[st.rating];
      const next = st.rating === "nailed" ? st.songs.filter(o => missing(o).length === 1).slice(0, 3) : [];
      return `<div class="p-head"><h1>How did it go?</h1></div><p class="p-sub">${esc(s.title)}</p>
        <div class="p-row">${opts.map(([k, l]) => `<button class="p-btn${st.rating === k ? " on" : ""}" data-rate="${k}">${l}</button>`).join("")}</div>
        ${tip ? `<div class="p-panel"><p>${esc(tip)}</p>${next.map(o => `<button class="p-item" data-song="${esc(o.id)}"><span class="grow"><b>${esc(o.title)}</b> — new: ${esc(missing(o)[0])}</span></button>`).join("")}
          <div class="p-row"><button class="p-btn primary" data-go="play">↻ Again</button><button class="p-btn" data-go="home">My songs</button></div></div>` : ""}
        <p class="p-muted">Kept only on this phone, to show your teacher. No scores.</p>`;
    },
  };

  // ------------------------------------------------------------ Variant C: Groove ladder (rhythm-first)
  function grooves() {
    const map = new Map();
    for (const s of st.songs) {
      const p = primaryPattern(s); if (!p) continue;
      if (!map.has(p.id)) map.set(p.id, { pattern: p, songs: [] });
      map.get(p.id).songs.push(s);
    }
    return GROOVES.filter(id => map.has(id)).map(id => map.get(id)).concat([...map.values()].filter(g => !GROOVES.includes(g.pattern.id)));
  }
  function stopPulse() { if (st.pulse) { clearInterval(st.pulse); st.pulse = null; st.pulseIdx = -1; } }
  function startPulse(p, bpm) {
    stopPulse();
    const perBeat = p.strokes.length / 4;
    st.pulse = setInterval(() => { st.pulseIdx = (st.pulseIdx + 1) % p.strokes.length; const el = document.getElementById("groove-strokes"); if (el) el.innerHTML = strokesHTML(p, st.pulseIdx); }, 60000 / bpm / perBeat);
  }
  const C = {
    home() {
      const gs = grooves();
      const firstOpen = gs.findIndex(g => !st.grooveDone.has(g.pattern.id));
      return `<div class="p-head"><h1>Grooves</h1><span class="p-muted">${st.grooveDone.size}/${gs.length} grooves</span></div>
        <p class="p-sub">Get the strumming hand right first. Each groove has songs to practise it on, easiest chords first.</p>
        <ol class="p-ladder">${gs.map((g, i) => `<li class="p-rung${st.grooveDone.has(g.pattern.id) ? " done" : i === firstOpen ? " current" : ""}">
          <button class="p-item" data-groove="${esc(g.pattern.id)}"><span class="grow"><span class="t">${esc(g.pattern.name.replace(/^\w+:\s*/, ""))}</span><br>
          <span class="a">${g.songs.length} songs${st.grooveDone.has(g.pattern.id) ? " · ✓ got it" : ""}</span></span></button>
          ${strokesHTML(g.pattern)}</li>`).join("")}</ol>`;
    },
    groove() {
      const g = grooves().find(x => x.pattern.id === st.grooveId);
      const songs = g.songs.slice().sort((a, b) => a.level - b.level || a.bpm - b.bpm);
      return `${backBtn("home", "Grooves")}
        <div class="p-head"><h1>${esc(g.pattern.name.replace(/^\w+:\s*/, ""))}</h1></div>
        <div class="p-panel"><h2>Rehearse it — no chords, mute the strings</h2>
          <div id="groove-strokes">${strokesHTML(g.pattern, st.pulseIdx)}</div>
          <p class="p-muted">${esc(g.pattern.description)}</p>
          <div class="p-row">${[70, 90, 110].map(b => `<button class="p-btn" data-pulse="${b}">▶ ${b} BPM</button>`).join("")}<button class="p-btn" data-act="pulse-stop">■</button></div></div>
        <div class="p-panel"><h2>Songs with this groove</h2><ul class="p-list">${songs.map(s => `<li><button class="p-item" data-song="${esc(s.id)}"><span class="grow"><span class="t">${esc(s.title)}</span><br><span class="a">${esc(s.artist)} · ~${Math.round(s.bpm)} BPM</span></span>${chips(s.core_shapes || [])}</button></li>`).join("")}</ul></div>
        <button class="p-btn" data-act="groove-done">${st.grooveDone.has(g.pattern.id) ? "✓ Marked as got it" : "I've got this groove"}</button>`;
    },
    prep(s) {
      const p = primaryPattern(s);
      return `${backBtn(st.grooveId ? "groove" : "home", "Groove")}
        <div class="p-head"><h1>${esc(s.title)}</h1><span class="p-muted">~${Math.round(s.bpm)} BPM</span></div>
        <div class="p-panel"><h2>Your strumming hand</h2>${strokesHTML(p)}</div>
        <div class="p-panel"><h2>Your fretting hand</h2><p>${(s.core_shapes || []).map(c => `<span class="p-big-chord" style="font-size:2rem;margin-right:12px">${esc(c)}</span>`).join("")}</p>
          <details><summary class="p-muted">Show shapes</summary>${diagramsHTML(s.core_shapes || [], 64)}</details>
          <p class="p-muted">Tip: if a change is hard, keep strumming open strings through it — never stop the hand.</p></div>
        <button class="p-btn big primary" data-go="play">▶ Strum along</button>`;
    },
    play(s) { return playScreen(s, `<p class="p-muted">Groove view would make the strum panel the hero and shrink chord names.</p>`); },
    after(s) {
      const g = grooves().find(x => x.songs.includes(s));
      const n = g ? g.songs.filter(o => st.played.includes(o.id)).length : 0;
      return `<div class="p-head"><h1>Groove check</h1></div><p class="p-sub">${esc(s.title)} · ${esc(g && g.pattern.name.replace(/^\w+:\s*/, ""))}</p>
        <div class="p-panel"><p>Did your strumming hand keep moving the whole song?</p>
          <div class="p-row"><button class="p-btn" data-go="play">Not yet — again</button><button class="p-btn primary" data-act="groove-done-from-song">Yes, kept going</button></div></div>
        <div class="p-panel"><p>${n} of ${g ? g.songs.length : 0} songs played with this groove.</p>
          <div class="p-row"><button class="p-btn" data-go="groove">More songs with this groove</button><button class="p-btn" data-go="home">Groove ladder</button></div></div>`;
    },
  };

  // ------------------------------------------------------------ render + events
  const V = { A, B, C };
  function render() {
    const v = V[st.variant], s = song();
    if (st.screen !== "groove") stopPulse();
    let html;
    if (st.screen === "groove" && v.groove && st.grooveId) html = v.groove();
    else if (st.screen !== "home" && s && v[st.screen]) html = v[st.screen](s);
    else { st.screen = "home"; html = v.home(); }
    app.innerHTML = html + `<p class="p-assume">PROTOTYPE · assumption: "Play" hands off to the existing player unchanged; this compares only the journey around it. Charts remain provisional automatic drafts; strum patterns are practice suggestions.</p>`;
    renderBar();
    window.scrollTo(0, 0);
  }
  function renderBar() {
    const i = VARIANTS.findIndex(([k]) => k === st.variant);
    bar.innerHTML = `<button data-cycle="-1" aria-label="Previous variant">‹</button>
      <span class="lbl">${VARIANTS[i][0]} (${VARIANTS[i][1]})<small>screen: ${st.screen}${song() && st.screen !== "home" ? ` · ${esc(song().title)}` : ""}</small></span>
      <button data-cycle="1" aria-label="Next variant">›</button>`;
  }
  function setVariant(k) {
    st.variant = k;
    const url = new URL(location.href); url.searchParams.set("variant", k); history.replaceState(null, "", url);
    if (st.screen === "groove" && k !== "C") st.screen = "home";
    render();
  }
  function cycle(d) { const i = VARIANTS.findIndex(([k]) => k === st.variant); setVariant(VARIANTS[(i + d + VARIANTS.length) % VARIANTS.length][0]); }
  function go(screen) {
    if (screen === "after" && st.songId) { st.played.push(st.songId); st.rating = null; }
    st.screen = screen; render();
  }

  document.addEventListener("click", e => {
    const t = e.target.closest("button, [data-song]"); if (!t) return;
    const d = t.dataset;
    if (d.cycle) return cycle(Number(d.cycle));
    if (d.song) { st.songId = d.song; return go("prep"); }
    if (d.go) return go(d.go);
    if (d.chord) { st.known.has(d.chord) ? st.known.delete(d.chord) : st.known.add(d.chord); return render(); }
    if (d.rate) { st.rating = d.rate; return render(); }
    if (d.groove) { st.grooveId = d.groove; return go("groove"); }
    if (d.pulse) { const g = grooves().find(x => x.pattern.id === st.grooveId); return startPulse(g.pattern, Number(d.pulse)); }
    switch (d.act) {
      case "shuffle": { const pool = st.songs.filter(s => s.level <= 3); st.songId = pool[Math.floor(Math.random() * pool.length)].id; return go("prep"); }
      case "fav": st.favourites.has(st.songId) ? st.favourites.delete(st.songId) : st.favourites.add(st.songId); return render();
      case "setup-done": st.setupDone = true; return render();
      case "edit-chords": st.setupDone = false; st.screen = "home"; return render();
      case "pulse-stop": stopPulse(); return render();
      case "groove-done": st.grooveDone.add(st.grooveId); return render();
      case "groove-done-from-song": { const g = grooves().find(x => x.songs.includes(song())); if (g) { st.grooveDone.add(g.pattern.id); st.grooveId = g.pattern.id; } return go("home"); }
    }
  });
  document.addEventListener("input", e => {
    if (e.target.id !== "q") return;
    st.query = e.target.value; const pos = e.target.selectionStart; render();
    const q = document.getElementById("q"); q.focus(); q.setSelectionRange(pos, pos);
  });
  document.addEventListener("keydown", e => {
    if (e.target.closest("input, textarea, [contenteditable]")) return;
    if (e.key === "ArrowLeft") cycle(-1); else if (e.key === "ArrowRight") cycle(1);
  });

  // ------------------------------------------------------------ boot: real catalogue + every song file
  (async function boot() {
    const idx = await (await fetch("songs/index.json")).json();
    const full = await Promise.all(idx.songs.map(s => fetch(`songs/${encodeURIComponent(s.id)}.json`).then(r => r.json())));
    st.songs = idx.songs.map((s, i) => Object.assign({}, s, { full: full[i] }));
    for (const s of st.songs) st.byId.set(s.id, s);
    ["A", "D", "E", "Em", "Am", "G", "C"].forEach(c => st.known.add(c)); // plausible after a few lessons; editable in B
    const v = new URLSearchParams(location.search).get("variant");
    st.variant = VARIANTS.some(([k]) => k === v) ? v : "A";
    render();
  })().catch(err => { app.innerHTML = `<p class="msg error">Prototype failed to load data: ${esc(err.message)}</p>`; });
})();
