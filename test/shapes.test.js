"use strict";
// Tests for strumalong/lib/shapes.js. Run with plain node: node strumalong/test/shapes.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SHAPES_PATH = path.resolve(__dirname, "..", "lib", "shapes.js");
const S = require(SHAPES_PATH);
const { getShape, renderShapeSVG, parseChord, QUALITIES, OPEN_STRING_PC: OPEN } = S;

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed += 1; console.log("ok   " + name); }
  catch (error) { failed += 1; console.log("FAIL " + name + "\n     " + String(error && error.stack || error).split("\n").slice(0, 6).join("\n     ")); }
}

// ---------------------------------------------------------------- shared checkers

// Allowed chord tones (semitones above the root) and the tones that must be present.
const FORMULA = {
  "": { allowed: [0, 4, 7], required: [0, 4] },
  m: { allowed: [0, 3, 7], required: [0, 3] },
  "7": { allowed: [0, 4, 7, 10], required: [0, 4, 10] },
  m7: { allowed: [0, 3, 7, 10], required: [0, 3, 10] },
  maj7: { allowed: [0, 4, 7, 11], required: [0, 4, 11] },
  sus2: { allowed: [0, 2, 7], required: [0, 2] },
  sus4: { allowed: [0, 5, 7], required: [0, 5] },
  "7sus4": { allowed: [0, 5, 7, 10], required: [0, 5, 10] },
  add9: { allowed: [0, 2, 4, 7], required: [0, 2, 4] },
  "6": { allowed: [0, 4, 7, 9], required: [0, 4, 9] },
  m6: { allowed: [0, 3, 7, 9], required: [0, 3, 9] },
  dim: { allowed: [0, 3, 6], required: [0, 3, 6] },
  aug: { allowed: [0, 4, 8], required: [0, 4, 8] },
  "9": { allowed: [0, 2, 4, 7, 10], required: [0, 2, 4, 10] },
  "5": { allowed: [0, 7], required: [0, 7] },
  dim7: { allowed: [0, 3, 6, 9], required: [0, 3, 6, 9] },
  m7b5: { allowed: [0, 3, 6, 10], required: [0, 3, 6, 10] }
};

function assertShapeInvariants(shape, label) {
  const where = `${label} ${JSON.stringify(shape)}`;
  assert.equal(shape.frets.length, 6, "frets length " + where);
  assert.equal(shape.fingers.length, 6, "fingers length " + where);
  for (const f of shape.frets) assert.ok(Number.isInteger(f) && f >= -1 && f <= 15, "fret range " + where);
  const sounding = shape.frets.filter(f => f >= 0).length;
  assert.ok(sounding >= 3, "at least three sounding strings " + where);
  shape.frets.forEach((fret, i) => {
    const finger = shape.fingers[i];
    assert.ok(Number.isInteger(finger) && finger >= 0 && finger <= 4, "finger range " + where);
    if (fret > 0) assert.ok(finger >= 1, `fretted string ${i} needs a finger ${where}`);
    else assert.equal(finger, 0, `open or muted string ${i} has no finger ${where}`);
  });
  // One finger presses one fret only.
  for (let finger = 1; finger <= 4; finger++) {
    const frets = new Set(shape.frets.filter((f, i) => shape.fingers[i] === finger));
    assert.ok(frets.size <= 1, `finger ${finger} on several frets ${where}`);
  }
  const fretted = shape.frets.filter(f => f > 0);
  const open = shape.frets.some(f => f === 0);
  assert.equal(shape.baseFret, fretted.length ? (open ? 1 : Math.min(...fretted)) : 1, "baseFret " + where);
  for (const f of fretted) assert.ok(f - shape.baseFret >= 0 && f - shape.baseFret <= 4, "fits the five-fret window " + where);
  if (shape.barre) {
    const { fret, from, to } = shape.barre;
    assert.ok(Number.isInteger(from) && Number.isInteger(to) && from >= 0 && to <= 5 && from < to, "barre span " + where);
    assert.equal(shape.frets[from], fret, "barre start on the barre fret " + where);
    assert.equal(shape.frets[to], fret, "barre end on the barre fret " + where);
    assert.ok(shape.fingers[from] >= 1 && shape.fingers[from] === shape.fingers[to], "one finger plays the barre " + where);
  }
  assert.equal(typeof shape.note, "string");
  assert.equal(typeof shape.name, "string");
}

