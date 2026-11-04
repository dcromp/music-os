"use strict";
const assert = require("node:assert/strict");
const { annotationExport, validateCandidate, currentEvent, exposureKey, loadExposure, recordExposure, refreshExposure, validateEvidence, clampSeek, playbackSnapshot, createPlaybackFrameLoop, feedbackKey, feedbackExport, captureFeedback, loadFeedback, saveFeedback, transposePracticeLabel, practiceLabel, coreChordLabel, displayedChord, practiceTimeline,
  currentHold, timingWindow, validateRhythmManifest, beatPosition, estimatedSpan, durationCaption, durationPresentation, holdBarDivisions, correctedDisplayEvents, validatePracticeManifest, safeTeachingURL, validateOnlineChecksManifest, pairedOnlineChecks, onlineFindingReview, onlineReviewSummary, validateLearningManifest, practiceProgressKey, practiceProgressExport, loadPracticeProgress, savePracticeProgress, nextPracticeStep, initialPracticeStep } = require("./app.js");
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
function frameFixture(renderOverride) {
  const audio = {currentTime: 4.07, paused: false, ended: false}, queue = new Map(), callbacks = new Map(), drawn = [], errors = [];
  let nextId = 0;
  const events = [{start_seconds: 2.414875283446712, end_seconds: 4.08671201814059, label: "A"},
    {start_seconds: 4.08671201814059, end_seconds: 4.829750566893424, label: "D"},
    {start_seconds: 4.829750566893424, end_seconds: 7.337505668934241, label: "E"}];
  const draw = () => drawn.push(playbackSnapshot(events, audio.currentTime).current?.label || null);
  const loop = createPlaybackFrameLoop({
    requestFrame: callback => { const id = ++nextId; queue.set(id, callback); callbacks.set(id, callback); return id; },
    cancelFrame: id => queue.delete(id), isPlaying: () => !audio.paused && !audio.ended,
    render: () => renderOverride ? renderOverride(draw) : draw(), onError: error => errors.push(error)
  });
  const frame = () => {
    assert.equal(queue.size, 1, "one refresh must be pending");
    const [id, callback] = queue.entries().next().value; queue.delete(id); callback();
  };
  return {audio, loop, queue, callbacks, drawn, errors, frame};
}
test("a frame refresh crosses the native D boundary without waiting for timeupdate", () => {
  const fixture = frameFixture(); fixture.loop.start(); fixture.frame();
  assert.deepEqual(fixture.drawn, ["A"]);
  fixture.audio.currentTime = 4.09; fixture.frame();
  assert.deepEqual(fixture.drawn, ["A", "D"]);
  fixture.audio.currentTime = 4.83; fixture.frame();
  assert.deepEqual(fixture.drawn, ["A", "D", "E"]);
  assert.equal(fixture.audio.currentTime, 4.83);
  fixture.loop.stop();
});
test("duplicate play and playing starts keep a single pending frame", () => {
  const fixture = frameFixture();
  fixture.loop.start(); fixture.loop.start(); fixture.loop.start();
  assert.equal(fixture.queue.size, 1); fixture.frame();
  assert.deepEqual(fixture.drawn, ["A"]); assert.equal(fixture.queue.size, 1);
  fixture.loop.start(); assert.equal(fixture.queue.size, 1); fixture.loop.stop();
});
test("pause and end cancel queued work while a resumed seek uses the actual audio clock", () => {
  const fixture = frameFixture(); fixture.loop.start();
  const cancelled = fixture.callbacks.values().next().value;
  fixture.audio.paused = true; fixture.loop.stop(); assert.equal(fixture.queue.size, 0);
  fixture.audio.currentTime = 5; cancelled(); assert.deepEqual(fixture.drawn, []);
  fixture.audio.currentTime = 4.1; fixture.audio.paused = false; fixture.loop.start();
  cancelled(); assert.equal(fixture.queue.size, 1); assert.deepEqual(fixture.drawn, []);
  fixture.frame(); assert.deepEqual(fixture.drawn, ["D"]);
  const afterResume = Array.from(fixture.callbacks.values()).at(-1);
  fixture.audio.ended = true; fixture.loop.stop(); afterResume();
  assert.equal(fixture.queue.size, 0); assert.deepEqual(fixture.drawn, ["D"]);
  fixture.audio.ended = false; fixture.audio.currentTime = 3; fixture.loop.start(); fixture.frame();
  assert.deepEqual(fixture.drawn, ["D", "A"]); fixture.loop.stop();
});
test("a stopped media clock ends refreshing even if its pause event was missed", () => {
  const fixture = frameFixture(); fixture.loop.start(); fixture.audio.paused = true; fixture.frame();
  assert.deepEqual(fixture.drawn, []); assert.equal(fixture.queue.size, 0);
});
test("a failed renderer stops the frame loop without an uncaught error and can recover", () => {
  let broken = true;
  const fixture = frameFixture(draw => { if (broken) throw new Error("render failed"); draw(); });
  fixture.loop.start(); assert.doesNotThrow(fixture.frame);
  assert.equal(fixture.errors.length, 1); assert.equal(fixture.queue.size, 0); assert.deepEqual(fixture.drawn, []);
  broken = false; fixture.audio.currentTime = 5; fixture.loop.start(); fixture.frame();
  assert.deepEqual(fixture.drawn, ["E"]); fixture.loop.stop();
});
test("missing animation-frame support leaves media-event rendering available", () => {
  let rendered = 0;
  for (const options of [{}, {requestFrame() { throw new Error("must require cancellation too"); }}]) {
    const loop = createPlaybackFrameLoop({...options, isPlaying: () => true, render: () => { rendered++; }});
    assert.doesNotThrow(() => { loop.start(); loop.start(); loop.stop(); });
  }
  assert.equal(rendered, 0);
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
test("current hold measures full duration and stops at its own end before an uncovered gap", () => {
  const held = currentHold(chart.chords, 4);
  assert.deepEqual([held.total_seconds, held.elapsed_seconds, held.remaining_seconds, held.progress_fraction], [5, 4, 1, 0.8]);
  assert.equal(currentHold(chart.chords, 5), null);
  assert.equal(currentHold(chart.chords, 5.9), null);
  assert.equal(currentHold(chart.chords, 6).event.label, "G");
  assert.equal(currentHold(chart.chords, 6).progress_fraction, 0);
  assert.equal(currentHold(chart.chords, 20), null);
});
test("current hold and proportional window recalculate from the audio clock after backward seek", () => {
  assert.equal(currentHold(chart.chords, 18).remaining_seconds, 2);
  assert.equal(currentHold(chart.chords, 1).remaining_seconds, 4);
  const later = timingWindow(chart.chords, 18, 20), earlier = timingWindow(chart.chords, 1, 20);
  assert.equal(later.now_seconds, 18); assert.equal(earlier.now_seconds, 1);
  assert.equal(earlier.blocks[0].event.label, "C");
  assert.equal(later.blocks[0].event.label, "G");
  assert.throws(() => currentHold(chart.chords, NaN));
  assert.throws(() => timingWindow(chart.chords, NaN, 20));
});
test("timeline geometry reflects a two-to-one duration ratio rather than equal chord cards", () => {
  const events = [{start_seconds: 0, end_seconds: 4, label: "C"}, {start_seconds: 4, end_seconds: 6, label: "G"}];
  const window = timingWindow(events, 0, 6, 6, 0);
  assert.equal(window.blocks[0].width_fraction, 2 / 3);
  assert.equal(window.blocks[1].width_fraction, 1 / 3);
  assert.equal(window.blocks[1].offset_fraction, 2 / 3);
  assert.equal(window.playhead_fraction, 0);
  assert.equal(timingWindow(events, 2, 6, 6, 4).playhead_fraction, 1 / 3);
});
test("timing strip represents uncovered gaps, unknown labels and silence as distinct intervals", () => {
  const events = [{start_seconds: 1, end_seconds: 2, label: "C"}, {start_seconds: 3, end_seconds: 4, label: "X"},
    {start_seconds: 4, end_seconds: 5, label: "N"}];
  const blocks = timingWindow(events, 0, 6, 6, 0).blocks;
  assert.deepEqual(blocks.map(block => block.kind), ["gap", "chord", "gap", "unclear", "silence", "gap"]);
  assert.deepEqual(blocks.map(block => [block.start_seconds, block.end_seconds]), [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6]]);
  assert.ok(Math.abs(blocks.reduce((sum, block) => sum + block.width_fraction, 0) - 1) < 1e-12);
});
test("window clipping preserves the original long hold and never extends beyond the recording", () => {
  const events = [{start_seconds: 0, end_seconds: 20, label: "C"}];
  const original = JSON.stringify(events);
  const window = timingWindow(events, 10, 20, 8, 2);
  assert.deepEqual([window.start_seconds, window.end_seconds], [8, 16]);
  assert.equal(window.blocks[0].width_fraction, 1);
  assert.equal(window.blocks[0].event.start_seconds, 0);
  assert.equal(window.blocks[0].event.end_seconds, 20);
  assert.equal(window.playhead_fraction, 0.25);
  assert.equal(timingWindow(events, 20, 20).playhead_fraction, 1);
  assert.deepEqual(timingWindow(events, 20, 20, 8, 0).blocks, []);
  assert.equal(JSON.stringify(events), original);
});
test("timing window rejects overlapping, invalid or nonfinite spans and empty duration", () => {
  for (const events of [[{start_seconds: 0, end_seconds: 21, label: "C"}],
    [{start_seconds: 0, end_seconds: 4, label: "C"}, {start_seconds: 3, end_seconds: 5, label: "G"}],
    [{start_seconds: 0, end_seconds: Infinity, label: "C"}]]) assert.throws(() => timingWindow(events, 0, 20));
  assert.throws(() => timingWindow([], 0, 0));
  assert.throws(() => timingWindow([], 0, 20, 0));
  assert.throws(() => timingWindow([], 0, 20, 4, 4));
});
test("core merged hold duration uses the whole displayed span without changing feedback or raw times", () => {
  const events = [{start_seconds: 0, end_seconds: 5, label: "F#m7"}, {start_seconds: 5, end_seconds: 10, label: "F#m"},
    {start_seconds: 10, end_seconds: 20, label: "Esus4"}];
  const raw = JSON.stringify(events), displayed = practiceTimeline(events, "capo-shapes", 2, "core-chords");
  const hold = currentHold(displayed, 7);
  assert.equal(hold.event.label, "Em"); assert.equal(hold.total_seconds, 10); assert.equal(hold.remaining_seconds, 3);
  const reported = captureFeedback(reviewCase, 7, {...chart, chords: events}, "tap", "now", {view: "capo-shapes", capo: 2, qualityMode: "core-chords"});
  assert.equal(reported.raw_sounding_chord, "F#m"); assert.equal(reported.playback_seconds, 7);
  assert.equal(JSON.stringify(events), raw);
});
const timedRecording = {...recording, audio_sha256: "a".repeat(64)};
const timedCase = {...reviewCase, recording: timedRecording};
const rhythmCase = {recording: timedRecording, beat_times_seconds: Array.from({length: 41}, (_, index) => index * 0.5),
  pulse_bpm: 120, beats_per_bar: 4, meter_label: "4/4 assumed", status: "estimated"};
const rhythmManifest = {schema_version: "playalong-rhythm-1.0", cases: [rhythmCase]};
const copied = value => JSON.parse(JSON.stringify(value));
test("valid beat grids are paired to the exact recording and offer approximate full and half bars", () => {
  const paired = validateRhythmManifest(rhythmManifest, [timedCase]).get(recording.id);
  assert.equal(paired, rhythmCase);
  assert.deepEqual(estimatedSpan(paired, 0, 2), {beats: 4, bars: 1});
  assert.deepEqual(estimatedSpan(paired, 0, 1), {beats: 2, bars: 0.5});
  assert.equal(durationCaption(0, 1, paired), "~½ bar · 1.0 s");
  assert.equal(durationCaption(0, 4, paired), "~2 bars · 4.0 s");
});
test("positive short holds never round to zero bars or beats", () => {
  assert.equal(durationCaption(0, 0.03, rhythmCase), "<0.1 bar · <0.1 s");
  assert.equal(durationCaption(0, 0.01, {...rhythmCase, beats_per_bar: null}), "<0.1 beat · <0.1 s");
});
test("fractional beat interpolation follows varying beat intervals without snapping chord boundaries", () => {
  const variable = {...rhythmCase, beat_times_seconds: [0, 0.5, 1.5, 2, 3]};
  assert.equal(beatPosition(variable.beat_times_seconds, 1), 1.5);
  assert.deepEqual(estimatedSpan(variable, 0.25, 2.5), {beats: 3, bars: 0.75});
  assert.equal(beatPosition(variable.beat_times_seconds, 3), 4);
  assert.equal(beatPosition(variable.beat_times_seconds, -0.01), null);
  assert.equal(beatPosition(variable.beat_times_seconds, 3.01), null);
});
test("beat estimates fall back to seconds outside covered pulses instead of extrapolating silence or outro", () => {
  const trimmed = {...rhythmCase, beat_times_seconds: [1, 2, 3]};
  assert.equal(estimatedSpan(trimmed, 0, 2), null);
  assert.equal(estimatedSpan(trimmed, 2, 4), null);
  assert.equal(durationCaption(0, 2, trimmed), "2.0 s");
  assert.equal(durationCaption(2, 4, trimmed), "2.0 s");
  assert.equal(durationCaption(0, 2, null), "2.0 s");
  assert.equal(beatPosition([], 1), null);
});
test("compound meter only gets bars when pulse unit is stated; variable meter remains beat-count only", () => {
  const compound = {...rhythmCase, beats_per_bar: 2, meter_label: "6/8 · 2 dotted-quarter beats per bar"};
  assert.equal(validateRhythmManifest({...rhythmManifest, cases: [compound]}, [timedCase]).size, 1);
  assert.equal(durationCaption(0, 1, compound), "~1 bar · 1.0 s");
  const unverified = {...rhythmCase, beats_per_bar: null, meter_label: "6/8; pulse unverified"};
  assert.equal(durationCaption(0, 1, unverified), "~2 beats · 1.0 s");
  const varies = {...unverified, meter_label: "Beat count; meter varies"};
  assert.equal(validateRhythmManifest({...rhythmManifest, cases: [varies]}, [timedCase]).get(recording.id).beats_per_bar, null);
  assert.equal(estimatedSpan(varies, 0, 4).bars, null);
});
test("rhythm payload validates all timestamps and rejects duplicate identities or malformed pulse metadata", () => {
  for (const change of [{beat_times_seconds: [0]}, {beat_times_seconds: [0, 0]}, {beat_times_seconds: [-0.1, 1]},
    {beat_times_seconds: [0, 21]}, {beat_times_seconds: [0, NaN]}, {beat_times_seconds: [1, 0]},
    {beat_times_seconds: Array.from({length: 5001}, (_, index) => index / 1000)}, {pulse_bpm: 0}, {pulse_bpm: 301},
    {pulse_bpm: Infinity}, {beats_per_bar: 3}, {meter_label: ""}, {status: "verified"}]) {
    assert.throws(() => validateRhythmManifest({...rhythmManifest, cases: [{...rhythmCase, ...change}]}, [timedCase]));
  }
  assert.throws(() => validateRhythmManifest({...rhythmManifest, cases: [rhythmCase, rhythmCase]}, [timedCase]));
  assert.throws(() => validateRhythmManifest({schema_version: "wrong", cases: [rhythmCase]}, [timedCase]));
});
test("mismatched rhythm hashes fall back per case while larger valid packs retain matching old songs", () => {
  const otherRecording = {...timedRecording, id: "other", audio_sha256: "b".repeat(64)};
  const other = {...rhythmCase, recording: otherRecording};
  const extended = {...rhythmManifest, cases: [rhythmCase, other]};
  assert.equal(validateRhythmManifest(extended, [timedCase]).size, 1);
  const wrong = {...rhythmCase, recording: {...timedRecording, audio_sha256: "c".repeat(64)}};
  const matches = validateRhythmManifest({...rhythmManifest, cases: [wrong, other]}, [timedCase, {recording: otherRecording}]);
  assert.equal(matches.has(recording.id), false); assert.equal(matches.has("other"), true);
  for (const change of [{sample_rate_hz: 200}, {duration_seconds: 21}]) {
    assert.equal(validateRhythmManifest({...rhythmManifest, cases: [{...rhythmCase, recording: {...timedRecording, ...change}}]}, [timedCase]).size, 0);
  }
});
const practiceCase = {recording: timedRecording, meter_label: "4/4 practice", beats_description: "Count four beats", status: "practice-suggestion", note: "Recorded parts may differ.",
  patterns: [{id: "start", name: "Steady downstrokes", counts: ["1", "2", "3", "4"], strokes: ["D", "D", "D", "D"], description: "Start slowly."},
    {id: "next", name: "Down and up", counts: ["1", "&", "2", "&", "3", "&", "4", "&"], strokes: ["D", "U", "D", "U", "D", "U", "D", "U"], description: "Keep the hand moving."}]};
const practiceManifest = {schema_version: "playalong-practice-1.0", cases: [practiceCase]};
test("practice suggestions validate two original drills without treating them as detected strumming", () => {
  assert.equal(validatePracticeManifest(practiceManifest, [timedCase]).get(recording.id), practiceCase);
  assert.equal(practiceCase.status, "practice-suggestion");
  assert.equal(practiceCase.patterns[0].strokes.length, 4);
  const house = {...practiceCase, meter_label: "6/8", patterns: [{...practiceCase.patterns[0], counts: ["1", "2", "3", "4", "5", "6"], strokes: ["D", "—", "—", "D", "—", "—"]}]};
  assert.equal(validatePracticeManifest({...practiceManifest, cases: [house]}, [timedCase]).size, 1);
});
test("practice data rejects invalid counts, strokes, duplicate patterns and oversized text", () => {
  for (const change of [{counts: []}, {counts: ["1"]}, {strokes: ["D", "D", "X", "D"]},
    {counts: Array(13).fill("1"), strokes: Array(13).fill("D")}, {counts: ["1", "2", "", "4"]},
    {id: ""}, {name: "x".repeat(101)}, {description: "x".repeat(601)}]) {
    assert.throws(() => validatePracticeManifest({...practiceManifest, cases: [{...practiceCase, patterns: [{...practiceCase.patterns[0], ...change}]}]}, [timedCase]));
  }
  assert.throws(() => validatePracticeManifest({...practiceManifest, cases: [{...practiceCase, patterns: [practiceCase.patterns[0], practiceCase.patterns[0]]}]}, [timedCase]));
  assert.throws(() => validatePracticeManifest({...practiceManifest, cases: [{...practiceCase, patterns: Array(3).fill(practiceCase.patterns[0])}]}, [timedCase]));
  assert.throws(() => validatePracticeManifest({...practiceManifest, cases: [practiceCase, practiceCase]}, [timedCase]));
});
test("practice pairing is per recording and independent from a missing or invalid beat grid", () => {
  const wrong = {...practiceCase, recording: {...timedRecording, audio_sha256: "d".repeat(64)}};
  assert.equal(validatePracticeManifest({...practiceManifest, cases: [wrong]}, [timedCase]).size, 0);
  assert.throws(() => validateRhythmManifest({schema_version: "broken"}, [timedCase]));
  assert.equal(validatePracticeManifest(practiceManifest, [timedCase]).size, 1);
  const other = {...practiceCase, recording: {...timedRecording, id: "new-other", audio_sha256: "e".repeat(64)}};
  assert.equal(validatePracticeManifest({...practiceManifest, cases: [practiceCase, other]}, [timedCase]).size, 1);
});
test("duration and strumming validation never changes saved feedback or source chart bytes", () => {
  const sourceBefore = JSON.stringify(chart), reports = [captureFeedback(reviewCase, 6, chart, "preserved", "now")];
  const feedbackBefore = JSON.stringify(reports);
  validateRhythmManifest(rhythmManifest, [timedCase]); validatePracticeManifest(practiceManifest, [timedCase]);
  currentHold(chart.chords, 6); timingWindow(chart.chords, 6, 20); durationCaption(6, 20, rhythmCase);
  assert.equal(JSON.stringify(chart), sourceBefore); assert.equal(JSON.stringify(reports), feedbackBefore);
});

const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const root = path.resolve(__dirname, "../.."), json = name => JSON.parse(fs.readFileSync(path.join(root, name), "utf8"));
const learningFixture = json("experiments/review/learning.json"), arrangementFixture = json("docs/FIRST_TEN_ARRANGEMENT_CHECK.json");
const learningCases = arrangementFixture.cases.map(item => ({id: item.recording.id, recording: item.recording}));
const learningPractice = validatePracticeManifest(json("experiments/review/practice.json"), learningCases);
const learning = validateLearningManifest(learningFixture, learningCases, learningPractice);
const clone = value => JSON.parse(JSON.stringify(value));
test("guitar-first source pins, selected order and exact audio identities match audited inputs", () => {
  const catalogue = json("catalogue/first-ten-review.json"), sources = [...arrangementFixture.sources, ...json("catalogue/starter-four-teaching-review.json").sources];
  for (const input of learningFixture.inputs) {
    assert.equal(crypto.createHash("sha256").update(fs.readFileSync(path.join(root, input.path))).digest("hex"), input.sha256);
  }
  assert.equal(learning.steps.length, 7); assert.equal(learning.guides.length, 2);
  assert.deepEqual(learning.steps.map(step => step.id), ["wild-thing", "knockin-on-heaven-s-door", "brown-eyed-girl", "twist-and-shout", "the-house-of-the-rising-sun", "wonderwall", "creep"]);
  for (const item of [...learning.steps, ...learning.guides]) {
    const proposal = catalogue.songs.find(song => song.id === item.id), paired = arrangementFixture.cases.find(song => song.song_id === item.id);
    assert.equal(item.recording.id, proposal.selected_recording.recording_id); assert.deepEqual(item.recording, paired.recording);
    if (item.status === "practice-suggestion") {
      assert.equal(proposal.practice_placement.track, "open-chord-rhythm"); assert.equal(item.order, learning.steps.indexOf(item) + 1);
      assert.equal(item.practice_pattern_id, learningPractice.get(item.recording.id).patterns[0].id);
    }
    for (const source of item.sources) assert.ok(sources.some(known => known.id === source.id && known.title === source.title && known.url === source.url));
  }
});
test("learning validation leaves source metadata and practice patterns unchanged", () => {
  const before = JSON.stringify(learningFixture), practiceBefore = JSON.stringify([...learningPractice]);
  const reversed = {...learningFixture, steps: [...learningFixture.steps].reverse()};
  assert.deepEqual(validateLearningManifest(reversed, learningCases, learningPractice).steps.map(step => step.order), [1, 2, 3, 4, 5, 6, 7]);
  assert.equal(JSON.stringify(learningFixture), before); assert.equal(JSON.stringify([...learningPractice]), practiceBefore);
});
test("learning paths filter unavailable recordings and preserve the source order in subset packs", () => {
  const subset = learningCases.filter(item => [learning.steps[5].recording.id, learning.steps[6].recording.id].includes(item.recording.id));
  const result = validateLearningManifest(learningFixture, subset, learningPractice);
  assert.equal(result.total_steps, 7); assert.deepEqual(result.steps.map(step => step.order), [6, 7]); assert.deepEqual(result.guides, []);
  const absent = validateLearningManifest(learningFixture, [{recording: {...learningCases[0].recording, id: "different-song"}}], learningPractice);
  assert.deepEqual(absent.steps, []); assert.deepEqual(absent.guides, []);
});
test("learning paths reject duplicate step IDs, orders and recording identities", () => {
  for (const mutate of [
    data => { data.steps[1].id = data.steps[0].id; },
    data => { data.steps[1].order = data.steps[0].order; },
    data => { data.steps[1].recording = data.steps[0].recording; },
    data => { data.guides[0].id = data.steps[0].id; },
    data => { data.guides[0].recording = data.steps[0].recording; },
    data => { data.steps[0].order = 0; },
    data => { data.steps[0].order = 1.5; },
  ]) {
    const data = clone(learningFixture); mutate(data); assert.throws(() => validateLearningManifest(data, learningCases, learningPractice));
  }
});
test("learning metadata rejects changed audio hash, rate or duration for an available recording", () => {
  for (const change of [{audio_sha256: "f".repeat(64)}, {sample_rate_hz: 44100}, {duration_seconds: 1}, {duration_seconds: NaN}]) {
    const data = clone(learningFixture); Object.assign(data.steps[0].recording, change);
    assert.throws(() => validateLearningManifest(data, learningCases, learningPractice));
  }
});
test("starting drills must exist on the exact paired practice recording, and riff guides cannot become strumming steps", () => {
  const wrong = clone(learningFixture); wrong.steps[0].practice_pattern_id = "invented-drill";
  assert.throws(() => validateLearningManifest(wrong, learningCases, learningPractice));
  const mismatched = new Map(learningPractice), id = learning.steps[0].recording.id;
  mismatched.set(id, {...mismatched.get(id), recording: {...learning.steps[0].recording, audio_sha256: "a".repeat(64)}});
  assert.throws(() => validateLearningManifest(learningFixture, learningCases, mismatched));
  assert.throws(() => validateLearningManifest(learningFixture, learningCases, new Map()));
  for (const change of [{practice_pattern_id: "steady-down"}, {order: 1}, {status: "practice-suggestion"}]) {
    const data = clone(learningFixture); Object.assign(data.guides[0], change);
    assert.throws(() => validateLearningManifest(data, learningCases, learningPractice));
  }
  assert.equal(learning.guides.every(item => !item.practice_pattern_id && !item.order), true);
});
test("teaching links require public HTTPS and never accept executable, local or credentialled URLs", () => {
  for (const value of ["javascript:alert(1)", "data:text/html,x", "file:///tmp/x", "http://example.com/a", "https://user:password@example.com/a",
    "https://localhost/a", "https://x.localhost/a", "https://127.0.0.1/a", "https://[::1]/a", "https://example.com:8080/a", " https://example.com/a", "https://example.com/\\x", "https://example.com/a\n"]) {
    assert.throws(() => safeTeachingURL(value));
    const data = clone(learningFixture); data.steps[0].sources[0].url = value;
    assert.throws(() => validateLearningManifest(data, learningCases, learningPractice));
  }
  assert.equal(safeTeachingURL("https://www.example.com/a%27b"), "https://www.example.com/a%27b");
  const duplicate = clone(learningFixture); duplicate.steps[0].sources.push(duplicate.steps[0].sources[0]);
  assert.throws(() => validateLearningManifest(duplicate, learningCases, learningPractice));
});
test("learning manifests reject malformed source pins and invalid optional metadata", () => {
  for (const change of [{path: "../private.json"}, {path: "/private.json"}, {path: "docs//private.json"}, {path: "docs/x.json?secret"}, {sha256: "missing"}]) {
    const data = clone(learningFixture); Object.assign(data.inputs[0], change);
    assert.throws(() => validateLearningManifest(data, learningCases, learningPractice));
  }
  for (const change of [{schema_version: "other"}, {status: "verified-lesson"}, {path_id: ""}, {revision: ""}, {steps: []}, {guides: null}]) {
    assert.throws(() => validateLearningManifest({...learningFixture, ...change}, learningCases, learningPractice));
  }
  const duplicated = clone(learningFixture); duplicated.inputs.push(duplicated.inputs[0]);
  assert.throws(() => validateLearningManifest(duplicated, learningCases, learningPractice));
});
test("practice progress keys isolate path revision, pack, step and audio, separately from issue feedback", () => {
  const step = learning.steps[0], key = practiceProgressKey(learning, "pack", step);
  assert.match(key, /^music-os-practice-progress:/);
  for (const other of [
    practiceProgressKey({...learning, path_id: "other"}, "pack", step),
    practiceProgressKey({...learning, revision: "2"}, "pack", step),
    practiceProgressKey(learning, "other-pack", step),
    practiceProgressKey(learning, "pack", {...step, id: "other-step"}),
    practiceProgressKey(learning, "pack", {...step, recording: {...step.recording, audio_sha256: "other"}}),
    feedbackKey("pack", {id: step.recording.id, recording: step.recording}),
  ]) assert.notEqual(key, other);
});
test("explicit practice marking and unmarking survive reload without implying mastery or audio completion", () => {
  const values = new Map(), storage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)}, step = learning.steps[0];
  assert.equal(loadPracticeProgress(storage, learning, "pack", step).practised, false);
  assert.equal(savePracticeProgress(storage, learning, "pack", step, true), "saved-on-this-browser");
  assert.deepEqual(loadPracticeProgress(storage, learning, "pack", step), {practised: true, persistence: "saved-on-this-browser"});
  savePracticeProgress(storage, learning, "pack", step, false);
  assert.equal(loadPracticeProgress(storage, learning, "pack", step).practised, false);
  const value = practiceProgressExport(learning, "pack", step, true);
  assert.equal(value.schema_version, "playalong-progress-1.0"); assert.equal(value.mastered, undefined); assert.equal(value.playback_seconds, undefined);
  assert.match(value.semantics, /not mastery/);
  assert.throws(() => savePracticeProgress(storage, learning, "pack", step, "true"));
});
test("saved practice progress cannot be reassigned to another path, step, pack or recording", () => {
  const step = learning.steps[0], saved = practiceProgressExport(learning, "pack", step, true);
  for (const change of [{schema_version: "wrong"}, {path_id: "other"}, {path_revision: "2"}, {step_id: "other"}, {pack_id: "other"}, {practised: "true"},
    {recording: {...step.recording, id: "other"}}, {recording: {...step.recording, audio_sha256: "different"}},
    {recording: {...step.recording, sample_rate_hz: 44100}}, {recording: {...step.recording, duration_seconds: 1}}]) {
    assert.deepEqual(loadPracticeProgress({getItem: () => JSON.stringify({...saved, ...change})}, learning, "pack", step), {practised: false, persistence: "unavailable"});
  }
});
test("unavailable or corrupt practice storage gives an honest tab-only fallback", () => {
  const step = learning.steps[0], blocked = {getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }};
  assert.deepEqual(loadPracticeProgress(blocked, learning, "pack", step), {practised: false, persistence: "unavailable"});
  assert.equal(savePracticeProgress(blocked, learning, "pack", step, true), "unavailable");
  for (const raw of ["broken", "null", "{}", "[]"]) {
    assert.equal(loadPracticeProgress({getItem: () => raw}, learning, "pack", step).persistence, "unavailable");
  }
});
test("next-song suggestions skip practised steps, wrap remaining gaps and never force a reset", () => {
  const progress = new Map(), steps = learning.steps.slice(0, 3), first = steps[0], second = steps[1], third = steps[2];
  assert.equal(nextPracticeStep(steps, progress), first);
  assert.equal(nextPracticeStep(steps, progress, first.id), second);
  progress.set(second.id, {practised: true}); assert.equal(nextPracticeStep(steps, progress, first.id), third);
  assert.equal(nextPracticeStep(steps, progress, third.id), first);
  progress.set(first.id, {practised: true}); progress.set(third.id, {practised: true});
  assert.equal(nextPracticeStep(steps, progress), null); assert.equal(nextPracticeStep(steps, progress, third.id), null);
  progress.set(first.id, {practised: false}); assert.equal(nextPracticeStep(steps, progress, first.id), null);
  assert.equal(nextPracticeStep(steps, progress), first);
  assert.equal(nextPracticeStep([], progress), null);
});
test("practice progress writes leave existing issue feedback and detector charts intact", () => {
  const values = new Map(), storage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)};
  const report = captureFeedback(reviewCase, 6, chart, "unchanged", "now"), key = feedbackKey("pack", reviewCase), step = learning.steps[0];
  saveFeedback(storage, key, reviewCase, "pack", [report]);
  const before = values.get(key), chartBefore = JSON.stringify(chart), sourceBefore = JSON.stringify(learningFixture);
  savePracticeProgress(storage, learning, "pack", step, true); savePracticeProgress(storage, learning, "pack", step, false);
  nextPracticeStep(learning.steps, new Map([[step.id, {practised: true}]]), step.id);
  assert.equal(values.get(key), before); assert.deepEqual(loadFeedback(storage, key, reviewCase, "pack").feedback, [report]);
  assert.equal(JSON.stringify(chart), chartBefore); assert.equal(JSON.stringify(learningFixture), sourceBefore);
});

