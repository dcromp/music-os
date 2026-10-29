/*
 * Strum Along chord shapes: a curated grip table, a movable-barre generator and an SVG renderer.
 *
 * UMD: window.StrumShapes in the browser, module.exports under node. ES2020. Needs lib/chords.js
 * (window.StrumChords), which reads the labels (Chords.normalize); load it first.
 *
 *   getShape(label)  -> { name, frets[6], fingers[6], baseFret, barre, note, source } | null
 *   renderShapeSVG(shape, { size, title, fingers, className }) -> SVG markup string
 *
 * Conventions
 *   - frets and fingers run low E (index 0) to high e (index 5). Fret -1 is a muted string,
 *     0 is open. Frets are absolute (a barre at the 3rd fret reads 3, not 0).
 *   - fingers: 1 index .. 4 little finger, 0 for muted or open strings.
 *   - barre: { fret, from, to } with from/to as string indices (0 = low E), or null.
 *     frets[from] and frets[to] always equal barre.fret.
 *   - baseFret: the fret shown at the top of the diagram. It is 1 whenever an open string is
 *     played (the diagram then has a nut); otherwise it is the lowest fretted fret.
 *   - Everything is provisional guidance for practice: chord charts here are automatic drafts and
 *     these are common textbook grips, not the voicing on any recording.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./chords.js"));
  else root.StrumShapes = factory(root.StrumChords);
})(typeof self !== "undefined" ? self : this, function (Chords) {
  "use strict";

  const OPEN_STRING_PC = [4, 9, 2, 7, 11, 4]; // standard tuning EADGBE
  const parseChord = Chords.normalize;

  // ---------------------------------------------------------------- curated grip table

  // [chord, frets (x = muted), fingers, barre {fret, from, to} | null]. Standard open-position
  // grips, a few explicit slash-bass grips, and the usual small barres. Frets low E -> high e.
  const GRIPS = [
    // A
    ["A", "x02220", "001230"], ["Am", "x02210", "002310"], ["A7", "x02020", "002030"],
    ["Am7", "x02010", "002010"], ["Asus2", "x02200", "001200"], ["Asus4", "x02230", "001230"],
    ["A7sus4", "x02030", "002030"], ["Amaj7", "x02120", "002130"], ["Aadd9", "x02420", "001420"],
    ["A6", "x02222", "001111", { fret: 2, from: 2, to: 5 }], ["Am6", "x02212", "002314"],
    ["Adim", "x0121x", "001320"], ["Aaug", "x03221", "004231"], ["A5", "x022xx", "001200"],
    ["A/E", "002220", "001230"], ["A/C#", "x42220", "041230"], ["A/G", "302220", "401230"],
    ["Am/E", "002210", "002310"], ["Am/G", "302210", "402310"],
    // B (open-position ones; every other B shape is a barre from the generator)
    ["B7", "x21202", "021304"], ["Bm7", "x20202", "010203"],
    // C
    ["C", "x32010", "032010"], ["Cadd9", "x32030", "032040"], ["Cmaj7", "x32000", "032000"],
    ["C7", "x32310", "032410"], ["Csus2", "x30033", "010023"],
    ["Csus4", "x33011", "034011", { fret: 1, from: 4, to: 5 }], ["C6", "x32210", "043210"],
    ["C/G", "332010", "432010"], ["C/E", "032010", "032010"], ["C/B", "x22010", "023010"],
    // D
    ["D", "xx0232", "000132"], ["Dm", "xx0231", "000231"], ["D7", "xx0212", "000213"],
    ["Dm7", "xx0211", "000211", { fret: 1, from: 4, to: 5 }],
    ["Dmaj7", "xx0222", "000111", { fret: 2, from: 3, to: 5 }], ["Dsus2", "xx0230", "000130"],
    ["Dsus4", "xx0233", "000123"], ["D7sus4", "xx0213", "000213"], ["D6", "xx0202", "000102"],
    ["D5", "xx023x", "000120"], ["Ddim", "xx0131", "000131", { fret: 1, from: 3, to: 5 }],
    ["D/F#", "2x0232", "100243"], ["D/A", "x00232", "000132"], ["D/C", "x30232", "040132"],
    // A Horse with No Name's second chord: F# bass, D A B E above (two fingers)
    ["D6add9/F#", "200200", "100200"],
    ["Dm/A", "x00231", "000231"],
    // E
    ["E", "022100", "023100"], ["Em", "022000", "023000"], ["E7", "020100", "020100"],
    ["Em7", "020000", "020000"], ["Esus4", "022200", "023400"], ["Emaj7", "021100", "031200"],
    ["E5", "022xxx", "012000"], ["E6", "022120", "034120"], ["Eadd9", "022102", "023104"],
    ["E9", "020102", "020103"], ["Eaug", "032110", "043120"],
    ["Edim", "0120xx", "012000"], ["E/G#", "422100", "423100"], ["E/B", "x22100", "023100"], ["Em/B", "x22000", "023000"],
    // F
    ["Fmaj7", "xx3210", "003210"], ["Fadd9", "xx3213", "003214"],
    ["F/A", "x03211", "003211", { fret: 1, from: 4, to: 5 }],
    ["F/C", "x33211", "034211", { fret: 1, from: 4, to: 5 }],
    // G
    ["G", "320033", "210034"], ["G7", "320001", "320001"], ["Gmaj7", "320002", "310002"],
    ["Gsus4", "330013", "230014"], ["Gsus2", "300033", "200034"], ["G6", "320000", "210000"],
    ["G/B", "x20003", "020003"], ["G/D", "xx0003", "000003"], ["G/F#", "220003", "120003"]
  ];

  function parseFretString(str) {
    return str.split("").map(ch => (ch === "x" ? -1 : Number(ch)));
  }

  /** Lowest-position rule: open strings mean a nut diagram, otherwise start at the lowest fretted fret. */
  function baseFretFor(frets) {
    const fretted = frets.filter(f => f > 0);
    if (!fretted.length) return 1;
    return frets.some(f => f === 0) ? 1 : Math.min(...fretted);
  }

  const GRIP_TABLE = new Map(); // "pc|quality|bassPc-or-empty" -> grip
  for (const [chord, fretStr, fingerStr, barre] of GRIPS) {
    const p = parseChord(chord);
    if (!p) throw new Error("Bad grip label " + chord);
    GRIP_TABLE.set(`${p.rootPc}|${p.quality}|${p.bassPc === null ? "" : p.bassPc}`, {
      frets: parseFretString(fretStr),
      fingers: fingerStr.split("").map(Number),
      barre: barre ? { fret: barre.fret, from: barre.from, to: barre.to } : null
    });
  }

  // ---------------------------------------------------------------- movable-barre generator

  // Templates are written relative to the "shape fret" b: a digit d means fret b+d, n means b-1,
  // x means muted. barre.rel is the offset of the barre inside the template. E shapes keep the
  // root on the low E string, A shapes keep it on the A string.
  const tpl = (rel, fingers, barre) => ({
    rel: rel.split("").map(ch => (ch === "x" ? null : ch === "n" ? -1 : Number(ch))),
    fingers: fingers.split("").map(Number),
    barre: barre || null
  });
  const B05 = { rel: 0, from: 0, to: 5 }, B04 = { rel: 0, from: 0, to: 4 }, B03 = { rel: 0, from: 0, to: 3 };
  const B15 = { rel: 0, from: 1, to: 5 }, B13 = { rel: 0, from: 1, to: 3 };

  const TEMPLATES = {
    "": { E: tpl("022100", "134211", B05), A: tpl("x02220", "013331", B15) },
    m: { E: tpl("022000", "134111", B05), A: tpl("x02210", "013421", B15) },
    "7": { E: tpl("020100", "131211", B05), A: tpl("x02020", "013141", B15) },
    m7: { E: tpl("020000", "131111", B05), A: tpl("x02010", "013121", B15) },
    maj7: { E: tpl("021100", "142311", B05), A: tpl("x02120", "013241", B15) },
    sus2: { E: tpl("024400", "124411", B05), A: tpl("x02200", "013411", B15) },
    sus4: { E: tpl("022200", "123411", B05), A: tpl("x02230", "012341", B15) },
    "7sus4": { E: tpl("020200", "131411", B05), A: tpl("x02030", "013141", B15) },
    add9: { E: tpl("024100", "134211", B05), A: tpl("x02420", "012431", B15) },
    "6": { E: tpl("0x2120", "103241", B05), A: tpl("x02222", "013333", { rel: 2, from: 2, to: 5 }) },
    m6: { E: tpl("0x2020", "103141", B05), A: tpl("x02x12", "013024") },
    dim: { E: tpl("0120xx", "123100", B03), A: tpl("x0121x", "012320", { rel: 1, from: 2, to: 4 }) },
    aug: { E: tpl("032110", "143221", B05), A: tpl("x03221", "014332", { rel: 2, from: 3, to: 4 }) },
    "9": { E: tpl("020102", "131214", B04), A: tpl("x0n000", "021344") },
    "5": { E: tpl("022xxx", "134000"), A: tpl("x022xx", "013400") },
    dim7: { E: tpl("01202x", "123140", B03), A: tpl("x01x12", "012023", { rel: 1, from: 2, to: 4 }) },
    m7b5: { E: tpl("0100xx", "121100", B03), A: tpl("x0101x", "012130", B13) }
  };
  const SHAPE_ROOT_PC = { E: 4, A: 9 };

  function realise(template, b) {
    const frets = template.rel.map(r => (r === null ? -1 : b + r));
    const fingers = template.fingers.map((f, i) => (frets[i] > 0 ? f : 0));
    const barre = template.barre ? { fret: b + template.barre.rel, from: template.barre.from, to: template.barre.to } : null;
    return { frets, fingers, barre };
  }

  /** Movable shape for any root and canonical quality: E or A shape, whichever sits lower (<= fret 10). */
  function generate(rootPc, quality) {
    const tpls = TEMPLATES[quality];
    if (!tpls) return null;
    let best = null;
    for (const kind of ["E", "A"]) {
      if (!tpls[kind]) continue;
      // 1..12: the open position (0) belongs to the grip table, so a generated shape starts at fret 1 or later.
      const b = ((rootPc - SHAPE_ROOT_PC[kind] - 1 + 12) % 12) + 1;
      if (!best || b < best.b) best = { kind, b };
    }
    if (!best) return null;
    const out = realise(tpls[best.kind], best.b);
    out.generated = true;
    out.power = quality === "5";
    return out;
  }

  // ---------------------------------------------------------------- public: getShape

  function finish(name, grip, note, source) {
    return {
      name,
      frets: grip.frets.slice(),
      fingers: grip.fingers.slice(),
      baseFret: baseFretFor(grip.frets),
      barre: grip.barre ? { fret: grip.barre.fret, from: grip.barre.from, to: grip.barre.to } : null,
      note,
      source
    };
  }

  function rootGrip(p) {
    const tabled = GRIP_TABLE.get(`${p.rootPc}|${p.quality}|`);
    if (tabled) return { grip: tabled, source: "table" };
    const generated = generate(p.rootPc, p.quality);
    return generated ? { grip: generated, source: "generated" } : null;
  }

  function noteFor(p, found, slashFallback) {
    const parts = [];
    if (slashFallback) parts.push("bass note omitted");
    else if (found.source === "generated") {
      parts.push(found.grip.power ? "power chord" : found.grip.barre ? "barre shape" : "movable shape");
    } else if (p.quality === "5") parts.push("power chord");
    else if (found.grip.barre) parts.push("barre shape");
    if (p.simplified) parts.push("simplified from " + p.input.trim());
    return parts.join("; ");
  }

  /**
   * Chord grip for a label such as "G", "F#m7", "Bb", "C/E", "E5", "A:min7". Returns null for N, X
   * and labels without a recognisable root (the UI then shows the chord name only).
   */
  function getShape(label) {
    const p = parseChord(label);
    if (!p) return null;
    if (p.bassPc !== null) {
      const explicit = GRIP_TABLE.get(`${p.rootPc}|${p.quality}|${p.bassPc}`);
      if (explicit) return finish(p.name, explicit, noteFor(p, { grip: explicit, source: "table" }, false), "table");
    }
    const found = rootGrip(p);
    if (!found) return null;
    return finish(p.name, found.grip, noteFor(p, found, p.bassPc !== null), found.source);
  }

  // ---------------------------------------------------------------- public: renderShapeSVG

  const esc = text => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const num = n => String(Math.round(n * 100) / 100);

  function ariaLabelFor(shape) {
    const frets = shape.frets.map(f => (f < 0 ? "x" : String(f))).join(" ");
    let label = `${shape.name || "Chord"} chord: ${frets}`;
    if (shape.barre) label += `, barre at fret ${shape.barre.fret}`;
    return label;
  }

  /**
   * Compact chord box as an SVG string: 6 strings, 5 frets, muted/open markers, dots with optional
   * finger numbers, a rounded barre bar, and a thick nut (base fret 1) or "Nfr" label. Strokes and
   * fills use currentColor; finger numbers use var(--diagram-bg, #fff) so they follow the theme.
   * Options: size (CSS width in px, default 96), title (true for the chord name, or a string),
   * fingers (false hides finger numbers), className.
   */
  function renderShapeSVG(shape, opts) {
    if (!shape || !Array.isArray(shape.frets) || shape.frets.length !== 6) return "";
    const options = opts || {};
    const size = Number(options.size) > 0 ? Number(options.size) : 96;
    const showFingers = options.fingers !== false;
    const title = options.title === true ? (shape.name || "") : typeof options.title === "string" ? options.title : "";
    const baseFret = Number.isInteger(shape.baseFret) && shape.baseFret >= 1 ? shape.baseFret : 1;

    const W = 100, left = 27, right = 89, gap = (right - left) / 5;
    const fretH = 15, rows = 5, radius = 5;
    const titleH = title ? 15 : 0;
    const top = titleH + 17;
    const bottom = top + fretH * rows;
    const H = bottom + 6;
    const sx = i => left + i * gap;
    const rowY = row => top + (row - 0.5) * fretH;
    const rowOf = fret => fret - baseFret + 1;
    const fingerAt = i => (shape.fingers && shape.fingers[i]) || 0;
    const parts = [];

    if (title) parts.push(`<text x="${W / 2}" y="11.5" text-anchor="middle" font-size="12" font-weight="700" fill="currentColor">${esc(title)}</text>`);

    // Fret lines then strings.
    for (let i = 1; i <= rows; i++) parts.push(`<line x1="${left}" y1="${num(top + i * fretH)}" x2="${right}" y2="${num(top + i * fretH)}" stroke="currentColor" stroke-width="1"/>`);
    if (baseFret === 1) parts.push(`<rect x="${left - 1}" y="${top - 2.4}" width="${right - left + 2}" height="4.8" rx="1" fill="currentColor"/>`);
    else {
      parts.push(`<line x1="${left}" y1="${top}" x2="${right}" y2="${top}" stroke="currentColor" stroke-width="1"/>`);
      parts.push(`<text x="${left - 8}" y="${num(top + fretH / 2 + 3.4)}" text-anchor="end" font-size="9.5" font-weight="600" fill="currentColor">${baseFret}fr</text>`);
    }
    for (let i = 0; i < 6; i++) parts.push(`<line x1="${num(sx(i))}" y1="${top}" x2="${num(sx(i))}" y2="${bottom}" stroke="currentColor" stroke-width="1.1"/>`);

    // Muted and open markers above the nut.
    const markerY = top - 9;
    for (let i = 0; i < 6; i++) {
      const fret = shape.frets[i], x = sx(i);
      if (fret < 0) parts.push(`<path d="M${num(x - 3)} ${num(markerY - 3)}L${num(x + 3)} ${num(markerY + 3)}M${num(x + 3)} ${num(markerY - 3)}L${num(x - 3)} ${num(markerY + 3)}" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/>`);
      else if (fret === 0) parts.push(`<circle cx="${num(x)}" cy="${num(markerY)}" r="3.2" stroke="currentColor" stroke-width="1.3" fill="none"/>`);
    }

    const label = (x, y, finger) => finger > 0 && showFingers
      ? `<text x="${num(x)}" y="${num(y + 3)}" text-anchor="middle" font-size="8" font-weight="700" style="fill:var(--diagram-bg,#fff)">${finger}</text>` : "";

    // Barre bar first so that dots and finger numbers sit on top of it.
    const barre = shape.barre;
    let barreRow = 0;
    if (barre && Number.isInteger(barre.fret)) {
      barreRow = rowOf(barre.fret);
      if (barreRow >= 1 && barreRow <= rows) {
        const cy = rowY(barreRow), x1 = sx(barre.from) - radius, x2 = sx(barre.to) + radius;
        parts.push(`<rect x="${num(x1)}" y="${num(cy - radius)}" width="${num(x2 - x1)}" height="${num(radius * 2)}" rx="${radius}" fill="currentColor"/>`);
        parts.push(label(sx(barre.from), cy, fingerAt(barre.from)));
      }
    }

    for (let i = 0; i < 6; i++) {
      const fret = shape.frets[i];
      if (!(fret > 0)) continue;
      if (barre && i >= barre.from && i <= barre.to && fret === barre.fret) continue; // covered by the bar
      const row = rowOf(fret);
      if (row < 1 || row > rows) continue;
      const cx = sx(i), cy = rowY(row);
      parts.push(`<circle cx="${num(cx)}" cy="${num(cy)}" r="${radius}" fill="currentColor"/>`);
      parts.push(label(cx, cy, fingerAt(i)));
    }

    const attrs = [
      `xmlns="http://www.w3.org/2000/svg"`,
      `viewBox="0 0 ${W} ${num(H)}"`,
      `width="${num(size)}"`,
      `height="${num((size * H) / W)}"`,
      `role="img"`,
      `aria-label="${esc(ariaLabelFor(shape))}"`,
      `focusable="false"`,
      `font-family="-apple-system, system-ui, Helvetica, Arial, sans-serif"`
    ];
    if (options.className) attrs.push(`class="${esc(options.className)}"`);
    return `<svg ${attrs.join(" ")}>${parts.filter(Boolean).join("")}</svg>`;
  }

  /** Chord labels that have an explicit table grip (before the generator), for tests and tooling. */
  function listGripLabels() { return GRIPS.map(g => g[0]); }

  return { getShape, renderShapeSVG, listGripLabels, OPEN_STRING_PC };
});
