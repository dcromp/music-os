"use strict";

// Exercise the real application logic with a minimal DOM. Native browser audio
// playback, decoding, seeking and rendering still require a browser smoke test.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      value: id === "offset" ? "0" : "",
      checked: false,
      currentTime: 0,
      paused: true,
      disabled: false,
      hidden: id === "csv-preview",
      textContent: "",
      handlers: {},
      loadCalls: 0,
      classList: { toggle() {} },
      addEventListener(name, handler) { this.handlers[name] = handler; },
      replaceChildren() {},
      add() {},
      pause() {},
      load() { this.loadCalls++; },
      setCustomValidity(message) { this.validationMessage = message; },
      checkValidity() { return !this.validationMessage; },
      reportValidity() { return this.checkValidity(); },
      reset() {},
    });
  }
  return elements.get(id);
}

const context = {
  document: { getElementById: element },
  window: { addEventListener() {} },
  requestAnimationFrame() {},
  Option: function Option(text, value) { this.text = text; this.value = value; },
  URL,
  location: new URL("http://127.0.0.1:8765/"),
  console,
  setTimeout,
};
vm.createContext(context);
let source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
// Expose private helpers in this isolated test context without modifying app.js.
const endOfClosure = /\n\}\)\(\);\s*$/;
assert.match(source, endOfClosure, "Expected the application closure for test instrumentation");
source = source.replace(endOfClosure, "\n globalThis.testApi = {validateChart,eventAt,checkPair,render,serializeCsv,state};\n})();");
vm.runInContext(source, context, { filename: "app.js" });
const { validateChart, eventAt, checkPair, render, serializeCsv, state } = context.testApi;
let passed = 0;
function check(name, run) {
  run();
  passed++;
  console.log(`PASS ${name}`);
}

function chart() {
  return {
    schema_version: "1.0",
    recording: { id: "fixture", title: "Fixture", duration_seconds: 10, sample_rate_hz: 22050 },
    analysis: { id: "baseline", algorithm: "baseline", version: "0.1", runtime_seconds: 0.1, parameters: {} },
    chords: [
      { start_seconds: 0, end_seconds: 2, label: "C" },
      { start_seconds: 2, end_seconds: 4, label: "Am" },
      { start_seconds: 5, end_seconds: 10, label: "G" },
    ],
    beats_seconds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  };
}

function readyChart(value = chart(), audioDuration = value.recording.duration_seconds) {
  state.candidates = [{ name: "Baseline", chart: value }];
  state.active = 0;
  state.audioUrl = "blob:fixture";
  state.audioName = "fixture.wav";
  state.duration = audioDuration;
  state.offset = 0;
  checkPair();
}

check("valid versioned chart is accepted", () => validateChart(chart()));
for (const [time, expected, description] of [
  [0, "C", "start is included"],
  [1.999, "C", "before a boundary remains current"],
  [2, "Am", "shared boundary selects the new chord"],
  [4, null, "end before a gap is excluded"],
  [4.99, null, "gaps do not invent chords"],
  [5, "G", "event after a gap is included"],
  [10, null, "recording end is excluded"],
  [-1, null, "time before the chart has no chord"],
]) {
  check(description, () => assert.equal(eventAt(chart().chords, time).event?.label ?? null, expected));
}

for (const [description, mutate] of [
  ["unsupported schema version", c => { c.schema_version = "2.0"; }],
  ["empty chord list", c => { c.chords = []; }],
  ["overlapping intervals", c => { c.chords[1].start_seconds = 1; }],
  ["out-of-order intervals", c => { c.chords.reverse(); }],
  ["event beyond recording end", c => { c.chords[2].end_seconds = 11; }],
  ["zero-length event", c => { c.chords[0].end_seconds = 0; }],
  ["negative start", c => { c.chords[0].start_seconds = -1; }],
  ["nonfinite boundary", c => { c.chords[0].end_seconds = NaN; }],
  ["missing chord label", c => { c.chords[0].label = ""; }],
  ["out-of-range confidence", c => { c.chords[0].confidence = 1.2; }],
  ["duplicate beats", c => { c.beats_seconds = [0, 1, 1]; }],
  ["downbeat outside duration", c => { c.downbeats_seconds = [0, 11]; }],
  ["zero recording duration", c => { c.recording.duration_seconds = 0; }],
]) {
  check(`rejects ${description}`, () => {
    const value = chart();
    mutate(value);
    assert.throws(() => validateChart(value));
  });
}

