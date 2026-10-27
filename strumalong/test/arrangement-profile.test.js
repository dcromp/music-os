"use strict";
// Tests for strumalong/tools/arrangement-profile.js through its interface: main shapes (the card chips and the shapes
// the level counts), the level and its reasons, and the expected_* comparison. Needs only lib/core.js.
// Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const path = require("node:path");
const { arrangementProfile, compareExpected, shapeTier, LEVELS } = require(path.join(__dirname, "..", "tools", "arrangement-profile.js"));

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}

// Synthetic song on a 120 BPM grid (beat i at 0.5 i s) with chord holds given in beats.
function songFromHolds(holds, opts = {}) {
  const beats = Array.from({ length: opts.beats || 200 }, (_, i) => i * 0.5);
  const labels = opts.labels || ["G", "C", "D", "Em"];
  let beat = 0;
  const chords = holds.map((n, i) => { const c = { s: beat * 0.5, e: (beat + n) * 0.5, l: labels[i % labels.length] }; beat += n; return c; });
  return { capo: opts.capo || 0, beats, chords, rhythm: { bpm: opts.bpm || 120, beats_per_bar: 4, beats_per_bar_assumed: false, bar_phase: 0 } };
}
const profileOf = (holds, labels, opts = {}) => arrangementProfile(songFromHolds(holds, { labels, ...opts }), opts);

// --- main shapes ----------------------------------------------------------------------------------
test("main shapes: longest first, ties by first appearance; N and X skipped; G7 counts as G (Simple)", () => {
  const p = profileOf([4, 20, 40, 20, 60, 2, 30], ["N", "G", "B", "G7", "C", "X", "Cm"]);
  // G 40 beats (20 + 20), B 40, C 60, Cm 30 of 190 chord beats.
  assert.deepEqual(p.main_shapes, ["C", "G", "B", "Cm"]);
});
test("main shapes: plain shapes need 4% of chord time, slash shapes 10%", () => {
  const p = profileOf([160, 16, 7, 16, 25], ["A", "G/B", "D", "D/F#", "E/G#"]);
  // total 224: G/B 7.1% and D/F# 7.1% (slash, dropped), D 3.1% (dropped), E/G# 11.2% (kept)
  assert.deepEqual(p.main_shapes, ["A", "E/G#"]);
  assert.deepEqual(profileOf([150, 10], ["A", "D"]).main_shapes, ["A", "D"], "D at 6.25% is a main shape");
});
test("main shapes: blips (under 0.75 beat) never count, however often they occur", () => {
  const holds = [], labels = [];
  for (let i = 0; i < 40; i++) { holds.push(4, 0.5); labels.push(["A", "D"][i % 2], "B"); }
  const p = profileOf(holds, labels);
  assert.deepEqual([p.main_shapes, p.level], [["A", "D"], 1], "B blips are 11% of the time but not a shape");
});
test("main shapes: capo shapes, and no cap on how many", () => {
  const labels = ["A", "B", "C#m", "D", "E", "F#m", "G#m"];
  const p = profileOf(labels.map((_, i) => 20 - i), labels, { capo: 2 });
  assert.deepEqual(p.main_shapes, ["G", "A", "Bm", "C", "D", "Em", "F#m"]);
  assert.deepEqual(profileOf([8], ["N"]).main_shapes, []);
});

