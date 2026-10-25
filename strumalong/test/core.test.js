"use strict";
// Unit tests for strumalong/lib/core.js. Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const core = require("../lib/core.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}
const close = (actual, expected, eps = 1e-9, message) => assert.ok(Math.abs(actual - expected) <= eps, message || `${actual} != ${expected}`);
const states = part => part.dots.map(d => d.state === "past" ? "◉" : d.state === "active" ? "●" : "○").join("");

// --- Synthetic songs -------------------------------------------------------------------------
// 4/4 at 120 BPM: beat i at 1 + 0.5 i seconds, i = 0..40 (last beat 21.0 s).
const grid = (first, step, count) => Array.from({ length: count }, (_, i) => +(first + step * i).toFixed(6));
function song4(confident, extra = {}) {
  return {
    id: "synthetic-4", capo: 0, recording: { duration_seconds: 22 },
    rhythm: { status: "estimated", bpm: 120, beats_per_bar: 4, beats_per_bar_assumed: false, meter_label: "4/4 assumed",
      bar_phase: 0, bar_phase_confident: confident },
    beats: grid(1, 0.5, 41),
    chords: [
      { s: 0, e: 1.0, l: "N" },       // starts 2 beat intervals before the grid: seconds fallback
      { s: 1.0, e: 3.0, l: "A" },     // beats 0..4: 4 dots
      { s: 3.0, e: 3.2, l: "D" },     // 0.4 beat: quick
      { s: 3.2, e: 5.0, l: "E" },     // beats 4.4..8: 4 dots, base 4 (a confident bar start)
      { s: 5.0, e: 5.5, l: "G7" },    // G7 + G merge in Core view
      { s: 5.5, e: 7.0, l: "G" },
      { s: 7.0, e: 8.0, l: "X" },     // unclear, 2 dots
      { s: 8.0, e: 18.0, l: "C", c: 1 }, // beats 14..34: 20 dots, capped to 8
      { s: 18.0, e: 22.0, l: "Am" },  // ends beyond the extended grid: seconds fallback, last chord
    ],
    strumming: { patterns: [
      { id: "steady-down", counts: ["1", "2", "3", "4"], strokes: ["D", "D", "D", "D"] },
      { id: "down-up", counts: ["1", "&", "2", "&", "3", "&", "4", "&"], strokes: ["D", "U", "D", "U", "D", "U", "D", "U"] },
    ] },
    ...extra,
  };
}
// House-like 6/8: 2 dotted-quarter beats per bar, beat every 0.75 s from 0.6 s.
function songHouse(phase = 0, confident = true) {
  return {
    id: "synthetic-68", capo: 0, recording: { duration_seconds: 40 },
    rhythm: { status: "estimated", bpm: 80, beats_per_bar: 2, beats_per_bar_assumed: false, meter_label: "6/8 · 2 dotted-quarter beats per bar",
      bar_phase: phase, bar_phase_confident: confident },
    beats: grid(0.6, 0.75, 48),
    chords: [{ s: 0, e: 0.55, l: "N" }, { s: 0.55, e: 2.1, l: "Am" }, { s: 2.1, e: 9.6, l: "C" }, { s: 9.6, e: 40, l: "E" }],
    strumming: { patterns: [{ id: "six-anchor", counts: ["1", "2", "3", "4", "5", "6"], strokes: ["D", "—", "—", "D", "—", "—"] }] },
  };
}

// --- Ported label helpers ------------------------------------------------------------------
test("transposePracticeLabel: capo shapes", () => {
  assert.equal(core.transposePracticeLabel("A", 2), "G");
  assert.equal(core.transposePracticeLabel("F#m7", 2), "Em7");
  assert.equal(core.transposePracticeLabel("Bb", 1), "A");
  assert.equal(core.transposePracticeLabel("E/G#", 2), "D/F#");
  assert.equal(core.transposePracticeLabel("Eb/G", 1), "D/Gb");
  assert.equal(core.transposePracticeLabel("N", 3), "N");
  assert.equal(core.transposePracticeLabel("X", 3), "X");
  assert.equal(core.transposePracticeLabel("C", 0), "C");
  assert.throws(() => core.transposePracticeLabel("C", 13));
  assert.throws(() => core.transposePracticeLabel("C", 1.5));
});
test("coreChordLabel: reduces known qualities only", () => {
  assert.equal(core.coreChordLabel("F#m7"), "F#m");
  assert.equal(core.coreChordLabel("Cmaj7"), "C");
  assert.equal(core.coreChordLabel("A:min7"), "Am");
  assert.equal(core.coreChordLabel("E7sus4"), "Esus4");
  assert.equal(core.coreChordLabel("Bsus4"), "Bsus4");
  assert.equal(core.coreChordLabel("G/B"), "G/B");
  assert.equal(core.coreChordLabel("Am7/G"), "Am/G");
  assert.equal(core.coreChordLabel("B7"), "B");
  assert.equal(core.coreChordLabel("N"), "N");
  assert.equal(core.coreChordLabel(null), null);
});

const mac = (() => {
  const file = path.join(__dirname, "..", "..", "experiments", "review", "app.js");
  try { return fs.existsSync(file) ? require(file) : null; } catch (_) { return null; }
})();
const PARITY_LABELS = ["N", "X", "A", "Am", "A:min", "A:maj", "A7", "Amaj7", "Am7", "F#m7", "F#m", "Bsus4", "Bsus2", "E/B", "E/G#", "Cm/D#",
  "F/C", "G/B", "D/F#", "C/G", "Bb", "Eb", "Db", "Gb7", "C#m", "Abmaj7", "B7", "Bm7", "Bm", "Cmaj7", "D7", "Dsus2", "Esus4", "E7sus4",
  "A7sus", "Gmaj(9)", "Cmaj(add9)", "C(1,3,5,9)", "Csus4(b7)", "Cadd9", "Cadd2", "Fmaj7", "Em7", "E:min7", "Fm", "Hm", "", "C/b7", "C/3",
  "Cb", "B#", "E#", "Fb", "Am/C", "Dm7", "G7", "E7", "Fmaj7/C", "Bbm", "A#dim", "Cdim7", "Caug", "C6", "Cm6", "C9", "C11", "C13", "c", "Am/", "Eb/Bb"];
