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
const QUALITY_MODES = ["full-chords", "core-chords"];
function coreChordLabel(label) {
  if (typeof label !== "string") return label;
  // Reduce only explicit, known qualities. Suspensions do not contain a major
  // or minor third, so they must not become ordinary major/minor chords.
  const parsed = /^([A-G](?:#|b)?)([^/]*)(\/(?:[A-G](?:#|b)?|[b#]?[1-7]))?$/.exec(label);
  if (!parsed) return label;
  const qualities = { m7: "m", min7: "m", minor7: "m", maj7: "", major7: "", add9: "", add2: "", "7": "", "7sus4": "sus4", "7sus": "sus4",
    "maj(9)": "", "maj(add9)": "", "(1,3,5,9)": "", "sus4(b7)": "sus4" };
  const suffix = parsed[2].replace(/^:/, "");
  if (!Object.hasOwn(qualities, suffix)) return label;
  return parsed[1] + qualities[suffix] + (parsed[3] || "");
}
function practiceLabel(label, view, capo, qualityMode = "full-chords") {
  if (!QUALITY_MODES.includes(qualityMode)) throw new Error("Invalid chord quality display.");
  const shape = view === "capo-shapes" ? transposePracticeLabel(label, capo) : label;
  return qualityMode === "core-chords" ? coreChordLabel(shape) : shape;
}
function displayedChord(label, view, capo, qualityMode = "full-chords") {
  return label === "N" ? "No chord" : label === "X" ? "Unclear" : practiceLabel(label, view, capo, qualityMode);
}
function practiceTimeline(events, view, capo, qualityMode = "full-chords") {
  const result = [];
  for (const event of events) {
    const displayed = { ...event, label: practiceLabel(event.label, view, capo, qualityMode),
      full_label: practiceLabel(event.label, view, capo) };
    const previous = result[result.length - 1];
    // Merge only adjacent equal core harmony. Never bridge a gap, uncertainty
    // or silence; original charts still provide the detector label at each tap.
    const coreHarmony = /^[A-G](?:#|b)?(?::?(?:maj|min|major|minor|m|sus2|sus4))?(?:\/(?:[A-G](?:#|b)?|[b#]?[1-7]))?$/.test(displayed.label);
    if (qualityMode === "core-chords" && coreHarmony && previous &&
        previous.end_seconds === displayed.start_seconds && previous.label === displayed.label) {
      previous.end_seconds = displayed.end_seconds;
    } else result.push(displayed);
  }
  return result;
}
function currentHold(events, seconds) {
  if (!validNumber(seconds) || seconds < 0) throw new Error("Use a valid playback time.");
  const event = currentEvent(events, seconds);
  if (!event) return null;
  const duration = event.end_seconds - event.start_seconds;
  return { event, total_seconds: duration, elapsed_seconds: seconds - event.start_seconds,
    remaining_seconds: event.end_seconds - seconds, progress_fraction: (seconds - event.start_seconds) / duration };
}
function timingWindow(events, seconds, duration, horizon = 16, history = 4) {
  const now = clampSeek(seconds, duration);
  if (!Array.isArray(events) || !validNumber(horizon) || horizon <= 0 ||
      !validNumber(history) || history < 0 || history >= horizon) throw new Error("Invalid timing window.");
  let previousEnd = 0;
  for (const event of events) {
    if (!validNumber(event.start_seconds) || !validNumber(event.end_seconds) || event.start_seconds < previousEnd ||
        event.end_seconds <= event.start_seconds || event.end_seconds > duration || typeof event.label !== "string") throw new Error("Invalid timing events.");
    previousEnd = event.end_seconds;
  }
  const start = Math.max(0, now - history), end = Math.min(duration, start + horizon), span = end - start;
  const blocks = [];
  function add(first, last, event = null) {
    blocks.push({ start_seconds: first, end_seconds: last, event,
      kind: !event ? "gap" : event.label === "X" ? "unclear" : event.label === "N" ? "silence" : "chord",
      offset_fraction: (first - start) / span, width_fraction: (last - first) / span });
  }
  let cursor = start;
  if (span > 0) {
    for (const event of events) {
      if (event.end_seconds <= start || event.start_seconds >= end) continue;
      const first = Math.max(start, event.start_seconds), last = Math.min(end, event.end_seconds);
      if (first > cursor) add(cursor, first);
      add(first, last, event); cursor = last;
    }
    if (cursor < end) add(cursor, end);
  }
  return { start_seconds: start, end_seconds: end, now_seconds: now,
    playhead_fraction: span > 0 ? (now - start) / span : 0, blocks };
}
function boundedText(value, limit, allowEmpty = false) {
  return typeof value === "string" && value.length <= limit && !/[\r\n]/.test(value) && (allowEmpty || Boolean(value.trim()));
}
function pairedMetadataCases(payload, schema, reviewCases) {
  if (!payload || payload.schema_version !== schema || !Array.isArray(payload.cases) ||
      !payload.cases.length || payload.cases.length > 64) throw new Error("Invalid optional practice data.");
  const expected = new Map(reviewCases.map(item => [item.recording?.id, item.recording])), seen = new Set();
  for (const item of payload.cases) {
    const recording = item?.recording, id = recording?.id;
    if (typeof id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(id) || seen.has(id) ||
        typeof recording.audio_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(recording.audio_sha256) ||
        !Number.isInteger(recording.sample_rate_hz) || recording.sample_rate_hz <= 0 ||
        !validNumber(recording.duration_seconds) || recording.duration_seconds <= 0) {
      throw new Error("Invalid optional practice recording identity.");
    }
    seen.add(id);
  }
  return { cases: payload.cases, expected };
}
function validateRhythmManifest(payload, reviewCases) {
  const { cases, expected } = pairedMetadataCases(payload, "playalong-rhythm-1.0", reviewCases), result = new Map();
  for (const item of cases) {
    const beats = item.beat_times_seconds;
    if (item.status !== "estimated" || !Array.isArray(beats) || beats.length < 2 || beats.length > 5000 ||
        !validNumber(item.pulse_bpm) || item.pulse_bpm < 20 || item.pulse_bpm > 300 ||
        ![2, 4, null].includes(item.beats_per_bar) || !boundedText(item.meter_label, 100)) throw new Error("Invalid estimated beat grid.");
    let previous = -1;
    for (const beat of beats) {
      if (!validNumber(beat) || beat < 0 || beat > item.recording.duration_seconds || beat <= previous) throw new Error("Invalid estimated beat timestamps.");
      previous = beat;
    }
    if (expected.has(item.recording.id) && pairedRecording(item.recording, expected.get(item.recording.id))) result.set(item.recording.id, item);
  }
  return result;
}
function beatPosition(beats, seconds) {
  if (!Array.isArray(beats) || beats.length < 2) return null;
  if (!validNumber(seconds) || seconds < beats[0] || seconds > beats[beats.length - 1]) return null;
  if (seconds === beats[beats.length - 1]) return beats.length - 1;
  let low = 0, high = beats.length - 1;
  while (low + 1 < high) { const middle = Math.floor((low + high) / 2); if (beats[middle] <= seconds) low = middle; else high = middle; }
  return low + (seconds - beats[low]) / (beats[low + 1] - beats[low]);
}
function estimatedSpan(rhythm, start, end) {
  if (!rhythm || !validNumber(start) || !validNumber(end) || end <= start) return null;
  const first = beatPosition(rhythm.beat_times_seconds, start), last = beatPosition(rhythm.beat_times_seconds, end);
  if (first === null || last === null) return null;
  const beats = last - first;
  return { beats, bars: rhythm.beats_per_bar === null ? null : beats / rhythm.beats_per_bar };
}
function durationCaption(start, end, rhythm = null) {
  const duration = end - start, seconds = duration > 0 && duration < 0.05 ? "<0.1 s" : `${duration.toFixed(1)} s`, estimate = estimatedSpan(rhythm, start, end);
  if (!estimate) return seconds;
  const rounded = value => value > 0 && value < 0.05 ? "<0.1" : value.toFixed(1).replace(/\.0$/, "");
  if (estimate.bars !== null) {
    if (estimate.bars < 0.05) return `<0.1 bar · ${seconds}`;
    const count = rounded(estimate.bars);
    return `~${count} ${count === "1" ? "bar" : "bars"} · ${seconds}`;
  }
  if (estimate.beats < 0.05) return `<0.1 beat · ${seconds}`;
  const count = rounded(estimate.beats);
  return `~${count} ${count === "1" ? "beat" : "beats"} · ${seconds}`;
}
function validatePracticeManifest(payload, reviewCases) {
  const { cases, expected } = pairedMetadataCases(payload, "playalong-practice-1.0", reviewCases), result = new Map();
  for (const item of cases) {
    if (item.status !== "practice-suggestion" || !boundedText(item.meter_label, 100) ||
        !boundedText(item.beats_description, 300) || !boundedText(item.note, 600, true) ||
        !Array.isArray(item.patterns) || !item.patterns.length || item.patterns.length > 2) throw new Error("Invalid suggested strumming.");
    const ids = new Set();
    for (const pattern of item.patterns) {
      if (!pattern || !boundedText(pattern.id, 64) || ids.has(pattern.id) || !boundedText(pattern.name, 100) ||
          !boundedText(pattern.description, 600) || !Array.isArray(pattern.counts) || !Array.isArray(pattern.strokes) ||
          !pattern.counts.length || pattern.counts.length > 12 || pattern.counts.length !== pattern.strokes.length ||
          !pattern.counts.every(count => boundedText(count, 20)) || !pattern.strokes.every(stroke => ["D", "U", "—"].includes(stroke))) throw new Error("Invalid suggested strumming pattern.");
      ids.add(pattern.id);
    }
    if (expected.has(item.recording.id) && pairedRecording(item.recording, expected.get(item.recording.id))) result.set(item.recording.id, item);
  }
  return result;
}

function safeTeachingURL(value) {
  if (!boundedText(value, 2048) || /[\s\\\u0000-\u001f\u007f]/.test(value)) throw new Error("Invalid teaching source URL.");
  let url;
  try { url = new URL(value); } catch (_) { throw new Error("Invalid teaching source URL."); }
  if (url.protocol !== "https:" || url.username || url.password || url.port ||
      !url.hostname.includes(".") || /^(?:\d|\[)/.test(url.hostname) || url.hostname.endsWith(".localhost")) {
    throw new Error("Teaching sources must use public HTTPS links.");
  }
  return url.href;
}
function validateLearningManifest(payload, reviewCases, practiceById) {
  const safeId = value => boundedText(value, 64) && /^[a-z0-9][a-z0-9.-]*$/.test(value);
  if (!payload || payload.schema_version !== "playalong-learning-1.0" ||
      !safeId(payload.path_id) || !safeId(payload.revision) || payload.status !== "provisional-practice-path" ||
      !boundedText(payload.title, 100) || !Array.isArray(payload.steps) || !payload.steps.length || payload.steps.length > 64 ||
      !Array.isArray(payload.guides) || payload.guides.length > 16 || !Array.isArray(payload.inputs) || !payload.inputs.length || payload.inputs.length > 8 ||
      !(practiceById instanceof Map)) throw new Error("Invalid optional learning path.");
  const inputPaths = new Set();
  for (const input of payload.inputs) {
    if (!input || !boundedText(input.path, 240) || !/^[a-zA-Z0-9_./-]+\.json$/.test(input.path) ||
        input.path.startsWith("/") || input.path.split("/").some(part => !part || part === "." || part === "..") ||
        inputPaths.has(input.path) || typeof input.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(input.sha256)) throw new Error("Invalid learning source pin.");
    inputPaths.add(input.path);
  }
  const all = [...payload.steps, ...payload.guides];
  const { expected } = pairedMetadataCases({schema_version: "playalong-learning-1.0", cases: all}, "playalong-learning-1.0", reviewCases);
  const ids = new Set(), orders = new Set(), availableSteps = [], availableGuides = [];
  for (const item of all) {
    const isStep = payload.steps.includes(item);
    if (!safeId(item.id) || ids.has(item.id) || !boundedText(item.title, 160) ||
        !boundedText(item.skill_focus, 600) || !boundedText(item.prerequisites, 400) || !boundedText(item.setup_note, 600) ||
        !Array.isArray(item.sources) || !item.sources.length || item.sources.length > 6) throw new Error("Invalid learning step.");
    ids.add(item.id);
    const sourceIds = new Set();
    for (const source of item.sources) {
      if (!source || !safeId(source.id) || sourceIds.has(source.id) || !boundedText(source.title, 300)) throw new Error("Invalid learning teaching source.");
      sourceIds.add(source.id); safeTeachingURL(source.url);
    }
    if (isStep) {
      if (item.status !== "practice-suggestion" || !Number.isInteger(item.order) || item.order < 1 || item.order > 64 || orders.has(item.order) ||
          !safeId(item.practice_pattern_id)) throw new Error("Invalid practice path order or drill.");
      orders.add(item.order);
    } else if (item.status !== "riff-guide" || !boundedText(item.note, 600) || item.order !== undefined || item.practice_pattern_id !== undefined) {
      throw new Error("Riff guides must stay separate from strumming steps.");
    }
    const recording = expected.get(item.recording.id);
    if (!recording) continue;
    if (!pairedRecording(item.recording, recording)) throw new Error("Learning metadata does not match the available recording.");
    if (isStep) {
      const practice = practiceById.get(recording.id);
      if (!practice || !pairedRecording(practice.recording, recording) ||
          !practice.patterns.some(pattern => pattern.id === item.practice_pattern_id)) throw new Error("Learning step references an unavailable practice drill.");
      availableSteps.push(item);
    } else availableGuides.push(item);
  }
  return {path_id: payload.path_id, revision: payload.revision, title: payload.title,
    total_steps: payload.steps.length, steps: availableSteps.sort((a, b) => a.order - b.order), guides: availableGuides};
}
function practiceProgressKey(path, packId, step) {
  return "music-os-practice-progress:" + JSON.stringify([path.path_id, path.revision, packId, step.id, step.recording.audio_sha256]);
}
function practiceProgressExport(path, packId, step, practised) {
  if (typeof practised !== "boolean" || typeof packId !== "string" || !packId) throw new Error("Invalid practice progress.");
  return {schema_version: "playalong-progress-1.0", path_id: path.path_id, path_revision: path.revision,
    pack_id: packId, step_id: step.id, recording: {...step.recording}, practised,
    semantics: "Optional self-report that this practice step was tried; not mastery or chord/timing accuracy."};
}
function loadPracticeProgress(storage, path, packId, step) {
  try {
    const raw = storage.getItem(practiceProgressKey(path, packId, step));
    if (raw === null) return {practised: false, persistence: "saved-on-this-browser"};
    const value = JSON.parse(raw);
    if (value.schema_version !== "playalong-progress-1.0" || value.path_id !== path.path_id || value.path_revision !== path.revision ||
        value.pack_id !== packId || value.step_id !== step.id || !pairedRecording(value.recording, step.recording) ||
        typeof value.practised !== "boolean") throw new Error("Invalid saved practice progress.");
    return {practised: value.practised, persistence: "saved-on-this-browser"};
  } catch (_) { return {practised: false, persistence: "unavailable"}; }
}
function savePracticeProgress(storage, path, packId, step, practised) {
  const value = practiceProgressExport(path, packId, step, practised);
  try { storage.setItem(practiceProgressKey(path, packId, step), JSON.stringify(value)); return "saved-on-this-browser"; }
  catch (_) { return "unavailable"; }
}
function initialPracticeStep(steps, progressById) {
  return nextPracticeStep(steps, progressById) || [...steps].sort((a, b) => a.order - b.order)[0] || null;
}
function nextPracticeStep(steps, progressById, selectedStepId = null) {
  const ordered = [...steps].sort((a, b) => a.order - b.order), current = ordered.findIndex(step => step.id === selectedStepId);
  const following = current < 0 ? ordered : [...ordered.slice(current + 1), ...ordered.slice(0, current)];
  return following.find(step => !progressById.get(step.id)?.practised) || null;
}

function feedbackKey(packId, reviewCase) {
  return "music-os-playalong-feedback:" + JSON.stringify([packId, reviewCase.id, reviewCase.recording.audio_sha256]);
}
function feedbackExport(reviewCase, packId, feedback) {
  return { schema_version: "playalong-feedback-1.0", review_pack_id: packId, recording: reviewCase.recording,
    origin: reviewCase.origin || null, candidate_exposure: "model-exposed", gold: false,
    semantics: "Playback issue reports, not chord labels or verified change times. Times are captured at the tap and include listener reaction delay. raw_sounding_chord is the detector label; displayed_chord follows the recorded practice view, capo and quality_mode. Missing quality_mode in older reports means full-chords.",
    feedback: feedback.map(item => ({ ...item })) };
}
function captureFeedback(reviewCase, seconds, chart, id, createdAt, practice = {}) {
  if (!validNumber(seconds) || seconds < 0 || seconds > reviewCase.recording.duration_seconds) {
    throw new Error("The playback position is outside this song.");
  }
  validateCandidate(chart, reviewCase.recording);
  const event = currentEvent(chart.chords, seconds);
  const view = practice.view || "sounding-pitches", capo = view === "capo-shapes" ? practice.capo : 0;
  const qualityMode = practice.qualityMode ?? "full-chords";
  if (!["sounding-pitches", "capo-shapes"].includes(view) || !Number.isInteger(capo) || capo < 0 || capo > 12) throw new Error("Invalid practice display.");
  if (!QUALITY_MODES.includes(qualityMode)) throw new Error("Invalid chord quality display.");
  return { id, playback_seconds: seconds,
    source_seconds: seconds + (reviewCase.origin?.source_offset_seconds || 0),
    candidate_analysis_id: chart.analysis?.id || null, raw_sounding_chord: event?.label || null,
    displayed_chord: event ? displayedChord(event.label, view, capo, qualityMode) : null,
    practice_view: view, practice_capo: capo, quality_mode: qualityMode,
    reason: "not-sure", note: "", created_at: createdAt };
}
function validFeedback(item, recording) {
  return item && typeof item.id === "string" && item.id && validNumber(item.playback_seconds) &&
    item.playback_seconds >= 0 && item.playback_seconds <= recording.duration_seconds &&
    validNumber(item.source_seconds) && FEEDBACK_REASONS.includes(item.reason) &&
    typeof item.note === "string" && item.note.length <= 1000 && typeof item.created_at === "string" &&
    (item.quality_mode === undefined || QUALITY_MODES.includes(item.quality_mode));
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
    captureFeedback, loadFeedback, saveFeedback, timeLabel, transposePracticeLabel, practiceLabel, coreChordLabel, displayedChord, practiceTimeline,
    currentHold, timingWindow, validateRhythmManifest, beatPosition, estimatedSpan, durationCaption, validatePracticeManifest, safeTeachingURL, validateLearningManifest, practiceProgressKey, practiceProgressExport, loadPracticeProgress, savePracticeProgress, nextPracticeStep, initialPracticeStep };
}

if (typeof document !== "undefined") {
  const el = id => document.getElementById(id), audio = el("audio"), states = new Map();
  let cases = [], selected = null, state = null, generation = 0, packId = "", feedbackCounter = 0;
  let rhythmById = new Map(), practiceById = new Map(), learningPath = null;
  const progressById = new Map();
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

  function learningStep() { return learningPath?.steps.find(step => pairedRecording(step.recording, selected?.recording)) || null; }
  function renderLearning() {
    const step = learningStep(), guide = learningPath?.guides.find(item => pairedRecording(item.recording, selected?.recording));
    const item = step || guide;
    el("learning-path").hidden = !item;
    if (!item) return;
    el("learning-heading").textContent = guide ? "Riff learning guide" : "Suggested practice path";
    el("learning-order-note").textContent = guide ? "A separate riff guide; choose any song." : "Provisional order; choose any song.";
    el("learning-title").textContent = guide ? item.title : `Step ${step.order} of ${learningPath.total_steps} · ${item.title}`;
    el("learning-focus").textContent = item.skill_focus;
    el("learning-prerequisites").textContent = `Useful first: ${item.prerequisites}.`;
    el("learning-setup").textContent = item.setup_note;
    el("learning-guide-note").hidden = !guide;
    el("learning-guide-note").textContent = guide?.note || "";
    el("learning-step-controls").hidden = !step;
    el("learning-sources").replaceChildren();
    for (const source of item.sources) {
      const link = document.createElement("a"); link.href = safeTeachingURL(source.url); link.textContent = source.title;
      link.target = "_blank"; link.rel = "noopener noreferrer"; el("learning-sources").append(link);
    }
    if (!step) { el("learning-progress").textContent = "Use the guide for riff notes, fingering and setup."; return; }
    const progress = progressById.get(step.id) || {practised: false, persistence: "unavailable"};
    el("practised-step").checked = progress.practised;
    el("practised-step").disabled = !state?.primary || !state.audioReady;
    const drill = state?.strumming?.patterns.find(pattern => pattern.id === step.practice_pattern_id);
    el("start-path-drill").disabled = !drill || !state?.primary || !state.audioReady;
    el("start-path-drill").textContent = drill ? `Use starting drill: ${drill.name.replace(/^start:\s*/i, "")}` : "Starting drill unavailable";
    const next = nextPracticeStep(learningPath.steps, progressById, step.id);
    el("next-path-song").disabled = !next;
    el("next-path-song").textContent = next ? `Try next: ${next.title}` : "No other unpractised steps";
    const practised = learningPath.steps.filter(item => progressById.get(item.id)?.practised).length;
    let message = `${practised}/${learningPath.steps.length} available steps marked practised. This is your own record of trying a step, not a skill assessment.`;
    if (learningPath.steps.length < learningPath.total_steps) message += ` ${learningPath.steps.length} of ${learningPath.total_steps} path songs are available here.`;
    if (practised === learningPath.steps.length) message += " All available steps are marked; revisit any song whenever you like.";
    if (progress.persistence === "unavailable") message += " Browser storage is unavailable or the saved record was invalid; changes stay in this tab.";
    el("learning-progress").textContent = message;
  }

  function controls(enabled) {
    for (const id of ["restart", "go", "back", "mark", "save", "show", "reveal", "problem", "save-feedback", "copy-feedback", "quality-mode", "duration-mode", "strum-pattern"]) el(id).disabled = !enabled;
    if (enabled) { el("duration-mode").disabled = !state?.rhythm; el("strum-pattern").disabled = !state?.strumming; }
    if (!enabled) { el("practised-step").disabled = true; el("start-path-drill").disabled = true; }
  }
  function readyControls() { controls(Boolean(state?.primary && state.audioReady)); renderLearning(); }
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
    el("quality-mode").value = state.qualityMode;
    el("quality-info").hidden = state.qualityMode !== "core-chords";
    el("chord-view").options[0].textContent = `Capo ${capo} · played shapes`;
    el("practice").textContent = capo && state.practiceView === "capo-shapes"
      ? `Capo ${capo} on your guitar. Chords below are the shapes you play.`
      : "Chords below show sounding pitches, with no display transposition.";
  }
  function durationInfo() {
    const rhythm = state?.rhythm;
    el("duration-mode").value = rhythm ? state.durationMode : "seconds";
    el("duration-mode").disabled = !rhythm || !state?.primary || !state.audioReady;
    el("rhythm-note").hidden = !rhythm || state.durationMode !== "estimated";
    if (rhythm) el("rhythm-note").textContent = `Estimated beat grid · ${rhythm.beats_per_bar === null ? "beat count only" : `${rhythm.beats_per_bar} beats per bar`} · ~${Math.round(rhythm.pulse_bpm)} BPM · ${rhythm.meter_label}. Approximate counts; beat grid and meter need checking.`;
  }
  function renderStrumming() {
    const practice = state?.strumming;
    el("strumming").hidden = !practice;
    if (!practice) return;
    if (!practice.patterns.some(pattern => pattern.id === state.strumPatternId)) state.strumPatternId = practice.patterns[0].id;
    el("strum-pattern").replaceChildren();
    practice.patterns.forEach((pattern, index) => {
      const option = document.createElement("option"); option.value = pattern.id;
      option.textContent = /^(?:start(?:ing)?|next)\s*:/i.test(pattern.name) ? pattern.name : `${index ? "Next" : "Starting"}: ${pattern.name}`;
      el("strum-pattern").append(option);
    });
    el("strum-pattern").value = state.strumPatternId;
    const pattern = practice.patterns.find(item => item.id === state.strumPatternId);
    el("strum-description").textContent = pattern.description;
    el("strum-meter").textContent = `${practice.meter_label} · ${practice.beats_description}`;
    el("strum-note").textContent = practice.note;
    el("strum-grid").replaceChildren(); el("strum-grid").style.gridTemplateColumns = `repeat(${pattern.counts.length}, minmax(0, 1fr))`;
    pattern.counts.forEach((count, index) => {
      const box = document.createElement("div"); box.className = "strum-box";
      const number = document.createElement("span"); number.className = "strum-count"; number.textContent = count;
      const stroke = document.createElement("strong"), value = pattern.strokes[index];
      stroke.textContent = value === "D" ? "D ↓" : value === "U" ? "U ↑" : "—";
      stroke.setAttribute("aria-label", value === "D" ? "Downstroke" : value === "U" ? "Upstroke" : "Skip stroke; keep hand moving");
      if (value === "—") box.classList.add("strum-rest"); box.append(number, stroke); el("strum-grid").append(box);
    });
    readyControls();
  }
  async function selectCase(index) {
    const token = ++generation; selected = cases[index];
    if (!states.has(selected.id)) {
      const key = exposureKey(packId, selected), saved = loadFeedback(storage, feedbackKey(packId, selected), selected, packId);
      states.set(selected.id, { marks: [], notes: "", ...loadExposure(storage, key), exposureKey: key, packId,
        ...saved, feedbackKey: feedbackKey(packId, selected), primary: null, evidence: null, candidates: null,
        audioReady: false, practiceView: selected.practice?.capo ? "capo-shapes" : "sounding-pitches",
        qualityMode: "full-chords", durationMode: "estimated", strumPatternId: null, started: performance.now() });
    }
    state = states.get(selected.id); const target = state, reviewCase = selected;
    state.rhythm = rhythmById.get(selected.recording.id) || null;
    state.strumming = practiceById.get(selected.recording.id) || null;
    state.audioReady = false; controls(false); audio.pause(); audio.removeAttribute("src"); audio.load();
    el("comparison").hidden = true; el("candidate-events").replaceChildren(); el("candidate").replaceChildren();
    el("play-current").textContent = "Loading…"; el("upcoming").replaceChildren(); el("next-change").textContent = "";
    el("full-chord").hidden = true;
    el("current-hold").textContent = ""; el("hold-progress").hidden = true; el("timing-blocks").replaceChildren(); el("timing-range").textContent = "";
    el("feedback-detail").hidden = true; state.activeFeedback = null;
    el("notes").value = state.notes; el("export").hidden = true; el("feedback-export").hidden = true;
    el("point-notice").hidden = true;
    practiceInfo(); durationInfo(); renderStrumming(); renderLearning();
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
      const timeline = practiceTimeline(state.primary.chords, state.practiceView, selected.practice?.capo || 0, state.qualityMode);
      const snapshot = playbackSnapshot(timeline, audio.currentTime);
      const hold = currentHold(timeline, audio.currentTime);
      const rhythm = state.durationMode === "estimated" ? state.rhythm : null;
      const display = label => label === "N" ? "No chord" : label === "X" ? "Unclear" : label;
      el("play-current").textContent = snapshot.current ? display(snapshot.current.label) : "—";
      const rawCurrent = currentEvent(state.primary.chords, audio.currentTime);
      const fullLabel = rawCurrent ? displayedChord(rawCurrent.label, state.practiceView, selected.practice?.capo || 0) : null;
      el("full-chord").hidden = !snapshot.current || fullLabel === display(snapshot.current.label);
      el("full-chord").textContent = fullLabel ? `Full chord: ${fullLabel}` : "";
      el("hold-progress").hidden = !hold;
      el("current-hold").textContent = hold ? `${hold.event.label === "N" || hold.event.label === "X" ? "Span" : "Hold"}: ${durationCaption(hold.event.start_seconds, hold.event.end_seconds, rhythm)} · ${hold.remaining_seconds.toFixed(1)} s left` : "No charted chord at this moment.";
      if (hold) {
        el("hold-progress-fill").style.width = `${hold.progress_fraction * 100}%`;
        el("hold-progress").setAttribute("aria-valuenow", String(Math.round(hold.progress_fraction * 100)));
        el("hold-progress").setAttribute("aria-valuetext", `${hold.remaining_seconds.toFixed(1)} seconds left of ${hold.total_seconds.toFixed(1)} seconds`);
      }
      el("next-change").textContent = snapshot.upcoming.length ? `Next in ${Math.max(0, snapshot.upcoming[0].start_seconds - audio.currentTime).toFixed(1)} s` : "";
      el("upcoming").replaceChildren();
      for (const event of snapshot.upcoming) {
        const node = document.createElement("div"); node.className = "upcoming-chord";
        const chord = document.createElement("strong"); chord.textContent = display(event.label);
        chord.title = `Full chord: ${display(event.full_label)}`;
        const time = document.createElement("span"); time.textContent = timeLabel(event.start_seconds);
        const length = document.createElement("span"); length.textContent = durationCaption(event.start_seconds, event.end_seconds, rhythm);
        node.append(chord, time, length); el("upcoming").append(node);
      }
      const window = timingWindow(timeline, audio.currentTime, selected.recording.duration_seconds);
      el("timing-range").textContent = `${timeLabel(window.start_seconds)}–${timeLabel(window.end_seconds)} · widths show time`;
      el("timing-blocks").replaceChildren();
      for (const block of window.blocks) {
        const node = document.createElement("div"); node.className = `timing-block timing-${block.kind}`;
        node.style.left = `${block.offset_fraction * 100}%`; node.style.width = `${block.width_fraction * 100}%`;
        const label = block.event ? display(block.event.label) : "No chart";
        node.textContent = label;
        node.title = `${label} · ${block.event ? durationCaption(block.event.start_seconds, block.event.end_seconds, rhythm) : `${(block.end_seconds - block.start_seconds).toFixed(1)} s`}`;
        el("timing-blocks").append(node);
      }
      el("timing-playhead").style.left = `${window.playhead_fraction * 100}%`;
      el("timing-track").setAttribute("aria-label", `Chord timing from ${timeLabel(window.start_seconds)} to ${timeLabel(window.end_seconds)}. Current time ${timeLabel(window.now_seconds)}. Blank sections have no chart.`);
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

  el("start-path-drill").addEventListener("click", () => {
    const step = learningStep();
    if (!step || !state?.primary || !state.audioReady || !state.strumming?.patterns.some(pattern => pattern.id === step.practice_pattern_id)) return;
    state.strumPatternId = step.practice_pattern_id; renderStrumming();
    el("strumming").scrollIntoView({block: "center"}); el("strum-pattern").focus({preventScroll: true});
  });
  el("next-path-song").addEventListener("click", () => {
    const next = nextPracticeStep(learningPath?.steps || [], progressById, learningStep()?.id);
    if (!next) return;
    const index = cases.findIndex(item => pairedRecording(item.recording, next.recording));
    if (index < 0) return;
    el("case").value = String(index); selectCase(index).catch(error => status(error.message));
  });
  el("practised-step").addEventListener("change", () => {
    const step = learningStep(); if (!step || !state?.primary || !state.audioReady) return;
    const practised = el("practised-step").checked;
    progressById.set(step.id, {practised, persistence: savePracticeProgress(storage, learningPath, packId, step, practised)});
    renderLearning();
  });

  el("case").addEventListener("change", () => selectCase(Number(el("case").value)).catch(error => status(error.message)));
  el("restart").addEventListener("click", () => seek(0)); el("back").addEventListener("click", () => seek(audio.currentTime - 2));
  el("go").addEventListener("click", () => { try { seek(Number(el("seek").value)); } catch (error) { status(error.message); } });
  el("seek").addEventListener("keydown", event => { if (event.key === "Enter") el("go").click(); });
  el("problem").addEventListener("click", () => {
    try {
      const item = captureFeedback(selected, audio.currentTime, state.primary, `${Date.now()}-${++feedbackCounter}`, new Date().toISOString(),
        {view: state.practiceView, capo: selected.practice?.capo || 0, qualityMode: state.qualityMode});
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
  el("quality-mode").addEventListener("change", () => { state.qualityMode = el("quality-mode").value; practiceInfo(); updateClock(); });
  el("duration-mode").addEventListener("change", () => { state.durationMode = el("duration-mode").value; durationInfo(); updateClock(); });
  el("strum-pattern").addEventListener("change", () => { state.strumPatternId = el("strum-pattern").value; renderStrumming(); });
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
    el("case").disabled = false;
    const initialGeneration = generation + 1;
    await selectCase(0);
    // Both files are optional and independent. Their absence or invalid data
    // cannot prevent audio/chord playback or discard saved issue reports.
    await Promise.all([
      (async () => {
        try { rhythmById = validateRhythmManifest(await getJSON("/rhythm.json"), cases); }
        catch (_) { rhythmById = new Map(); }
        if (state) { state.rhythm = rhythmById.get(selected.recording.id) || null; durationInfo(); readyControls(); updateClock(); }
      })(),
      (async () => {
        try { practiceById = validatePracticeManifest(await getJSON("/practice.json"), cases); }
        catch (_) { practiceById = new Map(); }
        if (state) { state.strumming = practiceById.get(selected.recording.id) || null; renderStrumming(); }
      })()
    ]);
    try {
      learningPath = validateLearningManifest(await getJSON("/learning.json"), cases, practiceById);
      for (const step of learningPath.steps) progressById.set(step.id, loadPracticeProgress(storage, learningPath, packId, step));
    } catch (_) { learningPath = null; progressById.clear(); }
    // Resume only during untouched initial loading. A user song choice, seek or
    // playback takes priority over a later optional-metadata response.
    if (learningPath && generation === initialGeneration && audio.paused && audio.currentTime === 0) {
      const first = initialPracticeStep(learningPath.steps, progressById);
      const index = first ? cases.findIndex(item => pairedRecording(item.recording, first.recording)) : -1;
      if (index >= 0 && selected !== cases[index]) {
        el("case").value = String(index); await selectCase(index);
      }
    }
    renderLearning();
  })().catch(error => { controls(false); status(error.message); });
}
