#!/usr/bin/env node
"use strict";
// Tests for catalogue_checks.js. Plain node + node:assert, synthetic fixtures only for the logic; the last section checks the
// founder's labels against the real (gitignored) packs and is skipped when they are absent.
//   node experiments/analysis/strumalong/catalogue_checks.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const cc = require("./catalogue_checks.js");

const REPO = path.resolve(__dirname, "../../..");
const SCRIPT = path.join(__dirname, "catalogue_checks.js");
let passed = 0;
const failures = [];
const tempRoots = [];
process.on("exit", () => { for (const root of tempRoots) fs.rmSync(root, { recursive: true, force: true }); });
function test(name, fn) {
  try { fn(); passed++; } catch (error) { failures.push(`${name}: ${error.message}`); console.error(`FAIL ${name}\n  ${error.stack.split("\n").slice(0, 4).join("\n  ")}`); }
}

// ---------------------------------------------------------------------------------------------------- synthetic builders
/** A grid of `n` beats at `bpm`, first beat at t0. */
const grid = (n, bpm = 120, t0 = 0.5) => Array.from({ length: n }, (_, i) => +(t0 + (i * 60) / bpm).toFixed(4));
/** [label, beats] pairs -> chord events on the grid (beat index = grid position of the event start). */
function chordsFromBeats(pairs, bpm = 120, t0 = 0.5, startBeat = 0) {
  const out = [];
  let beat = startBeat;
  for (const [l, len] of pairs) {
    out.push({ s: +(t0 + (beat * 60) / bpm).toFixed(4), e: +(t0 + ((beat + len) * 60) / bpm).toFixed(4), l });
    beat += len;
  }
  return out;
}
function viewOf(pairs, { bpb = 4, bpm = 120, extraBeats = 8, source = "pack", assumed = false } = {}) {
  const total = pairs.reduce((s, [, n]) => s + n, 0);
  const beats = grid(Math.ceil(total) + extraBeats, bpm);
  const chords = chordsFromBeats(pairs, bpm);
  return { id: "synthetic", source, duration: chords[chords.length - 1].e + 1, chords, beats, bpb, bpbAssumed: assumed, pulseBpm: bpm };
}
/** A four-chord loop, `loops` times, each chord `len` beats. `tweak(loopIndex, pairs)` may edit a loop's pairs. */
function loopPairs(chords, loops, len = 4, tweak = null) {
  const out = [];
  for (let i = 0; i < loops; i++) {
    let pairs = chords.map(c => [c, len]);
    if (tweak) pairs = tweak(i, pairs) || pairs;
    out.push(...pairs);
  }
  return out;
}
const EXPECT = (families, accepted = []) => ({ families, accepted, source: "test", confidence: "test" });
/** A hold-check entry in hold_homogeneity.py's shape for a view: every run of 16+ beats becomes a hold of floor(beats / 4) bars,
 *  `missed(bars)` of which fit another chord better. `shift` moves the hold starts (seconds), to fake a file from another chart. */
function holdEntryFor(view, missed, { viewSource = view.source, shift = 0 } = {}) {
  const runs = cc.familyRuns(view, 0.75).filter(r => r.key !== null && r.beats >= 16);
  return { view_source: viewSource, margin: 0.1, templates: "claim", holds: runs.map(r => {
    const bars = Math.floor(r.beats / 4);
    return { start_s: +(r.s + shift).toFixed(3), end_s: r.e, beats: Math.round(r.beats * 100) / 100, bars, missed_bars: missed(bars), held: r.label };
  }) };
}

// ---------------------------------------------------------------------------------------------------- chord families
test("familyKey reduces labels to root + major/minor/sus/power/dim/aug", () => {
  const cases = { Em7: "Em", Cmaj7: "C", "D/F#": "D", Asus4: "Asus", A5: "A5", Bdim: "Bdim", "G#m7": "G#m", Bbm: "A#m", "F#7": "F#", Cadd9: "C",
    "Dmaj7/F#": "D", Am7: "Am", A7sus4: "Asus", Gm7b5: "Gdim", E: "E", Eb: "D#", Caug: "Caug", "Cm/D#": "Cm" };
  for (const [label, key] of Object.entries(cases)) assert.equal(cc.familyKey(label), key, label);
  for (const label of ["N", "X", "", "H", null, undefined]) assert.equal(cc.familyKey(label), null, String(label));
});
test("familyMatches: same root and quality, sus and power chords are third-less, enharmonics agree", () => {
  assert.ok(cc.familyMatches("Em", "Em"));
  assert.ok(!cc.familyMatches("E", "Em"));
  assert.ok(!cc.familyMatches("G", "Em"), "relative major is a different family");
  assert.ok(cc.familyMatches("Asus", "A") && cc.familyMatches("Asus", "Am"));
  assert.ok(cc.familyMatches("D", "Dsus") && cc.familyMatches("Dm", "D5"));
  assert.ok(!cc.familyMatches("Asus", "B"));
  assert.equal(cc.familyKey("Bb"), cc.familyKey("A#"));
});
test("transposeLabel keeps quality and bass", () => {
  assert.equal(cc.transposeLabel("Em7", 2), "F#m7");
  assert.equal(cc.transposeLabel("Cadd9", 2), "Dadd9");
  assert.equal(cc.transposeLabel("G/B", 2), "A/C#");
  assert.equal(cc.transposeLabel("B", 1), "C");
  assert.equal(cc.transposeLabel("A", 0), "A");
});

// ---------------------------------------------------------------------------------------------------- chords check
test("chords: expected progression passes and reports cover 100%", () => {
  const v = viewOf(loopPairs(["Em", "C", "G", "D"], 6));
  const r = cc.checkChords(v, EXPECT(["Em", "C", "G", "D"]));
  assert.equal(r.status, "pass");
  assert.equal(r.cover, 1);
  assert.deepEqual(r.missing, []);
  assert.deepEqual(r.unexpected_main, []);
});
test("chords: N and X time is not chord time", () => {
  const v = viewOf([["N", 8], ...loopPairs(["Em", "C"], 4), ["X", 8]]);
  const r = cc.checkChords(v, EXPECT(["Em", "C"]));
  assert.equal(r.cover, 1);
  assert.equal(r.status, "pass");
});
test("chords: a wrong key fails on cover", () => {
  const v = viewOf(loopPairs(["F", "A#", "C", "Dm"], 6));
  const r = cc.checkChords(v, EXPECT(["Em", "C", "G", "D"]));
  assert.equal(r.status, "fail");
  assert.ok(r.cover < 0.5);
});
test("chords: partial cover flags; a big unexpected family flags and is named", () => {
  const v = viewOf([...loopPairs(["G", "C"], 4), ...loopPairs(["Am"], 3)]);   // Am is 12 of 44 beats = 27%
  const r = cc.checkChords(v, EXPECT(["G", "C"]));
  assert.equal(r.status, "flag");
  assert.deepEqual(r.unexpected_main, ["Am"]);
  assert.ok(r.reasons.some(x => x.includes("Am")));
});
test("chords: a missing core chord flags (the second chord of a two-chord song is gone)", () => {
  const v = viewOf(loopPairs(["Em"], 12));
  const r = cc.checkChords(v, EXPECT(["Em", "D"]));
  assert.equal(r.status, "flag");
  assert.deepEqual(r.missing, ["D"]);
});
test("chords: a missing non-core chord is reported but does not flag", () => {
  const v = viewOf(loopPairs(["C", "G", "Am", "F"], 6));
  const r = cc.checkChords(v, EXPECT(["C", "G", "Am", "F", "Dm"]));
  assert.deepEqual(r.missing, ["Dm"]);
  assert.equal(r.status, "pass");
});
test("chords: accepted extras are not 'unexpected'; sus chords satisfy their root", () => {
  const v = viewOf([...loopPairs(["A", "D"], 6), ...loopPairs(["Gsus4"], 2)]);
  const r = cc.checkChords(v, EXPECT(["A", "D"], ["G"]));
  assert.deepEqual(r.unexpected_main, []);
  assert.equal(r.cover, 1);
});
test("chords: no reference is reported as such and never fails", () => {
  const r = cc.checkChords(viewOf(loopPairs(["Em", "C"], 6)), null);
  assert.equal(r.status, "pass");
  assert.equal(r.reference, "none");
  assert.ok(r.chart_main.length);
});

