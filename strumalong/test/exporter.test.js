"use strict";
// Tests for strumalong/tools/build-songs.js. The Song export module (exportSong) is the test surface: songs are
// exported from in-memory drafts (a primary.json and a rhythm case built here) and checked on the song, card and
// report it returns. The adapter is tested in process (buildCatalogue, readCatalogue), and the real-data properties
// run on the catalogue built in memory from the packs when they are present. The timing-fix unit tests below still
// call those helpers directly until their own module takes them over; the Arrangement profile (main shapes, level)
// is tested through its own interface in arrangement-profile.test.js.
// Run: node strumalong/test/run.js (or this file directly). Requiring the exporter does not build anything.
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const os = require("node:os");
const crypto = require("node:crypto");

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
  const { barPhaseVote, barPhaseConfident } = X;
  const core = require(path.join(__dirname, "..", "lib", "core.js"));
  const grid = (first, step, count) => Array.from({ length: count }, (_, i) => +(first + step * i).toFixed(6));
  const event = (start, label = "A") => ({ start_seconds: start, end_seconds: start + 0.5, label });

  // --- in-memory drafts for exportSong ---------------------------------------------------------
  // A draft as a pack holds it: chord events (seconds) as primary.json bytes, and a paired rhythm case.
  function draftOf(events, beats, opts = {}) {
    const duration = Math.max(beats[beats.length - 1], ...events.map(e => e.end_seconds)) + 1;
    const recording = { id: "fixture-song", audio_sha256: "a".repeat(64), sample_rate_hz: 44100, duration_seconds: duration };
    const primary = Buffer.from(JSON.stringify({ schema_version: "1.0", recording, chords: events }));
    return {
      case: { id: recording.id, recording, source: { source: { video_id: "fixture-video", uploader: "Fixture", duration_seconds: duration } },
        artifacts: { primary_sha256: crypto.createHash("sha256").update(primary).digest("hex") } },
      primary, packId: "fixture-pack", correctionSet: undefined,
      rhythmCase: { status: "fixture", pulse_bpm: opts.bpm || 120, beats_per_bar: opts.assumed ? null : opts.bpb || 4, meter_label: "fixture",
        beat_times_seconds: beats },
      hashes: { manifest: "m", rhythm: "r", practice: "p", learning: "l", catalogue: "c" },
    };
  }
  const metadataOf = (extra = {}) => ({ title: "Fixture", artist: "Tests", capo: 0, capo_source: "none", setup_note: "Standard tuning.",
    strumming: null, learning: { skill_focus: "", prerequisites: "", sources: [] }, ...extra });
  // Chord events from holds in beats on the 120 BPM grid (beat i at 0.5 i s); lag: each change that many seconds early.
  function holdEvents(holds, opts = {}) {
    const labels = opts.labels || ["G", "C", "D", "Em"], lag = opts.lag || 0;
    let beat = opts.start || 0;
    return holds.map((n, i) => {
      const e = { start_seconds: +(beat * 0.5 - (i ? lag : 0)).toFixed(3), end_seconds: +((beat + n) * 0.5 - (i + 1 < holds.length ? lag : 0)).toFixed(3),
        label: labels[i % labels.length] };
      beat += n;
      return e;
    });
  }
  const exportEvents = (events, opts = {}) => X.exportSong(draftOf(events, opts.grid || grid(0, 0.5, opts.beats || 200), opts),
    metadataOf(opts.metadata), opts.settings);
  const exportHolds = (holds, opts = {}) => exportEvents(holdEvents(holds, opts), opts);
  const noFix = { timingFix: false };

  // --- bar-phase vote (song.rhythm) --------------------------------------------------------------
  const voteOf = (events, beats, bpb = 4) => {
    const { song, report } = exportEvents(events, { grid: beats, bpb, settings: noFix });
    return { vote: report.vote, rhythm: song.rhythm };
  };
  test("bar-phase vote: 2/4 starts 0.34 beat after even beats vote residue 0, confident", () => {
    const beats = grid(1, 0.5, 60); // beat i at 1 + 0.5 i s
    const events = [];
    for (let i = 2; i < 56; i += 4) events.push(event(beats[i] + 0.34 * 0.5)); // +0.34 beat: outside the old 0.125-beat window
    const { vote, rhythm } = voteOf(events, beats, 2);
    assert.deepEqual([vote.phase, vote.share, vote.votes, vote.eligible], [0, 1, events.length, events.length]);
    assert.deepEqual([rhythm.bar_phase, rhythm.bar_phase_share, rhythm.bar_phase_confident], [0, 1, true]);
    assert.equal(barPhaseConfident(vote, true), false, "an assumed meter is never confident");
  });
  test("bar-phase vote: only 2 eligible starts is not confident", () => {
    const beats = grid(1, 0.5, 40);
    const events = [event(0.2), event(beats[4]), event(beats[8]), event(beats[12], "N"), event(beats[16], "X"), event(beats[39] + 0.2)];
    const { vote, rhythm } = voteOf(events, beats);
    assert.deepEqual(vote, { phase: 0, share: 1, votes: 2, eligible: 2 }, "N, X and starts outside the grid do not vote");
    assert.equal(rhythm.bar_phase_confident, false);
  });
  test("bar-phase vote: a 50/50 residue split keeps the lowest residue and is not confident", () => {
    const beats = grid(1, 0.5, 80);
    const events = [];
    for (let k = 0; k < 6; k++) { events.push(event(beats[4 * k + 3])); events.push(event(beats[4 * k + 41] + 0.1)); } // residues 3 and 1
    const { vote, rhythm } = voteOf(events.sort((a, b) => a.start_seconds - b.start_seconds), beats);
    assert.deepEqual([vote.phase, vote.share, vote.votes], [1, 0.5, 12], "tie keeps the lowest residue");
    assert.deepEqual([rhythm.bar_phase, rhythm.bar_phase_share, rhythm.bar_phase_confident], [1, 0.5, false]);
  });
  test("bar-phase vote: rounding follows the app (a start 0.6 beat late votes for the next beat)", () => {
    const events = Array.from({ length: 10 }, (_, k) => event(4 * k + 1.6)); // round(4k + 1.6) = 4k + 2
    const { vote, rhythm } = voteOf(events, grid(0, 1, 50));
    assert.deepEqual([vote.phase, rhythm.bar_phase_confident], [2, true]);
    assert.deepEqual(barPhaseVote([1], events, 4), { phase: 0, share: 0, votes: 0, eligible: 0 });
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
  // The bar model as exportSong ships it, on the chart without the timing fix: report.bars before (one song-wide
  // bar_phase) and after (anchored bars), and the anchored chords in song.chords.
  const barsOf = (holds, opts = {}) => exportHolds(holds, { settings: noFix, ...opts });

  test("bar model: steady one-bar changes keep one confident phase (the old global phase)", () => {
    const { song, report } = barsOf(Array(16).fill(4), { start: 1 });
    assert.deepEqual(report.bars.runs.map(r => [r.mode, r.state, r.confident]), [["phase", 1, true]]);
    const m = report.bars.after;
    assert.deepEqual([m.on_bar, m.weird, m.split, m.restarts, m.approx_pct], [100, 0, 0, 0, 0]);
    assert.ok(song.chords.every(c => c.b === 1 && c.a === undefined));
    assert.deepEqual(report.bars.before, m, "same bars as the song-wide phase");
    assert.equal(song.rhythm.bar_confident_pct, 100);
  });
  test("bar model: a one-beat slip in the grid switches to a local phase instead of drawing every later bar mid-chord", () => {
    const { report: { bars } } = barsOf([...Array(10).fill(4), 5, ...Array(12).fill(4)]);
    const { before, after } = bars;
    assert.ok(before.split + before.weird >= 10, `the song-wide phase draws many mid-chord lines (${before.split} split, ${before.weird} weird)`);
    assert.equal(after.split, 0);
    assert.ok(after.weird <= 1, "at most the slipped 5-beat hold keeps an odd line");
    assert.equal(after.restarts, 1, "the count restarts once, at the slip");
    assert.deepEqual(bars.runs.map(r => [r.state, r.confident]), [[0, true], [1, true]]);
  });
  test("bar model: half-bar changes (G 4, C 2, D 2) put the bar line on G, not between C and D", () => {
    const { song, report } = barsOf(Array(8).fill([4, 2, 2]).flat(), { start: 2, labels: ["G", "C", "D"] });
    const m = report.bars.after;
    assert.ok(song.chords.every(c => c.b === 2), "G starts every bar");
    assert.deepEqual([m.on_bar_or_half, m.weird, m.split, m.approx_pct], [100, 0, 0, 0]);
    assert.equal(m.on_bar, 66.7);
  });
  test("bar model: no steady phase falls back to hold-relative bars (each change starts a bar, approx)", () => {
    const holds = Array(24).fill(3); // a three-beat song on a four-beat assumption: no 4-beat phase fits
    const { song, report } = barsOf(holds, { start: 1 });
    const m = report.bars.after, before = report.bars.before;
    assert.deepEqual(report.bars.runs.map(r => [r.mode, r.confident]), [["hold", false]]);
    assert.deepEqual([before.weird, before.split, m.weird, m.split, m.approx_pct], [12, 12, 0, 0, 100]);
    assert.equal(m.restarts, 23, "the count restarts at every change");
    assert.ok(song.chords.every(c => c.a === 1));
    let beat = 1;
    for (let i = 0; i < holds.length; i++) {
      assert.equal(core.strumStep(song, counter, beat * 0.5 + 0.01), 0, `hold ${i} at beat ${beat}: the count restarts at 1`);
      assert.ok(core.barAnchorAt(song, beat).bar);
      beat += holds[i];
    }
  });
  test("bar model: an assumed meter never claims confident bars; quick blips and N follow their neighbours", () => {
    assert.ok(barsOf(Array(16).fill(4), { assumed: true }).song.chords.every(c => c.a === 1));
    const events = holdEvents(Array(10).fill(4), { start: 1 });
    events.splice(3, 0, { start_seconds: +(events[2].end_seconds - 0.2).toFixed(3), end_seconds: events[2].end_seconds, label: "A" });
    events[2].end_seconds = +(events[2].end_seconds - 0.2).toFixed(3);
    events.unshift({ start_seconds: 0, end_seconds: 0.5, label: "N" });
    const { song } = exportEvents(events, { settings: noFix });
    assert.ok(song.chords.every(c => c.b === 1), "blip and N take the run's phase");
  });
  test("bar model: Full view (no merges) draws the same bars as Simple view", () => {
    const { song } = barsOf(Array(12).fill(4), { start: 1, labels: ["G", "G7", "C", "D"] }); // G + G7 merge in Simple
    for (const quality of ["core", "full"]) {
      const tl = core.buildTimeline(song, { quality });
      for (const ev of tl) {
        const cue = core.cueAt(tl, song, ev.s + 0.01), base = Math.round(cue.now.startBeat);
        for (const j of cue.now.barBefore) assert.ok(core.barAnchorAt(song, base + j).bar);
      }
    }
    assert.equal(core.buildTimeline(song, { quality: "full" }).length, 12);
  });

  // --- exportSong: the composition -----------------------------------------------------------------
  const holdCountsOf = song => X.gridHolds(song).filter(h => h.inGrid).map(h => h.count);
  test("exportSong: a chord change a beat off its repeats is moved before the bars, level and card see the chart (3982309)", () => {
    // Em C G D loop, every change 50 ms early (CREMA-like); in repeat 4 the C comes one beat late (Em 5, C 3).
    const holds = Object.assign(Array(40).fill(4), { 12: 5, 13: 3 });
    const opts = { start: 1, labels: ["Em", "C", "G", "D"], lag: 0.05 };
    const { song, card, report } = exportHolds(holds, opts);
    const entry = song.chart.corrections.find(k => k.kind === "timing");
    assert.deepEqual(entry.moves.map(m => [m.from, m.to, m.shift, m.agree]), [["Em", "C", -1, "8/9"]]);
    assert.deepEqual(report.timing.moves, entry.moves);
    assert.deepEqual(holdCountsOf(song), Array(40).fill(4), "the shipped chart has every hold a bar long again");
    const moved = song.chords[13];
    assert.deepEqual([moved.l, moved.t, moved.s, song.chords[12].e], ["C", 1, entry.moves[0].at, entry.moves[0].at]);
    assert.ok(song.chords.every(c => c.b === 1 && !c.a), "the moved chord keeps t:1 through the bar anchors, and every bar sits on the loop");
    assert.deepEqual(song.chords.map(c => c.l), holdEvents(holds, opts).map(e => e.label), "labels never change");
    assert.deepEqual([report.bars.after.weird, report.bars.after.split], [0, 0]);
    assert.ok(report.timing.before.consistency.pct < 100 && report.timing.after.consistency.pct === 100,
      `${report.timing.before.consistency.pct} -> ${report.timing.after.consistency.pct}`);
    assert.deepEqual([song.difficulty.median_hold_beats, [...card.core_shapes].sort()], [4, ["C", "D", "Em", "G"]]);

    // Catalogue timing_fix_off: the same draft ships unfixed, and "before the fix" above measured exactly that chart.
    const off = exportHolds(holds, { ...opts, settings: noFix });
    assert.ok(!off.song.chart.corrections.some(k => k.kind === "timing"));
    assert.deepEqual(holdCountsOf(off.song).slice(12, 14), [5, 3]);
    assert.deepEqual([off.report.timing.enabled, off.report.timing.moves], [false, []]);
    assert.match(off.report.timing.after.left[0].reason, /timing fix off/);
    assert.deepEqual(report.timing.before.bars, off.report.bars.after, "the unfixed chart is measured unfixed, whatever the fix does to its copy");
  });
  test("exportSong: label aliases relabel whole events, keep c:1 through the fix and the bars, and are recorded", () => {
    const metadata = { label_aliases: { map: { "F#m7": "D6add9/F#" }, note: "Played as the two-finger grip" } };
    const { song } = exportHolds(Array(16).fill(4), { start: 1, labels: ["Em", "F#m7"], metadata });
    assert.deepEqual([...new Set(song.chords.map(c => c.l))], ["Em", "D6add9/F#"]);
    assert.ok(song.chords.every(c => (c.l === "Em" ? c.c === undefined : c.c === 1) && c.b === 1));
    const alias = song.chart.corrections.find(k => k.id === "alias-F#m7");
    assert.deepEqual([alias.from, alias.to, alias.start, alias.end], ["F#m7", "D6add9/F#", 2.5, 32.5]);
    assert.match(alias.note, /^Played as the two-finger grip \(8 chart events between these times;/);
  });
  test("exportSong: pure; the draft is untouched and the same inputs give the same song", () => {
    const draft = draftOf(holdEvents(Object.assign(Array(40).fill(4), { 12: 5, 13: 3 }), { start: 1, lag: 0.05 }), grid(0, 0.5, 200));
    const frozen = JSON.stringify(draft), metadata = metadataOf();
    const first = X.exportSong(draft, metadata), second = X.exportSong(draft, metadata);
    assert.equal(JSON.stringify(draft), frozen);
    assert.deepEqual(metadata, metadataOf());
    assert.deepEqual(first, second);
    assert.deepEqual([first.song.order, first.card.order], [null, null], "order within a level is the catalogue's");
    assert.deepEqual(first.song.videos.map(v => [v.video_id, v.kind, v.timing_checked]), [["fixture-video", "analysed", true]]);
    assert.deepEqual([first.card.playable_embed, first.card.embed_note], [true, ""]);
  });
  test("exportSong: refuses a draft whose bytes do not match the manifest, and a song whose upload cannot embed", () => {
    const draft = draftOf(holdEvents(Array(8).fill(4)), grid(0, 0.5, 40));
    assert.throws(() => X.exportSong({ ...draft, primary: Buffer.concat([draft.primary, Buffer.from(" ")]) }, metadataOf()), /sha256 mismatch/);
    assert.throws(() => X.exportSong({ ...draft, rhythmCase: undefined }, metadataOf()), /no paired rhythm grid/);
    assert.throws(() => X.exportSong(draft, metadataOf({ playable_embed: false })), /playable_embed false/);
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

  // --- level (rules: arrangement-profile.test.js) ---------------------------------------------------
  test("exportSong: the card chips are the shapes the level counts", () => {
    // A rare slash shape (G/B, 6%) is neither a chip nor a level shape: D, A, G open chords, Level 2.
    const { song, card } = exportHolds([...Array(10).fill([20, 10, 5]).flat(), 22], { labels: [...Array(10).fill(["D", "A", "G"]).flat(), "G/B"] });
    assert.deepEqual(card.core_shapes, song.difficulty.main_shapes);
    assert.deepEqual([card.core_shapes, song.level], [["D", "A", "G"], 2]);
  });
  test("exportSong: expected_level mismatches warn and expected_shapes mismatches are reported, never failing", () => {
    const holds = Array(12).fill(8), labels = ["A", "D", "E"];
    const ok = exportHolds(holds, { labels, metadata: { expected: { level: 1, shapes: ["E", "D", "A"] } } });
    assert.deepEqual([ok.report.expected, ok.report.warnings.length], [{ level: null, shapes: null }, 0]);
    const off = exportHolds(holds, { labels, metadata: { expected: { level: 3, shapes: ["A", "D", "Asus4"] } } });
    assert.equal(off.song.level, 1, "the expectation never changes the level");
    assert.deepEqual(off.report.expected.level, { expected: 3, built: 1 });
    assert.deepEqual([off.report.expected.shapes.missing, off.report.expected.shapes.extra], [["Asus4"], ["E"]]);
    assert.ok(off.report.warnings.some(w => /built Level 1, metadata expected_level 3/.test(w)));
    assert.deepEqual(exportHolds(holds, { labels }).report.expected, { level: null, shapes: null }, "no expectations, nothing checked");
  });
  test("exportSong: a catalogue level override sets the level, group and default patterns, and keeps the computed level", () => {
    const quick = { bpm: 100, labels: ["A", "D", "E"] };
    const computed = exportHolds(Array(60).fill(2), quick);
    assert.equal(computed.song.difficulty.level, 3);
    assert.equal(computed.song.difficulty.computed_level, undefined);
    const { song, card } = exportHolds(Array(60).fill(2), { ...quick, settings: { levelOverride: { level: 1, reason: "Founder choice." } } });
    const d = song.difficulty;
    assert.deepEqual([d.level, d.label, d.computed_level, d.override_reason], [1, "First chords", 3, "Founder choice."]);
    assert.deepEqual([song.level, song.group, card.level, card.group, card.level_label], [1, "level-1", 1, "level-1", "First chords"]);
    assert.equal(song.strumming.patterns[0].id, "steady-down", "the overridden level's default patterns");
  });
  test("exportSong: unauthored songs get the level's default patterns, plain counts for other meters", () => {
    const ids = (level, bpb = 4) => exportHolds(Array(12).fill(8), { bpb, labels: ["G", "C", "D"], settings: { levelOverride: { level, reason: "r" } } })
      .song.strumming.patterns.map(p => `${p.name.split(":")[0]}:${p.strokes.join("")}`);
    assert.deepEqual(ids(1), ["Start:DDDD", "Next:DUDUDUDU"]);
    assert.deepEqual(ids(2), ["Start:DUDUDUDU", "Next:D—DU—UDU"]);
    assert.deepEqual(ids(3), ["Start:D—DU—UDU", "Next:DUDU—UDU"]);
    assert.deepEqual(ids(5), ["Start:D—DU—UDU", "Next:D—DUD—DU"]);
    assert.deepEqual(ids(3, 2), ["Start:DD", "Next:DUDU"]);
    for (const level of [1, 2, 3, 4, 5]) {
      const { song } = exportHolds(Array(12).fill(8), { settings: { levelOverride: { level, reason: "r" } } });
      assert.equal(song.strumming.source, "level-default");
      assert.match(song.strumming.note, new RegExp(`^Default practice patterns for Level ${level} songs`));
      for (const p of song.strumming.patterns) {
        assert.equal(p.counts.length, p.strokes.length);
        assert.equal(p.counts.length % 4, 0);
        assert.ok(p.description && p.id);
      }
    }
    const { song, card } = exportHolds(Array(12).fill(8), { labels: ["G", "C", "D"] });
    assert.deepEqual([song.level, song.group, card.level_label, song.strumming.source, song.strumming.patterns[1].id],
      [2, "level-2", "Open chords", "level-default", "folk-strum"]);
  });
  test("exportSong: authored patterns are kept, and must fit the meter", () => {
    const pattern = counts => ({ id: "p", name: "Start: p", counts, strokes: counts.map(() => "D"), description: "d" });
    const authored = exportHolds(Array(12).fill(8), { labels: ["G", "C", "D"],
      metadata: { strumming: { note: "n", patterns: [pattern(["1", "2", "3", "4"])] } }, settings: { levelOverride: { level: 4, reason: "r" } } });
    assert.deepEqual([authored.song.level, authored.song.strumming.source, authored.song.strumming.patterns.length], [4, "authored", 1]);
    assert.throws(() => exportHolds(Array(12).fill(8), { metadata: { strumming: { note: "n", patterns: [pattern(["1", "2", "3"])] } } }),
      /does not fit 4 beats per bar/);
  });

  // --- catalogue config and the adapter --------------------------------------------------------
  const tmpConfig = obj => { const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "strumalong-cfg-")), "catalogue.json"); fs.writeFileSync(f, JSON.stringify(obj)); return f; };
  const basePack = { id: "p", kind: "additions", dir: "d", rhythm: "r", metadata: "m" };
  const SONGS = path.join(__dirname, "..", "songs");
  test("readCatalogue: the shipped config parses; no excluded recording ships and every override is shipped", () => {
    const cfg = X.readCatalogue();
    assert.ok(cfg.packs.some(p => p.id === "automatic-first-ten-v1" && p.required));
    assert.ok(cfg.packs.some(p => p.id === "strumalong-additions-v2"), "v2 pack is configured (skipped while missing)");
    for (const id of ["radiohead-creep-youtube-20261010", "beatles-love-me-do-youtube-20261011", "green-day-good-riddance-youtube-20261024"]) assert.ok(cfg.exclude.has(id), id);
    const indexFile = path.join(SONGS, "index.json");
    if (!fs.existsSync(indexFile)) return;
    const shipped = JSON.parse(fs.readFileSync(indexFile, "utf8")).songs.map(card => card.id);
    for (const id of shipped) assert.ok(!cfg.exclude.has(id), `${id} is excluded (${cfg.exclude.has(id) && cfg.exclude.get(id).reason}) but ships`);
    for (const id of cfg.overrides.keys()) assert.ok(shipped.includes(id), `level override for ${id}, which does not ship`);
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
  test("adapter: a missing optional pack is skipped; a missing required pack stops the build", () => {
    const pack = { id: "strumalong-additions-v9", kind: "additions", dir: "experiments/generated/does-not-exist-v9",
      rhythm: "experiments/generated/does-not-exist-v9/rhythm.json", metadata: "strumalong/data/does-not-exist-v9.json" };
    const cfg = required => X.readCatalogue(tmpConfig({ schema: "strumalong-catalogue-config-1", packs: [{ ...pack, required }] }));
    const optional = X.buildCatalogue(cfg(false));
    assert.deepEqual([optional.built, optional.index.songs, optional.index.groups], [[], [], []]);
    assert.throws(() => X.buildCatalogue(cfg(true)), /strumalong-additions-v9: .* not found/);
  });

  // --- real data: the composition over every song in the packs ----------------------------------
  // The catalogue exactly as the CLI builds it, in memory. The packs are gitignored, so these skip without them.
  const PREPARED = path.join(__dirname, "..", "..", "experiments", "generated", "automatic-first-ten-v1", "manifest.json");
  const catalogue = fs.existsSync(PREPARED) ? X.buildCatalogue(X.readCatalogue()) : null;
  const built = catalogue ? catalogue.built : [];
  if (!catalogue) console.log("  (skipped real-data checks: experiments/generated packs not found)");
  test("real data: anchored bars never add mid-chord or one-beat-off lines, and cut them overall", () => {
    let beforeTotal = 0, afterTotal = 0;
    for (const { song, report: { bars: { before, after } } } of built) {
      assert.ok(after.weird + after.split <= before.weird + before.split, `${song.id}: ${after.weird}+${after.split} odd lines vs ${before.weird}+${before.split} before`);
      assert.ok(after.on_bar_or_half >= before.on_bar_or_half - 1e-9, `${song.id}: fewer changes on a bar or half-bar`);
      beforeTotal += before.weird + before.split; afterTotal += after.weird + after.split;
    }
    assert.ok(afterTotal <= beforeTotal / 2, `odd lines overall: ${beforeTotal} -> ${afterTotal}`);
  });
  test("real data: the shipped moves are the fix's, marked on the chords, idempotent, and off where the catalogue says", () => {
    const cfg = X.readCatalogue();
    let moved = 0;
    for (const { song, report: { timing } } of built) {
      const entry = song.chart.corrections.find(k => k.kind === "timing");
      assert.equal(timing.enabled, !cfg.timingOff.has(song.id));
      if (!timing.enabled) { assert.ok(!entry, `${song.id}: opted out, so no timing moves are recorded`); continue; }
      assert.deepEqual(entry ? entry.moves : [], timing.moves, `${song.id}: chart.corrections lists every move`);
      assert.equal(song.chords.filter(c => c.t).length, timing.moves.length, `${song.id}: t:1 on each moved chord`);
      for (const m of timing.moves) {
        const i = song.chords.findIndex(c => c.s === m.at);
        assert.ok(i > 0 && song.chords[i].t === 1 && song.chords[i - 1].e === m.at, `${song.id} ${m.at}: the moved boundary`);
      }
      const again = JSON.parse(JSON.stringify({ ...song, chords: song.chords.map(({ b, a, ...rest }) => rest) }));
      assert.equal(X.applyTimingFix(again).moves.length, 0, `${song.id}: idempotent`);
      moved += timing.moves.length;
    }
    if (built.length) assert.ok(moved > 0, "some songs have moves");
  });
  test("real data: every move is exactly one drawn beat, at most one beat in time, and leaves holds of a beat or more", () => {
    for (const { song, report: { timing } } of built) {
      const holds = X.gridHolds(song);
      for (const m of timing.moves) {
        const p1 = core.gridPosition(song.beats, m.at), p0 = core.gridPosition(song.beats, m.was);
        assert.equal(Math.round(p1) - Math.round(p0), m.shift, `${song.id} ${m.at}: one drawn beat`);
        assert.ok(Math.abs(p1 - p0) <= 1 + 1e-6, `${song.id} ${m.at}: ${Math.abs(p1 - p0).toFixed(2)} beats in time`);
        const i = holds.findIndex(h => h.s === m.at);
        assert.ok(i > 0, `${song.id} ${m.at}: a default-view change`);
        for (const h of [holds[i - 1], holds[i]]) assert.ok(h.inGrid && !h.quick && h.count >= 1 && h.span >= 1 - 1e-6, `${song.id} ${m.at}: hold under a beat`);
        assert.deepEqual([holds[i - 1].label, holds[i].label], [m.from, m.to], `${song.id} ${m.at}: labels as recorded`);
      }
    }
  });
  test("real data: the fix makes repeats more consistent and never adds odd bar lines or approx bars", () => {
    for (const { song, report: { timing: { before, after } } } of built) {
      assert.ok(after.consistency.pct >= before.consistency.pct, `${song.id}: consistency ${before.consistency.pct} -> ${after.consistency.pct}`);
      const b = before.bars, a = after.bars;
      assert.ok(a.weird <= b.weird && a.split <= b.split, `${song.id}: weird ${b.weird} -> ${a.weird}, split ${b.split} -> ${a.split}`);
      assert.ok(a.approx_pct <= b.approx_pct + 1e-9, `${song.id}: approx bars ${b.approx_pct}% -> ${a.approx_pct}%`);
    }
  });
  test("real data: Zombie's late C (founder report, 25 Oct) is moved one beat earlier", () => {
    const zombie = built.find(b => b.song.id === "cranberries-zombie-youtube-20261024");
    if (!zombie) return;
    const moves = zombie.report.timing.moves;
    assert.ok(moves.some(m => m.from === "Em" && m.to === "C" && m.shift === -1 && Math.abs(m.was - 133.933) < 0.01), JSON.stringify(moves));
  });
}

console.log(`exporter.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`exporter.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
