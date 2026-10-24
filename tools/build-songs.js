#!/usr/bin/env node
"use strict";
// Strum Along song exporter: repo packs -> strumalong/songs/index.json + strumalong/songs/<id>.json.
//
// Read-only on every repo input (frozen packs, experiments/review/*.json, additions). Only writes strumalong/songs/.
// Reuses the Mac player's own pure helpers (experiments/review/app.js) so chart validation, display corrections,
// beat-grid pairing and Core/capo label maths are the same code the reviewed player uses.
//
//   node strumalong/tools/build-songs.js           # build (re-runnable, deterministic)
//   node strumalong/tools/build-songs.js --check   # build in memory and fail if songs/ on disk differs
//
// Spec: docs/STRUMALONG_APP.md (Data schema, Additions pipeline). No lyrics anywhere in this data.

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT = path.resolve(__dirname, "..");            // strumalong/
const REPO = path.resolve(ROOT, "..");                 // repo root
// STRUMALONG_* overrides exist only so the exporter can be exercised against fixtures without touching the real outputs.
const SONGS_DIR = process.env.STRUMALONG_SONGS_DIR || path.join(ROOT, "songs");
const REVIEW = path.join(REPO, "experiments/review");
const FIRST_TEN = path.join(REPO, "experiments/generated/automatic-first-ten-v1");
const ADDITIONS_PACK = process.env.STRUMALONG_ADDITIONS_PACK || path.join(REPO, "experiments/generated/strumalong-additions-v1");
const ADDITIONS_META = process.env.STRUMALONG_ADDITIONS_META || path.join(ROOT, "data/additions.json");
const app = require(path.join(REVIEW, "app.js"));
const Core = require(path.join(ROOT, "lib/core.js"));

const CHECK = process.argv.includes("--check");
const warnings = [];
const warn = msg => { warnings.push(msg); console.warn("WARN  " + msg); };

const read = p => fs.readFileSync(p);
const readJSON = p => JSON.parse(read(p));
const sha = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const r3 = x => Math.round(x * 1000) / 1000;
const r2 = x => Math.round(x * 100) / 100;
const r1 = x => Math.round(x * 10) / 10;
const isNum = x => typeof x === "number" && Number.isFinite(x);
const isStr = x => typeof x === "string" && x.trim().length > 0;

// ---------------------------------------------------------------- catalogue vocabulary

const GROUPS = [
  { id: "path", title: "Suggested practice path", note: "Provisional order; choose any song." },
  { id: "more", title: "More rock & pop", note: "New automatic charts, not yet reviewed." },
  { id: "riff", title: "Riff songs", note: "No strumming guide; the chord display does not teach the riff." },
  { id: "outside", title: "Also available", note: "" },
];
const GROUP_IDS = GROUPS.map(g => g.id);
const CAPO_SOURCES = ["catalogue", "suggested", "none"];

// Clean human titles for the ten prepared recordings (manifest titles carry "Artist - " prefixes and remaster tags).
const TITLES = {
  "troggs-wild-thing-youtube-20261011": ["Wild Thing", "The Troggs"],
  "bob-dylan-knockin-heavens-door-youtube-20261011": ["Knockin' on Heaven's Door", "Bob Dylan"],
  "van-morrison-brown-eyed-girl-youtube-20261011": ["Brown Eyed Girl", "Van Morrison"],
  "beatles-love-me-do-youtube-20261011": ["Love Me Do", "The Beatles"],
  "beatles-twist-and-shout-youtube-20261011": ["Twist and Shout", "The Beatles"],
  "white-stripes-seven-nation-army-youtube-20261011": ["Seven Nation Army", "The White Stripes"],
  "nirvana-come-as-you-are-youtube-20261011": ["Come as You Are", "Nirvana"],
  "radiohead-creep-youtube-20261010": ["Creep", "Radiohead"],
  "animals-house-rising-sun-official-20261011": ["The House of the Rising Sun", "The Animals"],
  "oasis-wonderwall-youtube-20261010": ["Wonderwall", "Oasis"],
};