test("initial practice choice resumes the first unpractised available step and keeps a complete path revisitable", () => {
  const progress = new Map(), steps = learning.steps.slice(0, 3), before = JSON.stringify(steps);
  assert.equal(initialPracticeStep(steps, progress), steps[0]);
  progress.set(steps[0].id, {practised: true}); assert.equal(initialPracticeStep(steps, progress), steps[1]);
  progress.set(steps[2].id, {practised: true}); assert.equal(initialPracticeStep(steps, progress), steps[1]);
  progress.set(steps[1].id, {practised: true}); assert.equal(initialPracticeStep([...steps].reverse(), progress), steps[0]);
  assert.equal(initialPracticeStep([], progress), null); assert.equal(JSON.stringify(steps), before);
  assert.equal(progress.get(steps[0].id).practised, true);
});

// Add durationPresentation, holdBarDivisions and correctedDisplayEvents to the
// existing app.js helper import. This fragment uses the existing test()/assert.
const displayTestRhythm = {
  beat_times_seconds: Array.from({length: 41}, (_, index) => index * 0.5),
  beats_per_bar: 4
};

test("visible duration captions distinguish quarter, half, full and multiple bars", () => {
  assert.deepEqual(durationPresentation(0, 1, displayTestRhythm),
    {compact: "~½ bar", full: "~½ bar · 1.0 s", unit: "bars"});
  assert.equal(durationPresentation(0, 0.5, displayTestRhythm).compact, "~¼ bar");
  assert.equal(durationPresentation(0, 2, displayTestRhythm).compact, "~1 bar");
  assert.equal(durationPresentation(0, 3, displayTestRhythm).compact, "~1½ bars");
  assert.equal(durationPresentation(0, 4, displayTestRhythm).compact, "~2 bars");
});