function extraLabels() {
  // Labels from built songs and the local chart pack, when present (both optional).
  const found = new Set();
  const songsDir = path.join(__dirname, "..", "songs");
  try { for (const f of fs.readdirSync(songsDir)) if (f.endsWith(".json") && f !== "index.json") {
    for (const c of JSON.parse(fs.readFileSync(path.join(songsDir, f), "utf8")).chords || []) found.add(c.l);
  } } catch (_) { /* songs not built yet */ }
  return [...found];
}
test("parity: transposePracticeLabel and coreChordLabel match experiments/review/app.js", () => {
  if (!mac) { console.log("  (skipped parity: experiments/review/app.js not found)"); return; }
  const labels = [...new Set([...PARITY_LABELS, ...extraLabels()])];
  let checks = 0;
  for (const label of labels) {
    assert.equal(core.coreChordLabel(label), mac.coreChordLabel(label), `core ${label}`); checks++;
    for (let capo = 0; capo <= 12; capo++) {
      assert.equal(core.transposePracticeLabel(label, capo), mac.transposePracticeLabel(label, capo), `transpose ${label} capo ${capo}`);
      assert.equal(core.shapeLabel(label, { capo, view: "shapes", quality: "core" }), mac.practiceLabel(label, "capo-shapes", capo, "core-chords"));
      assert.equal(core.shapeLabel(label, { capo, view: "shapes", quality: "full" }), mac.practiceLabel(label, "capo-shapes", capo, "full-chords"));
      assert.equal(core.shapeLabel(label, { capo, view: "sounding", quality: "core" }), mac.practiceLabel(label, "sounding-pitches", capo, "core-chords"));
      checks += 4;
    }
  }
  for (const capo of [-1, 13, 2.5, "2", null]) {
    assert.throws(() => core.transposePracticeLabel("A", capo));
    assert.throws(() => mac.transposePracticeLabel("A", capo));
  }
  assert.ok(checks > 1000);
});
test("parity: beatPosition and formatTime match experiments/review/app.js", () => {
  if (!mac) return;
  const beats = song4(true).beats;
  for (let t = -1; t <= 23; t += 0.137) assert.equal(core.beatPosition(beats, t), mac.beatPosition(beats, t));
  for (const t of [0, 21, 1, 1.25, NaN, Infinity, "3"]) assert.equal(core.beatPosition(beats, t), mac.beatPosition(beats, t));
  assert.equal(core.beatPosition([1], 1), mac.beatPosition([1], 1));
  for (const s of [0, 0.4, 59.99, 60, 61.5, 3599, 3600, 7322]) assert.equal(core.formatTime(s), mac.timeLabel(s));
});

test("shapeLabel: view and quality options", () => {
  assert.equal(core.shapeLabel("A", { capo: 2 }), "G");
  assert.equal(core.shapeLabel("A", { capo: 2, view: "sounding" }), "A");
  assert.equal(core.shapeLabel("F#m7", { capo: 2, quality: "full" }), "Em7");
  assert.equal(core.shapeLabel("F#m7", { capo: 2 }), "Em");
  assert.equal(core.shapeLabel("F#m7", { capo: 2, view: "sounding", quality: "full" }), "F#m7");
  assert.equal(core.shapeLabel("N", { capo: 5 }), "N");
  assert.equal(core.shapeLabel("X", {}), "X");
  assert.equal(core.shapeLabel("C", { capo: 99 }), "C", "invalid capo falls back to 0");
  assert.equal(core.shapeLabel("C"), "C");
});
test("displayLabel: N, X and empty", () => {
  assert.equal(core.displayLabel("N"), "No chord");
  assert.equal(core.displayLabel("X"), "Unclear");
  assert.equal(core.displayLabel("Am"), "Am");
  assert.equal(core.displayLabel(""), "—");
  assert.equal(core.displayLabel(null), "—");
});

// --- buildTimeline ---------------------------------------------------------------------------
test("buildTimeline: core view merges G7 + G, full view does not", () => {
  const coreView = core.buildTimeline(song4(true), { quality: "core" });
  assert.deepEqual(coreView.map(e => e.label), ["N", "A", "D", "E", "G", "X", "C", "Am"]);
  const g = coreView[4];
  assert.deepEqual([g.s, g.e, g.full, g.sounding], [5.0, 7.0, "G7", "G7"]);
  const fullView = core.buildTimeline(song4(true), { quality: "full" });
  assert.deepEqual(fullView.map(e => e.label), ["N", "A", "D", "E", "G7", "G", "X", "C", "Am"]);
  assert.deepEqual(Object.keys(fullView[1]).sort(), ["c", "e", "full", "label", "s", "sounding"]);
});
test("buildTimeline: merges never bridge N or X; correction flag survives a merge", () => {
  const song = { capo: 0, chords: [{ s: 0, e: 1, l: "A" }, { s: 1, e: 2, l: "N" }, { s: 2, e: 3, l: "A" }, { s: 3, e: 4, l: "X" },
    { s: 4, e: 5, l: "X" }, { s: 5, e: 6, l: "N" }, { s: 6, e: 7, l: "N" }, { s: 7, e: 8, l: "A" }, { s: 8, e: 9, l: "A7", c: 1 }] };
  const tl = core.buildTimeline(song, { quality: "core" });
  assert.deepEqual(tl.map(e => e.label), ["A", "N", "A", "X", "X", "N", "N", "A"]);
  assert.deepEqual([tl[7].s, tl[7].e, tl[7].c], [7, 9, 1]);
});
test("buildTimeline: does not merge across a time gap", () => {
  const tl = core.buildTimeline({ chords: [{ s: 0, e: 1, l: "A" }, { s: 1.5, e: 2, l: "A" }] }, {});
  assert.equal(tl.length, 2);
});
test("buildTimeline: capo shapes, sounding view and capo override", () => {
  const song = { capo: 2, chords: [{ s: 0, e: 1, l: "F#m7" }, { s: 1, e: 2, l: "A" }, { s: 2, e: 3, l: "Bsus4" }, { s: 3, e: 4, l: "E/G#" }] };
  assert.deepEqual(core.buildTimeline(song, { view: "shapes", quality: "full" }).map(e => e.label), ["Em7", "G", "Asus4", "D/F#"]);
  assert.deepEqual(core.buildTimeline(song, { view: "shapes" }).map(e => e.label), ["Em", "G", "Asus4", "D/F#"]);
  assert.deepEqual(core.buildTimeline(song, { view: "sounding", quality: "full" }).map(e => e.label), ["F#m7", "A", "Bsus4", "E/G#"]);
  assert.deepEqual(core.buildTimeline(song, { capo: 0 }).map(e => e.label), ["F#m", "A", "Bsus4", "E/G#"]);
  assert.deepEqual(core.buildTimeline(song, { view: "shapes" }).map(e => e.sounding), ["F#m7", "A", "Bsus4", "E/G#"]);
});
test("buildTimeline: drops invalid and overlapping events, tolerates missing chords", () => {
  const tl = core.buildTimeline({ chords: [{ s: 0, e: 1, l: "A" }, { s: 0.5, e: 2, l: "D" }, { s: 2, e: 2, l: "E" }, null, { s: 2, e: 3 }, { s: 3, e: 4, l: "G" }] }, {});
  assert.deepEqual(tl.map(e => e.label), ["A", "G"]);
  assert.deepEqual(core.buildTimeline({}, {}), []);
  assert.deepEqual(core.buildTimeline(null), []);
});

