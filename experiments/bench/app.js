"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const audio = $("audio");
  const state = { candidates: [], active: -1, audioUrl: null, objectUrl: null, audioName: "", duration: null, offset: 0, validForAudio: false, request: 0, chartRequest: 0, ratings: [], suiteCases: [], suiteRequest: 0 };
  const tolerance = (duration) => Math.max(0.1, duration * 0.001);

  function status(message, isError = false) {
    $("status").textContent = message;
    $("status").classList.toggle("error", isError);
  }

  function validateChart(chart) {
    if (!chart || chart.schema_version !== "1.0") throw new Error('Expected schema_version "1.0".');
    const recording = chart.recording;
    if (!recording || typeof recording.id !== "string" || !recording.id.trim() || typeof recording.title !== "string" || !recording.title.trim()) throw new Error("Recording needs a nonempty id and title.");
    if (!Number.isFinite(recording.duration_seconds) || recording.duration_seconds <= 0) throw new Error("Recording duration_seconds must be positive.");
    if (!Number.isFinite(recording.sample_rate_hz) || recording.sample_rate_hz <= 0) throw new Error("Recording sample_rate_hz must be positive.");
    const analysis = chart.analysis;
    if (!analysis || typeof analysis.id !== "string" || !analysis.id.trim() || typeof analysis.algorithm !== "string" || !analysis.algorithm.trim() || typeof analysis.version !== "string") throw new Error("Analysis needs an id, algorithm and version.");
    if (!Number.isFinite(analysis.runtime_seconds) || analysis.runtime_seconds < 0) throw new Error("Analysis runtime_seconds must be zero or positive.");
    if (!Array.isArray(chart.chords) || !chart.chords.length) throw new Error("The chart has no chord events.");
    let previousEnd = 0;
    chart.chords.forEach((chord, index) => {
      if (!chord || !Number.isFinite(chord.start_seconds) || !Number.isFinite(chord.end_seconds) || chord.start_seconds < 0 || chord.end_seconds <= chord.start_seconds) throw new Error(`Chord ${index + 1} has invalid boundaries.`);
      if (chord.start_seconds < previousEnd) throw new Error(`Chord ${index + 1} overlaps the preceding chord or is out of order.`);
      if (chord.end_seconds > recording.duration_seconds + 0.001) throw new Error(`Chord ${index + 1} ends beyond the recording duration.`);
      if (typeof chord.label !== "string" || !chord.label.trim()) throw new Error(`Chord ${index + 1} has no label.`);
      if (chord.confidence !== undefined && (!Number.isFinite(chord.confidence) || chord.confidence < 0 || chord.confidence > 1)) throw new Error(`Chord ${index + 1} confidence must be between 0 and 1.`);
      previousEnd = chord.end_seconds;
    });
    for (const field of ["beats_seconds", "downbeats_seconds"]) {
      if (chart[field] === undefined) continue;
      if (!Array.isArray(chart[field])) throw new Error(`${field} must be an array.`);
      let previous = -1;
      for (const value of chart[field]) {
        if (!Number.isFinite(value) || value < 0 || value > recording.duration_seconds + 0.001 || value <= previous) throw new Error(`${field} must contain increasing times within the recording.`);
        previous = value;
      }
    }
    return chart;
  }

  function activeChart() { return state.candidates[state.active]?.chart ?? null; }
  function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return "—";
    const sign = seconds < 0 ? "−" : "";
    const absolute = Math.abs(seconds);
    return `${sign}${Math.floor(absolute / 60)}:${(absolute % 60).toFixed(1).padStart(4, "0")}`;
  }

  function populateCandidates() {
    const select = $("candidate");
    select.replaceChildren();
    const blind = $("blind-mode").checked;
    if (!state.candidates.length) {
      select.add(new Option("Load a chart first", ""));
      select.disabled = true;
      return;
    }
    state.candidates.forEach((candidate, index) => select.add(new Option(blind ? `Version ${index + 1}` : candidate.name, String(index))));
    select.disabled = false;
    select.value = String(state.active);
  }

  function checkPair() {
    const chart = activeChart();
    syncSeekControls();
    state.validForAudio = false;
    $("save-rating").disabled = true;
    $("source-title").textContent = chart ? chart.recording.title : state.audioName || "No recording loaded";
    if (chart) {
      $("analysis-info").textContent = $("blind-mode").checked
        ? `Version ${state.active + 1} · ${formatTime(chart.recording.duration_seconds)} recording`
        : `${chart.analysis.algorithm} · ${chart.analysis.version} · ${chart.analysis.runtime_seconds.toFixed(2)} s analysis runtime`;
    } else $("analysis-info").textContent = "No analysis loaded";
    if (!chart) { status(state.audioUrl ? "Audio loaded. Choose an analysis JSON chart." : "Load the generated demo, or choose an audio file and its analysis JSON."); render(); return; }
    if (!state.audioUrl) { status("Chart loaded. Choose its matching audio recording."); render(); return; }
    if (!Number.isFinite(state.duration)) { status("Chart loaded. Waiting for audio metadata…"); render(); return; }
    const difference = Math.abs(state.duration - chart.recording.duration_seconds);
    if (difference > tolerance(chart.recording.duration_seconds)) {
      status(`Audio/chart duration mismatch: audio ${state.duration.toFixed(2)} s, chart ${chart.recording.duration_seconds.toFixed(2)} s. Choose the matching recording.`, true);
      render(); return;
    }
    state.validForAudio = true;
    $("save-rating").disabled = false;
    status(`Ready · Audio ${state.audioName || chart.recording.title} · ${chart.chords.length} chord events. Confirm this is the exact recording; duration alone cannot establish identity.`);
    render();
  }

  function setAudio(url, name, isObjectUrl = false) {
    audio.pause();
    if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = isObjectUrl ? url : null;
    state.audioUrl = url;
    state.audioName = name;
    state.duration = null;
    $("seek-position").value = "0";
    $("seek-position").setCustomValidity("");
    $("seek-status").textContent = "Go and Restart preserve whether playback is paused or playing.";
    audio.src = url;
    audio.load();
    checkPair();
  }

  function syncSeekControls() {
    const ready = Boolean(state.audioUrl) && Number.isFinite(state.duration) && state.duration > 0;
    for (const id of ["seek-position", "seek-go", "restart"]) $(id).disabled = !ready;
    if (ready) $("seek-position").max = String(state.duration);
  }

  function seekTo(seconds) {
    if (!state.audioUrl || !Number.isFinite(state.duration) || state.duration <= 0) return;
    audio.currentTime = seconds;
    $("seek-status").textContent = `Audio position ${formatTime(seconds)}. Display offset applies only to the chart.`;
    render();
  }

  // Binary search gives the first event ending after t. Intervals are [start, end).
  function eventAt(chords, time) {
    let left = 0, right = chords.length;
    while (left < right) {
      const middle = Math.floor((left + right) / 2);
      if (chords[middle].end_seconds <= time) left = middle + 1;
      else right = middle;
    }
    const event = chords[left];
    return { index: left, event: event && event.start_seconds <= time ? event : null };
  }

  function render() {
    const mediaTime = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    $("clock").textContent = formatTime(mediaTime);
    const chart = activeChart();
    if (!chart || !state.validForAudio) {
      $("current-chord").textContent = "—";
      $("current-detail").textContent = "Waiting for matching audio and chart";
      $("next-chord").textContent = "—";
      $("next-detail").textContent = "Upcoming chords appear here";
      return;
    }
    const chartTime = mediaTime + state.offset;
    const found = eventAt(chart.chords, chartTime);
    $("current-chord").textContent = found.event?.label ?? "—";
    $("current-detail").textContent = found.event
      ? `${formatTime(found.event.start_seconds)}–${formatTime(found.event.end_seconds)} · chart time ${formatTime(chartTime)}`
      : chartTime >= chart.recording.duration_seconds ? "End of chart" : "No chord labelled at this time";
    let nextIndex = found.event ? found.index + 1 : found.index;
    // Preview the next different label, keeping repeated same-label segments current.
    while (found.event && nextIndex < chart.chords.length && chart.chords[nextIndex].label === found.event.label && chart.chords[nextIndex].start_seconds === chart.chords[nextIndex - 1].end_seconds) nextIndex++;
    const next = chart.chords[nextIndex];
    $("next-chord").textContent = next?.label ?? "—";
    $("next-detail").textContent = next ? `In ${Math.max(0, next.start_seconds - chartTime).toFixed(1)} s · at ${formatTime(next.start_seconds)}` : "No further chord changes";
  }

  function localUrl(value) {
    if (typeof value !== "string") throw new Error("Generated asset URLs must be strings.");
    const url = new URL(value, location.href);
    if (url.origin !== location.origin || !["http:", "https:"].includes(url.protocol)) throw new Error("Generated asset URLs must point to this local server.");
    return url.href;
  }
  async function getJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Request failed (${response.status}): ${new URL(url, location.href).pathname}`);
    return response.json();
  }

  async function loadRecording(recording, request) {
    if (!Array.isArray(recording.candidates) || !recording.candidates.length) throw new Error("No analysis candidates are available. Run the lab suite first.");
    const audioUrl = localUrl(recording.audio_url);
    const candidates = await Promise.all(recording.candidates.map(async (candidate, index) => ({ name: typeof candidate.name === "string" ? candidate.name : `Version ${index + 1}`, chart: validateChart(await getJson(localUrl(candidate.url))) })));
    const firstRecording = candidates[0].chart.recording;
    if (candidates.some(({ chart }) => chart.recording.id !== firstRecording.id || chart.recording.duration_seconds !== firstRecording.duration_seconds)) throw new Error("The candidate charts refer to different recordings.");
    if (request !== state.request) return;
    state.candidates = candidates;
    state.active = 0;
    populateCandidates();
    setAudio(audioUrl, firstRecording.title);
  }

  function clearRecordingPair() {
    audio.pause();
    if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = null;
    state.audioUrl = null;
    state.audioName = "";
    state.duration = null;
    state.candidates = [];
    state.active = -1;
    state.offset = 0;
    $("offset").value = "0";
    $("offset").setCustomValidity("");
    audio.removeAttribute("src");
    audio.load();
    populateCandidates();
    checkPair();
  }

  function suiteCaseLabel(testCase) {
    const level = String(testCase.level ?? "Unspecified level");
    return `${/^level\b/i.test(level) ? level : `Level ${level}`} · ${testCase.name} · ${testCase.condition || "Standard condition"}`;
  }

  $("load-suite").addEventListener("click", async () => {
    const request = ++state.suiteRequest;
    $("load-suite").disabled = true;
    $("suite-status").textContent = "Loading synthetic suite…";
    try {
      const suite = await getJson("/api/suite");
      if (!Array.isArray(suite.cases) || !suite.cases.length) throw new Error("No synthetic cases are available.");
      const ids = new Set();
      suite.cases.forEach((testCase) => {
        if (!testCase || typeof testCase.id !== "string" || !testCase.id.trim() || ids.has(testCase.id) || typeof testCase.name !== "string" || !testCase.name.trim()) throw new Error("The suite has an invalid or duplicate case.");
        ids.add(testCase.id);
        localUrl(testCase.audio_url);
        if (!Array.isArray(testCase.candidates) || !testCase.candidates.length) throw new Error(`No charts are available for ${testCase.name}.`);
        testCase.candidates.forEach((candidate) => localUrl(candidate.url));
      });
      if (request !== state.suiteRequest) return;
      state.suiteCases = suite.cases;
      const select = $("suite-case");
      select.replaceChildren();
      state.suiteCases.forEach((testCase) => select.add(new Option(suiteCaseLabel(testCase), testCase.id)));
      select.value = state.suiteCases[0].id;
      select.disabled = false;
      $("load-case").disabled = false;
      $("suite-status").textContent = `${state.suiteCases.length} synthetic cases available. Choose a case and press Load case. Results on synthetic audio are an early screen, not proof of real-music performance.`;
    } catch (error) {
      if (request === state.suiteRequest) $("suite-status").textContent = `Could not load synthetic suite: ${error.message} Run the lab suite first, then try again.`;
    } finally { $("load-suite").disabled = false; }
  });
  $("suite-case").addEventListener("change", () => {
    const selected = state.suiteCases.find((testCase) => testCase.id === $("suite-case").value);
    if (selected) $("suite-status").textContent = `Selected ${suiteCaseLabel(selected)}. Press Load case to replace the current recording and chart.`;
  });
  $("load-case").addEventListener("click", async () => {
    const testCase = state.suiteCases.find((item) => item.id === $("suite-case").value);
    if (!testCase) { $("suite-status").textContent = "Run the lab suite first, then load its synthetic cases."; return; }
    const request = ++state.request;
    ++state.chartRequest;
    $("load-case").disabled = true;
    clearRecordingPair();
    status(`Loading synthetic case: ${testCase.name}…`);
    try { await loadRecording(testCase, request); }
    catch (error) { if (request === state.request) status(`Could not load synthetic case: ${error.message} Run the lab suite first if generated files are missing.`, true); }
    finally { $("load-case").disabled = !state.suiteCases.length; }
  });

  $("load-demo").addEventListener("click", async () => {
    const request = ++state.request;
    ++state.chartRequest;
    $("load-demo").disabled = true;
    status("Loading local demo…");
    try {
      const demo = await getJson("/api/demo");
      if (!Array.isArray(demo.candidates) || !demo.candidates.length) throw new Error("Demo has no analysis candidates. Generate the demo first.");
      if (request !== state.request) return;
      await loadRecording(demo, request);
    } catch (error) { if (request === state.request) status(`Could not load demo: ${error.message}`, true); }
    finally { $("load-demo").disabled = false; }
  });

  $("audio-file").addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    ++state.request;
    setAudio(URL.createObjectURL(file), file.name, true);
  });
  $("chart-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    ++state.request;
    const request = ++state.chartRequest;
    state.candidates = [];
    state.active = -1;
    populateCandidates();
    checkPair();
    status("Reading local analysis JSON…");
    try {
      const chart = validateChart(JSON.parse(await file.text()));
      if (request !== state.chartRequest) return;
      state.candidates = [{ name: `${chart.analysis.algorithm} · ${chart.analysis.version}`, chart }];
      state.active = 0;
      populateCandidates();
      checkPair();
    } catch (error) { if (request === state.chartRequest) status(`Invalid analysis JSON: ${error.message}`, true); }
  });
  $("candidate").addEventListener("change", (event) => { state.active = Number(event.target.value); checkPair(); });
  $("blind-mode").addEventListener("change", () => { populateCandidates(); checkPair(); });
  $("offset").addEventListener("input", (event) => {
    const value = Number(event.target.value);
    if (event.target.value !== "" && Number.isFinite(value) && Math.abs(value) <= 30) { state.offset = value; event.target.setCustomValidity(""); render(); }
    else event.target.setCustomValidity("Choose an offset between −30 and 30 seconds.");
  });
  $("reset-offset").addEventListener("click", () => { state.offset = 0; $("offset").value = "0"; $("offset").setCustomValidity(""); render(); });
  $("seek-position").addEventListener("input", () => $("seek-position").setCustomValidity(""));
  $("seek-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("seek-position");
    const seconds = Number(input.value);
    if (input.disabled) return;
    if (input.value.trim() === "" || !Number.isFinite(seconds) || seconds < 0 || seconds > state.duration) {
      input.setCustomValidity(`Choose an audio position between 0 and ${state.duration.toFixed(3)} seconds.`);
      input.reportValidity();
      return;
    }
    input.setCustomValidity("");
    seekTo(seconds);
  });
  $("restart").addEventListener("click", () => {
    if ($("restart").disabled) return;
    $("seek-position").value = "0";
    $("seek-position").setCustomValidity("");
    seekTo(0);
  });
  audio.addEventListener("loadedmetadata", () => { state.duration = audio.duration; checkPair(); });
  audio.addEventListener("durationchange", () => { if (Number.isFinite(audio.duration)) { state.duration = audio.duration; checkPair(); } });
  audio.addEventListener("error", () => { state.duration = null; state.validForAudio = false; syncSeekControls(); $("save-rating").disabled = true; status("Could not play this audio. Check that the file exists and the browser supports its format.", true); render(); });
  for (const event of ["timeupdate", "seeked", "pause", "play", "ended", "ratechange"]) audio.addEventListener(event, render);

  $("feedback-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.validForAudio || !$("offset").checkValidity()) return;
    const chart = activeChart();
    state.ratings.push({ time_utc: new Date().toISOString(), recording_id: chart.recording.id, source_title: chart.recording.title, audio_source: state.audioName, analysis_id: chart.analysis.id, algorithm: chart.analysis.algorithm, algorithm_version: chart.analysis.version, duration_seconds: chart.recording.duration_seconds, display_offset_seconds: state.offset, playhead_seconds: audio.currentTime.toFixed(3), followability_1_5: $("followability").value, enjoyment_1_5: $("enjoyment").value, notes: $("notes").value });
    $("saved-count").textContent = `${state.ratings.length} saved`;
    $("download-csv").disabled = false;
    $("show-csv").disabled = false;
    $("feedback-status").textContent = "Rating saved in this tab. Download CSV to keep it; the row records the current playback position.";
    $("feedback-form").reset();
    if (!$("csv-preview").hidden) $("csv-text").value = serializeCsv(state.ratings);
  });

  function serializeCsv(rows) {
    if (!rows.length) return "";
    const columns = Object.keys(rows[0]);
    const csvCell = (value) => {
      let text = String(value ?? "");
      if (typeof value === "string" && /^\s*[=+@\-\t\r]/.test(text)) text = "'" + text;
      return `"${text.replaceAll('"', '""')}"`;
    };
    return [columns.map(csvCell).join(","), ...rows.map((row) => columns.map((column) => csvCell(row[column])).join(","))].join("\r\n") + "\r\n";
  }

  $("show-csv").addEventListener("click", () => {
    if (!state.ratings.length) return;
    const preview = $("csv-preview");
    preview.hidden = !preview.hidden;
    $("show-csv").textContent = preview.hidden ? "Show CSV" : "Hide CSV";
    $("csv-text").value = serializeCsv(state.ratings);
  });
  $("download-csv").addEventListener("click", () => {
    if (!state.ratings.length) return;
    const csv = serializeCsv(state.ratings);
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `music-os-playtests-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener("beforeunload", () => { if (state.objectUrl) URL.revokeObjectURL(state.objectUrl); });
  function frame() { render(); requestAnimationFrame(frame); }
  requestAnimationFrame(frame);
})();