test("irregular duration estimates retain decimals instead of snapping to a half bar", () => {
  // At this pulse rate a bar lasts two seconds: 1.2 s = 0.6 bar.
  assert.equal(durationPresentation(0, 1.2, displayTestRhythm).compact, "~0.6 bar");
  assert.equal(durationPresentation(0, 2.4, displayTestRhythm).compact, "~1.2 bars");
  assert.equal(durationPresentation(0, 0.01, displayTestRhythm).compact, "<0.1 bar");
});

test("duration display respects compound pulse units, unknown meter and observed coverage", () => {
  // Two dotted-quarter pulses make a 6/8 bar; four pulses make two bars.
  const compound = {...displayTestRhythm, beats_per_bar: 2};
  assert.equal(durationPresentation(0, 2, compound).compact, "~2 bars");
  const unknownMeter = {...displayTestRhythm, beats_per_bar: null};
  assert.deepEqual(durationPresentation(0, 1, unknownMeter),
    {compact: "~2 beats", full: "~2 beats · 1.0 s", unit: "beats"});
  const trimmed = {...displayTestRhythm, beat_times_seconds: [1, 2, 3]};
  for (const [start, end] of [[0, 2], [2, 4]]) {
    assert.deepEqual(durationPresentation(start, end, trimmed),
      {compact: "2.0 s", full: "2.0 s", unit: "seconds"});
  }
  assert.deepEqual(durationPresentation(0, 2),
    {compact: "2.0 s", full: "2.0 s", unit: "seconds"});
});