// Check the sounding notes of a shape against the chord the label asks for.
function assertSoundsLike(label, shape) {
  const parsed = parseChord(label);
  assert.ok(parsed, "parse " + label);
  const formula = FORMULA[parsed.quality];
  assert.ok(formula, "formula for " + parsed.quality);
  const omitted = /bass note omitted/.test(shape.note);
  const wantBass = parsed.bassPc !== null && !omitted ? parsed.bassPc : parsed.rootPc;
  const pcs = shape.frets.map((f, i) => (f < 0 ? null : (OPEN[i] + f) % 12));
  const sounding = pcs.filter(pc => pc !== null);
  const allowed = new Set(formula.allowed.map(i => (parsed.rootPc + i) % 12));
  // A label that asks for a 6/9 chord (e.g. A Horse with No Name's D6add9/F#) is simplified to "6"; its 9th is still a chord tone.
  if (parsed.quality === "6" && /6(\/9|add9|9)/.test(label)) allowed.add((parsed.rootPc + 2) % 12);
  if (parsed.bassPc !== null && !omitted) allowed.add(parsed.bassPc);
  for (const pc of sounding) assert.ok(allowed.has(pc), `${label}: note ${pc} is not in the chord ${JSON.stringify(shape)}`);
  for (const interval of formula.required) {
    assert.ok(sounding.includes((parsed.rootPc + interval) % 12), `${label}: missing chord tone +${interval} ${JSON.stringify(shape)}`);
  }
  assert.equal(pcs[shape.frets.findIndex(f => f >= 0)], wantBass, `${label}: wrong bass note ${JSON.stringify(shape)}`);
}

const ROOTS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"];

// ---------------------------------------------------------------- module shape

test("loads as UMD in node and in a browser-like global scope", () => {
  assert.equal(typeof getShape, "function");
  assert.equal(typeof renderShapeSVG, "function");
  const source = fs.readFileSync(SHAPES_PATH, "utf8");
  assert.ok(/^[\x00-\x7f]*$/.test(source), "source is ASCII only so it loads correctly whatever charset the host sends");
  const sandbox = {};
  vm.runInNewContext(source, { self: sandbox });
  assert.equal(typeof sandbox.StrumShapes.getShape, "function");
  assert.equal(typeof sandbox.StrumShapes.renderShapeSVG, "function");
  assert.equal(JSON.stringify(sandbox.StrumShapes.getShape("G")), JSON.stringify(getShape("G")));
});

// ---------------------------------------------------------------- parsing

test("N, X and non-chords return null", () => {
  for (const label of ["N", "X", "N.C.", "NC", "", "  ", "foo", "H", "Z7", "h", null, undefined, 42, {}, "/E", "5",
    "Foo", "Bob", "Amxyz", "Cmi"]) {
    assert.equal(getShape(label), null, JSON.stringify(label));
  }
});

test("exact o / o7 mean diminished; known minor extensions still parse", () => {
  // "Fo" is the same exact-"o" spelling as "Co", so it stays Fdim (only a bare "o" prefix, as in "Foo", is rejected).
  assert.equal(getShape("Co").name, "Cdim");
  assert.equal(getShape("Fo").name, "Fdim");
  assert.equal(getShape("Co7").name, "Cdim7");
  assert.equal(getShape("C\u00b0").name, "Cdim");
  for (const [label, name] of [["Amadd9", "Am"], ["Am(add11)", "Am"], ["Am9", "Am7"], ["Am6", "Am6"], ["Amsus4", "Am"], ["Ammaj7", "Am"], ["Amb5", "Adim"]]) {
    assert.equal(getShape(label).name, name, label);
  }
});