// ---------------------------------------------------------------------------------------------------- tempo check
const cfg = { start_bpm: 100, tempo_min_bpm: 80, tempo_max_bpm: 120, beats_per_bar: 4 };
test("tempo: a pulse inside the prior range passes", () => {
  const v = { ...viewOf(loopPairs(["G", "C"], 6), { bpm: 100 }), pulseBpm: 100 };
  const r = cc.checkTempo(v, cfg);
  assert.equal(r.status, "pass");
  assert.equal(r.in_range, true);
});
test("tempo: outside the range flags, far outside fails", () => {
  const near = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 125 }), pulseBpm: 125 }, cfg);
  assert.equal(near.status, "flag");
  const far = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 140 }), pulseBpm: 140 }, cfg);
  assert.equal(far.status, "fail");
});
test("tempo: a pulse pinned to the range edge flags as half/double suspicion", () => {
  const r = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 80.5 }), pulseBpm: 80.5 }, cfg);
  assert.equal(r.status, "flag");
  assert.equal(r.edge_pinned, true);
});
test("tempo: double and half the start tempo flag", () => {
  const wide = { start_bpm: 60, tempo_min_bpm: 40, tempo_max_bpm: 150, beats_per_bar: 4 };
  const dbl = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 121 }), pulseBpm: 121 }, wide);
  assert.equal(dbl.status, "flag");
  assert.match(dbl.reasons.join(" "), /double/);
  const half = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 60 }), pulseBpm: 60 }, { ...wide, start_bpm: 120 });
  assert.match(half.reasons.join(" "), /half/);
});
test("tempo: no range in the fixture still compares the start tempo and says so", () => {
  const r = cc.checkTempo({ ...viewOf(loopPairs(["G", "C"], 6), { bpm: 110 }), pulseBpm: 110 }, { start_bpm: 120, beats_per_bar: 4 });
  assert.equal(r.status, "pass");
  assert.equal(r.range, null);
  assert.match(r.note, /no tempo range/);
});
test("tempo: very long median holds suspect a double-time grid; one-beat holds a half-time grid", () => {
  const long = viewOf(loopPairs(["G", "C"], 6, 16), { bpm: 100 });
  assert.match(cc.checkTempo({ ...long, pulseBpm: 100 }, cfg).reasons.join(" "), /double/);
  const short = viewOf(loopPairs(["G", "C"], 12, 1), { bpm: 100 });
  assert.match(cc.checkTempo({ ...short, pulseBpm: 100 }, cfg).reasons.join(" "), /half/);
});
test("tempo: a grid whose spacing disagrees with the pulse flags", () => {
  const v = { ...viewOf(loopPairs(["G", "C"], 6), { bpm: 120 }), pulseBpm: 100 };
  const r = cc.checkTempo(v, { start_bpm: 100, tempo_min_bpm: 80, tempo_max_bpm: 130, beats_per_bar: 4 });
  assert.equal(r.status, "flag");
  assert.match(r.reasons.join(" "), /beat grid's own spacing/);
});

// ---------------------------------------------------------------------------------------------------- plausibility
// Em for 46-ish beats, D for 3, repeated, although the song alternates every bar: the A Horse with No Name chart signature.
const HORSE = [["Em", 6], ["D", 3], ["Em", 46], ["D", 3], ["Em", 28], ["D", 3], ["Em", 28], ["D", 3], ["Em", 12], ["D", 3]];
test("plausibility: the A Horse with No Name failure fails when the audio inside the long holds changes chord", () => {
  const view = viewOf(HORSE);
  const r = cc.checkPlausibility(view, EXPECT(["Em", "D"]), holdEntryFor(view, bars => Math.ceil(bars / 2)));
  assert.equal(r.status, "fail");
  assert.equal(r.merge_signature, true);
  assert.ok(r.long_hold_share >= 0.25);
  assert.equal(r.long_hold_count, 3);
  assert.ok(r.max_hold_beats >= 46);
  assert.equal(r.hold_evidence.status, "measured");
  assert.equal(r.hold_evidence.long_holds, 3, "only the chart's 24+ beat holds are judged, not the 16-beat ones in the file");
  assert.equal(r.hold_evidence.bars, 11 + 7 + 7);
  assert.ok(r.hold_evidence.missed_change_fraction >= 0.25);
  assert.match(r.reasons.join(" "), /changes chord: in 14 of 25 bars .* merges alternating chords/);
});
test("plausibility: the chart signature alone only flags (no hold check, a real vamp, too few bars, or a stale file)", () => {
  const view = viewOf(HORSE), exp = EXPECT(["Em", "D"]);
  const none = cc.checkPlausibility(view, exp);
  assert.equal(none.status, "flag");
  assert.equal(none.merge_signature, true);
  assert.match(none.reasons.join(" "), /no hold-homogeneity evidence/);
  const vamp = cc.checkPlausibility(view, exp, holdEntryFor(view, bars => (bars > 10 ? 1 : 0)));
  assert.equal(vamp.status, "flag", "the audio stays on the held chord: Ho Hey / Stuck in the Middle");
  assert.equal(vamp.hold_evidence.missed_change_fraction, 0.04);
  assert.match(vamp.reasons.join(" "), /real vamps or breaks/);
  const borderline = cc.checkPlausibility(view, exp, holdEntryFor(view, bars => Math.floor(bars * 0.24)));
  assert.equal(borderline.status, "flag", "under 25% of bars is not enough");
  const few = cc.checkPlausibility(view, exp, { ...holdEntryFor(view, () => 2), holds: holdEntryFor(view, () => 2).holds.map(h => ({ ...h, bars: 3 })) });
  assert.equal(few.hold_evidence.bars, 9);
  assert.equal(few.status, "flag", "9 bars, all of them 'missed', is still too little evidence");
  assert.match(few.reasons.join(" "), /measured only 9 bars/);
  const otherChart = cc.checkPlausibility(view, exp, holdEntryFor(view, bars => bars, { viewSource: "exported" }));
  assert.equal(otherChart.status, "flag");
  assert.equal(otherChart.hold_evidence.status, "mismatch");
  const shifted = cc.checkPlausibility(view, exp, holdEntryFor(view, bars => bars, { shift: 3 }));
  assert.equal(shifted.status, "flag");
  assert.equal(shifted.hold_evidence.status, "mismatch");
  assert.match(shifted.reasons.join(" "), /does not match this chart/);
  const c = cc.combine({ chords: { status: "pass", reasons: [], reference: "x" }, tempo: { status: "pass", reasons: [], pulse_bpm: 100, range: [1, 2] },
    plausibility: none, consistency: { status: "pass", reasons: [], evidence: "sufficient" }, embed: { status: "pass", reasons: [] }, instrument: { status: "not run", reasons: [] } });
  assert.ok(c.not_checked.includes("plausibility: hold homogeneity (no matching hold check)"));
});
test("plausibility: hold evidence is reported for songs without the signature but never changes their status", () => {
  const pairs = [...loopPairs(["A", "D", "E", "D"], 5, 2), ["A", 38], ...loopPairs(["A", "D", "E", "D"], 5, 2)];
  const view = viewOf(pairs);
  const r = cc.checkPlausibility(view, EXPECT(["A", "D", "E"]), holdEntryFor(view, bars => bars));
  assert.equal(r.status, "flag");
  assert.equal(r.merge_signature, false);
  assert.equal(r.hold_evidence.missed_change_fraction, 1);
  const loop = viewOf(loopPairs(["Em", "C", "G", "D"], 8));
  assert.equal(cc.checkPlausibility(loop, EXPECT(["Em", "C", "G", "D"]), { view_source: "pack", holds: [] }).hold_evidence.status, "no long holds");
});
test("plausibility: one legitimate long break only flags", () => {
  const pairs = [...loopPairs(["A", "D", "E", "D"], 5, 2), ["A", 38], ...loopPairs(["A", "D", "E", "D"], 5, 2)];
  const r = cc.checkPlausibility(viewOf(pairs), EXPECT(["A", "D", "E"]));
  assert.equal(r.status, "flag");
  assert.equal(r.long_hold_count, 1);
});
test("plausibility: a long hold of a one-chord song is not suspicious", () => {
  const r = cc.checkPlausibility(viewOf([["E", 20], ["N", 2], ["E", 28], ["N", 2], ["E", 20]]), EXPECT(["E"]));
  assert.equal(r.status, "pass", "one expected family: long holds do not mean merged chords, and 28 beats is under the max-hold flag");
  assert.ok(r.long_hold_share > 0.3);
  const r2 = cc.checkPlausibility(viewOf([["E", 20], ["E7", 30]]), EXPECT(["E"]));
  assert.equal(r2.long_hold_count, 1, "E and E7 are one family, so the hold is 50 beats");
  assert.equal(r2.status, "flag", "long hold flags on max hold even for one family");
  assert.equal(r2.reasons.length, 1);
});
test("plausibility: a stray blip does not split a long hold", () => {
  const r = cc.checkPlausibility(viewOf([["G", 4], ["Em", 20], ["B", 0.3], ["Em", 20], ["G", 4]]), EXPECT(["Em", "G"]));
  assert.ok(r.max_hold_beats >= 40, `got ${r.max_hold_beats}`);
});
test("plausibility: ordinary one-bar loops pass with no long holds", () => {
  const r = cc.checkPlausibility(viewOf(loopPairs(["Em", "C", "G", "D"], 8)), EXPECT(["Em", "C", "G", "D"]));
  assert.equal(r.status, "pass");
  assert.equal(r.long_hold_share, 0);
  assert.equal(r.max_hold_beats, 4);
});
test("plausibility: N and X share flags at 20% and fails at 50%", () => {
  const some = cc.checkPlausibility(viewOf([...loopPairs(["G", "C"], 8), ["N", 14], ["X", 6]]), EXPECT(["G", "C"]));
  assert.equal(some.status, "flag");
  assert.ok(some.nx_share >= 0.2 && some.nx_share < 0.5);
  const most = cc.checkPlausibility(viewOf([...loopPairs(["G", "C"], 2), ["N", 40]]), EXPECT(["G", "C"]));
  assert.equal(most.status, "fail");
});
test("plausibility: without a reference the chart's own main families decide whether the progression alternates", () => {
  const pairs = [["Em", 6], ["D", 3], ["Em", 40], ["D", 3], ["Em", 30], ["D", 3], ["Em", 30], ["D", 3]];
  const r = cc.checkPlausibility(viewOf(pairs), null);
  assert.equal(r.progression_basis, "chart");
  assert.equal(r.status, "flag", "chart-only evidence flags but never hard-fails");
});

// ---------------------------------------------------------------------------------------------------- consistency
const LOOP = ["Em", "C", "G", "D"];
test("consistency: a steady loop is fully consistent and passes", () => {
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 12)));
  assert.equal(r.status, "pass");
  assert.equal(r.consistency, 1);
  assert.equal(r.deviants, 0);
  assert.ok(r.eligible_changes >= 40);
});
test("consistency: the Zombie signature (a chord 1 beat before 3 beats of another, elsewhere correct) is found and flagged when repeated", () => {
  // loops 4 and 9: Em runs 5 beats, then C only 3
  const tweak = (i, pairs) => (i === 4 || i === 9 ? [["Em", 5], ["C", 3], pairs[2], pairs[3]] : null);
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 14, 4, tweak)));
  assert.equal(r.deviants, 2);
  assert.equal(r.status, "flag");
  assert.deepEqual(r.deviant_list.map(d => d.change), ["Em>C", "Em>C"]);
  assert.ok(r.deviant_list.every(d => d.offset_beats > 0.9 && d.offset_beats < 1.1), "both a beat late");
  assert.deepEqual(r.deviant_list.map(d => d.from_hold_beats), [5, 5]);
  assert.deepEqual(r.deviant_list.map(d => d.to_hold_beats), [3, 3]);
  assert.match(r.reasons.join(" "), /Em>C/);
});
test("consistency: a beat EARLY change is found too, with a negative offset", () => {
  const tweak = (i, pairs) => (i === 3 || i === 8 ? [["Em", 4], ["C", 3], ["G", 5], pairs[3]] : null);
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 14, 4, tweak)));
  const early = r.deviant_list.filter(d => d.offset_beats < 0);
  assert.ok(early.length >= 2, JSON.stringify(r.deviant_list));
});
test("consistency: a single stray change is recorded but does not flag", () => {
  const tweak = (i, pairs) => (i === 5 ? [["Em", 5], ["C", 3], pairs[2], pairs[3]] : null);
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 14, 4, tweak)));
  assert.equal(r.deviants, 1);
  assert.equal(r.status, "pass");
  assert.ok(r.consistency < 1);
});
test("consistency: timing noise under half a beat is ignored", () => {
  const v = viewOf(loopPairs(LOOP, 14));
  v.chords = v.chords.map((c, i) => (i % 3 === 0 ? { ...c, s: c.s + 0.12 } : c));   // 0.12 s = 0.24 beat at 120 BPM
  const r = cc.checkConsistency(v);
  assert.equal(r.deviants, 0);
  assert.equal(r.status, "pass");
});
test("consistency: a steady one-beat slip is a phase shift, not isolated mistimings, and flags when nothing follows it", () => {
  // 10 normal loops, then one 5-beat chord and every later change sits a beat late
  const pairs = [...loopPairs(LOOP, 10), ["Em", 5], ...loopPairs(["C", "G", "D", "Em"], 4).slice(0, 15)];
  const r = cc.checkConsistency(viewOf(pairs));
  assert.equal(r.deviants, 0, "shift members are not isolated deviants");
  assert.equal(r.shifts.length, 1);
  assert.ok(r.shifts[0].offset_beats > 0.9 && r.shifts[0].offset_beats < 1.1);
  assert.equal(r.status, "flag");
  assert.match(r.reasons.join(" "), /phase slip/);
});
test("consistency: a shift the exporter's bar anchors follow is reported but not flagged", () => {
  const pairs = [...loopPairs(LOOP, 10), ["Em", 5], ...loopPairs(["C", "G", "D", "Em"], 4).slice(0, 15)];
  const v = viewOf(pairs, { source: "exported" });
  // anchors: phase 0 until the slip, phase 1 after it (as the exporter's Viterbi pass would write)
  const slipAt = v.chords.find(c => c.l === "Em" && Math.abs((c.e - c.s) * 2 - 5) < 0.01).e;
  v.rawChords = v.chords.map(c => ({ ...c, b: c.s >= slipAt - 1e-6 ? 1 : 0 }));
  v.rhythm = { bar_model: "anchored-1", bar_confident_pct: 100 };
  const r = cc.checkConsistency(v);
  assert.equal(r.shifts.length, 1);
  assert.equal(r.shifts[0].anchor_follows, true);
  assert.equal(r.status, "pass");
  assert.equal(r.exporter.anchor_phases, 2);
});
test("consistency: a change placed a half bar away is a different placement, not a mistiming", () => {
  const tweak = (i, pairs) => (i === 5 || i === 9 ? [["Em", 6], ["C", 2], pairs[2], pairs[3]] : null);
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 14, 4, tweak)));
  assert.equal(r.deviants, 0);
  assert.ok(r.half_bar_placements >= 2);
  assert.equal(r.status, "pass");
});
test("consistency: on a 2-beat bar a one-beat offset is a half bar, so nothing is reported", () => {
  const tweak = (i, pairs) => (i === 4 || i === 9 ? [["Em", 3], ["C", 1], pairs[2], pairs[3]] : null);
  const r = cc.checkConsistency(viewOf(loopPairs(LOOP, 14, 2, tweak), { bpb: 2 }));
  assert.equal(r.deviants, 0);
  assert.equal(r.status, "pass");
});
test("consistency: a song that never repeats a change gives 'insufficient' evidence and passes", () => {
  const chords = ["C", "D", "E", "F", "G", "A", "B", "Cm", "Dm", "Em", "Fm", "Gm"];
  const pairs = chords.map((c, i) => [c, 4 + (i % 2)]);
  const r = cc.checkConsistency(viewOf(pairs));
  assert.equal(r.evidence, "insufficient");
  assert.equal(r.status, "pass");
  assert.match(r.note, /not enough repeated changes/);
});
test("consistency: groups need 4 occurrences; blips and N/X boundaries do not create changes", () => {
  const pairs = [];
  for (let i = 0; i < 6; i++) pairs.push(["Em", 4], ["B", 0.3], ["Em", 0.0001 + 0], ["C", 4], ["N", 2]);
  const v = viewOf(pairs);
  const r = cc.checkConsistency(v);
  assert.equal(r.changes, 6, "only Em>C boundaries count: blips are dropped and the N breaks every C>? change");
});
test("consistency: a pair seen only three times is too thin to define a usual position", () => {
  const pairs = [];
  for (let i = 0; i < 3; i++) pairs.push(["Em", i === 2 ? 5 : 4], ["C", i === 2 ? 3 : 4], ["Am", 4], ["F", 4], ["Dm", 8]);
  const r = cc.checkConsistency(viewOf(pairs));
  assert.equal(r.deviants, 0);
  assert.equal(r.eligible_changes, 0);
  assert.equal(r.evidence, "insufficient");
});
test("consistency: an assumed meter cannot hard-fail", () => {
  // every Em>C change at a different bar position
  const pairs = [];
  for (let i = 0; i < 12; i++) pairs.push(["Em", 4 + (i % 3)], ["C", 4]);
  const r = cc.checkConsistency(viewOf(pairs, { assumed: true }));
  assert.notEqual(r.status, "fail");
});
test("consistency: unknown per-chord keys written by the exporter are reported", () => {
  const v = viewOf(loopPairs(LOOP, 8), { source: "exported" });
  v.rawChords = v.chords.map((c, i) => ({ ...c, b: 0, ...(i === 3 ? { q: 1 } : {}) }));
  assert.deepEqual(cc.checkConsistency(v).exporter.other_chord_keys, ["q"]);
});