// Love Me Do left the guitar-first learning path (learning.json selection_update), so it has no learning step.
// This metadata is condensed from catalogue/starter-four-teaching-review.json (sources love-andy, love-brad).
const LOVE_ME_DO = {
  skill_focus: "Begin with on-beat chord changes; treat deliberate silence and swing as separate, later tasks.",
  prerequisites: "G/C/D changes",
  setup_note: "Project open-grip proposal in standard tuning (EADGBE) with G, C and D shapes. Capo and exact recording pitch remain unchecked.",
  sources: [
    { title: "Andy Guitar: Love Me Do", url: "https://www.andyguitar.co.uk/videos/beatles-guitar-day-01-love-me-do" },
    { title: "Brad Litton / Simple Guitar: Love Me Do", url: "https://www.simpleguitar.com/blog/howtoplaylovemedo" },
  ],
};

// Alternate uploads for recordings whose catalogue upload cannot be embedded. Measured values may override these
// through strumalong/data/additions.json "alternates" (see applyAlternateOverrides).
const DEFAULT_ALTERNATES = {
  "nirvana-come-as-you-are-youtube-20261011": [{
    video_id: "vabnZ9-ex7o", uploader: "NirvanaVEVO", kind: "alternate", duration_seconds: 225,
    offset_seconds: 0, timing_checked: false, note: "Official video; its intro shifts timing. Use the sync nudge.",
  }],
};
const AGE_RESTRICTED = new Set(["nirvana-come-as-you-are-youtube-20261011"]);

// ---------------------------------------------------------------- helpers

function pairedRecording(a, b) {
  return a && b && a.id === b.id && a.audio_sha256 === b.audio_sha256 && a.sample_rate_hz === b.sample_rate_hz &&
    isNum(a.duration_seconds) && Math.abs(a.duration_seconds - b.duration_seconds) <= 0.000001;
}

const mod = (value, n) => ((value % n) + n) % n;

// HEURISTIC (not a repo-reviewed measurement; downbeats are NOT verified): the bar phase is the beat-index
// residue (mod beats_per_bar) that the app itself draws for most chord changes. Every native chord start that is
// not N or X and lies strictly inside the beat grid casts one vote for mod(round(beatPosition(start)), bpb), the same
// rounding lib/core.js uses to place a hold's first dot. Ties keep the lowest residue. Confidence needs at least
// 8 votes and a winning share of at least 0.7 (barPhaseConfident).
function barPhaseVote(beats, nativeEvents, bpb) {
  const votes = {};
  let eligible = 0;
  if (beats.length > 1) {
    for (const e of nativeEvents) {
      const start = e.start_seconds;
      if (e.label === "N" || e.label === "X" || !(start > beats[0] && start < beats[beats.length - 1])) continue;
      eligible++;
      const r = mod(Math.round(Core.beatPosition(beats, start)), bpb);
      votes[r] = (votes[r] || 0) + 1;
    }
  }
  const total = Object.values(votes).reduce((a, b) => a + b, 0);
  const top = Object.entries(votes).sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
  if (!top || !total) return { phase: 0, share: 0, votes: total, eligible };
  return { phase: Number(top[0]), share: top[1] / total, votes: total, eligible };
}

// A varying meter (beats_per_bar null, so assumed 4) makes a global residue vote meaningless: never confident.
function barPhaseConfident(vote, assumed) {
  return !assumed && vote.votes >= 8 && vote.share >= 0.7;
}

// Library-card chips: the Core shapes (at the song's capo) that carry the chart, by seconds held. N and X are
// skipped; shapes under 3% of chord time are dropped, slash shapes under 10%; longest first (ties by first
// appearance), at most 6. Rare shapes stay in the chart and diagrams; they are only left off the card.
function coreShapes(chords, capo) {
  const seconds = new Map(); // insertion order = first appearance
  for (const e of chords) {
    if (e.l === "N" || e.l === "X") continue;
    const shape = app.coreChordLabel(app.transposePracticeLabel(e.l, capo));
    if (shape === "N" || shape === "X") continue;
    seconds.set(shape, (seconds.get(shape) || 0) + (e.e - e.s));
  }
  const total = [...seconds.values()].reduce((a, b) => a + b, 0);
  if (!(total > 0)) return [];
  return [...seconds].map(([shape, held], order) => ({ shape, held, share: held / total, order }))
    .filter(x => x.share >= 0.03 && !(x.shape.includes("/") && x.share < 0.10))
    .sort((a, b) => b.held - a.held || a.order - b.order)
    .slice(0, 6)
    .map(x => x.shape);
}