// --- chordIndexAt ----------------------------------------------------------------------------
test("chordIndexAt: boundaries, gaps and outside", () => {
  const ev = [{ s: 1, e: 2 }, { s: 2, e: 3 }, { s: 4, e: 5 }];
  assert.equal(core.chordIndexAt(ev, 0.5), -1);
  assert.equal(core.chordIndexAt(ev, 1), 0);
  assert.equal(core.chordIndexAt(ev, 1.999), 0);
  assert.equal(core.chordIndexAt(ev, 2), 1);
  assert.equal(core.chordIndexAt(ev, 3.5), -1);
  assert.equal(core.chordIndexAt(ev, 4.2), 2);
  assert.equal(core.chordIndexAt(ev, 5), -1);
  assert.equal(core.chordIndexAt([], 1), -1);
  assert.equal(core.chordIndexAt(ev, NaN), -1);
  const many = Array.from({ length: 1000 }, (_, i) => ({ s: i, e: i + 1 }));
  for (const t of [0, 0.5, 499.99, 500, 999.5]) assert.equal(core.chordIndexAt(many, t), Math.floor(t));
});

// --- cueAt -----------------------------------------------------------------------------------
const tlFor = (song, opts = { quality: "core" }) => core.buildTimeline(song, opts);
test("cueAt: inside an N span before the grid shows No chord in seconds", () => {
  const song = song4(true), cue = core.cueAt(tlFor(song), song, 0.5);
  assert.equal(cue.now.kind, "none");
  assert.equal(cue.now.display, "No chord");
  assert.deepEqual(cue.now.dots, []);
  assert.equal(cue.now.seconds, 1.0);
  close(cue.now.remaining, 0.5);
  assert.equal(cue.inBeatGrid, false);
  assert.equal(cue.beatsUntilChange, null);
  close(cue.secondsUntilChange, 0.5);
  assert.equal(cue.next.label, "A");
  assert.equal(states(cue.next), "○○○○");
});
test("cueAt: active, past and future dots through a 4-beat hold", () => {
  const song = song4(true), tl = tlFor(song);
  let cue = core.cueAt(tl, song, 1.0);
  assert.equal(cue.now.label, "A");
  assert.equal(states(cue.now), "●○○○");
  assert.equal(cue.beatsUntilChange, 4);
  assert.equal(cue.inBeatGrid, true);
  assert.equal(cue.now.barStart, true);
  cue = core.cueAt(tl, song, 2.0);
  assert.equal(states(cue.now), "◉◉●○");
  assert.equal(cue.beatsUntilChange, 2);
  cue = core.cueAt(tl, song, 2.6);
  assert.equal(states(cue.now), "◉◉◉●");
  assert.equal(cue.beatsUntilChange, 1);
  close(cue.secondsUntilChange, 0.4);
  assert.equal(cue.toEnd, false);
});
test("cueAt: quick change gets one dot and a quick flag (as NEXT and NOW)", () => {
  const song = song4(true), tl = tlFor(song);
  let cue = core.cueAt(tl, song, 2.9);
  assert.equal(cue.next.label, "D");
  assert.equal(cue.next.quick, true);
  assert.equal(cue.next.dots.length, 1);
  cue = core.cueAt(tl, song, 3.1);
  assert.equal(cue.now.label, "D");
  assert.equal(cue.now.quick, true);
  assert.equal(states(cue.now), "●");
  assert.equal(cue.beatsUntilChange, 1);
  assert.equal(cue.now.beats, 1);
});
test("cueAt: rounded start beat, clamped active dot and a confident bar start", () => {
  const song = song4(true), tl = tlFor(song);
  const cue = core.cueAt(tl, song, 3.3); // E: beats 4.4..8 -> 4 dots on beats 4..7
  assert.equal(cue.now.label, "E");
  assert.equal(cue.now.beats, 4);
  assert.equal(states(cue.now), "●○○○");
  assert.equal(cue.now.barStart, true);
  assert.deepEqual(cue.now.barBefore, []);
  assert.equal(core.cueAt(tl, song, 4.99).now.dots[3].state, "active");
});
test("cueAt: X span shows Unclear with dots", () => {
  const song = song4(true), cue = core.cueAt(tlFor(song), song, 7.6);
  assert.equal(cue.now.kind, "unclear");
  assert.equal(cue.now.display, "Unclear");
  assert.equal(states(cue.now), "◉●");
});
test("cueAt: long hold caps dots at 2 bars with more:n, bar lines from a confident phase", () => {
  const song = song4(true), tl = tlFor(song);
  let cue = core.cueAt(tl, song, 7.6);
  assert.equal(cue.next.label, "C");
  assert.equal(cue.next.c, 1);
  assert.equal(cue.next.beats, 20);
  assert.equal(states(cue.next), "○○○○○○○○");
  assert.equal(cue.next.more, 12);
  assert.deepEqual(cue.next.barBefore, [2, 6]); // beats 16 and 20 are bar starts (phase 0)
  assert.equal(cue.next.barStart, false);
  cue = core.cueAt(tl, song, 8.0);
  assert.equal(states(cue.now), "●○○○○○○○");
  assert.equal(cue.now.dotOffset, 0);
  assert.equal(cue.beatsUntilChange, 20);
  cue = core.cueAt(tl, song, 12.0); // beat 22 -> hold index 8, in the bar that starts at index 6
  assert.equal(cue.now.dotOffset, 6);
  assert.equal(states(cue.now), "◉◉●○○○○○");
  assert.deepEqual(cue.now.barBefore, [4]);
  assert.equal(cue.now.more, 6);
  assert.equal(cue.beatsUntilChange, 12);
  cue = core.cueAt(tl, song, 17.9); // last bar: window clamps to the end of the hold
  assert.equal(cue.now.dotOffset, 12);
  assert.equal(states(cue.now), "◉◉◉◉◉◉◉●");
  assert.equal(cue.now.more, 0);
  assert.equal(cue.beatsUntilChange, 1);
});
test("cueAt: an unconfident phase still anchors bar lines to bar_phase (approx bars), as the strum count does", () => {
  const song = song4(false), tl = tlFor(song);
  const cue = core.cueAt(tl, song, 8.0); // C starts on beat 14; phase 0 puts lines before beats 16 and 20
  assert.equal(cue.approxBars, true);
  assert.deepEqual(cue.now.barBefore, [2, 6], "not hold-relative [4]");
  assert.equal(cue.now.barStart, null, "no solid bar-start border without confidence");
  const later = core.cueAt(tl, song, 12.0); // beat 22 -> hold index 8, in the bar that starts at index 6
  assert.equal(later.now.dotOffset, 6);
  assert.deepEqual(later.now.barBefore, [4]);
  assert.equal(states(later.now), "◉◉●○○○○○");
  assert.equal(core.cueAt(tl, song4(true), 8).approxBars, false);
  const steady = song.strumming.patterns[0];
  assert.equal(core.strumStep(song, steady, 9.01), 0, "count 1 lights on the beat-16 bar line");
  assert.equal(core.strumStep(song, steady, 8.01), 2, "the chord change on beat 14 is count 3, not a restart");
});
test("cueAt: dots run round(startBeat)..round(endBeat), so contiguous holds share no beat", () => {
  const song = song4(true);
  // Beat i is at 1 + 0.5 i s. A spans beats 3.65..6.4 (span 2.75): 2 dots on beats 4 and 5, then D from beat 6.
  song.chords = [{ s: 1, e: 2.825, l: "E" }, { s: 2.825, e: 4.2, l: "A" }, { s: 4.2, e: 6, l: "D" }];
  const tl = tlFor(song);
  let cue = core.cueAt(tl, song, 2.9);
  assert.equal(cue.now.label, "A");
  assert.equal(cue.now.beats, 2, "round(6.4) - round(3.65) = 2, not round(2.75) = 3");
  assert.equal(states(cue.now), "●○");
  assert.equal(cue.beatsUntilChange, 2);
  assert.equal(Math.round(cue.now.startBeat) + cue.now.beats, Math.round(cue.next.startBeat));
  assert.equal(cue.next.barStart, false, "D's first dot is beat 6: mid-bar at phase 0");
  cue = core.cueAt(tl, song, 4.15); // last moment of A (beat 6.3) is still its second dot
  assert.equal(states(cue.now), "◉●");
});
test("cueAt: non-integer or missing bar phase never claims confidence", () => {
  const a = song4(true); a.rhythm.bar_phase = 1.5;
  assert.equal(core.cueAt(tlFor(a), a, 8).approxBars, true);
  const b = song4(true); delete b.rhythm.bar_phase;
  assert.equal(core.cueAt(tlFor(b), b, 8).approxBars, true);
  const c = song4(true); c.rhythm.bar_phase = 6; // normalised mod beats_per_bar: same as phase 2
  const cue = core.cueAt(tlFor(c), c, 8); // C starts on beat 14; (14 - 2) mod 4 == 0
  assert.equal(cue.now.barStart, true);
  assert.deepEqual(cue.now.barBefore, [4]);
});
test("cueAt: last chord running into the beatless tail falls back to seconds; next is null", () => {
  const song = song4(true), tl = tlFor(song);
  const cue = core.cueAt(tl, song, 19.0); // Am ends at 22.0 > last beat 21.0 + one interval
  assert.equal(cue.now.label, "Am");
  assert.deepEqual(cue.now.dots, []);
  assert.equal(cue.now.beats, null);
  assert.equal(cue.inBeatGrid, false);
  assert.equal(cue.beatsUntilChange, null);
  close(cue.secondsUntilChange, 3.0);
  assert.equal(cue.next, null);
  assert.equal(cue.toEnd, true);
});
test("cueAt: last chord inside the grid counts beats to the end", () => {
  const song = song4(true);
  song.chords = [{ s: 1, e: 3, l: "A" }];
  const cue = core.cueAt(tlFor(song), song, 1.6);
  assert.equal(cue.next, null);
  assert.equal(cue.toEnd, true);
  assert.equal(cue.beatsUntilChange, 3);
});
test("cueAt: at or after the end of the chart", () => {
  const song = song4(true), tl = tlFor(song);
  for (const t of [22.0, 30]) {
    const cue = core.cueAt(tl, song, t);
    assert.equal(cue.now.kind, "end");
    assert.equal(cue.now.display, "End");
    assert.equal(cue.next, null);
    assert.equal(cue.secondsUntilChange, null);
  }
});
test("cueAt: before the first chord (negative nudge) and in a gap", () => {
  const song = song4(true);
  song.chords = [{ s: 1.5, e: 3, l: "A" }, { s: 4, e: 6, l: "D" }];
  const tl = tlFor(song);
  let cue = core.cueAt(tl, song, -0.2);
  assert.equal(cue.now.kind, "before");
  assert.equal(cue.next.idx, 0);
  close(cue.secondsUntilChange, 1.7);
  assert.equal(cue.beatsUntilChange, null, "-0.2 s is outside the grid");
  cue = core.cueAt(tl, song, 1.1); // inside the grid, before the first chord at beat 1
  assert.equal(cue.now.kind, "before");
  assert.equal(cue.beatsUntilChange, 1);
  cue = core.cueAt(tl, song, 3.5);
  assert.equal(cue.now.kind, "gap");
  assert.equal(cue.next.label, "D");
  close(cue.secondsUntilChange, 0.5);
  assert.equal(cue.beatsUntilChange, 1);
});
test("cueAt: empty timeline, no beats and invalid t", () => {
  let cue = core.cueAt([], song4(true), 3);
  assert.equal(cue.now.kind, "empty");
  assert.equal(cue.next, null);
  const song = { chords: [{ s: 0, e: 2, l: "A" }, { s: 2, e: 2.2, l: "D" }, { s: 2.2, e: 4, l: "E" }], rhythm: { bpm: 120 } };
  cue = core.cueAt(tlFor(song), song, 1);
  assert.deepEqual(cue.now.dots, []);
  assert.equal(cue.inBeatGrid, false);
  assert.equal(cue.next.quick, true, "0.2 s at 120 BPM is under 0.75 beat");
  cue = core.cueAt(tlFor(song), song, NaN);
  assert.equal(cue.now.label, "A");
});
test("cueAt: chord starting just before the first beat still gets dots (one-beat extension)", () => {
  const song = songHouse(), tl = tlFor(song);
  const cue = core.cueAt(tl, song, 0.58); // Am starts 0.05 s before the first beat
  assert.equal(cue.now.label, "Am");
  assert.equal(cue.now.beats, 2);
  assert.equal(states(cue.now), "●○");
  assert.equal(cue.inBeatGrid, true);
});
test("cueAt: 2 beats per bar caps at 4 dots and puts bar lines every 2 beats", () => {
  const song = songHouse(0, true), tl = tlFor(song);
  const cue = core.cueAt(tl, song, 2.2); // C: beats 2..12 -> 10 dots
  assert.equal(cue.now.label, "C");
  assert.equal(cue.now.beats, 10);
  assert.equal(cue.now.dots.length, 4);
  assert.equal(cue.now.more, 6);
  assert.deepEqual(cue.now.barBefore, [2]);
  assert.equal(cue.beatsPerBar, 2);
  const odd = songHouse(1, true);
  assert.deepEqual(core.cueAt(tlFor(odd), odd, 2.2).now.barBefore, [1, 3]);
});
test("cueAt: Wonderwall-style assumed 4 beats per bar (null in data falls back to 4)", () => {
  const assumed = song4(false); assumed.rhythm.beats_per_bar_assumed = true; assumed.rhythm.bar_phase = null;
  let cue = core.cueAt(tlFor(assumed), assumed, 8);
  assert.equal(cue.beatsPerBar, 4);
  assert.equal(cue.approxBars, true);
  const missing = song4(true); missing.rhythm.beats_per_bar = null;
  cue = core.cueAt(tlFor(missing), missing, 8);
  assert.equal(cue.beatsPerBar, 4);
  assert.equal(cue.now.dots.length, 8);
});

