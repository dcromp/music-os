"use strict";
// Sanity checks for a Strum Along additions pack. Read-only. Uses the learner player's own validators
// (experiments/review/app.js) and the app's chord vocabulary (strumalong/lib/chords.js), so the pack is
// accepted by exactly the code the exporter will use.
//   node check_pack.js <pack dir> <rhythm config json> [--json]
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const REPO = path.resolve(__dirname, "../../..");
const app = require(path.join(REPO, "experiments/review/app.js"));
const Chords = require(path.join(REPO, "strumalong/lib/chords.js"));
const [PACK, CONFIG] = [process.argv[2], process.argv[3]];
const AS_JSON = process.argv.includes("--json");
const sha = b => crypto.createHash("sha256").update(b).digest("hex");
const read = p => fs.readFileSync(p);
const manifest = JSON.parse(read(path.join(PACK, "manifest.json")));
const rhythm = JSON.parse(read(path.join(PACK, "rhythm.json")));
const config = JSON.parse(read(CONFIG)).recordings;
const expectedPath = path.join(__dirname, "expected-chords.json");
const expected = fs.existsSync(expectedPath) ? JSON.parse(read(expectedPath)) : {};
const rhythmById = app.validateRhythmManifest(rhythm, manifest.cases);

// Reduce to {root pitch class, major|minor|other} ignoring bass, extensions and suspensions' naming.
function family(label) {
  if (label === "N" || label === "X") return null;
  const p = Chords.parse(Chords.coreLabel(label).split("/")[0]);
  if (!p) return null;
  const q = p.quality;
  const kind = q === "" ? "" : /^m(?!aj)/.test(q) ? "m" : /^sus/.test(q) ? "sus" : q.startsWith("dim") ? "dim" : q.startsWith("aug") ? "aug" : "?";
  return { root: p.rootPc, kind, text: Chords.noteName(p.rootPc) + (kind === "?" ? q : kind) };
}
const EASY = new Set(["A", "Am", "C", "D", "Dm", "E", "Em", "G"]), HALF = new Set(["F", "Bm", "B7"]);
function shapeScore(events, capo) {
  let score = 0, total = 0;
  for (const e of events) {
    if (e.label === "N" || e.label === "X") continue;
    const d = e.end_seconds - e.start_seconds;
    total += d;
    const c = Chords.coreLabel(Chords.shapeForCapo(e.label, capo)).split("/")[0];
    score += EASY.has(c) ? d : HALF.has(c) ? d * 0.5 : 0;
  }
  return total ? score / total : 0;
}
function median(a) { const s = [...a].sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null; }

