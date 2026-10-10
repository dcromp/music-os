"""Run the published CREMA chord model in its separate Keras 2 environment.

This adapter never trains or downloads a model. CREMA 0.2.0's official PyPI
wheel includes its pretrained assets; see docs/CREMA_SETUP.md for provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[3]
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
QUALITY_SUFFIX = {
    "maj": "", "min": "m", "maj7": "maj7", "min7": "m7", "minmaj7": "mmaj7",
    "7": "7", "maj6": "6", "min6": "m6", "9": "9", "maj9": "maj9",
    "min9": "m9", "11": "11", "min11": "m11", "13": "13", "min13": "m13",
    "dim": "dim", "dim7": "dim7", "hdim7": "m7b5", "aug": "aug",
    "sus2": "sus2", "sus4": "sus4", "5": "5",
}


def display_label(harte_label: str) -> str:
    """Normalise C:maj/C:min to C/Cm while preserving quality and bass.

    Unknown/out-of-gamut X remains X; it is not relabelled as silence. Extended
    Harte interval lists remain in Harte notation if no simple suffix exists.
    """
    if harte_label in ("N", "X"):
        return harte_label
    import mir_eval

    root_name, _, remainder = harte_label.partition(":")
    quality, separator, bass = remainder.partition("/")
    if not separator and "/" in root_name:
        root_name, _, bass = root_name.partition("/")
        separator = "/"
    root_pc = mir_eval.chord.pitch_class_to_semitone(root_name)
    quality = quality or "maj"
    if quality not in QUALITY_SUFFIX:
        return harte_label
    label = NOTES[root_pc] + QUALITY_SUFFIX[quality]
    if separator:
        relative_bass = mir_eval.chord.scale_degree_to_semitone(bass)
        label += "/" + NOTES[(root_pc + relative_bass) % 12]
    return label


def load_model():
    # Keep caches within ignored experiment assets and use CPU inference.
    cache_root = ROOT / "experiments" / "candidate-assets" / "crema-cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(cache_root / "numba"))
    os.environ.setdefault("MPLCONFIGDIR", str(cache_root / "matplotlib"))
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

    from crema.models.chord import ChordModel
    from keras.utils import disable_interactive_logging

    disable_interactive_logging()
    return ChordModel()


def analyze(audio_path: Path, recording_id: str, model=None) -> dict:
    started = time.perf_counter()
    includes_model_load = model is None
    if model is None:
        model = load_model()
    import librosa
    from crema.version import version as crema_version

    signal, sample_rate = librosa.load(str(audio_path), sr=None, mono=True)
    if signal.size == 0:
        raise ValueError("Audio is empty")
    duration = signal.size / sample_rate
    annotation = model.predict(y=signal, sr=sample_rate)
    events = []
    previous_end = 0.0
    for observation in annotation:
        start = max(previous_end, 0.0, min(duration, float(observation.time)))
        end = max(start, min(duration, float(observation.time + observation.duration)))
        if end <= start:
            continue
        native_label = str(observation.value)
        event = {
            "start_seconds": start,
            "end_seconds": end,
            "label": display_label(native_label),
            "native_label": native_label,
        }
        confidence = float(observation.confidence)
        if math.isfinite(confidence) and 0 <= confidence <= 1:
            # Native model score, not calibrated probability of correctness.
            event["confidence"] = confidence
        events.append(event)
        previous_end = end
    if not events:
        raise ValueError("CREMA returned no chord intervals")
    return {
        "schema_version": "1.0",
        "recording": {
            "id": recording_id,
            "title": audio_path.stem,
            "duration_seconds": duration,
            "sample_rate_hz": sample_rate,
            "audio_sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest(),
        },
        "analysis": {
            "id": f"{recording_id}-crema",
            "algorithm": "crema-pretrained",
            "version": f"{crema_version}/{model.version}/adapter-{VERSION}",
            "runtime_seconds": time.perf_counter() - started,
            "parameters": {
                "model_version": model.version,
                "device": "cpu",
                "intraop_threads": os.environ["TF_NUM_INTRAOP_THREADS"],
                "inter_op_threads": os.environ["TF_NUM_INTEROP_THREADS"],
                "postprocessing": "native CREMA inversion and Viterbi decoding; label normalisation only",
                "confidence_semantics": "uncalibrated native model score",
                "runtime_semantics": (
                    "includes imports, model load, features, inference and decoding" if includes_model_load
                    else "per-file features, inference and decoding; batch model load measured separately"
                ),
            },
        },
        "chords": events,
    }


def write_chart(path: Path, chart: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chart, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_batch(manifest_path: Path, output_root: Path) -> int:
    manifest_path = manifest_path.resolve(strict=True)
    output_root = output_root.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Validate paths before loading expensive libraries or creating outputs.
    jobs, protected_paths, seen_ids = [], {manifest_path}, set()
    for case in manifest["cases"]:
        recording_id = case["id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", recording_id):
            raise ValueError(f"Unsafe recording ID: {recording_id!r}")
        if recording_id in seen_ids:
            raise ValueError(f"Duplicate recording ID: {recording_id!r}")
        seen_ids.add(recording_id)
        audio_path = (manifest_path.parent / case["audio"]).resolve(strict=True)
        if not audio_path.is_relative_to(manifest_path.parent):
            raise ValueError(f"Audio is outside suite folder: {audio_path}")
        protected_paths.add(audio_path)
        # Unannotated recordings can be analysed without a gold chart. When a
        # reference is supplied, retain its path and overwrite protections.
        if "reference" in case:
            reference_path = (manifest_path.parent / case["reference"]).resolve(strict=True)
            if not reference_path.is_relative_to(manifest_path.parent):
                raise ValueError(f"Reference is outside suite folder: {reference_path}")
            protected_paths.add(reference_path)
        output_path = (output_root / "cases" / recording_id / "crema.json").resolve()
        if not output_path.is_relative_to(output_root):
            raise ValueError("Output symlink would leave the selected output folder")
        jobs.append((recording_id, audio_path, output_path))
    if not jobs:
        raise ValueError("Suite has no cases")
    if any(output in protected_paths for _, _, output in jobs):
        raise ValueError("Output would overwrite a source file")
    summary_path = (output_root / "crema-batch-summary.json").resolve()
    if not summary_path.is_relative_to(output_root) or summary_path in protected_paths:
        raise ValueError("Batch summary must stay in output folder without overwriting sources")
    started = time.perf_counter()
    model = load_model()
    model_load_seconds = time.perf_counter() - started
    failures = []
    for index, (recording_id, audio_path, output_path) in enumerate(jobs, 1):
        try:
            chart = analyze(audio_path, recording_id, model=model)
            chart["analysis"]["parameters"]["batch_model_load_seconds"] = model_load_seconds
            write_chart(output_path, chart)
            print(f"CREMA {index}/{len(jobs)} {recording_id}: {len(chart['chords'])} intervals, "
                  f"{chart['analysis']['runtime_seconds']:.2f}s", flush=True)
        except Exception as exc:
            failures.append({"id": recording_id, "error": f"{type(exc).__name__}: {exc}"})
            print(f"CREMA {index}/{len(jobs)} {recording_id}: FAILED {exc}", file=sys.stderr, flush=True)
            # Never leave a stale prediction looking successful after a failed rerun.
            output_path.unlink(missing_ok=True)
    summary = {"algorithm": "crema-pretrained", "total_cases": len(jobs),
               "successful_cases": len(jobs) - len(failures), "failures": failures,
               "model_load_seconds": model_load_seconds,
               "wall_seconds": time.perf_counter() - started}
    write_chart(summary_path, summary)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recording-id")
    parser.add_argument("--batch-manifest", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    try:
        if args.batch_manifest:
            if not args.output_root or args.audio or args.output or args.recording_id:
                parser.error("Batch mode requires --batch-manifest and --output-root only")
            return run_batch(args.batch_manifest, args.output_root)
        if not args.audio or not args.output or not args.recording_id or args.output_root:
            parser.error("Single mode requires --audio, --output, and --recording-id")
        audio_path = args.audio.resolve(strict=True)
        if args.output.resolve() == audio_path:
            raise ValueError("Output must not overwrite input audio")
        chart = analyze(audio_path, args.recording_id)
    except (ImportError, FileNotFoundError) as exc:
        print(f"CREMA unavailable: {exc}. See docs/CREMA_SETUP.md.", file=sys.stderr)
        return 2
    write_chart(args.output, chart)
    print(f"CREMA: {len(chart['chords'])} intervals in {chart['analysis']['runtime_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
