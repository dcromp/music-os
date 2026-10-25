#!/usr/bin/env node
"use strict";
// Strum Along song exporter: repo packs -> strumalong/songs/index.json + strumalong/songs/<id>.json.
//
// Which recordings ship is decided only by strumalong/data/catalogue.json (packs to read, exclusions with reasons,
// level overrides). Read-only on every repo input (frozen packs, experiments/review/*.json, additions metadata).
// Only writes strumalong/songs/. Reuses the Mac player's own pure helpers (experiments/review/app.js) so chart
// validation, display corrections, beat-grid pairing and Core/capo label maths are the same code the reviewed
// player uses, and lib/core.js for the timeline the app itself draws.
//
//   node strumalong/tools/build-songs.js           # build (re-runnable, deterministic) and print the bar/level report
//   node strumalong/tools/build-songs.js --check   # build in memory and fail if songs/ on disk differs
//
// Spec: docs/STRUMALONG_APP.md (Catalogue config, Data schema, Bar model, Difficulty levels). No lyrics anywhere.

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT = path.resolve(__dirname, "..");            // strumalong/
const REPO = path.resolve(ROOT, "..");                 // repo root
// STRUMALONG_* overrides exist only so the exporter can be exercised against fixtures without touching the real outputs.
const SONGS_DIR = process.env.STRUMALONG_SONGS_DIR || path.join(ROOT, "songs");
const CATALOGUE = process.env.STRUMALONG_CATALOGUE || path.join(ROOT, "data/catalogue.json");
const REVIEW = path.join(REPO, "experiments/review");
const app = require(path.join(REVIEW, "app.js"));
const Core = require(path.join(ROOT, "lib/core.js"));

const CHECK = process.argv.includes("--check");
const warnings = [];
const warn = msg => { warnings.push(msg); console.warn("WARN  " + msg); };

const read = p => fs.readFileSync(p);
const sha = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const r3 = x => Math.round(x * 1000) / 1000;
const r2 = x => Math.round(x * 100) / 100;
const r1 = x => Math.round(x * 10) / 10;
const isNum = x => typeof x === "number" && Number.isFinite(x);
const isStr = x => typeof x === "string" && x.trim().length > 0;
const mod = (value, n) => ((value % n) + n) % n;
const repoPath = p => path.resolve(REPO, p);
const rel = p => path.relative(REPO, p);

// ---------------------------------------------------------------- difficulty vocabulary (lead decision, 25 Oct 2026)

// Shape tiers are what the player frets: Core shapes at the song's default view (capo shapes, Simple quality).
const TIER_SHAPES = {
  1: ["A", "D", "E", "Em", "Am", "A7", "D7", "E7", "Am7", "Em7", "Asus2", "Asus4", "Dsus2", "Dsus4", "Esus4", "D6add9/F#"],
  2: ["G", "C", "Dm", "G7", "C7", "B7", "Cadd9", "Cmaj7", "Fmaj7", "Dm7", "G/B", "D/F#", "C/G"],
  3: ["F", "Bm", "Bm7", "F#m"],
};
const TIER_OF = new Map(Object.entries(TIER_SHAPES).flatMap(([tier, shapes]) => shapes.map(s => [s, Number(tier)])));
const TIER_NAMES = { 1: "first-chord shape", 2: "open chord", 3: "first barre-type shape", 4: "barre shape" };

const LEVELS = [
  { level: 1, label: "First chords", note: "Up to three easy shapes from A, D, E, Em and Am." },
  { level: 2, label: "Open chords", note: "Open chords such as G and C, up to four shapes, at a relaxed pace." },
  { level: 3, label: "More changes", note: "Open chords with more shapes, quicker changes or a syncopated strum." },
  { level: 4, label: "First barre (F / Bm)", note: "Adds a first barre-type shape: F, Bm or F#m." },
  { level: 5, label: "Barre chords", note: "Full barre shapes such as B, Bb, Cm or C#m." },
];
const LEVEL = new Map(LEVELS.map(l => [l.level, l]));
const levelTitle = n => `Level ${n} · ${LEVEL.get(n).label}`;
const MAIN_SHAPE_SHARE = 0.04;   // main shapes cover at least 4% of chord time
const BLIP_BEATS = 0.75;         // holds shorter than this are blips (the app's "quick" threshold)
const QUICK_CPM = 40, QUICK_MEDIAN_BEATS = 2, QUICK_MEDIAN_BPM = 120;

