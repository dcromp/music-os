#!/usr/bin/env node
"use strict";
// Strum Along catalogue check: automatic per-recording verdicts (pass / flag / fail) with reasons.
//
//   node experiments/analysis/strumalong/catalogue_checks.js            # table + writes docs/STRUMALONG_CATALOGUE_CHECKS.json
//   node experiments/analysis/strumalong/catalogue_checks.js --json     # full report on stdout (still writes the file)
//   ... --markdown      print the summary as a markdown table instead of the text table
//   ... --no-write      do not write the report file
//   ... --out <path>    write the report somewhere else
//   ... --check         fail (exit 1) when the report on disk differs from a fresh run
//   ... --strict        also exit 1 when a SHIPPED song is flagged (default: only on a hard-gate fail)
//
// Exit code is non-zero when a SHIPPED song fails a hard gate. Read-only on every input (frozen packs, review
// files, exported songs, fixtures); the only file written is the report. No audio is read and no lyrics exist
// anywhere in the inputs or the output. Spec, thresholds and validation: docs/STRUMALONG_CATALOGUE_CHECKS.md.

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const REPO = path.resolve(__dirname, "../../..");
const Core = require(path.join(REPO, "strumalong/lib/core.js"));       // beatPosition: the same maths the app and exporter use
const Chords = require(path.join(REPO, "strumalong/lib/chords.js"));   // chord-label parsing and capo transposition
const RepeatTiming = require(path.join(REPO, "strumalong/lib/repeat-timing.js"));  // the played-timing judgement (check 4)

const SCHEMA = "strumalong-catalogue-checks-1";
const INSTRUMENT_SCHEMA = "strumalong-instrument-tags-1";

// ------------------------------------------------------------------------------------------------ thresholds
// Every number a verdict depends on lives here and is printed into the report (`thresholds`).
const T = {
  main_family_share: 0.04,        // a "main" chord family covers >= 4% of chord time
  chords: {
    missing_below: 0.01,          // an expected family with < 1% of chord time is "missing"
    core_count: 3,                // the first three listed expected families are the song's core progression
    flag_cover: 0.80,             // share of chord time inside the expected families
    fail_cover: 0.50,
    flag_unexpected_share: 0.08,  // one unexpected family this large flags; any main (>= 4%) one is noted
  },
  tempo: {
    edge_pin: 0.015,              // pulse within 1.5% of a range edge: the prior may be clipping the true tempo
    range_slack: 0.01,            // tolerance before "outside the range"
    fail_outside: 0.10,           // more than 10% outside the range
    ratio_window: 0.08,           // pulse / start_bpm within 8% of 0.5 or 2 -> half/double suspicion
    hold_double_median: 12,       // median chord hold of 12+ beats: grid may be twice the real tempo
    hold_half_median: 1.0,        // median chord hold of <= 1 beat: grid may be half the real tempo
    flag_interval_cv: 0.08,       // beat intervals this irregular: the grid wanders
    flag_implied_gap: 0.04,       // median beat interval disagrees with pulse_bpm by > 4%
  },
  plausibility: {
    long_hold_beats: 24,          // a single hold this long is "long"
    flag_long_share: 0.10,        // flag: >= 10% of chord time in long holds, with >= 2 families in the progression
    flag_max_hold_beats: 32,      // flag: any single hold this long
    fail_long_share: 0.25,        // fail needs all of: >= 25% of chord time in long holds ...
    fail_long_count: 3,           // ... at least 3 separate long holds (one break or solo is legitimate) ...
    fail_max_hold_beats: 32,      // ... and one of them 32+ beats (8+ bars of 4/4), with >= 2 expected families.
    flag_nx_share: 0.20,          // N + X share of the recording
    fail_nx_share: 0.50,
    blip_beats: Core.QUICK_BEATS, // holds shorter than this (0.75) are blips: the app's and the exporter's "quick" line
    absent_family_floor: 0.01,    // with long holds, an expected family below this share counts as absent
    // Hold homogeneity (experiments/generated/strumalong-hold-checks.json, hold_homogeneity.py). The chart signature above alone
    // only flags; it fails when the audio inside those same long holds also changes chord. Calibrated on 25 Oct 2026: A Horse with
    // No Name 17 of 45 bars (0.38) against the vamps Ho Hey 1 of 22 (0.05) and Stuck in the Middle with You 1 of 55 (0.02).
    hold_fail_missed: 0.25,       // fail: >= 25% of the bars inside the chart's long holds fit another main chord better
    hold_min_bars: 12,            // ... measured over at least 12 bars (3 bars of evidence) ...
    hold_match_seconds: 1.0,      // a hold in the hold-check file is the chart's hold when its start is within 1 s
  },
  consistency: {
    min_group: 4,                 // a repeated change needs 4+ occurrences of the same from>to pair
    min_majority: 0.60,           // ... and 60%+ of them within inlier_beats of one position to define "the usual" position
    inlier_beats: 0.5,
    deviant_beats: 0.75,          // a change 0.75 to 1.5 beats from its group's usual position is a mistiming candidate
    half_bar_beats: 1.5,          // 1.5+ beats off (a half bar in 4/4) is a different placement of the change, not a mistiming
    min_shift_run: 3,             // 3+ consecutive deviants in the same direction are a phase shift, not isolated mistimings
    min_coverage: 0.40,           // eligible repeated changes / positioned changes; below: not enough evidence
    flag_min_deviants: 2,         // flag: at least 2 isolated changes about a beat off their usual position
    fail_consistency: 0.80,       // fail: under 80% of repeated changes at their usual position
    flag_auto_timing_share: 0.10, // flag: the exporter's auto-timing moved 10%+ of the chord changes
    worse_beats: 0.25,            // an auto-timing move that leaves a change 0.25+ beat further from its group's usual position is 'worse'
    flag_worsened_moves: 2,       // flag: 2+ such moves
    flag_shift_share: 0.10,       // flag: phase shifts the exporter's bar anchors do not follow, covering 10%+ of repeated changes
    list_deviants: 12,            // deviants listed per song
  },
  // Calibrated on 25 Oct 2026 against the founder's labels (44 recordings; docs/STRUMALONG_CATALOGUE_CHECKS.md, Validation).
  // Two questions. Guitar-led: the Demucs guitar stem's share of the harmonic accompaniment, corroborated by YAMNet tags (top-5
  // frame fractions). Strummed: restrike_onbeat from strum_features.py. Technique never fails on its own: the labelled picked and
  // riff songs (0.583-0.630) and dense strummed songs (0.627-0.655) overlap within about two standard errors.
  instrument: {
    guitar_keys: ["guitar", "acoustic_guitar", "electric_guitar", "steel_guitar"],
    other_keys: ["ukulele", "piano", "harmonica", "banjo", "mandolin", "accordion", "organ", "keyboard", "synthesizer", "violin", "harp"],
    share_fail: 0.10,             // guitar stem under 10% of guitar + piano + other: the stem is nearly empty (Riptide 0.04) ...
    share_flag: 0.33,             // ... under a third: guitar may not lead (Love Me Do 0.14, lowest shipped 0.17 and 0.22, next 0.59)
    // YAMNet thresholds as designed before the batch ran (top-5 frame fractions); they now only corroborate the guitar share.
    min_guitar: 0.25,             // best guitar tag below this: YAMNet hears no guitar
    min_other: 0.30,              // a non-guitar tag below this is ignored; at or above the best guitar tag it is reported
    fail_margin: 0.15,            // a non-guitar tag this far above the best guitar tag is a clear YAMNet lead
    restrike_flag: 0.64,          // restrike_onbeat below this flags: the highest labelled picked song (Creep 0.630) + 1 SE (0.01)
    restrike_min_attacks: 50,     // fewer on-beat attacks than this: not enough to judge
  },
};

// Embed facts recorded elsewhere in the repo for the first ten (the packs carry no embed check of their own).
const KNOWN_EMBED = {
  "nirvana-come-as-you-are-youtube-20261011": {
    status: "fail", note: "Age-restricted: the catalogue upload cannot play in an embed.",
    source: "git 60330ce strumalong/tools/build-songs.js (AGE_RESTRICTED set; embed_note says age-restricted); origin/gh-pages 786b87d app.js comment (24 Oct 2026 build)",
  },
};

// ------------------------------------------------------------------------------------------------ small helpers
const sha256 = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const r2 = x => (x === null || x === undefined ? null : Math.round(x * 100) / 100);
const r3 = x => (x === null || x === undefined ? null : Math.round(x * 1000) / 1000);
const isNum = x => typeof x === "number" && Number.isFinite(x);
const mod = (a, n) => ((a % n) + n) % n;
const median = values => {
  const s = [...values].sort((a, b) => a - b);
  return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null;
};
const pct = x => (x === null || x === undefined ? "n/a" : `${Math.round(x * 100)}%`);
const readJSON = file => JSON.parse(fs.readFileSync(file, "utf8"));
const tryJSON = file => { try { return fs.existsSync(file) ? readJSON(file) : null; } catch { return null; } };
const fileSha = file => (fs.existsSync(file) ? sha256(fs.readFileSync(file)) : null);
const STATUS_RANK = { pass: 0, flag: 1, fail: 2 };
const worst = statuses => statuses.reduce((w, s) => (STATUS_RANK[s] > STATUS_RANK[w] ? s : w), "pass");