function mergeAlternate(base, override) {
  const out = { ...base };
  if (isStr(override.uploader)) out.uploader = override.uploader;
  if (isNum(override.duration_seconds) && override.duration_seconds > 0) out.duration_seconds = override.duration_seconds;
  if (isNum(override.offset_seconds)) out.offset_seconds = r3(override.offset_seconds);
  if (typeof override.timing_checked === "boolean") out.timing_checked = override.timing_checked;
  if (isStr(override.note)) out.note = override.note;
  else if (out.timing_checked && override.timing_checked === true) out.note = "Official video; start offset measured against the analysed audio.";
  return out;
}

// additions.json "alternates" is loosely specified. Accepted shapes (all merge by video_id):
//   { "<recording_id>": [ {video_id, offset_seconds, timing_checked, ...}, ... ] }
//   { "<recording_id>": { video_id, ... } }            { "<recording_id>": { "<video_id>": {...} } }
//   { "<video_id>": { offset_seconds, ... } }
function applyAlternateOverrides(meta, recordingId, alternates) {
  const table = meta && meta.alternates;
  if (!table || typeof table !== "object") return alternates;
  const candidates = [];
  const byRecording = table[recordingId];
  if (Array.isArray(byRecording)) candidates.push(...byRecording);
  else if (byRecording && typeof byRecording === "object") {
    if (byRecording.video_id) candidates.push(byRecording);
    else for (const [video_id, value] of Object.entries(byRecording)) if (value && typeof value === "object") candidates.push({ video_id, ...value });
  }
  for (const alt of alternates) {
    const byVideo = table[alt.video_id];
    if (byVideo && typeof byVideo === "object" && !Array.isArray(byVideo)) candidates.push({ video_id: alt.video_id, ...byVideo });
  }
  let result = alternates.map(a => ({ ...a }));
  for (const cand of candidates) {
    if (!cand || !isStr(cand.video_id)) continue;
    const i = result.findIndex(a => a.video_id === cand.video_id);
    if (i >= 0) result[i] = mergeAlternate(result[i], cand);
    else if (isNum(cand.duration_seconds) && isStr(cand.uploader)) {
      result.push(mergeAlternate({ video_id: cand.video_id, uploader: cand.uploader, kind: "alternate", duration_seconds: cand.duration_seconds,
        offset_seconds: 0, timing_checked: false, note: "Alternate upload; timing unchecked. Use the sync nudge." }, cand));
    }
  }
  return result;
}

function videoEntry(v) {
  return { video_id: v.video_id, uploader: v.uploader, kind: v.kind, duration_seconds: v.duration_seconds,
    offset_seconds: v.offset_seconds, timing_checked: v.timing_checked, note: v.note,
    // Written only when false: the app skips this upload at start instead of waiting for a YouTube error.
    ...(v.embeddable === false ? { embeddable: false } : {}) };
}

// ---------------------------------------------------------------- song builder

/**
 * @param ctx { c, packId, packDir, hashes, rhythmCase, correctionSet, meta, extraAlternates }
 *   meta: { title, artist, group, order, capo, capo_source, setup_note, strumming, riff, learning, playable_embed?, embed_note? }
 */