// Default practice patterns for songs without authored patterns (4 beats per bar). Prepared and authored songs keep theirs.
const P = {
  steady: { id: "steady-down", name: "Start: steady downstrokes", counts: ["1", "2", "3", "4"], strokes: ["D", "D", "D", "D"],
    description: "Strum down on each count. Keep the motion steady and change shape when the chord cue changes." },
  eighths: (prefix) => ({ id: "down-up", name: `${prefix}: down-up eighths`, counts: ["1", "&", "2", "&", "3", "&", "4", "&"],
    strokes: ["D", "U", "D", "U", "D", "U", "D", "U"],
    description: "Alternate down and up in steady eighth notes: down on the numbers, up on the \"&\". Keep the hand moving through chord changes." }),
  folk: (prefix) => ({ id: "folk-strum", name: `${prefix}: D — D U — U D U`, counts: ["1", "&", "2", "&", "3", "&", "4", "&"],
    strokes: ["D", "—", "D", "U", "—", "U", "D", "U"],
    description: "Keep the down-up pendulum going; miss the strings on the \"&\" of 1 and on 3. A common pop and rock strum." }),
  ring3: { id: "ring-3", name: "Next: let count 3 ring", counts: ["1", "&", "2", "&", "3", "&", "4", "&"],
    strokes: ["D", "U", "D", "U", "—", "U", "D", "U"],
    description: "Down-up eighths, but miss the strings on 3 and come back in with the up-strum after it." },
  anchor13: { id: "anchor-1-3", name: "Next: anchor beats 1 and 3", counts: ["1", "&", "2", "&", "3", "&", "4", "&"],
    strokes: ["D", "—", "D", "U", "D", "—", "D", "U"],
    description: "Down on every count with an up after 2 and 4. Fewer strokes keep the barre hand settled through changes." },
};
function defaultPatterns(level, bpb) {
  if (bpb !== 4) {
    const counts = n => Array.from({ length: n }, (_, i) => (i % 2 ? "&" : String(i / 2 + 1)));
    return [
      { ...P.steady, counts: Array.from({ length: bpb }, (_, i) => String(i + 1)), strokes: Array(bpb).fill("D") },
      { ...P.eighths("Next"), counts: counts(2 * bpb), strokes: Array.from({ length: 2 * bpb }, (_, i) => (i % 2 ? "U" : "D")) },
    ];
  }
  if (level <= 1) return [P.steady, P.eighths("Next")];
  if (level === 2) return [P.eighths("Start"), P.folk("Next")];
  if (level === 3) return [P.folk("Start"), P.ring3];
  return [P.folk("Start"), P.anchor13];
}
const pickPattern = p => ({ id: p.id, name: p.name, counts: [...p.counts], strokes: [...p.strokes], description: p.description });

// ---------------------------------------------------------------- catalogue config

const CAPO_SOURCES = ["catalogue", "suggested", "none"];

function readCatalogue(file = CATALOGUE) {
  const bytes = read(file), cfg = JSON.parse(bytes);
  const fail = msg => { throw new Error(`${rel(file)}: ${msg}`); };
  if (cfg.schema !== "strumalong-catalogue-config-1") fail(`unexpected schema ${JSON.stringify(cfg.schema)}`);
  if (!Array.isArray(cfg.packs) || !cfg.packs.length) fail("packs must be a non-empty array");
  const ids = new Set();
  for (const pack of cfg.packs) {
    if (!isStr(pack.id) || ids.has(pack.id)) fail(`pack id missing or duplicated (${JSON.stringify(pack.id)})`);
    ids.add(pack.id);
    if (!["prepared", "additions"].includes(pack.kind)) fail(`pack ${pack.id}: kind must be "prepared" or "additions"`);
    const needed = pack.kind === "prepared" ? ["dir", "rhythm", "practice", "learning"] : ["dir", "rhythm", "metadata"];
    for (const key of needed) if (!isStr(pack[key])) fail(`pack ${pack.id}: ${key} path missing`);
  }
  const exclude = new Map();
  for (const item of cfg.exclude || []) {
    if (!isStr(item.recording_id) || !isStr(item.reason)) fail("every exclude entry needs recording_id and reason");
    if (exclude.has(item.recording_id)) fail(`duplicate exclude ${item.recording_id}`);
    exclude.set(item.recording_id, item);
  }
  const overrides = new Map();
  for (const item of cfg.level_overrides || []) {
    if (!isStr(item.recording_id) || !isStr(item.reason) || !LEVEL.has(item.level)) fail("every level override needs recording_id, level 1-5 and reason");
    if (overrides.has(item.recording_id)) fail(`duplicate level override ${item.recording_id}`);
    if (exclude.has(item.recording_id)) fail(`${item.recording_id} is both excluded and overridden`);
    overrides.set(item.recording_id, item);
  }
  return { ...cfg, exclude, overrides, sha256: sha(bytes) };
}

// ---------------------------------------------------------------- helpers

function pairedRecording(a, b) {
  return a && b && a.id === b.id && a.audio_sha256 === b.audio_sha256 && a.sample_rate_hz === b.sample_rate_hz &&
    isNum(a.duration_seconds) && Math.abs(a.duration_seconds - b.duration_seconds) <= 0.000001;
}

// HEURISTIC (not a repo-reviewed measurement; downbeats are NOT verified): the song-wide bar phase is the beat-index
// residue (mod beats_per_bar) that the app draws for most chord changes. Every native chord start that is not N or X
// and lies strictly inside the beat grid casts one vote for mod(round(beatPosition(start)), bpb). Ties keep the lowest
// residue. Confidence needs at least 8 votes and a winning share of at least 0.7 (barPhaseConfident). Since the bar
// model (barAnchors) it is only the fallback for beats no chord owns, and a summary statistic.
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

// The holds the app draws in its default view (Core quality; merges are view-independent), with the same beat
// rounding as lib/core.js cuePart: dots run round(startBeat) .. round(endBeat) - 1, a span under 0.75 beat is quick.
function gridHolds(song) {
  return Core.buildTimeline(song).map(ev => {
    const sb = Core.gridPosition(song.beats, ev.s), eb = Core.gridPosition(song.beats, ev.e);
    const hold = { s: ev.s, e: ev.e, label: ev.label, inGrid: sb !== null && eb !== null && eb > sb };
    if (!hold.inGrid) return hold;
    hold.sb = sb; hold.eb = eb; hold.base = Math.round(sb); hold.span = eb - sb;
    hold.quick = hold.span < BLIP_BEATS;
    hold.count = hold.quick ? 1 : Math.max(1, Math.round(eb) - hold.base);
    return hold;
  });
}

// ---------------------------------------------------------------- bar model (docs/STRUMALONG_APP.md, "Bar model")

