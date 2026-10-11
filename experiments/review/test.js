"use strict";
const assert = require("node:assert/strict");
const { annotationExport, validateCandidate, currentEvent, exposureKey, loadExposure, recordExposure, refreshExposure, validateEvidence, clampSeek, playbackSnapshot, feedbackKey, feedbackExport, captureFeedback, loadFeedback, saveFeedback, transposePracticeLabel, practiceLabel, coreChordLabel, displayedChord, practiceTimeline } = require("./app.js");
let checks = 0;
function test(name, callback) { callback(); checks++; console.log(`ok ${name}`); }
const recording = { id: "excerpt", title: "Generated", audio_sha256: "hash", duration_seconds: 20, sample_rate_hz: 100 };
const reviewCase = { recording, origin: { source_recording_id: "source", source_offset_seconds: 10, source_audio_sha256: "sourcehash" } };
reviewCase.id = recording.id;
const marks = [
  { time: "5.25", label: "G", uncertainty: "0.1", confidence: "unsure" },
  { time: "0", label: "C", uncertainty: "0.05", confidence: "certain" }
];
test("manual annotation sorts marks and preserves local/source origins", () => {
  const result = annotationExport(reviewCase, { marks, notes: "own listening", exposed: false }, 60);
  assert.equal(result.candidate_exposure, "audio-only-so-far");
  assert.equal(result.gold, false);
  assert.equal(result.status, "human-draft-needs-independent-verification");
  assert.deepEqual(result.annotations.map(mark => [mark.start_seconds, mark.end_seconds]), [[0, 5.25], [5.25, 20]]);
  assert.equal(result.origin.source_offset_seconds, 10);
  assert.equal(result.missing_initial_label, false);
  assert.equal(marks[0].time, "5.25");
});
test("reveal changes provenance, never inserts model events", () => {
  const result = annotationExport(reviewCase, { marks: [], notes: "", exposed: true }, 30);
  assert.equal(result.candidate_exposure, "model-exposed");
  assert.deepEqual(result.annotations, []);
  assert.equal(result.missing_initial_label, true);
  assert.equal(result.gold, false);
});
test("invalid and duplicate marks reject export", () => {
  for (const change of [{time: "NaN"}, {time: "20"}, {time: "-1"}, {time: ""}, {label: ""}, {uncertainty: "3"}, {uncertainty: ""}, {confidence: "guess"}]) {
    assert.throws(() => annotationExport(reviewCase, { marks: [{...marks[0], ...change}], exposed: false }, 1));
  }
  assert.throws(() => annotationExport(reviewCase, { marks: [marks[0], marks[0]], exposed: false }, 1));
});
const chart = { schema_version: "1.0", recording, chords: [
  { start_seconds: 0, end_seconds: 5, label: "C" }, { start_seconds: 6, end_seconds: 20, label: "G" }
] };
test("candidate pairing checks excerpt identity and audio hash", () => {
  assert.equal(validateCandidate(chart, recording), chart);
  for (const change of [{id: "other"}, {audio_sha256: "other"}, {duration_seconds: 21}, {duration_seconds: NaN}, {sample_rate_hz: 200}]) {
    assert.throws(() => validateCandidate({...chart, recording: {...recording, ...change}}, recording));
  }
});
test("candidate intervals are half-open with explicit gaps", () => {
  assert.equal(currentEvent(chart.chords, 4.99).label, "C");
  assert.equal(currentEvent(chart.chords, 5), null);
  assert.equal(currentEvent(chart.chords, 6).label, "G");
  assert.equal(currentEvent(chart.chords, 20), null);
});
test("candidate malformed intervals reject", () => {
  for (const chords of [[{start_seconds: 0, end_seconds: 21, label: "G"}],
                        [{start_seconds: 0, end_seconds: 4, label: "G"}, {start_seconds: 3, end_seconds: 8, label: "C"}],
                        [{start_seconds: NaN, end_seconds: 1, label: "C"}]]) {
    assert.throws(() => validateCandidate({...chart, chords}, recording));
  }
});
test("candidate exposure persists across a fresh session for the same pack/case/audio", () => {
  const values = new Map();
  const storage = { getItem: key => values.has(key) ? values.get(key) : null, setItem: (key, value) => values.set(key, value) };
  const key = exposureKey("pack", reviewCase);
  assert.equal(loadExposure(storage, key).exposed, false);
  const earlierTab = loadExposure(storage, key);
  assert.equal(recordExposure(storage, key), "browser-local-sticky");
  assert.equal(refreshExposure(earlierTab, storage, key).exposed, true);
  const fresh = loadExposure(storage, exposureKey("pack", reviewCase));
  assert.equal(fresh.exposed, true);
  assert.equal(annotationExport(reviewCase, {...fresh, marks: [], notes: ""}, 1).candidate_exposure, "model-exposed");
  assert.equal(loadExposure(storage, exposureKey("other-pack", reviewCase)).exposed, false);
  assert.equal(loadExposure(storage, exposureKey("pack", {...reviewCase, recording: {...recording, audio_sha256: "different-audio"}})).exposed, false);
});
test("unavailable exposure storage never creates an independent annotation claim", () => {
  const storage = { getItem() { throw new Error("unavailable"); }, setItem() { throw new Error("unavailable"); } };
  const state = loadExposure(storage, "key");
  assert.equal(state.exposed, true);
  assert.equal(state.exposureHistory, "unavailable-assume-exposed");
  assert.equal(recordExposure(storage, "key"), "unavailable-assume-exposed");
  const output = annotationExport(reviewCase, {...state, marks: [], notes: ""}, 1);
  assert.equal(output.candidate_exposure, "model-exposed");
  assert.equal(output.gold, false);
});