// --- level ------------------------------------------------------------------------------------------
test("shapeTier: lead tiers, slash shapes by root, everything else tier 4", () => {
  assert.deepEqual(["A", "Em", "Asus4", "G", "C", "B7", "G/B", "D/F#", "F", "Bm", "F#m", "B", "Cm", "Bb", "G#m", "Fm", "C/E", "F/C", "D/A"].map(shapeTier),
    [1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 2, 3, 1]);
});
test("level 1 to 5 from main shapes", () => {
  let p = profileOf(Array(12).fill(8), ["A", "D", "E"]);
  assert.deepEqual([p.level, p.label, p.main_shapes, p.hardest_shape], [1, "First chords", ["A", "D", "E"], "A"]);
  assert.equal(profileOf(Array(12).fill(8), ["A", "D", "E", "Em"]).level, 2, "all tier 1 with 4 shapes");
  assert.equal(profileOf(Array(12).fill(8), ["G", "C", "D", "Em"]).level, 2);
  p = profileOf(Array(15).fill(8), ["G", "C", "D", "Em", "Am"]);
  assert.deepEqual([p.level, p.main_shapes.length], [3, 5], "5+ open shapes");
  p = profileOf(Array(12).fill(8), ["C", "G", "F", "Am"]);
  assert.deepEqual([p.level, p.hardest_shape], [4, "F"]);
  p = profileOf(Array(12).fill(8), ["C", "G", "B", "Bm"]);
  assert.deepEqual([p.level, p.hardest_shape], [5, "B"]);
  assert.deepEqual(LEVELS.map(l => l.level), [1, 2, 3, 4, 5]);
});
test("the level counts exactly the main shapes: a rare slash shape neither adds a shape nor raises the level", () => {
  // Breakfast at Tiffany's on the shipped chart: D, A, G plus G/B (6.6%) and D/A (5.1%) used to make 5 shapes, Level 3.
  const p = profileOf([...Array(10).fill([20, 10, 5]).flat(), 25, 20], [...Array(10).fill(["D", "A", "G"]).flat(), "G/B", "D/A"]);
  assert.deepEqual([p.main_shapes, p.level], [["D", "A", "G"], 2]);
  assert.match(p.tier_reason, /^D, A, G: open chords \(hardest G, tier 2\), 3 main shapes\./);
});
test("rare shapes (under 4%) do not count; quick changes and syncopation move L1/L2 to L3", () => {
  const holds = [...Array(30).fill(8), 2], labels = [...Array(30).fill(0).map((_, i) => ["A", "D", "E"][i % 3]), "B"];
  let p = profileOf(holds, labels);
  assert.deepEqual([p.level, p.main_shapes.includes("B")], [1, false], "B at 0.8% of chord time is not a main shape");
  assert.equal(p.changes_per_min, 14.9, "8-beat holds at 120 BPM: 30 changes in 121 s of chords");
  assert.equal(p.median_hold_beats, 8);
  p = profileOf(Array(40).fill(4), ["A", "D", "E"]);
  assert.deepEqual([p.changes_per_min, p.level], [29.3, 1], "39 changes in 80 s: under the 40-a-minute line");
  p = profileOf(Array(40).fill(2), ["A", "D", "E"], { beats: 100 });
  assert.equal(p.level, 3, "median hold 2 beats at 120 BPM");
  assert.match(p.tier_reason, /median hold 2 beats/);
  assert.match(profileOf(Array(12).fill(8), ["G", "C", "D"]).tier_reason, /About 13.8 changes a minute\.$/);
  p = profileOf(Array(40).fill(3), ["A", "D", "E"], { beats: 130 });
  assert.deepEqual([p.changes_per_min, p.level], [39, 1], "39 changes a minute is under the 40 line");
  p = profileOf(Array(60).fill(2), ["A", "D", "E"], { bpm: 100 });
  assert.equal(p.level, 3, "40+ changes a minute is quick even below 120 BPM");
  assert.match(p.tier_reason, /changes a minute \(40\+\)/);
  assert.equal(profileOf(Array(12).fill(8), ["G", "C", "D"], { needsSyncopation: true }).level, 3);
  assert.equal(profileOf(Array(60).fill(2), ["C", "G", "F"], { bpm: 100 }).level, 4, "quick changes never lower a barre level");
});

// --- expected_* comparison ----------------------------------------------------------------------------
test("compareExpected: level and shape-set mismatches, order ignored; absent expectations are not checked", () => {
  const p = profileOf(Array(12).fill(8), ["A", "D", "E"]);
  assert.deepEqual(compareExpected(p, { level: 1, shapes: ["E", "D", "A"] }), { level: null, shapes: null });
  assert.deepEqual(compareExpected(p, {}), { level: null, shapes: null });
  const c = compareExpected(p, { level: 3, shapes: ["A", "D", "Asus4"] });
  assert.deepEqual(c.level, { expected: 3, built: 1 });
  assert.deepEqual([c.shapes.missing, c.shapes.extra], [["Asus4"], ["E"]]);
});

console.log(`arrangement-profile.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`${results.failed.length} arrangement-profile test(s) failed: ${results.failed.join("; ")}`);