// --- per-chord bar anchors (b / a) -----------------------------------------------------------
// song4 grid: beat i at 1 + 0.5 i s. A local phase switch and a hold-relative chord, written as the exporter does.
function anchoredSong() {
  const song = song4(false);
  song.chords = [
    { s: 1.0, e: 5.0, l: "A", b: 0 },          // beats 0..8: bar lines before beats 4 (phase 0)
    { s: 5.0, e: 7.5, l: "D", b: 0 },          // beats 8..13: line before beat 12
    { s: 7.5, e: 10.0, l: "E", b: 1 },         // beats 13..18: local phase 1 (a slip): it starts a bar; line before 17
    { s: 10.0, e: 11.5, l: "G", b: 2, a: 1 },  // beats 18..21: hold-relative (approx): starts a bar at 18
    { s: 11.5, e: 14.5, l: "C", b: 1, a: 1 },  // beats 21..27: hold-relative: starts a bar at 21, line before 25
  ];
  return song;
}
test("anchors: bar lines follow each chord's b; NEXT bar start only for confident anchors", () => {
  const song = anchoredSong(), tl = tlFor(song);
  let cue = core.cueAt(tl, song, 1.0);
  assert.deepEqual(cue.now.barBefore, [4]);
  assert.equal(cue.now.barStart, true, "phase-0 anchor, not approx: solid bar start");
  assert.equal(cue.approxBars, false);
  cue = core.cueAt(tl, song, 5.0);
  assert.deepEqual(cue.now.barBefore, [4], "D: beats 8..12, bar line before beat 12");
  assert.equal(cue.next.label, "E");
  assert.equal(cue.next.barStart, true, "E starts a bar under its own (local) phase 1");
  cue = core.cueAt(tl, song, 7.5);
  assert.deepEqual(cue.now.barBefore, [4], "E: beats 13..17, line before beat 17");
  assert.equal(cue.next.barStart, null, "G is hold-relative (approx): no solid border");
  cue = core.cueAt(tl, song, 10.0);
  assert.equal(cue.approxBars, true, "approx bars while a hold-relative anchor is in force");
  cue = core.cueAt(tl, song, 11.6);
  assert.deepEqual(cue.now.barBefore, [4], "C: beats 21..27, line before beat 25");
  assert.equal(cue.now.approx, true);
});
test("anchors: the strum count restarts at 1 where each anchor starts a bar", () => {
  const song = anchoredSong(), steady = song.strumming.patterns[0];
  const at = beat => core.strumStep(song, steady, 1 + 0.5 * beat + 0.01);
  assert.deepEqual([0, 3, 4, 8, 11, 12].map(at), [0, 3, 0, 0, 3, 0], "phase 0");
  assert.deepEqual([13, 14, 16, 17].map(at), [0, 1, 3, 0], "local phase 1 from beat 13");
  assert.deepEqual([18, 19, 20].map(at), [0, 1, 2], "hold-relative G starts a bar at 18");
  assert.deepEqual([21, 24, 25, 26].map(at), [0, 3, 0, 1], "hold-relative C restarts at 21 (G's bar had 3 beats)");
  const down = song.strumming.patterns[1];
  assert.equal(core.strumStep(song, down, 1 + 0.5 * 13.6), 1, "eighth steps also count from the anchor");
});
test("anchors: barAnchorAt reports phase, bar and approx per beat; unowned beats take the nearest owned anchor", () => {
  const song = anchoredSong();
  assert.deepEqual(core.barAnchorAt(song, 4), { phase: 0, approx: false, bar: true, half: false, anchored: true });
  assert.deepEqual(core.barAnchorAt(song, 15), { phase: 1, approx: false, bar: false, half: true, anchored: true });
  assert.equal(core.barAnchorAt(song, 18).approx, true);
  assert.equal(core.barAnchorAt(song, 35).phase, 1, "after the chart: the last owned anchor carries forward");
  assert.equal(core.barAnchorAt(song, -1).phase, 0, "before the chart: the first owned anchor carries back");
  assert.equal(core.barAnchorAt(song, 2.7).phase, 0, "a fractional beat uses its floor");
  const plain = song4(true);
  assert.deepEqual(core.barAnchorAt(plain, 6), { phase: 0, approx: false, bar: false, half: true, anchored: false }, "no b fields: song-wide phase");
  assert.equal(core.barAnchorAt(song4(false), 6).approx, true);
});
test("anchors: replacing the chord array refreshes the cached anchor map", () => {
  const song = anchoredSong(), steady = song.strumming.patterns[0];
  assert.equal(core.strumStep(song, steady, 1 + 0.5 * 13 + 0.01), 0);
  song.chords = song.chords.map(c => ({ ...c, b: 0, a: undefined }));
  assert.equal(core.strumStep(song, steady, 1 + 0.5 * 13 + 0.01), 1, "phase 0 everywhere now");
  assert.equal(core.cueAt(tlFor(song), song, 10.2).approxBars, false);
});