test("parses common label spellings to the same chord", () => {
  const equal = (a, b) => {
    const sa = getShape(a), sb = getShape(b);
    assert.ok(sa && sb, `${a} / ${b}`);
    assert.deepEqual(sa.frets, sb.frets, `${a} vs ${b}`);
    assert.equal(sa.name, sb.name, `${a} vs ${b} name`);
  };
  equal("A:maj", "A"); equal("A:min", "Am"); equal("A:7", "A7"); equal("A:min7", "Am7"); equal("A:maj7", "Amaj7");
  equal("A:sus4", "Asus4"); equal("A:sus2", "Asus2");
  equal("Amin", "Am"); equal("Amaj", "A"); equal("AM7", "Amaj7"); equal("Amaj7", "Amaj7"); equal("Amin7", "Am7");
  equal("Asus", "Asus4"); equal("A7sus", "A7sus4"); equal("A:sus4(b7)", "A7sus4");
  equal("A:maj(9)", "Aadd9"); equal("A:hdim7", "Am7b5"); equal("A:dim7", "Adim7"); equal("C♯", "C#"); equal("D♭m", "Dbm");
  equal("A:min/b3", "Am/C");
});

test("parseChord reports root, quality and bass", () => {
  assert.deepEqual(
    (({ root, rootPc, quality, bass, bassPc }) => ({ root, rootPc, quality, bass, bassPc }))(parseChord("F#m7")),
    { root: "F#", rootPc: 6, quality: "m7", bass: null, bassPc: null });
  assert.deepEqual(
    (({ root, rootPc, quality, bass, bassPc }) => ({ root, rootPc, quality, bass, bassPc }))(parseChord("Cm/D#")),
    { root: "C", rootPc: 0, quality: "m", bass: "D#", bassPc: 3 });
  assert.equal(parseChord("Bb").rootPc, 10);
  assert.equal(parseChord("A#").rootPc, 10);
  assert.equal(parseChord("E5").quality, "5");
  assert.equal(parseChord("G/G").bass, null, "G/G is just G");
  assert.equal(parseChord("A:min/b3").bass, "C");
  assert.equal(parseChord("Am9").quality, "m7");
  assert.equal(parseChord("Am9").simplified, true);
  assert.equal(parseChord("C7b9").quality, "7");
  assert.equal(parseChord("Cmaj9").quality, "maj7");
  assert.equal(parseChord("Cmmaj7").quality, "m");
  assert.equal(parseChord("C6/9").quality, "6");
});

test("enharmonic roots give the same grip but keep the spelling the caller used", () => {
  for (const [sharp, flat] of [["A#", "Bb"], ["C#m", "Dbm"], ["D#7", "Eb7"], ["F#m7", "Gbm7"], ["G#sus4", "Absus4"]]) {
    assert.deepEqual(getShape(sharp).frets, getShape(flat).frets, sharp);
    assert.equal(getShape(sharp).name, sharp);
    assert.equal(getShape(flat).name, flat);
  }
});

test("simplified qualities say so in the note", () => {
  const shape = getShape("Am9");
  assert.deepEqual(shape.frets, getShape("Am7").frets);
  assert.match(shape.note, /simplified from Am9/);
  assert.equal(getShape("Am7").note, "");
});

// ---------------------------------------------------------------- curated grips

test("curated open grips are the standard fingerings", () => {
  const frets = label => getShape(label).frets;
  assert.deepEqual(frets("G"), [3, 2, 0, 0, 3, 3]);
  assert.deepEqual(frets("C"), [-1, 3, 2, 0, 1, 0]);
  assert.deepEqual(frets("D"), [-1, -1, 0, 2, 3, 2]);
  assert.deepEqual(frets("A"), [-1, 0, 2, 2, 2, 0]);
  assert.deepEqual(frets("E"), [0, 2, 2, 1, 0, 0]);
  assert.deepEqual(frets("Am"), [-1, 0, 2, 2, 1, 0]);
  assert.deepEqual(frets("Em"), [0, 2, 2, 0, 0, 0]);
  assert.deepEqual(frets("Dm"), [-1, -1, 0, 2, 3, 1]);
  assert.deepEqual(frets("E7"), [0, 2, 0, 1, 0, 0]);
  assert.deepEqual(frets("A7"), [-1, 0, 2, 0, 2, 0]);
  assert.deepEqual(frets("D7"), [-1, -1, 0, 2, 1, 2]);
  assert.deepEqual(frets("G7"), [3, 2, 0, 0, 0, 1]);
  assert.deepEqual(frets("B7"), [-1, 2, 1, 2, 0, 2]);
  assert.deepEqual(frets("Cmaj7"), [-1, 3, 2, 0, 0, 0]);
  assert.deepEqual(frets("Asus4"), [-1, 0, 2, 2, 3, 0]);
  assert.deepEqual(frets("Dsus2"), [-1, -1, 0, 2, 3, 0]);
  assert.equal(getShape("G").baseFret, 1);
  assert.equal(getShape("G").barre, null);
  assert.equal(getShape("G").source, "table");
});

