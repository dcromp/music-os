"""CPU-only adapter for the official BTC-ISMIR19 major/minor checkpoint.

No training or downloads occur here. See docs/BTC_SETUP.md for the isolated
environment, pinned upstream source and checkpoint provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM_REVISION = "2682317be668032e6e4b269ded36adaa2ad57df0"
CHECKPOINT_SHA256 = "71c2c5db17e8c43b8a9a9da5db36ef2d667158c07a214eba16344c154c00bf54"
VERSION = "0.1.0"
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODEL_CACHE = {}


def infer(audio_path: Path, recording_id: str, repo: Path, threads: int) -> dict:
    started = time.perf_counter()
    checkpoint_path = repo / "test" / "btc_model.pt"
    for required in (repo / "btc_model.py", repo / "run_config.yaml", checkpoint_path):
        if not required.is_file():
            raise ValueError(f"BTC asset missing: {required}. Follow docs/BTC_SETUP.md.")
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if revision != UPSTREAM_REVISION:
        raise ValueError(f"Expected BTC source {UPSTREAM_REVISION}, found {revision}")
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    if checkpoint_sha != CHECKPOINT_SHA256:
        raise ValueError("Checkpoint hash differs from the inspected official major/minor checkpoint")

    os.environ.setdefault("NUMBA_CACHE_DIR", str(ROOT / "experiments" / "candidate-assets" / "numba-cache"))
    import numpy as np
    import torch
    import librosa
    import soundfile as sf
    import yaml

    # Upstream positional encodings use the removed np.float alias. This local
    # process compatibility alias changes no learned weights or computations.
    if "float" not in np.__dict__:
        np.float = float
    sys.path.insert(0, str(repo))
    from btc_model import BTC_model

    torch.set_num_threads(threads)
    with (repo / "run_config.yaml").open(encoding="utf-8") as source:
        config = yaml.safe_load(source)
    if config["model"]["num_chords"] != 25:
        raise ValueError("Only the official 25-label major/minor configuration is supported")
    key = (str(repo), checkpoint_sha, threads)
    model_reused = key in MODEL_CACHE
    if not model_reused:
        # The legacy checkpoint includes a NumPy scalar for std. Keep the
        # restricted weights-only loader and allow its necessary scalar/dtype.
        safe_types = [np.core.multiarray.scalar, np.dtype, type(np.dtype("float64"))]
        with torch.serialization.safe_globals(safe_types):
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        mean, std = float(checkpoint["mean"]), float(checkpoint["std"])
        if not math.isfinite(mean) or not math.isfinite(std) or std <= 0:
            raise ValueError("Invalid checkpoint feature normalization")
        model = BTC_model(config=config["model"]).to("cpu")
        model.load_state_dict(checkpoint["model"], strict=True)
        model.eval()
        MODEL_CACHE[key] = (model, mean, std)
    model, mean, std = MODEL_CACHE[key]

    samples, original_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    if not samples.shape[0] or original_rate <= 0 or not np.isfinite(samples).all():
        raise ValueError("Audio must contain finite, nonempty samples")
    duration = samples.shape[0] / original_rate
    signal = samples.mean(axis=1)
    feature_rate = int(config["mp3"]["song_hz"])
    if original_rate != feature_rate:
        signal = librosa.resample(signal, orig_sr=original_rate, target_sr=feature_rate)
    chunk_samples = round(float(config["mp3"]["inst_len"]) * feature_rate)
    hop = int(config["feature"]["hop_length"])
    features, frame_times = [], []
    # Preserve upstream ten-second CQT chunks while deriving exact frame times
    # from the actual hop and chunk origin. Avoid its uninitialized short-file
    # accumulator and approximate 10/108 clock, and never score padded frames.
    for start in range(0, len(signal), chunk_samples):
        chunk = signal[start:start + chunk_samples]
        cqt = librosa.cqt(chunk, sr=feature_rate, n_bins=int(config["feature"]["n_bins"]),
                          bins_per_octave=int(config["feature"]["bins_per_octave"]), hop_length=hop)
        times = (start + np.arange(cqt.shape[1]) * hop) / feature_rate
        keep = (times < (start + len(chunk)) / feature_rate) & (times < duration)
        features.append(np.log(np.abs(cqt[:, keep]) + 1e-6).T)
        frame_times.extend(times[keep].tolist())
    feature = (np.concatenate(features, axis=0) - mean) / std
    if not np.isfinite(feature).all() or not frame_times:
        raise ValueError("Feature extraction produced no finite frames")
    timestep = int(config["model"]["timestep"])
    padding = (-len(feature)) % timestep
    feature = np.pad(feature, ((0, padding), (0, 0)), constant_values=0)
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(feature), timestep):
            batch = torch.tensor(feature[start:start + timestep], dtype=torch.float32).unsqueeze(0)
            hidden, _ = model.self_attn_layers(batch)
            predicted, _ = model.output_layer(hidden)
            predictions.extend(predicted.squeeze(0).tolist())
    labels = [name + suffix for name in NOTES for suffix in ("", "m")] + ["N"]
    chords = []
    for timestamp, index in zip(frame_times, predictions):
        label = labels[int(index)]
        if chords and chords[-1]["label"] == label:
            continue
        if chords:
            chords[-1]["end_seconds"] = timestamp
        chords.append({"start_seconds": timestamp, "end_seconds": duration, "label": label})

    return {
        "schema_version": "1.0",
        "recording": {"id": recording_id, "title": audio_path.stem,
                      "duration_seconds": duration, "sample_rate_hz": original_rate,
                      "audio_sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                      "provenance": "User-supplied local audio; permissions recorded separately"},
        "analysis": {
            "id": f"btc-majmin-{CHECKPOINT_SHA256[:12]}", "algorithm": "BTC-ISMIR19",
            "version": f"adapter-{VERSION}/upstream-{UPSTREAM_REVISION[:12]}",
            "runtime_seconds": time.perf_counter() - started,
            "parameters": {"device": "cpu", "threads": threads, "feature_sample_rate_hz": feature_rate,
                           "cqt_n_bins": config["feature"]["n_bins"], "bins_per_octave": config["feature"]["bins_per_octave"],
                           "hop_samples": hop, "chunk_seconds": config["mp3"]["inst_len"],
                           "timestep": timestep, "vocabulary": "24 major/minor labels plus N",
                           "smoothing": "none", "timing": "exact CQT hop plus chunk origin; clipped to input duration",
                           "upstream_url": "https://github.com/jayg996/BTC-ISMIR19", "upstream_revision": revision,
                           "checkpoint": "test/btc_model.pt", "checkpoint_sha256": checkpoint_sha,
                           "torch_version": torch.__version__, "librosa_version": librosa.__version__, "numpy_version": np.__version__,
                           "model_reused": model_reused,
                           "runtime_includes": "feature extraction and CPU inference; first case also imports and loads checkpoint"},
        },
        "chords": chords,
    }


def write_result(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def batch(manifest_path: Path, output_root: Path, repo: Path, threads: int) -> dict:
    started = time.perf_counter()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases") if isinstance(manifest, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("Batch manifest needs a nonempty cases array")
    identifiers = [case.get("id") if isinstance(case, dict) else None for case in cases]
    if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) for value in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Batch case IDs must be unique safe identifiers")
    results = []
    for position, case in enumerate(cases, 1):
        output = output_root / "cases" / case["id"] / "btc.json"
        try:
            audio = case.get("audio")
            if not isinstance(audio, str) or not audio:
                raise ValueError("Case audio must be a nonempty relative path")
            audio_path = (manifest_path.parent / audio).resolve()
            if not audio_path.is_relative_to(manifest_path.parent.resolve()):
                raise ValueError("Case audio must stay inside the manifest directory")
            if output.resolve() == audio_path:
                raise ValueError("Output must not overwrite audio")
            # Do not leave an old successful output after a failed rerun.
            output.unlink(missing_ok=True)
            result = infer(audio_path, case["id"], repo, threads)
            write_result(output, result)
            results.append({"id": case["id"], "status": "ok", "output": str(output),
                            "runtime_seconds": result["analysis"]["runtime_seconds"]})
            print(f"BTC [{position}/{len(cases)}] {case['id']}: {result['analysis']['runtime_seconds']:.3f}s", flush=True)
        except Exception as error:
            results.append({"id": case["id"], "status": "failed", "error": str(error)})
            print(f"BTC [{position}/{len(cases)}] {case['id']}: FAILED {error}", file=sys.stderr, flush=True)
    summary = {"algorithm": "BTC-ISMIR19", "manifest": str(manifest_path),
               "runtime_seconds": time.perf_counter() - started, "cases": results,
               "failed_cases": sum(case["status"] == "failed" for case in results)}
    write_result(output_root / "btc-batch-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audio", type=Path)
    mode.add_argument("--batch-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recording-id")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--btc-repo", type=Path, default=ROOT / "experiments" / "candidate-assets" / "btc-ismir19")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    try:
        if not 1 <= args.threads <= 32:
            raise ValueError("Provide 1–32 CPU threads")
        if args.batch_manifest:
            if not args.output_root or args.output or args.recording_id:
                raise ValueError("Batch mode needs --output-root; use single-file flags separately")
            summary = batch(args.batch_manifest.resolve(), args.output_root.resolve(), args.btc_repo.resolve(), args.threads)
            if summary["failed_cases"]:
                parser.exit(1, f"BTC batch completed with {summary['failed_cases']} failed cases; see btc-batch-summary.json\n")
            return
        if not args.output or not args.recording_id or args.output_root:
            raise ValueError("Single-file mode needs --output and --recording-id")
        if args.audio.resolve() == args.output.resolve():
            raise ValueError("Output must not overwrite input audio")
        if not args.recording_id.strip() or not 1 <= args.threads <= 32:
            raise ValueError("Provide a nonempty recording ID and 1–32 CPU threads")
        result = infer(args.audio, args.recording_id.strip(), args.btc_repo.resolve(), args.threads)
        write_result(args.output, result)
        print(f"BTC saved {len(result['chords'])} events to {args.output}; {result['analysis']['runtime_seconds']:.3f}s")
    except (ValueError, OSError, KeyError, ImportError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
