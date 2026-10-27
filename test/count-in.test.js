"use strict";
// Tests for strumalong/lib/count-in.js: planning the count and scheduling its clicks.
// Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const { plan, due, LEAD_S } = require("../lib/count-in.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}
const close = (actual, expected, eps = 1e-9) => assert.ok(Math.abs(actual - expected) <= eps, `${actual} != ${expected}`);

// 120 bpm, first beat at 0.5 s, bars start on beats 1, 5, 9 ... (bar_phase 1).
function song(extra = {}) {
  return {
    rhythm: { bpm: 120, beats_per_bar: 4, bar_phase: 1, bar_phase_confident: true },
    beats: Array.from({ length: 100 }, (_, i) => 0.5 + 0.5 * i),
    chords: [{ s: 0, e: 50, l: "A" }],
    ...extra,
  };
}

test("mid-song: the count is the bar before the next bar start, then a fading bar of the music", () => {
  const p = plan(song(), 10.2); // beat 19 is at 10.0, 20 at 10.5; the next bar start is beat 21 (11.0)
  close(p.downbeat, 11.0);
  assert.deepEqual(p.count.map(c => c.t), [9.0, 9.5, 10.0, 10.5]);
  assert.deepEqual(p.count.map(c => c.n), [1, 2, 3, 4]);
  assert.deepEqual(p.fade.map(c => c.t), [11.0, 11.5, 12.0, 12.5]);
  assert.ok(p.fade.every((c, i) => c.n === 0 && c.gain < 1 && (i === 0 || c.gain < p.fade[i - 1].gain)));
  close(p.startAt, 9.0 - LEAD_S);
  assert.equal(p.clicks.length, 8);
});

test("a start just after a bar start still lands on that bar", () => {
  close(plan(song(), 11.05).downbeat, 11.0);
  close(plan(song(), 11.2).downbeat, 13.0);
});

test("from the very start the count runs before the video's 0 (pre-roll)", () => {
  const p = plan(song(), 0);
  close(p.downbeat, 1.0); // beat 1
  assert.deepEqual(p.count.map(c => c.t), [-1.0, -0.5, 0, 0.5]); // the grid extended backwards by its own spacing
  assert.ok(p.startAt < 0);
});

test("bar anchors on the chords decide where the count's 1 lands", () => {
  const s = song({ chords: [{ s: 0, e: 50, l: "A", b: 3 }] }); // bars start on beats 3, 7, 11 ...
  close(plan(s, 0.3).downbeat, 2.0); // beat 3
  close(plan(s, 0).downbeat, 0.0);   // beat -1, the grid extended back to 0.0, is also a bar start
});

test("3/4 counts three beats", () => {
  const p = plan(song({ rhythm: { bpm: 120, beats_per_bar: 3, bar_phase: 0, bar_phase_confident: true } }), 5);
  assert.deepEqual(p.count.map(c => c.n), [1, 2, 3]);
  assert.equal(p.fade.length, 3);
});

test("no beat grid falls back to the tempo; no tempo means no count-in", () => {
  const p = plan({ rhythm: { bpm: 60, beats_per_bar: 4 }, beats: [] }, 3.5);
  close(p.downbeat, 4);
  assert.deepEqual(p.count.map(c => c.t), [0, 1, 2, 3]);
  assert.equal(plan({ rhythm: {}, beats: [] }, 3), null);
  assert.equal(plan(song(), NaN), null);
});

test("due: clicks within the lookahead fire once, late ones are skipped, done after the last", () => {
  const clicks = plan(song(), 10.2).clicks; // 9.0 ... 12.5
  let r = due(clicks, 0, 8.95, 0.1, 0.05);
  assert.deepEqual(r.fire.map(f => f.click.t), [9.0]);
  close(r.fire[0].delay, 0.05);
  r = due(clicks, r.next, 8.97, 0.1, 0.05); // nothing new yet
  assert.equal(r.fire.length, 0);
  r = due(clicks, r.next, 10.3, 0.1, 0.05); // the clock jumped: 9.5 and 10.0 are too late, skipped
  assert.deepEqual(r.fire.map(f => f.click.t), []);
  assert.equal(r.next, 3);
  r = due(clicks, r.next, 12.45, 0.1, 0.05);
  assert.deepEqual(r.fire.map(f => f.click.t), [12.5]);
  assert.equal(r.done, true);
});

console.log(`count-in.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`count-in.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