const displayTestVariableRhythm = {
  beat_times_seconds: [0, 0.5, 1, 1.5, 2.5, 3.5, 5, 6.5, 8, 9.5, 11, 13, 15],
  beats_per_bar: 4
};
const displayTestLongEvent = {start_seconds: 0.25, end_seconds: 15, label: "A"};

test("hold divisions interpolate variable tempo from the original fractional-beat onset", () => {
  // Start is pulse 0.5. Four/eight pulses later are positions 4.5/8.5,
  // which interpolate to 3.0 s and 8.75 s in these independent timestamps.
  const before = JSON.stringify([displayTestLongEvent, displayTestVariableRhythm]);
  const divisions = holdBarDivisions(displayTestLongEvent, displayTestVariableRhythm, 0.25, 15);
  assert.deepEqual(divisions.map(item => item.time_seconds), [3, 8.75]);
  assert.ok(Math.abs(divisions[0].offset_fraction - 11 / 59) < 1e-12);
  assert.ok(Math.abs(divisions[1].offset_fraction - 34 / 59) < 1e-12);
  assert.equal(JSON.stringify([displayTestLongEvent, displayTestVariableRhythm]), before);
});

test("clipping a long hold preserves its onset-anchored divisions and full duration", () => {
  const divisions = holdBarDivisions(displayTestLongEvent, displayTestVariableRhythm, 5, 12);
  assert.equal(divisions.length, 1);
  assert.equal(divisions[0].time_seconds, 8.75);
  assert.ok(Math.abs(divisions[0].offset_fraction - 15 / 28) < 1e-12);
  assert.equal(durationPresentation(displayTestLongEvent.start_seconds,
    displayTestLongEvent.end_seconds, displayTestVariableRhythm).compact, "~2.9 bars");
  assert.deepEqual(holdBarDivisions(displayTestLongEvent, displayTestVariableRhythm, 3, 8.75), []);
});