// Objective weights. A drawn bar line is "weird" when it falls 1 beat after a change or 1 beat before the next change
// inside a hold of 3+ beats; a short hold (2..beats_per_bar beats) is "split" when a bar line falls inside it.
// Changes on a bar line cost nothing, on the half-bar a little (more when a long hold starts there), elsewhere more.
// A phase switch (a local slip in the beat grid or the chart) costs SWITCH; hold-relative bars restart the strum
// count, so each restart that is not a whole number of bars after the previous one costs RESET, and every
// hold-relative hold costs HOLD so a steady phase wins whenever it draws the same bars.
const BAR_COST = { weird: 1, split: 1, off: 0.5, half: 0.1, halfLong: 0.5, switch: 1.75, switchHold: 2.5, reset: 0.8, hold: 0.1,
  minChanges: 8, minFit: 0.8 };
if (process.env.STRUMALONG_BAR_COST) Object.assign(BAR_COST, JSON.parse(process.env.STRUMALONG_BAR_COST)); // tuning only

function holdLines(hold, phase, bpb) {
  const lines = [];
  for (let k = 1; k < hold.count; k++) if (mod(hold.base + k - phase, bpb) === 0) lines.push(k);
  return lines;
}
function holdFlaws(hold, lines, bpb) {
  const weird = hold.count >= 3 ? lines.filter(k => k === 1 || k === hold.count - 1).length : 0;
  const split = hold.count >= 2 && hold.count <= bpb && lines.length > 0 ? 1 : 0;
  return { weird, split };
}

/**
 * Per-hold bar anchors for the default-view timeline. A Viterbi pass over the chord changes chooses, per change,
 * either one of the beats_per_bar phases or "hold-relative" (the change starts a bar), minimising BAR_COST. A run of
 * one phase is confident when it has at least 8 changes, at least 80% of them on a bar line or half-bar, at least as
 * many on the bar as on the half-bar, and the meter is not assumed. Hold-relative and unconfident runs are approx.
 * One run covering the song is the old global phase; several runs are local phases (grid or chart slips).
 * @returns {{holds, anchors: Array<{phase:number, approx:boolean, mode:'phase'|'hold'}|null>, runs}}
 */
function barAnchors(song, opts = {}) {
  const W = { ...BAR_COST, ...(opts.weights || {}) };
  const bpb = song.rhythm.beats_per_bar, assumed = Boolean(song.rhythm.beats_per_bar_assumed);
  const holds = gridHolds(song);
  const scored = holds.map((h, i) => i).filter(i => holds[i].inGrid && !holds[i].quick && holds[i].label !== "N");
  const HOLD = bpb; // state index for hold-relative
  const offCost = (hold, phase) => {
    if (hold.label === "X") return 0;
    const d = mod(hold.base - phase, bpb);
    return d === 0 ? 0 : bpb % 2 === 0 && d === bpb / 2 ? (hold.count >= bpb ? W.halfLong : W.half) : W.off;
  };
  const emit = (t, state) => {
    const hold = holds[scored[t]];
    if (state < bpb) {
      const f = holdFlaws(hold, holdLines(hold, state, bpb), bpb);
      return W.weird * f.weird + W.split * f.split + offCost(hold, state);
    }
    const f = holdFlaws(hold, holdLines(hold, mod(hold.base, bpb), bpb), bpb);
    const prev = t ? holds[scored[t - 1]] : null;
    return W.weird * f.weird + W.hold + (prev && prev.count % bpb !== 0 ? W.reset : 0);
  };
  const step = (a, b) => (a === b ? 0 : a === HOLD || b === HOLD ? W.switchHold : W.switch);

  let path = [];
  if (scored.length) {
    let cost = Array.from({ length: bpb + 1 }, (_, s) => emit(0, s));
    const back = [];
    for (let t = 1; t < scored.length; t++) {
      const next = [], from = [];
      for (let s = 0; s <= bpb; s++) {
        let best = Infinity, arg = 0;
        for (let q = 0; q <= bpb; q++) { const c = cost[q] + step(q, s); if (c < best - 1e-9) { best = c; arg = q; } }
        next.push(best + emit(t, s)); from.push(arg);
      }
      cost = next; back.push(from);
    }
    let s = 0;
    for (let q = 1; q <= bpb; q++) if (cost[q] < cost[s] - 1e-9) s = q;
    path = [s];
    for (let t = scored.length - 2; t >= 0; t--) { s = back[t][s]; path.unshift(s); }
  }

  const runs = [];
  for (let t = 0, from = 0; t <= path.length; t++) {
    if (t < path.length && path[t] === path[from]) continue;
    if (t > from) runs.push({ from, to: t, state: path[from] });
    from = t;
  }
  for (const run of runs) {
    let on = 0, half = 0, changes = 0;
    for (let t = run.from; t < run.to; t++) {
      const hold = holds[scored[t]];
      if (hold.label === "X") continue;
      changes++;
      const d = run.state === HOLD ? 0 : mod(hold.base - run.state, bpb);
      if (d === 0) on++; else if (bpb % 2 === 0 && d === bpb / 2) half++;
    }
    run.mode = run.state === HOLD ? "hold" : "phase";
    run.changes = changes;
    run.confident = run.mode === "phase" && !assumed && changes >= W.minChanges && (on + half) >= W.minFit * changes && on >= half;
  }

  // Every in-grid hold takes the run of the latest scored hold at or before it (else the first run). Hold-relative
  // holds start their own bar; a quick hold in a hold-relative run takes the next hold's anchor (it is a pickup).
  const anchors = holds.map(() => null);
  const runAt = new Array(holds.length).fill(null);
  for (let i = 0, t = -1; i < holds.length; i++) {
    while (t + 1 < scored.length && scored[t + 1] <= i) t++;
    runAt[i] = runs.length ? runs.find(r => Math.max(t, 0) >= r.from && Math.max(t, 0) < r.to) : null;
  }
  for (let i = holds.length - 1; i >= 0; i--) {
    const hold = holds[i], run = runAt[i];
    if (!hold.inGrid) continue;
    if (!run) { anchors[i] = { phase: song.rhythm.bar_phase, approx: !song.rhythm.bar_phase_confident, mode: "global" }; continue; }
    if (run.mode === "phase") { anchors[i] = { phase: run.state, approx: !run.confident, mode: "phase" }; continue; }
    const nextAnchor = anchors.slice(i + 1).find(Boolean);
    anchors[i] = hold.quick && nextAnchor ? { ...nextAnchor } : { phase: mod(hold.base, bpb), approx: true, mode: "hold" };
  }
  return { holds, anchors, runs };
}

