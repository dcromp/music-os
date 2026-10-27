/* Strum Along repeat timing: do repeated chord changes land on a consistent beat?
 * UMD: window.StrumRepeatTiming in the browser, module.exports under node. No DOM, no network.
 * Spec: docs/STRUMALONG_APP.md ("Timing fix") and docs/adr/0001-repeat-timing-two-measures.md.
 *
 * Pop songs repeat their chord sequences with the same bar placement, so the repeats of a change are its timing
 * reference. A caller turns its timeline into positioned changes ({key, pos, ...}); this module groups them by key and
 * judges each against its group. Two measures, deliberately different (ADR 0001):
 *   - drawn:  pos is the integer beat the app draws, under the exporter's bar anchors. The usual position is the most
 *             common one; any other is off. The exporter's timing fix moves one-beat-off changes on this measure.
 *   - played: pos is the fractional beat-grid position. The usual position is the densest circular cluster; a change
 *             about a beat from it is a deviant. The catalogue checker's verdict uses this measure.
 * Most drawn-off changes sit well under a beat from their repeats in the grid: they round to another beat. Played
 * ignores those and finds changes that really sit a beat away. Neither is a verified timing reference.
 *
 * It also owns the shape of the exporter's "auto-timing" chart.corrections entry: correction() builds it,
 * readCorrections() and describe() read it. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.StrumRepeatTiming = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  const mod = (value, n) => ((value % n) + n) % n;
  const r1 = x => Math.round(x * 10) / 10;
  function median(values) {
    const v = [...values].sort((a, b) => a - b), n = v.length;
    return n ? (n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2) : 0;
  }

  /** Changes by key, in input order. */
  function groupByKey(changes) {
    const groups = new Map();
    for (const ch of changes) {
      if (!groups.has(ch.key)) groups.set(ch.key, []);
      groups.get(ch.key).push(ch);
    }
    return groups;
  }

  // ---------------------------------------------------------------- drawn timing (exporter)

  /** The drawn key: the 4-chord context (previous two, this, next) of the change into labels[i]; ^ and $ pad the ends. */
  const contextKey = (labels, i) => [i >= 2 ? labels[i - 2] : "^", labels[i - 1], labels[i], i + 1 < labels.length ? labels[i + 1] : "$"].join(" ");

  /**
   * Groups of 2+ changes with the same key. changes: {key, pos (integer drawn bar position), lenA, lenB (drawn beats of
   * the two holds), frac (offset from the drawn beat)}. group: {key, members, mode, agree, share, typA, typB, frac}:
   * mode = most common position (ties to the lowest), agree = members at it; typA/typB/frac = medians over those.
   */
  function drawnGroups(changes) {
    const groups = new Map();
    for (const [key, members] of groupByKey(changes)) {
      if (members.length < 2) continue;
      const tally = new Map();
      for (const ch of members) tally.set(ch.pos, (tally.get(ch.pos) || 0) + 1);
      const [mode, agree] = [...tally].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
      const at = members.filter(ch => ch.pos === mode);
      groups.set(key, { key, members, mode, agree, share: agree / members.length, typA: median(at.map(ch => ch.lenA)),
        typB: median(at.map(ch => ch.lenB)), frac: median(at.map(ch => ch.frac)) });
    }
    return groups;
  }

  /** Share of changes in groups of minRepeats+ (default 3) at their group's usual position: {repeated, consistent, pct}. */
  function drawnConsistency(groups, minRepeats = 3) {
    let repeated = 0, consistent = 0;
    for (const g of groups.values()) {
      if (g.members.length < minRepeats) continue;
      repeated += g.members.length; consistent += g.agree;
    }
    return { repeated, consistent, pct: repeated ? r1(100 * consistent / repeated) : 100 };
  }

  /** How far a drawn position is from its group's: d = beats after the mode (mod bpb); shift = the one-beat move that
   *  would join the mode (-1 earlier, +1 later), 0 when it is not one beat away. */
  function drawnOffset(pos, mode, bpb) {
    const d = mod(pos - mode, bpb);
    return { d, shift: d === 1 ? -1 : d === bpb - 1 ? 1 : 0 };
  }

  // ---------------------------------------------------------------- played timing (catalogue checker)

  /** The played key: the from>to chord-family pair. */
  const pairKey = (from, to) => `${from}>${to}`;

  const circDiff = (a, b, n) => { const d = mod(a - b, n); return d > n / 2 ? d - n : d; };      // a - b wrapped to (-n/2, n/2]

  /** The densest cluster of positions on a circle of length n: {centre, inliers, spread}. */
  function usualPosition(positions, n, tol) {
    let best = null;
    for (const p of positions) {
      const inliers = positions.filter(q => Math.abs(circDiff(q, p, n)) <= tol);
      const centre = mod(p + inliers.reduce((s, q) => s + circDiff(q, p, n), 0) / inliers.length, n);
      const spread = inliers.reduce((s, q) => s + Math.abs(circDiff(q, centre, n)), 0);
      if (!best || inliers.length > best.inliers.length || (inliers.length === best.inliers.length && spread < best.spread)) best = { centre, inliers, spread };
    }
    return best;
  }

  /**
   * Judge positioned changes ({t, key, pos (fractional, mod bpb), ...}) against their repeats.
   * settings: {min_group, min_majority, inlier_beats, deviant_beats, half_bar_beats, min_shift_run}.
   *   - eligible: members of groups with min_group+ changes and min_majority of them within inlier_beats of one
   *     position (the usual position), in time order, each with offset (signed beats from it) and usual.
   *   - deviant: an eligible change deviant_beats .. min(half_bar_beats, bpb/2 - 0.25) from its usual position. Further
   *     away is a different placement (half_bar), not a mistiming.
   *   - shifts: min_shift_run+ consecutive deviants in one direction by about the same amount (a slip of the grid or
   *     the chart, not a one-off); shiftStarts/shiftIdx index into eligible.
   *   - isolated: deviants outside shifts. consistency = 1 - isolated / eligible (null with nothing eligible).
   */
  function playedJudgement(changes, bpb, settings) {
    const C = settings;
    const eligible = [];
    let groupCount = 0;
    for (const members of groupByKey(changes).values()) {
      if (members.length < C.min_group) continue;
      const u = usualPosition(members.map(m => m.pos), bpb, C.inlier_beats);
      if (u.inliers.length / members.length < C.min_majority) continue;
      groupCount++;
      for (const m of members) eligible.push({ ...m, offset: circDiff(m.pos, u.centre, bpb), usual: u.centre });
    }
    eligible.sort((x, y) => x.t - y.t);
    // On a 2-beat bar a one-beat offset is already a half bar, so no mistiming can be reported there.
    const upper = Math.min(C.half_bar_beats, bpb / 2 - 0.25);
    const isDev = e => Math.abs(e.offset) >= C.deviant_beats && Math.abs(e.offset) < upper;
    const halfBar = eligible.filter(e => Math.abs(e.offset) >= Math.max(upper, C.deviant_beats)).length;
    const shiftIdx = new Set(), shifts = [], shiftStarts = [];
    for (let i = 0; i < eligible.length;) {
      if (!isDev(eligible[i])) { i++; continue; }
      let j = i + 1;
      while (j < eligible.length && isDev(eligible[j]) && Math.sign(eligible[j].offset) === Math.sign(eligible[i].offset) && Math.abs(eligible[j].offset - eligible[i].offset) <= 0.75) j++;
      if (j - i >= C.min_shift_run) {
        for (let k = i; k < j; k++) shiftIdx.add(k);
        shifts.push({ from: eligible[i].t, to: eligible[j - 1].t, changes: j - i, offsets: eligible.slice(i, j).map(e => e.offset) });
        shiftStarts.push(i);
      }
      i = j;
    }
    const isolated = eligible.filter((e, i) => isDev(e) && !shiftIdx.has(i));
    return { groupCount, eligible, isDev, halfBar, shifts, shiftStarts, shiftIdx, isolated,
      consistency: eligible.length ? 1 - isolated.length / eligible.length : null };
  }

  // ---------------------------------------------------------------- the auto-timing correction

  const isTiming = c => Boolean(c) && (c.kind === "timing" || c.id === "auto-timing");

  /** The one chart.corrections entry that summarises the timing fix's moves ({at, was, from, to, shift, agree}); null
   *  when nothing moved. */
  function correction(moves) {
    if (!moves.length) return null;
    const n = moves.length;
    return { id: "auto-timing", kind: "timing", count: n,
      start: Math.min(...moves.map(m => Math.min(m.at, m.was))), end: Math.max(...moves.map(m => Math.max(m.at, m.was))),
      note: `${n} chord change${n === 1 ? "" : "s"} moved by one beat to match the other repeats of the same sequence (automatic; raw chart unchanged)`,
      moves: moves.map(({ at, was, from, to, shift, agree }) => ({ at, was, from, to, shift, agree })) };
  }

  /** What an exported song says the timing fix moved: {entries, moves (count), flagged (chords with t), note, list}, or
   *  null when it has neither a timing entry nor a flagged chord. */
  function readCorrections(song) {
    const entries = ((song && song.chart && song.chart.corrections) || []).filter(isTiming);
    const flagged = ((song && song.chords) || []).filter(e => e.t).length;
    if (!entries.length && !flagged) return null;
    const isNum = x => typeof x === "number" && Number.isFinite(x);
    return { entries, flagged,
      moves: entries.reduce((n, c) => n + (isNum(c.count) ? c.count : Array.isArray(c.moves) ? c.moves.length : 0), 0),
      note: entries.map(c => c.note).filter(Boolean)[0] || null,
      list: entries.flatMap(c => (Array.isArray(c.moves) ? c.moves : [])) };
  }

  /** A timing entry for display: {note, moves: [{at, from, to, direction: "earlier" | "later"}]}; null for any other
   *  correction. */
  function describe(c) {
    if (!isTiming(c)) return null;
    return { note: c.note || "Some chord changes moved by one beat",
      moves: (Array.isArray(c.moves) ? c.moves : []).map(m => ({ at: m.at, from: m.from, to: m.to, direction: m.shift < 0 ? "earlier" : "later" })) };
  }

  return { contextKey, drawnGroups, drawnConsistency, drawnOffset, pairKey, usualPosition, playedJudgement,
    isTiming, correction, readCorrections, describe };
});