function buildSong(ctx) {
  const { c, packId, packDir, hashes, rhythmCase, correctionSet, meta } = ctx;
  const bytes = read(path.join(packDir, "cases", c.id, "primary.json"));
  const primarySha = sha(bytes);
  if (primarySha !== c.artifacts.primary_sha256) throw new Error(`primary.json sha256 mismatch for ${c.id}`);
  const chart = app.validateCandidate(JSON.parse(bytes), c.recording);
  const display = app.correctedDisplayEvents(chart, correctionSet, packId, primarySha);
  if (!rhythmCase) throw new Error(`no paired rhythm grid for ${c.id}`);

  // chords: sounding label after display corrections; c:1 marks a corrected event
  const chords = display.map(e => {
    const out = { s: r3(e.start_seconds), e: r3(e.end_seconds), l: e.label };
    if (e.display_correction) out.c = 1;
    return out;
  });
  chords.forEach((e, i) => {
    if (!(e.s >= 0) || !(e.e > e.s)) throw new Error(`${c.id}: chord ${i} collapsed after rounding`);
    if (i && e.s < chords[i - 1].e) throw new Error(`${c.id}: chord ${i} overlaps previous after rounding`);
  });

  const corrections = (correctionSet ? correctionSet.corrections : []).map(item => {
    const span = item.replacement_span || item.expected_event;
    return { id: item.id, start: r3(span.start_seconds), end: r3(span.end_seconds), from: item.expected_event.label, to: item.replacement_label,
      note: `${item.source}; provisional relabel, boundaries unverified.` };
  });

  // rhythm
  const beats = rhythmCase.beat_times_seconds.map(r3);
  beats.forEach((b, i) => { if (i && !(b > beats[i - 1])) throw new Error(`${c.id}: beats not strictly increasing after rounding`); });
  const assumed = rhythmCase.beats_per_bar === null;
  const bpb = assumed ? 4 : rhythmCase.beats_per_bar;
  const vote = barPhaseVote(beats, chart.chords, bpb);
  const confident = barPhaseConfident(vote, assumed);
  const rhythm = { status: rhythmCase.status, bpm: r1(rhythmCase.pulse_bpm), beats_per_bar: bpb, beats_per_bar_assumed: assumed,
    meter_label: rhythmCase.meter_label, bar_phase: vote.phase, bar_phase_confident: confident, bar_phase_share: r2(vote.share) };

  // videos
  const embedBlocked = AGE_RESTRICTED.has(c.id) || meta.playable_embed === false;
  const src = c.source.source;
  const analysed = { video_id: src.video_id, uploader: src.uploader, kind: "analysed", duration_seconds: src.duration_seconds,
    offset_seconds: 0, timing_checked: true, note: "Chart computed from this upload's audio.", ...(embedBlocked ? { embeddable: false } : {}) };
  const alternates = applyAlternateOverrides(ctx.alternateMeta, c.id, (ctx.defaultAlternates || []).map(a => ({ ...a })));
  const videos = [analysed, ...alternates].map(videoEntry);

  const recording = { id: c.recording.id, duration_seconds: r3(c.recording.duration_seconds), audio_sha256: c.recording.audio_sha256 };
  const song = {
    schema: "strumalong-song-1",
    id: c.id, title: meta.title, artist: meta.artist, group: meta.group, order: meta.order,
    recording, videos,
    chart: { source: c.primary_name || "CREMA automatic draft", sha256: primarySha, status: "provisional", corrections },
    capo: meta.capo, capo_source: meta.capo_source,
    setup_note: meta.setup_note,
    rhythm, beats, chords,
    strumming: meta.strumming,
    learning: meta.learning,
    riff: meta.riff,
    provenance: { pack: packId, manifest_sha256: hashes.manifest, rhythm_sha256: hashes.rhythm, practice_sha256: hashes.practice,
      learning_sha256: hashes.learning, ...(hashes.additions ? { additions_sha256: hashes.additions } : {}) },
  };

  // library card
  const alt = alternates.find(a => a.timing_checked) || alternates[0];
  const card = {
    id: c.id, title: meta.title, artist: meta.artist, group: meta.group, order: meta.order,
    video_id: analysed.video_id, duration_seconds: r2(c.recording.duration_seconds),
    bpm: Math.round(rhythmCase.pulse_bpm), meter_label: rhythmCase.meter_label, capo: meta.capo,
    core_shapes: coreShapes(chords, meta.capo),
    playable_embed: !embedBlocked,
    embed_note: !embedBlocked ? "" : (meta.embed_note ||
      (alt && alt.timing_checked ? "Catalogue upload is age-restricted; using the official video (start offset measured)."
        : "Catalogue upload is age-restricted; using the official video with unchecked timing.")),
  };
  return { song, card, stats: { chords: chords.length, beats: beats.length, vote, confident } };
}

// ---------------------------------------------------------------- serialisation

// Valid JSON, diff-friendly: one top-level key per line, one chord per line, everything else minified.
function serializeSong(song) {
  const lines = Object.keys(song).map(k => {
    const body = k === "chords" ? "[\n" + song.chords.map(e => JSON.stringify(e)).join(",\n") + "\n]" : JSON.stringify(song[k]);
    return JSON.stringify(k) + ":" + body;
  });
  return "{\n" + lines.join(",\n") + "\n}\n";
}

