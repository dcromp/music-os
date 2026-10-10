"use strict";

// Pure helpers are exported for offline tests; browser use requires no packages.
function validNumber(value) { return typeof value === "number" && Number.isFinite(value); }
function exposureKey(packId, reviewCase) {
  return "music-os-review-exposure:" + JSON.stringify([packId, reviewCase.id, reviewCase.recording.audio_sha256]);
}
function loadExposure(storage, key) {
  try {
    // Any stored value is conservative evidence of exposure, including corrupt values.
    return { exposed: storage.getItem(key) !== null, exposureHistory: "browser-local-sticky" };
  } catch (_) {
    return { exposed: true, exposureHistory: "unavailable-assume-exposed" };
  }
}
function recordExposure(storage, key) {
  try { storage.setItem(key, "1"); return "browser-local-sticky"; }
  catch (_) { return "unavailable-assume-exposed"; }
}
function refreshExposure(state, storage, key) {
  const saved = loadExposure(storage, key);
  return { exposed: state.exposed || saved.exposed,
    exposureHistory: saved.exposureHistory === "unavailable-assume-exposed"
      ? saved.exposureHistory : state.exposureHistory || saved.exposureHistory };
}
function annotationExport(reviewCase, state, elapsedSeconds) {
  const duration = reviewCase.recording.duration_seconds;
  if (state.marks.some(mark => String(mark.time).trim() === "" || String(mark.uncertainty).trim() === "")) {
    throw new Error("Mark times and uncertainties cannot be blank.");
  }
  const marks = state.marks.map(mark => ({
    start_seconds: Number(mark.time), label: String(mark.label).trim(),
    timing_uncertainty_seconds: Number(mark.uncertainty), confidence: mark.confidence
  })).sort((left, right) => left.start_seconds - right.start_seconds);
  for (let index = 0; index < marks.length; index++) {
    const mark = marks[index];
    if (!validNumber(mark.start_seconds) || mark.start_seconds < 0 || mark.start_seconds >= duration ||
        (index > 0 && mark.start_seconds <= marks[index - 1].start_seconds)) {
      throw new Error("Mark times must be distinct, finite and inside the listening window.");
    }
    if (!mark.label || mark.label.length > 40 || /[\r\n]/.test(mark.label)) {
      throw new Error("Each mark needs a chord name or ? for an unknown chord.");
    }
    if (!validNumber(mark.timing_uncertainty_seconds) || mark.timing_uncertainty_seconds < 0 ||
        mark.timing_uncertainty_seconds > 2 || !["certain", "unsure"].includes(mark.confidence)) {
      throw new Error("Use timing uncertainty from 0 to 2 seconds and a confidence choice.");
    }
    mark.end_seconds = index + 1 < marks.length ? marks[index + 1].start_seconds : duration;
  }
  return {
    schema_version: "listening-annotations-1.0", status: "human-draft-needs-independent-verification",
    review_pack_id: state.packId || null,
    recording: reviewCase.recording, origin: reviewCase.origin,
    candidate_exposure: state.exposed ? "model-exposed" : "audio-only-so-far",
    exposure_history: state.exposureHistory || "session-only-unverified",
    provenance: "Manually entered in local review interface; no model events were copied automatically",
    elapsed_seconds: elapsedSeconds,
    elapsed_seconds_semantics: "wall time since first selection in this tab; includes pauses and time on other cases",
    notes: state.notes, annotations: marks,
    missing_initial_label: !marks.length || marks[0].start_seconds > 0,
    gold: false
  };
}
function validateCandidate(chart, recording) {
  if (!chart || chart.schema_version !== "1.0" || !chart.recording || !Array.isArray(chart.chords) ||
      chart.recording.id !== recording.id || chart.recording.audio_sha256 !== recording.audio_sha256 ||
      !validNumber(chart.recording.duration_seconds) || !validNumber(recording.duration_seconds) ||
      chart.recording.sample_rate_hz !== recording.sample_rate_hz ||
      Math.abs(chart.recording.duration_seconds - recording.duration_seconds) > 0.000001) {
    throw new Error("Candidate does not match this listening audio.");
  }
  let end = 0;
  for (const event of chart.chords) {
    if (!validNumber(event.start_seconds) || !validNumber(event.end_seconds) ||
        event.start_seconds < end || event.start_seconds < 0 || event.end_seconds <= event.start_seconds ||
        event.end_seconds > recording.duration_seconds || typeof event.label !== "string" || !event.label) {
      throw new Error("Invalid candidate timing events.");
    }
    end = event.end_seconds;
  }
  return chart;
}
function currentEvent(events, seconds) {
  return events.find(event => event.start_seconds <= seconds && seconds < event.end_seconds) || null;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = { annotationExport, validateCandidate, currentEvent, exposureKey, loadExposure, recordExposure, refreshExposure };
}

