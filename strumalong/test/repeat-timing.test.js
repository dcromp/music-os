"use strict";
// Tests for strumalong/lib/repeat-timing.js through its interface. Run: node strumalong/test/run.js (or this file directly).
// The exporter (tools/build-songs.js, drawn timing) and the catalogue checker
// (experiments/analysis/strumalong/catalogue_checks.js, played timing) both call it; see docs/adr/0001-repeat-timing-two-measures.md.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const RT = require("../lib/repeat-timing.js");
const core = require("../lib/core.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}

// The checker's settings for played timing (catalogue_checks.js T.consistency).
const PLAYED = { min_group: 4, min_majority: 0.6, inlier_beats: 0.5, deviant_beats: 0.75, half_bar_beats: 1.5, min_shift_run: 3 };
const drawn = (key, pos, extra = {}) => ({ key, pos, lenA: 4, lenB: 4, frac: -0.2, ...extra });

test("one blip line: lib/core.js QUICK_BEATS is 0.75", () => {
  assert.equal(core.QUICK_BEATS, 0.75);
});

test("contextKey: the previous two, this and the next label, padded with ^ and $", () => {
  const labels = ["G", "Em", "C", "G"];
  assert.equal(RT.contextKey(labels, 1), "^ G Em C");
  assert.equal(RT.contextKey(labels, 3), "Em C G $");
  assert.equal(RT.pairKey("E:min", "C:maj"), "E:min>C:maj");
});

test("drawn: Zombie-like group, 7 repeats on beat 0 and one a beat late", () => {
  const changes = [...Array(7)].map(() => drawn("G Em C G", 0)).concat([drawn("G Em C G", 1, { lenA: 5, lenB: 3 }), drawn("once", 2)]);
  const groups = RT.drawnGroups(changes);
  assert.equal(groups.has("once"), false, "a single change is no group");
  const g = groups.get("G Em C G");
  assert.deepEqual([g.mode, g.agree, g.members.length, g.typA, g.typB], [0, 7, 8, 4, 4]);
  assert.equal(g.share, 7 / 8);
  assert.deepEqual(RT.drawnConsistency(groups), { repeated: 8, consistent: 7, pct: 87.5 });
  assert.deepEqual(RT.drawnOffset(1, g.mode, 4), { d: 1, shift: -1 }, "one beat late moves one beat earlier");
  assert.deepEqual(RT.drawnOffset(3, g.mode, 4), { d: 3, shift: 1 });
  assert.equal(RT.drawnOffset(2, g.mode, 4).shift, 0, "half a bar away is not a one-beat move");
});

test("drawn: ties go to the lowest position; groups under 3 repeats do not count toward consistency", () => {
  const groups = RT.drawnGroups([drawn("a", 2), drawn("a", 1)]);
  assert.equal(groups.get("a").mode, 1);
  assert.deepEqual(RT.drawnConsistency(groups), { repeated: 0, consistent: 0, pct: 100 });
});

test("played: a change a beat from its cluster is a deviant; a 0.3-beat wobble and a half-bar placement are not", () => {
  const at = (t, pos) => ({ t, key: "G>Em", pos });
  const changes = [at(1, 0.1), at(2, 3.9), at(3, 0.0), at(4, 0.2), at(5, 0.3), at(6, 1.0), at(7, 2.0)];
  const j = RT.playedJudgement(changes, 4, PLAYED);
  assert.equal(j.groupCount, 1);
  assert.equal(j.eligible.length, 7);
  assert.deepEqual(j.isolated.map(e => e.t), [6], "only the change about a beat off");
  assert.equal(j.halfBar, 1, "pos 2 is a half-bar placement");
  assert.ok(Math.abs(j.consistency - 6 / 7) < 1e-12);
});

test("played: three consecutive deviants one way are a shift, not isolated mistimings", () => {
  const at = (t, pos) => ({ t, key: "A>D", pos });
  const changes = [at(1, 0), at(2, 0), at(3, 0), at(4, 0), at(5, 0), at(6, 1), at(7, 1.1), at(8, 0.9)];
  const j = RT.playedJudgement(changes, 4, PLAYED);
  assert.equal(j.isolated.length, 0);
  assert.equal(j.shifts.length, 1);
  assert.equal(j.shifts[0].changes, 3);
  assert.deepEqual(j.shiftStarts, [5]);
  assert.equal(j.consistency, 1);
});

test("played: a group without a 60% majority, or under 4 changes, is not eligible", () => {
  const at = (t, pos, key = "C>G") => ({ t, key, pos });
  const j = RT.playedJudgement([at(1, 0), at(2, 1), at(3, 2), at(4, 3), at(5, 0, "x"), at(6, 0, "x"), at(7, 0, "x")], 4, PLAYED);
  assert.equal(j.groupCount, 0);
  assert.equal(j.consistency, null);
});

test("the two measures differ on a rounding snap: drawn calls it a beat off, played calls it noise", () => {
  // Five repeats at grid position 0.45 (drawn on beat 0) and one at 0.55 (drawn on beat 1): 0.1 beat apart in the grid.
  const grid = [0.45, 0.45, 0.45, 0.45, 0.45, 0.55];
  const d = RT.drawnGroups(grid.map(p => drawn("k", Math.round(p))));
  assert.equal(RT.drawnConsistency(d).pct, 83.3);
  const p = RT.playedJudgement(grid.map((pos, t) => ({ t, key: "k", pos })), 4, PLAYED);
  assert.equal(p.consistency, 1);
});

test("correction: one auto-timing entry, read back the same way by the checker and the app", () => {
  assert.equal(RT.correction([]), null);
  const moves = [{ at: 133.2, was: 133.933, from: "Em", to: "C", shift: -1, agree: "7/8", extra: 1 },
    { at: 10, was: 9.9, from: "G", to: "Em", shift: 1, agree: "3/4" }];
  const c = RT.correction(moves);
  assert.deepEqual(Object.keys(c), ["id", "kind", "count", "start", "end", "note", "moves"]);
  assert.deepEqual([c.id, c.kind, c.count, c.start, c.end], ["auto-timing", "timing", 2, 9.9, 133.933]);
  assert.equal(c.note, "2 chord changes moved by one beat to match the other repeats of the same sequence (automatic; raw chart unchanged)");
  assert.deepEqual(Object.keys(c.moves[0]), ["at", "was", "from", "to", "shift", "agree"], "only the documented move fields");
  assert.match(RT.correction(moves.slice(0, 1)).note, /^1 chord change moved/);

  const song = { chart: { corrections: [{ id: "x", start: 1, end: 2, from: "A", to: "B" }, c] }, chords: [{ s: 0, e: 1, l: "G", t: 1 }] };
  const read = RT.readCorrections(song);
  assert.deepEqual([read.moves, read.flagged, read.note, read.list.length, read.entries.length], [2, 1, c.note, 2, 1]);
  assert.equal(RT.readCorrections({ chart: { corrections: [] }, chords: [{ s: 0, e: 1, l: "G" }] }), null);

  assert.equal(RT.describe(song.chart.corrections[0]), null, "a label correction is not a timing entry");
  assert.deepEqual(RT.describe(c).moves.map(m => m.direction), ["earlier", "later"]);
  assert.equal(RT.describe({ kind: "timing" }).note, "Some chord changes moved by one beat");
});

test("real data: every exported auto-timing entry is exactly what correction() builds from its moves", () => {
  const dir = path.join(__dirname, "..", "songs");
  let n = 0;
  for (const f of fs.readdirSync(dir).filter(name => name.endsWith(".json") && name !== "index.json")) {
    const song = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    for (const c of (song.chart && song.chart.corrections) || []) {
      if (!RT.describe(c)) continue;
      n++;
      assert.deepEqual(c, RT.correction(c.moves), f);
      assert.equal(RT.readCorrections(song).flagged, c.count, `${f}: one t flag per move`);
    }
  }
  console.log(`     (${n} auto-timing entries)`);
});

console.log(`repeat-timing.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`repeat-timing.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
