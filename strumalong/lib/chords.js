/* Strum Along chord shape vocabulary: the one place that reads and rewrites chord labels.
 * UMD: window.StrumChords in the browser, module.exports under node. No dependencies, ES2020.
 * Load it before lib/core.js and lib/shapes.js, which both use it.
 *
 *   parse(label)                -> { root, rootPc, quality, bass, bassPc } | null
 *   shapeForCapo(sounding, capo) -> the chord shape fretted with that capo ("A", 2 -> "G")
 *   soundingForCapo(shape, capo) -> the sounding chord of a shape with that capo ("G", 2 -> "A"), sharp spelling
 *   coreLabel(label)            -> the label with known extensions removed ("F#m7" -> "F#m"), else unchanged
 *   normalize(label)            -> { name, root, rootPc, quality, bass, bassPc, simplified, input } | null,
 *                                  quality being one of QUALITIES (the diagram vocabulary)
 *   noteName(pc)                -> sharp spelling of a pitch class (0 = C)
 *
 * Chart labels are a root (A-G with an optional # or b), a quality suffix, and an optional
 * bass after "/": a note, or a Harte scale degree such as b7. A leading ":" on the quality
 * (Harte "A:min7") is accepted. N (no chord) and X (unclear) are not chords.
 * The frozen review player (experiments/review/app.js) keeps its own copy of the capo and core
 * rules as evidence; shapeForCapo and coreLabel give the same output. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.StrumChords = api;
})(typeof window !== "undefined" ? window : typeof self !== "undefined" ? self : null, function () {
  "use strict";

  const hasOwn = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const mod12 = value => ((value % 12) + 12) % 12;

  // ---------------------------------------------------------------- pitch classes

  const NATURAL_PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  const DEGREE_PC = { 1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11 };
  const NOTE = /^([A-G])([#b])?$/;
  const DEGREE = /^([b#]?)([1-7])$/;

  function pcOf(letter, accidental) {
    return mod12(NATURAL_PC[letter] + (accidental === "#" ? 1 : accidental === "b" ? -1 : 0));
  }
  function notePc(text) {
    const m = NOTE.exec(text);
    return m ? pcOf(m[1], m[2]) : null;
  }
  function spell(pc, flat) { return (flat ? FLAT_NAMES : SHARP_NAMES)[mod12(pc)]; }
  function noteName(pc) { return Number.isInteger(pc) ? spell(pc, false) : null; }

  // Root, suffix as written, and whatever follows the first "/" (null without a slash).
  const LABEL = /^([A-G][#b]?)([^/]*)(?:\/(.*))?$/;
  function split(label) {
    if (typeof label !== "string") return null;
    const m = LABEL.exec(label);
    return m ? { root: m[1], rootPc: notePc(m[1]), suffix: m[2], bass: m[3] === undefined ? null : m[3] } : null;
  }
  const chartBass = bass => bass === null || NOTE.test(bass) || DEGREE.test(bass);

  /** Spelling-level parse of a chart label. quality is the suffix as written, without a Harte ":".
   *  bassPc is resolved for a scale-degree bass too. null for N, X, junk and an unreadable bass. */
  function parse(label) {
    const p = split(label);
    if (!p || !chartBass(p.bass)) return null;
    let bassPc = null;
    if (p.bass !== null) {
      const degree = DEGREE.exec(p.bass);
      bassPc = degree ? mod12(p.rootPc + DEGREE_PC[degree[2]] + (degree[1] === "#" ? 1 : degree[1] === "b" ? -1 : 0)) : notePc(p.bass);
    }
    return { root: p.root, rootPc: p.rootPc, quality: p.suffix.replace(/^:/, ""), bass: p.bass, bassPc };
  }

  // ---------------------------------------------------------------- capo

  function checkCapo(capo) {
    if (!Number.isInteger(capo) || capo < 0 || capo > 12) throw new Error("Use a capo fret from 0 to 12.");
  }

  /** Chord shape for a sounding chord with a capo on `capo`: the root and a note bass move down.
   *  A flat root keeps flat spelling (Eb/G, capo 1 -> D/Gb). A degree or unreadable bass is kept.
   *  N, X, non-strings and capo 0 return the label unchanged. Throws for a capo outside 0-12. */
  function shapeForCapo(sounding, capo) {
    checkCapo(capo);
    if (typeof sounding !== "string" || !capo || sounding === "N" || sounding === "X") return sounding;
    const p = split(sounding);
    if (!p) return sounding;
    const flatRoot = p.root.includes("b");
    const bass = p.bass === null ? "" : "/" + (NOTE.test(p.bass) ? spell(notePc(p.bass) - capo, flatRoot || p.bass.includes("b")) : p.bass);
    return spell(p.rootPc - capo, flatRoot) + p.suffix + bass;
  }

  /** Sounding chord for a shape fretted with a capo on `capo`: the root and a note bass move up, sharp
   *  spelling (capo 0 respells Bb as A#). A degree or unreadable bass is kept. Throws for a capo outside 0-12. */
  function soundingForCapo(shape, capo) {
    checkCapo(capo);
    const p = split(shape);
    if (!p) return shape;
    const bass = p.bass === null ? "" : "/" + (NOTE.test(p.bass) ? spell(notePc(p.bass) + capo, false) : p.bass);
    return spell(p.rootPc + capo, false) + p.suffix + bass;
  }

  // ---------------------------------------------------------------- core labels

  // Only explicit, known qualities reduce. Suspensions do not contain a major or minor third, so
  // they must not become ordinary major/minor chords.
  const CORE_QUALITY = { m7: "m", min7: "m", minor7: "m", maj7: "", major7: "", add9: "", add2: "", "7": "", "7sus4": "sus4", "7sus": "sus4",
    "maj(9)": "", "maj(add9)": "", "(1,3,5,9)": "", "sus4(b7)": "sus4" };

  /** Core ("Simple") form of a label: m7 -> m, maj7/7/add9 -> major, 7sus4 -> sus4. The bass is kept.
   *  Any other label, including N, X and non-strings, is returned unchanged. */
  function coreLabel(label) {
    const p = split(label);
    if (!p || !chartBass(p.bass)) return label;
    const quality = p.suffix.replace(/^:/, "");
    if (!hasOwn(CORE_QUALITY, quality)) return label;
    return p.root + CORE_QUALITY[quality] + (p.bass === null ? "" : "/" + p.bass);
  }

  // ---------------------------------------------------------------- canonical qualities (diagrams)

  // Canonical qualities the shape engine knows. The empty string is a major triad.
  const QUALITIES = ["", "m", "7", "m7", "maj7", "sus2", "sus4", "7sus4", "add9", "6", "m6", "dim", "aug", "9", "5", "dim7", "m7b5"];

  // Exact spellings (after lower-casing, with parentheses removed) -> canonical quality.
  const EXACT = {
    "": "", maj: "", major: "", m: "m", min: "m", minor: "m", "-": "m",
    "7": "7", dom7: "7", dom: "7",
    m7: "m7", min7: "m7", minor7: "m7", "-7": "m7",
    maj7: "maj7", major7: "maj7", ma7: "maj7",
    sus2: "sus2", "2": "sus2", sus4: "sus4", sus: "sus4", "4": "sus4",
    "7sus4": "7sus4", "7sus": "7sus4", sus4b7: "7sus4", sus7: "7sus4",
    add9: "add9", add2: "add9", majadd9: "add9", "add(9)": "add9",
    "6": "6", maj6: "6", m6: "m6", min6: "m6", "-6": "m6",
    dim: "dim", o: "dim", "\u00b0": "dim", mb5: "dim", minb5: "dim",
    dim7: "dim7", o7: "dim7", "\u00b07": "dim7",
    hdim7: "m7b5", hdim: "m7b5", m7b5: "m7b5", min7b5: "m7b5", "m7-5": "m7b5", "\u00f8": "m7b5", "\u00f87": "m7b5",
    aug: "aug", "+": "aug", aug5: "aug", "#5": "aug", "5#": "aug",
    "9": "9", dom9: "9", "5": "5"
  };

  // Map a quality suffix onto one of QUALITIES: { quality, simplified } or null when not understood.
  // `simplified` is true when an extension had to be dropped (for example m9 -> m7).
  function canonicalQuality(raw) {
    let q = String(raw == null ? "" : raw).replace(/\s+/g, "").replace(/^:/, "");
    // Case-sensitive spellings first: M means major, m means minor.
    if (/^(maj\(9\)|maj\(add9\)|\(1,3,5,9\))$/i.test(q)) return { quality: "add9", simplified: false };
    q = q.replace(/[()]/g, "");
    if (/^(M|Maj|MAJ|major|Major)$/.test(q)) return { quality: "", simplified: false };
    if (/^(M7|M\u03947|\u0394|\u03947|Maj7|MAJ7|Ma7|MA7)$/.test(q)) return { quality: "maj7", simplified: false };
    if (/^(m|min|-)(maj|Maj|M|\u0394)/.test(q)) return { quality: "m", simplified: true }; // minor-major seventh
    const lower = q.toLowerCase();
    if (hasOwn(EXACT, lower)) return { quality: EXACT[lower], simplified: false };
    if (/^(maj|major|ma)(7|9|11|13)/.test(lower)) return { quality: "maj7", simplified: true };
    if (/^(maj|major)/.test(lower)) return { quality: "maj7", simplified: true };
    let m;
    if ((m = /^(?:minor|min|m|-)(.*)$/.exec(lower))) {
      const rest = m[1];
      // Only known minor extensions (madd9, m(add11), m9, m6, msus...); "Amxyz" is not a chord.
      if (rest && !/^(add|sus|maj|[0-9b#(])/.test(rest)) return null;
      if (/^b5/.test(rest)) return { quality: "dim", simplified: true };
      if (/^(7|9|11|13)/.test(rest)) return { quality: "m7", simplified: true };
      if (/^6/.test(rest)) return { quality: "m6", simplified: true };
      return { quality: "m", simplified: true }; // madd9, m(add11), ...
    }
    if (/^7sus/.test(lower) || /^sus4?b7/.test(lower)) return { quality: "7sus4", simplified: true };
    if (/^sus2/.test(lower)) return { quality: "sus2", simplified: true };
    if (/^sus/.test(lower)) return { quality: "sus4", simplified: true };
    if (/^9/.test(lower)) return { quality: "9", simplified: true };
    if (/^(11|13)/.test(lower)) return { quality: "7", simplified: true };
    if (/^7/.test(lower)) return { quality: "7", simplified: true }; // 7b9, 7#9, 7#5, 7b5 ...
    if (/^6/.test(lower)) return { quality: "6", simplified: true }; // 6/9
    if (/^add/.test(lower)) return { quality: "add9", simplified: true };
    // Exact "o" and "o7" are in EXACT; a bare "o" prefix is not ("Foo", "Bob" are not chords).
    if (/^(dim|\u00b0)/.test(lower)) return { quality: "dim", simplified: true };
    if (/^(aug|\+)/.test(lower)) return { quality: "aug", simplified: true };
    return null;
  }

  /**
   * Canonical form for a chord diagram: "F#m7", "Bb", "C/E", "A:min7", "E5", "Cm/D#", "G/b7" (Harte
   * interval bass). Also accepts Unicode sharp/flat signs, surrounding spaces and a quality containing "/" ("C6/9").
   * Returns null for N / X / no-chord markers and for anything without a recognisable root.
   */
  function normalize(label) {
    if (typeof label !== "string") return null;
    const s = label.trim().replace(/\u266f/g, "#").replace(/\u266d/g, "b").replace(/[\u2212\u2013]/g, "-");
    if (!s || /^(N|X|N\.?C\.?|NC|\*)$/i.test(s)) return null;
    const m = /^([A-G])([#b])?(.*)$/.exec(s);
    if (!m) return null;
    const rootText = m[1] + (m[2] || "");
    const rootPc = pcOf(m[1], m[2]);
    let rest = m[3];
    let bassText = null, bassPc = null;
    const slash = /^(.*)\/([A-G][#b]?|[b#]?[1-7])$/.exec(rest);
    if (slash) {
      rest = slash[1];
      const tail = slash[2];
      if (NOTE.test(tail)) { bassText = tail; bassPc = notePc(tail); }
      else {
        const degree = DEGREE.exec(tail);
        bassPc = mod12(rootPc + DEGREE_PC[degree[2]] + (degree[1] === "#" ? 1 : degree[1] === "b" ? -1 : 0));
        bassText = spell(bassPc, m[2] === "b" || (m[1] === "F" && !m[2]));
      }
    }
    const quality = canonicalQuality(rest);
    if (!quality) return null;
    if (bassPc === rootPc) { bassText = null; bassPc = null; } // C/C is just C
    return {
      name: rootText + quality.quality + (bassText ? "/" + bassText : ""),
      root: rootText, rootPc, quality: quality.quality,
      bass: bassText, bassPc, simplified: quality.simplified, input: label
    };
  }

  return { parse, shapeForCapo, soundingForCapo, coreLabel, normalize, noteName, QUALITIES };
});
