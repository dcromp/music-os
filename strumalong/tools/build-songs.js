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
// exportSong is the Song export module: one draft + its metadata + the catalogue's settings -> song, card, report,
// with no file access. Everything below it is the filesystem adapter: read the config and packs, order the catalogue,
// write songs/ (or compare it, --check) and print the report.
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
const SONGS_DIR = path.join(ROOT, "songs");
const CATALOGUE = path.join(ROOT, "data/catalogue.json");
const REVIEW = path.join(REPO, "experiments/review");
const app = require(path.join(REVIEW, "app.js"));
const Core = require(path.join(ROOT, "lib/core.js"));
const { arrangementProfile, compareExpected, gridHolds, LEVELS, LEVEL } = require("./arrangement-profile.js");

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

// ---------------------------------------------------------------- levels (tiers, main shapes and level rules: tools/arrangement-profile.js)

const levelTitle = n => `Level ${n} · ${LEVEL.get(n).label}`;

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
  // Per-song opt-out of the automatic timing fix ("Timing fix"): {recording_id, reason}.
  const timingOff = new Map();
  for (const item of cfg.timing_fix_off || []) {
    if (!isStr(item.recording_id) || !isStr(item.reason)) fail("every timing_fix_off entry needs recording_id and reason");
    if (timingOff.has(item.recording_id)) fail(`duplicate timing_fix_off ${item.recording_id}`);
    timingOff.set(item.recording_id, item);
  }
  return { ...cfg, exclude, overrides, timingOff, sha256: sha(bytes) };
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
// share its anchor, so Full view (no merges) draws the same bars as Simple view. Any earlier b/a is replaced; every
// other chord field (c, t, and anything added later) is kept.
function applyBarAnchors(song) {
  const { holds, anchors, runs } = barAnchors(song);
  let h = 0;
  // New chord objects (a new array): lib/core.js caches its per-beat anchor map by chord-array identity.
  song.chords = song.chords.map(({ b, a, ...native }) => {
    const chord = { ...native };
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

// ---------------------------------------------------------------- repetition-consistency timing fix
// (docs/STRUMALONG_APP.md, "Timing fix"). Founder feedback, 25 Oct 2026: in Zombie one Em -> C change sat a beat later
// than every other time the same sequence is played. Pop songs repeat chord sequences with the same bar placement, so
// a change that sits exactly one beat away from where the other repeats of the same sequence sit is moved by one beat
// to match them. Display-level only: the raw chart (primary.json) is unchanged, labels never change, and every move is
// listed in chart.corrections. Runs before the bar anchors and the difficulty, so both see the fixed chart.
//
// A "change" is the start of a default-view hold (Core shapes at the song's capo, so quality blips do not split
// groups) between two in-grid chord holds that are neither N/X nor quick. Its group is the four-label context
// (previous, from, to, next). Its position is the beat of the change within the bar under a provisional phase: the
// bar-model Viterbi (barAnchors) run on the current chart, ignoring any stored b/a. A lone wrong change cannot pull a
// phase run onto itself (two phase switches cost more than one off-bar change), and the hold-length check below is
// phase-free, so a phase artefact alone can never justify a move. A move needs all of:
//   - a group of >= minAgree + 1 repeats whose most common position holds >= minShare of them and >= minAgree repeats;
//   - this change exactly one beat from that position (two beats or more is a different arrangement: left alone);
//   - both holds in the same phase run (a run boundary may be a beat-grid slip, not a chart error);
//   - under a confident phase, the change not leaving a bar or half-bar line for an off-beat position (a push that
//     most repeats round the other way only moves where the bars are a guess anyway: approx bars);
//   - the two holds' lengths after the move closer to the majority's median lengths (neither worse, the sum better,
//     and within maxDevAfter beats in total), with both holds and the shrinking native chord still >= 1 beat;
//   - no founder/alias correction (c:1) on either native chord, and the boundary not moved before (t:1).
// The moved change takes the majority repeats' median offset from their beat (clamped so it still rounds to the target
// beat and moves at most one beat in time), so it looks like the repeats it now matches. Passes repeat until nothing
// moves, so the fix is idempotent: run on its own output it moves nothing.
const TIMING_FIX = { minAgree: 3, minShare: 0.6, maxDevAfter: 1, minBeats: 1, maxFrac: 0.4, maxPasses: 8 };

const timingKey = (holds, i) => [i >= 2 ? holds[i - 2].label : "^", holds[i - 1].label, holds[i].label,
  i + 1 < holds.length ? holds[i + 1].label : "$"].join(" ");

// Seconds at fractional grid position p (the inverse of Core.beatPosition inside the grid).
function secondsAtPosition(beats, p) {
  const i = Math.min(beats.length - 2, Math.max(0, Math.floor(p)));
  return beats[i] + (p - i) * (beats[i + 1] - beats[i]);
}

/**
 * The changes of the default-view timeline with their repeat groups, under the provisional phase (opts.anchors: a
 * reference anchor per hold instead, e.g. the unfixed chart's, so a before/after comparison shares one bar grid).
 * @returns {{holds, changes: Array<{i, key, pos, lenA, lenB, frac, sameRun, native}>, groups: Map<string, object>}}
 *   group: {key, members, mode, agree, share, typA, typB, frac} for groups of 2+ changes (mode = most common position,
 *   ties to the lowest; typA/typB/frac = medians over the members at the mode).
 */
function timingGroups(song, opts = {}) {
  const bpb = song.rhythm.beats_per_bar;
  const provisional = barAnchors(song), holds = provisional.holds;
  const anchors = opts.anchors && opts.anchors.length === holds.length ? opts.anchors : provisional.anchors;
  const firstNative = new Map(song.chords.map((ch, k) => [ch.s, k]));
  const chordHold = h => h && h.inGrid && !h.quick && h.label !== "N" && h.label !== "X";
  const changes = [];
  for (let i = 1; i < holds.length; i++) {
    const A = holds[i - 1], B = holds[i], anchor = anchors[i];
    if (!chordHold(A) || !chordHold(B) || !anchor || anchor.mode !== "phase") continue;
    const prev = anchors[i - 1];
    changes.push({ i, key: timingKey(holds, i), pos: mod(B.base - anchor.phase, bpb), lenA: A.count, lenB: B.count,
      frac: B.sb - B.base, sameRun: Boolean(prev && prev.mode === "phase" && prev.phase === anchor.phase), confident: !anchor.approx,
      native: firstNative.has(B.s) ? firstNative.get(B.s) : -1 });
  }
  const groups = new Map();
  for (const ch of changes) {
    if (!groups.has(ch.key)) groups.set(ch.key, { key: ch.key, members: [] });
    groups.get(ch.key).members.push(ch);
  }
  for (const [key, g] of groups) {
    if (g.members.length < 2) { groups.delete(key); continue; }
    const tally = new Map();
    for (const ch of g.members) tally.set(ch.pos, (tally.get(ch.pos) || 0) + 1);
    const [mode, agree] = [...tally].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
    const at = g.members.filter(ch => ch.pos === mode);
    Object.assign(g, { mode, agree, share: agree / g.members.length, typA: median(at.map(ch => ch.lenA)), typB: median(at.map(ch => ch.lenB)),
      frac: median(at.map(ch => ch.frac)) });
  }
  return { holds, changes, groups };
}

// Share of changes in repeated groups (3+ repeats) that sit at their group's most common position. Compare a chart
// before and after the fix under one reference phase (opts.anchors): re-phasing a whole section by half a bar
// changes the drawn bars, not where the chords sit relative to each other.
function timingConsistency(song, opts = {}) {
  if (!(song.rhythm.beats_per_bar >= 3)) return { repeated: 0, consistent: 0, pct: 100 };
  let repeated = 0, consistent = 0;
  for (const g of timingGroups(song, opts).groups.values()) {
    if (g.members.length < 3) continue;
    repeated += g.members.length; consistent += g.agree;
  }
  return { repeated, consistent, pct: repeated ? r1(100 * consistent / repeated) : 100 };
}

// Every change that disagrees with a repeated group, with the move it would get or the reason it is left alone.
function timingCandidates(song, opts = {}) {
  const W = { ...TIMING_FIX, ...(opts.settings || {}) };
  const bpb = song.rhythm.beats_per_bar, beats = song.beats, chords = song.chords;
  const { holds, changes, groups } = timingGroups(song, opts);
  const out = [];
  for (const ch of changes) {
    const g = groups.get(ch.key);
    if (!g || g.members.length < 3 || ch.pos === g.mode) continue;
    const A = holds[ch.i - 1], B = holds[ch.i];
    const item = { change: ch, group: g, at: B.s, from: A.label, to: B.label, shift: 0, reason: null };
    out.push(item);
    const d = mod(ch.pos - g.mode, bpb);
    item.shift = d === 1 ? -1 : d === bpb - 1 ? 1 : 0;
    const k = ch.native;
    if (g.agree < W.minAgree || g.share < W.minShare - 1e-9) { item.reason = `no clear majority (${g.agree} of ${g.members.length} repeats agree)`; continue; }
    if (!item.shift) { item.reason = `${Math.min(d, bpb - d)} beats from the other repeats (only one-beat moves)`; continue; }
    if (!ch.sameRun) { item.reason = "starts a new bar-phase run (may be a beat-grid slip)"; continue; }
    const onLine = pos => pos === 0 || (bpb % 2 === 0 && pos === bpb / 2);
    if (ch.confident && onLine(ch.pos) && !onLine(g.mode)) { item.reason = "would leave the bar or half-bar line of a confident bar phase"; continue; }
    if (k < 1 || Math.abs(chords[k - 1].e - chords[k].s) > 1e-6 || Math.abs(chords[k - 1].e - A.e) > 1e-6) { item.reason = "chord boundary not contiguous"; continue; }
    if (chords[k].t) { item.reason = "already moved once"; continue; }
    if (chords[k].c || chords[k - 1].c) { item.reason = "next to a corrected chord"; continue; }
    const lenA = ch.lenA + item.shift, lenB = ch.lenB - item.shift;
    if (lenA < W.minBeats || lenB < W.minBeats) { item.reason = "a hold would drop below one beat"; continue; }
    const dev = (a, b) => [Math.abs(a - g.typA), Math.abs(b - g.typB)];
    const [a0, b0] = dev(ch.lenA, ch.lenB), [a1, b1] = dev(lenA, lenB);
    if (!(a1 <= a0 && b1 <= b0 && a1 + b1 < a0 + b0 && a1 + b1 <= W.maxDevAfter + 1e-9)) {
      item.reason = `hold lengths ${ch.lenA}+${ch.lenB} would become ${lenA}+${lenB}, not the repeats' ${g.typA}+${g.typB}`; continue;
    }
    // Placement: the majority's offset from its beat, at most one beat from where the change was, still rounding to the target.
    const target = B.base + item.shift;
    let p = target + Math.max(-W.maxFrac, Math.min(W.maxFrac, g.frac));
    p = Math.max(B.sb - 1, Math.min(B.sb + 1, p));
    if (!(target >= 0 && target <= beats.length - 1 && p >= 0 && p <= beats.length - 1)) { item.reason = "target beat outside the beat grid"; continue; }
    const s = r3(secondsAtPosition(beats, p)), q = Core.gridPosition(beats, s);
    const shrinking = item.shift < 0 ? [chords[k - 1].s, s] : [s, chords[k].e];
    const shrunk = Core.gridPosition(beats, shrinking[1]) - Core.gridPosition(beats, shrinking[0]);
    if (!(shrunk >= W.minBeats - 1e-9)) { item.reason = "the shortened chord would drop below one beat"; continue; }
    if (q === null || Math.round(q) !== target || Math.abs(q - B.sb) > 1 + 1e-6 || !(s > chords[k - 1].s && s < chords[k].e)) { item.reason = "no clean target time"; continue; }
    item.newStart = s;
  }
  return out;
}

/**
 * Apply the timing fix to song.chords (a new array; moved chords are new objects with t:1). Returns the moves
 * ({at, was, from, to, shift, agree}, in time order) and the changes still disagreeing with their group, with reasons.
 * opts.enabled false (catalogue timing_fix_off) or fewer than 3 beats per bar (direction ambiguous) moves nothing.
 */
function applyTimingFix(song, opts = {}) {
  const W = { ...TIMING_FIX, ...(opts.settings || {}) };
  const moves = [];
  let passes = 0, settled = true;
  if (opts.enabled !== false && song.rhythm.beats_per_bar >= 3 && song.beats.length >= 2) {
    song.chords = song.chords.map(ch => ({ ...ch }));
    for (settled = false; passes < W.maxPasses; passes++) {
      const touched = new Set(), pass = [];
      for (const item of timingCandidates(song, { settings: opts.settings })) {
        const i = item.change.i; // hold index: a neighbouring boundary changes this one's hold lengths, so it waits a pass
        if (item.newStart === undefined || touched.has(i - 1) || touched.has(i + 1)) continue;
        touched.add(i);
        pass.push({ k: item.change.native, item });
      }
      if (!pass.length) { settled = true; break; }
      for (const { k, item } of pass) {
        const was = song.chords[k].s;
        song.chords[k - 1] = { ...song.chords[k - 1], e: item.newStart };
        song.chords[k] = { ...song.chords[k], s: item.newStart, t: 1 };
        moves.push({ at: item.newStart, was, from: item.from, to: item.to, shift: item.shift, agree: `${item.group.agree}/${item.group.members.length}` });
      }
    }
  }
  moves.sort((a, b) => a.at - b.at);
  return { moves, left: timingLeftAlone(song, { settings: opts.settings, enabled: opts.enabled }), passes, settled };
}

// The changes that still disagree with a repeated group, with the reason each was left alone. opts.anchors: judge them
// under a reference phase (the build report uses the unfixed chart's, matching its consistency column).
function timingLeftAlone(song, opts = {}) {
  if (!(song.rhythm.beats_per_bar >= 3)) return [];
  return timingCandidates(song, opts).map(item => ({ at: item.at, from: item.from, to: item.to, shift: item.shift,
    agree: `${item.group.agree}/${item.group.members.length}`, reason: opts.enabled === false ? "timing fix off for this song" : item.reason ||
      (opts.anchors ? "one beat off under the unfixed chart's bar phase, not under the phase re-fitted after the other moves" : "would move next pass") }));
}

// The one chart.corrections entry that summarises the moves (none when nothing moved).
function timingCorrection(moves) {
  if (!moves.length) return null;
  const n = moves.length;
  return { id: "auto-timing", kind: "timing", count: n,
    start: Math.min(...moves.map(m => Math.min(m.at, m.was))), end: Math.max(...moves.map(m => Math.max(m.at, m.was))),
    note: `${n} chord change${n === 1 ? "" : "s"} moved by one beat to match the other repeats of the same sequence (automatic; raw chart unchanged)`,
    moves: moves.map(({ at, was, from, to, shift, agree }) => ({ at, was, from, to, shift, agree })) };
}

// ---------------------------------------------------------------- level override (the profile itself: tools/arrangement-profile.js)

function median(values) {
  const v = [...values].sort((a, b) => a - b), n = v.length;
  return n ? (n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2) : 0;
}

function applyLevelOverride(difficulty, override) {
  if (!override) return difficulty;
  return { ...difficulty, level: override.level, label: LEVEL.get(override.level).label, computed_level: difficulty.level,
    override_reason: override.reason };
}

// ---------------------------------------------------------------- song export

/**
 * Song export: one analysed chord draft, its authored metadata and the catalogue's settings for it -> the song file,
 * its library card and a build report. Pure: it reads and writes no files (main() below is the filesystem adapter).
 *
 * @param draft { case, primary, rhythmCase, correctionSet, packId, hashes }
 *   case: the pack manifest case (id, recording, source.source, artifacts.primary_sha256, primary_name).
 *   primary: the bytes of cases/<id>/primary.json, checked against case.artifacts.primary_sha256.
 *   rhythmCase: the paired beat grid. correctionSet: reported display corrections (prepared pack) or undefined.
 *   hashes: { manifest, rhythm, practice, learning, additions?, catalogue } for song.provenance.
 * @param metadata { title, artist, capo, capo_source, setup_note, strumming|null, learning, needs_syncopation?,
 *   playable_embed?, label_aliases?, expected?: { level, shapes } }  strumming null means "no authored patterns": the level's defaults are used.
 * @param settings { timingFix?, levelOverride? }  timingFix false: catalogue timing_fix_off lists this recording.
 *   levelOverride: a catalogue level_overrides entry ({ level, reason }).
 * @returns {{ song, card, report }}  song.order and card.order stay null: order within a level is a catalogue decision.
 *   report: { warnings, expected: compareExpected result, chords, beats, vote, bars: {before, after, runs}, timing: {moves, left, passes, settled,
 *   enabled, before, after} } for the build report.
 *
 * Each chart step gets its own copy of the chords (chartView), so no step depends on whether another one replaces
 * song.chords or edits it in place: the unfixed chart stays the unfixed chart.
 */
function exportSong(draft, metadata, settings = {}) {
  const { case: c, primary, rhythmCase, correctionSet, packId, hashes } = draft;
  const meta = metadata, timingFix = settings.timingFix !== false;
  const warnings = [];
  const primarySha = sha(primary);
  if (primarySha !== c.artifacts.primary_sha256) throw new Error(`primary.json sha256 mismatch for ${c.id}`);
  const chart = app.validateCandidate(JSON.parse(primary), c.recording);
  const display = app.correctedDisplayEvents(chart, correctionSet, packId, primarySha);
  if (!rhythmCase) throw new Error(`no paired rhythm grid for ${c.id}`);
  // Alternate uploads were removed (#44): the analysed upload is the only video, so it has to embed.
  if (meta.playable_embed === false) throw new Error(`${c.id}: playable_embed false needs an embeddable alternate video, and alternates are not supported`);

  // chords: sounding label after display corrections; c:1 marks a corrected event
  // Optional per-song label aliases from additions metadata: a chart label the detector names differently from the
  // grip players use (e.g. A Horse with No Name's F#m7 is played as D6add9/F#). Applied to whole events; c:1 marks them.
  const aliases = meta.label_aliases || null;
  const aliasCounts = {};
  const unfixed = display.map(e => {
    const out = { s: r3(e.start_seconds), e: r3(e.end_seconds), l: e.label };
    if (e.display_correction) out.c = 1;
    if (aliases && Object.prototype.hasOwnProperty.call(aliases.map, e.label)) {
      const seen = aliasCounts[e.label] || { count: 0, start: out.s, end: out.e };
      aliasCounts[e.label] = { count: seen.count + 1, start: Math.min(seen.start, out.s), end: Math.max(seen.end, out.e) };
      out.l = aliases.map[e.label]; out.c = 1;
    }
    return out;
  });
  unfixed.forEach((e, i) => {
    if (!(e.s >= 0) || !(e.e > e.s)) throw new Error(`${c.id}: chord ${i} collapsed after rounding`);
    if (i && e.s < unfixed[i - 1].e) throw new Error(`${c.id}: chord ${i} overlaps previous after rounding`);
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
  const rhythm = { status: rhythmCase.status, bpm: r1(rhythmCase.pulse_bpm), beats_per_bar: bpb, beats_per_bar_assumed: assumed,
    meter_label: rhythmCase.meter_label, bar_phase: vote.phase, bar_phase_confident: barPhaseConfident(vote, assumed), bar_phase_share: r2(vote.share) };
  // What the chart steps (and lib/core.js) read of a song, around a fresh copy of the given chords.
  const chartView = chords => ({ capo: meta.capo, beats, rhythm, chords: chords.map(ch => ({ ...ch })) });

  // repetition-consistency timing fix (display-level), measured against the same anchored bars without it
  const fixing = chartView(unfixed);
  const timing = applyTimingFix(fixing, { enabled: timingFix });
  const fixed = fixing.chords;
  const timingEntry = timingCorrection(timing.moves);
  if (timingEntry) corrections.push(timingEntry);
  if (!timing.settled) warnings.push(`${c.id}: timing fix still moving after ${timing.passes} passes`);
  const reference = { anchors: barAnchors(chartView(unfixed)).anchors };
  const anchoredUnfixed = chartView(unfixed);
  applyBarAnchors(anchoredUnfixed);
  const timingBefore = { consistency: timingConsistency(chartView(unfixed), reference), bars: barMetrics(anchoredUnfixed) };
  const timingAfter = { consistency: timingConsistency(chartView(fixed), reference),
    left: timingLeftAlone(chartView(fixed), { ...reference, enabled: timingFix }) };

  // bar anchors on the fixed chords, then the bar summary the details panel reads
  const before = barMetrics(chartView(fixed));
  const anchoring = chartView(fixed);
  const bars = applyBarAnchors(anchoring);
  const chords = anchoring.chords;
  const after = barMetrics(anchoring);
  timingAfter.bars = after;

  // level (with any catalogue override) and the level's default patterns for unauthored songs
  const difficulty = applyLevelOverride(arrangementProfile(anchoring, { needsSyncopation: meta.needs_syncopation === true }), settings.levelOverride);
  // editorial expected_level / expected_shapes (additions research drafts): reported only, never a reference
  const expected = compareExpected(difficulty, meta.expected || {});
  if (expected.level) warnings.push(`${c.id}: built Level ${expected.level.built}, metadata expected_level ${expected.level.expected} (report only)`);
  const strumming = meta.strumming ? { ...meta.strumming, source: meta.strumming.source || "authored" }
    : { note: `Default practice patterns for Level ${difficulty.level} songs; not checked against the recording.`,
      source: "level-default", patterns: defaultPatterns(difficulty.level, bpb).map(pickPattern) };
  for (const p of strumming.patterns) {
    if (p.counts.length !== p.strokes.length || p.counts.length % bpb !== 0) throw new Error(`${c.id}: pattern ${p.id} does not fit ${bpb} beats per bar`);
  }
  const group = `level-${difficulty.level}`;

  const src = c.source.source;
  const song = {
    schema: "strumalong-song-2",
    id: c.id, title: meta.title, artist: meta.artist, group, order: null, level: difficulty.level,
    recording: { id: c.recording.id, duration_seconds: r3(c.recording.duration_seconds), audio_sha256: c.recording.audio_sha256 },
    videos: [{ video_id: src.video_id, uploader: src.uploader, kind: "analysed", duration_seconds: src.duration_seconds,
      offset_seconds: 0, timing_checked: true, note: "Chart computed from this upload's audio." }],
    chart: { source: c.primary_name || "CREMA automatic draft", sha256: primarySha, status: "provisional", corrections },
    capo: meta.capo, capo_source: meta.capo_source,
    setup_note: meta.setup_note,
    difficulty,
    rhythm: { ...rhythm, bar_model: "anchored-1", bar_confident_pct: r1(100 - after.approx_pct) },
    beats, chords,
    strumming,
    learning: meta.learning,
    provenance: { pack: packId, manifest_sha256: hashes.manifest, rhythm_sha256: hashes.rhythm, practice_sha256: hashes.practice,
      learning_sha256: hashes.learning, ...(hashes.additions ? { additions_sha256: hashes.additions } : {}), catalogue_sha256: hashes.catalogue },
  };
  const card = {
    id: c.id, title: meta.title, artist: meta.artist, group, order: null, level: difficulty.level, level_label: difficulty.label,
    video_id: src.video_id, duration_seconds: r2(c.recording.duration_seconds),
    bpm: Math.round(rhythmCase.pulse_bpm), meter_label: rhythmCase.meter_label, capo: meta.capo,
    core_shapes: difficulty.main_shapes, // the shapes the level counts (one Arrangement profile)
    playable_embed: true, embed_note: "",
  };
  const report = { warnings, expected, chords: chords.length, beats: beats.length, vote, bars: { before, after, runs: bars.runs },
    timing: { ...timing, enabled: timingFix, before: timingBefore, after: timingAfter } };
  return { song, card, report };
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

// The catalogue's settings for one recording, and its export from the pack's draft bytes (song warnings go to the log).
const settingsFor = (cfg, id) => ({ timingFix: !cfg.timingOff.has(id), levelOverride: cfg.overrides.get(id) });
function exportCase(cfg, packDir, draft, metadata) {
  const c = draft.case;
  const primary = read(path.join(packDir, "cases", c.id, "primary.json"));
  const result = exportSong({ ...draft, primary }, metadata, settingsFor(cfg, c.id));
  result.report.warnings.forEach(warn);
  return result;
}

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
    built.push(exportCase(cfg, dir,
      { case: c, packId: manifest.pack_id, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: prac.display_corrections },
      { title: titles[0], artist: titles[1], capo, capo_source: capo > 0 ? "catalogue" : "none",
        setup_note: entry ? entry.setup_note : "Standard tuning (EADGBE). Capo and exact recording pitch are unchecked.",
        strumming: { note: prac.note, beats_description: prac.beats_description, source: "authored",
          patterns: prac.patterns.map(p => ({ id: p.id, name: p.name, counts: p.counts, strokes: p.strokes, description: p.description })) },
        learning: entry ? { skill_focus: entry.skill_focus, prerequisites: entry.prerequisites, sources: entry.sources.map(s => ({ title: s.title, url: s.url })) }
          : { skill_focus: "", prerequisites: "", sources: [] } }));
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
      built.push(exportCase(cfg, dir,
        { case: c, packId, hashes, rhythmCase: rhythmById.get(c.id), correctionSet: undefined },
        { title: entry.title, artist: entry.artist,
          // "suggested" with capo 0 means no capo is suggested: the song contract is capo_source "none" exactly at capo 0.
          capo: entry.capo, capo_source: entry.capo > 0 ? entry.capo_source : "none", setup_note: entry.setup_note, strumming,
          needs_syncopation: entry.needs_syncopation === true, playable_embed: entry.playable_embed,
          label_aliases: entry.label_aliases || null,
          // editorial research drafts, compared with the built profile and reported only
          expected: { level: entry.expected_level, shapes: entry.expected_shapes },
          learning: { skill_focus: entry.skill_focus || "", prerequisites: entry.prerequisites || "",
            sources: (entry.sources || []).map(s => ({ title: s.title, url: s.url })) } }));
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
  for (const id of cfg.timingOff.keys()) if (!ids.has(id)) warn(`timing_fix_off for ${id}, which is not in the catalogue`);
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
  for (const { song, report: { bars: s } } of built) {
    const b = s.before, a = s.after;
    console.log(`${song.title.slice(0, 40).padEnd(40)} ${pad(`${b.on_bar_or_half}→${a.on_bar_or_half}`, 12)} ${pad(`${b.weird}→${a.weird}`, 8)} ` +
      `${pad(`${b.split}→${a.split}`, 9)} ${pad(`${b.restarts}→${a.restarts}`, 9)} ${pad(`${b.approx_pct}→${a.approx_pct}`, 10)}  ` +
      s.runs.map(r => `${r.mode === "hold" ? "H" : r.state}${r.confident ? "" : "?"}×${r.to - r.from}`).join(" "));
  }
  console.log("\nTiming fix (repetition consistency; anchored bars without -> with the fix). consistent = % of changes in repeated");
  console.log("sequences (3+ repeats) at their group's usual bar position:");
  console.log(`${"song".padEnd(40)} ${"moved".padStart(5)} ${"consistent %".padStart(13)} ${"weird".padStart(7)} ${"split".padStart(7)} ${"on bar+half".padStart(12)}  left alone`);
  let movedTotal = 0;
  for (const { song, report: { timing: t } } of built) {
    const b = t.before, a = t.after;
    movedTotal += t.moves.length;
    console.log(`${song.title.slice(0, 40).padEnd(40)} ${pad(t.enabled ? t.moves.length : "off", 5)} ${pad(`${b.consistency.pct}→${a.consistency.pct}`, 13)} ` +
      `${pad(`${b.bars.weird}→${a.bars.weird}`, 7)} ${pad(`${b.bars.split}→${a.bars.split}`, 7)} ${pad(`${b.bars.on_bar_or_half}→${a.bars.on_bar_or_half}`, 12)}  ${a.left.length}`);
  }
  console.log(`${movedTotal} chord changes moved in total. Moves (shape labels at the default view; -1 = one beat earlier):`);
  for (const { song, report: { timing: t } } of built) {
    if (!t.moves.length) continue;
    console.log(`  ${song.title}: ` + t.moves.map(m => `${Core.formatTime(m.at)} ${m.from}→${m.to} ${m.shift < 0 ? "-1" : "+1"}`).join(", "));
  }
  const detail = (process.argv.find(arg => arg.startsWith("--timing-detail=")) || "").slice("--timing-detail=".length);
  for (const { song, report: { timing: t } } of built) {
    if (!detail || !song.id.includes(detail)) continue;
    console.log(`\nTiming detail: ${song.title} (${song.id})`);
    for (const m of t.moves) console.log(`  moved ${Core.formatTime(m.at)} (${m.at.toFixed(3)} s, was ${m.was.toFixed(3)} s) ${m.from}→${m.to} ` +
      `one beat ${m.shift < 0 ? "earlier" : "later"}; ${m.agree} repeats agree`);
    for (const m of t.after.left) console.log(`  left  ${Core.formatTime(m.at)} (${m.at.toFixed(3)} s) ${m.from}→${m.to}; ${m.agree} repeats agree: ${m.reason}`);
  }

  console.log("\nExpected shapes (additions metadata expected_shapes vs built main shapes; editorial drafts, report only):");
  let shapeMismatches = 0;
  for (const { song, report: { expected } } of built) {
    const sh = expected && expected.shapes;
    if (!sh) continue;
    shapeMismatches++;
    console.log(`  ${song.title}: expected ${sh.expected.join(" ")} · built ${sh.built.join(" ")}` +
      `${sh.missing.length ? ` · not main: ${sh.missing.join(" ")}` : ""}${sh.extra.length ? ` · unexpected: ${sh.extra.join(" ")}` : ""}`);
  }
  console.log(`  ${shapeMismatches} song(s) differ.`);

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

  for (const { song, report: s } of built) {
    const bytes = Buffer.byteLength(outputs.get(song.id + ".json"));
    console.log(`${song.id.slice(0, 44).padEnd(44)} L${song.level}#${song.order} chords=${String(s.chords).padStart(3)} beats=${String(s.beats).padStart(3)} ` +
      `bpm=${String(song.rhythm.bpm).padEnd(5)} bpb=${song.rhythm.beats_per_bar}${song.rhythm.beats_per_bar_assumed ? "(assumed)" : ""} ` +
      `vote=${song.rhythm.bar_phase}/${s.vote.share.toFixed(2)}/${s.vote.votes}v bars=${song.rhythm.bar_confident_pct}%confident capo=${song.capo} bytes=${bytes}`);
  }
  for (const [id, item] of cfg.exclude) console.log(`excluded ${id}: ${item.reason}`);
  report(built);
  console.log(`\nwrote ${built.length} songs + index.json to ${rel(SONGS_DIR)}${warnings.length ? `; ${warnings.length} warning(s)` : ""}`);
}

module.exports = {
  exportSong,
  // adapter: the catalogue config, and the whole catalogue built in memory from the packs (what main() writes)
  readCatalogue, buildCatalogue,
  // Exported only for unit tests the chord vocabulary and repeat-timing deepenings will move into their own modules
  // (the Arrangement profile is tools/arrangement-profile.js); nothing else should import them.
  barPhaseVote, barPhaseConfident, gridHolds, barAnchors, applyTimingFix, timingConsistency, timingCorrection,
};

if (require.main === module) main();
