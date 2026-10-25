/* Strum Along core: pure timeline, cue and strum helpers (no DOM, no network).
 * UMD: window.StrumCore in the browser, module.exports under node.
 * Spec: docs/STRUMALONG_APP.md, section "lib/core.js API".
 * Charts are provisional automatic drafts, beats come from an estimated grid and
 * bars are approximate. Nothing here verifies downbeats or recorded strumming. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.StrumCore = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  function validNumber(value) { return typeof value === "number" && Number.isFinite(value); }
  function mod(value, n) { return ((value % n) + n) % n; }
  const hasOwn = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

  // Ported from experiments/review/app.js line 181 (transposePracticeLabel). Behaviour unchanged.
  function transposePracticeLabel(label, capo) {
    if (!Number.isInteger(capo) || capo < 0 || capo > 12) throw new Error("Use a capo fret from 0 to 12.");
    if (typeof label !== "string" || !capo || label === "N" || label === "X") return label;
    const notes = { C: 0, "B#": 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4,
      "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11 };
    const sharp = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const flat = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
    const shifted = (note, preferFlat = false) => (note.includes("b") || preferFlat ? flat : sharp)[(notes[note] - capo + 12) % 12];
    const parsed = /^([A-G](?:#|b)?)([^/]*)(?:\/(.*))?$/.exec(label);
    if (!parsed || !(parsed[1] in notes)) return label;
    const bass = parsed[3] === undefined ? "" : "/" + (/^[A-G](?:#|b)?$/.test(parsed[3]) && parsed[3] in notes ? shifted(parsed[3], parsed[1].includes("b")) : parsed[3]);
    return shifted(parsed[1]) + parsed[2] + bass;
  }

  // Ported from experiments/review/app.js line 195 (coreChordLabel). Behaviour unchanged;
  // Object.hasOwn is replaced by an equivalent own-property check.
  function coreChordLabel(label) {
    if (typeof label !== "string") return label;
    // Reduce only explicit, known qualities. Suspensions do not contain a major
    // or minor third, so they must not become ordinary major/minor chords.
    const parsed = /^([A-G](?:#|b)?)([^/]*)(\/(?:[A-G](?:#|b)?|[b#]?[1-7]))?$/.exec(label);
    if (!parsed) return label;
    const qualities = { m7: "m", min7: "m", minor7: "m", maj7: "", major7: "", add9: "", add2: "", "7": "", "7sus4": "sus4", "7sus": "sus4",
      "maj(9)": "", "maj(add9)": "", "(1,3,5,9)": "", "sus4(b7)": "sus4" };
    const suffix = parsed[2].replace(/^:/, "");
    if (!hasOwn(qualities, suffix)) return label;
    return parsed[1] + qualities[suffix] + (parsed[3] || "");
  }

  function capoFret(value) { return Number.isInteger(value) && value >= 0 && value <= 12 ? value : 0; }

  // Shape (what the left hand holds) or sounding label, in Core ("Simple") or Full quality.
  // Equivalent to experiments/review/app.js practiceLabel (line 207) with renamed options.
  function shapeLabel(sounding, opts) {
    const o = opts || {};
    const shape = o.view === "sounding" ? sounding : transposePracticeLabel(sounding, capoFret(o.capo));
    return o.quality === "full" ? shape : coreChordLabel(shape);
  }

  function displayLabel(label) {
    if (label === "N") return "No chord";
    if (label === "X") return "Unclear";
    return typeof label === "string" && label ? label : "—";
  }

  // Display events {s,e,label,full,sounding,c}. Adjacent equal labels merge after the
  // transforms (core reduction can make G7 + G one hold). N and X never merge.
  function buildTimeline(song, opts) {
    const o = opts || {};
    const capo = capoFret(Number.isInteger(o.capo) ? o.capo : song && song.capo);
    const view = o.view === "sounding" ? "sounding" : "shapes";
    const quality = o.quality === "full" ? "full" : "core";
    const out = [];
    const chords = song && Array.isArray(song.chords) ? song.chords : [];
    let previousEnd = -Infinity;
    for (const chord of chords) {
      if (!chord || !validNumber(chord.s) || !validNumber(chord.e) || chord.e <= chord.s || typeof chord.l !== "string") continue;
      if (chord.s < previousEnd - 1e-6) continue; // overlapping/out-of-order events are dropped, never reordered
      previousEnd = chord.e;
      const full = shapeLabel(chord.l, { capo, view, quality: "full" });
      const label = quality === "core" ? coreChordLabel(full) : full;
      const prev = out[out.length - 1];
      if (prev && label !== "N" && label !== "X" && prev.label === label && Math.abs(prev.e - chord.s) < 1e-3) {
        prev.e = chord.e;
        if (chord.c) prev.c = 1;
        continue;
      }
      out.push({ s: chord.s, e: chord.e, label, full, sounding: chord.l, c: chord.c ? 1 : 0 });
    }
    return out;
  }

  // Binary search: index of the event with s <= t < e, or -1 (before, after or in a gap).
  function chordIndexAt(events, t) {
    if (!Array.isArray(events) || !events.length || !validNumber(t)) return -1;
    let low = 0, high = events.length - 1;
    while (low <= high) {
      const middle = (low + high) >> 1, event = events[middle];
      if (t < event.s) high = middle - 1;
      else if (t >= event.e) low = middle + 1;
      else return middle;
    }
    return -1;
  }

  // Ported from experiments/review/app.js line 306 (beatPosition). Behaviour unchanged.
  function beatPosition(beats, seconds) {
    if (!Array.isArray(beats) || beats.length < 2) return null;
    if (!validNumber(seconds) || seconds < beats[0] || seconds > beats[beats.length - 1]) return null;
    if (seconds === beats[beats.length - 1]) return beats.length - 1;
    let low = 0, high = beats.length - 1;
    while (low + 1 < high) { const middle = Math.floor((low + high) / 2); if (beats[middle] <= seconds) low = middle; else high = middle; }
    return low + (seconds - beats[low]) / (beats[low + 1] - beats[low]);
  }

  // beatPosition with the grid extended by one beat interval at each end, so a chord
  // that starts a few frames before the first estimated beat (or a final strum just
  // after the last one) still gets beat dots. Further out it is null (seconds fallback).
  function gridPosition(beats, seconds) {
    const strict = beatPosition(beats, seconds);
    if (strict !== null || !Array.isArray(beats) || beats.length < 2 || !validNumber(seconds)) return strict;
    const n = beats.length;
    const first = beats[1] - beats[0], last = beats[n - 1] - beats[n - 2];
    if (seconds < beats[0] && first > 0 && beats[0] - seconds <= first) return (seconds - beats[0]) / first;
    if (seconds > beats[n - 1] && last > 0 && seconds - beats[n - 1] <= last) return n - 1 + (seconds - beats[n - 1]) / last;
    return null;
  }

  function rhythmInfo(song) {
    const rhythm = (song && song.rhythm) || {};
    const bpb = Number.isInteger(rhythm.beats_per_bar) && rhythm.beats_per_bar > 0 ? rhythm.beats_per_bar : 4;
    const phaseKnown = Number.isInteger(rhythm.bar_phase);
    const info = {
      bpb,
      phase: phaseKnown ? mod(rhythm.bar_phase, bpb) : 0,
      confident: rhythm.bar_phase_confident === true && phaseKnown,
      bpm: validNumber(rhythm.bpm) && rhythm.bpm > 0 ? rhythm.bpm : null,
      beats: song && Array.isArray(song.beats) ? song.beats : [],
    };
    info.anchors = anchorMap(song, info);
    return info;
  }

  // ---- Bar anchors (docs/STRUMALONG_APP.md, "Bar model").
  // The exporter writes a compact per-chord anchor: `b` = bar phase (beat residue mod beats_per_bar that starts a
  // bar while this chord is held) and `a: 1` when that anchor is approximate. Every grid beat takes the anchor of
  // the chord whose dots own it (round(startBeat) .. round(endBeat) - 1, the same rounding as the dots), so the drawn
  // bar lines and the strum count read one per-beat anchor and can never disagree. Beats no chord owns take the
  // nearest owned beat's anchor (earlier first). A song without `b` fields keeps the single song-wide
  // rhythm.bar_phase (approximate unless rhythm.bar_phase_confident), exactly as before.
  const anchorCache = typeof WeakMap === "function" ? new WeakMap() : null;
  function anchorMap(song, info) {
    const chords = song && Array.isArray(song.chords) ? song.chords : [];
    const cached = anchorCache && song && typeof song === "object" ? anchorCache.get(song) : null;
    if (cached && cached.beats === info.beats && cached.chords === chords && cached.bpb === info.bpb &&
      cached.phase0 === info.phase && cached.confident === info.confident) return cached;
    const n = info.beats.length;
    const map = { beats: info.beats, chords, bpb: info.bpb, phase0: info.phase, confident: info.confident,
      phase: null, approx: null, anchored: false };
    if (n >= 2) {
      const phase = new Array(n + 2).fill(-1), approx = new Array(n + 2).fill(false); // slot = beat index + 1 (beats -1..n)
      for (const chord of chords) {
        if (!chord || !Number.isInteger(chord.b) || !validNumber(chord.s) || !validNumber(chord.e)) continue;
        const sb = gridPosition(info.beats, chord.s), eb = gridPosition(info.beats, chord.e);
        if (sb === null || eb === null || !(eb > sb)) continue;
        const lo = Math.max(-1, Math.round(sb)), hi = Math.min(n + 1, Math.round(eb));
        for (let beat = lo; beat < hi; beat++) { phase[beat + 1] = mod(chord.b, info.bpb); approx[beat + 1] = chord.a === 1; map.anchored = true; }
      }
      if (map.anchored) {
        let last = -1, lastApprox = false;
        for (let i = 0; i < phase.length; i++) {
          if (phase[i] >= 0) { last = phase[i]; lastApprox = approx[i]; } else if (last >= 0) { phase[i] = last; approx[i] = lastApprox; }
        }
        for (let i = phase.length - 1; i >= 0; i--) {
          if (phase[i] >= 0) { last = phase[i]; lastApprox = approx[i]; } else { phase[i] = last; approx[i] = lastApprox; }
        }
        map.phase = phase; map.approx = approx;
      }
    }
    if (anchorCache && song && typeof song === "object") anchorCache.set(song, map);
    return map;
  }
  function slotOf(map, beat) { return Math.max(0, Math.min(map.phase.length - 1, beat + 1)); }
  function phaseAtBeat(info, beat) {
    const map = info.anchors;
    return map && map.anchored && Number.isInteger(beat) ? map.phase[slotOf(map, beat)] : info.phase;
  }
  function approxAtBeat(info, beat) {
    const map = info.anchors;
    return map && map.anchored && Number.isInteger(beat) ? map.approx[slotOf(map, beat)] : !info.confident;
  }
  function isBarBeat(info, beat) { return mod(beat - phaseAtBeat(info, beat), info.bpb) === 0; }

  // The anchor in force at grid beat `beat` (an integer index; -1 and beats.length are the one-beat extensions).
  // bar: the strum count reads 1 on this beat (a drawn bar line, or a hold that starts a bar).
  function barAnchorAt(song, beat) {
    const info = rhythmInfo(song);
    const b = Number.isInteger(beat) ? beat : Math.floor(Number(beat));
    if (!Number.isInteger(b)) return null;
    const phase = phaseAtBeat(info, b), offset = mod(b - phase, info.bpb);
    return { phase, approx: approxAtBeat(info, b), bar: offset === 0, half: info.bpb % 2 === 0 && offset === info.bpb / 2,
      anchored: Boolean(info.anchors && info.anchors.anchored) };
  }

  const QUICK_BEATS = 0.75;

  function kindOf(label) { return label === "N" ? "none" : label === "X" ? "unclear" : "chord"; }

  // One cue column (NOW or NEXT). `active` is the absolute dot index of the current
  // beat inside this hold (-1 for NEXT).
  function cuePart(event, idx, info, t, isNow) {
    const part = {
      idx, kind: kindOf(event.label), label: event.label, display: displayLabel(event.label),
      full: event.full, sounding: event.sounding, c: event.c ? 1 : 0, s: event.s, e: event.e,
      seconds: event.e - event.s, remaining: isNow ? Math.max(0, event.e - t) : event.e - event.s,
      startBeat: null, endBeat: null, spanBeats: null, beats: null, active: -1,
      dots: [], dotOffset: 0, barBefore: [], more: 0, quick: false, barStart: null, approx: null,
    };
    const sb = gridPosition(info.beats, event.s), eb = gridPosition(info.beats, event.e);
    if (sb === null || eb === null || eb <= sb) {
      // Outside the beat grid: seconds only.
      const beatSeconds = info.bpm ? 60 / info.bpm : 0.5;
      part.quick = part.seconds < QUICK_BEATS * beatSeconds;
      return part;
    }
    const span = eb - sb, base = Math.round(sb);
    // Dots run from round(startBeat) to round(endBeat), so each grid beat belongs to exactly one hold.
    // A hold that owns no grid beat after rounding (e.g. 0.87 beat from 30.52 to 31.39) is a quick change too.
    const owned = Math.round(eb) - base;
    const quick = span < QUICK_BEATS || owned < 1;
    const count = quick ? 1 : owned;
    part.startBeat = sb; part.endBeat = eb; part.spanBeats = span; part.beats = count; part.quick = quick;
    // Bar lines and the strum count read the same per-beat anchor (see anchorMap). An approximate anchor
    // still draws its lines (labelled "approx bars") but gives NEXT no solid bar-start border.
    const isBar = k => isBarBeat(info, base + k);
    part.approx = approxAtBeat(info, base);
    part.barStart = part.approx ? null : isBar(0);
    if (isNow) {
      const bt = gridPosition(info.beats, t);
      part.active = bt === null ? 0 : Math.min(count - 1, Math.max(0, Math.floor(bt) - base));
    }
    const cap = 2 * info.bpb;
    let offset = 0;
    if (count > cap && part.active > 0) {
      // Keep the active beat in the first shown bar, with one bar of look-ahead.
      let barStartK = 0;
      for (let k = part.active; k > 0; k--) if (isBar(k)) { barStartK = k; break; }
      offset = Math.min(barStartK, count - cap);
    }
    const shown = Math.min(cap, count - offset);
    for (let j = 0; j < shown; j++) {
      const k = offset + j;
      part.dots.push({ state: part.active < 0 || k > part.active ? "future" : k === part.active ? "active" : "past" });
      if (j > 0 && isBar(k)) part.barBefore.push(j);
    }
    part.dotOffset = offset;
    part.more = count - offset - shown;
    return part;
  }

  function pseudoPart(kind, display) {
    return { idx: -1, kind, label: null, display, full: null, sounding: null, c: 0, s: null, e: null,
      seconds: null, remaining: null, startBeat: null, endBeat: null, spanBeats: null, beats: null, active: -1,
      dots: [], dotOffset: 0, barBefore: [], more: 0, quick: false, barStart: null, approx: null };
  }

  // Cue model for the layout A panel at cue time t (seconds on the analysed recording).
  function cueAt(timeline, song, t) {
    const info = rhythmInfo(song);
    const events = Array.isArray(timeline) ? timeline : [];
    const time = validNumber(t) ? t : 0;
    const bt = gridPosition(info.beats, time);
    const result = { t: time, beat: bt, now: null, next: null, beatsUntilChange: null, secondsUntilChange: null,
      inBeatGrid: false, toEnd: false, approxBars: bt === null ? !info.confident : approxAtBeat(info, Math.floor(bt)),
      beatsPerBar: info.bpb };
    if (!events.length) { result.now = pseudoPart("empty", "—"); return result; }
    const idx = chordIndexAt(events, time);
    let nextIdx;
    if (idx >= 0) {
      result.now = cuePart(events[idx], idx, info, time, true);
      nextIdx = idx + 1;
    } else if (time < events[0].s) {
      result.now = pseudoPart("before", "Get ready");
      nextIdx = 0;
    } else if (time >= events[events.length - 1].e) {
      result.now = pseudoPart("end", "End");
      return result;
    } else {
      nextIdx = events.findIndex(event => event.s > time);
      result.now = pseudoPart("gap", "—");
    }
    if (nextIdx >= 0 && nextIdx < events.length) {
      result.next = cuePart(events[nextIdx], nextIdx, info, time, false);
    }
    const now = result.now;
    if (now.idx >= 0) {
      result.secondsUntilChange = Math.max(0, now.e - time);
      result.toEnd = result.next === null;
      if (now.dots.length && bt !== null) {
        result.inBeatGrid = true;
        result.beatsUntilChange = now.beats - now.active;
      }
    } else if (result.next) {
      result.secondsUntilChange = Math.max(0, result.next.s - time);
      if (bt !== null && result.next.startBeat !== null) {
        result.beatsUntilChange = Math.max(1, Math.round(result.next.startBeat) - Math.floor(bt));
      }
    }
    return result;
  }

  // Index into pattern.strokes at time t, or null outside the (one-beat-extended) grid.
  function strumStep(song, pattern, t) {
    if (!pattern || !Array.isArray(pattern.strokes) || !pattern.strokes.length) return null;
    const info = rhythmInfo(song);
    const beat = gridPosition(info.beats, t);
    if (beat === null) return null;
    const counts = Array.isArray(pattern.counts) && pattern.counts.length ? pattern.counts.length : pattern.strokes.length;
    const stepsPerBeat = counts / info.bpb;
    // Same per-beat anchor as the drawn bar lines: the beat that owns this moment decides where count 1 is.
    const pos = mod(beat - phaseAtBeat(info, Math.floor(beat + 1e-9)), info.bpb);
    const step = Math.floor(pos * stepsPerBeat + 1e-9);
    return Math.min(pattern.strokes.length - 1, Math.max(0, step));
  }

  const EASY_SHAPES = new Set(["A", "Am", "C", "D", "Dm", "E", "Em", "G"]);
  const HALF_SHAPES = new Set(["F", "Bm", "B7"]);

  // Capo suggestion for the exporter: share of chord seconds on easy open shapes.
  function suggestCapo(chords) {
    const list = Array.isArray(chords) ? chords : [];
    const scores = [];
    for (let capo = 0; capo <= 7; capo++) {
      let total = 0, credit = 0;
      for (const chord of list) {
        if (!chord) continue;
        const label = typeof chord.l === "string" ? chord.l : typeof chord.sounding === "string" ? chord.sounding : chord.label;
        const s = validNumber(chord.s) ? chord.s : chord.start, e = validNumber(chord.e) ? chord.e : chord.end;
        if (typeof label !== "string" || label === "N" || label === "X" || !validNumber(s) || !validNumber(e) || e <= s) continue;
        const seconds = e - s;
        total += seconds;
        const shape = transposePracticeLabel(label, capo).split("/")[0];
        const core = coreChordLabel(shape);
        if (EASY_SHAPES.has(core)) credit += seconds;
        else if (HALF_SHAPES.has(core) || HALF_SHAPES.has(shape)) credit += seconds / 2;
      }
      scores.push(total > 0 ? credit / total : 0);
    }
    const best = Math.max(...scores);
    const capo = scores.findIndex(score => score >= best - 0.03);
    return { capo, score: scores[capo], scores };
  }

  // Mirrors experiments/review/app.js line 635 (timeLabel): "m:ss".
  function formatTime(seconds) {
    const whole = validNumber(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
  }

  function strokeGlyph(stroke) { return stroke === "D" ? "↓" : stroke === "U" ? "↑" : "·"; }

  // Cue time on the analysed recording: player clock + the video's known offset +
  // the user's per-video nudge (ms) − global output latency (ms, e.g. Bluetooth).
  // Latency is wall-clock delay, so it covers latency × rate of media time at a playback
  // rate other than 1. The nudge and offset are media time and are not scaled.
  function cueTime(playerSeconds, offsetSeconds, nudgeMs, latencyMs, rate) {
    const p = validNumber(playerSeconds) ? playerSeconds : 0;
    const r = validNumber(rate) && rate > 0 ? rate : 1;
    return p + (validNumber(offsetSeconds) ? offsetSeconds : 0) + (validNumber(nudgeMs) ? nudgeMs : 0) / 1000 -
      (validNumber(latencyMs) ? latencyMs : 0) / 1000 * r;
  }

  function expectedDuration(song, video) {
    if (video && validNumber(video.duration_seconds) && video.duration_seconds > 0) return video.duration_seconds;
    const recording = song && song.recording;
    return recording && validNumber(recording.duration_seconds) ? recording.duration_seconds : null;
  }

  // Ad / wrong-video guard: true when the player reports a duration that differs from the
  // expected upload by more than the tolerance. Unknown durations (0, NaN) never trip it.
  function durationMismatch(playerDuration, expected, tolerance) {
    if (!validNumber(playerDuration) || playerDuration <= 0 || !validNumber(expected) || expected <= 0) return false;
    return Math.abs(playerDuration - expected) > (validNumber(tolerance) ? tolerance : 3);
  }

  return { transposePracticeLabel, coreChordLabel, shapeLabel, displayLabel, buildTimeline, chordIndexAt, beatPosition,
    gridPosition, barAnchorAt, cueAt, strumStep, suggestCapo, formatTime, strokeGlyph, cueTime, expectedDuration, durationMismatch };
});