// --- strumStep -------------------------------------------------------------------------------
test("strumStep: 4/4 patterns follow the beat grid", () => {
  const song = song4(true), [steady, downUp] = song.strumming.patterns;
  assert.equal(core.strumStep(song, steady, 1.0), 0);
  assert.equal(core.strumStep(song, steady, 1.49), 0);
  assert.equal(core.strumStep(song, steady, 1.5), 1);
  assert.equal(core.strumStep(song, steady, 2.75), 3);
  assert.equal(core.strumStep(song, steady, 3.0), 0);
  assert.equal(core.strumStep(song, downUp, 1.0), 0);
  assert.equal(core.strumStep(song, downUp, 1.25), 1);
  assert.equal(core.strumStep(song, downUp, 2.8), 7);
  assert.equal(core.strumStep(song, downUp, 3.0), 0);
});
test("strumStep: bar phase shifts count 1", () => {
  const song = song4(true); song.rhythm.bar_phase = 1;
  const steady = song.strumming.patterns[0];
  assert.equal(core.strumStep(song, steady, 1.5), 0);
  assert.equal(core.strumStep(song, steady, 1.0), 3);
});
test("strumStep: 6-count pattern on 2 beats per bar is 3 steps per beat", () => {
  const song = songHouse(0, true), six = song.strumming.patterns[0];
  const at = beat => core.strumStep(song, six, 0.6 + 0.75 * beat);
  assert.deepEqual([0, 0.34, 0.67, 1, 1.34, 1.99, 2, 3.5].map(at), [0, 1, 2, 3, 4, 5, 0, 4]);
  const shifted = songHouse(1, true);
  assert.equal(core.strumStep(shifted, six, 0.6 + 0.75), 0);
});
test("strumStep: outside the grid is null; one-beat extension at each end", () => {
  const song = song4(true), steady = song.strumming.patterns[0];
  assert.equal(core.strumStep(song, steady, 0.2), null);
  assert.equal(core.strumStep(song, steady, 0.75), 3, "half a beat before the first beat");
  assert.equal(core.strumStep(song, steady, 21.2), 0, "just after the last beat (index 40)");
  assert.equal(core.strumStep(song, steady, 21.6), null, "beatless tail");
  assert.equal(core.strumStep(song, null, 2), null);
  assert.equal(core.strumStep(song, { counts: [], strokes: [] }, 2), null);
  assert.equal(core.strumStep({ ...song, beats: [] }, steady, 2), null);
});
test("strumStep: assumed 4 beats per bar for a null meter", () => {
  const song = song4(false); song.rhythm.beats_per_bar = null;
  assert.equal(core.strumStep(song, song.strumming.patterns[1], 2.75), 7);
});

