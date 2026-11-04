"use strict";
// Tests for strumalong/lib/chords.js, the chord shape vocabulary. Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Chords = require("../lib/chords.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}

const ROOTS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "Fb", "E#", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B", "Cb", "B#"];
const ROOT_PC = { C: 0, "B#": 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4, "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11 };

// --- parse -----------------------------------------------------------------------------------
test("parse: root, pitch class, quality and bass", () => {
  assert.deepEqual(Chords.parse("F#m7"), { root: "F#", rootPc: 6, quality: "m7", bass: null, bassPc: null });
  assert.deepEqual(Chords.parse("Cm/D#"), { root: "C", rootPc: 0, quality: "m", bass: "D#", bassPc: 3 });
  assert.deepEqual(Chords.parse("A:min7"), { root: "A", rootPc: 9, quality: "min7", bass: null, bassPc: null }, "Harte colon dropped");
  assert.deepEqual(Chords.parse("G/b7"), { root: "G", rootPc: 7, quality: "", bass: "b7", bassPc: 5 }, "degree bass is resolved");
  assert.equal(Chords.parse("Bbmaj7").rootPc, 10);
  for (const root of ROOTS) assert.equal(Chords.parse(root).rootPc, ROOT_PC[root], root);
});
test("parse: N, X, junk and unreadable basses are not chords", () => {
  for (const label of ["N", "X", "", "H", "c", "Hm", "C/xyz", "C/E/G", "C/", " C", null, undefined, 7]) assert.equal(Chords.parse(label), null, String(label));
});

// --- shapeForCapo ----------------------------------------------------------------------------
test("shapeForCapo: the shape moves down by the capo fret", () => {
  assert.equal(Chords.shapeForCapo("A", 2), "G");
  assert.equal(Chords.shapeForCapo("F#m7", 2), "Em7");
  assert.equal(Chords.shapeForCapo("Bb", 1), "A");
  assert.equal(Chords.shapeForCapo("C", 1), "B");
  assert.equal(Chords.shapeForCapo("C", 2), "A#", "a natural root takes sharp spelling");
  assert.equal(Chords.shapeForCapo("Eb", 2), "Db", "a flat root keeps flat spelling");
  assert.equal(Chords.shapeForCapo("A:min7", 2), "G:min7", "the quality is kept as written");
});
test("shapeForCapo: note basses move with the root; others are kept", () => {
  assert.equal(Chords.shapeForCapo("E/G#", 2), "D/F#");
  assert.equal(Chords.shapeForCapo("Eb/G", 1), "D/Gb", "flat root -> flat bass");
  assert.equal(Chords.shapeForCapo("A/Bb", 1), "G#/A", "flat bass -> flat bass spelling");
  assert.equal(Chords.shapeForCapo("C/b7", 2), "A#/b7");
  assert.equal(Chords.shapeForCapo("C/xyz", 2), "A#/xyz");
});
test("shapeForCapo: N, X, junk and capo 0 are unchanged", () => {
  for (const label of ["N", "X", "Hm", "", "Bb", "A:min"]) assert.equal(Chords.shapeForCapo(label, 0), label);
  for (const label of ["N", "X", "Hm", ""]) assert.equal(Chords.shapeForCapo(label, 3), label);
  assert.equal(Chords.shapeForCapo(null, 3), null);
});
test("shapeForCapo / soundingForCapo: a capo outside 0-12 throws", () => {
  for (const capo of [-1, 13, 1.5, 2.5, "2", null, undefined, NaN]) {
    assert.throws(() => Chords.shapeForCapo("A", capo), /capo/, String(capo));
    assert.throws(() => Chords.soundingForCapo("A", capo), /capo/, String(capo));
  }
});

// --- soundingForCapo -------------------------------------------------------------------------
test("soundingForCapo: the sounding chord moves up, sharp spelling", () => {
  assert.equal(Chords.soundingForCapo("Em7", 2), "F#m7");
  assert.equal(Chords.soundingForCapo("Cadd9", 2), "Dadd9");
  assert.equal(Chords.soundingForCapo("G/B", 2), "A/C#");
  assert.equal(Chords.soundingForCapo("B", 1), "C");
  assert.equal(Chords.soundingForCapo("A", 0), "A");
  assert.equal(Chords.soundingForCapo("Bb", 0), "A#", "capo 0 respells flats as sharps");
  assert.equal(Chords.soundingForCapo("G/b7", 2), "A/b7", "a degree bass is relative and is kept");
  for (const label of ["N", "X", "Hm"]) assert.equal(Chords.soundingForCapo(label, 2), label);
});
test("soundingForCapo undoes shapeForCapo up to spelling", () => {
  for (const root of ROOTS) for (const suffix of ["", "m", "7", "sus4"]) for (let capo = 0; capo <= 12; capo++) {
    const label = root + suffix + "/E";
    const back = Chords.parse(Chords.soundingForCapo(Chords.shapeForCapo(label, capo), capo));
    assert.deepEqual([back.rootPc, back.quality, back.bassPc], [ROOT_PC[root], suffix, 4], `${label} capo ${capo}`);
  }
});

// --- coreLabel -------------------------------------------------------------------------------
test("coreLabel: reduces known qualities only", () => {
  const cases = { "F#m7": "F#m", Cmaj7: "C", "A:min7": "Am", E7sus4: "Esus4", A7sus: "Asus4", B7: "B", "Am7/G": "Am/G", "Fmaj7/C": "F/C",
    Cadd9: "C", Cadd2: "C", "Gmaj(9)": "G", "Cmaj(add9)": "C", "C(1,3,5,9)": "C", "Csus4(b7)": "Csus4", "C7/b7": "C/b7" };
  for (const [label, core] of Object.entries(cases)) assert.equal(Chords.coreLabel(label), core, label);
});
test("coreLabel: suspensions, other qualities and non-chords are unchanged", () => {
  for (const label of ["Bsus4", "Bsus2", "G/B", "Am", "C6", "C9", "Cdim7", "Caug", "A:min", "N", "X", "", "Hm", "Am7/", "C7/xyz", "Cm7/E/G"]) {
    assert.equal(Chords.coreLabel(label), label, label);
  }
  assert.equal(Chords.coreLabel(null), null);
  assert.equal(Chords.coreLabel(undefined), undefined);
});

// --- normalize -------------------------------------------------------------------------------
const brief = p => (({ root, rootPc, quality, bass, bassPc }) => ({ root, rootPc, quality, bass, bassPc }))(p);
test("normalize: root, canonical quality and bass", () => {
  assert.deepEqual(brief(Chords.normalize("F#m7")), { root: "F#", rootPc: 6, quality: "m7", bass: null, bassPc: null });
  assert.deepEqual(brief(Chords.normalize("Cm/D#")), { root: "C", rootPc: 0, quality: "m", bass: "D#", bassPc: 3 });
  assert.equal(Chords.normalize("Bb").rootPc, 10);
  assert.equal(Chords.normalize("A#").rootPc, 10);
  assert.equal(Chords.normalize("E5").quality, "5");
  assert.equal(Chords.normalize("G/G").bass, null, "G/G is just G");
  assert.equal(Chords.normalize("A:min/b3").bass, "C");
  assert.equal(Chords.normalize("F/b7").bass, "Eb", "an F root spells a degree bass flat");
  assert.equal(Chords.normalize("Am9").quality, "m7");
  assert.equal(Chords.normalize("Am9").simplified, true);
  assert.equal(Chords.normalize("Am7").simplified, false);
  assert.equal(Chords.normalize("C7b9").quality, "7");
  assert.equal(Chords.normalize("Cmaj9").quality, "maj7");
  assert.equal(Chords.normalize("Cmmaj7").quality, "m");
  assert.equal(Chords.normalize("C6/9").quality, "6");
  assert.equal(Chords.normalize(" C♯m ").name, "C#m");
  assert.equal(Chords.normalize("A:hdim7").name, "Am7b5");
  assert.equal(Chords.normalize("Bbm/F").input, "Bbm/F");
});
test("normalize: no-chord markers and unknown qualities are null", () => {
  for (const label of ["N", "X", "N.C.", "NC", "*", "", "H", "Amxyz", "Foo", null, 3]) assert.equal(Chords.normalize(label), null, String(label));
});
test("normalize: every quality lands in QUALITIES", () => {
  for (const label of ["C", "Cm", "C7", "Cm7", "Cmaj7", "Csus2", "Csus4", "C7sus4", "Cadd9", "C6", "Cm6", "Cdim", "Caug", "C9", "C5", "Cdim7", "Cm7b5",
    "C11", "C13", "Cm11", "Cmaj13", "C7#9", "Cmadd9", "C:maj", "CM7", "CΔ", "Cø", "C+", "Co7"]) {
    const p = Chords.normalize(label);
    assert.ok(p && Chords.QUALITIES.includes(p.quality), label);
  }
});

// --- noteName --------------------------------------------------------------------------------
test("noteName: sharp spelling of a pitch class", () => {
  assert.deepEqual([0, 1, 4, 10, 11, 12, -1].map(Chords.noteName), ["C", "C#", "E", "A#", "B", "C", "B"]);
  assert.equal(Chords.noteName(null), null);
});

// --- exported songs --------------------------------------------------------------------------
test("every label in the exported songs parses or is N/X, and its shapes stay chord labels", () => {
  const dir = path.join(__dirname, "..", "songs");
  const labels = new Set();
  for (const f of fs.readdirSync(dir)) if (f.endsWith(".json") && f !== "index.json") {
    for (const c of JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")).chords || []) labels.add(c.l);
  }
  assert.ok(labels.size > 20);
  for (const label of labels) {
    if (label === "N" || label === "X") continue;
    assert.ok(Chords.parse(label), label);
    assert.ok(Chords.normalize(label), label);
    for (let capo = 0; capo <= 7; capo++) assert.ok(Chords.parse(Chords.coreLabel(Chords.shapeForCapo(label, capo))), `${label} capo ${capo}`);
  }
});

console.log(`chords.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`chords.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