check("matching recording enables rating", () => {
  readyChart();
  assert.equal(state.validForAudio, true);
  assert.equal(element("save-rating").disabled, false);
  assert.equal(element("seek-go").disabled, false);
});
check("short recording accepts a 0.09 second metadata difference", () => {
  readyChart(chart(), 10.09);
  assert.equal(state.validForAudio, true);
});
check("short recording rejects a 0.11 second metadata difference", () => {
  readyChart(chart(), 10.11);
  assert.equal(state.validForAudio, false);
  assert.equal(element("save-rating").disabled, true);
  assert.match(element("status").textContent, /mismatch/);
});
check("long recording accepts a difference below 0.1 percent", () => {
  const value = chart();
  value.recording.duration_seconds = 200;
  readyChart(value, 200.19);
  assert.equal(state.validForAudio, true);
});
check("long recording rejects a difference above 0.1 percent", () => {
  const value = chart();
  value.recording.duration_seconds = 200;
  readyChart(value, 200.21);
  assert.equal(state.validForAudio, false);
});
check("current and upcoming chords are separate", () => {
  readyChart();
  element("audio").currentTime = 2;
  render();
  assert.equal(element("current-chord").textContent, "Am");
  assert.equal(element("next-chord").textContent, "G");
});
check("positive offset previews later chart events", () => {
  readyChart();
  element("audio").currentTime = 1;
  state.offset = 1;
  render();
  assert.equal(element("current-chord").textContent, "Am");
});
check("negative offset delays the chart", () => {
  readyChart();
  element("audio").currentTime = 2;
  state.offset = -1;
  render();
  assert.equal(element("current-chord").textContent, "C");
});
check("repeated renders do not advance a paused playhead", () => {
  readyChart();
  element("audio").currentTime = 2.5;
  render();
  render();
  assert.equal(element("audio").currentTime, 2.5);
  assert.equal(element("current-chord").textContent, "Am");
});
check("seeking backward and replay use the audio clock immediately", () => {
  readyChart();
  element("audio").currentTime = 6;
  element("audio").handlers.seeked();
  assert.equal(element("current-chord").textContent, "G");
  element("audio").currentTime = 0;
  element("audio").handlers.seeked();
  assert.equal(element("current-chord").textContent, "C");
});
check("candidate switching preserves audio, position and offset", () => {
  readyChart();
  const alternative = chart();
  alternative.analysis.id = "alternative";
  alternative.chords[1].label = "Dm";
  state.candidates.push({ name: "Alternative", chart: alternative });
  const audio = element("audio");
  audio.src = "blob:fixture";
  audio.currentTime = 2.5;
  state.offset = 0.05;
  const callsBefore = audio.loadCalls;
  element("candidate").handlers.change({ target: { value: "1" } });
  assert.equal(element("current-chord").textContent, "Dm");
  assert.equal(audio.src, "blob:fixture");
  assert.equal(audio.currentTime, 2.5);
  assert.equal(audio.loadCalls, callsBefore);
  assert.equal(state.offset, 0.05);
});
check("explicit Go seeks to audio seconds with the offset preserved", () => {
  readyChart();
  const audio = element("audio");
  audio.paused = false;
  state.offset = -0.5;
  element("seek-position").value = "5.5";
  element("seek-form").handlers.submit({ preventDefault() {} });
  assert.equal(audio.currentTime, 5.5);
  assert.equal(audio.paused, false);
  assert.equal(state.offset, -0.5);
  assert.equal(element("current-chord").textContent, "G");
});
check("Go rejects positions outside actual audio duration", () => {
  readyChart();
  element("audio").currentTime = 2;
  for (const value of ["-1", "11", "", "NaN"]) {
    element("seek-position").value = value;
    element("seek-form").handlers.submit({ preventDefault() {} });
    assert.equal(element("audio").currentTime, 2);
    assert.match(element("seek-position").validationMessage, /between 0 and/);
  }
});
check("Restart returns to zero and preserves paused state", () => {
  readyChart();
  const audio = element("audio");
  audio.currentTime = 6;
  audio.paused = true;
  element("restart").handlers.click();
  assert.equal(audio.currentTime, 0);
  assert.equal(audio.paused, true);
  assert.equal(element("current-chord").textContent, "C");
});
check("explicit seeking is disabled before audio metadata", () => {
  readyChart();
  state.duration = null;
  checkPair();
  assert.equal(element("seek-position").disabled, true);
  assert.equal(element("seek-go").disabled, true);
  assert.equal(element("restart").disabled, true);
});
check("CSV preserves comma, quote and newline notes", () => {
  const csv = serializeCsv([{ notes: 'Chord "C", then\nAm', score: 4 }]);
  assert.equal(csv, '"notes","score"\r\n"Chord ""C"", then\nAm","4"\r\n');
});
check("CSV protects formula-like text without changing numerical offsets", () => {
  const csv = serializeCsv([{ notes: "=1+1", spaced: "  +SUM(A1)", negative_offset: -0.5 }]);
  assert.equal(csv, '"notes","spaced","negative_offset"\r\n"\'=1+1","\'  +SUM(A1)","-0.5"\r\n');
});
check("Show CSV reveals the same serialization for manual copying", () => {
  state.ratings = [{ notes: 'A, "B"\nC', followability_1_5: "4" }];
  element("show-csv").handlers.click();
  assert.equal(element("csv-preview").hidden, false);
  assert.equal(element("csv-text").value, serializeCsv(state.ratings));
  assert.equal(element("show-csv").textContent, "Hide CSV");
  element("show-csv").handlers.click();
  assert.equal(element("csv-preview").hidden, true);
});

(async () => {
  readyChart();
  await element("chart-file").handlers.change({ target: { files: [{ text: async () => JSON.stringify({ ...chart(), chords: [] }) }] } });
  check("invalid imported chart clears the old chart and disables rating", () => {
    assert.equal(state.candidates.length, 0);
    assert.equal(state.validForAudio, false);
    assert.equal(element("save-rating").disabled, true);
    assert.equal(element("current-chord").textContent, "—");
    assert.match(element("status").textContent, /no chord events/);
  });
  console.log(`\n${passed} validation and timing checks passed. Browser audio remains a separate smoke test.`);
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