// --- suggestCapo -----------------------------------------------------------------------------
test("suggestCapo: open shapes at capo 0 score 1", () => {
  const r = core.suggestCapo([{ s: 0, e: 4, l: "A" }, { s: 4, e: 8, l: "D" }, { s: 8, e: 12, l: "E" }, { s: 12, e: 20, l: "N" }]);
  assert.equal(r.capo, 0);
  assert.equal(r.score, 1);
  assert.equal(r.scores.length, 8);
});
test("suggestCapo: capo 2 shapes win for an F#m/A/Bm/D/E chart", () => {
  const chords = ["F#m", "A", "Bm", "D", "E"].map((l, i) => ({ s: i * 2, e: i * 2 + 2, l }));
  const r = core.suggestCapo(chords);
  assert.equal(r.capo, 2);
  assert.equal(r.score, 1);
  close(r.scores[0], (2 + 1 + 2 + 2) / 10);
});
test("suggestCapo: lower capo on near-ties; half credit for F, Bm and B7", () => {
  const r = core.suggestCapo([{ s: 0, e: 98, l: "A" }, { s: 98, e: 100, l: "F#m" }]);
  close(r.scores[0], 0.98); close(r.scores[2], 1);
  assert.equal(r.capo, 0);
  assert.equal(core.suggestCapo([{ s: 0, e: 1, l: "B7" }]).scores[0], 0.5);
  assert.equal(core.suggestCapo([{ s: 0, e: 1, l: "F" }]).scores[0], 0.5);
  const cSharpMinor = core.suggestCapo([{ s: 0, e: 1, l: "C#m" }]);
  assert.equal(cSharpMinor.capo, 4, "C#m -> Am shape at capo 4");
  assert.equal(cSharpMinor.scores[2], 0.5, "C#m -> Bm shape at capo 2 is half credit");
  assert.equal(core.suggestCapo([{ s: 0, e: 1, l: "C#7" }]).capo, 1, "C#7 -> C7 (core C) at capo 1");
  assert.equal(core.suggestCapo([{ s: 0, e: 1, l: "G/B" }]).scores[0], 1, "slash chords score on their root shape");
});
test("suggestCapo: accepts start/end/sounding events; empty charts", () => {
  assert.equal(core.suggestCapo([{ start: 0, end: 2, sounding: "Bb" }]).capo, 1);
  const empty = core.suggestCapo([]);
  assert.deepEqual([empty.capo, empty.score], [0, 0]);
  assert.equal(core.suggestCapo([{ s: 0, e: 3, l: "X" }]).score, 0);
  assert.equal(core.suggestCapo(null).capo, 0);
});