// ---------------------------------------------------------------------------------------------------- embed
test("embed: the recorded age restriction fails; an exporter-marked unplayable upload flags; fixtures pass; otherwise unknown", () => {
  assert.equal(cc.checkEmbed("nirvana-come-as-you-are-youtube-20261011", {}).status, "fail");
  const flagged = cc.checkEmbed("x", { exported: { playable_embed: false, embed_note: "alternate used" } });
  assert.equal(flagged.status, "flag");
  assert.match(flagged.reasons.join(" "), /alternate used/);
  const ok = cc.checkEmbed("x", { candidate: { embed: "OK", fixture: "f.json" } });
  assert.equal(ok.status, "pass");
  const bad = cc.checkEmbed("x", { candidate: { embed: "blocked", fixture: "f.json" } });
  assert.equal(bad.status, "flag");
  assert.equal(cc.checkEmbed("x", { fixture_checked: { fixture: "f.json", note: "playability OK" } }).status, "pass");
  assert.equal(cc.checkEmbed("x", {}).status, "unknown");
});

// ---------------------------------------------------------------------------------------------------- instrument
const STRUM = (restrike, extra = {}) => ({ restrike_onbeat: restrike, restrike_onbeat_se: 0.01, onbeat_attacks: 300, single_onbeat: 0.05, version: "strum-features-1", ...extra });
const GUITAR = { guitar: 0.7, acoustic_guitar: 0.5, ukulele: 0.02, piano: 0.03 };
test("instrument: not run without tags, or with an entry that carries nothing", () => {
  assert.equal(cc.checkInstrument(null).status, "not run");
  assert.equal(cc.checkInstrument({ model: "m" }).status, "not run");
});
test("instrument: a strummed, guitar-led recording passes both parts", () => {
  const r = cc.checkInstrument({ model: "m", scores: GUITAR, stems: { guitar_share_of_harmonic: 0.95 }, strum: STRUM(0.72) });
  assert.equal(r.status, "pass");
  assert.equal(r.guitar_led.status, "pass");
  assert.equal(r.strummed.status, "pass");
  assert.equal(r.guitar_led.guitar_share_of_harmonic, 0.95);
  assert.equal(r.strummed.restrike_onbeat, 0.72);
  assert.equal(r.guitar, 0.7);
});
test("instrument: the Riptide signature fails (empty guitar stem and no YAMNet guitar), and technique is then not measured", () => {
  const r = cc.checkInstrument({ scores: { guitar: 0.06, ukulele: 0.11, plucked_string: 0.15 }, stems: { guitar_share_of_harmonic: 0.04 }, strum: STRUM(0.66) });
  assert.equal(r.status, "fail");
  assert.equal(r.guitar_led.status, "fail");
  assert.match(r.reasons.join(" "), /nearly empty .* not a guitar-led recording/);
  assert.equal(r.strummed.status, "not measured");
  const c = cc.combine({ chords: { status: "pass", reasons: [], reference: "x" }, tempo: { status: "pass", reasons: [], pulse_bpm: 100, range: [1, 2] },
    plausibility: { status: "pass", reasons: [] }, consistency: { status: "pass", reasons: [], evidence: "sufficient" }, embed: { status: "pass", reasons: [] }, instrument: r });
  assert.ok(c.not_checked.some(x => /strummed \(not measured/.test(x)));
});
test("instrument: one weak guitar signal only flags (Love Me Do, Sweet Caroline, Three Little Birds)", () => {
  const lowShare = cc.checkInstrument({ scores: { guitar: 0.25, harmonica: 0.28 }, stems: { guitar_share_of_harmonic: 0.14 }, strum: STRUM(0.70) });
  assert.equal(lowShare.status, "flag", "guitar share 0.14 with YAMNet still hearing guitar is borderline, not strong evidence");
  assert.match(lowShare.reasons.join(" "), /only 14% of the harmonic accompaniment/);
  const emptyStemOnly = cc.checkInstrument({ scores: GUITAR, stems: { guitar_share_of_harmonic: 0.05 }, strum: STRUM(0.70) });
  assert.equal(emptyStemOnly.status, "flag", "an empty stem that YAMNet contradicts may be a separation failure");
  const noYamnetGuitar = cc.checkInstrument({ scores: { guitar: 0.1, piano: 0.05 }, stems: { guitar_share_of_harmonic: 0.9 }, strum: STRUM(0.70) });
  assert.equal(noYamnetGuitar.status, "flag");
  assert.match(noYamnetGuitar.reasons.join(" "), /YAMNet hears little guitar/);
});
test("instrument: a low guitar share with a clear YAMNet lead fails; YAMNet alone never fails", () => {
  for (const tag of ["ukulele", "piano", "harmonica", "banjo"]) {
    const both = cc.checkInstrument({ scores: { guitar: 0.3, acoustic_guitar: 0.2, [tag]: 0.8 }, stems: { guitar_share_of_harmonic: 0.2 } });
    assert.equal(both.status, "fail", tag);
    assert.match(both.reasons.join(" "), new RegExp(`${tag} \\(0.8\\) clearly ahead`));
    const tagsOnly = cc.checkInstrument({ scores: { guitar: 0.3, [tag]: 0.8 } });
    assert.equal(tagsOnly.status, "flag", `${tag}: no stem statistics, so only a flag`);
  }
  const close = cc.checkInstrument({ scores: { guitar: 0.6, ukulele: 0.62 }, stems: { guitar_share_of_harmonic: 0.9 } });
  assert.equal(close.status, "flag");
  assert.match(close.reasons.join(" "), /ukulele \(0.62\) at least as often as guitar/);
});
test("instrument: a low on-beat restrike flags as picked-like and never fails", () => {
  for (const v of [0.63, 0.59, 0.30]) {
    const r = cc.checkInstrument({ scores: GUITAR, stems: { guitar_share_of_harmonic: 0.99 }, strum: STRUM(v) });
    assert.equal(r.status, "flag", String(v));
    assert.equal(r.strummed.status, "flag");
    assert.match(r.reasons.join(" "), /strummed: On-beat guitar attacks re-strike only/);
  }
  assert.equal(cc.checkInstrument({ scores: GUITAR, stems: { guitar_share_of_harmonic: 0.99 }, strum: STRUM(cc.T.instrument.restrike_flag) }).status, "pass");
});
test("instrument: too few on-beat attacks or no strum block leave technique unjudged", () => {
  const few = cc.checkInstrument({ scores: GUITAR, stems: { guitar_share_of_harmonic: 0.99 }, strum: STRUM(0.5, { onbeat_attacks: 20 }) });
  assert.equal(few.status, "pass");
  assert.equal(few.strummed.status, "not measured");
  const none = cc.checkInstrument({ scores: GUITAR, stems: { guitar_share_of_harmonic: 0.99 } });
  assert.equal(none.strummed.status, "not run");
  const c = cc.combine({ chords: { status: "pass", reasons: [], reference: "x" }, tempo: { status: "pass", reasons: [], pulse_bpm: 100, range: [1, 2] },
    plausibility: { status: "pass", reasons: [] }, consistency: { status: "pass", reasons: [], evidence: "sufficient" }, embed: { status: "pass", reasons: [] }, instrument: none });
  assert.ok(c.not_checked.includes("instrument: strummed (not run)"));
});
test("instrument: YAMNet's strum class is ignored (it does not separate picked from strummed)", () => {
  assert.equal(cc.checkInstrument({ scores: { ...GUITAR, strum: 0.01 }, stems: { guitar_share_of_harmonic: 0.99 } }).status, "pass");
});
test("instrument: bad scores and stale tags or stems flag", () => {
  assert.equal(cc.checkInstrument({ scores: { guitar: 7.2 } }).status, "flag");
  assert.equal(cc.checkInstrument({ model: "m", scores: "x" }).status, "flag");
  const tags = { audio_sha256: "aaa", scores: GUITAR, stems: { guitar_share_of_harmonic: 0.9 }, strum: STRUM(0.7, { audio_sha256: "aaa" }) };
  assert.equal(cc.checkInstrument(tags, "aaa").status, "pass");
  assert.equal(cc.checkInstrument(tags, "bbb").status, "flag");
  assert.equal(cc.checkInstrument(tags, null).status, "pass", "no pack hash to compare with");
  const staleStrum = cc.checkInstrument({ ...tags, strum: STRUM(0.7, { audio_sha256: "old" }) }, "aaa");
  assert.equal(staleStrum.status, "flag");
  assert.match(staleStrum.reasons.join(" "), /re-run stems_6s.py and strum_features.py/);
});

// ---------------------------------------------------------------------------------------------------- combine
test("combine: the verdict is the worst check; unknown, not run and no reference never lower it", () => {
  const base = () => ({ chords: { status: "pass", reasons: [], reference: "x" }, tempo: { status: "pass", reasons: [], pulse_bpm: 100, range: [1, 2] }, plausibility: { status: "pass", reasons: [] },
    consistency: { status: "pass", reasons: [], evidence: "sufficient" }, embed: { status: "unknown", reasons: [] }, instrument: { status: "not run", reasons: [] } });
  const pass = cc.combine(base());
  assert.equal(pass.verdict, "pass");
  assert.deepEqual(pass.not_checked, ["embed (unknown)", "instrument (not run)"]);
  const flag = base(); flag.tempo = { status: "flag", reasons: ["t"], pulse_bpm: 1, range: [1, 2] };
  assert.equal(cc.combine(flag).verdict, "flag");
  const fail = base(); fail.plausibility = { status: "fail", reasons: ["p"] }; fail.tempo = flag.tempo;
  const c = cc.combine(fail);
  assert.equal(c.verdict, "fail");
  assert.deepEqual(c.reasons, ["tempo: t", "plausibility: p"]);
  const noRef = base(); noRef.chords = { status: "pass", reasons: [], reference: "none" };
  assert.ok(cc.combine(noRef).not_checked.includes("chords (no reference)"));
});

// ---------------------------------------------------------------------------------------------------- end to end on a synthetic repo
function writeJSON(file, value) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value, null, 2)); }
function makeRepo({ shipBad = false, flagGood = false, goodTweak = null, holds = true } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "catalogue-checks-"));
  tempRoots.push(root);
  const w = (rel, v) => writeJSON(path.join(root, rel), v);
  const good = loopPairs(LOOP, 14, 4, goodTweak);
  const bad = [["Em", 6], ["D", 3], ["Em", 46], ["D", 3], ["Em", 40], ["D", 3], ["Em", 36], ["D", 3], ["Em", 12], ["D", 3]];
  const ids = { good: "good-song-youtube-20261025", bad: "bad-song-youtube-20261025" };
  const entries = { [ids.good]: good, [ids.bad]: bad };
  const manifest = { cases: [], }, rhythm = { cases: [] };
  for (const [id, pairs] of Object.entries(entries)) {
    const chords = chordsFromBeats(pairs), beats = grid(pairs.reduce((s, [, n]) => s + n, 0) + 8);
    const duration = chords[chords.length - 1].e + 2;
    manifest.cases.push({ id, name: id, recording: { id, duration_seconds: duration } });
    rhythm.cases.push({ recording: { id }, beat_times_seconds: beats, pulse_bpm: 120, beats_per_bar: 4 });
    w(`packs/p1/cases/${id}/primary.json`, { chords: chords.map(c => ({ start_seconds: c.s, end_seconds: c.e, label: c.l })) });
  }
  w("packs/p1/manifest.json", manifest);
  w("packs/p1/rhythm.json", rhythm);
  w("strumalong/data/catalogue.json", {
    packs: [{ id: "p1", kind: "additions", dir: "packs/p1", rhythm: "packs/p1/rhythm.json", metadata: "x.json", required: false }],
    exclude: shipBad ? [] : [{ recording_id: ids.bad, title: "Bad Song", reason: "founder says no" }, { recording_id: "ghost-youtube-1", title: "Ghost", reason: "typo" }],
  });
  w("experiments/fixtures/rhythm-strumalong-additions-v1.json", { recordings: {
    [ids.good]: { start_bpm: 120, tempo_min_bpm: 100, tempo_max_bpm: flagGood ? 118 : 140, beats_per_bar: 4 }, [ids.bad]: { start_bpm: 120, tempo_min_bpm: 100, tempo_max_bpm: 140, beats_per_bar: 4 } } });
  w("experiments/fixtures/strumalong-additions-candidates-v1.json", { checked: "2026-10-25: oembed 200 + embed-page playability OK with github.io Referer", first_picks: [
    { recording_id: ids.good, title: "Good Song", artist: "A", embed: null }, { recording_id: ids.bad, title: "Bad Song", artist: "B" }] });
  w("experiments/analysis/strumalong/expected-chords.json", { [ids.good]: { sounding: LOOP, confidence: "high" }, [ids.bad]: { sounding: ["Em", "D"], confidence: "medium" } });
  w("strumalong/songs/index.json", { schema: "strumalong-catalogue-2", songs: [] });
  // hold_homogeneity.py output: the bad song's long Em holds really alternate (every other bar fits D better)
  if (holds) {
    const view = { source: "pack", chords: chordsFromBeats(bad), beats: grid(bad.reduce((n, [, b]) => n + b, 0) + 8) };
    w("experiments/generated/strumalong-hold-checks.json", { [ids.bad]: holdEntryFor(view, bars => Math.ceil(bars / 2)) });
  }
  return { root, ids };
}
test("end to end: the good song passes, the A-Horse-like song fails plausibility, and a stale exclusion is reported", () => {
  const { root, ids } = makeRepo();
  const report = cc.runChecks(root);
  assert.equal(report.schema, cc.SCHEMA);
  assert.equal(report.songs.length, 2);
  const good = report.songs.find(s => s.recording_id === ids.good), bad = report.songs.find(s => s.recording_id === ids.bad);
  assert.equal(good.shipped, true);
  assert.equal(good.verdict, "pass");
  assert.equal(good.title, "Good Song");
  assert.equal(good.view_source, "pack");
  assert.equal(bad.shipped, false);
  assert.equal(bad.excluded_reason, "founder says no");
  assert.equal(bad.checks.plausibility.status, "fail");
  assert.equal(bad.verdict, "fail");
  assert.deepEqual(report.unmatched_exclusions, ["ghost-youtube-1"]);
  assert.deepEqual(report.summary, { recordings: 2, shipped: 1, excluded: 1, shipped_pass: 1, shipped_flag: 0, shipped_fail: 0, excluded_pass: 0, excluded_flag: 0, excluded_fail: 1 });
  assert.ok(report.generated_from.catalogue.sha256 && report.generated_from.packs[0].manifest_sha256);
  assert.ok(report.generated_from.files.some(f => f.path.endsWith("expected-chords.json")));
  assert.equal(report.generated_from.instrument_tags, null);
  assert.ok(report.generated_from.hold_checks && report.generated_from.hold_checks.sha256);
  assert.equal(bad.checks.plausibility.hold_evidence.status, "measured");
  assert.ok(good.not_checked.includes("embed (unknown)") === false, "the fixture-level embed check counts as evidence");
  assert.ok(good.not_checked.includes("instrument (not run)"));
});
test("end to end: without the hold-check file the A-Horse-like chart only flags", () => {
  const { root, ids } = makeRepo({ holds: false });
  const report = cc.runChecks(root);
  const bad = report.songs.find(s => s.recording_id === ids.bad);
  assert.equal(bad.checks.plausibility.status, "flag");
  assert.equal(bad.verdict, "flag");
  assert.equal(report.generated_from.hold_checks, null);
  assert.ok(bad.not_checked.includes("plausibility: hold homogeneity (no matching hold check)"));
});
test("end to end: an exported song is preferred over the pack chart, and instrument tags are applied when the file exists", () => {
  const { root, ids } = makeRepo();
  const pairs = loopPairs(LOOP, 14);
  const chords = chordsFromBeats(pairs).map(c => ({ ...c, b: 0 }));
  const song = { schema: "strumalong-song-2", id: ids.good, title: "Exported Title", artist: "Exported Artist", recording: { duration_seconds: 200 },
    rhythm: { beats_per_bar: 4, bpm: 120, bar_model: "anchored-1", bar_confident_pct: 100 }, beats: grid(pairs.reduce((s, [, n]) => s + n, 0) + 8),
    chords: chords.map(c => ({ s: c.s, e: c.e, l: c.l, b: c.b })) };
  writeJSON(path.join(root, `strumalong/songs/${ids.good}.json`), song);
  writeJSON(path.join(root, "strumalong/songs/index.json"), { songs: [{ id: ids.good, title: "Exported Title", artist: "Exported Artist", playable_embed: false, embed_note: "age-restricted; alternate" }] });
  writeJSON(path.join(root, "experiments/generated/strumalong-instrument-tags.json"), { schema: cc.INSTRUMENT_SCHEMA, model: { name: "test" }, recordings: {
    [ids.good]: { scores: { guitar: 0.2, ukulele: 0.9 }, stems: { guitar_share_of_harmonic: 0.05 }, strum: { restrike_onbeat: 0.7, onbeat_attacks: 200 } } } });
  const report = cc.runChecks(root);
  const good = report.songs.find(s => s.recording_id === ids.good);
  assert.equal(good.view_source, "exported");
  assert.equal(good.title, "Exported Title");
  assert.equal(good.exported, true);
  assert.equal(good.checks.embed.status, "flag");
  assert.equal(good.checks.instrument.status, "fail");
  assert.equal(good.checks.instrument.guitar_led.status, "fail");
  assert.equal(good.checks.instrument.strummed.status, "not measured");
  assert.equal(good.verdict, "fail");
  assert.ok(report.generated_from.instrument_tags && report.generated_from.instrument_tags.sha256);
  assert.equal(good.checks.consistency.exporter.anchor_phases, 1);
});
test("end to end: the bare map form of the instrument tags file is accepted", () => {
  const { root, ids } = makeRepo();
  writeJSON(path.join(root, "experiments/generated/strumalong-instrument-tags.json"), { [ids.good]: { model: "m", scores: { acoustic_guitar: 0.9 } } });
  const good = cc.runChecks(root).songs.find(s => s.recording_id === ids.good);
  assert.equal(good.checks.instrument.status, "pass");
  assert.equal(good.checks.instrument.model, "m");
  assert.ok(good.not_checked.includes("instrument: strummed (not run)"));
});
/** Write an exported song for the good recording: `pairs` are the shipped chords, `flagged` the start times that carry t:1. */
function writeExported(root, ids, pairs, { moves = [], flagged = [] } = {}) {
  const chords = chordsFromBeats(pairs).map(c => ({ s: c.s, e: c.e, l: c.l, ...(flagged.some(t => Math.abs(t - c.s) < 1e-3) ? { t: 1 } : {}), b: 0 }));
  const song = { schema: "strumalong-song-2", id: ids.good, title: "Good Song", artist: "A", recording: { duration_seconds: 200 },
    rhythm: { beats_per_bar: 4, bpm: 120, bar_model: "anchored-1", bar_confident_pct: 100 }, beats: grid(pairs.reduce((s, [, n]) => s + n, 0) + 8),
    chart: { corrections: moves.length ? [{ id: "auto-timing", kind: "timing", count: moves.length, note: "moved by the exporter", moves }] : [] }, chords };
  writeJSON(path.join(root, `strumalong/songs/${ids.good}.json`), song);
  writeJSON(path.join(root, "strumalong/songs/index.json"), { songs: [{ id: ids.good, title: "Good Song", artist: "A", playable_embed: true }] });
}
const beatTime = beat => +(0.5 + beat * 0.5).toFixed(4);          // grid(): first beat at 0.5 s, 120 BPM
test("auto-timing: raw mistimings that the exporter fixed are detected on the raw chart and reported as fixed", () => {
  const tweak = (i, pairs) => (i === 4 || i === 9 ? [["Em", 5], ["C", 3], pairs[2], pairs[3]] : null);
  const { root, ids } = makeRepo({ goodTweak: tweak });
  const was = [beatTime(4 * 16 + 5), beatTime(9 * 16 + 5)], at = [beatTime(4 * 16 + 4), beatTime(9 * 16 + 4)];
  writeExported(root, ids, loopPairs(LOOP, 14), { flagged: at, moves: at.map((a, i) => ({ at: a, was: was[i], from: "Em", to: "C", shift: -1, agree: "12/14" })) });
  const good = cc.runChecks(root).songs.find(s => s.recording_id === ids.good);
  const c = good.checks.consistency;
  assert.equal(c.status, "pass");
  assert.equal(c.deviants, 0, "the shipped timeline is clean");
  assert.equal(c.auto_timing.moves, 2);
  assert.equal(c.auto_timing.raw_chart.deviants, 2, "the raw chart has the Zombie signature twice");
  assert.equal(c.auto_timing.raw_chart.status, "flag");
  assert.equal(c.auto_timing.full_beat_moves, 2);
  assert.equal(c.auto_timing.moves_that_fix_a_mistiming, 2);
  assert.equal(c.auto_timing.moves_that_made_it_worse, 0);
  assert.ok(good.notes.some(n => /auto-timing moved 2/.test(n)));
  assert.equal(good.verdict, "pass");
  assert.equal(cc.exporterAutoTiming(JSON.parse(fs.readFileSync(path.join(root, `strumalong/songs/${ids.good}.json`), "utf8"))).flagged_events, 2);
  assert.match(cc.markdownTable({ songs: [good] }), /\| fixed \|/);
});
test("auto-timing: a move that pushes a correct change a beat away is flagged", () => {
  const { root, ids } = makeRepo();                                  // the raw chart is clean
  // the 'fixed' timeline moves two C entries a whole beat early, away from where every other Em>C sits
  const shipped = loopPairs(LOOP, 14, 4, (i, pairs) => (i === 4 || i === 9 ? [["Em", 3], ["C", 5], pairs[2], pairs[3]] : null));
  const at = [beatTime(4 * 16 + 3), beatTime(9 * 16 + 3)], was = [beatTime(4 * 16 + 4), beatTime(9 * 16 + 4)];
  writeExported(root, ids, shipped, { flagged: at, moves: at.map((a, i) => ({ at: a, was: was[i], from: "Em", to: "C", shift: -1, agree: "12/14" })) });
  const good = cc.runChecks(root).songs.find(s => s.recording_id === ids.good);
  const c = good.checks.consistency;
  assert.equal(c.auto_timing.moves_that_made_it_worse, 2);
  assert.equal(c.status, "flag");
  assert.equal(c.deviants, 2, "and the shipped timeline now has the two mistimings");
  assert.match(c.reasons.join(" "), /auto-timing moves put a change further/);
});
test("auto-timing: a song the exporter did not touch has no auto_timing block", () => {
  const { root, ids } = makeRepo();
  writeExported(root, ids, loopPairs(LOOP, 14));
  const c = cc.runChecks(root).songs.find(s => s.recording_id === ids.good).checks.consistency;
  assert.equal(c.auto_timing, undefined);
});
test("end to end: the report is deterministic", () => {
  const { root } = makeRepo();
  assert.equal(JSON.stringify(cc.runChecks(root)), JSON.stringify(cc.runChecks(root)));
});
test("end to end: a pack that is missing is skipped, not fatal", () => {
  const { root } = makeRepo();
  const cat = JSON.parse(fs.readFileSync(path.join(root, "strumalong/data/catalogue.json"), "utf8"));
  cat.packs.push({ id: "p2", kind: "additions", dir: "packs/nope", rhythm: "packs/nope/rhythm.json", required: false });
  writeJSON(path.join(root, "strumalong/data/catalogue.json"), cat);
  const report = cc.runChecks(root);
  assert.equal(report.songs.length, 2);
  assert.deepEqual(report.generated_from.packs.map(p => [p.id, p.available]), [["p1", true], ["p2", false]]);
});