test("hold divisions require covered declared meter and never add an end-boundary tick", () => {
  const event = {start_seconds: 0, end_seconds: 4, label: "A"};
  assert.deepEqual(holdBarDivisions(event, displayTestRhythm, 0, 4),
    [{time_seconds: 2, offset_fraction: 0.5}]);
  assert.deepEqual(holdBarDivisions(event, {...displayTestRhythm, beats_per_bar: 2}, 0, 4),
    [{time_seconds: 1, offset_fraction: 0.25}, {time_seconds: 2, offset_fraction: 0.5},
      {time_seconds: 3, offset_fraction: 0.75}]);
  assert.deepEqual(holdBarDivisions(event, {...displayTestRhythm, beats_per_bar: null}, 0, 4), []);
  assert.deepEqual(holdBarDivisions(event, {...displayTestRhythm, beat_times_seconds: [1, 2, 3]}, 0, 4), []);
  assert.deepEqual(holdBarDivisions(event, null, 0, 4), []);
});

const displayTestRecording = {
  id: "display-correction-recording", title: "Correction fixture",
  audio_sha256: "b".repeat(64), sample_rate_hz: 22050, duration_seconds: 40
};
const displayTestChart = {
  schema_version: "1.0", recording: displayTestRecording, analysis: {id: "native-analysis-1"},
  chords: [{start_seconds: 0, end_seconds: 24, label: "D"},
    {start_seconds: 24, end_seconds: 26, label: "E"},
    {start_seconds: 26, end_seconds: 40, label: "A"}]
};
const displayTestCorrection = {
  id: "reported-A-near-25", expected_event: {start_seconds: 24, end_seconds: 26, label: "E"},
  replacement_label: "A", reported_seconds: 25, timing_status: "native-boundaries-unverified",
  note: "User heard A around this moment; exact change boundaries remain unchecked."
};
const displayTestCorrectionSet = {
  schema_version: "reported-chord-corrections-1.0", status: "user-reported-provisional", gold: false,
  pack_id: "display-test-pack", primary_sha256: "c".repeat(64), analysis_id: "native-analysis-1",
  recording: displayTestRecording, corrections: [displayTestCorrection]
};
const cloneDisplayTest = value => JSON.parse(JSON.stringify(value));

test("a reported correction changes only the paired display event without mutating detector data", () => {
  const before = JSON.stringify([displayTestChart, displayTestCorrectionSet]);
  const events = correctedDisplayEvents(displayTestChart, displayTestCorrectionSet, "display-test-pack", "c".repeat(64));
  assert.deepEqual(events.map(event => [event.start_seconds, event.end_seconds, event.label]),
    [[0, 24, "D"], [24, 26, "A"], [26, 40, "A"]]);
  assert.equal(events[1].display_correction.id, "reported-A-near-25");
  assert.equal(events[0].display_correction, undefined);
  assert.equal(JSON.stringify([displayTestChart, displayTestCorrectionSet]), before);
  assert.equal(correctedDisplayEvents(displayTestChart, null, "display-test-pack", "c".repeat(64)), displayTestChart.chords);
  assert.equal(currentEvent(events, 25).label, "A");
  assert.equal(currentEvent(displayTestChart.chords, 25).label, "E");
});

test("reported display corrections reject other packs, chart hashes, analyses and recording identities", () => {
  const apply = set => correctedDisplayEvents(displayTestChart, set, "display-test-pack", "c".repeat(64));
  for (const change of [{pack_id: "another-pack"}, {primary_sha256: "d".repeat(64)},
    {analysis_id: "another-analysis"}, {schema_version: "other"}, {status: "reviewed"}, {gold: true}]) {
    assert.throws(() => apply({...displayTestCorrectionSet, ...change}));
  }
  for (const change of [{id: "another-recording"}, {audio_sha256: "e".repeat(64)},
    {sample_rate_hz: 44100}, {duration_seconds: 41}]) {
    assert.throws(() => apply({...displayTestCorrectionSet,
      recording: {...displayTestRecording, ...change}}));
  }
  for (const hash of [null, "", "c".repeat(63), "C".repeat(64)]) {
    assert.throws(() => correctedDisplayEvents(displayTestChart, displayTestCorrectionSet, "display-test-pack", hash));
  }
});