// --- small helpers ---------------------------------------------------------------------------
test("formatTime: m:ss with clamping", () => {
  assert.equal(core.formatTime(0), "0:00");
  assert.equal(core.formatTime(59.9), "0:59");
  assert.equal(core.formatTime(61), "1:01");
  assert.equal(core.formatTime(3600), "60:00");
  assert.equal(core.formatTime(-5), "0:00");
  assert.equal(core.formatTime(NaN), "0:00");
  assert.equal(core.formatTime(undefined), "0:00");
});
test("strokeGlyph, cueTime, expectedDuration, durationMismatch", () => {
  assert.deepEqual(["D", "U", "—", "x"].map(core.strokeGlyph), ["↓", "↑", "·", "·"]);
  close(core.cueTime(10, 0.5, 100, 200), 10.4);
  close(core.cueTime(10, undefined, undefined, undefined), 10);
  close(core.cueTime(NaN, 1, -50, 0), 0.95);
  assert.equal(core.cueTime(10, 0, 0, 200, 0.5), 9.9, "latency is wall-clock: 200 ms at 0.5x is 0.1 s of media");
  close(core.cueTime(10, 0.5, 100, 200, 2), 10.2, 1e-9, "nudge and offset are not scaled by the rate");
  for (const bad of [0, -1, NaN, undefined, "2"]) close(core.cueTime(10, 0, 0, 200, bad), 9.8, 1e-9, `rate ${bad} falls back to 1`);
  const song = { recording: { duration_seconds: 218.9 } };
  assert.equal(core.expectedDuration(song, { duration_seconds: 225 }), 225);
  assert.equal(core.expectedDuration(song, { duration_seconds: 0 }), 218.9);
  assert.equal(core.expectedDuration(song, null), 218.9);
  assert.equal(core.expectedDuration({}, null), null);
  assert.equal(core.durationMismatch(155, 155.35), false);
  assert.equal(core.durationMismatch(158.4, 155.35), true);
  assert.equal(core.durationMismatch(30, 155), true);
  assert.equal(core.durationMismatch(0, 155), false);
  assert.equal(core.durationMismatch(NaN, 155), false);
  assert.equal(core.durationMismatch(30, null), false);
  assert.equal(core.durationMismatch(160, 155, 10), false);
});