const report = [];
for (const c of manifest.cases) {
  const bytes = read(path.join(PACK, "cases", c.id, "primary.json"));
  const chart = app.validateCandidate(JSON.parse(bytes), c.recording);       // throws on mismatch
  if (sha(bytes) !== c.artifacts.primary_sha256) throw new Error("primary sha mismatch " + c.id);
  const rh = rhythmById.get(c.id);
  if (!rh) throw new Error("rhythm.json does not pair with " + c.id);
  const cfg = config[c.id];
  const events = chart.chords, dur = c.recording.duration_seconds;
  const bySecs = new Map();
  let nx = 0;
  for (const e of events) {
    const d = e.end_seconds - e.start_seconds;
    if (e.label === "N" || e.label === "X") { nx += d; continue; }
    bySecs.set(e.label, (bySecs.get(e.label) || 0) + d);
  }
  const chordSecs = dur - nx;
  const top = [...bySecs.entries()].sort((a, b) => b[1] - a[1]);
  // Core-family vocabulary (what a learner would see under "Simple")
  const famSecs = new Map();
  for (const [l, d] of bySecs) { const f = family(l); const k = f ? f.text : l; famSecs.set(k, (famSecs.get(k) || 0) + d); }
  const famTop = [...famSecs.entries()].sort((a, b) => b[1] - a[1]);
  const covered = famTop.filter(([, d]) => d / chordSecs >= 0.03).map(([k]) => k);
  // Capo scores 0..7, lower capo preferred within 0.03
  const scores = [0, 1, 2, 3, 4, 5, 6, 7].map(cp => +shapeScore(events, cp).toFixed(3));
  const best = Math.max(...scores);
  const capo = scores.findIndex(s => s >= best - 0.03);
  // Beat grid
  const beats = rh.beat_times_seconds, ivs = beats.slice(1).map((b, i) => b - beats[i]);
  const medIv = median(ivs), impliedBpm = 60 / medIv;
  const cv = Math.sqrt(ivs.reduce((s, x) => s + (x - medIv) ** 2, 0) / ivs.length) / medIv;
  const lo = cfg.tempo_min_bpm, hi = cfg.tempo_max_bpm;
  // chord starts near a beat (within 15% of the interval)
  let near = 0, considered = 0;
  for (const e of events.slice(1)) {
    if (e.label === "N" || e.start_seconds <= beats[0] || e.start_seconds >= beats[beats.length - 1]) continue;
    const p = app.beatPosition(beats, e.start_seconds), frac = Math.abs(p - Math.round(p));
    considered++; if (frac <= 0.15) near++;
  }
  const holds = events.filter(e => e.label !== "N" && e.label !== "X").map(e => app.estimatedSpan(rh, e.start_seconds, e.end_seconds)).filter(Boolean).map(s => s.beats);
  const expSet = expected[c.id]?.sounding;
  let expCover = null, missing = null, extra = null;
  if (expSet) {
    const want = new Set(expSet.map(x => { const f = family(x); return f ? f.text : x; }));
    expCover = +([...bySecs].filter(([l]) => { const f = family(l); return f && want.has(f.text); }).reduce((s, [, d]) => s + d, 0) / chordSecs).toFixed(3);
    const have = new Set(covered);
    missing = [...want].filter(w => !have.has(w));
    extra = covered.filter(h => !want.has(h));
  }
  report.push({
    id: c.id, video_id: c.source.source.video_id, uploader: c.source.source.uploader, duration_seconds: +dur.toFixed(2),
    chord_events: events.length, distinct_labels: bySecs.size, distinct_core_families: famSecs.size,
    nx_share: +(nx / dur).toFixed(3), top_labels: top.slice(0, 8).map(([l, d]) => `${l} ${(100 * d / chordSecs).toFixed(0)}%`),
    core_families_ge3pct: covered, expected_cover: expCover, expected_missing: missing, unexpected_ge3pct: extra,
    capo_scores: scores, capo_suggested: capo, capo_best_score: best,
    pulse_bpm: +rh.pulse_bpm.toFixed(2), implied_bpm: +impliedBpm.toFixed(2), beat_interval_cv: +cv.toFixed(3),
    config: { start: cfg.start_bpm, min: lo, max: hi, bpb: cfg.beats_per_bar }, in_range: rh.pulse_bpm >= lo && rh.pulse_bpm <= hi,
    ratio_to_start: +(rh.pulse_bpm / cfg.start_bpm).toFixed(2),
    beats: beats.length, first_beat: +beats[0].toFixed(2), tail_without_beats_s: +(dur - beats[beats.length - 1]).toFixed(2),
    chord_starts_near_beat: considered ? +(near / considered).toFixed(2) : null, median_hold_beats: holds.length ? +median(holds).toFixed(2) : null,
    first_chords: events.slice(0, 14).map(e => `${e.label}@${e.start_seconds.toFixed(1)}`).join(" ")
  });
}
if (AS_JSON) console.log(JSON.stringify(report, null, 1));
else for (const r of report) {
  console.log(`\n== ${r.id}  [${r.video_id} · ${r.uploader} · ${r.duration_seconds}s]`);
  console.log(`  chords: ${r.chord_events} events, ${r.distinct_labels} labels, ${r.distinct_core_families} core families; N/X ${(100 * r.nx_share).toFixed(0)}%`);
  console.log(`  top: ${r.top_labels.join(", ")}`);
  console.log(`  core families >=3%: ${r.core_families_ge3pct.join(" ")}${r.expected_cover === null ? "" : `   | expected-set cover ${(100 * r.expected_cover).toFixed(0)}% missing[${r.expected_missing}] unexpected[${r.unexpected_ge3pct}]`}`);
  console.log(`  capo scores 0-7: ${r.capo_scores.join(" ")} -> suggest ${r.capo_suggested}`);
  console.log(`  pulse ${r.pulse_bpm} bpm (implied ${r.implied_bpm}, cv ${r.beat_interval_cv}); config start ${r.config.start} range ${r.config.min}-${r.config.max} bpb ${r.config.bpb}; in range: ${r.in_range}; ratio to start ${r.ratio_to_start}`);
  console.log(`  beats ${r.beats} (first ${r.first_beat}s, tail gap ${r.tail_without_beats_s}s); chord starts near beat ${r.chord_starts_near_beat}; median hold ${r.median_hold_beats} beats`);
  console.log(`  start: ${r.first_chords}`);
}