test("every curated grip passes the shape invariants and sounds like its label", () => {
  const labels = S.listGripLabels();
  assert.ok(labels.length >= 70, "table has " + labels.length + " grips");
  const seen = new Set();
  for (const label of labels) {
    assert.ok(!seen.has(label), "duplicate grip " + label);
    seen.add(label);
    const shape = getShape(label);
    assert.ok(shape, label);
    assert.equal(shape.source, "table", label + " is served from the table");
    assert.equal(shape.name, parseChord(label).name);
    assertShapeInvariants(shape, label);
    assertSoundsLike(label, shape);
  }
  // The families named in the brief are all present.
  for (const label of ["A", "Am", "A7", "Am7", "Asus2", "Asus4", "A7sus4", "Amaj7", "B7", "C", "Cadd9", "Cmaj7", "C7", "Csus2", "Csus4",
    "D", "Dm", "D7", "Dm7", "Dmaj7", "Dsus2", "Dsus4", "E", "Em", "E7", "Em7", "Esus4", "Emaj7", "Fmaj7", "G", "G7", "Gmaj7", "Gsus4",
    "G/B", "D/F#", "C/G", "C/E", "E/B", "Em/B", "D/A", "F/C", "A5", "E5", "D5"]) {
    assert.ok(seen.has(label), "missing curated grip " + label);
  }
});

// ---------------------------------------------------------------- generator

test("barre generator reproduces the textbook movable shapes", () => {
  const bb = getShape("Bb");
  assert.deepEqual(bb.frets, [-1, 1, 3, 3, 3, 1]);
  assert.deepEqual(bb.barre, { fret: 1, from: 1, to: 5 });
  assert.equal(bb.baseFret, 1);
  assert.equal(bb.note, "barre shape");
  assert.equal(bb.source, "generated");

  const fsm = getShape("F#m");
  assert.deepEqual(fsm.frets, [2, 4, 4, 2, 2, 2]);
  assert.deepEqual(fsm.barre, { fret: 2, from: 0, to: 5 });
  assert.equal(fsm.baseFret, 2);
  assert.equal(fsm.note, "barre shape");

  const csm = getShape("C#m");
  assert.deepEqual(csm.frets, [-1, 4, 6, 6, 5, 4]);
  assert.deepEqual(csm.barre, { fret: 4, from: 1, to: 5 });
  assert.equal(csm.baseFret, 4);

  assert.deepEqual(getShape("F").frets, [1, 3, 3, 2, 1, 1]);
  assert.deepEqual(getShape("F").barre, { fret: 1, from: 0, to: 5 });
  assert.deepEqual(getShape("Fm").frets, [1, 3, 3, 1, 1, 1]);
  assert.deepEqual(getShape("Bm").frets, [-1, 2, 4, 4, 3, 2]);
  assert.deepEqual(getShape("B").frets, [-1, 2, 4, 4, 4, 2]);
  assert.deepEqual(getShape("Cm").frets, [-1, 3, 5, 5, 4, 3]);
  assert.deepEqual(getShape("Gm").frets, [3, 5, 5, 3, 3, 3]);
  assert.deepEqual(getShape("F#").frets, [2, 4, 4, 3, 2, 2]);
  assert.deepEqual(getShape("F#m7").frets, [2, 4, 2, 2, 2, 2]);
  assert.deepEqual(getShape("F7").frets, [1, 3, 1, 2, 1, 1]);
  assert.deepEqual(getShape("Ab").frets, [4, 6, 6, 5, 4, 4]);
  assert.deepEqual(getShape("Bm7").frets, [-1, 2, 0, 2, 0, 2], "open Bm7 comes from the table");
  assert.deepEqual(getShape("Bbm7").frets, [-1, 1, 3, 1, 2, 1]);
});

