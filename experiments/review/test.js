"use strict";
const assert = require("node:assert/strict");
const { annotationExport, validateCandidate, currentEvent, exposureKey, loadExposure, recordExposure, refreshExposure } = require("./app.js");
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
console.log(`${checks} review helper checks passed`);
