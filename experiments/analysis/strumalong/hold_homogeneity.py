#!/usr/bin/env python
"""Hold homogeneity: does the audio inside a long chart hold really stay on the held chord?

Run with an environment that has numpy, soundfile and librosa (the CREMA one):

    .venv-crema/bin/python experiments/analysis/strumalong/hold_homogeneity.py [--only ID[,ID...]] [--margin 0.10] [--min-hold-beats 16]

Why: the automatic chart sometimes merges chords that alternate every bar into one long hold (A Horse with No Name: Em shown for
up to 46 beats while the song alternates Em / D6add9-F# every bar). catalogue_checks.js flags long holds from the chart alone. This
looks at the audio inside each long hold and asks whether another of the song's main chords fits a bar better than the held one.
catalogue_checks.js reads this file: its merge signature fails only when 25%+ of the bars inside its own 24+ beat holds (12+ bars,
holds matched by start time within 1 s) are missed changes here; otherwise it flags.

For every recording in strumalong/data/catalogue.json (shipped and excluded):

1. Chart. If strumalong/songs/<id>.json is exported, its sounding chords, beats and beats_per_bar are used (`view_source:
   "exported"`, what ships, including the exporter's corrections). Otherwise the pack's primary.json chords on the pack's
   rhythm.json beats (`"pack"`, the raw CREMA draft; 4 beats a bar when the pack has no meter).
2. Holds. A hold is a run of one chord family (root + triad kind, as catalogue_checks.js `familyKey`), with N and X breaking it
   and a blip under 0.75 beat between two runs of the same family absorbed. A long hold is >= --min-hold-beats (16) beats.
   The held chord is the hold's time-weighted most common label (Em7 stays Em7).
3. Main chords. Chart families covering at least 4% of chord time; each is represented by its most common label. These are the
   candidates the held chord is compared against.
4. Bars. Inside a long hold, bars of beats_per_bar beats counted from the hold start (the chart's own change point); a partial
   bar at the end is dropped. Each bar's chroma is the sum of the CQT chroma frames (librosa chroma_cqt, harmonic part of the
   audio, norm=None so loud strums dominate) over the bar's inner 80% (10% trimmed at each end, away from the change).
5. Score. Pearson correlation between the bar's 12-bin chroma and a binary template (1 on the label's pitch classes, slash bass
   included; qualities maj, min, 7, m7, maj7, sus, add9, 6, 6add9, 9, 5, dim, aug are known). `--templates claim` (default): the
   held chord is judged exactly as the chart labels it (Em7 stays {E G B D}) against the best colour variant of every other main
   chord (D, D6, D7, Dmaj7, Dadd9, D6add9 ...). A bar is a **missed change** when the best rival's correlation beats the held
   chord's by more than --margin (default 0.10, Pearson r). missed_change_fraction = missed bars / bars inside long holds (null
   when there are no such bars). `--templates variants` gives the held chord its best colour variant too, `label` uses chart
   labels only. `sensitivity` repeats the fraction at margins 0.05, 0.10, 0.15 and 0.20.

   Known blind spot: chords with nearly the same pitch classes (relative major/minor with colour tones, e.g. G6 against Em7, or
   Em7 against D6add9 with the open E and B strings ringing) are close on any chroma template; `claim` mode can call a coloured
   chord a missed change, and `variants` mode explains an alternation away. Treat the number as a ranking signal, not a verdict.

Output experiments/generated/strumalong-hold-checks.json (gitignored), keyed by recording id: long_holds (count), bars,
missed_change_fraction, examples (the bars with the largest margins), plus per-hold detail, main chords and the parameters.
Nothing is modified apart from that file. No lyrics, no network.
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strumalong_common import (HOLDS_PATH, SONGS_DIR, STEMS_DIR, chord_pitch_classes, family_key,  # noqa: E402
                               load_recordings, parse_only, read_json, write_json_atomic)

MIN_HOLD_BEATS = 16
MARGIN = 0.10
MAIN_SHARE = 0.04
BLIP_BEATS = 0.75
TRIM = 0.10
SENSITIVITY = (0.05, 0.10, 0.15, 0.20)
HOP = 512
MAX_EXAMPLES = 8


# ------------------------------------------------------------------------------------------------ beats and holds
def median_interval(beats):
    b = np.asarray(beats, dtype=float)
    return float(np.median(np.diff(b))) if len(b) >= 2 else None


def beat_position(beats, t):
    """Fractional beat index at time t, extrapolating at the median interval outside the grid (None for fewer than 2 beats)."""
    b = np.asarray(beats, dtype=float)
    iv = median_interval(b)
    if iv is None or iv <= 0:
        return None
    if t < b[0]:
        return -(b[0] - t) / iv
    if t > b[-1]:
        return len(b) - 1 + (t - b[-1]) / iv
    return float(np.interp(t, b, np.arange(len(b))))


def beat_time(beats, x):
    """Inverse of beat_position."""
    b = np.asarray(beats, dtype=float)
    iv = median_interval(b)
    if x < 0:
        return float(b[0] + x * iv)
    if x > len(b) - 1:
        return float(b[-1] + (x - (len(b) - 1)) * iv)
    return float(np.interp(x, np.arange(len(b)), b))


def family_runs(chords, beats, blip_beats=BLIP_BEATS):
    """Mirror of catalogue_checks.js familyRuns. chords: [{s, e, l}]. -> runs {key, s, e, b0, b1, beats, labels{label: seconds}}."""
    runs = []
    for c in chords:
        key = family_key(c["l"])
        last = runs[-1] if runs else None
        if last and key is not None and last["key"] == key and abs(last["e"] - c["s"]) < 0.25:
            last["e"] = c["e"]
            last["labels"][c["l"]] += c["e"] - c["s"]
        else:
            runs.append({"key": key, "s": c["s"], "e": c["e"], "labels": Counter({c["l"]: c["e"] - c["s"]})})
    for r in runs:
        r["b0"], r["b1"] = beat_position(beats, r["s"]), beat_position(beats, r["e"])
        r["beats"] = None if r["b0"] is None else r["b1"] - r["b0"]
    out = []
    for i, r in enumerate(runs):
        prev = out[-1] if out else None
        nxt = runs[i + 1] if i + 1 < len(runs) else None
        if (r["key"] is not None and r["beats"] is not None and r["beats"] < blip_beats and prev and nxt
                and prev["key"] is not None and prev["key"] == nxt["key"]):
            continue                                   # a stray frame between two runs of one family
        gap = (r["b0"] - prev["b1"]) if (prev and prev["b1"] is not None and r["b0"] is not None) else None
        if prev and r["key"] is not None and prev["key"] == r["key"] and gap is not None and gap <= 0.8:
            prev["e"], prev["b1"] = r["e"], r["b1"]
            prev["beats"] = prev["b1"] - prev["b0"]
            prev["labels"].update(r["labels"])
        else:
            out.append(r)
    return out


def long_holds(runs, min_beats=MIN_HOLD_BEATS):
    return [r for r in runs if r["key"] is not None and r["beats"] is not None and r["beats"] >= min_beats]


def main_chords(chords, share=MAIN_SHARE):
    """-> {family_key: {"label": most common label, "share": share of chord time, "seconds": s}} for families >= share."""
    secs, labels = defaultdict(float), defaultdict(Counter)
    for c in chords:
        k = family_key(c["l"])
        if k is None:
            continue
        d = c["e"] - c["s"]
        secs[k] += d
        labels[k][c["l"]] += d
    total = sum(secs.values())
    if total <= 0:
        return {}
    ordered = sorted(secs, key=lambda k: -secs[k])
    return {k: {"label": labels[k].most_common(1)[0][0], "share": secs[k] / total, "seconds": secs[k]}
            for k in ordered if secs[k] / total >= share}


# ------------------------------------------------------------------------------------------------ templates and scoring
# Colour tones a strummed chord of each family may carry. In "variants" mode a family is scored by its best-fitting variant, for the
# held chord and the rivals alike, so Em7 versus D6add9 is judged on D6add9's own notes, not on a bare D triad.
VARIANT_SUFFIXES = {
    "": ["", "6", "7", "maj7", "add9", "6add9"],
    "m": ["m", "m6", "m7", "madd9"],
    "sus": ["sus4", "sus2", "7sus4"],
    "5": ["5"],
    "dim": ["dim", "dim7", "m7b5"],
    "aug": ["aug"],
}


def family_variants(key):
    """Chord labels of a family key ("D" -> D, D6, D7, Dmaj7, Dadd9, D6add9)."""
    root, kind = (key[:2], key[2:]) if len(key) > 1 and key[1] == "#" else (key[:1], key[1:])
    return [root + suffix for suffix in VARIANT_SUFFIXES.get(kind, [kind])]


def template_vector(label):
    pcs = chord_pitch_classes(label)
    if pcs is None:
        return None
    v = np.zeros(12)
    v[pcs] = 1.0
    return v


def pearson(x, t):
    x = np.asarray(x, dtype=float) - np.mean(x)
    t = np.asarray(t, dtype=float) - np.mean(t)
    d = float(np.sqrt((x @ x) * (t @ t)))
    return 0.0 if d <= 1e-12 else float(x @ t / d)


def best_fit(chroma_vec, labels):
    """-> (best label, its Pearson correlation) over candidate chord labels."""
    best = None
    for label in labels:
        t = template_vector(label)
        if t is None:
            continue
        r = pearson(chroma_vec, t)
        if best is None or r > best[1]:
            best = (label, r)
    return best


def score_bar(chroma_vec, held, rivals, mode="claim"):
    """held: (family_key, label); rivals: {family_key: label}.
    mode "claim" (default): the held chord is judged as the chart labels it (its own label's template) against the best colour
    variant of every other main chord; "variants": the held chord also gets its best colour variant; "label": every chord is only
    its chart label.
    -> (held label, held r), (winner key, winner label, winner r) or None, margin = winner r - held r (None without rivals)."""
    def labels_of(key, label, is_held):
        if mode == "variants" or (mode == "claim" and not is_held):
            return family_variants(key)
        return [label]

    held_fit = best_fit(chroma_vec, labels_of(*held, True))
    best = None
    for key, label in rivals.items():
        fit = best_fit(chroma_vec, labels_of(key, label, False))
        if fit and (best is None or fit[1] > best[2]):
            best = (key, fit[0], fit[1])
    if held_fit is None or best is None:
        return held_fit, best, None
    return held_fit, best, best[2] - held_fit[1]


def bar_windows(beats, b0, b1, bpb):
    """Bars of bpb beats counted from b0 while they fit before b1. -> [(start_time, end_time)]."""
    n = int(np.floor((b1 - b0) / bpb + 1e-9))
    return [(beat_time(beats, b0 + k * bpb), beat_time(beats, b0 + (k + 1) * bpb)) for k in range(n)]


def window_chroma(chroma, sr, hop, t0, t1, trim=TRIM):
    """Sum of chroma frames over the inner part of [t0, t1]; None when no frame falls inside."""
    pad = (t1 - t0) * trim
    f0, f1 = int(np.ceil((t0 + pad) * sr / hop)), int(np.floor((t1 - pad) * sr / hop))
    f0, f1 = max(f0, 0), min(f1, chroma.shape[1] - 1)
    if f1 < f0:
        return None
    return chroma[:, f0:f1 + 1].sum(axis=1)


def analyse_holds(chords, beats, bpb, chroma, sr, hop, margin=MARGIN, min_hold_beats=MIN_HOLD_BEATS, mode="claim"):
    """The core of the check, with the chroma matrix supplied (so it is testable without audio)."""
    runs = family_runs(chords, beats)
    holds = long_holds(runs, min_hold_beats)
    mains = main_chords(chords)
    bars_all, hold_rows = [], []
    for h in holds:
        held_label = h["labels"].most_common(1)[0][0]
        rivals = {k: v["label"] for k, v in mains.items() if k != h["key"]}
        row = {"start_s": round(h["s"], 3), "end_s": round(h["e"], 3), "beats": round(h["beats"], 2), "held": held_label,
               "bars": 0, "missed_bars": 0}
        for t0, t1 in bar_windows(beats, h["b0"], h["b1"], bpb):
            vec = window_chroma(chroma, sr, hop, t0, t1)
            if vec is None or not np.any(vec > 0) or not rivals:
                continue
            held_fit, best, delta = score_bar(vec, (h["key"], held_label), rivals, mode)
            if best is None or held_fit is None:
                continue
            held_r = held_fit[1]
            row["bars"] += 1
            bars_all.append({"start_s": round(t0, 3), "end_s": round(t1, 3), "held": held_label, "winner": best[1],
                             "held_fit": held_fit[0], "margin": round(delta, 3), "held_corr": round(held_r, 3), "winner_corr": round(best[2], 3),
                             "hold_start_s": row["start_s"], "hold_end_s": row["end_s"]})
            if delta > margin:
                row["missed_bars"] += 1
        row["missed_fraction"] = round(row["missed_bars"] / row["bars"], 3) if row["bars"] else None
        hold_rows.append(row)
    n = len(bars_all)
    deltas = [b["margin"] for b in bars_all]
    sens = {f"{m:.2f}": (round(sum(d > m for d in deltas) / n, 3) if n else None) for m in SENSITIVITY}
    missed = sum(d > margin for d in deltas)
    top = sorted((b for b in bars_all if b["margin"] > margin), key=lambda b: -b["margin"])[:MAX_EXAMPLES]
    return {
        "long_holds": len(holds), "long_hold_beats": round(sum(h["beats"] for h in holds), 1),
        "bars": n, "missed_bars": int(missed),
        "missed_change_fraction": round(missed / n, 3) if n else None,
        "mean_margin": round(float(np.mean(deltas)), 3) if n else None,
        "sensitivity": sens,
        "holds": hold_rows,
        "examples": sorted(top, key=lambda b: b["start_s"]),
        "main_chords": {k: {"label": v["label"], "share": round(v["share"], 3)} for k, v in mains.items()},
    }


# ------------------------------------------------------------------------------------------------ chart views and audio
def build_view(rec):
    """-> (chords [{s,e,l}], beats, bpb, bpb_assumed, view_source) or (None, note)."""
    song = read_json(SONGS_DIR / f"{rec['id']}.json")
    if song and isinstance(song.get("chords"), list) and song.get("beats"):
        bpb = (song.get("rhythm") or {}).get("beats_per_bar")
        return ([{"s": c["s"], "e": c["e"], "l": c["l"]} for c in song["chords"]], song["beats"], int(bpb or 4), not bpb, "exported"), None
    primary = read_json(rec["primary_path"])
    rhythm = rec["rhythm"]
    if not primary or not rhythm or not rhythm.get("beat_times_seconds"):
        return None, "no exported song and no pack chart or beat grid to build one from"
    bpb = rhythm.get("beats_per_bar")
    chords = [{"s": c["start_seconds"], "e": c["end_seconds"], "l": c["label"]} for c in primary.get("chords", [])]
    return (chords, rhythm["beat_times_seconds"], int(bpb or 4), not bpb, "pack"), None


def compute_chroma(path, use_hpss=True):
    import librosa
    import soundfile as sf

    y, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(1)
    hop = HOP if sr >= 20000 else 384                      # chroma_cqt needs a hop divisible by 64
    if use_hpss:
        y = librosa.effects.harmonic(y, margin=4.0)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, n_chroma=12, norm=None)
    return chroma, sr, hop


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="recording id(s), comma separated or repeated")
    ap.add_argument("--margin", type=float, default=MARGIN, help="Pearson-r margin for a missed change (default 0.10)")
    ap.add_argument("--min-hold-beats", type=float, default=MIN_HOLD_BEATS)
    ap.add_argument("--templates", choices=["claim", "variants", "label"], default="claim",
                    help="claim: held chord as labelled vs rivals' best colour variant (default); variants: both sides best variant; label: chart labels only")
    ap.add_argument("--source", choices=["mix", "guitar-stem"], default="mix", help="audio the chroma is taken from")
    ap.add_argument("--no-hpss", action="store_true", help="skip the harmonic/percussive split")
    ap.add_argument("--out", default=str(HOLDS_PATH))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)

    recs = load_recordings(only=parse_only(args.only))
    out_path = Path(args.out)
    results = {}
    for i, rec in enumerate(recs, 1):
        view, note = build_view(rec)
        base = {"title": rec["title"], "pack": rec["pack"], "shipped": not rec["excluded"], "excluded": rec["excluded"]}
        if view is None:
            results[rec["id"]] = {**base, "skipped": note}
            print(f"[{i}/{len(recs)}] {rec['id']}: skipped, {note}", flush=True)
            continue
        chords, beats, bpb, bpb_assumed, source = view
        audio = rec["audio_path"] if args.source == "mix" else STEMS_DIR / rec["id"] / "guitar16k.wav"
        if not Path(audio).is_file():
            results[rec["id"]] = {**base, "skipped": f"audio missing: {audio}"}
            print(f"[{i}/{len(recs)}] {rec['id']}: skipped, audio missing", flush=True)
            continue
        runs = family_runs(chords, beats)
        if not long_holds(runs, args.min_hold_beats):                    # no chroma needed
            res = analyse_holds(chords, beats, bpb, np.zeros((12, 1)), 22050, HOP, args.margin, args.min_hold_beats, args.templates)
        else:
            chroma, sr, hop = compute_chroma(audio, use_hpss=not args.no_hpss)
            res = analyse_holds(chords, beats, bpb, chroma, sr, hop, args.margin, args.min_hold_beats, args.templates)
        results[rec["id"]] = {**base, "view_source": source, "beats_per_bar": bpb, "beats_per_bar_assumed": bpb_assumed,
                              "min_hold_beats": args.min_hold_beats, "margin": args.margin, "templates": args.templates,
                              "audio_source": args.source, **res}
        print(f"[{i}/{len(recs)}] {rec['id']:60s} {source:8s} holds {res['long_holds']:2d} bars {res['bars']:3d} "
              f"missed {res['missed_change_fraction']}  sens {res['sensitivity']}", flush=True)

    if not args.no_write:
        existing = read_json(out_path) or {}
        existing.update(results)
        write_json_atomic(out_path, {k: existing[k] for k in sorted(existing)})
        print(f"wrote {out_path} ({len(existing)} recordings, {len(results)} updated)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