test("every root x quality has a playable generated or curated shape that sounds right", () => {
  let table = 0, generated = 0;
  for (const root of ROOTS) {
    for (const quality of QUALITIES) {
      const label = root + quality;
      const shape = getShape(label);
      assert.ok(shape, "no shape for " + label);
      assertShapeInvariants(shape, label);
      assertSoundsLike(label, shape);
      assert.equal(shape.name, label, "name for " + label);
      if (shape.source === "generated") {
        generated += 1;
        assert.ok(shape.note.length > 0, "generated shape explains itself " + label);
        const fretted = shape.frets.filter(f => f > 0);
        assert.ok(Math.min(...fretted) <= 10, `base fret over 10 for ${label} ${JSON.stringify(shape)}`);
        assert.ok(Math.max(...fretted) <= 14, `reaches past fret 14 for ${label}`);
      } else table += 1;
    }
  }
  console.log(`     (${ROOTS.length * QUALITIES.length} combinations: ${table} curated, ${generated} generated)`);
  assert.equal(table + generated, ROOTS.length * QUALITIES.length);
});

test("barre quality labels: movable shapes carry their barre or a movable-shape note", () => {
  for (const label of ["C#m", "Bb", "F#m7", "Abmaj7", "Bsus4", "Ebsus2", "Bb7sus4", "Gbadd9", "B6", "Cm6", "C#dim", "Daug", "Eb9", "F#m7b5", "Bdim7"]) {
    const shape = getShape(label);
    assert.equal(shape.source, "generated", label);
    assert.match(shape.note, /^(barre shape|movable shape)$/, label);
    if (shape.barre) assert.equal(shape.note, "barre shape", label);
  }
});

test("power chords use two or three strings", () => {
  const e5 = getShape("E5"), a5 = getShape("A5"), d5 = getShape("D5"), g5 = getShape("G5"), bb5 = getShape("Bb5"), fs5 = getShape("F#5");
  assert.deepEqual(e5.frets, [0, 2, 2, -1, -1, -1]);
  assert.deepEqual(a5.frets, [-1, 0, 2, 2, -1, -1]);
  assert.deepEqual(d5.frets, [-1, -1, 0, 2, 3, -1]);
  assert.deepEqual(g5.frets, [3, 5, 5, -1, -1, -1]);
  for (const shape of [e5, a5, d5, g5, bb5, fs5]) {
    const strings = shape.frets.filter(f => f >= 0).length;
    assert.ok(strings === 2 || strings === 3, shape.name + " strings " + strings);
    assert.match(shape.note, /power chord/, shape.name);
  }
  assert.equal(g5.baseFret, 3);
  assert.deepEqual(getShape("A:5").frets, a5.frets);
});

// ---------------------------------------------------------------- slash chords

test("explicit slash grips win, other slash chords fall back to the root shape", () => {
  assert.deepEqual(getShape("G/B").frets, [-1, 2, 0, 0, 0, 3]);
  assert.deepEqual(getShape("D/F#").frets, [2, -1, 0, 2, 3, 2]);
  assert.deepEqual(getShape("C/G").frets, [3, 3, 2, 0, 1, 0]);
  assert.deepEqual(getShape("C/E").frets, [0, 3, 2, 0, 1, 0]);
  assert.deepEqual(getShape("E/B").frets, [-1, 2, 2, 1, 0, 0]);
  assert.equal(getShape("G/B").note, "");
  assert.equal(getShape("G/B").name, "G/B");
  for (const label of ["Cm/D#", "A#/D", "A#m/C#", "D#/A#", "F#m/C#", "Am/D", "Bm/F#"]) {
    const shape = getShape(label), rootShape = getShape(parseChord(label).root + parseChord(label).quality);
    assert.ok(shape, label);
    assert.equal(shape.note, "bass note omitted", label);
    assert.deepEqual(shape.frets, rootShape.frets, label);
    assert.deepEqual(shape.barre, rootShape.barre, label);
    assert.equal(shape.name, label);
    assertShapeInvariants(shape, label);
  }
  assert.deepEqual(getShape("G/G").frets, getShape("G").frets);
  assert.equal(getShape("G/G").name, "G");
});

