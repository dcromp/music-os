"use strict";
// Unit tests for the pure helpers in strumalong/tools/build-songs.js: bar-phase vote, library chips, the bar model
// (anchors and its objective), difficulty levels, default patterns and the catalogue config; plus real-data
// properties over the built songs in strumalong/songs.
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
  const X = require(EXPORTER);
  const { barPhaseVote, barPhaseConfident, coreShapes } = X;
  const core = require(path.join(__dirname, "..", "lib", "core.js"));
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

  // --- bar model --------------------------------------------------------------------------------
  // Synthetic song on a 120 BPM grid (beat i at 0.5 i s) with chord holds given in beats.
  function songFromHolds(holds, opts = {}) {
    const beats = grid(0, 0.5, opts.beats || 200);
    let beat = opts.start || 0;
    const labels = opts.labels || ["G", "C", "D", "Em"];
    const chords = holds.map((n, i) => { const c = { s: beat * 0.5, e: (beat + n) * 0.5, l: labels[i % labels.length] }; beat += n; return c; });
    const bpb = opts.bpb || 4;
    const vote = barPhaseVote(beats, chords.map(c => ({ start_seconds: c.s, label: c.l })), bpb);
    return { capo: 0, beats, chords, rhythm: { bpm: 120, beats_per_bar: bpb, beats_per_bar_assumed: Boolean(opts.assumed), meter_label: "4/4 assumed",
      bar_phase: vote.phase, bar_phase_confident: barPhaseConfident(vote, Boolean(opts.assumed)) } };
  }
  const anchored = song => { const copy = JSON.parse(JSON.stringify(song)); X.applyBarAnchors(copy); return copy; };
  const counter = { counts: ["1", "2", "3", "4"], strokes: ["D", "D", "D", "D"] };

  test("bar model: steady one-bar changes keep one confident phase (the old global phase)", () => {
    const song = songFromHolds(Array(16).fill(4), { start: 1 });
    const result = X.barAnchors(song);
    assert.deepEqual(result.runs.map(r => [r.mode, r.state, r.confident]), [["phase", 1, true]]);
    const after = anchored(song), m = X.barMetrics(after);
    assert.deepEqual([m.on_bar, m.weird, m.split, m.restarts, m.approx_pct], [100, 0, 0, 0, 0]);
    assert.ok(after.chords.every(c => c.b === 1 && c.a === undefined));
    assert.deepEqual(X.barMetrics(song), m, "same bars as the song-wide phase");
  });
  test("bar model: a one-beat slip in the grid switches to a local phase instead of drawing every later bar mid-chord", () => {
    const song = songFromHolds([...Array(10).fill(4), 5, ...Array(12).fill(4)]);
    const before = X.barMetrics(song), after = X.barMetrics(anchored(song));
    assert.ok(before.split + before.weird >= 10, `the song-wide phase draws many mid-chord lines (${before.split} split, ${before.weird} weird)`);
    assert.equal(after.split, 0);
    assert.ok(after.weird <= 1, "at most the slipped 5-beat hold keeps an odd line");
    assert.equal(after.restarts, 1, "the count restarts once, at the slip");
    const runs = X.barAnchors(song).runs;
    assert.deepEqual(runs.map(r => [r.state, r.confident]), [[0, true], [1, true]]);
  });
  test("bar model: half-bar changes (G 4, C 2, D 2) put the bar line on G, not between C and D", () => {
    const song = songFromHolds(Array(8).fill([4, 2, 2]).flat(), { start: 2, labels: ["G", "C", "D"] });
    const after = anchored(song), m = X.barMetrics(after);
    assert.ok(after.chords.every(c => c.b === 2), "G starts every bar");
    assert.deepEqual([m.on_bar_or_half, m.weird, m.split, m.approx_pct], [100, 0, 0, 0]);
    assert.equal(m.on_bar, 66.7);
  });
  test("bar model: no steady phase falls back to hold-relative bars (each change starts a bar, approx)", () => {
    const holds = Array(24).fill(3); // a three-beat song on a four-beat assumption: no 4-beat phase fits
    const song = songFromHolds(holds, { start: 1 });
    const after = anchored(song), m = X.barMetrics(after), before = X.barMetrics(song);
    const result = X.barAnchors(song);
    assert.deepEqual(result.runs.map(r => [r.mode, r.confident]), [["hold", false]]);
    assert.deepEqual([before.weird, before.split, m.weird, m.split, m.approx_pct], [12, 12, 0, 0, 100]);
    assert.equal(m.restarts, 23, "the count restarts at every change");
    let beat = 1;
    for (let i = 0; i < holds.length; i++) {
      const hold = result.anchors[i];
      if (hold.mode === "hold") {
        assert.equal(hold.approx, true);
        assert.equal(core.strumStep(after, counter, beat * 0.5 + 0.01), 0, `hold ${i} at beat ${beat}: the count restarts at 1`);
        assert.ok(core.barAnchorAt(after, beat).bar);
      }
      beat += holds[i];
    }
  });
  test("bar model: an assumed meter never claims confident bars; quick blips and N follow their neighbours", () => {
    const song = songFromHolds(Array(16).fill(4), { assumed: true });
    assert.ok(anchored(song).chords.every(c => c.a === 1));
    const blip = songFromHolds([4, 4, 4, 4, 4, 4, 4, 4, 4, 4], { start: 1 });
    blip.chords.splice(3, 0, { s: blip.chords[2].e - 0.2, e: blip.chords[2].e, l: "A" });
    blip.chords[2].e = +(blip.chords[2].e - 0.2).toFixed(3);
    blip.chords.unshift({ s: 0, e: 0.5, l: "N" });
    const after = anchored(blip);
    assert.ok(after.chords.every(c => c.b === 1), "blip and N take the run's phase");
  });
  test("bar model: Full view (no merges) draws the same bars as Simple view", () => {
    const song = songFromHolds(Array(12).fill(4), { start: 1, labels: ["G", "G7", "C", "D"] }); // G + G7 merge in Simple
    const after = anchored(song);
    for (const quality of ["core", "full"]) {
      const tl = core.buildTimeline(after, { quality });
      for (const ev of tl) {
        const cue = core.cueAt(tl, after, ev.s + 0.01), base = Math.round(cue.now.startBeat);
        for (const j of cue.now.barBefore) assert.ok(core.barAnchorAt(after, base + j).bar);
      }
    }
    assert.equal(core.buildTimeline(after, { quality: "full" }).length, 12);
  });

  // --- timing fix (repetition consistency) ----------------------------------------------------------
  // Chords from holds in beats on the 120 BPM grid, each change `lag` seconds before its beat (CREMA-like).
  function loopSong(holds, labels, opts = {}) {
    const song = songFromHolds(holds, { start: 1, labels, ...opts });
    const lag = opts.lag === undefined ? 0.05 : opts.lag;
    song.chords.forEach((c, i) => { if (i) c.s = +(c.s - lag).toFixed(3); if (i + 1 < song.chords.length) c.e = +(c.e - lag).toFixed(3); });
    return song;
  }
  const EmCGD = ["Em", "C", "G", "D"];
  const holdCounts = song => X.gridHolds(song).filter(h => h.inGrid).map(h => h.count);
  const fixed = (song, opts) => { const copy = JSON.parse(JSON.stringify(song)); const result = X.applyTimingFix(copy, opts); return { copy, result }; };

  test("timing fix: a loop with one late and one early change is moved onto the other repeats; labels unchanged", () => {
    const holds = Array(40).fill(4);
    holds[12] = 5; holds[13] = 3;  // repeat 4: C one beat late (Em 5, C 3)
    holds[25] = 3; holds[26] = 5;  // repeat 7: G one beat early (C 3, G 5)
    const song = loopSong(holds, EmCGD);
    const { copy, result } = fixed(song);
    assert.deepEqual(result.moves.map(m => [m.from, m.to, m.shift]), [["Em", "C", -1], ["C", "G", 1]]);
    assert.deepEqual(holdCounts(copy), Array(40).fill(4), "every hold is a bar again");
    assert.deepEqual(copy.chords.map(c => c.l), song.chords.map(c => c.l), "labels never change");
    assert.equal(copy.chords.length, song.chords.length);
    assert.deepEqual(copy.chords.map((c, i) => (c.t ? i : -1)).filter(i => i >= 0), [13, 26], "t:1 on the chords whose start moved");
    for (const m of result.moves) {
      const i = copy.chords.findIndex(c => c.s === m.at);
      assert.equal(copy.chords[i - 1].e, m.at, "the previous chord ends where the moved one starts");
      assert.equal(m.at, +(0.5 * Math.round(m.at / 0.5) - 0.05).toFixed(3), "moved change keeps the repeats' 50 ms lead on its beat");
      assert.ok(Math.abs(m.at - m.was) <= 0.5 + 1e-9, "never more than one beat in time");
    }
    assert.deepEqual(result.moves.map(m => m.agree), ["8/9", "9/10"], "repeats with the same four-chord context (the first has no previous chord)");
    const entry = X.timingCorrection(result.moves);
    assert.deepEqual([entry.id, entry.kind, entry.count, entry.moves.length], ["auto-timing", "timing", 2, 2]);
    assert.equal(entry.note, "2 chord changes moved by one beat to match the other repeats of the same sequence (automatic; raw chart unchanged)");
    assert.equal(X.timingCorrection([]), null);
    const before = X.timingConsistency(song), after = X.timingConsistency(copy, { anchors: X.barAnchors(song).anchors });
    assert.ok(before.pct < 100 && after.pct === 100, `${before.pct} -> ${after.pct}`);
  });
  test("timing fix: idempotent; run on its own output it moves nothing", () => {
    const holds = Array(40).fill(4);
    holds[12] = 5; holds[13] = 3; holds[13 + 8] = 5; holds[14 + 8] = 3;
    const once = fixed(loopSong(holds, EmCGD)).copy;
    const twice = fixed(once);
    assert.equal(twice.result.moves.length, 0);
    assert.deepEqual(twice.copy.chords, once.chords);
    assert.deepEqual(twice.result.left, []);
  });
  test("timing fix: no clear majority, too few repeats, or two beats off: untouched", () => {
    const split = Array(32).fill(4);                     // 8 repeats, C late in 4 of them: 4 vs 4
    for (const r of [1, 3, 5, 7]) { split[4 * r] = 5; split[4 * r + 1] = 3; }
    let { copy, result } = fixed(loopSong(split, EmCGD));
    assert.equal(result.moves.length, 0);
    assert.ok(result.left.length && result.left.every(m => /no clear majority/.test(m.reason)), JSON.stringify(result.left));
    assert.deepEqual(holdCounts(copy), holdCounts(loopSong(split, EmCGD)));
    const three = Array(16).fill(4); three[4] = 5; three[5] = 3;   // 3 repeats of D Em C G, 2 agree: below minAgree (3)
    ({ result } = fixed(loopSong(three, EmCGD)));
    assert.equal(result.moves.length, 0);
    assert.match(result.left[0].reason, /2 of 3 repeats agree/);
    const two = Array(40).fill(4); two[12] = 6; two[13] = 2;       // C two beats late: a different arrangement
    ({ result } = fixed(loopSong(two, EmCGD)));
    assert.equal(result.moves.length, 0);
    assert.match(result.left[0].reason, /2 beats from the other repeats/);
  });
  test("timing fix: never leaves a hold or the shortened chord under one beat, never touches corrected chords", () => {
    // G (4 beats) then a one-beat G7 merge into one Core hold of 5 before a late C: moving C would empty the G7.
    const song = loopSong(Array(40).fill(4), EmCGD);
    const late = song.chords[13], g = song.chords[12];
    song.chords.splice(13, 0, { s: +(late.s).toFixed(3), e: +(late.s + 0.5).toFixed(3), l: "Em7" });
    late.s = +(late.s + 0.5).toFixed(3);
    assert.equal(holdCounts(song)[12], 5, "Em + Em7 is one 5-beat Em hold in Simple view");
    let { result } = fixed(song);
    assert.equal(result.moves.length, 0);
    assert.match(result.left[0].reason, /shortened chord would drop below one beat/);
    assert.ok(g.l === "Em");
    const corrected = loopSong(Object.assign(Array(40).fill(4), { 12: 5, 13: 3 }), EmCGD);
    corrected.chords[13].c = 1;
    ({ result } = fixed(corrected));
    assert.equal(result.moves.length, 0);
    assert.match(result.left[0].reason, /corrected chord/);
    const off = fixed(loopSong(Object.assign(Array(40).fill(4), { 12: 5, 13: 3 }), EmCGD), { enabled: false });
    assert.equal(off.result.moves.length, 0, "catalogue timing_fix_off");
    assert.match(off.result.left[0].reason, /timing fix off/);
    const twoFour = loopSong(Object.assign(Array(40).fill(4), { 12: 5, 13: 3 }), EmCGD, { bpb: 2 });
    assert.equal(fixed(twoFour).result.moves.length, 0, "two beats per bar: one beat either way is ambiguous");
  });
  test("timing fix: a beat-grid slip (every later change shifted) is not 'fixed'", () => {
    const holds = [...Array(24).fill(4), 5, ...Array(23).fill(4)];
    const song = loopSong(holds, EmCGD);
    const { copy, result } = fixed(song);
    assert.equal(result.moves.length, 0, JSON.stringify(result.moves));
    assert.deepEqual(copy.chords, song.chords);
  });
  test("timing fix: under a confident bar phase a change is never moved off the bar or half-bar line", () => {
    // Bars of G 4, C 4, D 4, Em 3 + A 1 (A pushed onto beat 4): 80% of changes on the bar, a confident phase.
    // One repeat plays Em 2 + A 2 (A on the half-bar); the other repeats round A to beat 4.
    const unit = [4, 4, 4, 3, 1], labels = ["G", "C", "D", "Em", "A"];
    const holds = Array(10).fill(unit).flat();
    holds[5 * 4 + 3] = 2; holds[5 * 4 + 4] = 2;
    const { result } = fixed(loopSong(holds, labels));
    assert.equal(result.moves.length, 0);
    assert.ok(result.left.some(m => /confident bar phase/.test(m.reason)), JSON.stringify(result.left));
    const guess = fixed(loopSong(holds, labels, { assumed: true })); // assumed meter: the bars are a guess, the repeats decide
    assert.deepEqual(guess.result.moves.map(m => [m.from, m.to, m.shift]), [["Em", "A", 1]]);
  });
  test("readCatalogue: timing_fix_off entries need a recording_id and a reason", () => {
    const base = { schema: "strumalong-catalogue-config-1", packs: [{ id: "p", kind: "additions", dir: "d", rhythm: "r", metadata: "m" }] };
    const os = require("node:os");
    const cfgFile = obj => { const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "strumalong-cfg-")), "catalogue.json"); fs.writeFileSync(f, JSON.stringify(obj)); return f; };
    assert.deepEqual([...X.readCatalogue(cfgFile({ ...base, timing_fix_off: [{ recording_id: "a", reason: "r" }] })).timingOff.keys()], ["a"]);
    assert.throws(() => X.readCatalogue(cfgFile({ ...base, timing_fix_off: [{ recording_id: "a" }] })), /timing_fix_off/);
    assert.equal(X.readCatalogue(cfgFile(base)).timingOff.size, 0);
  });

  // --- difficulty -------------------------------------------------------------------------------
  test("shapeTier: lead tiers, slash shapes by root, everything else tier 4", () => {
    assert.deepEqual(["A", "Em", "Asus4", "G", "C", "B7", "G/B", "D/F#", "F", "Bm", "F#m", "B", "Cm", "Bb", "G#m", "Fm", "C/E", "F/C", "D/A"].map(X.shapeTier),
      [1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 2, 3, 1]);
  });
  const levelOf = (holds, labels, opts = {}) => {
    const song = songFromHolds(holds, { labels, ...opts });
    if (opts.bpm) song.rhythm.bpm = opts.bpm;
    return X.difficultyOf(song, opts);
  };
  test("difficultyOf: levels 1 to 5 from main shapes", () => {
    let d = levelOf(Array(12).fill(8), ["A", "D", "E"]);
    assert.deepEqual([d.level, d.label, d.main_shapes, d.hardest_shape], [1, "First chords", ["A", "D", "E"], "A"]);
    assert.equal(levelOf(Array(12).fill(8), ["A", "D", "E", "Em"]).level, 2, "all tier 1 with 4 shapes");
    assert.equal(levelOf(Array(12).fill(8), ["G", "C", "D", "Em"]).level, 2);
    d = levelOf(Array(15).fill(8), ["G", "C", "D", "Em", "Am"]);
    assert.deepEqual([d.level, d.main_shapes.length], [3, 5], "5+ open shapes");
    d = levelOf(Array(12).fill(8), ["C", "G", "F", "Am"]);
    assert.deepEqual([d.level, d.hardest_shape], [4, "F"]);
    d = levelOf(Array(12).fill(8), ["C", "G", "B", "Bm"]);
    assert.deepEqual([d.level, d.hardest_shape], [5, "B"]);
  });
  test("difficultyOf: rare shapes (under 4%) and blips do not count; quick changes and syncopation move L1/L2 to L3", () => {
    const holds = [...Array(30).fill(8), 2], labels = [...Array(30).fill(0).map((_, i) => ["A", "D", "E"][i % 3]), "B"];
    let d = levelOf(holds, labels);
    assert.deepEqual([d.level, d.main_shapes.includes("B")], [1, false], "B at 0.8% of chord time is not a main shape");
    assert.equal(d.changes_per_min, 14.9, "8-beat holds at 120 BPM: 30 changes in 121 s of chords");
    assert.equal(d.median_hold_beats, 8);
    d = levelOf(Array(40).fill(4), ["A", "D", "E"]);
    assert.deepEqual([d.changes_per_min, d.level], [29.3, 1], "39 changes in 80 s: under the 40-a-minute line");
    d = levelOf(Array(40).fill(2), ["A", "D", "E"], { bpm: 120, beats: 100 });
    assert.equal(d.level, 3, "median hold 2 beats at 120 BPM");
    assert.match(d.tier_reason, /median hold 2 beats/);
    assert.match(levelOf(Array(12).fill(8), ["G", "C", "D"]).tier_reason, /About 13.8 changes a minute\.$/);
    d = levelOf(Array(40).fill(3), ["A", "D", "E"], { beats: 130 });
    assert.deepEqual([d.changes_per_min, d.level], [39, 1], "39 changes a minute is under the 40 line");
    d = levelOf(Array(60).fill(2), ["A", "D", "E"], { bpm: 100 });
    assert.equal(d.level, 3, "40+ changes a minute is quick even below 120 BPM");
    assert.match(d.tier_reason, /changes a minute \(40\+\)/);
    assert.equal(levelOf(Array(12).fill(8), ["G", "C", "D"], { needsSyncopation: true }).level, 3);
    assert.equal(levelOf(Array(60).fill(2), ["C", "G", "F"], { bpm: 100 }).level, 4, "quick changes never lower a barre level");
  });
  test("applyLevelOverride keeps the computed level and the reason", () => {
    const d = levelOf(Array(60).fill(2), ["A", "D", "E"], { bpm: 100 });
    const o = X.applyLevelOverride(d, { level: 1, reason: "Founder choice." });
    assert.deepEqual([o.level, o.label, o.computed_level, o.override_reason], [1, "First chords", 3, "Founder choice."]);
    assert.equal(X.applyLevelOverride(d, undefined), d);
  });
  test("defaultPatterns: by level, and plain counts for other meters", () => {
    const ids = (level, bpb = 4) => X.defaultPatterns(level, bpb).map(p => `${p.name.split(":")[0]}:${p.strokes.join("")}`);
    assert.deepEqual(ids(1), ["Start:DDDD", "Next:DUDUDUDU"]);
    assert.deepEqual(ids(2), ["Start:DUDUDUDU", "Next:D—DU—UDU"]);
    assert.deepEqual(ids(3), ["Start:D—DU—UDU", "Next:DUDU—UDU"]);
    assert.deepEqual(ids(5), ["Start:D—DU—UDU", "Next:D—DUD—DU"]);
    assert.deepEqual(ids(3, 2), ["Start:DD", "Next:DUDU"]);
    for (const level of [1, 2, 3, 4, 5]) for (const p of X.defaultPatterns(level, 4)) {
      assert.equal(p.counts.length, p.strokes.length);
      assert.equal(p.counts.length % 4, 0);
      assert.ok(p.description && p.id);
    }
  });
  test("finishSong: unauthored songs get the level's default patterns; authored patterns are kept", () => {
    const song = songFromHolds(Array(12).fill(8), { labels: ["G", "C", "D"] });
    const built = { song: { ...song, id: "x", strumming: null }, card: {}, difficulty: X.difficultyOf(song) };
    X.finishSong(built);
    assert.deepEqual([built.song.level, built.song.group, built.card.level_label, built.song.strumming.source], [2, "level-2", "Open chords", "level-default"]);
    assert.equal(built.song.strumming.patterns[1].id, "folk-strum");
    const authored = { song: { ...song, id: "y", strumming: { note: "n", patterns: [{ id: "p", name: "Start: p", counts: ["1", "2", "3", "4"], strokes: ["D", "U", "D", "U"], description: "d" }] } },
      card: {}, difficulty: X.difficultyOf(song) };
    X.finishSong(authored, { level: 4, reason: "r" });
    assert.deepEqual([authored.song.level, authored.song.strumming.source, authored.song.strumming.patterns.length], [4, "authored", 1]);
    const bad = { song: { ...song, id: "z", strumming: { note: "n", patterns: [{ id: "p", name: "p", counts: ["1", "2", "3"], strokes: ["D", "U", "D"], description: "d" }] } },
      card: {}, difficulty: X.difficultyOf(song) };
    assert.throws(() => X.finishSong(bad), /does not fit 4 beats per bar/);
  });

  // --- catalogue config -------------------------------------------------------------------------
  const os = require("node:os");
  const tmpConfig = obj => { const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "strumalong-cfg-")), "catalogue.json"); fs.writeFileSync(f, JSON.stringify(obj)); return f; };
  const basePack = { id: "p", kind: "additions", dir: "d", rhythm: "r", metadata: "m" };
  test("readCatalogue: the shipped config parses; every exclusion and override has a reason", () => {
    const cfg = X.readCatalogue();
    assert.ok(cfg.packs.some(p => p.id === "automatic-first-ten-v1" && p.required));
    assert.ok(cfg.packs.some(p => p.id === "strumalong-additions-v2"), "v2 pack is configured (skipped while missing)");
    for (const id of ["radiohead-creep-youtube-20261010", "beatles-love-me-do-youtube-20261011", "green-day-good-riddance-youtube-20261024"]) assert.ok(cfg.exclude.has(id), id);
    assert.equal(cfg.exclude.size, 10, "founder-feedback drops (incl. Riptide, ukulele-led) plus A Horse with No Name (chart misses its changes)");
  });
  test("readCatalogue: rejects bad schema, missing reasons, unknown kinds and conflicting entries", () => {
    const base = { schema: "strumalong-catalogue-config-1", packs: [basePack] };
    assert.equal(X.readCatalogue(tmpConfig(base)).exclude.size, 0);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, schema: "x" })), /unexpected schema/);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, packs: [{ ...basePack, kind: "riff" }] })), /kind/);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, packs: [{ ...basePack, metadata: "" }] })), /metadata path/);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, exclude: [{ recording_id: "a" }] })), /reason/);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, level_overrides: [{ recording_id: "a", level: 6, reason: "r" }] })), /level 1-5/);
    assert.throws(() => X.readCatalogue(tmpConfig({ ...base, exclude: [{ recording_id: "a", reason: "r" }], level_overrides: [{ recording_id: "a", level: 2, reason: "r" }] })), /both excluded/);
  });

  test("exporter: a missing optional pack is skipped; a missing required pack stops the build", () => {
    const { spawnSync } = require("node:child_process");
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "strumalong-out-"));
    const pack = { id: "strumalong-additions-v9", kind: "additions", dir: "experiments/generated/does-not-exist-v9",
      rhythm: "experiments/generated/does-not-exist-v9/rhythm.json", metadata: "strumalong/data/does-not-exist-v9.json" };
    const run = required => spawnSync(process.execPath, [EXPORTER], { encoding: "utf8",
      env: { ...process.env, STRUMALONG_SONGS_DIR: dir, STRUMALONG_CATALOGUE: tmpConfig({ schema: "strumalong-catalogue-config-1", packs: [{ ...pack, required }] }) } });
    const optional = run(false);
    assert.equal(optional.status, 0, optional.stderr);
    assert.match(optional.stdout, /strumalong-additions-v9: .* not found; skipped/);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, "index.json"), "utf8")).songs, []);
    const required = run(true);
    assert.notEqual(required.status, 0);
    assert.match(required.stderr, /strumalong-additions-v9: .* not found/);
  });

  // --- real data: the bar objective over every built song ------------------------------------
  const SONGS = path.join(__dirname, "..", "songs");
  const built = fs.existsSync(SONGS) ? fs.readdirSync(SONGS).filter(f => f.endsWith(".json") && f !== "index.json") : [];
  test("real data: anchored bars never add mid-chord or one-beat-off lines, and cut them overall", () => {
    if (!built.length) { console.log("  (skipped real-data bar objective: no songs/*.json yet)"); return; }
    let beforeTotal = 0, afterTotal = 0;
    for (const f of built) {
      const song = JSON.parse(fs.readFileSync(path.join(SONGS, f), "utf8"));
      const plain = { ...song, chords: song.chords.map(({ b, a, ...rest }) => rest) }; // the old song-wide bar_phase
      const before = X.barMetrics(plain), after = X.barMetrics(song);
      assert.ok(after.weird + after.split <= before.weird + before.split, `${f}: ${after.weird}+${after.split} odd lines vs ${before.weird}+${before.split} before`);
      assert.ok(after.on_bar_or_half >= before.on_bar_or_half - 1e-9, `${f}: fewer changes on a bar or half-bar`);
      beforeTotal += before.weird + before.split; afterTotal += after.weird + after.split;
      const rebuilt = JSON.parse(JSON.stringify(plain));
      X.applyBarAnchors(rebuilt);
      assert.deepEqual(rebuilt.chords, song.chords, `${f}: anchors are reproducible from the chart and grid`);
    }
    assert.ok(afterTotal <= beforeTotal / 2, `odd lines overall: ${beforeTotal} -> ${afterTotal}`);
  });

  // --- real data: the timing fix over every built song ------------------------------------------
  // The unfixed chart is recoverable from the recorded moves (`was`), so the fix can be re-run from it.
  const plainChords = chords => chords.map(({ b, a, t, ...rest }) => rest);
  function unfixedOf(song) {
    const entry = song.chart.corrections.find(k => k.kind === "timing");
    const chords = plainChords(song.chords);
    for (const m of entry ? entry.moves : []) {
      const i = chords.findIndex(c => c.s === m.at);
      chords[i].s = m.was; chords[i - 1].e = m.was;
    }
    return { ...song, chords };
  }
  test("real data: the timing fix is reproducible from the recorded moves, idempotent, and only moves times", () => {
    if (!built.length) return;
    // Songs opted out in the catalogue config ship their unfixed chart, so there is nothing to reproduce.
    const cfgFile = path.join(__dirname, "..", "data", "catalogue.json");
    const optedOut = new Set((JSON.parse(fs.readFileSync(cfgFile, "utf8")).timing_fix_off || []).map(t => t.recording_id));
    let moved = 0;
    for (const f of built) {
      const song = JSON.parse(fs.readFileSync(path.join(SONGS, f), "utf8"));
      if (optedOut.has(song.id)) {
        assert.ok(!song.chart.corrections.some(k => k.kind === "timing"), `${f}: opted out, so no timing moves are recorded`);
        continue;
      }
      const entry = song.chart.corrections.find(k => k.kind === "timing");
      const raw = unfixedOf(song), rerun = JSON.parse(JSON.stringify(raw));
      const result = X.applyTimingFix(rerun);
      assert.deepEqual(result.moves, entry ? entry.moves : [], `${f}: the fix re-run on the unfixed chart makes the recorded moves`);
      assert.deepEqual(rerun.chords, song.chords.map(({ b, a, ...rest }) => rest), `${f}: and the shipped chords`);
      assert.deepEqual(raw.chords.map(c => c.l), song.chords.map(c => c.l), `${f}: labels never change`);
      const again = JSON.parse(JSON.stringify({ ...song, chords: song.chords.map(({ b, a, ...rest }) => rest) }));
      assert.equal(X.applyTimingFix(again).moves.length, 0, `${f}: idempotent`);
      moved += result.moves.length;
    }
    assert.ok(moved > 0, "some songs have moves");
  });
  test("real data: every move is exactly one drawn beat, at most one beat in time, and leaves holds of a beat or more", () => {
    for (const f of built) {
      const song = JSON.parse(fs.readFileSync(path.join(SONGS, f), "utf8"));
      const entry = song.chart.corrections.find(k => k.kind === "timing");
      if (!entry) continue;
      const holds = X.gridHolds(song);
      for (const m of entry.moves) {
        const p1 = core.gridPosition(song.beats, m.at), p0 = core.gridPosition(song.beats, m.was);
        assert.equal(Math.round(p1) - Math.round(p0), m.shift, `${f} ${m.at}: one drawn beat`);
        assert.ok(Math.abs(p1 - p0) <= 1 + 1e-6, `${f} ${m.at}: ${Math.abs(p1 - p0).toFixed(2)} beats in time`);
        const i = holds.findIndex(h => h.s === m.at);
        assert.ok(i > 0, `${f} ${m.at}: a default-view change`);
        for (const h of [holds[i - 1], holds[i]]) assert.ok(h.inGrid && !h.quick && h.count >= 1 && h.span >= 1 - 1e-6, `${f} ${m.at}: hold under a beat`);
        assert.deepEqual([holds[i - 1].label, holds[i].label], [m.from, m.to], `${f} ${m.at}: labels as recorded`);
      }
    }
  });
  test("real data: the fix makes repeats more consistent and never adds odd bar lines or approx bars", () => {
    for (const f of built) {
      const song = JSON.parse(fs.readFileSync(path.join(SONGS, f), "utf8"));
      const raw = unfixedOf(song), reference = { anchors: X.barAnchors(raw).anchors };
      const before = X.timingConsistency(raw, reference), after = X.timingConsistency(song, reference);
      assert.ok(after.pct >= before.pct, `${f}: consistency ${before.pct} -> ${after.pct}`);
      const anchoredRaw = JSON.parse(JSON.stringify(raw));
      X.applyBarAnchors(anchoredRaw);
      const b = X.barMetrics(anchoredRaw), a = X.barMetrics(song);
      assert.ok(a.weird <= b.weird && a.split <= b.split, `${f}: weird ${b.weird} -> ${a.weird}, split ${b.split} -> ${a.split}`);
      assert.ok(a.approx_pct <= b.approx_pct + 1e-9, `${f}: approx bars ${b.approx_pct}% -> ${a.approx_pct}%`);
    }
  });
  test("real data: Zombie's late C (founder report, 25 Oct) is moved one beat earlier", () => {
    const file = path.join(SONGS, "cranberries-zombie-youtube-20261024.json");
    if (!fs.existsSync(file)) return;
    const song = JSON.parse(fs.readFileSync(file, "utf8"));
    const entry = song.chart.corrections.find(k => k.kind === "timing");
    assert.ok(entry && entry.moves.some(m => m.from === "Em" && m.to === "C" && m.shift === -1 && Math.abs(m.was - 133.933) < 0.01), JSON.stringify(entry));
  });
}

console.log(`exporter.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`exporter.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