// ---------------------------------------------------------------- first ten

function buildFirstTen(outputs, cards, stats) {
  const manifestBytes = read(path.join(FIRST_TEN, "manifest.json")), manifest = JSON.parse(manifestBytes);
  const rhythmBytes = read(path.join(REVIEW, "rhythm.json")), rhythm = JSON.parse(rhythmBytes);
  const practiceBytes = read(path.join(REVIEW, "practice.json")), practice = JSON.parse(practiceBytes);
  const learningBytes = read(path.join(REVIEW, "learning.json")), learning = JSON.parse(learningBytes);
  const hashes = { manifest: sha(manifestBytes), rhythm: sha(rhythmBytes), practice: sha(practiceBytes), learning: sha(learningBytes) };
  if (rhythm.manifest_sha256 && rhythm.manifest_sha256 !== hashes.manifest) throw new Error("rhythm.json is pinned to a different manifest.json");

  const rhythmById = app.validateRhythmManifest(rhythm, manifest.cases);
  const practiceById = new Map(practice.cases.map(p => [p.recording.id, p]));
  const stepById = new Map(learning.steps.map(s => [s.recording.id, s]));
  const guideById = new Map(learning.guides.map((g, i) => [g.recording.id, { g, i }]));
  const outsideOrder = manifest.cases.filter(c => !stepById.has(c.id) && !guideById.has(c.id)).map(c => c.id);

  for (const c of manifest.cases) {
    const titles = TITLES[c.id];
    if (!titles) throw new Error(`no clean title for ${c.id}; add it to TITLES`);
    const prac = practiceById.get(c.id), step = stepById.get(c.id), guideRef = guideById.get(c.id);
    if (!prac) throw new Error(`no practice case for ${c.id}`);
    const entry = step || (guideRef && guideRef.g) || null;
    for (const paired of [prac, entry]) if (paired && !pairedRecording(paired.recording, c.recording)) throw new Error(`recording identity mismatch for ${c.id}`);

    let group, order;
    if (step) { group = "path"; order = step.order; }
    else if (guideRef) { group = "riff"; order = guideRef.i + 1; }
    else { group = "outside"; order = outsideOrder.indexOf(c.id) + 1; }

    const capoValue = c.practice && Number.isInteger(c.practice.capo) ? c.practice.capo : 0;
    const isRiff = Boolean(guideRef);
    const learn = entry ? { skill_focus: entry.skill_focus, prerequisites: entry.prerequisites, sources: entry.sources.map(s => ({ title: s.title, url: s.url })) }
      : { skill_focus: LOVE_ME_DO.skill_focus, prerequisites: LOVE_ME_DO.prerequisites, sources: LOVE_ME_DO.sources };
    const strumming = {
      note: prac.note, beats_description: prac.beats_description,
      // Riff songs get no strum drill (spec): keep the practice note, drop the arrows.
      patterns: isRiff ? [] : prac.patterns.map(p => ({ id: p.id, name: p.name, counts: p.counts, strokes: p.strokes, description: p.description })),
    };
    const built = buildSong({
      c, packId: manifest.pack_id, packDir: FIRST_TEN, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: prac.display_corrections,
      defaultAlternates: DEFAULT_ALTERNATES[c.id], alternateMeta: readAdditionsMeta(),
      meta: { title: titles[0], artist: titles[1], group, order, capo: capoValue, capo_source: capoValue > 0 ? "catalogue" : "none",
        setup_note: entry ? entry.setup_note : LOVE_ME_DO.setup_note, strumming, learning: learn,
        riff: isRiff ? { note: guideRef.g.note } : null },
    });
    emit(outputs, cards, stats, built, manifest.pack_id);
  }
}

// ---------------------------------------------------------------- additions

let additionsMetaCache;
function readAdditionsMeta() {
  if (additionsMetaCache !== undefined) return additionsMetaCache;
  additionsMetaCache = null;
  if (!fs.existsSync(ADDITIONS_META)) return null;
  try {
    const bytes = read(ADDITIONS_META), meta = JSON.parse(bytes);
    if (meta.schema === "strumalong-additions-1") { meta.__sha = sha(bytes); additionsMetaCache = meta; }
    else warn(`${path.relative(REPO, ADDITIONS_META)}: unexpected schema ${JSON.stringify(meta.schema)}; ignored`);
  } catch (error) { warn(`${path.relative(REPO, ADDITIONS_META)} unreadable (${error.message}); ignored`); }
  return additionsMetaCache;
}