test("corrections require exact half-open native spans and reject duplicate or unmatched replacements", () => {
  const apply = correction => correctedDisplayEvents(displayTestChart,
    {...displayTestCorrectionSet, corrections: [correction]}, "display-test-pack", "c".repeat(64));
  for (const expected of [{start_seconds: 24.01, end_seconds: 26, label: "E"},
    {start_seconds: 24, end_seconds: 26.01, label: "E"}, {start_seconds: 24, end_seconds: 26, label: "D"}]) {
    assert.throws(() => apply({...displayTestCorrection, expected_event: expected}));
  }
  for (const change of [{reported_seconds: 23.99}, {reported_seconds: 26}, {reported_seconds: NaN},
    {timing_status: "verified"}, {replacement_label: ""}, {id: ""}, {note: ""}]) {
    assert.throws(() => apply({...displayTestCorrection, ...change}));
  }
  assert.equal(currentEvent(apply({...displayTestCorrection, reported_seconds: 24}), 24).label, "A");
  assert.throws(() => correctedDisplayEvents(displayTestChart,
    {...displayTestCorrectionSet, corrections: [displayTestCorrection, {...displayTestCorrection, id: "duplicate-event"}]},
    "display-test-pack", "c".repeat(64)));
});

test("corrected feedback persists raw E, displayed A and provisional provenance across reload", () => {
  const fixtureCase = {id: displayTestRecording.id, recording: displayTestRecording,
    origin: {source_offset_seconds: 10}};
  const before = JSON.stringify([displayTestChart, displayTestCorrectionSet]);
  const report = captureFeedback(fixtureCase, 25.2, displayTestChart, "corrected-tap", "now",
    {correction: displayTestCorrection});
  assert.equal(report.raw_sounding_chord, "E");
  assert.equal(report.displayed_chord, "A");
  assert.equal(report.candidate_analysis_id, "native-analysis-1");
  assert.equal(report.playback_seconds, 25.2);
  assert.equal(report.source_seconds, 35.2);
  assert.equal(report.display_correction_id, "reported-A-near-25");
  assert.equal(report.display_correction_status, "user-reported-provisional");
  assert.equal(report.display_correction_reported_seconds, 25);
  const values = new Map(), storage = {
    getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)
  };
  const key = feedbackKey("display-test-pack", fixtureCase);
  assert.equal(saveFeedback(storage, key, fixtureCase, "display-test-pack", [report]), "saved-on-this-browser");
  assert.deepEqual(loadFeedback(storage, key, fixtureCase, "display-test-pack").feedback, [report]);
  const exported = JSON.parse(values.get(key));
  assert.equal(exported.gold, false);
  const malformed = cloneDisplayTest(exported);
  delete malformed.feedback[0].display_correction_status;
  storage.setItem(key, JSON.stringify(malformed));
  assert.equal(loadFeedback(storage, key, fixtureCase, "display-test-pack").persistence, "unavailable");
  assert.throws(() => captureFeedback(fixtureCase, 26, displayTestChart, "out-of-event", "now",
    {correction: displayTestCorrection}));
  assert.equal(JSON.stringify([displayTestChart, displayTestCorrectionSet]), before);
});

test("guitar-first membership changes preserve existing progress and omit Love Me Do from next suggestions", () => {
  const values = new Map(), storage = {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)};
  const dylan = learning.steps.find(step => step.id === "knockin-on-heaven-s-door");
  assert.equal(learning.path_id, "first-ten-rhythm"); assert.equal(learning.revision, "1");
  assert.equal(dylan.order, 2);
  const oldDylan = {...dylan, order: 3};
  savePracticeProgress(storage, learning, "automatic-first-ten-v1", oldDylan, true);
  assert.equal(loadPracticeProgress(storage, learning, "automatic-first-ten-v1", dylan).practised, true);
  const loveRecording = arrangementFixture.cases.find(item => item.song_id === "love-me-do").recording;
  const oldLove = {id: "love-me-do", order: 2, recording: loveRecording};
  savePracticeProgress(storage, learning, "automatic-first-ten-v1", oldLove, true);
  const loveKey = practiceProgressKey(learning, "automatic-first-ten-v1", oldLove), saved = values.get(loveKey);
  const progress = new Map([[learning.steps[0].id, {practised: true}]]);
  assert.equal(initialPracticeStep(learning.steps, progress).id, dylan.id);
  assert.equal(nextPracticeStep(learning.steps, progress, "wild-thing").id, dylan.id);
  assert.equal(learning.steps.some(step => step.id === "love-me-do"), false);
  assert.equal(values.get(loveKey), saved);
  assert.equal(loadPracticeProgress(storage, learning, "automatic-first-ten-v1", oldLove).practised, true);
  assert.equal(learningCases.some(item => item.recording.id === loveRecording.id), true);
});
test("reported correction requires explicit analysis and pack identity even when both inputs omit them", () => {
  const primary = {...chart, analysis: {}, chords: [{start_seconds: 0, end_seconds: 5, label: "E"}]};
  const set = {schema_version: "reported-chord-corrections-1.0", status: "user-reported-provisional", gold: false,
    primary_sha256: "a".repeat(64), recording, corrections: [{id: "reported-a", expected_event: primary.chords[0],
      replacement_label: "A", reported_seconds: 2, timing_status: "native-boundaries-unverified", note: "Reported A"}]};
  assert.throws(() => correctedDisplayEvents(primary, set, undefined, "a".repeat(64)));
  assert.throws(() => correctedDisplayEvents(primary, {...set, pack_id: "pack"}, "pack", "a".repeat(64)));
});


const splitChart = {...displayTestChart, chords: [
  {start_seconds: 0, end_seconds: 6, label: "F"},
  {start_seconds: 6, end_seconds: 11, label: "Am"},
  {start_seconds: 11, end_seconds: 13, label: "Em"},
  {start_seconds: 13, end_seconds: 40, label: "Am"}
]};
const splitCorrection = {id: "intro-e-near-8", expected_event: splitChart.chords[1],
  replacement_label: "E", replacement_span: {start_seconds: 8, end_seconds: 9.5}, reported_seconds: 8,
  time_basis: "founder-approximate-point",
  timing_status: "secondary-boundaries-unverified", note: "Reported E; secondary timing remains provisional."};
const splitSet = {...displayTestCorrectionSet, corrections: [splitCorrection]};