test("seek limits follow the audio clock, not an independent timer", () => {
  assert.equal(clampSeek(-2, 20), 0);
  assert.equal(clampSeek(25, 20), 20);
  assert.equal(clampSeek(5.25, 20), 5.25);
  assert.throws(() => clampSeek(NaN, 20));
  assert.throws(() => clampSeek(1, Infinity));
  assert.throws(() => clampSeek(1, 0));
});
test("current and upcoming chords recalculate after forward and backward seeks", () => {
  const events = [ {start_seconds: 0, end_seconds: 5, label: "G"},
    {start_seconds: 5, end_seconds: 10, label: "B"}, {start_seconds: 10, end_seconds: 20, label: "C"} ];
  assert.equal(playbackSnapshot(events, 9).current.label, "B");
  assert.deepEqual(playbackSnapshot(events, 9).upcoming.map(event => event.label), ["C"]);
  assert.equal(playbackSnapshot(events, 1).current.label, "G");
  assert.deepEqual(playbackSnapshot(events, 1).upcoming.map(event => event.label), ["B", "C"]);
  assert.equal(playbackSnapshot(events, 5).current.label, "B");
  assert.equal(playbackSnapshot(events, 20).current, null);
  assert.deepEqual(playbackSnapshot(events, 20).upcoming, []);
});
const evidence = { schema_version: "automatic-draft-evidence-1.0", recording, review_points: [
  { start_seconds: 4, end_seconds: 10, reason: "Chord roots differ", priority_kind: "root_disagreement" }
] };
test("automatic disagreement suggestions require exact audio pairing and bounded windows", () => {
  assert.equal(validateEvidence(evidence, recording), evidence);
  for (const change of [{ id: "different" }, {audio_sha256: "different"}, {duration_seconds: 21}, {sample_rate_hz: 200}]) {
    assert.throws(() => validateEvidence({...evidence, recording: {...recording, ...change}}, recording));
  }
  for (const point of [{start_seconds: -1, end_seconds: 4, reason: "Mismatch"},
    {start_seconds: 2, end_seconds: 21, reason: "Mismatch"}, {start_seconds: 5, end_seconds: 5, reason: "Mismatch"},
    {start_seconds: 1, end_seconds: 2, reason: ""}, {start_seconds: NaN, end_seconds: 5, reason: "Mismatch"}]) {
    assert.throws(() => validateEvidence({...evidence, review_points: [point]}, recording));
  }
});
test("one tap captures the current audio position, source offset and displayed chord without manual entries", () => {
  const report = captureFeedback(reviewCase, 6.25, chart, "tap-1", "2026-10-10T12:00:00Z");
  assert.equal(report.playback_seconds, 6.25);
  assert.equal(report.source_seconds, 16.25);
  assert.equal(report.displayed_chord, "G");
  assert.equal(report.reason, "not-sure");
  assert.equal(report.note, "");
  assert.equal(captureFeedback(reviewCase, 5.5, chart, "gap", "now").displayed_chord, null);
  assert.equal(captureFeedback(reviewCase, 20, chart, "ended", "now").displayed_chord, null);
});
test("feedback rejects invalid clock readings and a chart from other audio", () => {
  for (const time of [NaN, Infinity, -1, 20.01]) assert.throws(() => captureFeedback(reviewCase, time, chart, "tap", "now"));
  assert.throws(() => captureFeedback(reviewCase, 5, {...chart, recording: {...recording, audio_sha256: "wrong"}}, "tap", "now"));
});
test("feedback survives a fresh session with optional reason and note edits", () => {
  const values = new Map();
  const storage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)};
  const key = feedbackKey("pack", reviewCase);
  const report = {...captureFeedback(reviewCase, 6.25, chart, "tap-1", "now"), reason: "late-change", note: "guitar changes first"};
  assert.equal(loadFeedback(storage, key, reviewCase, "pack").feedback.length, 0);
  assert.equal(saveFeedback(storage, key, reviewCase, "pack", [report]), "saved-on-this-browser");
  assert.deepEqual(loadFeedback(storage, key, reviewCase, "pack").feedback, [report]);
  saveFeedback(storage, key, reviewCase, "pack", []);
  assert.deepEqual(loadFeedback(storage, key, reviewCase, "pack").feedback, []);
});
test("saved feedback cannot be silently paired with a different song or audio version", () => {
  const report = captureFeedback(reviewCase, 6.25, chart, "tap-1", "now");
  const storage = { getItem: () => JSON.stringify(feedbackExport(reviewCase, "pack", [report])) };
  assert.equal(loadFeedback(storage, "key", {...reviewCase, recording: {...recording, audio_sha256: "different"}}, "pack").persistence, "unavailable");
  assert.equal(loadFeedback(storage, "key", reviewCase, "another-pack").persistence, "unavailable");
  assert.notEqual(feedbackKey("pack", reviewCase), feedbackKey("pack", {...reviewCase, recording: {...recording, audio_sha256: "different"}}));
});
test("unavailable or corrupt browser storage preserves an honest fallback", () => {
  const report = captureFeedback(reviewCase, 6.25, chart, "tap-1", "now");
  const storage = {getItem() {throw new Error("blocked");}, setItem() {throw new Error("blocked");}};
  assert.equal(loadFeedback(storage, "key", reviewCase, "pack").persistence, "unavailable");
  assert.equal(saveFeedback(storage, "key", reviewCase, "pack", [report]), "unavailable");
  assert.equal(loadFeedback({getItem: () => "not-json"}, "key", reviewCase, "pack").persistence, "unavailable");
});
test("issue reports stay distinct from verified chord labels and manual annotations", () => {
  const report = captureFeedback(reviewCase, 6.25, chart, "tap-1", "now");
  const exported = feedbackExport(reviewCase, "pack", [report]);
  assert.equal(exported.schema_version, "playalong-feedback-1.0");
  assert.equal(exported.candidate_exposure, "model-exposed");
  assert.equal(exported.gold, false);
  assert.equal(exported.annotations, undefined);
  assert.match(exported.semantics, /reaction delay/);
  assert.deepEqual(annotationExport(reviewCase, {marks: [], exposed: true}, 1).annotations, []);
});
test("capo2 practice shapes preserve the Wonderwall chord qualities", () => {
  for (const [sounding, shape] of [["F#m7", "Em7"], ["A", "G"], ["Esus4", "Dsus4"], ["B7sus4", "A7sus4"]]) {
    assert.equal(transposePracticeLabel(sounding, 2), shape);
    assert.equal(practiceLabel(sounding, "sounding-pitches", 2), sounding);
  }
});
test("capo display transposes named slash bass while preserving relative bass and unknown labels", () => {
  assert.equal(transposePracticeLabel("F#m7/C#", 2), "Em7/B");
  assert.equal(transposePracticeLabel("Bbmaj7/F", 2), "Abmaj7/Eb");
  assert.equal(transposePracticeLabel("F#:min7/b3", 2), "E:min7/b3");
  for (const label of ["N", "X", "?", "unknown"]) assert.equal(transposePracticeLabel(label, 2), label);
  assert.throws(() => transposePracticeLabel("F#m7", -2));
  assert.throws(() => transposePracticeLabel("F#m7", 1.5));
});
test("capo-view feedback preserves raw detector output and the shape actually displayed", () => {
  const sourceChart = {...chart, chords: [{start_seconds: 0, end_seconds: 20, label: "F#m7/C#"}]};
  const report = captureFeedback(reviewCase, 6.25, sourceChart, "shape-tap", "now", {view: "capo-shapes", capo: 2});
  assert.equal(report.raw_sounding_chord, "F#m7/C#");
  assert.equal(report.displayed_chord, "Em7/B");
  assert.equal(report.practice_view, "capo-shapes");
  assert.equal(report.practice_capo, 2);
  assert.equal(sourceChart.chords[0].label, "F#m7/C#");
  const original = captureFeedback(reviewCase, 6.25, sourceChart, "original-tap", "now", {view: "sounding-pitches", capo: 2});
  assert.equal(original.displayed_chord, "F#m7/C#");
  assert.equal(original.practice_capo, 0);
});
test("core chords reduce only known added notes while full display stays unchanged", () => {
  const examples = [["Em7", "Em"], ["Cmaj7", "C"], ["Cadd9", "C"],
    ["G7", "G"], ["A7sus4", "Asus4"], ["C:7", "C"], ["E:min7", "Em"],
    ["C:maj7", "C"], ["C:add9", "C"], ["A:7sus4", "Asus4"],
    ["Gminor7", "Gm"], ["Cmaj(add9)", "C"], ["C(1,3,5,9)", "C"], ["Asus4(b7)", "Asus4"],
    ["A:sus4(b7)", "Asus4"], ["D:maj(add9)/F#", "D/F#"]];
  for (const [full, core] of examples) {
    assert.equal(coreChordLabel(full), core);
    assert.equal(practiceLabel(full, "sounding-pitches", 0), full);
    assert.equal(practiceLabel(full, "sounding-pitches", 0, "core-chords"), core);
  }
});
test("core qualities contain only pitch classes already in each full chord", () => {
  // Independently specified intervals check the musical subset, including sus4.
  const examples = [
    ["Cm7", [0, 3, 7, 10], "Cm", [0, 3, 7]],
    ["Cmaj7", [0, 4, 7, 11], "C", [0, 4, 7]],
    ["Cadd9", [0, 2, 4, 7], "C", [0, 4, 7]],
    ["C7", [0, 4, 7, 10], "C", [0, 4, 7]],
    ["C7sus4", [0, 5, 7, 10], "Csus4", [0, 5, 7]]
  ];
  for (const [full, fullNotes, core, coreNotes] of examples) {
    assert.equal(coreChordLabel(full), core);
    assert.equal(coreNotes.every(note => fullNotes.includes(note)), true);
  }
});
test("D and Dsus4 remain different; unsupported and unknown qualities remain explicit", () => {
  assert.notEqual(coreChordLabel("D"), coreChordLabel("Dsus4"));
  for (const label of ["D", "Dm", "Dsus2", "Dsus4", "Ddim", "Ddim7", "Daug", "D5", "Dm7b5", "D6", "Dm6", "Dmmaj7",
    "Dsus4(7)", "DM7", "D:dim7", "D:hdim7", "D:aug", "D:sus4(7)", "Dunknown", "Dadd9/unknown", "N", "X", "?", "unknown"]) {
    assert.equal(coreChordLabel(label), label);
  }
  assert.equal(displayedChord("X", "sounding-pitches", 0, "core-chords"), "Unclear");
  assert.equal(displayedChord("N", "sounding-pitches", 0, "core-chords"), "No chord");
});
test("capo transposition precedes core reduction and preserves named or relative bass", () => {
  for (const [source, result] of [["F#m7/C#", "Em/B"], ["Bbmaj7/F", "Ab/Eb"],
    ["F#:min7/b3", "Em/b3"], ["B7sus4/5", "Asus4/5"]]) {
    assert.equal(practiceLabel(source, "capo-shapes", 2, "core-chords"), result);
  }
  assert.throws(() => practiceLabel("Em7", "sounding-pitches", 0, "guess"));
});
test("core feedback preserves raw full chord, played shape, quality mode and unchanged chart times", () => {
  const sourceChart = {...chart, chords: [{start_seconds: 0, end_seconds: 20, label: "F#m7/C#"}]};
  const original = JSON.stringify(sourceChart);
  const report = captureFeedback(reviewCase, 6.25, sourceChart, "core-tap", "now", {view: "capo-shapes", capo: 2, qualityMode: "core-chords"});
  assert.equal(report.raw_sounding_chord, "F#m7/C#");
  assert.equal(report.displayed_chord, "Em/B");
  assert.equal(report.practice_view, "capo-shapes");
  assert.equal(report.practice_capo, 2);
  assert.equal(report.quality_mode, "core-chords");
  assert.equal(JSON.stringify(sourceChart), original);
  assert.equal(captureFeedback(reviewCase, 6.25, chart, "full", "now").quality_mode, "full-chords");
  assert.throws(() => captureFeedback(reviewCase, 6.25, chart, "invalid", "now", {qualityMode: "guess"}));
  assert.throws(() => captureFeedback(reviewCase, 6.25, chart, "invalid", "now", {qualityMode: ""}));
});
test("core display leaves uncertainty, silence and temporal gaps intact in feedback", () => {
  const sourceChart = {...chart, chords: [{start_seconds: 0, end_seconds: 5, label: "X"}, {start_seconds: 6, end_seconds: 20, label: "N"}]};
  const mode = {qualityMode: "core-chords"};
  assert.equal(captureFeedback(reviewCase, 1, sourceChart, "unknown", "now", mode).displayed_chord, "Unclear");
  assert.equal(captureFeedback(reviewCase, 1, sourceChart, "unknown", "now", mode).raw_sounding_chord, "X");
  assert.equal(captureFeedback(reviewCase, 5.5, sourceChart, "gap", "now", mode).displayed_chord, null);
  assert.equal(captureFeedback(reviewCase, 6, sourceChart, "silence", "now", mode).displayed_chord, "No chord");
});
test("feedback reload preserves quality choice, accepts old reports and rejects unknown new modes", () => {
  const values = new Map();
  const storage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)};
  const report = captureFeedback(reviewCase, 6.25, chart, "core", "now", {qualityMode: "core-chords"});
  saveFeedback(storage, "key", reviewCase, "pack", [report]);
  assert.deepEqual(loadFeedback(storage, "key", reviewCase, "pack").feedback, [report]);
  const oldReport = {...report}; delete oldReport.quality_mode;
  storage.setItem("key", JSON.stringify(feedbackExport(reviewCase, "pack", [oldReport])));
  assert.deepEqual(loadFeedback(storage, "key", reviewCase, "pack").feedback, [oldReport]);
  storage.setItem("key", JSON.stringify(feedbackExport(reviewCase, "pack", [{...report, quality_mode: "unknown-mode"}])));
  assert.equal(loadFeedback(storage, "key", reviewCase, "pack").persistence, "unavailable");
});
test("core timeline merges contiguous equal shapes without changing raw labels or feedback times", () => {
  const events = [{start_seconds: 0, end_seconds: 5, label: "F#m7"}, {start_seconds: 5, end_seconds: 10, label: "F#m"},
    {start_seconds: 10, end_seconds: 15, label: "Esus4"}, {start_seconds: 15, end_seconds: 20, label: "E"}];
  const original = JSON.stringify(events);
  const displayed = practiceTimeline(events, "capo-shapes", 2, "core-chords");
  assert.deepEqual(displayed.map(event => [event.start_seconds, event.end_seconds, event.label]), [[0, 10, "Em"], [10, 15, "Dsus4"], [15, 20, "D"]]);
  assert.equal(playbackSnapshot(displayed, 6).upcoming[0].start_seconds, 10);
  assert.equal(JSON.stringify(events), original);
  const sourceChart = {...chart, chords: events};
  const report = captureFeedback(reviewCase, 6, sourceChart, "merged", "now", {view: "capo-shapes", capo: 2, qualityMode: "core-chords"});
  assert.equal(report.playback_seconds, 6);
  assert.equal(report.raw_sounding_chord, "F#m");
  assert.equal(report.displayed_chord, "Em");
  assert.equal(practiceTimeline(events, "capo-shapes", 2).length, events.length);
});
test("core timeline never bridges gaps, silence, uncertainty or suspended-to-major changes", () => {
  const events = [{start_seconds: 0, end_seconds: 1, label: "Cadd9"}, {start_seconds: 2, end_seconds: 3, label: "C"},
    {start_seconds: 3, end_seconds: 4, label: "X"}, {start_seconds: 4, end_seconds: 5, label: "X"},
    {start_seconds: 5, end_seconds: 6, label: "N"}, {start_seconds: 6, end_seconds: 7, label: "N"},
    {start_seconds: 7, end_seconds: 8, label: "Dsus4"}, {start_seconds: 8, end_seconds: 9, label: "D"}];
  const displayed = practiceTimeline(events, "sounding-pitches", 0, "core-chords");
  assert.equal(displayed.length, events.length);
  assert.equal(currentEvent(displayed, 1.5), null);
  assert.equal(currentEvent(displayed, 3.5).label, "X");
  assert.equal(currentEvent(displayed, 5.5).label, "N");
  assert.equal(currentEvent(displayed, 7.5).label, "Dsus4");
});
console.log(`${checks} review helper checks passed`);