// ---------------------------------------------------------------- renderer

// Tiny XML well-formedness check: tags balance and attributes are quoted, entities are valid.
function assertWellFormedXml(xml) {
  const tagRe = /<(\/?)([A-Za-z][\w:-]*)((?:\s+[\w:-]+="[^"<]*")*)\s*(\/?)>/y;
  const stack = [];
  let pos = 0, root = null, elements = 0;
  while (pos < xml.length) {
    if (xml[pos] === "<") {
      tagRe.lastIndex = pos;
      const m = tagRe.exec(xml);
      assert.ok(m, "malformed tag at " + pos + ": " + xml.slice(pos, pos + 60));
      const [whole, closing, name, , selfClosing] = m;
      if (closing) {
        assert.equal(stack.pop(), name, "unbalanced </" + name + ">");
      } else {
        elements += 1;
        if (!root) root = name;
        else assert.ok(stack.length > 0, "second root element " + name);
        if (!selfClosing) stack.push(name);
      }
      pos += whole.length;
    } else {
      const next = xml.indexOf("<", pos);
      const text = xml.slice(pos, next < 0 ? xml.length : next);
      assert.ok(!/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/.test(text), "bad entity in text " + text);
      assert.ok(!text.includes(">") || /^[^<]*$/.test(text), "stray > in text");
      pos += text.length;
    }
  }
  assert.equal(stack.length, 0, "unclosed tags: " + stack.join(","));
  assert.equal(root, "svg");
  // Attribute values must not contain a raw ampersand.
  for (const attr of xml.matchAll(/="([^"]*)"/g)) assert.ok(!/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/.test(attr[1]), "bad entity in attribute " + attr[1]);
  return elements;
}

const count = (text, needle) => text.split(needle).length - 1;

test("SVG for G is well formed, labelled and themeable", () => {
  const svg = renderShapeSVG(getShape("G"));
  assertWellFormedXml(svg);
  assert.ok(svg.startsWith("<svg "));
  assert.match(svg, /role="img"/);
  assert.match(svg, /aria-label="G chord: 3 2 0 0 3 3"/);
  assert.match(svg, /currentColor/);
  assert.match(svg, /var\(--diagram-bg,#fff\)/);
  assert.match(svg, /viewBox="0 0 100 [\d.]+"/);
  assert.match(svg, /width="96"/, "default width 96");
  assert.equal(count(svg, 'r="5"'), 4, "four dots for the four fretted strings");
  assert.equal(count(svg, 'r="3.2"'), 2, "two open-string circles");
  assert.equal(count(svg, "M"), 0, "no mute crosses on G");
  assert.ok(!/fr<\/text>/.test(svg), "no base fret label at the nut");
  assert.match(svg, /<rect x="26" /, "thick nut");
});

test("SVG shows muted strings, base fret labels and barres", () => {
  const c = renderShapeSVG(getShape("C"));
  assertWellFormedXml(c);
  assert.equal(count(c, "<path "), 1, "one muted string");
  assert.equal(count(c, 'r="3.2"'), 2, "two open strings");
  assert.match(c, /aria-label="C chord: x 3 2 0 1 0"/);

  const fsm = renderShapeSVG(getShape("F#m"));
  assertWellFormedXml(fsm);
  assert.match(fsm, />2fr<\/text>/, "base fret label");
  assert.match(fsm, /aria-label="F#m chord: 2 4 4 2 2 2, barre at fret 2"/);
  assert.ok(!/<rect x="26" /.test(fsm), "no thick nut away from the nut");
  assert.match(fsm, /rx="5"/, "rounded barre bar");

  const csm = renderShapeSVG(getShape("C#m"));
  assert.match(csm, />4fr<\/text>/);

  const f = renderShapeSVG(getShape("F"));
  assertWellFormedXml(f);
  assert.match(f, /<rect x="26" /, "F is barred at the first fret and keeps its nut");
  assert.equal(count(f, 'r="5"'), 3, "three dots beside the barre bar");
});

test("SVG options: size, title, fingers, className and escaping", () => {
  const shape = getShape("Em");
  const big = renderShapeSVG(shape, { size: 150 });
  assert.match(big, /width="150"/);
  const w = Number(/width="([\d.]+)"/.exec(big)[1]), h = Number(/height="([\d.]+)"/.exec(big)[1]);
  const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(big);
  assert.ok(Math.abs(h / w - Number(vb[2]) / Number(vb[1])) < 0.01, "aspect ratio follows the viewBox");
  assert.match(renderShapeSVG(shape, { size: 0 }), /width="96"/, "invalid size falls back to the default");
  assert.match(renderShapeSVG(shape, { size: "abc" }), /width="96"/);

  const plain = renderShapeSVG(shape), titled = renderShapeSVG(shape, { title: true });
  assertWellFormedXml(titled);
  assert.ok(!/>Em<\/text>/.test(plain), "no title by default");
  assert.match(titled, />Em<\/text>/);
  assert.match(renderShapeSVG(shape, { title: "NOW" }), />NOW<\/text>/);
  const hPlain = Number(/height="([\d.]+)"/.exec(plain)[1]), hTitled = Number(/height="([\d.]+)"/.exec(titled)[1]);
  assert.ok(hTitled > hPlain, "title adds height");

  assert.equal(count(plain, "var(--diagram-bg"), 2, "two finger numbers on Em");
  const noFingers = renderShapeSVG(shape, { fingers: false });
  assert.equal(count(noFingers, "var(--diagram-bg"), 0);
  assertWellFormedXml(noFingers);
  assert.match(renderShapeSVG(shape, { className: "diagram now" }), /class="diagram now"/);

  const nasty = renderShapeSVG({ ...shape, name: 'A<&">b' }, { title: true });
  assertWellFormedXml(nasty);
  assert.ok(!nasty.includes('A<&">b'));
  assert.match(nasty, /A&lt;&amp;&quot;&gt;b/);
});

test("renderShapeSVG tolerates bad input", () => {
  assert.equal(renderShapeSVG(null), "");
  assert.equal(renderShapeSVG(undefined), "");
  assert.equal(renderShapeSVG({}), "");
  assert.equal(renderShapeSVG({ frets: [1, 2] }), "");
  const nameless = renderShapeSVG({ frets: [0, 0, 0, 0, 0, 0], fingers: [0, 0, 0, 0, 0, 0], baseFret: 1, barre: null });
  assertWellFormedXml(nameless);
  assert.match(nameless, /aria-label="Chord chord: 0 0 0 0 0 0"|aria-label="Chord: 0 0 0 0 0 0"|aria-label="[^"]*0 0 0 0 0 0"/);
});

test("every root x quality renders to well-formed SVG with the right marker counts", () => {
  for (const root of ROOTS) {
    for (const quality of QUALITIES) {
      const shape = getShape(root + quality);
      const svg = renderShapeSVG(shape, { title: true, size: 120 });
      assertWellFormedXml(svg);
      assert.match(svg, /role="img"/);
      assert.match(svg, /aria-label="[^"]+ chord: /);
      assert.equal(count(svg, "<path "), shape.frets.filter(f => f < 0).length, shape.name + " mutes");
      assert.equal(count(svg, 'r="3.2"'), shape.frets.filter(f => f === 0).length, shape.name + " opens");
      const covered = shape.frets.filter((f, i) => f > 0 && shape.barre && i >= shape.barre.from && i <= shape.barre.to && f === shape.barre.fret).length;
      const dots = shape.frets.filter(f => f > 0).length - covered;
      assert.equal(count(svg, 'r="5"'), dots, shape.name + " dots");
      if (shape.baseFret > 1) assert.ok(svg.includes(`>${shape.baseFret}fr</text>`), shape.name + " base fret label");
    }
  }
});

// ---------------------------------------------------------------- coverage over real charts

const REPO = path.resolve(__dirname, "..", "..");
const APP_JS = path.join(REPO, "experiments", "review", "app.js");
let review = null;
try { if (fs.existsSync(APP_JS)) review = require(APP_JS); } catch (error) { console.log("note: could not load experiments/review/app.js (" + error.message + ")"); }

function labelVariants(label, capos) {
  const out = new Set([label, review.coreChordLabel(label)]);
  for (const capo of capos) {
    const shifted = review.transposePracticeLabel(label, capo);
    out.add(shifted);
    out.add(review.coreChordLabel(shifted));
  }
  return out;
}

function assertCovered(variants, where) {
  let checked = 0;
  for (const label of variants) {
    if (label === "N" || label === "X") { assert.equal(getShape(label), null, label); continue; }
    const shape = getShape(label);
    assert.ok(shape, `${where}: no shape for ${label}`);
    assertShapeInvariants(shape, label);
    assertSoundsLike(label, shape);
    checked += 1;
  }
  return checked;
}

const PACK_CASES = path.join(REPO, "experiments", "generated", "automatic-first-ten-v1", "cases");
if (!review) console.log("skip coverage tests: experiments/review/app.js not available");
else if (!fs.existsSync(PACK_CASES)) console.log("skip pack coverage: experiments/generated/automatic-first-ten-v1 is not present (it is gitignored)");
else {
  test("shapes cover every chord in the first-ten pack, plus core forms and capo shapes (capo 2 and 0-7)", () => {
    const labels = new Set();
    let charts = 0;
    for (const id of fs.readdirSync(PACK_CASES)) {
      const file = path.join(PACK_CASES, id, "primary.json");
      if (!fs.existsSync(file)) continue;
      charts += 1;
      for (const chord of JSON.parse(fs.readFileSync(file, "utf8")).chords) labels.add(chord.label);
    }
    assert.ok(charts >= 1 && labels.size > 5, "found the pack charts");
    const variants = new Set();
    for (const label of labels) for (const v of labelVariants(label, [2])) variants.add(v);
    const checkedCapo2 = assertCovered(variants, "capo 2");
    const all = new Set();
    for (const label of labels) for (const v of labelVariants(label, [0, 1, 2, 3, 4, 5, 6, 7])) all.add(v);
    const checkedAll = assertCovered(all, "capo 0-7");
    console.log(`     (${charts} charts, ${labels.size} raw labels, ${checkedCapo2} capo-2 variants, ${checkedAll} variants over capos 0-7)`);
  });
}

const SONGS_DIR = path.join(REPO, "strumalong", "songs");
if (review && fs.existsSync(SONGS_DIR)) {
  const songFiles = fs.readdirSync(SONGS_DIR).filter(name => name.endsWith(".json") && name !== "index.json");
  if (songFiles.length) {
    test(`shapes cover every chord in ${songFiles.length} exported song files (core and capo shapes)`, () => {
      let labelsSeen = 0, variantsChecked = 0;
      for (const name of songFiles) {
        const song = JSON.parse(fs.readFileSync(path.join(SONGS_DIR, name), "utf8"));
        if (!Array.isArray(song.chords)) continue;
        const capo = Number.isInteger(song.capo) ? song.capo : 0;
        const labels = new Set(song.chords.map(chord => chord.l));
        labelsSeen += labels.size;
        for (const label of labels) variantsChecked += assertCovered(labelVariants(label, [capo]), name);
      }
      console.log(`     (${songFiles.length} songs, ${labelsSeen} song-label pairs, ${variantsChecked} variants)`);
    });
  } else console.log("skip song coverage: strumalong/songs has no song files yet");
}

console.log(`\n${passed} passed, ${failed} failed`);
// Throw rather than process.exit: run.js requires every test file in one process, and an exit here would end
// the run with status 0 even after an earlier file failed.
if (failed) throw new Error(`shapes.test.js: ${failed} failing test(s)`);