test("a bounded intro correction restores a missing change while preserving both adjacent Am spans", () => {
  const before = JSON.stringify([splitChart, splitSet]);
  const events = correctedDisplayEvents(splitChart, splitSet, "display-test-pack", "c".repeat(64));
  assert.deepEqual(events.map(e => [e.start_seconds, e.end_seconds, e.label]),
    [[0, 6, "F"], [6, 8, "Am"], [8, 9.5, "E"], [9.5, 11, "Am"], [11, 13, "Em"], [13, 40, "Am"]]);
  for (const [seconds, label] of [[7.99, "Am"], [8, "E"], [9.499, "E"], [9.5, "Am"], [11, "Em"]]) {
    assert.equal(currentEvent(events, seconds).label, label);
  }
  assert.equal(JSON.stringify([splitChart, splitSet]), before);
});
test("split corrections reject out-of-parent, malformed, empty and unsupported timing proposals", () => {
  const apply = change => correctedDisplayEvents(splitChart, {...splitSet, corrections: [{...splitCorrection, ...change}]}, "display-test-pack", "c".repeat(64));
  for (const span of [null, {}, {start_seconds: 5, end_seconds: 9}, {start_seconds: 8, end_seconds: 12},
    {start_seconds: 8, end_seconds: 8}, {start_seconds: 9, end_seconds: 8}, {start_seconds: NaN, end_seconds: 9}]) {
    assert.throws(() => apply({replacement_span: span}));
  }
  for (const change of [{reported_seconds: 7.99}, {reported_seconds: 9.5},
    {timing_status: "native-boundaries-unverified"}, {time_basis: "exact-human-boundaries"}]) assert.throws(() => apply(change));
});
test("split feedback preserves raw Am, displayed E and the provisional displayed interval", () => {
  const review = {id: displayTestRecording.id, recording: displayTestRecording};
  const report = captureFeedback(review, 8.2, splitChart, "split-tap", "now", {correction: splitCorrection});
  assert.equal(report.raw_sounding_chord, "Am"); assert.equal(report.displayed_chord, "E");
  assert.deepEqual(report.display_correction_span, {start_seconds: 8, end_seconds: 9.5});
  for (const seconds of [7.9, 9.5, 11]) assert.throws(() => captureFeedback(review, seconds, splitChart, "wrong-span", "now", {correction: splitCorrection}));
  const values = new Map(), storage = {getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v)};
  const key = feedbackKey("display-test-pack", review);
  saveFeedback(storage, key, review, "display-test-pack", [report]);
  assert.deepEqual(loadFeedback(storage, key, review, "display-test-pack").feedback, [report]);
  const invalid = {...report, display_correction_span: {start_seconds: 8.3, end_seconds: 9.5}};
  assert.throws(() => saveFeedback(storage, key, review, "display-test-pack", [invalid]));
});
test("contextual intro feedback distinguishes a representative point from a reported timestamp", () => {
  const correction = {id: "intro-second-e", expected_event: splitChart.chords[2], replacement_label: "E", reported_seconds: 12,
    timing_status: "native-boundaries-unverified", time_basis: "representative-native-cue-point-not-user-timestamp",
    note: "The supplied intro order contains E here; 12 seconds is a representative point, not the user's timestamp."};
  const review = {id: displayTestRecording.id, recording: displayTestRecording};
  const report = captureFeedback(review, 12.2, splitChart, "context-tap", "now", {correction});
  assert.equal(report.raw_sounding_chord, "Em"); assert.equal(report.displayed_chord, "E");
  assert.equal(report.display_correction_time_basis, "representative-native-cue-point-not-user-timestamp");
  const values = new Map(), storage = {getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v)};
  const key = feedbackKey("display-test-pack", review);
  saveFeedback(storage, key, review, "display-test-pack", [report]);
  assert.deepEqual(loadFeedback(storage, key, review, "display-test-pack").feedback, [report]);
  const legacy = {...report}; delete legacy.display_correction_span; delete legacy.display_correction_time_basis;
  saveFeedback(storage, key, review, "display-test-pack", [legacy]);
  assert.deepEqual(loadFeedback(storage, key, review, "display-test-pack").feedback, [legacy]);
  assert.throws(() => saveFeedback(storage, key, review, "display-test-pack", [{...report, display_correction_time_basis: "verified"}]));
});

test("every shipped correction applies to its declared native cues and exact paired identity", () => {
  for (const item of json("experiments/review/practice.json").cases) {
    const set = item.display_corrections;
    if (!set) continue;
    const declared = {schema_version: "1.0", recording: item.recording, analysis: {id: set.analysis_id},
      chords: set.corrections.map(c => c.expected_event).sort((a, b) => a.start_seconds - b.start_seconds)};
    validateCandidate(declared, item.recording);
    const display = correctedDisplayEvents(declared, set, set.pack_id, set.primary_sha256);
    for (const correction of set.corrections) {
      const current = currentEvent(display, correction.reported_seconds);
      assert.equal(current.label, correction.replacement_label);
      const report = captureFeedback({id: item.recording.id, recording: item.recording}, correction.reported_seconds,
        declared, correction.id, "now", {correction: current.display_correction});
      assert.equal(report.displayed_chord, correction.replacement_label);
      assert.equal(report.raw_sounding_chord, correction.expected_event.label);
    }
  }
});

const onlineRecording = {...recording, audio_sha256: "d".repeat(64)};
const onlineChart = {...chart, recording: onlineRecording, analysis: {id: "native-model-analysis"},
  chords: chart.chords.map(event => ({...event, label: event.label === "G" ? "Gm" : event.label}))};
const onlineEntry = {recording: onlineRecording, primary_sha256: "e".repeat(64), analysis_id: onlineChart.analysis.id,
  status: "source-checks", sources: [
    {id: "teacher-one", title: "Teacher one", url: "https://teacher-one.example/lesson", status: "extracted", sounding_chords: ["C", "G"]},
    {id: "teacher-two", title: "Teacher two", url: "https://teacher-two.example/lesson", status: "extracted", sounding_chords: ["C", "G"]}
  ], findings: [{id: "palette-1", kind: "outside-source-palette", start_seconds: 6, end_seconds: 8,
    native_label: "Gm", source_ids: ["teacher-one", "teacher-two"], reason: "Two comparable teaching sources use G major."}],
  summary: {independent_source_groups: 2, flagged_spans: 1}, limits: ["Source agreement is not independently timed musical truth."]};
const onlinePayload = {schema_version: "online-chord-checks-1.0", pack_id: "online-pack", created_at_utc: "2026-10-17T12:00:00Z", cases: [onlineEntry]};
const onlineCases = [{id: onlineRecording.id, recording: onlineRecording}];
test("online checks bind a separate warning queue to pack, audio and exact native chart without edits", () => {
  const before = JSON.stringify({onlinePayload, onlineChart});
  const report = validateOnlineChecksManifest(onlinePayload, "online-pack", onlineCases);
  assert.equal(report.cases.get(onlineRecording.id), onlineEntry);
  assert.equal(report.created_at_utc, onlinePayload.created_at_utc);
  assert.equal(pairedOnlineChecks(onlineEntry, onlineChart, "e".repeat(64)), onlineEntry);
  assert.equal(JSON.stringify({onlinePayload, onlineChart}), before);
  assert.equal(currentEvent(onlineChart.chords, 7).label, "Gm");
});
test("online metadata rejects stale packs, audio identities, unknown and duplicate cases", () => {
  for (const change of [{schema_version: "other"}, {pack_id: "other"}, {created_at_utc: "yesterday"},
    {created_at_utc: "2026-10-17T12:00:00"}, {cases: []}, {cases: [onlineEntry, onlineEntry]}]) {
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, ...change}, "online-pack", onlineCases));
  }
  for (const change of [{id: "other"}, {audio_sha256: "f".repeat(64)}, {sample_rate_hz: 200}, {duration_seconds: 21}]) {
    const entry = {...onlineEntry, recording: {...onlineRecording, ...change}};
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [entry]}, "online-pack", onlineCases));
  }
  for (const change of [{analysis_id: "other"}, {primary_sha256: "f".repeat(64)}, {recording: {...onlineRecording, audio_sha256: "f".repeat(64)}}]) {
    assert.throws(() => pairedOnlineChecks({...onlineEntry, ...change}, onlineChart, "e".repeat(64)));
  }
  for (const hash of [null, "missing", "f".repeat(64)]) assert.throws(() => pairedOnlineChecks(onlineEntry, onlineChart, hash));
});
test("online warning spans must be finite, bounded and linked to known teaching sources", () => {
  const finding = onlineEntry.findings[0];
  for (const change of [{start_seconds: NaN}, {end_seconds: Infinity}, {start_seconds: -1}, {end_seconds: 21},
    {start_seconds: 8}, {end_seconds: 5}, {native_label: ""}, {reason: "x".repeat(1001)}, {id: "../../bad"},
    {kind: "verified-correction"}, {source_ids: []}, {source_ids: ["unknown"]}, {source_ids: ["teacher-one", "teacher-one"]}]) {
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, findings: [{...finding, ...change}]}]}, "online-pack", onlineCases));
  }
  assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, findings: [finding, finding]}]}, "online-pack", onlineCases));
});
test("online source links, labels, status and summary data remain bounded", () => {
  const source = onlineEntry.sources[0];
  for (const change of [{url: "javascript:alert(1)"}, {url: "http://teacher.example/"}, {url: "https://localhost/"},
    {url: "https://127.0.0.1/"}, {url: "https://teacher.example:8443/"}, {url: "https://user:password@teacher.example/"},
    {id: "bad/route"}, {title: ""}, {status: "x".repeat(101)}, {comparison_status: "x".repeat(101)}, {sounding_chords: ["x".repeat(101)]},
    {sounding_chords: Array(65).fill("C")}]) {
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, sources: [{...source, ...change}, onlineEntry.sources[1]]}]}, "online-pack", onlineCases));
  }
  for (const summary of [{independent_source_groups: -1, flagged_spans: 1}, {independent_source_groups: 3, flagged_spans: 1},
    {independent_source_groups: 2, flagged_spans: 0}, {independent_source_groups: true, flagged_spans: 1}]) {
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, summary}]}, "online-pack", onlineCases));
  }
  assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, limits: ["x".repeat(1001)]}]}, "online-pack", onlineCases));
});
test("insufficient online sources and riff cases have explicit coverage without invented findings", () => {
  for (const status of ["insufficient-sources", "not-harmony-task"]) {
    const entry = {...clone(onlineEntry), status, sources: [], findings: [], summary: {independent_source_groups: 0, flagged_spans: 0}};
    assert.equal(validateOnlineChecksManifest({...onlinePayload, cases: [entry]}, "online-pack", onlineCases).cases.get(onlineRecording.id).status, status);
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, status}]}, "online-pack", onlineCases));
  }
  const empty = {...onlineEntry, findings: [], summary: {...onlineEntry.summary, flagged_spans: 0}};
  assert.deepEqual(validateOnlineChecksManifest({...onlinePayload, cases: [empty]}, "online-pack", onlineCases).cases.get(onlineRecording.id).findings, []);
});
test("online search discovery reports cache, failure and setup assumptions without hiding coverage", () => {
  const search = {provider: "web-provider", status: "request-failed", cache_hit: false, retrieved_at_utc: null,
    notes: ["Saved teaching pages were still checked; discovery did not return a usable result."]};
  const entry = {...onlineEntry, search, sources: onlineEntry.sources.map(source => ({...source, comparison_status: "teaching-hypothesis"}))};
  assert.equal(validateOnlineChecksManifest({...onlinePayload, cases: [entry]}, "online-pack", onlineCases).cases.get(onlineRecording.id).search, search);
  for (const change of [{provider: ""}, {status: "x".repeat(101)}, {cache_hit: "yes"}, {retrieved_at_utc: "yesterday"},
    {retrieved_at_utc: "2026-10-17T12:00:00"}, {notes: ["x".repeat(1001)]}, {notes: Array(17).fill("note")}]) {
    assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...entry, search: {...search, ...change}}]}, "online-pack", onlineCases));
  }
});


