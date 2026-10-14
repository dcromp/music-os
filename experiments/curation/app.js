"use strict";

function finite(value) { return typeof value === "number" && Number.isFinite(value); }
function sameRecording(a, b) { return ["id", "audio_sha256", "duration_seconds", "sample_rate_hz"].every(key => a?.[key] === b?.[key]); }
function seekTime(value, duration) {
  if (!finite(value) || !finite(duration) || duration <= 0) throw new Error("Use a finite audio position.");
  return Math.max(0, Math.min(value, duration));
}
function validateEdits(edits, duration) {
  if (!Array.isArray(edits) || edits.length > 500 || !finite(duration) || duration <= 0) throw new Error("Invalid correction list.");
  let previous = 0;
  for (const edit of edits) {
    if (!finite(edit.start_seconds) || !finite(edit.end_seconds) || edit.start_seconds < previous || edit.end_seconds <= edit.start_seconds || edit.end_seconds > duration ||
        typeof edit.label !== "string" || edit.label.length > 100 || !/^(?:N|X|[A-G][#b]?[A-Za-z0-9#b():,./+*\-]*)$/.test(edit.label)) throw new Error("Use ordered, non-overlapping spans and sounding chord labels (or N/X).");
    previous = edit.end_seconds;
  }
  return edits;
}
function overlayEdits(events, edits, duration) {
  validateEdits(edits, duration);
  const bounds = [...new Set([0, duration, ...events.flatMap(event => [event.start_seconds, event.end_seconds]), ...edits.flatMap(edit => [edit.start_seconds, edit.end_seconds])])].sort((a, b) => a - b);
  const result = [];
  let sourceIndex = 0, editIndex = 0;
  for (let index = 0; index + 1 < bounds.length; index++) {
    const first = bounds[index], last = bounds[index + 1];
    while (sourceIndex < events.length && events[sourceIndex].end_seconds <= first) sourceIndex++;
    while (editIndex < edits.length && edits[editIndex].end_seconds <= first) editIndex++;
    const edit = edits[editIndex], native = events[sourceIndex];
    const replacement = edit && edit.start_seconds <= first && first < edit.end_seconds;
    const original = native && native.start_seconds <= first && first < native.end_seconds;
    if (!replacement && !original) continue;
    const label = replacement ? edit.label : native.label, origin = replacement ? "review-edit" : "native";
    const previous = result[result.length - 1];
    if (previous && previous.end_seconds === first && previous.label === label && previous.origin === origin) previous.end_seconds = last;
    else result.push({start_seconds: first, end_seconds: last, label, origin});
  }
  return result;
}
function startSession(actor, now, wall, id, task) {
  if (!["human", "agent", "qa"].includes(actor) || !finite(now) || !Number.isFinite(Date.parse(wall)) || typeof id !== "string" || !id || typeof task !== "string" || !task) throw new Error("Choose the reviewer type before starting.");
  return {actor, began: now, lastActivity: now, started_at: wall, id, task};
}
function sessionElapsed(session, now) {
  if (!session) return 0;
  if (!finite(now) || now < session.began) throw new Error("Review clock moved backwards.");
  return Math.min(1800, (now - session.began) / 1000);
}
function sessionTick(session, now, playing) {
  if (!session) return {session: null, cutoff: null};
  sessionElapsed(session, now);
  const updated = playing ? {...session, lastActivity: now} : session;
  const cutoff = Math.min(session.began + 1800000, playing ? Infinity : updated.lastActivity + 60000);
  return {session: updated, cutoff: now >= cutoff ? cutoff : null};
}
function endSession(session, now, wall) {
  if (!session || !Number.isFinite(Date.parse(wall))) throw new Error("No active review session.");
  return {id: session.id, actor: session.actor, task: session.task, started_at: session.started_at, ended_at: wall,
    active_seconds: sessionElapsed(session, now)};
}
function reviewEffort(sessions) {
  return Object.fromEntries(["human", "agent", "qa"].map(actor => [actor, {measured: sessions.some(item => item.actor === actor),
    seconds: sessions.filter(item => item.actor === actor).reduce((sum, item) => sum + item.active_seconds, 0)}]));
}
function validateDraft(draft, manifest, item, review) {
  if (draft?.schema_version !== "catalogue-curation-draft-1.0" || draft.status !== "model-exposed-curation-draft" || draft.gold !== false ||
      draft.pack_id !== manifest.pack_id || !sameRecording(draft.recording, item.recording) ||
      !draft.base_artifacts || Object.keys(draft.base_artifacts).length !== Object.keys(item.artifacts).length ||
      Object.entries(item.artifacts).some(([key, value]) => draft.base_artifacts[key] !== value) || !Number.isInteger(draft.revision) || draft.revision < 0) throw new Error("Saved draft belongs to different source audio/charts.");
  validateEdits(draft.chord_edits, item.recording.duration_seconds);
  if (!Array.isArray(draft.checked_points) || new Set(draft.checked_points).size !== draft.checked_points.length || draft.checked_points.some(id => !review.points.some(point => point.id === id)) || !Array.isArray(draft.sessions)) throw new Error("Invalid saved review state.");
  for (const item of draft.sessions) if (!["human", "agent", "qa"].includes(item.actor) || !finite(item.active_seconds) || item.active_seconds < 0 || item.active_seconds > 1800) throw new Error("Invalid saved review effort.");
  return draft;
}

if (typeof module !== "undefined") module.exports = {sameRecording, seekTime, validateEdits, overlayEdits, startSession, sessionElapsed, sessionTick, endSession, reviewEffort, validateDraft};

if (typeof document !== "undefined") {
  const el = id => document.getElementById(id), audio = el("audio");
  let manifest, selected, primary, secondary, review, draft, timer = null, dirty = false, busy = false, generation = 0;
  let reviewEvents = [], playbackEnd = null;
  const now = () => performance.now(), wall = () => new Date().toISOString();
  const status = message => { el("status").textContent = message; };
  function node(tag, value) { const item = document.createElement(tag); item.textContent = value; return item; }
  function safeURL(value) {
    const parsed = new URL(value, location.href);
    if (parsed.origin !== location.origin || !parsed.pathname.startsWith("/cases/") || parsed.search || parsed.hash) throw new Error("Invalid local asset URL.");
    return parsed.href;
  }
  async function json(url, options) {
    const response = await fetch(url, {...options, cache: "no-store"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
    return result;
  }
  function controls() {
    for (const id of ["save", "add-edit", "add-section", "export", "source-view", "use-span", "go", "seek", "edit-start", "edit-end", "edit-label", "edit-note", "section-start", "section-end", "section-name", "setup_notes", "rhythm_notes", "review_notes"]) el(id).disabled = busy || !draft;
    el("case").disabled = busy || !manifest;
    for (const node of document.querySelectorAll("#points input, #points button, #edits button, #sections button")) node.disabled = busy || !draft;
    el("start-review").disabled = busy || !draft || Boolean(timer);
    el("pause-review").disabled = busy || !timer;
    el("actor").disabled = Boolean(timer) || busy;
    el("task").disabled = Boolean(timer) || busy;
  }
  function renderEffort() {
    if (!draft) return;
    const value = reviewEffort(draft.sessions);
    el("effort").textContent = `Human review: ${value.human.measured ? value.human.seconds.toFixed(1) + " s" : "unmeasured"}. Agent review: ${value.agent.measured ? value.agent.seconds.toFixed(1) + " s" : "unmeasured"}. QA is excluded (${value.qa.seconds.toFixed(1)} s).`;
    el("active-time").textContent = timer ? `Review running · ${sessionElapsed(timer, now()).toFixed(1)} s` : "Review timer paused";
  }
  function renderTimeline() {
    if (!primary) return;
    const choice = el("source-view").value;
    reviewEvents = choice === "crema" ? secondary.chords : choice === "btc" ? primary.chords : overlayEdits(primary.chords, draft.chord_edits, selected.recording.duration_seconds);
    el("events").replaceChildren();
    for (const event of reviewEvents) {
      const row = document.createElement("tr");
      row.append(node("td", event.start_seconds.toFixed(3)), node("td", event.end_seconds.toFixed(3)), node("td", event.label), node("td", event.origin || "native"));
      const cell = document.createElement("td"), button = node("button", "Replay");
      button.addEventListener("click", () => replay(event.start_seconds, Math.min(selected.recording.duration_seconds, event.end_seconds + 1)));
      cell.append(button); row.append(cell); row.dataset.start = event.start_seconds; row.dataset.end = event.end_seconds; el("events").append(row);
    }
    clock();
  }
  function renderChanges() {
    for (const [key, target, title] of [["chord_edits", "edits", "label"], ["sections", "sections", "name"]]) {
      el(target).replaceChildren();
      draft[key].forEach((item, index) => {
        const row = node("div", `${item.start_seconds.toFixed(3)}–${item.end_seconds.toFixed(3)} s · ${item[title]} · ${item.note || ""}`);
        const button = node("button", "Remove");
        button.addEventListener("click", () => { if (busy || !draft) return; draft[key].splice(index, 1); dirty = true; renderChanges(); renderTimeline(); });
        row.append(button); el(target).append(row);
      });
    }
  }
  function renderPoints() {
    el("points").replaceChildren();
    for (const point of review.points) {
      const row = document.createElement("div"), replayButton = node("button", `${point.start_seconds.toFixed(1)}–${point.end_seconds.toFixed(1)} s`);
      replayButton.addEventListener("click", () => replay(point.start_seconds, point.end_seconds));
      const label = document.createElement("label"), check = document.createElement("input"); check.type = "checkbox";
      check.checked = draft.checked_points.includes(point.id);
      check.addEventListener("change", () => { if (busy || !draft) return; draft.checked_points = check.checked ? [...draft.checked_points, point.id] : draft.checked_points.filter(id => id !== point.id); dirty = true; });
      label.append(check, document.createTextNode(" Reviewed this window"));
      row.append(replayButton, node("span", point.reason), label); el("points").append(row);
    }
  }
  function sourceContext() {
    const context = review.source_context;
    el("context").replaceChildren(node("p", `Teacher setup: ${context.setup.tuning}; capo ${context.setup.capo === null ? "not confirmed" : context.setup.capo}. ${context.setup.tuning_status}. ${context.setup.capo_status}.`),
      node("p", `Entry shapes: ${context.entry_shapes?.join(", ") || "Riff/section instruction required; no complete chord palette supplied"}.`),
      node("p", `Rhythm proposal: ${context.rhythm_hypothesis}`));
    for (const item of context.correction_needs) el("context").append(node("p", item));
    if (context.context_update) el("context").append(node("p", `Source review ${context.context_update.checked_date}: ${context.context_update.note}`));
    if (review.practice_palette?.grips?.length) {
      el("context").append(node("p", "Project grip examples · low string to high string; x = mute, 0 = open. Frets are relative to the proposed capo. Notes checked symbolically; exact recorded voicings and suitability remain unverified."));
      const grid = document.createElement("div"); grid.className = "grip-grid";
      for (const grip of review.practice_palette.grips) grid.append(node("code", `${grip.shape}: ${grip.frets_low_to_high.map(value => value === null ? "x" : value).join(" ")}`));
      el("context").append(grid);
    }
    for (const source of context.sources) {
      const url = new URL(source.url);
      if (url.protocol !== "https:" || url.username || url.password) continue;
      const link = node("a", source.title); link.href = source.url; link.target = "_blank"; link.rel = "noopener noreferrer"; el("context").append(link);
    }
    const stats = review.statistics;
    el("statistics").textContent = `${stats.primary_intervals} BTC intervals; ${stats.secondary_intervals} CREMA intervals; ${stats.short_primary_events} BTC events under 0.5 s; ${stats.flags} model flags. These are workload hints, not error counts.`;
  }
  function clock() {
    if (!draft) return;
    const seconds = audio.currentTime, event = reviewEvents.find(item => item.start_seconds <= seconds && seconds < item.end_seconds);
    el("position").textContent = `${seconds.toFixed(2)} / ${selected.recording.duration_seconds.toFixed(2)} s`;
    el("current").textContent = event?.label || "Unlabelled gap";
    for (const row of el("events").children) row.classList.toggle("active", Number(row.dataset.start) <= seconds && seconds < Number(row.dataset.end));
    if (playbackEnd !== null && seconds >= playbackEnd) { audio.pause(); playbackEnd = null; }
  }
  async function replay(first, last) {
    if (!finite(audio.duration) || Math.abs(audio.duration - selected.recording.duration_seconds) > 0.02) return status("Audio is not ready or does not match this recording.");
    audio.currentTime = Math.max(0, first); playbackEnd = last;
    try { await audio.play(); } catch (_) { status("Use the audio play control to start playback."); }
    clock();
  }
  async function save() {
    if (!draft || !dirty || busy) return;
    busy = true; controls();
    try {
      const result = await json(selected.draft_url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(draft)});
      draft = validateDraft(result.draft, manifest, selected, review); dirty = false;
      status(`Draft revision ${draft.revision} saved separately. No lesson is approved.`);
    } finally { busy = false; controls(); renderEffort(); }
  }
  function pauseTimer(cutoff = now()) {
    if (!timer) return;
    draft.sessions.push(endSession(timer, cutoff, wall())); timer = null; dirty = true; controls(); renderEffort();
  }
  async function choose(index) {
    if (selected) {
      pauseTimer();
      try { await save(); } catch (error) { el("case").value = String(manifest.cases.indexOf(selected)); throw error; }
    }
    const token = ++generation; audio.pause(); audio.removeAttribute("src"); audio.load(); playbackEnd = null;
    selected = manifest.cases[index]; draft = null; busy = true; controls();
    primary = secondary = review = null; reviewEvents = [];
    for (const id of ["context", "points", "events", "edits", "sections"]) el(id).replaceChildren();
    for (const id of ["setup_notes", "rhythm_notes", "review_notes"]) el(id).value = "";
    for (const id of ["edit-start", "edit-end", "edit-label", "edit-note", "section-start", "section-end", "section-name"]) el(id).value = "";
    el("seek").value = "0";
    el("current").textContent = "Loading…"; el("statistics").textContent = "";
    el("effort").textContent = "Loading review effort…";
    status("Loading selected recording…");
    const values = await Promise.all([json(safeURL(selected.primary_url)), json(safeURL(selected.secondary_url)), json(safeURL(selected.review_url)), json(selected.draft_url)]);
    if (token !== generation) return;
    [primary, secondary, review] = values;
    if (![primary, secondary, review].every(value => sameRecording(value.recording, selected.recording))) throw new Error("Review audio, source context and charts do not match.");
    draft = validateDraft(values[3].draft, manifest, selected, review); dirty = false; busy = false;
    audio.src = safeURL(selected.audio_url); audio.load(); el("source-view").value = "working";
    for (const id of ["setup_notes", "rhythm_notes", "review_notes"]) el(id).value = draft[id];
    renderTimeline(); renderChanges(); renderPoints(); sourceContext(); renderEffort(); controls();
    status("Review workspace ready. Corrections remain separate model-exposed drafts.");
  }
  el("case").addEventListener("change", () => choose(Number(el("case").value)).catch(error => { busy = false; controls(); status(error.message); }));
  el("source-view").addEventListener("change", renderTimeline);
  el("go").addEventListener("click", () => {
    try {
      if (!el("seek").value.trim() || !finite(audio.duration) || Math.abs(audio.duration - selected.recording.duration_seconds) > 0.02) throw new Error("Matching audio must be ready before seeking.");
      playbackEnd = null; audio.currentTime = seekTime(Number(el("seek").value), selected.recording.duration_seconds); clock();
    } catch (error) { status(error.message); }
  });
  el("start-review").addEventListener("click", () => {
    try { timer = startSession(el("actor").value, now(), wall(), "session-" + crypto.randomUUID(), el("task").value); controls(); renderEffort(); }
    catch (error) { status(error.message); }
  });
  el("pause-review").addEventListener("click", () => { pauseTimer(); save().catch(error => status(error.message)); });
  el("save").addEventListener("click", () => { pauseTimer(); save().catch(error => status(error.message)); });
  el("use-span").addEventListener("click", () => {
    const event = reviewEvents.find(item => item.start_seconds <= audio.currentTime && audio.currentTime < item.end_seconds);
    if (!event) return status("No current labelled interval.");
    el("edit-start").value = event.start_seconds.toFixed(6); el("edit-end").value = event.end_seconds.toFixed(6); el("edit-label").value = event.label;
  });
  el("add-edit").addEventListener("click", () => {
    try {
      if (["edit-start", "edit-end", "edit-label"].some(id => !el(id).value.trim())) throw new Error("Enter a start, end and sounding label.");
      const item = {start_seconds: Number(el("edit-start").value), end_seconds: Number(el("edit-end").value), label: el("edit-label").value.trim(), note: el("edit-note").value};
      const next = [...draft.chord_edits, item].sort((a, b) => a.start_seconds - b.start_seconds); validateEdits(next, selected.recording.duration_seconds);
      draft.chord_edits = next; dirty = true; renderChanges(); renderTimeline();
      status("Replacement added to the working copy; raw detector outputs are unchanged.");
    } catch (error) { status(error.message); }
  });
  el("add-section").addEventListener("click", () => {
    try {
      if (["section-start", "section-end", "section-name"].some(id => !el(id).value.trim())) throw new Error("Enter section bounds and a name.");
      const item = {start_seconds: Number(el("section-start").value), end_seconds: Number(el("section-end").value), name: el("section-name").value.trim(), note: ""};
      const next = [...draft.sections, item].sort((a, b) => a.start_seconds - b.start_seconds); let previous = 0;
      for (const item of next) { if (!finite(item.start_seconds) || !finite(item.end_seconds) || item.start_seconds < previous || item.end_seconds <= item.start_seconds || item.end_seconds > selected.recording.duration_seconds) throw new Error("Sections must be bounded and non-overlapping."); previous = item.end_seconds; }
      draft.sections = next; dirty = true; renderChanges();
    } catch (error) { status(error.message); }
  });
  for (const id of ["setup_notes", "rhythm_notes", "review_notes"]) el(id).addEventListener("input", () => { if (busy || !draft) return; draft[id] = el(id).value; dirty = true; });
  el("export").addEventListener("click", () => {
    pauseTimer();
    const url = URL.createObjectURL(new Blob([JSON.stringify(draft, null, 2) + "\n"], {type: "application/json"}));
    const link = document.createElement("a"); link.href = url; link.download = selected.id + "-curation-draft.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  for (const name of ["timeupdate", "seeked", "loadedmetadata"]) audio.addEventListener(name, clock);
  for (const name of ["play", "pause", "ended"]) audio.addEventListener(name, () => { if (timer) timer.lastActivity = now(); });
  for (const name of ["pointerdown", "keydown"]) document.addEventListener(name, () => { if (timer) timer.lastActivity = now(); });
  function suspend(cutoff = now()) { pauseTimer(cutoff); save().catch(error => status(error.message)); }
  document.addEventListener("visibilitychange", () => { if (document.hidden) suspend(); });
  window.addEventListener("blur", () => suspend());
  window.addEventListener("beforeunload", event => { if (timer || dirty) { event.preventDefault(); event.returnValue = ""; } });
  setInterval(() => {
    const tick = sessionTick(timer, now(), !audio.paused);
    timer = tick.session;
    if (tick.cutoff !== null) {
      suspend(tick.cutoff); status("Review paused after inactivity or the 30-minute session limit.");
    }
    renderEffort();
  }, 1000);
  (async () => {
    manifest = await json("/manifest.json");
    if (manifest.schema_version !== "catalogue-curation-1.0" || manifest.gold !== false || !Array.isArray(manifest.cases) || !manifest.cases.length) throw new Error("Invalid review pack.");
    manifest.cases.forEach((item, index) => { const option = node("option", item.name); option.value = index; el("case").append(option); });
    await choose(0);
  })().catch(error => { busy = false; controls(); status(error.message); });
}
