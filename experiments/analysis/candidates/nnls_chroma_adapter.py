"""Frozen NNLS-Chroma pitch-class evidence from a separate project-local host.

This consumes only a PCM16 mono WAV, never a chord chart or reference timings.
Native feature centers and raw activation norms are preserved. This is offline
acoustic evidence, not an independent timed chord recognizer or probability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab

SCHEMA = "pitch-class-evidence-1.0"
PLUGIN_REVISION = "4c5f214a75cb354f8d8c933e161377c5b4d83713"
SDK_REVISION = "44c2487763eb248a933e9eff9169cfadee375009"
NATIVE_BINS = ["A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab"]
PITCH_CLASSES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
REORDER = [NATIVE_BINS.index(label) for label in PITCH_CLASSES]
FROZEN_PARAMETERS = {"useNNLS": 1.0, "tuningmode": 0.0, "whitening": 1.0,
                     "s": 0.7, "chromanormalize": 0.0, "rollon": 0.0}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_native_metadata(metadata: dict, sample_rate: int, sample_count: int) -> None:
    if not isinstance(metadata, dict):
        raise ValueError("Missing native metadata")
    for name, expected in {"plugin": "nnls-chroma:nnls-chroma", "output": "chroma", "plugin_version": 5,
                           "sample_rate_hz": sample_rate, "frames": sample_count,
                           "hop_size": 2048, "block_size": 16384, "timestamp_method": "ShiftData",
                           "timestamp_adjustment_seconds": 0, "window": "Hann",
                           "timestamp_semantics": "analysis window center", "native_bin_names": NATIVE_BINS}.items():
        if metadata.get(name) != expected:
            raise ValueError(f"Native {name} differs from frozen acoustic configuration")
    parameters = metadata.get("parameters", {})
    if set(parameters) != set(FROZEN_PARAMETERS) or any(
        not isinstance(parameters[name], (int, float)) or isinstance(parameters[name], bool)
        or not math.isclose(parameters[name], expected, rel_tol=0, abs_tol=1e-6)
        for name, expected in FROZEN_PARAMETERS.items()
    ):
        raise ValueError("Native parameter defaults differ from frozen configuration")


def parse_native(text: str, sample_rate: int, sample_count: int) -> tuple[np.ndarray, np.ndarray, dict]:
    metadata, times, vectors = None, [], []
    for line in text.splitlines():
        if line.startswith("#"):
            if metadata is not None:
                raise ValueError("Duplicate native metadata")
            metadata = json.loads(line[1:])
        elif line.strip():
            values = line.split("\t")
            if len(values) != 13:
                raise ValueError("Native features require timestamp and 12 chroma activations")
            times.append(float(values[0]))
            vectors.append([float(value) for value in values[1:]])
    validate_native_metadata(metadata, sample_rate, sample_count)
    times = np.array(times, dtype=float)
    vectors = np.array(vectors, dtype=float)
    expected_times = np.arange(0, sample_count, 2048, dtype=float) / sample_rate
    if len(times) != len(expected_times) or not np.all(np.isfinite(times)) or not np.allclose(
        times, expected_times, rtol=0, atol=1.1e-9
    ):
        raise ValueError("Native feature timestamps do not match exact ShiftData frame centers")
    if vectors.shape != (len(times), 12) or not np.all(np.isfinite(vectors)) or np.any(vectors < 0):
        raise ValueError("Native activations must be finite nonnegative 12-bin vectors")
    return times, vectors[:, REORDER], metadata


def validate_build(host: Path, plugin_dir: Path, info: dict) -> None:
    if info["plugin"]["revision"] != PLUGIN_REVISION or info["vamp_sdk"]["revision"] != SDK_REVISION:
        raise ValueError("Unreviewed native source revisions")
    if sha(host) != info["host_binary_sha256"] or sha(plugin_dir / "nnls-chroma.dylib") != info["plugin_binary_sha256"]:
        raise ValueError("Native binary differs from build provenance")
    if sha(Path(__file__).with_name("nnls-chroma-host.cpp")) != info["host_source_sha256"]:
        raise ValueError("Build host source changed; rebuild the acoustic host")


def centered_rms(signal: np.ndarray, times: np.ndarray, sample_rate: int, frame_size: int) -> np.ndarray:
    # Rectangular original-audio RMS over the same support as the native Hann
    # FFT. Silence has its own evidence; chroma normalization cannot override it.
    square_sum = np.concatenate(([0.0], np.cumsum(np.square(signal), dtype=float)))
    centers = np.rint(times * sample_rate).astype(int)
    starts = np.maximum(0, centers - frame_size // 2)
    ends = np.minimum(len(signal), centers + frame_size // 2)
    return np.sqrt(np.maximum(0, square_sum[ends] - square_sum[starts]) / frame_size)


def extract(audio: Path, recording_id: str, *, host: Path | None = None,
            plugin_dir: Path | None = None, build_info: Path | None = None) -> dict:
    started = time.perf_counter()
    if not isinstance(recording_id, str) or not recording_id.strip():
        raise ValueError("recording_id is required")
    native = ROOT / "experiments/candidate-assets/nnls-chroma-evidence-native"
    host = host or native / "nnls-chroma-host"
    plugin_dir = plugin_dir or ROOT / "experiments/candidate-assets/chordino-native"
    build_info = build_info or native / "buildinfo.json"
    info = json.loads(build_info.read_text())
    validate_build(host, plugin_dir, info)
    signal, sample_rate = lab.read_wav(audio)
    duration = len(signal) / sample_rate
    if not len(signal) or duration > 600:
        raise ValueError("Acoustic experiment requires nonempty audio no longer than 600 seconds")
    environment = os.environ.copy()
    environment["VAMP_PATH"] = str(plugin_dir.resolve())
    result = subprocess.run([str(host.resolve()), str(audio.resolve())], env=environment,
                            capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(f"NNLS acoustic host exited {result.returncode}: {result.stderr[-1500:]}")
    times, chroma, metadata = parse_native(result.stdout, sample_rate, len(signal))
    norms = np.linalg.norm(chroma, axis=1)
    normalized = np.divide(chroma, norms[:, None], out=np.zeros_like(chroma), where=norms[:, None] > 0)
    rms = centered_rms(signal, times, sample_rate, metadata["block_size"])
    threshold = max(1e-5, float(np.max(np.abs(signal))) * 0.025)
    evidence = {
        "schema_version": SCHEMA,
        "recording": {"id": recording_id, "title": audio.stem, "duration_seconds": duration,
                      "sample_rate_hz": sample_rate, "sample_count": len(signal), "audio_sha256": sha(audio)},
        "analysis": {"id": "nnls-chroma-frozen-v1", "algorithm": "NNLS-Chroma acoustic evidence",
                     "version": "adapter-0.1", "runtime_seconds": time.perf_counter() - started,
                     "native_host": metadata, "build": info,
                     "normalization": "C-first reorder, then per-frame L2; all-zero frames remain zero",
                     "silence": {"method": "original-audio RMS over native centered FFT support; edge padding divides by full frame size",
                                 "threshold": threshold, "rule": "max(1e-5, peak absolute sample * 0.025)"},
                     "offline": True, "global_tuning": True,
                     "no_chart_or_reference_consumed": True,
                     "limitations": ["native ~93ms hop and ~743ms support at 22050Hz",
                                     "FFT window centers are not physical chord-change timestamps",
                                     "normalized chroma/cosine similarity is not calibrated confidence"]},
        "pitch_classes": PITCH_CLASSES,
        "times_seconds": times.tolist(), "chroma_c_first": normalized.tolist(),
        "raw_chroma_l2": norms.tolist(), "rms": rms.tolist(), "silent": (rms < threshold).tolist(),
    }
    validate_evidence(evidence)
    return evidence


def validate_evidence(evidence: dict, audio: Path | None = None) -> None:
    try:
        _validate_evidence(evidence, audio)
    except (KeyError, TypeError, IndexError, OverflowError) as error:
        raise ValueError("Malformed acoustic evidence packet") from error


def _validate_evidence(evidence: dict, audio: Path | None = None) -> None:
    if not isinstance(evidence, dict) or evidence.get("schema_version") != SCHEMA:
        raise ValueError(f"Expected {SCHEMA}")
    recording = evidence["recording"]
    if evidence.get("pitch_classes") != PITCH_CLASSES:
        raise ValueError("Evidence pitch classes must be C-first")
    sample_rate, sample_count = recording["sample_rate_hz"], recording["sample_count"]
    if not isinstance(sample_rate, int) or isinstance(sample_rate, bool) or not 8000 <= sample_rate <= 192000:
        raise ValueError("Invalid evidence sample rate")
    if not isinstance(sample_count, int) or isinstance(sample_count, bool) or not 0 < sample_count <= 600 * sample_rate:
        raise ValueError("Invalid or oversized evidence sample count")
    if not math.isclose(recording["duration_seconds"], sample_count / sample_rate, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Evidence duration differs from sample count")
    validate_native_metadata(evidence["analysis"]["native_host"], sample_rate, sample_count)
    analysis = evidence["analysis"]
    if analysis.get("id") != "nnls-chroma-frozen-v1" or analysis.get("algorithm") != "NNLS-Chroma acoustic evidence" or any(
        analysis.get(flag) is not True for flag in ("no_chart_or_reference_consumed", "offline", "global_tuning")
    ):
        raise ValueError("Unexpected acoustic evidence source or analysis assumptions")
    if not isinstance(recording.get("audio_sha256"), str) or len(recording["audio_sha256"]) != 64 or any(char not in "0123456789abcdef" for char in recording["audio_sha256"]):
        raise ValueError("Invalid audio SHA256")
    times = np.asarray(evidence["times_seconds"], dtype=float)
    expected = np.arange(0, sample_count, 2048, dtype=float) / sample_rate
    if times.shape != expected.shape or not np.all(np.isfinite(times)) or not np.allclose(times, expected, rtol=0, atol=1.1e-9):
        raise ValueError("Evidence times must match native centers")
    chroma = np.asarray(evidence["chroma_c_first"], dtype=float)
    if chroma.shape != (len(times), 12) or not np.all(np.isfinite(chroma)) or np.any(chroma < 0):
        raise ValueError("Invalid evidence chroma")
    lengths = np.linalg.norm(chroma, axis=1)
    if np.any((lengths != 0) & ~np.isclose(lengths, 1, rtol=0, atol=1e-8)):
        raise ValueError("Evidence vectors must be zero or L2 normalized")
    for name in ("raw_chroma_l2", "rms"):
        values = np.asarray(evidence[name], dtype=float)
        if values.shape != times.shape or not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError(f"Invalid evidence {name}")
    if np.any((np.asarray(evidence["raw_chroma_l2"]) == 0) != (lengths == 0)):
        raise ValueError("Raw activation norms disagree with zero normalized vectors")
    if not isinstance(evidence["silent"], list) or len(evidence["silent"]) != len(times) or any(
        type(value) is not bool for value in evidence["silent"]
    ):
        raise ValueError("Silence flags must be one boolean per frame")
    threshold = evidence["analysis"]["silence"]["threshold"]
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("Invalid evidence silence threshold")
    if evidence["silent"] != (np.asarray(evidence["rms"]) < threshold).tolist():
        raise ValueError("Silence flags disagree with independent audio RMS")
    if audio is not None:
        signal, rate = lab.read_wav(audio)
        if sha(audio) != recording["audio_sha256"] or rate != sample_rate or len(signal) != sample_count:
            raise ValueError("Acoustic evidence does not match the supplied audio")
    json.dumps(evidence, allow_nan=False)


def extract_to_file(audio: Path, recording_id: str, output: Path) -> dict:
    # Runtime import avoids a module import cycle: the aligner lazily imports
    # this adapter only when an external acoustic packet is supplied.
    from chart_aligner import check_output_path, write_json_safely
    check_output_path(output, [audio], overwrite=False)
    evidence = extract(audio, recording_id)
    write_json_safely(output, evidence, [audio])
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--recording-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = extract_to_file(args.audio, args.recording_id, args.output)
    print(f"NNLS acoustic evidence: {len(evidence['times_seconds'])} frames; {evidence['analysis']['runtime_seconds']:.3f}s")


if __name__ == "__main__":
    main()