// --- Invariants: synthetic fuzz plus any built songs -----------------------------------------
function checkInvariants(song, timeline, t, label) {
  const cue = core.cueAt(timeline, song, t);
  const bpb = Number.isInteger(song.rhythm && song.rhythm.beats_per_bar) ? song.rhythm.beats_per_bar : 4;
  for (const part of [cue.now, cue.next]) {
    if (!part) continue;
    assert.ok(part.dots.length <= 2 * bpb, `${label}: dot cap at ${t}`);
    assert.ok(part.dots.length === 0 || part.dots.length >= 1);
    if (part.beats !== null) assert.equal(part.dotOffset + part.dots.length + part.more, part.beats, `${label}: dot accounting at ${t}`);
    for (const j of part.barBefore) assert.ok(j > 0 && j < part.dots.length, `${label}: bar index at ${t}`);
    if (part.quick && part.beats !== null) assert.equal(part.beats, 1);
  }
  if (cue.now.idx >= 0) {
    const ev = timeline[cue.now.idx];
    assert.ok(ev.s <= t && t < ev.e, `${label}: now contains t=${t}`);
    if (cue.now.dots.length) assert.equal(cue.now.dots.filter(d => d.state === "active").length, 1, `${label}: one active dot at ${t}`);
    if (cue.next) assert.equal(cue.next.idx, cue.now.idx + 1);
    else assert.equal(cue.now.idx, timeline.length - 1);
  }
  if (cue.next) assert.ok(cue.next.dots.every(d => d.state === "future"));
  if (cue.beatsUntilChange !== null) assert.ok(Number.isInteger(cue.beatsUntilChange) && cue.beatsUntilChange >= 1, `${label}: beats until change at ${t}`);
  if (cue.secondsUntilChange !== null) assert.ok(cue.secondsUntilChange >= 0);
  const step = core.strumStep(song, (song.strumming && song.strumming.patterns && song.strumming.patterns[0]) || null, t);
  if (step !== null) assert.ok(Number.isInteger(step) && step >= 0 && step < song.strumming.patterns[0].strokes.length);
}
test("invariants: randomised synthetic songs", () => {
  let seed = 12345;
  const rand = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  const labels = ["A", "Am", "C", "D", "E", "G", "G7", "N", "X", "F#m7", "Bsus4"];
  for (let n = 0; n < 40; n++) {
    const bpb = [2, 4, null][n % 3], step = 0.3 + rand() * 0.6, first = rand() * 3;
    const beats = grid(first, step, 20 + Math.floor(rand() * 200));
    const chords = []; let s = 0;
    while (s < beats[beats.length - 1] + 5) { const e = +(s + 0.05 + rand() * (rand() < 0.1 ? 30 : 3)).toFixed(3); chords.push({ s, e, l: labels[Math.floor(rand() * labels.length)] }); s = e; }
    const steps = [4, 6, 8][n % 3 === 0 ? 1 : Math.floor(rand() * 3)];
    const pattern = { counts: Array.from({ length: steps }, (_, i) => String(i + 1)), strokes: Array.from({ length: steps }, (_, i) => i % 2 ? "U" : "D") };
    const song = { capo: n % 4, rhythm: { bpm: 60 / step, beats_per_bar: bpb, bar_phase: Math.floor(rand() * 4), bar_phase_confident: rand() < 0.5 }, beats, chords,
      strumming: { patterns: [pattern] } };
    for (const quality of ["core", "full"]) {
      const tl = core.buildTimeline(song, { quality });
      for (let t = -2; t < s + 2; t += 0.173) checkInvariants(song, tl, t, `fuzz ${n}`);
      for (const ev of tl) for (const t of [ev.s, ev.e - 1e-6, (ev.s + ev.e) / 2]) checkInvariants(song, tl, t, `fuzz ${n} edge`);
    }
  }
});
function builtSongs() {
  const dir = path.join(__dirname, "..", "songs");
  let files = [];
  try { files = fs.readdirSync(dir).filter(f => f.endsWith(".json") && f !== "index.json").sort(); } catch (_) { /* not built yet */ }
  return files.map(f => ({ f, song: JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) }));
}
test("property: every drawn bar line is where the strum count reads 1 (built songs, confident or approx)", () => {
  const songs = builtSongs();
  if (!songs.length) { console.log("  (skipped bar-line/strum property: no songs/*.json yet)"); return; }
  let lines = 0;
  const kinds = new Set();
  for (const { f, song } of songs) {
    const beats = song.beats, bpb = song.rhythm.beats_per_bar;
    const counter = { counts: Array.from({ length: bpb }, (_, i) => String(i + 1)), strokes: Array(bpb).fill("D") };
    const tl = core.buildTimeline(song);
    for (let b = 0; b + 1 < beats.length; b++) {
      const anchor = core.barAnchorAt(song, b);
      kinds.add(anchor.approx);
      // Both ways: count 1 exactly on the beats the anchor calls bar starts.
      assert.equal(core.strumStep(song, counter, beats[b] + 0.01) === 0, anchor.bar, `${f}: beat ${b} count-1 / bar-start mismatch`);
    }
    for (let t = beats[0]; t <= beats[beats.length - 1]; t += 0.37) {
      const cue = core.cueAt(tl, song, t);
      for (const part of [cue.now, cue.next]) {
        if (!part || part.startBeat === null) continue;
        for (const j of part.barBefore) {
          const b = Math.round(part.startBeat) + part.dotOffset + j;
          if (b < 0 || b >= beats.length) continue;
          assert.equal(core.strumStep(song, counter, beats[b] + 0.01), 0, `${f}: bar line before beat ${b} (t=${t.toFixed(2)}) is not count 1`);
          lines++;
        }
      }
    }
  }
  assert.ok(lines > 1000, `checked ${lines} bar lines`);
  assert.equal(kinds.size, 2, "built songs include both confident and approx bar anchors");
});
test("property: contiguous in-grid holds hand over beats exactly (built songs, default timeline)", () => {
  const songs = builtSongs();
  if (!songs.length) { console.log("  (skipped hold hand-over property: no songs/*.json yet)"); return; }
  let pairs = 0;
  for (const { f, song } of songs) {
    const tl = core.buildTimeline(song);
    for (let i = 0; i + 1 < tl.length; i++) {
      if (Math.abs(tl[i].e - tl[i + 1].s) >= 1e-3) continue;
      const cue = core.cueAt(tl, song, tl[i].s);
      const a = cue.now, b = cue.next;
      assert.equal(a.idx, i, `${f}: event ${i} is NOW at its own start`);
      if (a.startBeat === null || !b || b.startBeat === null || a.quick || b.quick) continue;
      assert.equal(Math.round(a.startBeat) + a.beats, Math.round(b.startBeat),
        `${f}: event ${i} (${tl[i].label} ${tl[i].s}-${tl[i].e}) beats ${a.beats} from ${a.startBeat.toFixed(2)}; next starts ${b.startBeat.toFixed(2)}`);
      pairs++;
    }
  }
  assert.ok(pairs > 500, `checked ${pairs} hand-overs`);
});
test("invariants: built songs in strumalong/songs (when present)", () => {
  const dir = path.join(__dirname, "..", "songs");
  let files = [];
  try { files = fs.readdirSync(dir).filter(f => f.endsWith(".json") && f !== "index.json"); } catch (_) { /* not built yet */ }
  if (!files.length) { console.log("  (skipped built-song invariants: no songs/*.json yet)"); return; }
  for (const f of files) {
    const song = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    const end = song.recording && song.recording.duration_seconds || 300;
    for (const quality of ["core", "full"]) for (const view of ["shapes", "sounding"]) {
      const tl = core.buildTimeline(song, { quality, view });
      assert.ok(tl.length > 0, `${f}: timeline`);
      for (let t = -0.5; t < end + 1; t += 0.25) checkInvariants(song, tl, t, f);
    }
  }
});

console.log(`core.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`core.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
