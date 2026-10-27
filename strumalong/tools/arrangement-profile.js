"use strict";
// Arrangement profile: a song's main chord shapes, its level (1-5) and the reasons for that level, at the song's
// default view (capo shapes, Simple). The exporter uses the one profile for both the library-card chips and the level,
// so the card always shows the shapes the level was computed on.
//
//   arrangementProfile(song, { needsSyncopation })  -> song.difficulty (main_shapes doubles as the card's core_shapes)
//   compareExpected(profile, { level, shapes })     -> editorial expected_level / expected_shapes mismatches (report only)
//
// Spec: docs/STRUMALONG_APP.md, "Difficulty levels" (lead decision 25 Oct 2026; one main-shape rule, issue #41).

const path = require("node:path");
const Core = require(path.join(__dirname, "..", "lib", "core.js"));

// Shape tiers are what the player frets: Core shapes at the song's default view (capo shapes, Simple quality).
const TIER_SHAPES = {
  1: ["A", "D", "E", "Em", "Am", "A7", "D7", "E7", "Am7", "Em7", "Asus2", "Asus4", "Dsus2", "Dsus4", "Esus4", "D6add9/F#"],
  2: ["G", "C", "Dm", "G7", "C7", "B7", "Cadd9", "Cmaj7", "Fmaj7", "Dm7", "G/B", "D/F#", "C/G"],
  3: ["F", "Bm", "Bm7", "F#m"],
};
const TIER_OF = new Map(Object.entries(TIER_SHAPES).flatMap(([tier, shapes]) => shapes.map(s => [s, Number(tier)])));

const LEVELS = [
  { level: 1, label: "First chords", note: "Up to three easy shapes from A, D, E, Em and Am." },
  { level: 2, label: "Open chords", note: "Open chords such as G and C, up to four shapes, at a relaxed pace." },
  { level: 3, label: "More changes", note: "Open chords with more shapes, quicker changes or a syncopated strum." },
  { level: 4, label: "First barre (F / Bm)", note: "Adds a first barre-type shape: F, Bm or F#m." },
  { level: 5, label: "Barre chords", note: "Full barre shapes such as B, Bb, Cm or C#m." },
];
const LEVEL = new Map(LEVELS.map(l => [l.level, l]));

const MAIN_SHAPE_SHARE = 0.04;   // main shapes cover at least 4% of non-blip chord time
const MAIN_SLASH_SHARE = 0.10;   // a slash shape (bass-note variant) needs 10%
const BLIP_BEATS = Core.QUICK_BEATS;  // holds shorter than this are blips (the app's "quick" threshold, 0.75 beat)
const QUICK_CPM = 40, QUICK_MEDIAN_BEATS = 2, QUICK_MEDIAN_BPM = 120;

const r1 = x => Math.round(x * 10) / 10;

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

/**
 * Main shapes: Core shapes covering >= 4% of chord time (slash shapes >= 10%), ignoring N, X and blips (< 0.75 beat);
 * longest first, ties by first appearance. Changes: label changes between consecutive non-blip chord holds (not across
 * N or X), per minute of non-blip chord time. Median hold: beats per non-blip chord hold.
 *   L5 any tier-4 main shape; L4 any tier-3; else L1 when all tier 1 and <= 3 shapes, L2 when <= 4 shapes (any
 *   number if all tier 1), L3 when 5+ shapes; and L1/L2 move to L3 on quick changes (median hold <= 2 beats at
 *   >= 120 BPM, or >= 40 changes/min) or an authored needs_syncopation flag.
 */
function arrangementProfile(song, opts = {}) {
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
    .filter(x => x.share >= (x.shape.includes("/") ? MAIN_SLASH_SHARE : MAIN_SHAPE_SHARE))
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

/**
 * Compare a profile (after any level override) with the editorial expected_level / expected_shapes from the additions
 * research. These are drafts, not references: the result is reported, never used to change or fail the build.
 * Returns { level: null | {expected, built}, shapes: null | {expected, built, missing, extra} }.
 */
function compareExpected(profile, expected = {}) {
  const out = { level: null, shapes: null };
  if (Number.isInteger(expected.level) && expected.level !== profile.level) out.level = { expected: expected.level, built: profile.level };
  if (Array.isArray(expected.shapes)) {
    const want = new Set(expected.shapes), have = new Set(profile.main_shapes);
    const missing = expected.shapes.filter(s => !have.has(s)), extra = profile.main_shapes.filter(s => !want.has(s));
    if (missing.length || extra.length) out.shapes = { expected: expected.shapes, built: profile.main_shapes, missing, extra };
  }
  return out;
}

module.exports = { arrangementProfile, compareExpected, shapeTier, gridHolds, LEVELS, LEVEL, BLIP_BEATS, MAIN_SHAPE_SHARE, MAIN_SLASH_SHARE };