// ------------------------------------------------------------------------------------------------ chord families
/** Parse a chord label into {root, kind, bass}. kind: "" major-ish, "m" minor-ish, "sus", "5", "dim", "aug". null for N, X or junk. */
function parseChord(label) {
  if (typeof label !== "string" || label === "N" || label === "X") return null;
  const p = Chords.parse(label.trim());
  if (!p) return null;
  const q = p.quality;
  // Order matters: "maj7" and "m7b5" both start with "m".
  let kind;
  if (q === "") kind = "";
  else if (/sus/.test(q)) kind = "sus";                   // sus4, sus2, 7sus4
  else if (/^(dim|o|°|m7b5|hdim)/.test(q)) kind = "dim";
  else if (/^(aug|\+)/.test(q)) kind = "aug";
  else if (q === "5") kind = "5";
  else if (/^(maj|M)/.test(q)) kind = "";
  else if (/^(m|min|minor)/.test(q)) kind = "m";
  else kind = "";                       // 6, 7, 9, 11, 13, add9, (...) keep the major triad
  return { root: p.rootPc, kind, bass: p.bass };
}
/** Family key: root + kind ("Em", "G", "Asus", "D5"). null for N, X, junk. */
function familyKey(label) {
  const p = parseChord(label);
  return p ? Chords.noteName(p.root) + p.kind : null;
}
const splitFamily = key => { const p = Chords.parse(key); return { root: p.rootPc, kind: p.quality }; };
/** A chart family satisfies an expected family when the root matches and the quality agrees. A sus or power chord has no
 *  third, so it satisfies either the major or the minor chord on its root. */
function familyMatches(chartKey, expectedKey) {
  const c = splitFamily(chartKey), e = splitFamily(expectedKey);
  if (c.root !== e.root) return false;
  if (c.kind === e.kind) return true;
  if ((c.kind === "sus" || c.kind === "5") && (e.kind === "" || e.kind === "m")) return true;
  if ((e.kind === "sus" || e.kind === "5") && (c.kind === "" || c.kind === "m")) return true;
  return false;
}
const dedupe = list => [...new Set(list)];

// ------------------------------------------------------------------------------------------------ views, beats, holds
/** A "view" is what the checks run on: {id, source, duration, chords:[{s,e,l}], beats:[], bpb, bpbAssumed, pulseBpm}. */

function medianInterval(beats) {
  if (!Array.isArray(beats) || beats.length < 2) return null;
  return median(beats.slice(1).map((b, i) => b - beats[i]));
}
/** Fractional beat index at time t; outside the grid it extrapolates at the median interval so every hold has a length. */
function beatAt(beats, t) {
  const p = Core.beatPosition(beats, t);
  if (p !== null) return p;
  const iv = medianInterval(beats);
  if (!iv || !beats.length) return null;
  return t < beats[0] ? -(beats[0] - t) / iv : beats.length - 1 + (t - beats[beats.length - 1]) / iv;
}
/** Gap between two runs, in beats (seconds at the median interval would do the same; beats keep slow songs honest). */
const gapBeats = (a, b) => (a.b1 !== null && b.b0 !== null ? b.b0 - a.b1 : (b.s - a.e) * 2);
const GAP_TOLERANCE_BEATS = 0.8;           // a stray frame between two chords can be up to the blip size
/** Merge adjacent chord events of one family into runs. N and X break runs. Blips (shorter than `blipBeats`) sandwiched between
 *  two runs of the same family are absorbed so a long hold is not split by one stray frame. */