// Write the anchors onto the native chords: b = bar phase, a = 1 when approximate. Natives inside one merged hold
// share its anchor, so Full view (no merges) draws the same bars as Simple view.
function applyBarAnchors(song) {
  const { holds, anchors, runs } = barAnchors(song);
  let h = 0;
  // New chord objects (a new array): lib/core.js caches its per-beat anchor map by chord-array identity.
  song.chords = song.chords.map(native => {
    const chord = { s: native.s, e: native.e, l: native.l, ...(native.c ? { c: native.c } : {}) };
    while (h < holds.length && holds[h].e <= chord.s + 1e-6) h++;
    const hold = holds[h];
    if (!hold || !(hold.s <= chord.s + 1e-6 && chord.e <= hold.e + 1e-6) || !anchors[h]) return chord;
    chord.b = anchors[h].phase;
    if (anchors[h].approx) chord.a = 1;
    return chord;
  });
  return { runs, holds, anchors };
}

// The bar objective, measured on what lib/core.js draws (per-beat anchors via Core.barAnchorAt).
//   changes: chord holds (not N, not quick) in the grid; on_bar / on_bar_or_half: % of them whose first beat is a bar
//   start / a bar start or half-bar; weird and split as in BAR_COST; restarts: bar starts that are not a whole bar
//   after the previous one (the strum count restarts early); approx_pct: % of chord beats under approximate anchors.
function barMetrics(song) {
  const bpb = song.rhythm.beats_per_bar;
  const holds = gridHolds(song);
  const at = beat => Core.barAnchorAt(song, beat);
  let changes = 0, onBar = 0, onHalf = 0, weird = 0, split = 0, lines = 0, chordBeats = 0, approxBeats = 0;
  for (const hold of holds) {
    if (!hold.inGrid || hold.label === "N") continue;
    if (!hold.quick) {
      changes++;
      const a = at(hold.base);
      if (a.bar) onBar++; else if (a.half) onHalf++;
    }
    const drawn = [];
    for (let k = 1; k < hold.count; k++) if (at(hold.base + k).bar) drawn.push(k);
    lines += drawn.length;
    const f = holdFlaws(hold, drawn, bpb);
    weird += f.weird; split += f.split;
    for (let k = 0; k < hold.count; k++) { chordBeats++; if (at(hold.base + k).approx) approxBeats++; }
  }
  let restarts = 0, previous = null;
  for (let beat = 0; beat < song.beats.length; beat++) {
    if (!at(beat).bar) continue;
    if (previous !== null && beat - previous !== bpb) restarts++;
    previous = beat;
  }
  const pct = (a, b) => (b ? r1(100 * a / b) : 0);
  return { changes, on_bar: pct(onBar, changes), on_bar_or_half: pct(onBar + onHalf, changes), weird, split, lines, restarts,
    approx_pct: pct(approxBeats, chordBeats) };
}

// ---------------------------------------------------------------- difficulty (docs/STRUMALONG_APP.md, "Difficulty levels")

function shapeTier(shape) {
  if (TIER_OF.has(shape)) return TIER_OF.get(shape);
  const slash = /^([^/]+)\/.+$/.exec(shape);  // other slash shapes are fretted as their root shape (bass note omitted)
  if (slash && TIER_OF.has(slash[1])) return TIER_OF.get(slash[1]);
  return 4;
}

function median(values) {
  const v = [...values].sort((a, b) => a - b), n = v.length;
  return n ? (n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2) : 0;
}

/**
 * Difficulty at the song's default view (capo shapes, Simple). Main shapes: Core shapes covering >= 4% of chord time,
 * ignoring N, X and blips (< 0.75 beat). Changes: label changes between consecutive non-blip chord holds (not across
 * N or X), per minute of non-blip chord time. Median hold: beats per non-blip chord hold.
 *   L5 any tier-4 main shape; L4 any tier-3; else L1 when all tier 1 and <= 3 shapes, L2 when <= 4 shapes (any
 *   number if all tier 1), L3 when 5+ shapes; and L1/L2 move to L3 on quick changes (median hold <= 2 beats at
 *   >= 120 BPM, or >= 40 changes/min) or an authored needs_syncopation flag.
 */
