"use strict";
// Unit tests for the pure helpers in strumalong/tools/build-songs.js (bar-phase vote, library chips).
// Run: node strumalong/test/run.js (or this file directly). Requiring the exporter does not build anything.
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const EXPORTER = path.join(__dirname, "..", "tools", "build-songs.js");
const REVIEW_APP = path.join(__dirname, "..", "..", "experiments", "review", "app.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}

if (!fs.existsSync(REVIEW_APP)) {
  console.log("exporter.test.js: SKIP - experiments/review/app.js not found (the exporter needs it)");
} else {
  const { barPhaseVote, barPhaseConfident, coreShapes } = require(EXPORTER);
  const grid = (first, step, count) => Array.from({ length: count }, (_, i) => +(first + step * i).toFixed(6));
  const event = (start, label = "A") => ({ start_seconds: start, end_seconds: start + 0.5, label });

  // --- barPhaseVote / barPhaseConfident ------------------------------------------------------
  test("barPhaseVote: 2/4 starts 0.34 beat after even beats vote residue 0, confident", () => {
    const beats = grid(1, 0.5, 60); // beat i at 1 + 0.5 i s
    const events = [];
    for (let i = 2; i < 56; i += 4) events.push(event(beats[i] + 0.34 * 0.5)); // +0.34 beat: outside the old 0.125-beat window
    const vote = barPhaseVote(beats, events, 2);
    assert.equal(vote.phase, 0);
    assert.equal(vote.share, 1);
    assert.equal(vote.votes, events.length);
    assert.equal(vote.eligible, events.length);
    assert.ok(vote.votes >= 8);
    assert.equal(barPhaseConfident(vote, false), true);
    assert.equal(barPhaseConfident(vote, true), false, "an assumed meter is never confident");
  });
  test("barPhaseVote: only 2 eligible starts is not confident", () => {
    const beats = grid(1, 0.5, 40);
    const events = [event(0.2), event(beats[4]), event(beats[8]), event(beats[12], "N"), event(beats[16], "X"), event(beats[39] + 0.2)];
    const vote = barPhaseVote(beats, events, 4);
    assert.deepEqual(vote, { phase: 0, share: 1, votes: 2, eligible: 2 }, "N, X and starts outside the grid do not vote");
    assert.equal(barPhaseConfident(vote, false), false);
  });
  test("barPhaseVote: a 50/50 residue split keeps the lowest residue and is not confident", () => {
    const beats = grid(1, 0.5, 80);
    const events = [];
    for (let k = 0; k < 6; k++) { events.push(event(beats[4 * k + 3])); events.push(event(beats[4 * k + 41] + 0.1)); } // residues 3 and 1
    const vote = barPhaseVote(beats, events, 4);
    assert.equal(vote.phase, 1, "tie keeps the lowest residue");
    assert.equal(vote.share, 0.5);
    assert.equal(vote.votes, 12);
    assert.equal(barPhaseConfident(vote, false), false);
  });
  test("barPhaseVote: rounding follows the app (a start 0.6 beat late votes for the next beat)", () => {
    const beats = grid(0, 1, 50);
    const events = Array.from({ length: 10 }, (_, k) => event(4 * k + 1.6)); // round(4k + 1.6) = 4k + 2
    const vote = barPhaseVote(beats, events, 4);
    assert.equal(vote.phase, 2);
    assert.equal(barPhaseConfident(vote, false), true);
    assert.deepEqual(barPhaseVote([1], events, 4), { phase: 0, share: 0, votes: 0, eligible: 0 });
  });

  // --- coreShapes --------------------------------------------------------------------------------
  const chord = (s, e, l) => ({ s, e, l });
  test("coreShapes: ordered by seconds held, rare shapes and rare slash shapes dropped, at most 6", () => {
    const chords = [
      chord(0, 2, "N"), chord(2, 12, "G"), chord(12, 32, "B"), chord(32, 34, "Cm/D#"), // Cm/D# 2/97 s: rare slash
      chord(34, 64, "C"), chord(64, 65, "F"), chord(65, 80, "Cm"), chord(80, 81, "X"), chord(81, 101, "G7"),
    ];
    // G + G7 -> G (30 s), B 20, Cm 15, C 30, F 1 (1%), Cm/D# 2 (2%): ties keep first appearance (G before C).
    assert.deepEqual(coreShapes(chords, 0), ["G", "C", "B", "Cm"]);
  });
  test("coreShapes: a slash shape needs 10% of chord time; plain shapes need 3%", () => {
    const chords = [chord(0, 80, "A"), chord(80, 88, "G/B"), chord(88, 92, "D"), chord(92, 100, "D/F#"), chord(100, 112, "E/G#")];
    // total 112: G/B 7.1% (dropped), D 3.6% (kept), D/F# 7.1% (dropped), E/G# 10.7% (kept)
    assert.deepEqual(coreShapes(chords, 0), ["A", "E/G#", "D"]);
  });
  test("coreShapes: capo shapes and the 6-chip cap", () => {
    const labels = ["A", "B", "C#m", "D", "E", "F#m", "G#m"];
    const chords = labels.map((l, i) => chord(i * 10, i * 10 + 10 - i, l)); // shorter each time
    assert.deepEqual(coreShapes(chords, 2), ["G", "A", "Bm", "C", "D", "Em"]);
    assert.deepEqual(coreShapes([chord(0, 1, "N")], 0), []);
  });
}

console.log(`exporter.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`exporter.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