function familyRuns(view, blipBeats) {
  const runs = [];
  for (const e of view.chords) {
    const key = familyKey(e.l);
    const last = runs[runs.length - 1];
    if (last && last.key === key && key !== null && Math.abs(last.e - e.s) < 0.25) last.e = e.e;
    else runs.push({ key, label: e.l, s: e.s, e: e.e });
  }
  for (const r of runs) { r.b0 = beatAt(view.beats, r.s); r.b1 = beatAt(view.beats, r.e); r.beats = r.b0 === null ? null : r.b1 - r.b0; }
  const out = [];
  for (let i = 0; i < runs.length; i++) {
    const r = runs[i], prev = out[out.length - 1], next = runs[i + 1];
    if (blipBeats && r.key !== null && r.beats !== null && r.beats < blipBeats && prev && next && prev.key !== null && prev.key === next.key) {
      continue;   // dropped; the neighbours merge when `next` arrives
    }
    if (prev && prev.key === r.key && r.key !== null && gapBeats(prev, r) <= GAP_TOLERANCE_BEATS) { prev.e = r.e; prev.b1 = r.b1; prev.beats = prev.b1 - prev.b0; }
    else out.push({ ...r });
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ check 1: chords
/** Chord time per family. N and X time is returned separately. */
function familyShares(chords) {
  const byFamily = new Map();
  let chordSecs = 0, nSecs = 0, xSecs = 0;
  for (const e of chords) {
    const d = e.e - e.s;
    if (e.l === "N") { nSecs += d; continue; }
    if (e.l === "X") { xSecs += d; continue; }
    const key = familyKey(e.l);
    if (!key) { xSecs += d; continue; }
    chordSecs += d;
    byFamily.set(key, (byFamily.get(key) || 0) + d);
  }
  return { byFamily, chordSecs, nSecs, xSecs };
}

/** expected: {families:[sounding family labels, core first], accepted:[extra accepted labels], source, confidence} or null. */
function checkChords(view, expected) {
  const { byFamily, chordSecs } = familyShares(view.chords);
  const out = { status: "pass", reasons: [] };
  if (!expected || !expected.families.length) {
    return { status: "pass", reference: "none", note: "no reference", reasons: [], chart_main: mainFamilies(byFamily, chordSecs) };
  }
  if (chordSecs <= 0) return { status: "fail", reference: expected.source, reasons: ["The chart has no chord time."], cover: 0, chart_main: [] };
  const required = dedupe(expected.families.map(f => familyKey(f)).filter(Boolean));
  const accepted = dedupe([...required, ...(expected.accepted || []).map(f => familyKey(f)).filter(Boolean)]);
  const matchesAny = (key, list) => list.some(e => familyMatches(key, e));
  let covered = 0;
  for (const [key, secs] of byFamily) if (matchesAny(key, accepted)) covered += secs;
  const cover = covered / chordSecs;
  const shareOfExpected = e => { let s = 0; for (const [key, secs] of byFamily) if (familyMatches(key, e)) s += secs; return s / chordSecs; };
  const missing = required.filter(e => shareOfExpected(e) < T.chords.missing_below);
  const coreMissing = required.slice(0, T.chords.core_count).filter(e => missing.includes(e));
  const weak = required.filter(e => !missing.includes(e) && shareOfExpected(e) < T.main_family_share);
  const main = mainFamilies(byFamily, chordSecs);
  const unexpectedMain = main.filter(f => !matchesAny(f.family, accepted));
  out.reference = expected.source;
  out.reference_confidence = expected.confidence || null;
  out.expected = required;
  out.accepted_extra = accepted.filter(a => !required.includes(a));
  out.cover = r3(cover);
  out.chart_main = main;
  out.missing = missing;
  out.weak = weak;
  out.unexpected_main = unexpectedMain.map(f => f.family);
  out.unexpected_main_detail = unexpectedMain;
  if (cover < T.chords.fail_cover) { out.status = "fail"; out.reasons.push(`Only ${pct(cover)} of chord time is in the expected families (${required.join(" ")}); the key or the whole chart is probably wrong.`); }
  else if (cover < T.chords.flag_cover) { out.status = "flag"; out.reasons.push(`Only ${pct(cover)} of chord time is in the expected families (${required.join(" ")}).`); }
  if (coreMissing.length) { out.status = worst([out.status, "flag"]); out.reasons.push(`Core expected chord${coreMissing.length > 1 ? "s" : ""} missing from the chart (<${pct(T.chords.missing_below)} of chord time): ${coreMissing.join(" ")}.`); }
  const bigUnexpected = unexpectedMain.filter(f => f.share >= T.chords.flag_unexpected_share);
  if (bigUnexpected.length) { out.status = worst([out.status, "flag"]); out.reasons.push(`Unexpected main chord${bigUnexpected.length > 1 ? "s" : ""}: ${bigUnexpected.map(f => `${f.family} ${pct(f.share)}`).join(", ")}.`); }
  return out;
}
function mainFamilies(byFamily, chordSecs) {
  return [...byFamily].filter(([, s]) => chordSecs > 0 && s / chordSecs >= T.main_family_share)
    .sort((a, b) => b[1] - a[1]).map(([family, s]) => ({ family, share: r3(s / chordSecs) }));
}

// ------------------------------------------------------------------------------------------------ check 2: tempo
/** config: the rhythm fixture entry {start_bpm, tempo_min_bpm?, tempo_max_bpm?, beats_per_bar}. */
function checkTempo(view, config) {
  const out = { status: "pass", reasons: [] };
  const pulse = view.pulseBpm;
  if (!isNum(pulse)) return { status: "pass", note: "no pulse recorded", reasons: [] };
  out.pulse_bpm = r2(pulse);
  const iv = medianInterval(view.beats);
  if (iv) {
    out.implied_bpm = r2(60 / iv);
    const gap = Math.abs(60 / iv - pulse) / pulse;
    const ivs = view.beats.slice(1).map((b, i) => b - view.beats[i]);
    const cv = Math.sqrt(ivs.reduce((s, x) => s + (x - iv) ** 2, 0) / ivs.length) / iv;
    out.interval_cv = r3(cv);
    if (gap > T.tempo.flag_implied_gap) { out.status = worst([out.status, "flag"]); out.reasons.push(`The beat grid's own spacing (${out.implied_bpm} BPM) disagrees with the recorded pulse (${out.pulse_bpm} BPM).`); }
    if (cv > T.tempo.flag_interval_cv) { out.status = worst([out.status, "flag"]); out.reasons.push(`The beat grid is irregular (interval variation ${pct(cv)}).`); }
  }
  if (!config) { out.range = null; out.note = "no rhythm config entry"; return out; }
  const lo = config.tempo_min_bpm, hi = config.tempo_max_bpm, start = config.start_bpm;
  out.start_bpm = start ?? null;
  out.range = isNum(lo) && isNum(hi) ? [lo, hi] : null;
  if (out.range) {
    const below = lo - pulse, above = pulse - hi;
    out.in_range = pulse >= lo * (1 - T.tempo.range_slack) && pulse <= hi * (1 + T.tempo.range_slack);
    if (!out.in_range) {
      const over = Math.max(below / lo, above / hi);
      const st = over > T.tempo.fail_outside ? "fail" : "flag";
      out.status = worst([out.status, st]);
      out.reasons.push(`Pulse ${out.pulse_bpm} BPM is outside the prior range ${lo}-${hi} BPM.`);
    } else if (pulse <= lo * (1 + T.tempo.edge_pin) || pulse >= hi * (1 - T.tempo.edge_pin)) {
      out.edge_pinned = true;
      out.status = worst([out.status, "flag"]);
      out.reasons.push(`Pulse ${out.pulse_bpm} BPM sits on the edge of the prior range ${lo}-${hi} BPM; the range may be clipping the real tempo (half/double-time suspicion).`);
    }
  } else out.note = "no tempo range in the rhythm fixture (default prior); only the start tempo is compared";
  if (isNum(start) && start > 0) {
    const ratio = pulse / start;
    out.ratio_to_start = r2(ratio);
    const near = target => Math.abs(ratio / target - 1) <= T.tempo.ratio_window;
    if (near(0.5) || near(2)) { out.status = worst([out.status, "flag"]); out.reasons.push(`Pulse is ${near(2) ? "double" : "half"} the start tempo (${start} BPM): half/double-time suspicion.`); }
  }
  const runs = familyRuns(view, T.plausibility.blip_beats).filter(r => r.key !== null && r.beats !== null);
  const medHold = median(runs.map(r => r.beats));
  out.median_hold_beats = r2(medHold);
  if (medHold !== null && medHold >= T.tempo.hold_double_median) { out.status = worst([out.status, "flag"]); out.reasons.push(`Median chord hold is ${r2(medHold)} beats: the grid may be running at double the real tempo.`); }
  if (medHold !== null && medHold <= T.tempo.hold_half_median) { out.status = worst([out.status, "flag"]); out.reasons.push(`Median chord hold is ${r2(medHold)} beat: the grid may be running at half the real tempo.`); }
  return out;
}

// ------------------------------------------------------------------------------------------------ check 3: chart plausibility
/** Hold homogeneity on the chart's own long holds. `holds` is the recording's entry in strumalong-hold-checks.json
 *  (hold_homogeneity.py: per hold `start_s`, `beats`, `bars`, `missed_bars`, and `view_source`). Each long run of this check is
 *  matched to the hold-check hold that starts within hold_match_seconds; the evidence is the missed bars over the matched bars.
 *  null without an entry; status "mismatch" when the entry was made from another chart (view source or holds do not line up). */
function holdEvidence(longRuns, holds, viewSource) {
  const P = T.plausibility;
  if (!holds || !Array.isArray(holds.holds)) return null;
  const base = { file_view_source: holds.view_source ?? null, margin: holds.margin ?? null, templates: holds.templates ?? null };
  if (!longRuns.length) return { status: "no long holds", ...base };
  if (holds.view_source && holds.view_source !== viewSource) return { status: "mismatch", note: `made from the ${holds.view_source} chart, checked on the ${viewSource} chart`, ...base };
  let bars = 0, missed = 0;
  const matched = [];
  for (const r of longRuns) {
    const h = holds.holds.find(x => isNum(x.start_s) && Math.abs(x.start_s - r.s) <= P.hold_match_seconds && isNum(x.bars) && isNum(x.missed_bars));
    if (!h) continue;
    bars += h.bars; missed += h.missed_bars;
    matched.push({ start_seconds: r2(r.s), beats: r2(r.beats), family: r.key, bars: h.bars, missed_bars: h.missed_bars });
  }
  if (matched.length < longRuns.length) {
    return { status: "mismatch", note: `${longRuns.length - matched.length} of ${longRuns.length} long holds have no matching hold in the hold-check file; re-run hold_homogeneity.py`, matched_holds: matched.length, ...base };
  }
  return { status: "measured", long_holds: longRuns.length, bars, missed_bars: missed, missed_change_fraction: bars ? r3(missed / bars) : null,
    holds: matched, ...base };
}

function checkPlausibility(view, expected, holds = null) {
  const P = T.plausibility;
  const { byFamily, chordSecs, nSecs, xSecs } = familyShares(view.chords);
  const out = { status: "pass", reasons: [] };
  const dur = view.duration || (view.chords.length ? view.chords[view.chords.length - 1].e : 0);
  out.n_share = r3(dur ? nSecs / dur : 0);
  out.x_share = r3(dur ? xSecs / dur : 0);
  const nx = dur ? (nSecs + xSecs) / dur : 0;
  out.nx_share = r3(nx);
  const runs = familyRuns(view, P.blip_beats).filter(r => r.key !== null && r.beats !== null);
  if (!runs.length || chordSecs <= 0) { out.status = "fail"; out.reasons.push("No chord holds to judge."); return out; }
  const long = runs.filter(r => r.beats >= P.long_hold_beats);
  const longSecs = long.reduce((s, r) => s + (r.e - r.s), 0);
  out.long_hold_share = r3(longSecs / chordSecs);
  out.long_hold_count = long.length;
  const top = runs.reduce((a, b) => (b.beats > a.beats ? b : a));
  out.max_hold_beats = r2(top.beats);
  out.max_hold = { family: top.key, start_seconds: r2(top.s), beats: r2(top.beats) };
  const topFam = [...byFamily].sort((a, b) => b[1] - a[1])[0];
  out.top_family = { family: topFam[0], share: r3(topFam[1] / chordSecs) };
  let longByFam = new Map();
  for (const r of long) longByFam.set(r.key, (longByFam.get(r.key) || 0) + (r.e - r.s));
  const [domFam, domSecs] = [...longByFam].sort((a, b) => b[1] - a[1])[0] || [null, 0];
  out.long_hold_dominant = domFam ? { family: domFam, share_of_chord_time: r3(domSecs / chordSecs) } : null;
  const expFams = expected && expected.families.length ? dedupe(expected.families.map(familyKey).filter(Boolean)) : null;
  const mainCount = mainFamilies(byFamily, chordSecs).length;
  const alternating = expFams ? expFams.length >= 2 : mainCount >= 2;
  out.expected_families = expFams ? expFams.length : null;
  out.progression_basis = expFams ? "expected" : "chart";
  // A long-hold family only matters when the progression alternates: a drone song may hold one chord.
  let absent = [];
  if (expFams) {
    const share = e => { let s = 0; for (const [k, secs] of byFamily) if (familyMatches(k, e)) s += secs; return s / chordSecs; };
    absent = expFams.filter(e => share(e) < P.absent_family_floor);
  }
  out.expected_absent = absent;
  const ev = holdEvidence(long, holds, view.source);
  if (ev) out.hold_evidence = ev;
  const signature = expFams && expFams.length >= 2 && out.long_hold_share >= P.fail_long_share && long.length >= P.fail_long_count && out.max_hold_beats >= P.fail_max_hold_beats;
  out.merge_signature = !!signature;
  if (signature) {
    // The chart shape alone is also what a real vamp or a long intro looks like, so it only flags. It fails when the audio inside
    // the same holds changes chord (hold homogeneity), the second, independent piece of evidence.
    const chart = `${pct(out.long_hold_share)} of chord time sits in ${long.length} single holds of ${P.long_hold_beats}+ beats (longest ${out.max_hold_beats} beats of ${out.max_hold.family}) although the progression has ${expFams.length} families`;
    if (ev && ev.status === "measured" && ev.bars >= P.hold_min_bars && ev.missed_change_fraction >= P.hold_fail_missed) {
      out.status = "fail";
      out.reasons.push(`${chart}, and the audio inside those holds changes chord: in ${ev.missed_bars} of ${ev.bars} bars another main chord fits better than the held one (hold check). The chart probably merges alternating chords.`);
    } else {
      out.status = "flag";
      const why = !ev ? "no hold-homogeneity evidence (run hold_homogeneity.py)"
        : ev.status !== "measured" ? `the hold check does not match this chart (${ev.note})`
        : ev.bars < P.hold_min_bars ? `the hold check measured only ${ev.bars} bars`
        : `the audio inside them mostly stays on the held chord (${ev.missed_bars} of ${ev.bars} bars fit another chord better, under ${pct(P.hold_fail_missed)}), so they may be real vamps or breaks`;
      out.reasons.push(`${chart}; the chart may merge alternating chords, but ${why}.`);
    }
  } else if (alternating && out.long_hold_share >= P.flag_long_share) {
    out.status = "flag";
    out.reasons.push(`${pct(out.long_hold_share)} of chord time sits in holds of ${P.long_hold_beats}+ beats (longest ${out.max_hold_beats} beats of ${out.max_hold.family}).`);
  } else if (out.max_hold_beats >= P.flag_max_hold_beats) {
    out.status = "flag";
    out.reasons.push(`One hold lasts ${out.max_hold_beats} beats (${out.max_hold.family} from ${out.max_hold.start_seconds}s).`);
  }
  if (out.status !== "pass" && absent.length && alternating) out.reasons.push(`Expected chord${absent.length > 1 ? "s" : ""} absent from the chart: ${absent.join(" ")}.`);
  if (nx >= P.fail_nx_share) { out.status = "fail"; out.reasons.push(`${pct(nx)} of the recording is N or X (no chord / unclear).`); }
  else if (nx >= P.flag_nx_share) { out.status = worst([out.status, "flag"]); out.reasons.push(`${pct(nx)} of the recording is N or X (no chord / unclear).`); }
  return out;
}

// ------------------------------------------------------------------------------------------------ check 4: timing consistency
/** Do repeated chord changes fall at the same place in the bar every time?
 *
 *  Definitions (all on family labels, so Em7 = Em and D/F# = D):
 *   - sequence: the chart's chord runs with blips (< 0.75 beat) removed and adjacent equal families merged.
 *   - change: the boundary between two consecutive runs that are both real chords and touch (no N or X between them).
 *   - position: the beat index of the new run's start (fractional, from the beat grid) modulo beats-per-bar, in [0, bpb).
 *     The absolute phase never matters: positions are only compared with other positions of the same change.
 *   - group: every change with the same "from>to" pair. A group is *eligible* when it has at least 4 changes and 60% of them
 *     lie within half a beat of one position, its *usual position* (the circular mean of those inliers).
 *   - deviant: a change in an eligible group 0.75 to 1.5 beats from the group's usual position (about a beat; under 0.5 is
 *     the grid's noise, and half a bar or more is a different placement of the change, counted only as half_bar_placements).
 *     The signed offset is in beats (+1 means a beat late, -1 a beat early).
 *   - shift: three or more consecutive eligible changes (in time) that all deviate in the same direction by about the same
 *     amount. That is a whole stretch of the song sitting a beat off (the grid or the chart slipped), not a one-off mistiming.
 *     The exporter's local bar phases are built to follow such slips; the report says whether they did.
 *   - consistency = 1 - isolated deviants / eligible changes (shift members are excluded from the numerator and reported
 *     as their own share).
 *
 *  This is the founder's "every other time that sequence is played the timing is correct" test: it needs the sequence to
 *  repeat, so it says nothing about a mistiming in a part that is played only once. */
function changeSequence(view) {
  const P = T.plausibility;
  const runs = familyRuns(view, P.blip_beats);
  const sequence = [];
  for (const r of runs) {
    if (r.key !== null && r.beats !== null && r.beats < P.blip_beats) continue;       // a stray frame between two chords
    const prev = sequence[sequence.length - 1];
    if (prev && prev.key === r.key && r.key !== null && gapBeats(prev, r) <= GAP_TOLERANCE_BEATS) { prev.e = r.e; prev.b1 = r.b1; prev.beats = prev.b1 - prev.b0; }
    else sequence.push({ ...r });
  }
  return sequence;
}
function checkConsistency(view) {
  const C = T.consistency;
  const out = { status: "pass", reasons: [] };
  const bpb = view.bpb || 4;
  out.beats_per_bar = bpb;
  out.bpb_assumed = !!view.bpbAssumed;
  out.source = view.source;
  const seq = changeSequence(view);
  const first = view.beats[0], last = view.beats[view.beats.length - 1];
  const changes = [];
  let total = 0, outside = 0;
  for (let i = 1; i < seq.length; i++) {
    const a = seq[i - 1], b = seq[i];
    if (a.key === null || b.key === null || gapBeats(a, b) > GAP_TOLERANCE_BEATS) continue;
    total++;
    if (!(b.s >= first && b.s < last)) { outside++; continue; }
    const beat = Core.beatPosition(view.beats, b.s);
    changes.push({ t: b.s, key: RepeatTiming.pairKey(a.key, b.key), pos: mod(beat, bpb), fromBeats: a.beats, toBeats: b.beats });
  }
  out.changes = total;
  out.positioned = changes.length;
  out.outside_grid = outside;
  // Played timing (lib/repeat-timing.js): usual positions, deviants about a beat off, and shift runs (a stretch sitting a beat off).
  const judged = RepeatTiming.playedJudgement(changes, bpb, C);
  const { eligible, halfBar, shiftIdx, shiftStarts, isolated, groupCount } = judged;
  const shifts = judged.shifts.map(sh => ({ from_seconds: r2(sh.from), to_seconds: r2(sh.to), changes: sh.changes, offset_beats: r2(sh.offsets.reduce((x, y) => x + y, 0) / sh.offsets.length) }));
  out.repeated_groups = groupCount;
  out.eligible_changes = eligible.length;
  out.coverage = changes.length ? r3(eligible.length / changes.length) : 0;
  out.deviants = isolated.length;
  out.half_bar_placements = halfBar;
  out.consistency = judged.consistency === null ? null : r3(judged.consistency);
  out.shift_share = eligible.length ? r3(shiftIdx.size / eligible.length) : 0;
  out.shifts = shifts;
  Object.defineProperty(out, "_eligible", { value: eligible, enumerable: false });     // for withAutoTiming; not serialised
  out.deviant_list = isolated.slice(0, C.list_deviants).map(e => ({ t: r2(e.t), change: e.key, offset_beats: r2(e.offset), from_hold_beats: r2(e.fromBeats), to_hold_beats: r2(e.toBeats) }));
  // Exporter fields, read as they are written: bar anchors (b, a), display corrections (c) and the auto-timing flag (t). Unknown
  // per-chord keys are reported so that a new flag from the exporter is not silently ignored.
  if (view.source === "exported") {
    const raw = view.rawChords || [];
    const known = new Set(["s", "e", "l", "b", "a", "c", "t"]);
    const extra = new Set();
    for (const e of raw) for (const k of Object.keys(e)) if (!known.has(k)) extra.add(k);
    out.exporter = {
      bar_model: view.rhythm?.bar_model ?? null,
      bar_confident_pct: view.rhythm?.bar_confident_pct ?? null,
      anchor_phases: dedupe(raw.filter(e => isNum(e.b)).map(e => e.b)).length,
      approx_anchored_events: raw.filter(e => e.a === 1).length,
      corrected_events: raw.filter(e => e.c === 1).length,
      auto_timed_events: raw.filter(e => e.t).length,
      other_chord_keys: [...extra].sort(),
    };
    // Did the exporter's bar anchors follow each shift? Compare the anchor in force just before the last repeated change ahead of
    // the run with the anchor at the run's first change; a different value means the bar lines moved with the slip (the switch can
    // sit on the chord that starts a long hold, hence "just before").
    const anchorAt = t => { let b = null; for (const e of raw) { if (e.s <= t + 1e-6 && isNum(e.b)) b = e.b; } return b; };
    shifts.forEach((sh, k) => {
      const first = eligible[shiftStarts[k]], before = eligible[shiftStarts[k] - 1];
      sh.anchor_follows = before ? anchorAt(before.t - 0.01) !== anchorAt(first.t) : null;
    });
  }
  if (!changes.length || out.coverage < C.min_coverage || out.consistency === null) {
    out.note = `not enough repeated changes to judge (${eligible.length} of ${changes.length} positioned changes are in repeated groups; need ${pct(C.min_coverage)})`;
    out.evidence = "insufficient";
    return out;
  }
  out.evidence = "sufficient";
  const list = isolated.slice(0, 4).map(e => `${r2(e.t)}s ${e.key} (${e.offset > 0 ? "+" : ""}${r2(e.offset)} beat)`).join(", ");
  if (out.consistency < C.fail_consistency && !view.bpbAssumed) {
    out.status = "fail";
    out.reasons.push(`Only ${pct(out.consistency)} of repeated chord changes sit where the same change usually falls (${isolated.length} of ${eligible.length} are about a beat off); first at ${list}.`);
  } else if (isolated.length >= C.flag_min_deviants) {
    out.status = "flag";
    out.reasons.push(`${isolated.length} of ${eligible.length} repeated chord changes (${pct(1 - out.consistency)}) fall about a beat away from where the same change usually falls${out.bpb_assumed ? " (meter assumed, so bar positions are indicative only)" : ""}; first at ${list}.`);
  }
  // A slip the exporter's bar anchors already follow does not hurt the learner's bar lines; one they do not follow does.
  const unhandled = shifts.filter(sh => sh.anchor_follows !== true);
  out.unhandled_shift_share = eligible.length ? r3(unhandled.reduce((n, sh) => n + sh.changes, 0) / eligible.length) : 0;
  if (unhandled.length && out.unhandled_shift_share >= C.flag_shift_share) {
    out.status = worst([out.status, "flag"]);
    const sh = unhandled.map(s => `${s.from_seconds}-${s.to_seconds}s (${s.changes} changes, ${s.offset_beats > 0 ? "+" : ""}${s.offset_beats} beat${s.anchor_follows === false ? ", the exporter's bar anchors do not follow" : ""})`).join("; ");
    out.reasons.push(`${pct(out.unhandled_shift_share)} of repeated changes sit in stretches that are a steady beat off, a phase slip of the grid or the chart: ${sh}.`);
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ check 5: embed
function checkEmbed(id, evidence) {
  const known = KNOWN_EMBED[id];
  if (known) return { status: known.status, evidence: [known.note], source: known.source, reasons: [known.note] };
  const out = { status: "pass", evidence: [], reasons: [] };
  if (evidence.exported && evidence.exported.playable_embed === false) {
    out.status = "flag";
    const note = `The analysed upload is marked as not embeddable${evidence.exported.embed_note ? `: ${evidence.exported.embed_note}` : ""}.`;
    out.evidence.push(note); out.reasons.push(note);
    return out;
  }
  if (evidence.candidate && evidence.candidate.embed) {
    out.evidence.push(`Candidate fixture records embed "${evidence.candidate.embed}" (${evidence.candidate.fixture}).`);
    out.source = evidence.candidate.fixture;
    if (!/^ok$/i.test(evidence.candidate.embed)) { out.status = "flag"; out.reasons.push(`Candidate fixture records embed "${evidence.candidate.embed}".`); }
    return out;
  }
  if (evidence.fixture_checked) {
    out.evidence.push(`Fixture-level check: ${evidence.fixture_checked.note}`);
    out.source = evidence.fixture_checked.fixture;
    return out;
  }
  return { status: "unknown", evidence: [], reasons: [], note: "no embed check recorded in the repo for this recording" };
}

// ------------------------------------------------------------------------------------------------ check 6: instrument
/** tags: the recording's entry in strumalong-instrument-tags.json, or null. Fields read (docs/STRUMALONG_CATALOGUE_CHECKS.md):
 *   audio_sha256, model, scores (YAMNet, yamnet_tags.py), stems.guitar_share_of_harmonic (Demucs, stems_6s.py) and
 *   strum.{restrike_onbeat, restrike_onbeat_se, onbeat_attacks, single_onbeat, audio_sha256} (strum_features.py).
 *  audioSha: the pack's sha256 of the prepared audio; tags or strum features made from another file are stale and flag.
 *  Two parts, each pass / flag / fail / not run: `guitar_led` and `strummed`. The check's status is the worse of the two. */
function checkInstrument(tags, audioSha = null) {
  const I = T.instrument;
  if (!tags) return { status: "not run", reasons: [], note: "no instrument tags for this recording" };
  const out = { status: "pass", reasons: [], model: tags.model ?? null };
  if (tags.audio_sha256 && audioSha && tags.audio_sha256 !== audioSha) {
    return { status: "flag", reasons: ["The instrument tags were made from a different audio file than the pack's prepared audio; re-run the tagger."], model: tags.model ?? null };
  }
  // --- guitar-led: Demucs guitar share of the harmonic accompaniment, corroborated by YAMNet
  const share = isNum(tags.stems?.guitar_share_of_harmonic) ? tags.stems.guitar_share_of_harmonic : null;
  let scores = tags.scores && typeof tags.scores === "object" ? tags.scores : null;
  const g = { status: "pass", reasons: [], guitar_share_of_harmonic: r3(share) };
  if (tags.scores !== undefined && !scores) { g.status = "flag"; g.reasons.push("Instrument tags carry no scores object."); }
  if (scores) {
    const bad = Object.entries(scores).filter(([, v]) => !isNum(v) || v < 0 || v > 1);
    if (bad.length) { g.status = "flag"; g.reasons.push(`Instrument scores must be in [0,1]; invalid: ${bad.slice(0, 4).map(([k]) => k).join(", ")}.`); scores = null; }
  }
  if (!scores && share === null && !g.reasons.length) { g.status = "not run"; g.note = "no YAMNet scores and no stem statistics"; }
  else {
    const score = k => (scores && isNum(scores[k]) ? scores[k] : 0);
    const guitar = scores ? Math.max(...I.guitar_keys.map(score)) : null;
    const others = scores ? I.other_keys.filter(k => k in scores).map(k => [k, scores[k]]).sort((a, b) => b[1] - a[1]) : [];
    const [lead, leadScore] = others[0] || [null, 0];
    g.yamnet_best_guitar = r3(guitar);
    g.yamnet_lead_other = lead ? { tag: lead, score: r3(leadScore) } : null;
    out.guitar = g.yamnet_best_guitar;                       // kept at the top level for older readers of the report
    out.lead_other = g.yamnet_lead_other;
    const noGuitar = scores !== null && guitar < I.min_guitar;
    const otherAsStrong = scores !== null && lead && leadScore >= I.min_other && leadScore >= guitar;
    const clearLead = scores !== null && lead && leadScore >= I.min_other && leadScore >= guitar + I.fail_margin;
    const lowShare = share !== null && share < I.share_flag;
    if (share !== null && share < I.share_fail && noGuitar) {
      g.status = "fail";
      g.reasons.push(`The Demucs guitar stem is nearly empty (guitar ${pct(share)} of the guitar + piano + other energy) and YAMNet hears no guitar (best guitar tag ${r2(guitar)}): not a guitar-led recording.`);
    } else if (lowShare && clearLead) {
      g.status = "fail";
      g.reasons.push(`Guitar is ${pct(share)} of the harmonic accompaniment and YAMNet hears ${lead} (${r2(leadScore)}) clearly ahead of guitar (${r2(guitar)}): not a guitar-led recording.`);
    } else {
      if (lowShare) g.reasons.push(`Guitar carries only ${pct(share)} of the harmonic accompaniment (Demucs guitar / (guitar + piano + other)); another instrument may lead. Listen.`);
      if (noGuitar) g.reasons.push(`YAMNet hears little guitar (best guitar tag ${r2(guitar)}).`);
      if (!noGuitar && (otherAsStrong || clearLead)) g.reasons.push(`YAMNet hears ${lead} (${r2(leadScore)}) at least as often as guitar (${r2(guitar)}).`);
      if (g.reasons.length) g.status = worst([g.status, "flag"]);
    }
  }
  // --- strummed: on-beat restrike of the guitar stem (strum_features.py)
  const s = tags.strum && typeof tags.strum === "object" ? tags.strum : null;
  const st = { status: "pass", reasons: [] };
  if (!s) { st.status = "not run"; st.note = "no strum features (run strum_features.py)"; }
  else {
    Object.assign(st, { restrike_onbeat: s.restrike_onbeat ?? null, restrike_onbeat_se: s.restrike_onbeat_se ?? null, onbeat_attacks: s.onbeat_attacks ?? null,
      single_onbeat: s.single_onbeat ?? null, version: s.version ?? null });
    if (s.audio_sha256 && audioSha && s.audio_sha256 !== audioSha) {
      st.status = "flag"; st.reasons.push("The strum features were made from a stem of a different audio file than the pack's prepared audio; re-run stems_6s.py and strum_features.py.");
    } else if (g.status === "fail") {
      st.status = "not measured"; st.note = "not guitar-led, so the guitar stem holds mostly bleed from other instruments";
    } else if (!isNum(s.restrike_onbeat) || !isNum(s.onbeat_attacks) || s.onbeat_attacks < I.restrike_min_attacks) {
      st.status = "not measured"; st.note = `too few on-beat guitar attacks (${s.onbeat_attacks ?? 0}; need ${I.restrike_min_attacks})`;
    } else if (s.restrike_onbeat < I.restrike_flag) {
      st.status = "flag";
      st.reasons.push(`On-beat guitar attacks re-strike only ${pct(s.restrike_onbeat)} of the sounding partials (restrike_onbeat ${r3(s.restrike_onbeat)}${isNum(s.restrike_onbeat_se) ? ` ± ${r3(s.restrike_onbeat_se)}` : ""}, flag under ${I.restrike_flag}; the founder-labelled picked and riff songs score 0.58 to 0.63). The recorded guitar may be picked or a riff, or this is dense or distorted strumming (a known false alarm). Listen.`);
    }
  }
  out.guitar_led = g;
  out.strummed = st;
  const parts = [g.status, st.status].filter(x => x === "pass" || x === "flag" || x === "fail");
  out.status = parts.length ? worst(parts) : "not run";
  for (const r of g.reasons) out.reasons.push(`guitar-led: ${r}`);
  for (const r of st.reasons) out.reasons.push(`strummed: ${r}`);
  return out;
}

// ------------------------------------------------------------------------------------------------ combine
/** The overall verdict is the worst status of the checks that ran. "unknown", "not run" and "no reference" never lower it;
 *  they are listed in `not_checked` so that a pass is read as "nothing objected", not "verified". */
function combine(checks) {
  const names = ["chords", "tempo", "plausibility", "consistency", "embed", "instrument"];
  const statuses = names.map(n => checks[n].status).map(s => (s === "pass" || s === "flag" || s === "fail" ? s : "pass"));
  const verdict = worst(statuses);
  const reasons = [], notes = [];
  for (const n of names) for (const r of checks[n].reasons || []) reasons.push(`${n}: ${r}`);
  for (const n of names) for (const r of checks[n].notes || []) notes.push(`${n}: ${r}`);
  const notChecked = [];
  if (checks.chords.reference === "none") notChecked.push("chords (no reference)");
  if (checks.consistency.evidence === "insufficient") notChecked.push("consistency (too few repeated changes)");
  if (checks.embed.status === "unknown") notChecked.push("embed (unknown)");
  if (checks.instrument.status === "not run") notChecked.push("instrument (not run)");
  else {
    const ins = checks.instrument;
    if (ins.guitar_led && ins.guitar_led.status === "not run") notChecked.push("instrument: guitar-led (not run)");
    if (ins.strummed && ins.strummed.status === "not run") notChecked.push("instrument: strummed (not run)");
    if (ins.strummed && ins.strummed.status === "not measured") notChecked.push(`instrument: strummed (not measured: ${ins.strummed.note})`);
  }
  if (checks.plausibility.merge_signature && !(checks.plausibility.hold_evidence && checks.plausibility.hold_evidence.status === "measured")) notChecked.push("plausibility: hold homogeneity (no matching hold check)");
  if (checks.tempo.range === null && checks.tempo.pulse_bpm !== undefined) notChecked.push("tempo range (default prior)");
  return { verdict, reasons, notes, not_checked: notChecked };
}

// ------------------------------------------------------------------------------------------------ loading
function loadInputs(repo = REPO, options = {}) {
  const abs = p => path.resolve(repo, p);
  const rel = p => path.relative(repo, p);
  const cataloguePath = options.catalogue || abs("strumalong/data/catalogue.json");
  const catalogue = readJSON(cataloguePath);
  const excluded = new Map((catalogue.exclude || []).map(x => [x.recording_id, x]));
  const songsDir = options.songsDir || abs("strumalong/songs");
  const index = tryJSON(path.join(songsDir, "index.json"));
  const indexById = new Map((index?.songs || []).map(s => [s.id, s]));
  const sources = [];     // {path, sha256}
  const note = p => { if (fs.existsSync(p)) sources.push({ path: rel(p), sha256: fileSha(p) }); };

  // expected chord files (curated, additions)
  const expectedDir = options.expectedDir || abs("experiments/analysis/strumalong");
  const expectedFiles = ["expected-chords.json", "expected-chords-v2.json", "expected-chords-v3.json", "expected-chords-v4.json"].map(f => path.join(expectedDir, f));
  const expected = new Map();
  for (const f of expectedFiles) {
    const d = tryJSON(f); if (!d) continue;
    note(f);
    for (const [id, v] of Object.entries(d)) expected.set(id, { families: v.sounding || [], accepted: [], confidence: v.confidence || null, source: rel(f) });
  }
  // first ten: teaching chord set at the teaching capo, plus the online-checked sounding palettes as accepted extras
  const reviewPath = options.firstTenReview || abs("catalogue/first-ten-review.json");
  const review = tryJSON(reviewPath);
  const titles = new Map();
  if (review) {
    note(reviewPath);
    for (const s of review.songs || []) {
      const id = s.selected_recording?.recording_id; if (!id) continue;
      titles.set(id, { title: s.title, artist: s.artist });
      const t = s.teaching || {};
      if (Array.isArray(t.chord_set) && t.chord_set.length) {
        const capo = isNum(t.capo) ? t.capo : isNum(t.proposed_capo) ? t.proposed_capo : 0;
        expected.set(id, { families: [...t.chord_set, ...(t.optional_shapes || [])].map(l => Chords.soundingForCapo(l, capo)), accepted: [],
          confidence: `teaching chord set${capo ? ` at capo ${capo}` : ""}; not a complete timed chart`, source: `${rel(reviewPath)} (teaching.chord_set, sounding at capo ${capo})` });
      }
    }
  }
  const onlinePath = options.onlineReviewed || abs("experiments/generated/accompaniment-review-20261018/online-reviewed-v2.json");
  const online = tryJSON(onlinePath);
  if (online) {
    note(onlinePath);
    for (const c of online.cases || []) {
      const ex = expected.get(c.recording?.id); if (!ex) continue;
      const extra = [];
      for (const s of c.sources || []) if (s.comparison_status !== "excluded-source") extra.push(...(s.sounding_chords || []));
      ex.accepted = dedupe(extra);
      if (extra.length) ex.source += ` + ${rel(onlinePath)} (sounding_chords as accepted extras)`;
    }
  }

  // candidate fixtures (titles, artists, embed)
  const candidates = new Map();
  const fixtureChecked = [];
  for (const name of ["strumalong-additions-candidates-v1.json", "strumalong-additions-candidates-v2.json", "strumalong-additions-candidates-v4.json"]) {
    const f = options.fixturesDir ? path.join(options.fixturesDir, name) : abs("experiments/fixtures/" + name);
    const d = tryJSON(f); if (!d) continue;
    note(f);
    const fixture = rel(f);
    for (const list of [d.first_picks || [], d.fallbacks_in_order || []]) for (const x of list) {
      if (!x.recording_id) continue;
      candidates.set(x.recording_id, { title: x.title, artist: x.artist, embed: x.embed || null, fixture, checked: d.checked || null });
    }
    fixtureChecked.push({ fixture, checked: d.checked || "", ids: new Set((d.first_picks || []).map(x => x.recording_id).filter(Boolean)) });
  }

  // rhythm configs (tempo priors)
  const rhythmConfig = new Map();
  for (const name of ["rhythm-first-ten.json", "rhythm-strumalong-additions-v1.json", "rhythm-strumalong-additions-v2.json", "rhythm-strumalong-additions-v4.json", "rhythm-strumalong-additions-v4b.json"]) {
    const f = options.fixturesDir ? path.join(options.fixturesDir, name) : abs("experiments/fixtures/" + name);
    const d = tryJSON(f); if (!d) continue;
    note(f);
    for (const [id, v] of Object.entries(d.recordings || {})) rhythmConfig.set(id, v);
  }

  // instrument tags (optional)
  const instrumentPath = options.instrumentTags || abs("experiments/generated/strumalong-instrument-tags.json");
  const instrumentRaw = tryJSON(instrumentPath);
  let instrument = null, instrumentSha = null;
  if (instrumentRaw) {
    instrumentSha = fileSha(instrumentPath);
    const map = instrumentRaw.recordings && typeof instrumentRaw.recordings === "object" ? instrumentRaw.recordings : instrumentRaw;
    instrument = new Map(Object.entries(map).filter(([, v]) => v && typeof v === "object" && !Array.isArray(v)).map(([id, v]) => [id, { ...v, model: v.model ?? instrumentRaw.model ?? null }]));
  }

  // hold homogeneity (optional; hold_homogeneity.py). Keyed by recording id; a {recordings: {...}} wrapper is accepted too.
  const holdPath = options.holdChecks || abs("experiments/generated/strumalong-hold-checks.json");
  const holdRaw = tryJSON(holdPath);
  let holdChecks = null, holdSha = null;
  if (holdRaw && typeof holdRaw === "object") {
    holdSha = fileSha(holdPath);
    const map = holdRaw.recordings && typeof holdRaw.recordings === "object" ? holdRaw.recordings : holdRaw;
    holdChecks = new Map(Object.entries(map).filter(([, v]) => v && typeof v === "object" && Array.isArray(v.holds)));
  }

  // packs
  const packs = [];
  const recordings = [];
  for (const pack of catalogue.packs || []) {
    const dir = abs(pack.dir), manifestPath = path.join(dir, "manifest.json"), rhythmPath = abs(pack.rhythm);
    const manifest = tryJSON(manifestPath), rhythm = tryJSON(rhythmPath);
    if (!manifest || !rhythm) { packs.push({ id: pack.id, dir: pack.dir, available: false }); continue; }
    note(manifestPath); note(rhythmPath);
    packs.push({ id: pack.id, dir: pack.dir, available: true, cases: manifest.cases.length, manifest_sha256: fileSha(manifestPath), rhythm_sha256: fileSha(rhythmPath) });
    const rhythmById = new Map((rhythm.cases || []).map(c => [c.recording?.id, c]));
    for (const c of manifest.cases) {
      const id = c.id;
      const primaryPath = path.join(dir, "cases", id, "primary.json");
      const primary = tryJSON(primaryPath);
      recordings.push({ id, pack: pack.id, caseName: c.name, duration: c.recording?.duration_seconds, audioSha: c.recording?.audio_sha256 ?? null, primary, primarySha: fileSha(primaryPath), rhythm: rhythmById.get(id) || null });
    }
  }

  // exported songs (only read for recordings present in the index, i.e. built)
  const exported = new Map();
  for (const rec of recordings) {
    const f = path.join(songsDir, `${rec.id}.json`);
    const s = tryJSON(f);
    if (s && s.schema && Array.isArray(s.chords)) exported.set(rec.id, { song: s, sha256: fileSha(f) });
  }

  return {
    catalogue, cataloguePath, excluded, index, indexById, indexSha: fileSha(path.join(songsDir, "index.json")),
    expected, candidates, fixtureChecked, rhythmConfig, instrument, instrumentPath: instrumentRaw ? rel(instrumentPath) : null, instrumentSha,
    holdChecks, holdPath: holdChecks ? rel(holdPath) : null, holdSha,
    packs, recordings, exported, titles, sources, rel,
  };
}

/** The view of the pack's raw CREMA chart on the pack's beat grid (no display corrections, no exporter timing fixes). */
function buildPackView(rec, inputs) {
  const chords = (rec.primary?.chords || []).map(c => ({ s: c.start_seconds, e: c.end_seconds, l: c.label }));
  const bpbRaw = rec.rhythm?.beats_per_bar;
  return { id: rec.id, source: "pack", duration: rec.duration, chords, beats: rec.rhythm?.beat_times_seconds || [], bpb: bpbRaw || 4,
    bpbAssumed: bpbRaw === null || bpbRaw === undefined, pulseBpm: rec.rhythm?.pulse_bpm ?? null };
}
/** What the exporter says it moved: chart.corrections entries of kind "timing" (id "auto-timing") and the per-chord flag `t`. */
function exporterAutoTiming(song) {
  const read = RepeatTiming.readCorrections(song);
  if (!read) return null;
  return { moves: read.moves, flagged_events: read.flagged, note: read.note, details: read.list.slice(0, 12) };
}
/** Build the view the checks run on: the exported song when there is one (what the learner sees, display corrections and the
 *  exporter's timing fixes included), else the pack's raw CREMA chart on the pack's beat grid. */
function buildView(rec, inputs) {
  const ex = inputs.exported.get(rec.id);
  const cfg = inputs.rhythmConfig.get(rec.id);
  if (ex) {
    const s = ex.song;
    return { id: rec.id, source: "exported", duration: s.recording?.duration_seconds ?? rec.duration,
      chords: s.chords.map(c => ({ s: c.s, e: c.e, l: c.l })), rawChords: s.chords, beats: s.beats || [], bpb: s.rhythm?.beats_per_bar || 4,
      bpbAssumed: !!(s.rhythm?.beats_per_bar_assumed) || cfg?.beats_per_bar === null, pulseBpm: rec.rhythm?.pulse_bpm ?? s.rhythm?.bpm ?? null,
      rhythm: s.rhythm, autoTiming: exporterAutoTiming(s) };
  }
  return buildPackView(rec, inputs);
}

function songMeta(rec, inputs) {
  const ex = inputs.exported.get(rec.id)?.song;
  const card = inputs.indexById.get(rec.id);
  const cand = inputs.candidates.get(rec.id);
  const tt = inputs.titles.get(rec.id);
  const exc = inputs.excluded.get(rec.id);
  return {
    title: ex?.title || card?.title || cand?.title || tt?.title || exc?.title || rec.caseName || rec.id,
    artist: ex?.artist || card?.artist || cand?.artist || tt?.artist || "",
  };
}

/** The exporter fixes mistimed repeated changes itself (auto-timing). The verdict is about what ships, so it is judged on the
 *  exported timeline; but a fix that agrees with its group by construction proves nothing, so the raw chart is analysed too and
 *  both are reported. Many moves mean the chart leans heavily on the fix and flag. */
function withAutoTiming(consistency, view, rawView) {
  const C = T.consistency;
  const raw = checkConsistency(rawView);
  const total = view.autoTiming.moves || view.autoTiming.flagged_events;
  const share = consistency.positioned ? total / consistency.positioned : 0;
  // Independent read on each move. The exporter's `shift` is in beat-bucket units, so a move can be a snap of a fraction of a beat or
  // a whole beat. Per move: how far the change was from its group's usual position in the raw chart (this check's measure), how far
  // the exporter moved it, and where it ends up.
  const iv = medianInterval(rawView.beats) || 0.5;
  const moves = (view.autoTiming.details || []).map(m => {
    const hit = raw._eligible.find(e => isNum(m.was) && Math.abs(e.t - m.was) < 0.06);
    const moved = isNum(m.at) && isNum(m.was) ? (m.at - m.was) / iv : null;
    const before = hit ? hit.offset : null;
    return { at: m.at ?? null, was: m.was ?? null, change: m.from && m.to ? `${m.from}>${m.to}` : null, shift_buckets: m.shift ?? null, agree: m.agree ?? null,
      moved_beats: moved === null ? null : r2(moved), raw_offset_beats: before === null ? null : r2(before),
      offset_after_beats: before === null || moved === null ? null : r2(before + moved) };
  });
  const measured = moves.filter(m => m.raw_offset_beats !== null && m.moved_beats !== null);
  const fullBeat = moves.filter(m => m.moved_beats !== null && Math.abs(m.moved_beats) >= C.deviant_beats);
  const confirmed = measured.filter(m => Math.abs(m.raw_offset_beats) >= C.deviant_beats && Math.abs(m.offset_after_beats) < Math.abs(m.raw_offset_beats)).length;
  const worsened = measured.filter(m => Math.abs(m.offset_after_beats) > Math.abs(m.raw_offset_beats) + C.worse_beats).length;
  consistency.auto_timing = {
    moves: view.autoTiming.moves, flagged_events: view.autoTiming.flagged_events, share: r3(share), exporter_note: view.autoTiming.note,
    raw_chart: { status: raw.status, eligible_changes: raw.eligible_changes, deviants: raw.deviants, shifts: raw.shifts.length, deviant_list: raw.deviant_list },
    shipped_deviants: consistency.deviants,
    moves_measured: measured.length, full_beat_moves: fullBeat.length, moves_that_fix_a_mistiming: confirmed, moves_that_made_it_worse: worsened,
    details: moves,
  };
  if (worsened >= C.flag_worsened_moves) {
    consistency.status = worst([consistency.status, "flag"]);
    consistency.reasons.push(`${worsened} of the exporter's auto-timing moves put a change further from its group's usual position than the raw chart had it (by ${C.worse_beats}+ beat).`);
  }
  const notes = consistency.notes || (consistency.notes = []);
  if (fullBeat.length || raw.deviants >= 2 || share >= 0.05) {
    const measurable = measured.length ? `${confirmed} of the ${measured.length} moves it can measure fix a change that was about a beat off` : "none of the moves is in a group large enough to measure";
    notes.push(`The exporter's auto-timing moved ${total} repeated change${total === 1 ? "" : "s"} (${fullBeat.length} by a whole beat, the rest small snaps). By this check's own measure the raw chart has ${raw.deviants} isolated mistimed change${raw.deviants === 1 ? "" : "s"} and the shipped timeline ${consistency.deviants}; ${measurable}.`);
  }
  if (share >= C.flag_auto_timing_share) {
    consistency.status = worst([consistency.status, "flag"]);
    consistency.reasons.push(`${pct(share)} of the chord changes needed the exporter's auto-timing fix; the chart leans heavily on it.`);
  }
}

function checkRecording(rec, inputs) {
  const view = buildView(rec, inputs);
  const expected = inputs.expected.get(rec.id) || null;
  const exc = inputs.excluded.get(rec.id);
  const cand = inputs.candidates.get(rec.id) || null;
  const fixtureChecked = inputs.fixtureChecked.find(f => f.ids.has(rec.id));
  const embedEvidence = {
    exported: inputs.indexById.get(rec.id) || null,
    candidate: cand && cand.embed ? { embed: cand.embed, fixture: cand.fixture } : null,
    fixture_checked: fixtureChecked && /playability OK/i.test(fixtureChecked.checked) ? { fixture: fixtureChecked.fixture, note: fixtureChecked.checked.split(";")[0] } : null,
  };
  const consistency = checkConsistency(view);
  if (view.autoTiming) withAutoTiming(consistency, view, buildPackView(rec, inputs));
  const checks = {
    chords: checkChords(view, expected),
    tempo: checkTempo(view, inputs.rhythmConfig.get(rec.id) || null),
    plausibility: checkPlausibility(view, expected, inputs.holdChecks ? inputs.holdChecks.get(rec.id) || null : null),
    consistency,
    embed: checkEmbed(rec.id, embedEvidence),
    instrument: checkInstrument(inputs.instrument ? inputs.instrument.get(rec.id) || null : null, rec.audioSha),
  };
  const { verdict, reasons, notes, not_checked } = combine(checks);
  const meta = songMeta(rec, inputs);
  const shipped = !exc;
  const row = { recording_id: rec.id, title: meta.title, artist: meta.artist, pack: rec.pack, shipped, ...(exc ? { excluded_reason: exc.reason } : {}),
    exported: inputs.exported.has(rec.id), view_source: view.source, chart_sha256: rec.primarySha, exported_sha256: inputs.exported.get(rec.id)?.sha256 ?? null,
    checks, verdict, reasons, notes, not_checked };
  return row;
}

function runChecks(repo = REPO, options = {}) {
  const inputs = loadInputs(repo, options);
  const songs = inputs.recordings.map(rec => checkRecording(rec, inputs));
  // Excluded ids that name no recording in any available pack are reported so that a typo or a missing pack is visible.
  const known = new Set(inputs.recordings.map(r => r.id));
  const unmatchedExclusions = [...inputs.excluded.keys()].filter(id => !known.has(id));
  const summary = { recordings: songs.length, shipped: songs.filter(s => s.shipped).length, excluded: songs.filter(s => !s.shipped).length };
  for (const group of ["shipped", "excluded"]) for (const v of ["pass", "flag", "fail"]) summary[`${group}_${v}`] = songs.filter(s => (group === "shipped") === s.shipped && s.verdict === v).length;
  const report = {
    schema: SCHEMA,
    generated_from: {
      catalogue: { path: inputs.rel(inputs.cataloguePath), sha256: fileSha(inputs.cataloguePath) },
      packs: inputs.packs,
      files: inputs.sources.sort((a, b) => a.path.localeCompare(b.path)),
      songs_index_sha256: inputs.indexSha,
      exported_songs: songs.filter(s => s.exported).length,
      instrument_tags: inputs.instrumentPath ? { path: inputs.instrumentPath, sha256: inputs.instrumentSha } : null,
      hold_checks: inputs.holdPath ? { path: inputs.holdPath, sha256: inputs.holdSha } : null,
    },
    thresholds: T,
    summary,
    unmatched_exclusions: unmatchedExclusions,
    songs,
  };
  return report;
}

// ------------------------------------------------------------------------------------------------ output
function table(report) {
  const col = (s, n) => String(s).padEnd(n).slice(0, n);
  const mark = c => {
    const s = c.status;
    if (s === "pass" && c.auto_timing && c.auto_timing.raw_chart.deviants > c.auto_timing.shipped_deviants) return "fixed";
    return s === "pass" ? "pass" : s === "flag" ? "FLAG" : s === "fail" ? "FAIL" : s === "unknown" ? "?" : s === "not run" ? "-" : s;
  };
  const lines = [];
  lines.push(`${col("Song", 56)} ${col("Ship", 4)} ${col("Chords", 7)} ${col("Tempo", 6)} ${col("Plaus", 6)} ${col("Timing", 7)} ${col("Embed", 6)} ${col("Instr", 6)} Verdict`);
  for (const s of report.songs) {
    const c = s.checks;
    const chords = c.chords.reference === "none" ? "no ref" : mark(c.chords);
    lines.push(`${col(`${s.title} - ${s.artist}`, 56)} ${col(s.shipped ? "yes" : "no", 4)} ${col(chords, 7)} ${col(mark(c.tempo), 6)} ${col(mark(c.plausibility), 6)} ${col(c.consistency.evidence === "insufficient" ? "few" : mark(c.consistency), 7)} ${col(mark(c.embed), 6)} ${col(mark(c.instrument), 6)} ${s.verdict.toUpperCase()}`);
  }
  lines.push("");
  const m = report.summary;
  lines.push(`Shipped ${m.shipped}: ${m.shipped_pass} pass, ${m.shipped_flag} flag, ${m.shipped_fail} fail. Excluded ${m.excluded}: ${m.excluded_pass} pass, ${m.excluded_flag} flag, ${m.excluded_fail} fail.`);
  for (const s of report.songs) if (s.reasons.length || (s.notes || []).length) {
    lines.push(`\n${s.verdict.toUpperCase()}  ${s.title} (${s.artist})${s.shipped ? "" : "  [excluded]"}`);
    for (const r of s.reasons) lines.push(`  - ${r}`);
    for (const n of s.notes || []) lines.push(`  . ${n}`);
  }
  return lines.join("\n");
}

/** The summary as a markdown table (docs/STRUMALONG_CATALOGUE_CHECKS.md carries a snapshot; refresh with --markdown). */
function markdownTable(report) {
  const cell = c => {
    if (c.reference === "none") return "no ref";
    if (c.evidence === "insufficient") return "few";
    if (c.status === "pass" && c.auto_timing && c.auto_timing.raw_chart.deviants > c.auto_timing.shipped_deviants) return "fixed";
    return { pass: "pass", flag: "**FLAG**", fail: "**FAIL**", unknown: "?", "not run": "-" }[c.status] || c.status;
  };
  const cut = (text, n) => (text.length > n ? text.slice(0, n - 1) + "…" : text);
  const lines = ["| Song | Ships | Chords | Tempo | Plausibility | Timing | Embed | Instrument | Verdict | Flagged by |", "|---|---|---|---|---|---|---|---|---|---|"];
  for (const s of report.songs) {
    const c = s.checks;
    const by = ["chords", "tempo", "plausibility", "consistency", "embed", "instrument"].filter(n => c[n].status === "flag" || c[n].status === "fail").map(n => (n === "consistency" ? "timing" : n));
    lines.push(`| ${cut(s.title, 38)} (${cut(s.artist, 24)}) | ${s.shipped ? "yes" : "no"} | ${cell(c.chords)} | ${cell(c.tempo)} | ${cell(c.plausibility)} | ${cell(c.consistency)} | ${cell(c.embed)} | ${cell(c.instrument)} | ${s.verdict === "pass" ? "pass" : `**${s.verdict.toUpperCase()}**`} | ${by.join(", ") || "-"} |`);
  }
  return lines.join("\n");
}

function main(argv, env = process.env) {
  const flag = f => argv.includes(f);
  // CATALOGUE_CHECKS_REPO points the whole run at another tree (the tests use a synthetic one); the default is this checkout.
  const repo = env.CATALOGUE_CHECKS_REPO ? path.resolve(env.CATALOGUE_CHECKS_REPO) : REPO;
  const outIdx = argv.indexOf("--out");
  const outPath = outIdx >= 0 ? path.resolve(argv[outIdx + 1]) : path.join(repo, "docs/STRUMALONG_CATALOGUE_CHECKS.json");
  const report = runChecks(repo);
  const text = JSON.stringify(report, null, 2) + "\n";
  if (flag("--check")) {
    const disk = fs.existsSync(outPath) ? fs.readFileSync(outPath, "utf8") : null;
    if (disk !== text) { console.error(`CHECK FAILED: ${path.relative(repo, outPath)} is ${disk === null ? "missing" : "stale"}; run catalogue_checks.js to regenerate.`); return 1; }
    console.log("CHECK OK: catalogue-checks.json is current.");
  } else if (!flag("--no-write")) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, text);
  }
  if (flag("--json")) process.stdout.write(text);
  else if (flag("--markdown")) console.log(markdownTable(report));
  else console.log(table(report));
  const shippedFail = report.songs.filter(s => s.shipped && s.verdict === "fail");
  const shippedFlag = report.songs.filter(s => s.shipped && s.verdict === "flag");
  if (shippedFail.length) { console.error(`\n${shippedFail.length} shipped song(s) fail a hard gate: ${shippedFail.map(s => s.title).join(", ")}`); return 1; }
  if (flag("--strict") && shippedFlag.length) { console.error(`\n--strict: ${shippedFlag.length} shipped song(s) flagged: ${shippedFlag.map(s => s.title).join(", ")}`); return 1; }
  return 0;
}

module.exports = {
  T, SCHEMA, INSTRUMENT_SCHEMA, KNOWN_EMBED,
  parseChord, familyKey, familyMatches, familyRuns, familyShares, beatAt,
  checkChords, checkTempo, checkPlausibility, holdEvidence, checkConsistency, changeSequence, checkEmbed, checkInstrument, combine,
  loadInputs, buildView, buildPackView, exporterAutoTiming, checkRecording, runChecks, table, markdownTable, main,
};

if (require.main === module) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { console.error(`catalogue_checks: ${error && error.message ? error.message : error}`); process.exitCode = 2; }
}
