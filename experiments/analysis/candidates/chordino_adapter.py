"""Local WAV/Vamp adapter for the source-built Chordino candidate.

The small native host and plugin are built separately; see docs/CHORDINO_SETUP.md.
No downloads, model training or source-audio changes occur in this adapter.
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
PLUGIN_REVISION = "4c5f214a75cb354f8d8c933e161377c5b4d83713"
SDK_REVISION = "44c2487763eb248a933e9eff9169cfadee375009"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab


def normalize_label(native: str) -> str:
    # Native Chordino display syntax; retain extensions and absolute bass notes.
    return native.replace(":min", "m").replace(":maj", "maj").replace(":", "")


def intervals_from_native(text: str, duration: float) -> tuple[list[dict], dict]:
    """Retain genuine N events, but remove the documented terminal N sentinel."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration must be positive and finite")
    metadata, native_events = None, []
    for line in text.splitlines():
        if line.startswith("#"):
            if metadata is not None:
                raise ValueError("Duplicate host metadata")
            metadata = json.loads(line[1:])
            continue
        if not line.strip():
            continue
        timestamp, label = line.split("\t", 1)
        timestamp = float(timestamp)
        if not math.isfinite(timestamp) or not label.strip():
            raise ValueError("Invalid native timestamp or chord label")
        if native_events and timestamp < native_events[-1][0]:
            raise ValueError("Native events must be ordered")
        native_events.append((timestamp, label.strip()))
    if not isinstance(metadata, dict) or metadata.get("final_N_is_termination_marker") is not True:
        raise ValueError("Host metadata must identify Chordino's terminal sentinel")
    if len(native_events) < 2 or native_events[-1][1] != "N":
        raise ValueError("Expected native events followed by terminal N")
    native_events.pop()  # Only this last N is artificial, per upstream source.
    boundaries = []
    for timestamp, native in native_events:
        start = max(0.0, timestamp)
        if start >= duration:
            continue
        event = {"start_seconds": start, "end_seconds": duration,
                 "label": normalize_label(native), "native_label": native}
        if boundaries and boundaries[-1]["start_seconds"] == start:
            boundaries[-1] = event
        else:
            boundaries.append(event)
    if not boundaries:
        raise ValueError("No in-range native chord events")
    # A host delay is not a guessed chord. Make any initial uncovered range explicit.
    if boundaries[0]["start_seconds"] > 0:
        boundaries.insert(0, {"start_seconds": 0.0, "end_seconds": duration,
                              "label": "X", "native_label": "uncovered host interval"})
    events = []
    for event in boundaries:
        if events and events[-1]["label"] == event["label"]:
            continue
        if events:
            events[-1]["end_seconds"] = event["start_seconds"]
        events.append(event)
    return events, metadata


def analyze(audio: Path, recording_id: str, host: Path, plugin_dir: Path, build_info: dict) -> dict:
    started = time.perf_counter()
    samples, sample_rate = lab.read_wav(audio)
    duration = len(samples) / sample_rate
    environment = os.environ.copy()
    environment["VAMP_PATH"] = str(plugin_dir.resolve())
    process = subprocess.run([str(host.resolve()), str(audio.resolve())],
                             capture_output=True, text=True, timeout=180, env=environment)
    if process.returncode:
        raise ValueError(f"Native host exited {process.returncode}: {process.stderr[-1500:]}")
    events, metadata = intervals_from_native(process.stdout, duration)
    if metadata.get("sample_rate_hz") != sample_rate:
        raise ValueError("Host sample rate differs from decoded WAV")
    if metadata.get("frames") != len(samples):
        raise ValueError("Host frame count differs from decoded WAV")
    result = {"schema_version": "1.0",
              "recording": {"id": recording_id, "title": audio.stem, "duration_seconds": duration,
                            "sample_rate_hz": sample_rate,
                            "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest()},
              "analysis": {"id": "chordino-nnls-hmm-v1", "algorithm": "Chordino-NNLS-Chroma",
                           "version": "adapter-0.1", "runtime_seconds": time.perf_counter() - started,
                           "parameters": {"native_host": metadata, "build": build_info,
                                          "device": "cpu", "smoothing": "upstream default HMM/Viterbi",
                                          "terminal_N": "remove last native termination marker only; extend final active event to input duration",
                                          "runtime_includes": "WAV validation and one native process including plugin loading"}},
              "chords": events}
    lab.validate_chart(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recording-id")
    parser.add_argument("--batch-manifest", type=Path)
    parser.add_argument("--output-root", type=Path)
    native = ROOT / "experiments/candidate-assets/chordino-native"
    parser.add_argument("--host", type=Path, default=native / "chordino-host")
    parser.add_argument("--plugin-dir", type=Path, default=native)
    parser.add_argument("--build-info", type=Path, default=native / "buildinfo.json")
    args = parser.parse_args()
    if not args.host.is_file() or not args.build_info.is_file():
        parser.error("Build the project-local native host/plugin first; see docs/CHORDINO_SETUP.md")
    build_info = json.loads(args.build_info.read_text())
    if build_info["plugin"]["revision"] != PLUGIN_REVISION or build_info["vamp_sdk"]["revision"] != SDK_REVISION:
        raise ValueError("Native source versions differ from reviewed revisions")
    for name, path in (("chordino-host", args.host), ("nnls-chroma.dylib", args.plugin_dir / "nnls-chroma.dylib")):
        if hashlib.sha256(path.read_bytes()).hexdigest() != build_info["binaries"][name]["sha256"]:
            raise ValueError(f"{name} hash differs from its build provenance")
    if (args.plugin_dir / "chord.dict").exists():
        raise ValueError("This benchmark requires the reviewed built-in chord dictionary")
    jobs = []
    if args.batch_manifest:
        manifest = json.loads(args.batch_manifest.read_text())
        output_root = args.output_root or args.batch_manifest.parent
        seen = set()
        for case in manifest["cases"]:
            case_id = case["id"]
            if not isinstance(case_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", case_id) or case_id in seen:
                raise ValueError("Case IDs must be unique safe identifiers")
            seen.add(case_id)
            audio = (args.batch_manifest.parent / case["audio"]).resolve()
            if not audio.is_relative_to(args.batch_manifest.parent.resolve()):
                raise ValueError("Case audio leaves manifest directory")
            jobs.append((audio, output_root / "cases" / case_id / "chordino.json", case_id))
    else:
        if not args.audio or not args.output or not args.recording_id:
            parser.error("Provide --audio, --output and --recording-id")
        jobs = [(args.audio, args.output, args.recording_id)]
    failures = []
    started = time.perf_counter()
    for audio, output, recording_id in jobs:
        try:
            if output.resolve() == audio.resolve():
                raise ValueError("Output must not overwrite audio")
            output.unlink(missing_ok=True)
            result = analyze(audio, recording_id, args.host, args.plugin_dir, build_info)
            lab.write_json(output, result)
            print(f"Chordino {recording_id}: {result['analysis']['runtime_seconds']:.3f}s", flush=True)
        except Exception as error:
            failures.append({"id": recording_id, "error": str(error)})
            print(f"Chordino failed {recording_id}: {error}", file=sys.stderr, flush=True)
    if args.batch_manifest:
        lab.write_json(output_root / "chordino-batch-summary.json", {
            "cases": len(jobs), "failures": failures,
            "batch_wall_seconds": time.perf_counter() - started, "build": build_info})
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