// ---------------------------------------------------------------------------------------------------- CLI
function cli(root, args = []) {
  return spawnSync(process.execPath, [SCRIPT, ...args], { env: { ...process.env, CATALOGUE_CHECKS_REPO: root }, encoding: "utf8" });
}
test("cli: writes the report, exits 0 when no shipped song fails, and --check detects a stale file", () => {
  const { root } = makeRepo();
  const run = cli(root);
  assert.equal(run.status, 0, run.stderr);
  const file = path.join(root, "docs/STRUMALONG_CATALOGUE_CHECKS.json");
  assert.ok(fs.existsSync(file));
  assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).songs.length, 2);
  assert.match(run.stdout, /Shipped 1: 1 pass, 0 flag, 0 fail/);
  assert.equal(cli(root, ["--check"]).status, 0);
  fs.appendFileSync(file, " ");
  const stale = cli(root, ["--check"]);
  assert.equal(stale.status, 1);
  assert.match(stale.stderr, /stale/);
});
test("cli: a missing catalogue is a clear error with exit code 2", () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "catalogue-checks-empty-"));
  tempRoots.push(empty);
  const run = cli(empty, ["--no-write"]);
  assert.equal(run.status, 2);
  assert.match(run.stderr, /catalogue_checks:/);
});
test("cli: --json prints the report and --no-write leaves the disk alone", () => {
  const { root } = makeRepo();
  const run = cli(root, ["--json", "--no-write"]);
  assert.equal(run.status, 0);
  assert.equal(JSON.parse(run.stdout).schema, cc.SCHEMA);
  assert.ok(!fs.existsSync(path.join(root, "docs/STRUMALONG_CATALOGUE_CHECKS.json")));
});
test("cli: exits non-zero when a SHIPPED song fails a hard gate, and --strict also stops on a flag", () => {
  const { root } = makeRepo({ shipBad: true });
  const run = cli(root, ["--no-write"]);
  assert.equal(run.status, 1);
  assert.match(run.stderr, /shipped song\(s\) fail a hard gate: Bad Song/);
  const ok = makeRepo();
  assert.equal(cli(ok.root, ["--no-write"]).status, 0, "an excluded song may fail without stopping the run");
  const flagged = makeRepo({ flagGood: true });
  assert.equal(cli(flagged.root, ["--no-write"]).status, 0, "a flag alone does not stop the run");
  const strict = cli(flagged.root, ["--no-write", "--strict"]);
  assert.equal(strict.status, 1);
  assert.match(strict.stderr, /--strict: 1 shipped song\(s\) flagged: Good Song/);
});

