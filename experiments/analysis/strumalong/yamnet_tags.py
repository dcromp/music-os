#!/usr/bin/env python
"""YAMNet instrument tags for the Strum Along instrument stage.

Run with the CREMA environment (TensorFlow 2.15, scipy, soundfile):

    .venv-crema/bin/python experiments/analysis/strumalong/yamnet_tags.py [--only ID[,ID...]] [--scores-from mix|stem|max] [--stat p90|mean|top5] [--include-strum]

For every recording in strumalong/data/catalogue.json (excluded ones too) it runs YAMNet on

  (a) the full mix (the pack's prepared audio, resampled to 16 kHz), and
  (b) the guitar stem experiments/generated/strumalong-stems/<id>/guitar16k.wav, when stems_6s.py has made it,

and merges the result, together with the stem statistics from <id>/stats.json, into
experiments/generated/strumalong-instrument-tags.json (schema `strumalong-instrument-tags-1`, extended; see
docs/STRUMALONG_CATALOGUE_CHECKS.md). Existing entries for other recordings are kept, so --only updates in place.

Offline: the SavedModel is the founder-approved copy in experiments/candidate-assets/yamnet-1/model (tarball SHA-256 checked).

Per class, per source: `mean` score, `p90` (90th percentile over frames) and `top5_frac` (fraction of frames in which the class
is among the five highest scores). YAMNet frames are 0.96 s windows every 0.48 s. `strum_given_guitar` is the mean Strum score
over the frames where any guitar class (Guitar, Electric guitar, Acoustic guitar, Steel guitar) is in the top five, with the
number of such frames.

The flat `scores` map that catalogue_checks.js reads is one statistic (--stat, default top5) of one source (--scores-from,
default max, i.e. per tag the larger of the full-mix and guitar-stem value) for the instrument tags its gates know. The
`aggregation` text in `model` says which. Defaults chosen after the 3-song smoke test: YAMNet's full-mix probabilities are tiny for
every instrument in a dense mix (guitar p90 0.02 to 0.06 even for strummed songs, "Music" 0.9), so a p90 or mean cannot meet the
checker's thresholds, while the share of frames in which a class is top-5 is on a scale they can use. The Strum class is left out
of `scores` unless --include-strum: on the smoke test it was higher for the picked House of the Rising Sun than for strummed
Zombie. Since the full-batch calibration (25 October 2026) the checker uses these tags only to corroborate the Demucs guitar
share (guitar-led) and ignores `strum`; strummed-or-picked comes from strum_features.py, whose `strum` blocks this tool keeps.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strumalong_common import (REPO, STEMS_DIR, TAGS_PATH, file_sha256, load_recordings, parse_only, read_json,  # noqa: E402
                               write_json_atomic)

MODEL_DIR = REPO / "experiments" / "candidate-assets" / "yamnet-1" / "model"
TARBALL = REPO / "experiments" / "candidate-assets" / "yamnet-1" / "yamnet_1.tar.gz"
TARBALL_SHA256 = "b80da2a1a56926fb0767205051a200dd7b3beaf3ea1ea126c42a53943996e5e0"
SCHEMA = "strumalong-instrument-tags-1"
YAMNET_RATE = 16000

# key -> display_name in assets/yamnet_class_map.csv. Looked up by name, never by hard-coded index.
CLASS_KEYS = {
    "guitar": "Guitar", "acoustic_guitar": "Acoustic guitar", "electric_guitar": "Electric guitar",
    "steel_guitar": "Steel guitar, slide guitar", "bass_guitar": "Bass guitar", "tapping_guitar": "Tapping (guitar technique)",
    "strum": "Strum", "plucked_string": "Plucked string instrument",
    "banjo": "Banjo", "mandolin": "Mandolin", "ukulele": "Ukulele", "sitar": "Sitar",
    "piano": "Piano", "electric_piano": "Electric piano", "keyboard": "Keyboard (musical)", "organ": "Organ",
    "synthesizer": "Synthesizer", "harmonica": "Harmonica", "accordion": "Accordion",
    "brass": "Brass instrument", "trumpet": "Trumpet", "violin": "Violin, fiddle", "harp": "Harp",
    "drum_kit": "Drum kit", "singing": "Singing", "speech": "Speech", "music": "Music",
}
GUITAR_CLASSES = ["guitar", "acoustic_guitar", "electric_guitar", "steel_guitar"]   # what "any guitar class" means
# The tags the catalogue_checks.js gates know (guitar_keys + other_keys + strum), plus a few close relatives. Singing, speech,
# music and drums are context, not instrument evidence, so they stay out of the flat `scores` map.
SCORE_KEYS = ["guitar", "acoustic_guitar", "electric_guitar", "steel_guitar", "ukulele", "piano", "harmonica", "banjo",
              "mandolin", "accordion", "organ", "keyboard", "synthesizer", "violin", "harp", "electric_piano", "brass", "trumpet",
              "plucked_string", "sitar"]


# ------------------------------------------------------------------------------------------------ pure helpers (numpy only)
def read_class_map(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [r["display_name"] for r in sorted(rows, key=lambda r: int(r["index"]))]


def class_indices(names):
    idx = {}
    for key, display in CLASS_KEYS.items():
        hits = [i for i, n in enumerate(names) if n == display]
        if len(hits) != 1:
            raise RuntimeError(f"class {display!r} matched {len(hits)} entries in the class map")
        idx[key] = hits[0]
    return idx


def top_k_mask(scores, k=5):
    """[frames, classes] boolean: is the class among the k highest scores of its frame."""
    mask = np.zeros(scores.shape, dtype=bool)
    if scores.shape[0] == 0:
        return mask
    top = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    np.put_along_axis(mask, top, True, axis=1)
    return mask


def summarize(scores, idx, names, top_n=8):
    """scores: [frames, 521] YAMNet class probabilities. -> per-class mean / p90 / top5_frac for CLASS_KEYS, the overall top
    classes by mean score, and strum_given_guitar."""
    frames = int(scores.shape[0])
    if frames == 0:
        return {"frames": 0}
    in_top = top_k_mask(scores, 5)
    classes = {}
    for key, i in idx.items():
        col = scores[:, i]
        classes[key] = {"mean": round(float(col.mean()), 4), "p90": round(float(np.percentile(col, 90)), 4),
                        "top5_frac": round(float(in_top[:, i].mean()), 4)}
    means = scores.mean(0)
    order = np.argsort(-means)[:top_n]
    top_classes = [{"name": names[i], "mean": round(float(means[i]), 4), "top5_frac": round(float(in_top[:, i].mean()), 4)} for i in order]
    guitar_frames = in_top[:, [idx[k] for k in GUITAR_CLASSES]].any(1)
    n_g = int(guitar_frames.sum())
    return {
        "frames": frames, "classes": classes, "top_classes": top_classes,
        "any_guitar_top5_frac": round(float(guitar_frames.mean()), 4),
        "strum_given_guitar": {"value": (round(float(scores[guitar_frames, idx["strum"]].mean()), 4) if n_g else None),
                               "frames": n_g},
    }


def flat_scores(mix, stem, source="max", stat="top5", include_strum=False):
    """The flat {tag: score in [0,1]} map catalogue_checks.js reads. `source`: mix, stem or max (per tag, over both)."""
    def pick(summary, key):
        if not summary or "classes" not in summary:
            return None
        c = summary["classes"].get(key)
        return None if c is None else c["top5_frac" if stat == "top5" else stat]

    out = {}
    for key in SCORE_KEYS + (["strum"] if include_strum else []):
        a, b = (pick(mix, key), pick(stem, key))
        if source == "mix":
            v = a
        elif source == "stem":
            v = b if b is not None else a
        else:
            vals = [x for x in (a, b) if x is not None]
            v = max(vals) if vals else None
        if v is not None:
            out[key] = round(float(min(1.0, max(0.0, v))), 4)
    return out


def aggregation_text(source, stat, include_strum=False):
    """Short text for model.aggregation (the checker copies `model` into every song's report, so it stays one line)."""
    s = {"p90": "p90", "mean": "mean", "top5": "top-5 frame fraction"}[stat]
    src = {"mix": "full mix", "stem": "guitar stem", "max": "max of full mix and guitar stem"}[source]
    return f"{s} of YAMNet class scores, {src}" + ("" if include_strum else "; no strum key")


AGGREGATION_DETAIL = ("scores[tag] is one statistic of one source: p90 = 90th percentile over frames of the class probability, mean = "
                      "mean over frames, top5 = fraction of frames in which the class is among the five highest scores. Frames are "
                      "0.96 s windows every 0.48 s. top5 is in [0,1] but is a frame fraction, not a probability. Per-source detail "
                      "(mean, p90, top5_frac for every tag) is in full_mix and guitar_stem.")


# Fields other tools merge into the same file (strum_features.py): kept when an entry or the document is rewritten here.
FOREIGN_ENTRY_KEYS = ("strum",)
FOREIGN_DOC_KEYS = ("strum_features",)


def merge_tags(existing, model, new_recordings, provenance=None):
    """Merge new per-recording entries into an existing tags document (same schema), keeping the others, and keeping the
    fields strum_features.py owns (per-recording `strum`, top-level `strum_features`)."""
    same = (existing or {}).get("schema") == SCHEMA
    recs = dict((existing or {}).get("recordings", {})) if same else {}
    for rid, entry in new_recordings.items():
        old = recs.get(rid) or {}
        keep = {k: old[k] for k in FOREIGN_ENTRY_KEYS if k in old and k not in entry}
        recs[rid] = {**entry, **keep}
    doc = {"schema": SCHEMA, "model": model, "recordings": {k: recs[k] for k in sorted(recs)}}
    if provenance:
        doc["provenance"] = provenance
    if same:
        for k in FOREIGN_DOC_KEYS:
            if k in existing:
                doc[k] = existing[k]
    return doc


# ------------------------------------------------------------------------------------------------ model and audio
def load_yamnet():
    import tensorflow as tf
    if TARBALL.is_file():
        sha = file_sha256(TARBALL)
        if sha != TARBALL_SHA256:
            raise RuntimeError(f"yamnet tarball SHA-256 mismatch: {sha}")
    model = tf.saved_model.load(str(MODEL_DIR))
    names = read_class_map(MODEL_DIR / "assets" / "yamnet_class_map.csv")
    if len(names) != 521:
        raise RuntimeError(f"class map has {len(names)} entries, expected 521")
    return tf, model, names


def read_mono(path, target_rate=YAMNET_RATE):
    import soundfile as sf
    from math import gcd
    from scipy.signal import resample_poly

    wav, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if wav.ndim > 1:
        wav = wav.mean(1)
    if sr != target_rate:
        g = gcd(int(sr), target_rate)
        wav = resample_poly(wav, target_rate // g, int(sr) // g).astype(np.float32)
    return np.clip(wav, -1.0, 1.0).astype(np.float32)


def run_yamnet(tf, model, wav):
    if len(wav) < YAMNET_RATE:                       # YAMNet needs at least one 0.96 s window
        return np.zeros((0, 521), dtype=np.float32)
    scores, _emb, _spec = model(tf.constant(wav, dtype=tf.float32))
    return scores.numpy()


def stem_block(stats):
    s = stats.get("stems", {})
    return {
        "energy_share": s.get("energy_share"), "rms_dbfs": s.get("rms_dbfs"),
        "guitar_share_of_harmonic": s.get("guitar_share_of_harmonic"),
        "guitar_low_band_ratio": (stats.get("guitar_band") or {}).get("low_band_ratio"),
        "guitar_low_band_db": (stats.get("guitar_band") or {}).get("low_band_db"),
        "guitar_active_fraction": (stats.get("guitar_band") or {}).get("active_fraction"),
        "guitar_centroid_hz": (stats.get("guitar_band") or {}).get("centroid_hz"),
        "model": (stats.get("model") or {}).get("name"), "weights_sha256": (stats.get("model") or {}).get("weights_sha256"),
        "stats_file": f"experiments/generated/strumalong-stems/{stats.get('recording_id')}/stats.json",
    }


def tag_recording(rec, tf, model, names, idx, args):
    audio_sha = file_sha256(rec["audio_path"])
    mix_summary = summarize(run_yamnet(tf, model, read_mono(rec["audio_path"])), idx, names)
    stem_path = STEMS_DIR / rec["id"] / "guitar16k.wav"
    stem_summary = summarize(run_yamnet(tf, model, read_mono(stem_path)), idx, names) if stem_path.is_file() else None
    stats = read_json(STEMS_DIR / rec["id"] / "stats.json")
    entry = {
        "audio_sha256": audio_sha, "pack": rec["pack"], "excluded": rec["excluded"],
        "scores": flat_scores(mix_summary, stem_summary, args.scores_from, args.stat, args.include_strum),
        "scores_aggregation": f"{args.scores_from}/{args.stat}",
        "full_mix": mix_summary,
    }
    if rec["excluded_reason"]:
        entry["excluded_reason"] = rec["excluded_reason"]
    if stem_summary is not None:
        entry["guitar_stem"] = stem_summary
    if stats:
        entry["stems"] = stem_block(stats)
        if stats.get("audio_sha256") != audio_sha:
            entry["stems"]["warning"] = "stems were made from a different audio file than the one tagged here; re-run stems_6s.py --force"
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="recording id(s), comma separated or repeated")
    ap.add_argument("--scores-from", choices=["mix", "stem", "max"], default="max", help="source of the flat `scores` map (default max of mix and stem)")
    ap.add_argument("--stat", choices=["p90", "mean", "top5"], default="top5", help="statistic of the flat `scores` map (default top5 = fraction of frames in the top five)")
    ap.add_argument("--include-strum", action="store_true", help="also put the Strum class in the flat `scores` map (evidence only; the checker ignores it)")
    ap.add_argument("--out", default=str(TAGS_PATH), help="output JSON (default experiments/generated/strumalong-instrument-tags.json)")
    ap.add_argument("--require-stems", action="store_true", help="skip recordings that have no guitar stem yet")
    args = ap.parse_args(argv)

    recs = load_recordings(only=parse_only(args.only))
    tf, model, names = load_yamnet()
    idx = class_indices(names)
    print(f"YAMNet loaded; {len(recs)} recordings; indices: " + ", ".join(f"{k}={idx[k]}" for k in ("guitar", "acoustic_guitar", "electric_guitar", "strum", "ukulele", "piano", "harmonica")), flush=True)

    new, failures = {}, []
    for i, rec in enumerate(recs, 1):
        if not rec["audio_exists"]:
            print(f"[{i}/{len(recs)}] {rec['id']}: audio missing", flush=True)
            failures.append(rec["id"])
            continue
        if args.require_stems and not (STEMS_DIR / rec["id"] / "guitar16k.wav").is_file():
            print(f"[{i}/{len(recs)}] {rec['id']}: no guitar stem yet, skipped", flush=True)
            continue
        try:
            e = tag_recording(rec, tf, model, names, idx, args)
        except Exception as exc:  # keep going; report at the end
            print(f"[{i}/{len(recs)}] {rec['id']}: FAILED {exc!r}", flush=True)
            failures.append(rec["id"])
            continue
        new[rec["id"]] = e
        s = e["scores"]
        g = e.get("guitar_stem")
        print(f"[{i}/{len(recs)}] {rec['id']}  scores[{args.scores_from}/{args.stat}]: guitar {s.get('guitar')} uke {s.get('ukulele')} piano {s.get('piano')} harm {s.get('harmonica')}"
              + ("" if g is None else f"  | stem p90: guitar {g['classes']['guitar']['p90']} strum {g['classes']['strum']['p90']} uke {g['classes']['ukulele']['p90']}"), flush=True)

    stem_model = None
    for e in new.values():
        if e.get("stems", {}).get("weights_sha256"):
            stem_model = {"name": e["stems"]["model"], "weights_sha256": e["stems"]["weights_sha256"]}
            break
    model_block = {
        "name": "yamnet", "version": "1", "sha256": TARBALL_SHA256,
        "aggregation": aggregation_text(args.scores_from, args.stat, args.include_strum),
        "stem_model": stem_model,
    }
    provenance = {
        "saved_model_pb_sha256": file_sha256(MODEL_DIR / "saved_model.pb"),
        "class_map": "assets/yamnet_class_map.csv (521 classes, looked up by display_name)",
        "scores_from": args.scores_from, "scores_stat": args.stat, "strum_in_scores": args.include_strum,
        "aggregation_detail": AGGREGATION_DETAIL,
        "frame_window_seconds": 0.96, "frame_hop_seconds": 0.48,
        "guitar_classes": [CLASS_KEYS[k] for k in GUITAR_CLASSES],
        "tool": "experiments/analysis/strumalong/yamnet_tags.py",
    }
    out = Path(args.out)
    doc = merge_tags(read_json(out), model_block, new, provenance)
    write_json_atomic(out, doc)
    print(f"wrote {out} ({len(doc['recordings'])} recordings, {len(new)} updated, {len(failures)} failed)", flush=True)
    if failures:
        print("failed: " + ", ".join(failures), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
