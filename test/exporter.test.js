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
    assert.equal(cfg.exclude.size, 8, "7 founder-feedback drops plus A Horse with No Name (chart misses its changes)");
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
}

console.log(`exporter.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`exporter.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