function difficultyOf(song, opts = {}) {
  const bpm = song.rhythm.bpm;
  const seconds = new Map(), holdBeats = [];
  let changes = 0, chordSeconds = 0, previous = null;
  for (const hold of gridHolds(song)) {
    if (hold.label === "N" || hold.label === "X") { previous = null; continue; }
    const span = hold.inGrid ? hold.span : (hold.e - hold.s) * bpm / 60;
    if (span < BLIP_BEATS) continue;
    const beats = hold.inGrid ? hold.count : Math.max(1, Math.round(span));
    const held = hold.e - hold.s;
    seconds.set(hold.label, (seconds.get(hold.label) || 0) + held);
    chordSeconds += held;
    holdBeats.push(beats);
    if (previous !== null && previous !== hold.label) changes++;
    previous = hold.label;
  }
  const main = [...seconds].map(([shape, held], order) => ({ shape, share: held / chordSeconds, order, tier: shapeTier(shape) }))
    .filter(x => x.share >= MAIN_SHAPE_SHARE)
    .sort((a, b) => b.share - a.share || a.order - b.order);
  const cpm = chordSeconds > 0 ? changes / (chordSeconds / 60) : 0;
  const medianHold = median(holdBeats);
  const hardest = main.reduce((best, x) => (!best || x.tier > best.tier ? x : best), null);
  const maxTier = hardest ? hardest.tier : 1;
  const names = main.map(x => x.shape).join(", ");
  const bumps = [];
  if (cpm >= QUICK_CPM) bumps.push(`${r1(cpm)} changes a minute (${QUICK_CPM}+)`);
  if (medianHold <= QUICK_MEDIAN_BEATS && bpm >= QUICK_MEDIAN_BPM) bumps.push(`median hold ${medianHold} beats at ~${Math.round(bpm)} BPM`);
  if (opts.needsSyncopation) bumps.push("a syncopated strum is needed");
  let level, reason;
  if (maxTier === 4) { level = 5; reason = `${hardest.shape} is a barre shape (tier 4); main shapes ${names}.`; }
  else if (maxTier === 3) { level = 4; reason = `${hardest.shape} is a first barre-type shape (tier 3); main shapes ${names}.`; }
  else {
    level = maxTier === 1 ? (main.length <= 3 ? 1 : 2) : main.length <= 4 ? 2 : 3;
    reason = maxTier === 1 ? `${names}: all first-chord shapes (tier 1), ${main.length} main shapes.`
      : `${names}: open chords (hardest ${hardest.shape}, tier 2), ${main.length} main shapes.`;
    if (bumps.length && level < 3) level = 3;
  }
  // The pace part: quick-change evidence when present, otherwise the plain change rate.
  reason += bumps.length ? ` Quicker: ${bumps.join("; ")}.` : ` About ${r1(cpm)} changes a minute.`;
  return { level, label: LEVEL.get(level).label, main_shapes: main.map(x => x.shape), hardest_shape: hardest ? hardest.shape : null,
    tier_reason: reason, changes_per_min: r1(cpm), median_hold_beats: medianHold };
}

function applyLevelOverride(difficulty, override) {
  if (!override) return difficulty;
  return { ...difficulty, level: override.level, label: LEVEL.get(override.level).label, computed_level: difficulty.level,
    override_reason: override.reason };
}

// ---------------------------------------------------------------- alternates

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

