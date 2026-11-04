/* Strum Along count-in (#60): a one-bar count at the song's own tempo that leads into a bar start, then
 * clicks that carry on and fade out over the first bar of the music (founder request, 27 October 2026).
 * UMD: window.StrumCountIn in the browser, module.exports under node. Pure: no DOM, audio or timers.
 * Needs lib/core.js (window.StrumCore) for bar anchors; load it first.
 * All times are chart (cue) seconds. app.js converts to player time, runs the clock and plays the clicks.
 * The beat grid is estimated and bar starts are approximate, so the count is too. */
(function (root, factory) {
  "use strict";
  const node = typeof module !== "undefined" && module.exports;
  const api = factory(node ? require("./core.js") : root.StrumCore);
  if (node) module.exports = api;
  if (root) root.StrumCountIn = api;
})(typeof window !== "undefined" ? window : null, function (Core) {
  "use strict";

  const LEAD_S = 0.4;           // playback starts this long before the first count beat
  const EARLY_S = 0.08;         // a bar start this close before the start point still counts as "at" it
  const FADE_GAINS = [0.6, 0.42, 0.26, 0.12]; // clicks over the first bar of the music; the count itself is 1
  const num = value => typeof value === "number" && Number.isFinite(value);

  // Grid beat i in seconds. The estimated grid is extended at both ends by its own edge spacing (the median of
  // the first or last few intervals), so a count can run before the first estimated beat, even before 0.
  function grid(song) {
    const beats = song && Array.isArray(song.beats) ? song.beats.filter(num) : [];
    const rhythm = (song && song.rhythm) || {};
    if (beats.length >= 2) {
      const n = beats.length;
      const median = list => list.slice().sort((a, b) => a - b)[Math.floor(list.length / 2)];
      const gaps = beats.slice(1).map((b, i) => b - beats[i]).filter(g => g > 0);
      if (!gaps.length) return null;
      const head = median(gaps.slice(0, 8)), tail = median(gaps.slice(-8));
      return {
        at: i => i < 0 ? beats[0] + i * head : i >= n ? beats[n - 1] + (i - n + 1) * tail : beats[i],
        // Index of the first grid beat at or after t.
        from(t) {
          if (t <= beats[0]) return -Math.floor((beats[0] - t) / head);
          if (t > beats[n - 1]) return n - 1 + Math.ceil((t - beats[n - 1]) / tail);
          let lo = 0, hi = n - 1;
          while (lo + 1 < hi) { const mid = (lo + hi) >> 1; if (beats[mid] < t) lo = mid; else hi = mid; }
          return beats[lo] >= t ? lo : hi;
        },
      };
    }
    if (num(rhythm.bpm) && rhythm.bpm > 0) {
      const period = 60 / rhythm.bpm;
      return { at: i => i * period, from: t => Math.ceil(t / period) };
    }
    return null;
  }

  // The count for a start at chart time `from`: the bar start `downbeat` at or after it, `count` (the bar before
  // it, numbered 1..beats-per-bar), `fade` (the first bar of the music, with falling gains) and `startAt`
  // (where playback should begin; it can be before the video's 0, in which case app.js pre-rolls).
  // Null when the song has no usable tempo.
  function plan(song, from) {
    const g = grid(song);
    if (!g || !num(from)) return null;
    const rhythm = (song && song.rhythm) || {};
    const bpb = Number.isInteger(rhythm.beats_per_bar) && rhythm.beats_per_bar > 0 ? rhythm.beats_per_bar : 4;
    let d = g.from(from - EARLY_S);
    for (let k = 0; k < bpb && !isBar(song, d); k++) d++;
    const count = [], fade = [];
    for (let k = 0; k < bpb; k++) count.push({ t: g.at(d - bpb + k), n: k + 1, gain: 1 });
    for (let k = 0; k < bpb; k++) fade.push({ t: g.at(d + k), n: 0, gain: FADE_GAINS[Math.min(k, FADE_GAINS.length - 1)] });
    return { downbeat: g.at(d), count, fade, clicks: count.concat(fade), startAt: count[0].t - LEAD_S };
  }
  function isBar(song, beat) {
    const anchor = Core.barAnchorAt(song, beat);
    return !anchor || anchor.bar;
  }

  // Which clicks to schedule now. `next` is the index of the first unscheduled click, `t` the current chart time.
  // A click within `lookahead` seconds is due, with `delay` = how far ahead it is in chart seconds (divide by
  // the playback rate for wall time). A click already more than `late` seconds behind is skipped silently.
  function due(clicks, next, t, lookahead, late) {
    const fire = [];
    let i = next;
    while (i < clicks.length && clicks[i].t <= t + lookahead) {
      if (clicks[i].t >= t - late) fire.push({ click: clicks[i], delay: Math.max(0, clicks[i].t - t) });
      i++;
    }
    return { fire, next: i, done: i >= clicks.length };
  }

  return { plan, due, LEAD_S };
});
