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
const FEEDBACK_REASONS = ["not-sure", "wrong-chord", "late-change", "too-many-changes"];
function pairedRecording(candidate, recording) {
  return candidate && candidate.id === recording.id && candidate.audio_sha256 === recording.audio_sha256 &&
    candidate.sample_rate_hz === recording.sample_rate_hz && validNumber(candidate.duration_seconds) &&
    Math.abs(candidate.duration_seconds - recording.duration_seconds) <= 0.000001;
}
function validateEvidence(evidence, recording) {
  if (!evidence || evidence.schema_version !== "automatic-draft-evidence-1.0" || !pairedRecording(evidence.recording, recording) || !Array.isArray(evidence.review_points)) {
    throw new Error("Automatic review suggestions do not match this audio.");
  }
  for (const point of evidence.review_points) {
    if (!validNumber(point.start_seconds) || !validNumber(point.end_seconds) || point.start_seconds < 0 ||
        point.end_seconds <= point.start_seconds || point.end_seconds > recording.duration_seconds ||
        typeof point.reason !== "string" || !point.reason) throw new Error("Invalid automatic review suggestion.");
  }
  return evidence;
}
function clampSeek(seconds, duration) {
  if (!validNumber(seconds) || !validNumber(duration) || duration <= 0) throw new Error("Use a valid playback time.");
  return Math.min(duration, Math.max(0, seconds));
}
function playbackSnapshot(events, seconds, count = 3) {
  return { current: currentEvent(events, seconds),
    upcoming: events.filter(event => event.start_seconds > seconds).slice(0, count) };
}
function transposePracticeLabel(label, capo) {
  if (!Number.isInteger(capo) || capo < 0 || capo > 12) throw new Error("Use a capo fret from 0 to 12.");
  if (typeof label !== "string" || !capo || label === "N" || label === "X") return label;
  const notes = { C: 0, "B#": 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4,
    "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11 };
  const sharp = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const flat = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  const shifted = (note, preferFlat = false) => (note.includes("b") || preferFlat ? flat : sharp)[(notes[note] - capo + 12) % 12];
  const parsed = /^([A-G](?:#|b)?)([^/]*)(?:\/(.*))?$/.exec(label);
  if (!parsed || !(parsed[1] in notes)) return label;
  const bass = parsed[3] === undefined ? "" : "/" + (/^[A-G](?:#|b)?$/.test(parsed[3]) && parsed[3] in notes ? shifted(parsed[3], parsed[1].includes("b")) : parsed[3]);
  return shifted(parsed[1]) + parsed[2] + bass;
}
function practiceLabel(label, view, capo) {
  return view === "capo-shapes" ? transposePracticeLabel(label, capo) : label;
}
function feedbackKey(packId, reviewCase) {
  return "music-os-playalong-feedback:" + JSON.stringify([packId, reviewCase.id, reviewCase.recording.audio_sha256]);
}
function feedbackExport(reviewCase, packId, feedback) {
  return { schema_version: "playalong-feedback-1.0", review_pack_id: packId, recording: reviewCase.recording,
    origin: reviewCase.origin || null, candidate_exposure: "model-exposed", gold: false,
    semantics: "Playback issue reports, not chord labels or verified change times. Times are captured at the tap and include listener reaction delay. raw_sounding_chord is the detector label; displayed_chord follows the recorded practice view and capo.",
    feedback: feedback.map(item => ({ ...item })) };
}
function captureFeedback(reviewCase, seconds, chart, id, createdAt, practice = {}) {
  if (!validNumber(seconds) || seconds < 0 || seconds > reviewCase.recording.duration_seconds) {
    throw new Error("The playback position is outside this song.");
  }
  validateCandidate(chart, reviewCase.recording);
  const event = currentEvent(chart.chords, seconds);
  const view = practice.view || "sounding-pitches", capo = view === "capo-shapes" ? practice.capo : 0;
  if (!["sounding-pitches", "capo-shapes"].includes(view) || !Number.isInteger(capo) || capo < 0 || capo > 12) throw new Error("Invalid practice display.");
  return { id, playback_seconds: seconds,
    source_seconds: seconds + (reviewCase.origin?.source_offset_seconds || 0),
    candidate_analysis_id: chart.analysis?.id || null, raw_sounding_chord: event?.label || null,
    displayed_chord: event ? practiceLabel(event.label, view, capo) : null,
    practice_view: view, practice_capo: capo,
    reason: "not-sure", note: "", created_at: createdAt };
}
function validFeedback(item, recording) {
  return item && typeof item.id === "string" && item.id && validNumber(item.playback_seconds) &&
    item.playback_seconds >= 0 && item.playback_seconds <= recording.duration_seconds &&
    validNumber(item.source_seconds) && FEEDBACK_REASONS.includes(item.reason) &&
    typeof item.note === "string" && item.note.length <= 1000 && typeof item.created_at === "string";
}
function loadFeedback(storage, key, reviewCase, packId) {
  try {
    const raw = storage.getItem(key);
    if (raw === null) return { feedback: [], persistence: "saved-on-this-browser" };
    const value = JSON.parse(raw);
    if (value.schema_version !== "playalong-feedback-1.0" || value.review_pack_id !== packId ||
        !pairedRecording(value.recording, reviewCase.recording) || !Array.isArray(value.feedback) ||
        !value.feedback.every(item => validFeedback(item, reviewCase.recording))) throw new Error("Invalid saved feedback");
    return { feedback: value.feedback, persistence: "saved-on-this-browser" };
  } catch (_) { return { feedback: [], persistence: "unavailable" }; }
}
function saveFeedback(storage, key, reviewCase, packId, feedback) {
  if (!feedback.every(item => validFeedback(item, reviewCase.recording))) throw new Error("Invalid feedback report.");
  try { storage.setItem(key, JSON.stringify(feedbackExport(reviewCase, packId, feedback))); return "saved-on-this-browser"; }
  catch (_) { return "unavailable"; }
}
function timeLabel(seconds) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = { annotationExport, validateCandidate, currentEvent, exposureKey, loadExposure, recordExposure,
    refreshExposure, pairedRecording, validateEvidence, clampSeek, playbackSnapshot, feedbackKey, feedbackExport,
    captureFeedback, loadFeedback, saveFeedback, timeLabel, transposePracticeLabel, practiceLabel };
}

if (typeof document !== "undefined") {
  const el = id => document.getElementById(id), audio = el("audio"), states = new Map();
  let cases = [], selected = null, state = null, generation = 0, packId = "", feedbackCounter = 0;
  const storage = { getItem: key => window.localStorage.getItem(key), setItem: (key, value) => window.localStorage.setItem(key, value) };
  const status = text => { el("status").textContent = text; };
  const safeURL = value => {
    const url = new URL(value, window.location.href);
    if (url.origin !== window.location.origin || url.search || url.hash) throw new Error("Only local pack files are allowed.");
    return url.href;
  };
  async function getJSON(url) {
    const response = await fetch(safeURL(url));
    if (!response.ok) throw new Error(`Local song file unavailable (${response.status}).`);
    return response.json();
  }
  function controls(enabled) {
    for (const id of ["restart", "go", "back", "mark", "save", "show", "reveal", "problem", "save-feedback", "copy-feedback"]) el(id).disabled = !enabled;
  }
  function readyControls() { controls(Boolean(state?.primary && state.audioReady)); }
  function seek(seconds) {
    if (!selected || !Number.isFinite(audio.duration)) return;
    audio.currentTime = clampSeek(seconds, Math.min(audio.duration, selected.recording.duration_seconds));
    updateClock();
  }
  function replay(seconds) { seek(seconds); audio.play().catch(error => status(error.message)); }
  function cell(row, child) { const node = document.createElement("td"); node.append(child); row.append(node); }
  function button(text, callback) {
    const node = document.createElement("button"); node.textContent = text; node.addEventListener("click", callback); return node;
  }
  function textInput(mark, key, type, attributes = {}) {
    const input = document.createElement("input"); input.type = type; input.value = mark[key];
    for (const [name, value] of Object.entries(attributes)) input.setAttribute(name, value);
    input.addEventListener("input", () => { mark[key] = input.value; }); return input;
  }
  function renderMarks() {
    el("marks").replaceChildren();
    for (const mark of state.marks) {
      const row = document.createElement("tr");
      cell(row, textInput(mark, "time", "number", { min: 0, step: 0.01, "aria-label": "Mark time in seconds" }));
      cell(row, textInput(mark, "label", "text", { maxlength: 40, "aria-label": "Chord label", placeholder: "?" }));
      cell(row, textInput(mark, "uncertainty", "number", { min: 0, max: 2, step: 0.01, "aria-label": "Timing uncertainty in seconds" }));
      const confidence = document.createElement("select"); confidence.setAttribute("aria-label", "Annotation confidence");
      for (const value of ["unsure", "certain"]) { const option = document.createElement("option"); option.value = value; option.textContent = value; confidence.append(option); }
      confidence.value = mark.confidence; confidence.addEventListener("change", () => { mark.confidence = confidence.value; }); cell(row, confidence);
      cell(row, button("Replay", () => replay(Number(mark.time) - 0.5)));
      cell(row, button("Remove", () => { state.marks = state.marks.filter(value => value !== mark); renderMarks(); }));
      el("marks").append(row);
    }
  }
  function exposure() {
    el("exposure").textContent = state.exposureHistory === "unavailable-assume-exposed"
      ? "Exposure history is unavailable. Manual exports conservatively assume model exposure and require independent checking."
      : "Automatic chart exposure is recorded for this audio. Manual exports are model-exposed drafts; no model events are inserted into the manual editor.";
  }
  function persist() {
    state.persistence = saveFeedback(storage, state.feedbackKey, selected, packId, state.feedback);
    if (state.persistence === "unavailable") status("Your feedback is kept in this tab, but browser storage is unavailable. Use Download feedback to keep a copy.");
  }
  function renderFeedback() {
    el("feedback-list").replaceChildren();
    el("feedback-summary").textContent = state.feedback.length
      ? `${state.feedback.length} ${state.feedback.length === 1 ? "issue" : "issues"} ${state.persistence === "unavailable" ? "kept in this tab; download a copy before closing" : "saved on this browser"}.`
      : "No issues saved for this song yet.";
    for (const item of state.feedback) {
      const row = document.createElement("div"); row.className = "feedback-row";
      const text = document.createElement("span");
      const reasons = { "not-sure": "Something felt wrong", "wrong-chord": "Wrong chord", "late-change": "Change is late", "too-many-changes": "Too many changes" };
      text.textContent = `${timeLabel(item.playback_seconds)} · ${reasons[item.reason]}${item.note ? ` · ${item.note}` : ""}`;
      row.append(text, button("Replay", () => replay(item.playback_seconds - 2)), button("Remove", () => {
        state.feedback = state.feedback.filter(value => value.id !== item.id);
        if (state.activeFeedback === item.id) { state.activeFeedback = null; el("feedback-detail").hidden = true; }
        persist(); renderFeedback();
      }));
      el("feedback-list").append(row);
    }
  }
  function renderPoints() {
    el("review-points").replaceChildren();
    const points = state.evidence?.review_points || [];
    if (!points.length) { el("review-points").textContent = "No automatic review suggestions available for this song."; return; }
    for (const point of points) {
      const row = document.createElement("div"); row.className = "point-row";
      const text = document.createElement("span"); text.textContent = `${timeLabel(point.start_seconds)} · ${point.reason}`;
      row.append(text, button("Replay this spot", () => replay(point.start_seconds - 2))); el("review-points").append(row);
    }
  }
  function practiceInfo() {
    const capo = selected.practice?.capo || 0;
    el("practice").hidden = !selected.practice;
    el("chord-view-choice").hidden = !capo;
    el("chord-view").value = state.practiceView;
    el("chord-view").options[0].textContent = `Capo ${capo} · played shapes`;
    el("practice").textContent = capo && state.practiceView === "capo-shapes"
      ? `Capo ${capo} on your guitar. Chords below are the shapes you play.`
      : "Chords below show sounding pitches, with no display transposition.";
  }
  async function selectCase(index) {
    const token = ++generation; selected = cases[index];
    if (!states.has(selected.id)) {
      const key = exposureKey(packId, selected), saved = loadFeedback(storage, feedbackKey(packId, selected), selected, packId);
      states.set(selected.id, { marks: [], notes: "", ...loadExposure(storage, key), exposureKey: key, packId,
        ...saved, feedbackKey: feedbackKey(packId, selected), primary: null, evidence: null, candidates: null,
        audioReady: false, practiceView: selected.practice?.capo ? "capo-shapes" : "sounding-pitches", started: performance.now() });
    }
    state = states.get(selected.id); const target = state, reviewCase = selected;
    state.audioReady = false; controls(false); audio.pause(); audio.removeAttribute("src"); audio.load();
    el("comparison").hidden = true; el("candidate-events").replaceChildren(); el("candidate").replaceChildren();
    el("play-current").textContent = "Loading…"; el("upcoming").replaceChildren(); el("next-change").textContent = "";
    el("feedback-detail").hidden = true; state.activeFeedback = null;
    el("notes").value = state.notes; el("export").hidden = true; el("feedback-export").hidden = true;
    el("point-notice").hidden = true;
    practiceInfo();
    el("origin").textContent = JSON.stringify({ recording: selected.recording, origin: selected.origin || null,
      source: selected.source || selected.source_references || null, practice: selected.practice || null, summary: selected.summary || null }, null, 2);
    renderMarks(); renderFeedback(); renderPoints();
    audio.src = safeURL(selected.audio_url); audio.load();
    status("Preparing the automatic chord draft…");
    target.exposed = true; target.exposureHistory = recordExposure(storage, target.exposureKey); exposure();
    try {
      const primary = target.primary || validateCandidate(await getJSON(selected.primary_url || selected.candidates[0].url), reviewCase.recording);
      if (token !== generation) return;
      target.primary = primary; readyControls(); updateClock(); status("Ready. Press play and follow the chords. Feedback saves automatically when you tap.");
      if (reviewCase.evidence_url && !target.evidence) {
        try {
          const evidence = validateEvidence(await getJSON(reviewCase.evidence_url), reviewCase.recording);
          if (token !== generation) return;
          target.evidence = evidence; renderPoints(); updateClock();
        } catch (error) { if (token === generation) status(`Chord draft ready. ${error.message}`); }
      } else { renderPoints(); }
      if (target.persistence === "unavailable") status("Chord draft ready. Browser feedback storage is unavailable; feedback can still be downloaded.");
    } catch (error) { if (token === generation) { controls(false); status(error.message); } }
  }
  function updateClock() {
    if (!selected) return;
    el("position").textContent = `${timeLabel(audio.currentTime)} / ${timeLabel(selected.recording.duration_seconds)}`;
    if (state?.primary) {
      const snapshot = playbackSnapshot(state.primary.chords, audio.currentTime);
      const display = label => ({ N: "No chord", X: "Unclear" }[label] || practiceLabel(label, state.practiceView, selected.practice?.capo || 0));
      el("play-current").textContent = snapshot.current ? display(snapshot.current.label) : "—";
      el("next-change").textContent = snapshot.upcoming.length ? `Next in ${Math.max(0, snapshot.upcoming[0].start_seconds - audio.currentTime).toFixed(1)} s` : "";
      el("upcoming").replaceChildren();
      for (const event of snapshot.upcoming) {
        const node = document.createElement("div"); node.className = "upcoming-chord";
        const chord = document.createElement("strong"); chord.textContent = display(event.label);
        const time = document.createElement("span"); time.textContent = timeLabel(event.start_seconds); node.append(chord, time); el("upcoming").append(node);
      }
      const point = (state.evidence?.review_points || []).find(item => item.start_seconds <= audio.currentTime && audio.currentTime < item.end_seconds);
      el("point-notice").hidden = !point || !el("points-details").open;
      if (point) el("point-notice").textContent = "The algorithms disagree around here. This is only a suggested check — play on or flag it if it sounds wrong.";
    }
    if (state?.candidates && !el("comparison").hidden) {
      const chart = state.candidates[Number(el("candidate").value)];
      el("current").textContent = currentEvent(chart.chords, audio.currentTime)?.label || "No labelled chord here";
      for (const row of el("candidate-events").children) row.classList.toggle("active", Number(row.dataset.start) <= audio.currentTime && audio.currentTime < Number(row.dataset.end));
    }
  }
  function renderCandidate() {
    if (!state.candidates) return;
    const chart = state.candidates[Number(el("candidate").value)]; el("candidate-events").replaceChildren();
    for (const event of chart.chords) {
      const row = document.createElement("tr");
      for (const value of [event.start_seconds.toFixed(3), event.end_seconds.toFixed(3), event.label]) { const span = document.createElement("span"); span.textContent = value; cell(row, span); }
      cell(row, button("Replay", () => replay(event.start_seconds)));
      row.dataset.start = event.start_seconds; row.dataset.end = event.end_seconds; el("candidate-events").append(row);
    }
    updateClock();
  }
  function manualExported() {
    Object.assign(state, refreshExposure(state, storage, state.exposureKey)); exposure();
    return JSON.stringify(annotationExport(selected, state, (performance.now() - state.started) / 1000), null, 2) + "\n";
  }
  function feedbackExported() { return JSON.stringify(feedbackExport(selected, packId, state.feedback), null, 2) + "\n"; }
  function download(text, filename) {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  el("case").addEventListener("change", () => selectCase(Number(el("case").value)).catch(error => status(error.message)));
  el("restart").addEventListener("click", () => seek(0)); el("back").addEventListener("click", () => seek(audio.currentTime - 2));
  el("go").addEventListener("click", () => { try { seek(Number(el("seek").value)); } catch (error) { status(error.message); } });
  el("seek").addEventListener("keydown", event => { if (event.key === "Enter") el("go").click(); });
  el("problem").addEventListener("click", () => {
    try {
      const item = captureFeedback(selected, audio.currentTime, state.primary, `${Date.now()}-${++feedbackCounter}`, new Date().toISOString(),
        {view: state.practiceView, capo: selected.practice?.capo || 0});
      state.feedback.push(item); state.activeFeedback = item.id; persist(); renderFeedback();
      el("feedback-detail").hidden = false; el("captured").textContent = `Captured at ${timeLabel(item.playback_seconds)}. You can keep playing.`;
      el("reason").value = "not-sure"; el("feedback-note").value = "";
      if (state.persistence !== "unavailable") status(`Issue saved at ${timeLabel(item.playback_seconds)}. Reason and note are optional.`);
    } catch (error) { status(error.message); }
  });
  function editFeedback() {
    const item = state?.feedback.find(value => value.id === state.activeFeedback); if (!item) return;
    item.reason = el("reason").value; item.note = el("feedback-note").value; persist(); renderFeedback();
  }
  el("reason").addEventListener("change", editFeedback); el("feedback-note").addEventListener("input", editFeedback);
  el("save-feedback").addEventListener("click", () => { download(feedbackExported(), `${selected.id}-feedback.json`); status("Feedback downloaded. Your saved feedback remains on this browser."); });
  el("copy-feedback").addEventListener("click", async () => {
    const text = feedbackExported();
    try { await navigator.clipboard.writeText(text); status("Feedback JSON copied."); }
    catch (_) { el("feedback-export").value = text; el("feedback-export").hidden = false; el("feedback-export").select(); status("Select and copy the feedback JSON below."); }
  });
  el("mark").addEventListener("click", () => {
    if (audio.currentTime >= selected.recording.duration_seconds) { status("Seek before the end to mark a change."); return; }
    state.marks.push({ time: audio.currentTime.toFixed(3), label: "?", uncertainty: 0.1, confidence: "unsure" }); renderMarks();
    el("marks").lastElementChild.querySelector('input[type="text"]').focus();
  });
  el("notes").addEventListener("input", () => { state.notes = el("notes").value; });
  el("show").addEventListener("click", () => { try { el("export").value = manualExported(); el("export").hidden = false; status("Manual draft shown for optional export."); } catch (error) { status(error.message); } });
  el("save").addEventListener("click", () => { try { download(manualExported(), `${selected.id}-annotations.json`); status("Manual annotation draft downloaded."); } catch (error) { status(error.message); } });
  el("reveal").addEventListener("click", async () => {
    const token = generation, target = state, reviewCase = selected;
    try {
      const descriptors = reviewCase.candidates || [{ name: reviewCase.primary_name || "Play along draft", url: reviewCase.primary_url }, ...(reviewCase.secondary || []), ...(reviewCase.additional || [])];
      const charts = target.candidates || await Promise.all(descriptors.map(async candidate => validateCandidate(await getJSON(candidate.url), reviewCase.recording)));
      if (token !== generation) return;
      target.candidates = charts; el("candidate").replaceChildren();
      descriptors.forEach((candidate, index) => { const option = document.createElement("option"); option.value = index; option.textContent = candidate.name; el("candidate").append(option); });
      el("comparison").hidden = false; renderCandidate(); status("Other automatic drafts loaded. Manual annotations remain separate.");
    } catch (error) { if (token === generation) status(error.message); }
  });
  el("candidate").addEventListener("change", renderCandidate);
  el("chord-view").addEventListener("change", () => { state.practiceView = el("chord-view").value; practiceInfo(); updateClock(); });
  el("points-details").addEventListener("toggle", updateClock);
  audio.addEventListener("loadedmetadata", () => {
    if (!selected || audio.currentSrc !== safeURL(selected.audio_url)) return;
    if (Math.abs(audio.duration - selected.recording.duration_seconds) > 0.02) { state.audioReady = false; controls(false); status("Audio duration mismatch; play along disabled."); return; }
    state.audioReady = true; readyControls(); updateClock();
  });
  for (const event of ["timeupdate", "seeked", "loadeddata", "ended"]) audio.addEventListener(event, updateClock);
  audio.addEventListener("error", () => { if (state) state.audioReady = false; controls(false); status("Local audio could not load. Check the local server and song files."); });
  (async () => {
    const manifest = await getJSON("/manifest.json");
    if (!["listening-review-1.0", "automatic-drafts-1.0"].includes(manifest.schema_version) || typeof manifest.pack_id !== "string" || !manifest.pack_id || !Array.isArray(manifest.cases) || !manifest.cases.length) throw new Error("Invalid or empty local song pack.");
    packId = manifest.pack_id; cases = manifest.cases;
    cases.forEach((reviewCase, index) => {
      safeURL(reviewCase.audio_url);
      if (reviewCase.primary_url) safeURL(reviewCase.primary_url); else if (!reviewCase.candidates?.length) throw new Error("Song has no automatic draft.");
      if (reviewCase.evidence_url) safeURL(reviewCase.evidence_url);
      for (const candidate of [...(reviewCase.candidates || []), ...(reviewCase.secondary || []), ...(reviewCase.additional || [])]) safeURL(candidate.url);
      const option = document.createElement("option"); option.value = index; option.textContent = reviewCase.name; el("case").append(option);
    });
    el("case").disabled = false; await selectCase(0);
  })().catch(error => { controls(false); status(error.message); });
}