const reviewedFinding = {...clone(onlineEntry.findings[0]),
  review_binding: Object.fromEntries(["id", "kind", "start_seconds", "end_seconds", "native_label", "source_ids"].map(key => [key, clone(onlineEntry.findings[0][key])])),
  review: {schema_version: "online-finding-review-1.0", status: "local-evidence-proposal", gold: false,
    candidate_exposure: "model-exposed", actor: "agent", reviewed_at_utc: "2026-10-18T12:00:00Z",
    note: "Local diagnostic favours G, without establishing a physical boundary.", guide_correction_ids: [],
    proposal: {label: "G", timing_status: "native-boundaries-unverified"},
    evidence_refs: [{path: "docs/WARNING_EVIDENCE.json", sha256: "a".repeat(64)}]}};
test("optional local review proposal preserves native chart, warnings and correction provenance", () => {
  const entry = {...onlineEntry, findings: [reviewedFinding]}, payload = {...onlinePayload, cases: [entry]};
  const before = JSON.stringify({payload, onlineChart});
  assert.equal(validateOnlineChecksManifest(payload, "online-pack", onlineCases).cases.get(onlineRecording.id).findings.length, 1);
  assert.equal(onlineFindingReview(reviewedFinding).review.proposal.label, "G");
  assert.equal(onlineReviewSummary([reviewedFinding]), "0 covered by provisional guide; 1 proposal; 0 inconclusive.");
  assert.equal(currentEvent(correctedDisplayEvents(onlineChart, null, "online-pack", "e".repeat(64)), 7).label, "Gm");
  assert.equal(captureFeedback({id: onlineRecording.id, recording: onlineRecording}, 7, onlineChart, "test-review", "now").raw_sounding_chord, "Gm");
  assert.equal(JSON.stringify({payload, onlineChart}), before);
});
test("stale or malformed optional review leaves validated original warning available", () => {
  for (const change of [{status: "independently-accepted"}, {gold: true}, {actor: "human"}, {candidate_exposure: "audio-only"},
    {reviewed_at_utc: "yesterday"}, {reviewed_at_utc: "2026-10-18T12:00:00"}, {note: "x".repeat(1501)},
    {proposal: {label: "G", timing_status: "verified"}}, {guide_correction_ids: ["invented"]},
    {evidence_refs: [{path: "../private.json", sha256: "a".repeat(64)}]},
    {evidence_refs: [{path: "docs/.private.json", sha256: "a".repeat(64)}]},
    {evidence_refs: [{path: "docs/a.json", sha256: "bad"}]}]) {
    const finding = {...reviewedFinding, review: {...reviewedFinding.review, ...change}};
    const payload = {...onlinePayload, cases: [{...onlineEntry, findings: [finding]}]};
    assert.equal(validateOnlineChecksManifest(payload, "online-pack", onlineCases).cases.get(onlineRecording.id).findings.length, 1);
    assert.equal(onlineFindingReview(finding).review, null);
    assert.match(onlineFindingReview(finding).error, /original warning remains/);
  }
  for (const change of [{start_seconds: 6.1}, {native_label: "G"}, {source_ids: ["unknown"]}, {end_seconds: Infinity}]) {
    assert.equal(onlineFindingReview({...reviewedFinding, review_binding: {...reviewedFinding.review_binding, ...change}}).review, null);
  }
});
test("covered notes require actual applied founder overlays and retain the broad replay span", () => {
  const finding = {...reviewedFinding, review: {...reviewedFinding.review, status: "covered-by-provisional-guide",
    guide_correction_ids: ["intro-first-e", "intro-second-e"], proposal: null}};
  assert.equal(onlineFindingReview(finding, ["intro-first-e", "intro-second-e"]).review.status, "covered-by-provisional-guide");
  assert.equal(onlineFindingReview(finding, ["intro-first-e"]).review, null);
  assert.equal(finding.start_seconds, 6); assert.equal(finding.end_seconds, 8);
  const inconclusive = {...reviewedFinding, review: {...reviewedFinding.review, status: "inconclusive", proposal: null}};
  assert.equal(onlineReviewSummary([finding, reviewedFinding, inconclusive], ["intro-first-e", "intro-second-e"]),
    "1 covered by provisional guide; 1 proposal; 1 inconclusive.");
});
test("old reports keep their warning-only behavior and reviews cannot hide invalid warning metadata", () => {
  assert.deepEqual(onlineFindingReview(onlineEntry.findings[0]), {review: null, error: ""});
  assert.equal(onlineReviewSummary(onlineEntry.findings), "");
  assert.equal(onlineFindingReview({...reviewedFinding, review: undefined}).review, null);
  assert.throws(() => validateOnlineChecksManifest({...onlinePayload, cases: [{...onlineEntry, findings: [{...reviewedFinding, end_seconds: 99}]}]}, "online-pack", onlineCases));
});

test("ticket 4 drills distinguish ringing skips, compound counts and variable picking", () => {
  const practice = validatePracticeManifest(json("experiments/review/practice.json"), learningCases);
  const brown = practice.get("van-morrison-brown-eyed-girl-youtube-20261011");
  const next = brown.patterns.find(pattern => pattern.id === "down-up");
  assert.deepEqual(next.counts, ["1", "&", "2", "&", "3", "&", "4", "&"]);
  assert.deepEqual(next.strokes, ["D", "U", "D", "U", "—", "U", "D", "U"]);
  assert.match(next.description, /hand moving/); assert.match(next.description, /let the previous sound ring/);
  assert.match(next.description, /Do not damp/); assert.equal(brown.patterns[0].id, "steady-down");
  const house = practice.get("animals-house-rising-sun-official-20261011");
  assert.deepEqual(house.patterns[0].strokes, ["D", "—", "—", "D", "—", "—"]);
  assert.match(house.note, /two dotted-quarter/); assert.match(house.note, /fingerstyle is an optional adaptation/);
  const creep = practice.get("radiohead-creep-youtube-20261010");
  assert.match(creep.note, /B major and C minor/); assert.match(creep.patterns[1].description, /do not prescribe one fixed verse arpeggio/);
});

console.log(`${checks} review helper checks passed`);