function validateAdditionsEntry(entry) {
  const problems = [];
  if (!isStr(entry.recording_id)) problems.push("recording_id");
  if (!isStr(entry.title)) problems.push("title");
  if (!isStr(entry.artist)) problems.push("artist");
  if (!Number.isInteger(entry.capo) || entry.capo < 0 || entry.capo > 12) problems.push("capo");
  if (!CAPO_SOURCES.includes(entry.capo_source)) problems.push("capo_source");
  if (!isStr(entry.setup_note)) problems.push("setup_note");
  const patterns = entry.strumming && entry.strumming.patterns;
  if (!entry.riff && (!isStr(entry.strumming && entry.strumming.note) || !Array.isArray(patterns) || !patterns.length)) problems.push("strumming");
  if (entry.group !== undefined && !GROUP_IDS.includes(entry.group)) problems.push("group");
  return problems;
}

function buildAdditions(outputs, cards, stats) {
  const rel = p => path.relative(REPO, p);
  const manifestPath = path.join(ADDITIONS_PACK, "manifest.json"), rhythmPath = path.join(ADDITIONS_PACK, "rhythm.json");
  if (!fs.existsSync(manifestPath)) return console.log(`additions: ${rel(manifestPath)} not found; skipped`);
  const meta = readAdditionsMeta();
  if (!meta) return console.log(`additions: ${rel(ADDITIONS_META)} missing or unusable; skipped`);
  if (!fs.existsSync(rhythmPath)) return console.log(`additions: ${rel(rhythmPath)} not found; skipped`);

  let manifest, manifestBytes, rhythmBytes, rhythmById;
  try {
    manifestBytes = read(manifestPath); manifest = JSON.parse(manifestBytes);
    rhythmBytes = read(rhythmPath);
    const rhythm = JSON.parse(rhythmBytes);
    if (rhythm.manifest_sha256 && rhythm.manifest_sha256 !== sha(manifestBytes)) throw new Error("rhythm.json is pinned to a different manifest.json");
    rhythmById = app.validateRhythmManifest(rhythm, manifest.cases);
  } catch (error) { return warn(`additions pack unusable (${error.message}); skipped all additions`); }

  const hashes = { manifest: sha(manifestBytes), rhythm: sha(rhythmBytes), practice: meta.__sha, learning: meta.__sha, additions: meta.__sha };
  const packId = manifest.pack_id || "strumalong-additions-v1";
  const entries = [...meta.songs].sort((a, b) => (a.order ?? 1e9) - (b.order ?? 1e9));
  const caseById = new Map(manifest.cases.map(c => [c.id, c]));
  for (const c of manifest.cases) if (!entries.some(e => e.recording_id === c.id)) warn(`additions: manifest case ${c.id} has no entry in additions.json; skipped`);

  let n = 0;
  for (const entry of entries) {
    const c = caseById.get(entry.recording_id);
    if (!c) { warn(`additions: ${entry.recording_id} is in additions.json but not in the manifest; skipped`); continue; }
    const problems = validateAdditionsEntry(entry);
    if (problems.length) { warn(`additions: ${c.id} has invalid metadata (${problems.join(", ")}); skipped`); continue; }
    try {
      const riff = entry.riff && isStr(entry.riff.note) ? { note: entry.riff.note } : null;
      const strumming = { note: entry.strumming ? entry.strumming.note || "" : "", ...(entry.strumming && entry.strumming.beats_description ? { beats_description: entry.strumming.beats_description } : {}),
        patterns: riff ? [] : entry.strumming.patterns.map(p => ({ id: p.id, name: p.name, counts: p.counts, strokes: p.strokes, description: p.description })) };
      const built = buildSong({
        c, packId, packDir: ADDITIONS_PACK, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: undefined,
        defaultAlternates: [], alternateMeta: meta,
        meta: { title: entry.title, artist: entry.artist, group: entry.group || "more", order: Number.isInteger(entry.order) ? entry.order : ++n,
          // "suggested" with capo 0 means no capo is suggested: the song contract is capo_source "none" exactly at capo 0.
          capo: entry.capo, capo_source: entry.capo > 0 ? entry.capo_source : "none", setup_note: entry.setup_note, strumming, riff,
          playable_embed: entry.playable_embed, embed_note: entry.embed_note,
          learning: { skill_focus: entry.skill_focus || "", prerequisites: entry.prerequisites || "",
            sources: (entry.sources || []).map(s => ({ title: s.title, url: s.url })) } },
      });
      emit(outputs, cards, stats, built, packId);
    } catch (error) { warn(`additions: ${c.id} skipped (${error.message})`); }
  }
}