// ---------------------------------------------------------------------------------------------------- the founder's labels, on the real packs
const realPacks = ["automatic-first-ten-v1", "strumalong-additions-v1", "strumalong-additions-v2"].every(p => fs.existsSync(path.join(REPO, "experiments/generated", p, "manifest.json")));
if (!realPacks) console.log("(real-pack validation skipped: gitignored packs are not present)");
else {
  const real = cc.runChecks(REPO);
  const byId = id => real.songs.find(s => s.recording_id === id);
  test("real packs: every catalogue exclusion names a recording that exists", () => {
    assert.deepEqual(real.unmatched_exclusions, []);
  });
  const haveHolds = fs.existsSync(path.join(REPO, "experiments/generated/strumalong-hold-checks.json"));
  test("real packs: A Horse with No Name (excluded, long Em holds) fails plausibility; the vamps Ho Hey and Stuck in the Middle only flag", () => {
    const s = byId("america-a-horse-with-no-name-youtube-20261025");
    assert.equal(s.shipped, false);
    assert.equal(s.checks.plausibility.merge_signature, true);
    assert.ok(s.checks.plausibility.max_hold_beats >= 46);
    assert.equal(s.checks.plausibility.status, haveHolds ? "fail" : "flag");
    for (const id of ["lumineers-ho-hey-youtube-20261025", "stealers-wheel-stuck-in-the-middle-with-you-youtube-20261025"]) {
      const p = byId(id).checks.plausibility;
      assert.equal(p.merge_signature, true, id);
      assert.equal(p.status, "flag", `${id}: the chart signature alone never fails`);
      if (haveHolds) assert.ok(p.hold_evidence.status === "measured" && p.hold_evidence.missed_change_fraction < 0.1, id);
    }
  });
  test("real packs: Come As You Are is caught by the recorded age restriction", () => {
    assert.equal(byId("nirvana-come-as-you-are-youtube-20261011").checks.embed.status, "fail");
  });
  test("real packs: Zombie's mistimed repeated changes are found on the raw chart (founder report, 25 Oct 2026)", () => {
    const inputs = cc.loadInputs(REPO);
    const rec = inputs.recordings.find(r => r.id === "cranberries-zombie-youtube-20261024");
    const raw = cc.checkConsistency(cc.buildPackView(rec, inputs));
    assert.equal(raw.status, "flag");
    assert.ok(raw.deviants >= 2, `deviants ${raw.deviants}`);
    assert.ok(raw.deviant_list.some(d => d.change === "Em>C" && d.offset_beats > 0.9 && d.from_hold_beats > 5), "an Em>C change about a beat late: the Em runs 5+ beats before C's 3");
    // What ships is either still flagged, or the exporter's auto-timing has fixed it (then the report says so).
    const shipped = byId("cranberries-zombie-youtube-20261024").checks.consistency;
    assert.ok(shipped.status === "flag" || (shipped.auto_timing && shipped.auto_timing.raw_chart.deviants > shipped.auto_timing.shipped_deviants), "shipped Zombie is flagged or reported as auto-timed");
  });
  const INSTRUMENT_NEGATIVES = ["vance-joy-riptide-youtube-20261024", "beatles-love-me-do-youtube-20261011", "radiohead-creep-youtube-20261010",
    "green-day-good-riddance-youtube-20261024", "animals-house-rising-sun-official-20261011", "white-stripes-seven-nation-army-youtube-20261011",
    "nirvana-come-as-you-are-youtube-20261011", "lynyrd-skynyrd-sweet-home-alabama-youtube-20261024"];
  const tagsPath = path.join(REPO, "experiments/generated/strumalong-instrument-tags.json");
  const haveStrum = fs.existsSync(tagsPath) && Object.values(JSON.parse(fs.readFileSync(tagsPath, "utf8")).recordings || {}).every(r => r.strum && r.stems);
  test("real packs: the instrument-only negatives are not caught by the other checks (honest limits)", () => {
    for (const id of ["radiohead-creep-youtube-20261010", "animals-house-rising-sun-official-20261011", "white-stripes-seven-nation-army-youtube-20261011",
      "lynyrd-skynyrd-sweet-home-alabama-youtube-20261024", "vance-joy-riptide-youtube-20261024"]) {
      const others = ["chords", "tempo", "plausibility", "consistency", "embed"].map(n => byId(id).checks[n].status);
      assert.ok(!others.includes("fail"), `${id} has no non-instrument failure`);
    }
  });
  if (!haveStrum) console.log("(instrument-stage validation skipped: run stems_6s.py, yamnet_tags.py and strum_features.py)");
  else {
    test("real packs: the instrument stage catches every founder-labelled instrument or technique negative (in-sample)", () => {
      for (const id of INSTRUMENT_NEGATIVES) assert.ok(["flag", "fail"].includes(byId(id).checks.instrument.status), id);
      assert.equal(byId("vance-joy-riptide-youtube-20261024").checks.instrument.guitar_led.status, "fail", "ukulele-led: empty guitar stem, no YAMNet guitar");
      assert.equal(byId("beatles-love-me-do-youtube-20261011").checks.instrument.guitar_led.status, "flag", "harmonica-led: low guitar share, but YAMNet still hears guitar");
      for (const id of INSTRUMENT_NEGATIVES.slice(2)) assert.equal(byId(id).checks.instrument.strummed.status, "flag", id);
    });
    // Fails are only "not guitar-led": Riptide (ukulele) and, since the v3 pack (26 Oct), Give Peace a Chance and Down on the
    // Corner, which catalogue.json excludes for that reason. No strummed guitar recording fails, and nothing shipped does.
    test("real packs: the instrument stage is conservative: only the three non-guitar-led recordings fail it, and A Horse with No Name (strummed) passes it", () => {
      const fails = real.songs.filter(s => s.checks.instrument.status === "fail");
      assert.deepEqual(fails.map(s => s.recording_id), ["vance-joy-riptide-youtube-20261024",
        "plastic-ono-band-give-peace-a-chance-youtube-20261026", "creedence-clearwater-revival-down-on-the-corner-youtube-20261026"]);
      for (const s of fails) {
        assert.equal(s.checks.instrument.guitar_led.status, "fail", s.recording_id);
        assert.equal(s.shipped, false, `${s.recording_id} is excluded`);
      }
      assert.equal(byId("america-a-horse-with-no-name-youtube-20261025").checks.instrument.status, "pass");
      assert.equal(byId("proclaimers-im-gonna-be-500-miles-youtube-20261025").checks.instrument.status, "pass");
    });
  }
  test("real packs: every song carries all six checks and a verdict", () => {
    for (const s of real.songs) {
      assert.deepEqual(Object.keys(s.checks), ["chords", "tempo", "plausibility", "consistency", "embed", "instrument"]);
      assert.ok(["pass", "flag", "fail"].includes(s.verdict), s.recording_id);
      assert.ok(typeof s.shipped === "boolean");
    }
    assert.equal(real.songs.length, 56);   // 44 + the 12 recordings of strumalong-additions-v3 (26 Oct): 43 shipped, 13 excluded
    assert.equal(real.summary.shipped, 43);
  });
}

if (failures.length) { console.error(`\n${failures.length} test(s) failed (${passed} passed):\n  - ${failures.join("\n  - ")}`); process.exitCode = 1; }
else console.log(`catalogue_checks.test.js: ${passed} checks passed`);