// additions metadata "alternates" (merge by video_id). Accepted shapes:
//   { "<recording_id>": [ {video_id, offset_seconds, timing_checked, ...}, ... ] }
//   { "<recording_id>": { video_id, ... } }            { "<recording_id>": { "<video_id>": {...} } }
//   { "<video_id>": { offset_seconds, ... } }
// A new alternate needs video_id, uploader and duration_seconds.
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
 * @param ctx { c, packId, packDir, hashes, rhythmCase, correctionSet, meta, alternateMeta }
 *   meta: { title, artist, capo, capo_source, setup_note, strumming|null, learning, needs_syncopation?, playable_embed?, embed_note? }
 *   strumming null means "no authored patterns": the level's default patterns are filled in by finishSong.
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
  // Optional per-song label aliases from additions metadata: a chart label the detector names differently from the
  // grip players use (e.g. A Horse with No Name's F#m7 is played as D6add9/F#). Applied to whole events; c:1 marks them.
  const aliases = (meta && meta.label_aliases) || null;
  const aliasCounts = {};
  const chords = display.map(e => {
    const out = { s: r3(e.start_seconds), e: r3(e.end_seconds), l: e.label };
    if (e.display_correction) out.c = 1;
    if (aliases && Object.prototype.hasOwnProperty.call(aliases.map, e.label)) {
      const seen = aliasCounts[e.label] || { count: 0, start: out.s, end: out.e };
      aliasCounts[e.label] = { count: seen.count + 1, start: Math.min(seen.start, out.s), end: Math.max(seen.end, out.e) };
      out.l = aliases.map[e.label]; out.c = 1;
    }
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
  for (const [from, { count, start, end }] of Object.entries(aliasCounts)) {
    corrections.push({ id: `alias-${from}`, start, end, from, to: aliases.map[from],
      note: `${aliases.note} (${count} chart event${count === 1 ? "" : "s"} between these times; label alias, timings unchanged)` });
  }

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
  const embedBlocked = meta.playable_embed === false;
  const src = c.source.source;
  const analysed = { video_id: src.video_id, uploader: src.uploader, kind: "analysed", duration_seconds: src.duration_seconds,
    offset_seconds: 0, timing_checked: true, note: "Chart computed from this upload's audio.", ...(embedBlocked ? { embeddable: false } : {}) };
  const alternates = applyAlternateOverrides(ctx.alternateMeta, c.id, []);
  if (embedBlocked && !alternates.some(a => a.embeddable !== false)) throw new Error(`${c.id}: playable_embed false needs an embeddable alternate video`);
  const videos = [analysed, ...alternates].map(videoEntry);

  const recording = { id: c.recording.id, duration_seconds: r3(c.recording.duration_seconds), audio_sha256: c.recording.audio_sha256 };
  const song = {
    schema: "strumalong-song-2",
    id: c.id, title: meta.title, artist: meta.artist, group: null, order: null, level: null,
    recording, videos,
    chart: { source: c.primary_name || "CREMA automatic draft", sha256: primarySha, status: "provisional", corrections },
    capo: meta.capo, capo_source: meta.capo_source,
    setup_note: meta.setup_note,
    difficulty: null,
    rhythm, beats, chords,
    strumming: meta.strumming,
    learning: meta.learning,
    provenance: { pack: packId, manifest_sha256: hashes.manifest, rhythm_sha256: hashes.rhythm, practice_sha256: hashes.practice,
      learning_sha256: hashes.learning, ...(hashes.additions ? { additions_sha256: hashes.additions } : {}), catalogue_sha256: hashes.catalogue },
  };

  // bar anchors on the chords, then the bar summary the details panel reads
  const before = barMetrics(song);
  const bars = applyBarAnchors(song);
  const after = barMetrics(song);
  rhythm.bar_model = "anchored-1";
  rhythm.bar_confident_pct = r1(100 - after.approx_pct);
  const difficulty = difficultyOf(song, { needsSyncopation: meta.needs_syncopation === true });

  const alt = alternates.find(a => a.timing_checked) || alternates[0];
  const card = {
    id: c.id, title: meta.title, artist: meta.artist, group: null, order: null, level: null, level_label: null,
    video_id: analysed.video_id, duration_seconds: r2(c.recording.duration_seconds),
    bpm: Math.round(rhythmCase.pulse_bpm), meter_label: rhythmCase.meter_label, capo: meta.capo,
    core_shapes: coreShapes(chords, meta.capo),
    playable_embed: !embedBlocked,
    embed_note: !embedBlocked ? "" : (meta.embed_note ||
      (alt && alt.timing_checked ? "This upload can't play in the app; using the official video (start offset measured)."
        : "This upload can't play in the app; using the official video with unchecked timing.")),
  };
  return { song, card, difficulty, packId, stats: { chords: chords.length, beats: beats.length, vote, confident, before, after, runs: bars.runs } };
}

// Level (with any override), default patterns for unauthored songs, and the grouping fields.
function finishSong(built, override) {
  const { song, card } = built;
  const difficulty = applyLevelOverride(built.difficulty, override);
  song.difficulty = difficulty;
  song.level = card.level = difficulty.level;
  card.level_label = difficulty.label;
  song.group = card.group = `level-${difficulty.level}`;
  if (!song.strumming) {
    song.strumming = { note: `Default practice patterns for Level ${difficulty.level} songs; not checked against the recording.`,
      source: "level-default", patterns: defaultPatterns(difficulty.level, song.rhythm.beats_per_bar).map(pickPattern) };
  } else song.strumming.source = song.strumming.source || "authored";
  for (const p of song.strumming.patterns) {
    if (p.counts.length !== p.strokes.length || p.counts.length % song.rhythm.beats_per_bar !== 0) {
      throw new Error(`${song.id}: pattern ${p.id} does not fit ${song.rhythm.beats_per_bar} beats per bar`);
    }
  }
  return built;
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

// ---------------------------------------------------------------- prepared pack (automatic-first-ten-v1)

// Clean human titles for the prepared recordings (manifest titles carry "Artist - " prefixes and remaster tags).
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

function loadPrepared(pack, cfg, built) {
  const dir = repoPath(pack.dir);
  const manifestBytes = read(path.join(dir, "manifest.json")), manifest = JSON.parse(manifestBytes);
  const rhythmBytes = read(repoPath(pack.rhythm)), rhythm = JSON.parse(rhythmBytes);
  const practiceBytes = read(repoPath(pack.practice)), practice = JSON.parse(practiceBytes);
  const learningBytes = read(repoPath(pack.learning)), learning = JSON.parse(learningBytes);
  const hashes = { manifest: sha(manifestBytes), rhythm: sha(rhythmBytes), practice: sha(practiceBytes), learning: sha(learningBytes), catalogue: cfg.sha256 };
  if (rhythm.manifest_sha256 && rhythm.manifest_sha256 !== hashes.manifest) throw new Error(`${pack.rhythm} is pinned to a different manifest.json`);
  if (manifest.pack_id !== pack.id) warn(`${pack.id}: manifest pack_id is ${JSON.stringify(manifest.pack_id)}`);

  const rhythmById = app.validateRhythmManifest(rhythm, manifest.cases);
  const practiceById = new Map(practice.cases.map(p => [p.recording.id, p]));
  const learnById = new Map([...learning.steps, ...learning.guides].map(s => [s.recording.id, s]));

  for (const c of manifest.cases) {
    if (cfg.exclude.has(c.id)) continue;
    const titles = TITLES[c.id];
    if (!titles) throw new Error(`no clean title for ${c.id}; add it to TITLES`);
    const prac = practiceById.get(c.id), entry = learnById.get(c.id) || null;
    if (!prac) throw new Error(`no practice case for ${c.id}`);
    for (const paired of [prac, entry]) if (paired && !pairedRecording(paired.recording, c.recording)) throw new Error(`recording identity mismatch for ${c.id}`);
    const capo = c.practice && Number.isInteger(c.practice.capo) ? c.practice.capo : 0;
    built.push(buildSong({
      c, packId: manifest.pack_id, packDir: dir, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: prac.display_corrections,
      alternateMeta: null,
      meta: { title: titles[0], artist: titles[1], capo, capo_source: capo > 0 ? "catalogue" : "none",
        setup_note: entry ? entry.setup_note : "Standard tuning (EADGBE). Capo and exact recording pitch are unchecked.",
        strumming: { note: prac.note, beats_description: prac.beats_description, source: "authored",
          patterns: prac.patterns.map(p => ({ id: p.id, name: p.name, counts: p.counts, strokes: p.strokes, description: p.description })) },
        learning: entry ? { skill_focus: entry.skill_focus, prerequisites: entry.prerequisites, sources: entry.sources.map(s => ({ title: s.title, url: s.url })) }
          : { skill_focus: "", prerequisites: "", sources: [] } },
    }));
  }
}

// ---------------------------------------------------------------- additions packs

function readAdditionsMeta(file) {
  if (!fs.existsSync(file)) return null;
  try {
    const bytes = read(file), meta = JSON.parse(bytes);
    if (meta.schema !== "strumalong-additions-1") { warn(`${rel(file)}: unexpected schema ${JSON.stringify(meta.schema)}; ignored`); return null; }
    if (!Array.isArray(meta.songs)) { warn(`${rel(file)}: songs must be an array; ignored`); return null; }
    meta.__sha = sha(bytes);
    return meta;
  } catch (error) { warn(`${rel(file)} unreadable (${error.message}); ignored`); return null; }
}

const STROKES = new Set(["D", "U", "—"]);
function validPattern(p) {
  return p && isStr(p.id) && isStr(p.name) && isStr(p.description) && Array.isArray(p.counts) && Array.isArray(p.strokes) &&
    p.counts.length > 0 && p.counts.length === p.strokes.length && p.counts.every(isStr) && p.strokes.every(s => STROKES.has(s));
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
  // Patterns are optional (the level's defaults are used); when given they must all be well formed.
  if (patterns !== undefined && (!Array.isArray(patterns) || !patterns.every(validPattern))) problems.push("strumming.patterns");
  if (entry.needs_syncopation !== undefined && typeof entry.needs_syncopation !== "boolean") problems.push("needs_syncopation");
  if (entry.label_aliases !== undefined && !(entry.label_aliases && typeof entry.label_aliases.map === "object" && isStr(entry.label_aliases.note) &&
    Object.values(entry.label_aliases.map).every(isStr))) problems.push("label_aliases");
  return problems;
}

function loadAdditions(pack, cfg, built) {
  const dir = repoPath(pack.dir), metaPath = repoPath(pack.metadata), rhythmPath = repoPath(pack.rhythm);
  const manifestPath = path.join(dir, "manifest.json");
  const skip = why => { if (pack.required) throw new Error(`${pack.id}: ${why}`); console.log(`${pack.id}: ${why}; skipped`); };
  if (!fs.existsSync(manifestPath)) return skip(`${rel(manifestPath)} not found`);
  if (!fs.existsSync(rhythmPath)) return skip(`${rel(rhythmPath)} not found`);
  const meta = readAdditionsMeta(metaPath);
  if (!meta) return skip(`${rel(metaPath)} missing or unusable`);

  let manifest, manifestBytes, rhythmBytes, rhythmById;
  try {
    manifestBytes = read(manifestPath); manifest = JSON.parse(manifestBytes);
    rhythmBytes = read(rhythmPath);
    const rhythm = JSON.parse(rhythmBytes);
    if (rhythm.manifest_sha256 && rhythm.manifest_sha256 !== sha(manifestBytes)) throw new Error("rhythm.json is pinned to a different manifest.json");
    rhythmById = app.validateRhythmManifest(rhythm, manifest.cases);
  } catch (error) { if (pack.required) throw error; return warn(`${pack.id}: pack unusable (${error.message}); skipped`); }
  const packId = manifest.pack_id || pack.id;
  if (packId !== pack.id) warn(`${pack.id}: manifest pack_id is ${JSON.stringify(manifest.pack_id)}`);

  const hashes = { manifest: sha(manifestBytes), rhythm: sha(rhythmBytes), practice: meta.__sha, learning: meta.__sha, additions: meta.__sha, catalogue: cfg.sha256 };
  const caseById = new Map(manifest.cases.map(c => [c.id, c]));
  for (const c of manifest.cases) {
    if (!cfg.exclude.has(c.id) && !meta.songs.some(e => e.recording_id === c.id)) warn(`${pack.id}: manifest case ${c.id} has no metadata entry; skipped`);
  }
  for (const entry of meta.songs) {
    if (cfg.exclude.has(entry.recording_id)) continue;
    const c = caseById.get(entry.recording_id);
    if (!c) { warn(`${pack.id}: ${entry.recording_id} has metadata but is not in the manifest; skipped`); continue; }
    const problems = validateAdditionsEntry(entry);
    if (problems.length) { warn(`${pack.id}: ${c.id} has invalid metadata (${problems.join(", ")}); skipped`); continue; }
    try {
      const authored = entry.strumming && Array.isArray(entry.strumming.patterns) && entry.strumming.patterns.length;
      const strumming = authored ? {
        note: entry.strumming.note || "A starting rhythm exercise. The recording may use a different pattern.",
        ...(entry.strumming.beats_description ? { beats_description: entry.strumming.beats_description } : {}), source: "authored",
        patterns: entry.strumming.patterns.map(p => ({ id: p.id, name: p.name, counts: p.counts, strokes: p.strokes, description: p.description })),
      } : null;
      built.push(buildSong({
        c, packId, packDir: dir, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: undefined, alternateMeta: meta,
        meta: { title: entry.title, artist: entry.artist,
          // "suggested" with capo 0 means no capo is suggested: the song contract is capo_source "none" exactly at capo 0.
          capo: entry.capo, capo_source: entry.capo > 0 ? entry.capo_source : "none", setup_note: entry.setup_note, strumming,
          needs_syncopation: entry.needs_syncopation === true, playable_embed: entry.playable_embed, embed_note: entry.embed_note,
          label_aliases: entry.label_aliases || null,
          learning: { skill_focus: entry.skill_focus || "", prerequisites: entry.prerequisites || "",
            sources: (entry.sources || []).map(s => ({ title: s.title, url: s.url })) } },
      }));
    } catch (error) { warn(`${pack.id}: ${c.id} skipped (${error.message})`); }
  }
}

// ---------------------------------------------------------------- catalogue

// Within a level: fewest changes per minute first, then slower tempo, then title.
function compareWithinLevel(a, b) {
  return a.difficulty.changes_per_min - b.difficulty.changes_per_min || a.song.rhythm.bpm - b.song.rhythm.bpm ||
    a.song.title.localeCompare(b.song.title) || (a.song.id < b.song.id ? -1 : 1);
}

function buildCatalogue(cfg) {
  const built = [];
  for (const pack of cfg.packs) (pack.kind === "prepared" ? loadPrepared : loadAdditions)(pack, cfg, built);
  const ids = new Set();
  for (const b of built) { if (ids.has(b.song.id)) throw new Error(`duplicate song id ${b.song.id}`); ids.add(b.song.id); }
  for (const id of cfg.overrides.keys()) if (!ids.has(id)) warn(`level override for ${id}, which is not in the catalogue`);
  for (const b of built) finishSong(b, cfg.overrides.get(b.song.id));
  const ordered = [];
  for (const { level } of LEVELS) {
    const members = built.filter(b => b.song.level === level).sort((x, y) => compareWithinLevel(
      { difficulty: x.song.difficulty, song: x.song }, { difficulty: y.song.difficulty, song: y.song }));
    members.forEach((b, i) => { b.song.order = b.card.order = i + 1; ordered.push(b); });
  }
  const used = new Set(ordered.map(b => b.song.level));
  const index = { schema: "strumalong-catalogue-2",
    groups: LEVELS.filter(l => used.has(l.level)).map(l => ({ id: `level-${l.level}`, level: l.level, title: levelTitle(l.level), note: l.note })),
    songs: ordered.map(b => b.card) };
  return { built: ordered, index };
}

// ---------------------------------------------------------------- output

function report(built) {
  const pad = (v, n) => String(v).padStart(n);
  console.log("\nBar model (before = one song-wide bar_phase; after = anchored bars). weird/split counts, % of changes on bar or half-bar:");
  console.log(`${"song".padEnd(40)} ${"on bar+half".padStart(12)} ${"weird".padStart(8)} ${"split".padStart(9)} ${"restarts".padStart(9)} ${"approx%".padStart(10)}  runs`);
  for (const { song, stats: s } of built) {
    const b = s.before, a = s.after;
    console.log(`${song.title.slice(0, 40).padEnd(40)} ${pad(`${b.on_bar_or_half}→${a.on_bar_or_half}`, 12)} ${pad(`${b.weird}→${a.weird}`, 8)} ` +
      `${pad(`${b.split}→${a.split}`, 9)} ${pad(`${b.restarts}→${a.restarts}`, 9)} ${pad(`${b.approx_pct}→${a.approx_pct}`, 10)}  ` +
      s.runs.map(r => `${r.mode === "hold" ? "H" : r.state}${r.confident ? "" : "?"}×${r.to - r.from}`).join(" "));
  }
  console.log("\nLevels:");
  for (const { song } of built) {
    const d = song.difficulty;
    console.log(`L${d.level}${d.computed_level ? ` (computed L${d.computed_level})` : ""} #${song.order} ${song.title} · ${d.main_shapes.join(" ")} · ` +
      `${d.changes_per_min}/min · median ${d.median_hold_beats} beats · ~${Math.round(song.rhythm.bpm)} BPM · ${d.tier_reason}`);
  }
}

function main() {
  const cfg = readCatalogue();
  const { built, index } = buildCatalogue(cfg);
  const outputs = new Map();
  for (const b of built) outputs.set(b.song.id + ".json", serializeSong(b.song));
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

  for (const { song, stats: s } of built) {
    const bytes = Buffer.byteLength(outputs.get(song.id + ".json"));
    console.log(`${song.id.slice(0, 44).padEnd(44)} L${song.level}#${song.order} chords=${String(s.chords).padStart(3)} beats=${String(s.beats).padStart(3)} ` +
      `bpm=${String(song.rhythm.bpm).padEnd(5)} bpb=${song.rhythm.beats_per_bar}${song.rhythm.beats_per_bar_assumed ? "(assumed)" : ""} ` +
      `vote=${song.rhythm.bar_phase}/${s.vote.share.toFixed(2)}/${s.vote.votes}v bars=${song.rhythm.bar_confident_pct}%confident capo=${song.capo} bytes=${bytes}`);
  }
  for (const [id, item] of cfg.exclude) console.log(`excluded ${id}: ${item.reason}`);
  report(built);
  console.log(`\nwrote ${built.length} songs + index.json to ${rel(SONGS_DIR)}${warnings.length ? `; ${warnings.length} warning(s)` : ""}`);
}

module.exports = { barPhaseVote, barPhaseConfident, coreShapes, gridHolds, barAnchors, applyBarAnchors, barMetrics, BAR_COST,
  shapeTier, difficultyOf, applyLevelOverride, defaultPatterns, readCatalogue, finishSong, LEVELS };

if (require.main === module) main();