// ---------------------------------------------------------------- output

function emit(outputs, cards, stats, built, packId) {
  const text = serializeSong(built.song);
  if (outputs.has(built.song.id + ".json")) throw new Error(`duplicate song id ${built.song.id}`);
  outputs.set(built.song.id + ".json", text);
  cards.push(built.card);
  stats.push({ id: built.song.id, pack: packId, group: built.song.group, bytes: Buffer.byteLength(text), capo: built.song.capo,
    bpb: built.song.rhythm.beats_per_bar, assumed: built.song.rhythm.beats_per_bar_assumed, bpm: built.song.rhythm.bpm,
    phase: built.song.rhythm.bar_phase, share: built.song.rhythm.bar_phase_share, confident: built.song.rhythm.bar_phase_confident,
    votes: built.stats.vote.votes, chords: built.stats.chords, beats: built.stats.beats, shapes: built.card.core_shapes.length,
    corrected: built.song.chords.filter(e => e.c).length, embed: built.card.playable_embed });
}

function main() {
  const outputs = new Map(), cards = [], stats = [];
  buildFirstTen(outputs, cards, stats);
  buildAdditions(outputs, cards, stats);

  cards.sort((a, b) => GROUP_IDS.indexOf(a.group) - GROUP_IDS.indexOf(b.group) || a.order - b.order || (a.id < b.id ? -1 : 1));
  const used = new Set(cards.map(c => c.group));
  const index = { schema: "strumalong-catalogue-1", groups: GROUPS.filter(g => used.has(g.id)), songs: cards };
  outputs.set("index.json", JSON.stringify(index, null, 2) + "\n");

  fs.mkdirSync(SONGS_DIR, { recursive: true });
  const existing = fs.readdirSync(SONGS_DIR).filter(f => f.endsWith(".json"));
  const stale = existing.filter(f => !outputs.has(f));

  if (CHECK) {
    const diffs = [...outputs].filter(([f, text]) => !fs.existsSync(path.join(SONGS_DIR, f)) || read(path.join(SONGS_DIR, f)).toString() !== text).map(([f]) => f);
    if (diffs.length || stale.length) {
      console.error(`CHECK FAILED: out of date: ${diffs.join(", ") || "-"}; stale: ${stale.join(", ") || "-"}`);
      process.exit(1);
    }
    console.log(`CHECK OK: ${outputs.size} files up to date`);
    return;
  }
  for (const [f, text] of outputs) fs.writeFileSync(path.join(SONGS_DIR, f), text);
  for (const f of stale) { fs.unlinkSync(path.join(SONGS_DIR, f)); console.log(`removed stale ${f}`); }

  for (const s of stats) {
    console.log(`${s.id.slice(0, 44).padEnd(44)} ${s.group.padEnd(7)} chords=${String(s.chords).padStart(3)} beats=${String(s.beats).padStart(3)} bpm=${String(s.bpm).padEnd(5)} ` +
      `bpb=${s.bpb}${s.assumed ? "(assumed)" : ""} phase=${s.phase} share=${s.share.toFixed(2)}/${s.votes}v ${s.confident ? "CONFIDENT" : "approx"} ` +
      `capo=${s.capo} shapes=${s.shapes} corrected=${s.corrected} embed=${s.embed} bytes=${s.bytes}`);
  }
  console.log(`wrote ${stats.length} songs + index.json to ${path.relative(REPO, SONGS_DIR)}${warnings.length ? `; ${warnings.length} warning(s)` : ""}`);
}

module.exports = { barPhaseVote, barPhaseConfident, coreShapes };

if (require.main === module) main();