if (typeof document !== "undefined") {
  const el = id => document.getElementById(id);
  const audio = el("audio");
  const states = new Map();
  let cases = [], selected = null, state = null, generation = 0, packId = "";
  const exposureStorage = {
    getItem: key => window.localStorage.getItem(key),
    setItem: (key, value) => window.localStorage.setItem(key, value)
  };
  const status = text => { el("status").textContent = text; };
  const safeURL = value => {
    const url = new URL(value, window.location.href);
    if (url.origin !== window.location.origin || url.search || url.hash) throw new Error("Only local pack files are allowed.");
    return url.href;
  };
  async function getJSON(url) {
    const response = await fetch(safeURL(url));
    if (!response.ok) throw new Error(`Local review file unavailable (${response.status}).`);
    return response.json();
  }
  function controls(enabled) {
    for (const id of ["restart", "go", "back", "mark", "save", "show", "reveal"]) el(id).disabled = !enabled;
  }
  function seek(seconds) {
    if (!Number.isFinite(audio.duration)) return;
    audio.currentTime = Math.min(audio.duration, Math.max(0, seconds));
  }
  function makeCell(row, child) {
    const cell = document.createElement("td");
    cell.append(child);
    row.append(cell);
  }
  function textInput(mark, key, type, attributes = {}) {
    const input = document.createElement("input");
    input.type = type;
    input.value = mark[key];
    for (const [name, value] of Object.entries(attributes)) input.setAttribute(name, value);
    input.addEventListener("input", () => { mark[key] = input.value; });
    return input;
  }
  function renderMarks() {
    el("marks").replaceChildren();
    for (const mark of state.marks) {
      const row = document.createElement("tr");
      makeCell(row, textInput(mark, "time", "number", { min: 0, step: 0.01, "aria-label": "Mark time in seconds" }));
      const label = textInput(mark, "label", "text", { maxlength: 40, "aria-label": "Chord label", placeholder: "?" });
      makeCell(row, label);
      makeCell(row, textInput(mark, "uncertainty", "number", { min: 0, max: 2, step: 0.01, "aria-label": "Timing uncertainty in seconds" }));
      const confidence = document.createElement("select");
      confidence.setAttribute("aria-label", "Annotation confidence");
      for (const value of ["unsure", "certain"]) {
        const option = document.createElement("option"); option.value = value; option.textContent = value;
        confidence.append(option);
      }
      confidence.value = mark.confidence;
      confidence.addEventListener("change", () => { mark.confidence = confidence.value; });
      makeCell(row, confidence);
      const replay = document.createElement("button"); replay.textContent = "Replay";
      replay.addEventListener("click", () => { seek(Number(mark.time) - 0.5); audio.play().catch(error => status(error.message)); });
      makeCell(row, replay);
      const remove = document.createElement("button"); remove.textContent = "Remove";
      remove.addEventListener("click", () => { state.marks = state.marks.filter(value => value !== mark); renderMarks(); });
      makeCell(row, remove);
      el("marks").append(row);
    }
  }
  function exposure() {
    el("exposure").textContent = state.exposureHistory === "unavailable-assume-exposed"
      ? "Exposure history could not be saved or read. Exports conservatively assume model exposure and require independent checking."
      : state.exposed
      ? "Candidate exposure is recorded for this audio, including earlier visits. Exports are marked model-exposed even while charts are hidden."
      : "Candidate charts are hidden. This draft is audio-only so far.";
  }
  async function selectCase(index) {
    generation++;
    selected = cases[index];
    if (!states.has(selected.id)) {
      const key = exposureKey(packId, selected);
      states.set(selected.id, {
        marks: [], notes: "", ...loadExposure(exposureStorage, key), exposureKey: key, packId,
        candidates: null, started: performance.now()
      });
    }
    state = states.get(selected.id);
    Object.assign(state, refreshExposure(state, exposureStorage, state.exposureKey));
    controls(false);
    audio.pause(); audio.removeAttribute("src"); audio.load();
    el("comparison").hidden = true;
    el("candidate-events").replaceChildren();
    el("candidate").replaceChildren();
    el("current").textContent = "No labelled chord here";
    el("notes").value = state.notes;
    el("export").hidden = true;
    el("origin").textContent = `${selected.bounds_description} · source ${selected.origin.source_offset_seconds.toFixed(3)}–${selected.origin.source_end_seconds.toFixed(3)} s · excerpt SHA256 ${selected.recording.audio_sha256}`;
    renderMarks(); exposure();
    audio.src = safeURL(selected.audio_url);
    audio.load();
    status("Listen, then mark changes. Candidate charts stay hidden until you reveal them.");
  }
  function renderCandidate() {
    if (!state.candidates) return;
    const chart = state.candidates[Number(el("candidate").value)];
    el("candidate-events").replaceChildren();
    for (const event of chart.chords) {
      const row = document.createElement("tr");
      for (const value of [event.start_seconds.toFixed(3), event.end_seconds.toFixed(3), event.label]) {
        const span = document.createElement("span"); span.textContent = value; makeCell(row, span);
      }
      const button = document.createElement("button"); button.textContent = "Replay";
      button.addEventListener("click", () => { seek(event.start_seconds); audio.play().catch(error => status(error.message)); });
      makeCell(row, button);
      row.dataset.start = event.start_seconds; row.dataset.end = event.end_seconds;
      el("candidate-events").append(row);
    }
    updateClock();
  }
  function updateClock() {
    el("position").textContent = `${audio.currentTime.toFixed(3)} s (source ${(audio.currentTime + (selected?.origin.source_offset_seconds || 0)).toFixed(3)} s)`;
    if (!state?.exposed || !state.candidates || el("comparison").hidden) return;
    const chart = state.candidates[Number(el("candidate").value)];
    const event = currentEvent(chart.chords, audio.currentTime);
    el("current").textContent = event ? event.label : "No labelled chord here";
    for (const row of el("candidate-events").children) {
      row.classList.toggle("active", Number(row.dataset.start) <= audio.currentTime && audio.currentTime < Number(row.dataset.end));
    }
  }
  function exported() {
    // Refresh before export to observe another tab's reveal of this same audio.
    Object.assign(state, refreshExposure(state, exposureStorage, state.exposureKey));
    exposure();
    return JSON.stringify(annotationExport(selected, state, (performance.now() - state.started) / 1000), null, 2) + "\n";
  }
  function showExport() {
    try { el("export").value = exported(); el("export").hidden = false; status("Copy this JSON into a local file. It remains a manual draft."); }
    catch (error) { status(error.message); }
  }
  el("case").addEventListener("change", () => selectCase(Number(el("case").value)).catch(error => status(error.message)));
  el("restart").addEventListener("click", () => seek(0));
  el("go").addEventListener("click", () => seek(Number(el("seek").value)));
  el("back").addEventListener("click", () => seek(audio.currentTime - 2));
  el("seek").addEventListener("keydown", event => { if (event.key === "Enter") seek(Number(el("seek").value)); });
  el("mark").addEventListener("click", () => {
    if (audio.currentTime >= selected.recording.duration_seconds) { status("Seek before the end to mark a change."); return; }
    state.marks.push({ time: audio.currentTime.toFixed(3), label: "?", uncertainty: 0.1, confidence: "unsure" });
    renderMarks(); el("marks").lastElementChild.querySelector('input[type="text"]').focus();
  });
  el("notes").addEventListener("input", () => { state.notes = el("notes").value; });
  el("show").addEventListener("click", showExport);
  el("save").addEventListener("click", () => {
    try {
      const url = URL.createObjectURL(new Blob([exported()], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${selected.id}-annotations.json`; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status("Annotation draft downloaded. If downloading is unavailable, use Show JSON to copy.");
    } catch (error) { status(error.message); }
  });
  el("reveal").addEventListener("click", async () => {
    const token = generation, target = state, reviewCase = selected;
    target.exposed = true;
    target.exposureHistory = recordExposure(exposureStorage, target.exposureKey);
    exposure();
    try {
      const charts = target.candidates || await Promise.all(reviewCase.candidates.map(async candidate =>
        validateCandidate(await getJSON(candidate.url), reviewCase.recording)));
      if (token !== generation) return;
      target.candidates = charts;
      el("candidate").replaceChildren();
      reviewCase.candidates.forEach((candidate, index) => {
        const option = document.createElement("option"); option.value = index; option.textContent = candidate.name; el("candidate").append(option);
      });
      el("comparison").hidden = false; renderCandidate();
      status("Anonymous model drafts revealed. Your annotations are separate and now marked model-exposed.");
    } catch (error) { if (token === generation) status(error.message); }
  });
  el("candidate").addEventListener("change", renderCandidate);
  audio.addEventListener("loadedmetadata", () => {
    if (!selected) return;
    if (audio.currentSrc !== safeURL(selected.audio_url)) return;
    if (Math.abs(audio.duration - selected.recording.duration_seconds) > 0.02) { controls(false); status("Audio duration mismatch; review disabled."); return; }
    controls(true); updateClock();
  });
  audio.addEventListener("timeupdate", updateClock);
  audio.addEventListener("error", () => { controls(false); status("Local audio could not load. Check the review server and pack files."); });
  (async () => {
    const manifest = await getJSON("/manifest.json");
    if (manifest.schema_version !== "listening-review-1.0" || typeof manifest.pack_id !== "string" || !manifest.pack_id || !Array.isArray(manifest.cases) || !manifest.cases.length) throw new Error("Invalid or empty local review pack.");
    packId = manifest.pack_id;
    cases = manifest.cases;
    cases.forEach((reviewCase, index) => {
      safeURL(reviewCase.audio_url); reviewCase.candidates.forEach(candidate => safeURL(candidate.url));
      const option = document.createElement("option"); option.value = index; option.textContent = reviewCase.name; el("case").append(option);
    });
    el("case").disabled = false;
    await selectCase(0);
  })().catch(error => { controls(false); status(error.message); });
}
