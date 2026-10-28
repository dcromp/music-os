/* PROTOTYPE, throwaway (branch prototype/strumalong-merged-song). Not for deployment.
 * Question: what should one screen look like that merges the get-ready sheet (#/ready/<id>) into the
 * song page (#/song/<id>)? Three variants on the existing song route, switched with ?variant=A|B|C
 * (localhost only). With a variant set, #/ready/<id> opens the song page.
 *   A  Ready card in the cue panel: the video loads above; until the first Play the cue panel shows
 *      "You'll need" diagrams instead of NOW/NEXT, then turns into the live cues.
 *   B  Ready sheet, then the player: the page opens as the get-ready sheet with the video under it;
 *      Play folds the sheet away and the page becomes the player.
 *   C  Video-first strip: the video, then a compact strip of chord chips (tap for a diagram) and a
 *      one-line strum, then the cues. Chips light up with the chord being played; options fold away.
 * Switch with the floating bar or the [ and ] keys (the arrow keys already seek in the player). */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  const local = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  const VARIANTS = { A: "Ready card in the cue panel", B: "Ready sheet, then the player", C: "Video-first chord strip" };
  const variant = String(params.get("variant") || "").toUpperCase();
  if (!local || !VARIANTS[variant]) return;

  const esc = v => String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = id => document.getElementById(id);
  let started = false, song = null, lastState = "—", chipTimer = 0;

  function diagram(label, size) {
    let svg = "";
    try { const lib = window.StrumShapes, shape = lib && lib.getShape(label); svg = shape ? String(lib.renderShapeSVG(shape, { size }) || "") : ""; } catch (_) { svg = ""; }
    return `<figure class="diagram"><figcaption><span class="d-name">${esc(label)}</span></figcaption>${svg ? `<div class="d-svg">${svg}</div>` : `<p class="muted d-missing">No diagram</p>`}</figure>`;
  }
  function facts(s) {
    const d = s.difficulty || {};
    const capo = Number(s.capo) > 0 ? Number(s.capo) : 0;
    const bpm = s.rhythm && Number.isFinite(s.rhythm.bpm) ? Math.round(s.rhythm.bpm) : null;
    const pattern = s.strumming && Array.isArray(s.strumming.patterns) ? s.strumming.patterns.find(p => p && Array.isArray(p.strokes) && p.strokes.length) : null;
    return { capo, bpm, pattern, shapes: Array.isArray(d.main_shapes) ? d.main_shapes : [], meta: [capo ? `Capo ${capo}` : "No capo", bpm ? `~${bpm} BPM` : ""].filter(Boolean).join(" · ") };
  }
  function strokeGrid(pattern) {
    const counts = Array.isArray(pattern.counts) ? pattern.counts : [];
    return `<div class="stroke-grid" style="grid-template-columns:repeat(${pattern.strokes.length},1fr)">
      ${pattern.strokes.map(x => `<span class="stroke${x === "D" || x === "U" ? "" : " rest"}">${x === "D" || x === "U" ? esc(x) : "·"}</span>`).join("")}
      ${pattern.strokes.map((_, i) => `<span class="stroke-count">${esc(counts[i] || "")}</span>`).join("")}</div>`;
  }
  const isFav = id => { try { return (JSON.parse(localStorage.getItem("music-os-strumalong-v1:favourites")) || []).includes(id); } catch (_) { return false; } };
  const favButton = id => `<button type="button" class="btn" data-act="fav" data-id="${esc(id)}" aria-pressed="${isFav(id)}">${isFav(id) ? "★ Favourite" : "☆ Favourite"}</button>`;

  function setStarted(on) {
    if (started === on) return;
    started = on;
    document.body.classList.toggle("mp-pre", !on);
    if (on && variant === "B") window.scrollTo({ top: 0, behavior: "smooth" });
    bar();
  }

  // ------------------------------------------------------------------ variants
  function mountA(f) {
    const panel = $("cue-panel");
    panel.insertAdjacentHTML("afterbegin", `<div class="mp-ready">
      <p class="mp-meta">${esc(f.meta)}</p>
      ${song.setup_note ? `<p class="hint">${esc(song.setup_note)}</p>` : ""}
      ${f.shapes.length ? `<h2 class="panel-title">You'll need</h2><div class="diagrams mp-grid">${f.shapes.map(l => diagram(l, 64)).join("")}</div>` : ""}
      <p class="row">${favButton(song.id)}</p></div>`);
  }

  function mountB(f) {
    document.querySelector(".song-grid").insertAdjacentHTML("afterbegin", `<div class="mp-sheet">
      <p class="mp-meta">${esc(f.meta)}</p>
      ${song.setup_note ? `<p class="hint">${esc(song.setup_note)}</p>` : ""}
      ${f.shapes.length ? `<section class="panel"><h2 class="panel-title">You'll need</h2><div class="diagrams ready-diagrams">${f.shapes.map(l => diagram(l, 84)).join("")}</div></section>` : ""}
      ${f.pattern ? `<section class="panel"><h2 class="panel-title">Strum</h2>${strokeGrid(f.pattern)}<p class="hint">${esc(f.pattern.name || "")}. A practice suggestion, not the recorded part.</p></section>` : ""}
      <button type="button" class="btn btn-play ready-play mp-sheet-play" data-act="play">▶ Play</button>
      <p class="row">${favButton(song.id)}</p>
      <p class="hint mp-under">The video is just below; it loads while you get ready.</p></div>`);
  }

  function mountC(f) {
    const video = document.querySelector(".col-video");
    const strokes = f.pattern ? f.pattern.strokes.map(x => x === "D" ? "↓" : x === "U" ? "↑" : "·").join(" ") : "";
    video.insertAdjacentHTML("beforeend", `<div class="mp-strip">
      <div class="mp-strip-row"><span class="mp-label">${esc(f.capo ? `Capo ${f.capo}` : "Chords")}</span>
        <span class="mp-chips">${f.shapes.map(l => `<button type="button" class="chip mp-chip" data-mp-chip="${esc(l)}">${esc(l)}</button>`).join("")}</span>
        ${favButton(song.id).replace('class="btn"', 'class="btn small mp-fav"').replace(/(★|☆) Favourite/, "$1")}</div>
      <div id="mp-pop" class="mp-pop" hidden></div>
      ${strokes ? `<div class="mp-strip-row"><span class="mp-label">Strum</span><span class="mp-strum">${strokes}</span>${f.bpm ? `<span class="mp-bpm">~${f.bpm} BPM</span>` : ""}</div>` : ""}</div>`);
    // Options fold away under the cues.
    const controls = document.querySelector(".col-controls");
    const details = document.createElement("details");
    details.className = "panel mp-options";
    details.innerHTML = "<summary>⚙ Options: sync, speed, view, count-in</summary>";
    controls.parentNode.insertBefore(details, controls);
    details.appendChild(controls);
    $("strum-panel").classList.add("mp-hide");
    $("diagram-panel").classList.add("mp-hide");
    document.addEventListener("click", e => {
      const chip = e.target.closest("[data-mp-chip]");
      if (!chip) return;
      const pop = $("mp-pop"), label = chip.dataset.mpChip;
      const same = !pop.hidden && pop.dataset.label === label;
      pop.hidden = same;
      pop.dataset.label = label;
      if (!same) pop.innerHTML = diagram(label, 110);
    });
    // Light the chip of the chord being played (read off the NOW cue).
    window.clearInterval(chipTimer);
    chipTimer = window.setInterval(() => {
      const now = $("now-chord"), next = $("next-chord");
      document.querySelectorAll(".mp-chip").forEach(c => {
        c.classList.toggle("mp-now", started && now && c.dataset.mpChip === now.textContent.trim());
        c.classList.toggle("mp-next", started && next && c.dataset.mpChip === next.textContent.trim());
      });
    }, 150);
  }

  // ------------------------------------------------------------------ hooks from app.js
  window.MergeProto = {
    mount(s) {
      song = s;
      started = false;
      lastState = "not started";
      document.body.className = `mp-on mp-v${variant} mp-pre`;
      const f = facts(s);
      ({ A: mountA, B: mountB, C: mountC })[variant](f);
      bar();
    },
    state(code) {
      lastState = { "-1": "unstarted", 0: "ended", 1: "playing", 2: "paused", 3: "buffering", 5: "cued" }[code] || String(code);
      if (code === 1 || code === 3) setStarted(true);
      bar();
    },
  };
  // A Play tap starts the merged screen at once, so the count-in plays over the live cues.
  document.addEventListener("click", e => { if (song && e.target.closest('[data-act="play"],[data-act="again"]')) setStarted(true); }, true);
  window.addEventListener("hashchange", () => { song = null; window.clearInterval(chipTimer); document.body.className = "mp-on"; bar(); });

  // ------------------------------------------------------------------ floating switcher
  const keys = Object.keys(VARIANTS);
  function go(step) {
    const next = keys[(keys.indexOf(variant) + step + keys.length) % keys.length];
    const p = new URLSearchParams(location.search);
    p.set("variant", next);
    location.search = p.toString(); // keeps the hash, reloads into the new variant
  }
  function bar() {
    let el = $("mp-bar");
    if (!el) {
      el = document.createElement("div");
      el.id = "mp-bar";
      el.innerHTML = `<button type="button" data-mp="-1" aria-label="Previous variant">‹</button><span id="mp-label"></span><button type="button" data-mp="1" aria-label="Next variant">›</button>`;
      el.addEventListener("click", e => { const b = e.target.closest("[data-mp]"); if (b) go(Number(b.dataset.mp)); });
      document.body.appendChild(el);
    }
    $("mp-label").innerHTML = `<b>${variant}</b> ${esc(VARIANTS[variant])}<small>${song ? `${started ? "started" : "before first Play"} · video ${esc(lastState)}` : "open a song"}</small>`;
  }
  document.addEventListener("keydown", e => {
    if (e.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable)) return;
    if (e.key === "[") go(-1);
    else if (e.key === "]") go(1);
  });
  document.addEventListener("DOMContentLoaded", () => { document.body.classList.add("mp-on"); bar(); });
})();
