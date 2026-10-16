"""Local experiment tooling. No model downloads or YouTube access.

This simple spectral-template detector is a baseline, not a guitar transcription
claim. The synthetic fixture checks plumbing; evaluate real recordings separately.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "experiments" / "generated"
BENCH = ROOT / "experiments" / "bench"
VERSION = "0.1.0"
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def validate_chart(chart: dict) -> None:
    def number(value) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def text(value) -> bool:
        return isinstance(value, str) and bool(value.strip())

    if not isinstance(chart, dict) or chart.get("schema_version") != "1.0":
        raise ValueError("Expected schema_version 1.0")
    recording = chart.get("recording", {})
    if not isinstance(recording, dict):
        raise ValueError("Recording must be an object")
    duration = recording.get("duration_seconds")
    if not number(duration) or duration <= 0:
        raise ValueError("recording.duration_seconds must be finite and positive")
    if not text(recording.get("id")) or not text(recording.get("title")):
        raise ValueError("Recording ID and title are required")
    if not number(recording.get("sample_rate_hz")) or recording["sample_rate_hz"] <= 0:
        raise ValueError("recording.sample_rate_hz must be finite and positive")
    analysis = chart.get("analysis")
    if not isinstance(analysis, dict) or not all(text(analysis.get(k)) for k in ("id", "algorithm", "version")):
        raise ValueError("Analysis ID, algorithm and version are required")
    if not number(analysis.get("runtime_seconds")) or analysis["runtime_seconds"] < 0:
        raise ValueError("analysis.runtime_seconds must be finite and nonnegative")
    chords = chart.get("chords")
    if not isinstance(chords, list) or not chords:
        raise ValueError("Expected a nonempty chord timeline")
    previous_end = 0.0
    for chord in chords:
        if not isinstance(chord, dict):
            raise ValueError("Each chord event must be an object")
        start, end = chord.get("start_seconds"), chord.get("end_seconds")
        if not all(number(v) for v in (start, end)):
            raise ValueError("Chord timestamps must be finite seconds")
        if start < previous_end or end <= start or end > duration + 0.001:
            raise ValueError("Chord intervals must be ordered, nonoverlapping and within audio duration")
        if not text(chord.get("label")):
            raise ValueError("Chord label is required; use N for no chord")
        if "confidence" in chord and (not number(chord["confidence"]) or not 0 <= chord["confidence"] <= 1):
            raise ValueError("Optional confidence must be a finite number from 0 to 1")
        previous_end = end
    for key in ("beats_seconds", "downbeats_seconds"):
        points = chart.get(key, [])
        if not isinstance(points, list) or any(
            not number(v) or v < 0 or v > duration + 0.001
            for v in points
        ) or any(a >= b for a, b in zip(points, points[1:])):
            raise ValueError(f"{key} must be strictly increasing timestamps in seconds")


def load_chart(path: Path) -> dict:
    chart = json.loads(path.read_text(encoding="utf-8"))
    validate_chart(chart)
    return chart


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("Use 16-bit PCM WAV; the prepare command converts other formats")
        sample_rate = audio.getframerate()
        channels = audio.getnchannels()
        data = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float64)
    return data.reshape(-1, channels).mean(axis=1) / 32768.0, sample_rate


def create_fixture(directory: Path) -> tuple[Path, Path]:
    """Known triads, silence, offbeat boundaries and an inversion; not a guitar."""
    sample_rate = 22050
    events = [
        ("C", [48, 52, 55], 3.0),
        ("Am", [45, 48, 52], 2.75),
        ("F", [53, 57, 60], 3.25),
        ("G", [43, 47, 50], 3.0),
        ("N", [], 1.0),
        ("Dm", [50, 53, 57], 2.5),
        ("Em", [52, 55, 59], 3.5),
        ("C", [52, 55, 60], 3.0),
    ]
    segments, chords, position = [], [], 0
    for label, midi_notes, duration in events:
        count = round(duration * sample_rate)
        t = np.arange(count) / sample_rate
        signal = np.zeros(count)
        for note in midi_notes:
            frequency = 440.0 * 2 ** ((note - 69) / 12)
            signal += sum(np.sin(2 * np.pi * frequency * h * t) / h**2 for h in (1, 2, 3))
        if midi_notes:
            signal /= np.max(np.abs(signal))
            # Short attack/release helps distinguish audio transitions from label changes.
            fade = min(round(0.025 * sample_rate), count // 2)
            signal[:fade] *= np.linspace(0, 1, fade)
            signal[-fade:] *= np.linspace(1, 0, fade)
            signal *= 0.7
        segments.append(signal)
        chords.append({"start_seconds": position / sample_rate,
                       "end_seconds": (position + count) / sample_rate, "label": label})
        position += count
    directory.mkdir(parents=True, exist_ok=True)
    audio_path, reference_path = directory / "audio.wav", directory / "reference.json"
    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes((np.concatenate(segments) * 32767).astype("<i2").tobytes())
    duration = position / sample_rate
    reference = {
        "schema_version": "1.0",
        "recording": {"id": "synthetic-triads-v1", "title": "Synthetic triads — setup fixture",
                      "duration_seconds": duration, "sample_rate_hz": sample_rate,
                      "provenance": "Generated locally; not a real song or guitar performance"},
        "analysis": {"id": "synthetic-reference-v1", "algorithm": "fixture-reference",
                     "version": VERSION, "runtime_seconds": 0, "parameters": {}},
        "chords": chords,
        "beats_seconds": [i / 2 for i in range(math.ceil(duration * 2))],
        "downbeats_seconds": [float(i) for i in range(0, math.ceil(duration), 2)],
    }
    validate_chart(reference)
    write_json(reference_path, reference)
    return audio_path, reference_path


def detect(audio_path: Path, recording_id: str | None = None) -> dict:
    started = time.perf_counter()
    signal, sample_rate = read_wav(audio_path)
    if not len(signal):
        raise ValueError("Audio is empty")
    duration = len(signal) / sample_rate
    frame_size = 2 ** math.ceil(math.log2(sample_rate * 0.18))
    hop = max(1, round(sample_rate * 0.025))
    padding = frame_size // 2
    padded = np.pad(signal, (padding, padding))
    window = np.hanning(frame_size)
    frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    selected = np.flatnonzero((frequencies >= 65) & (frequencies <= 2000))
    pitch_classes = np.rint(69 + 12 * np.log2(frequencies[selected] / 440)).astype(int) % 12
    templates, labels = [], []
    for root, name in enumerate(NOTES):
        for intervals, suffix in (([0, 4, 7], ""), ([0, 3, 7], "m")):
            template = np.zeros(12)
            template[(root + np.array(intervals)) % 12] = 1 / np.sqrt(3)
            templates.append(template)
            labels.append(name + suffix)
    templates = np.array(templates)
    peak = float(np.max(np.abs(signal)))
    threshold = max(1e-5, peak * 0.025)
    predictions = []
    for offset in range(0, len(signal), hop):
        frame = padded[offset:offset + frame_size]
        if float(np.sqrt(np.mean(frame**2))) < threshold:
            label = "N"
        else:
            powers = np.abs(np.fft.rfft(frame * window))[selected] ** 2
            chroma = np.bincount(pitch_classes, weights=powers, minlength=12)
            norm = np.linalg.norm(chroma)
            label = labels[int(np.argmax(templates @ (chroma / norm)))] if norm else "N"
        predictions.append((offset / sample_rate, label))
    chords = []
    for timestamp, label in predictions:
        if chords and chords[-1]["label"] == label:
            continue
        if chords:
            chords[-1]["end_seconds"] = timestamp
        chords.append({"start_seconds": timestamp, "end_seconds": duration, "label": label})
    result = {
        "schema_version": "1.0",
        "recording": {"id": recording_id or audio_path.stem, "title": audio_path.stem,
                      "duration_seconds": duration, "sample_rate_hz": sample_rate,
                      "provenance": "User-supplied local audio; permission recorded separately"},
        "analysis": {"id": f"spectral-template-{VERSION}", "algorithm": "spectral-template",
                     "version": VERSION, "runtime_seconds": time.perf_counter() - started,
                     "parameters": {"frame_size": frame_size, "hop_samples": hop,
                                    "vocabulary": "24 major/minor chords plus N",
                                    "smoothing": "none", "source_separation": "none"}},
        "chords": chords,
    }
    validate_chart(result)
    return result


def agreement(reference: dict, prediction: dict) -> dict:
    validate_chart(reference)
    validate_chart(prediction)
    if reference["recording"]["id"] != prediction["recording"]["id"]:
        raise ValueError("Reference and prediction must identify the same recording")
    duration = reference["recording"]["duration_seconds"]
    if abs(duration - prediction["recording"]["duration_seconds"]) > 0.05:
        raise ValueError("Reference and prediction durations differ")
    covered = sum(c["end_seconds"] - c["start_seconds"] for c in reference["chords"])
    matching = 0.0
    for expected in reference["chords"]:
        for actual in prediction["chords"]:
            if expected["label"] == actual["label"]:
                matching += max(0.0, min(expected["end_seconds"], actual["end_seconds"])
                                - max(expected["start_seconds"], actual["start_seconds"]))
    return {"duration_weighted_exact_label_agreement": matching / covered,
            "reference_coverage_fraction": covered / duration,
            "reference_events": len(reference["chords"]),
            "predicted_events": len(prediction["chords"]),
            "audio_duration_seconds": duration,
            "analysis_runtime_seconds": prediction["analysis"]["runtime_seconds"],
            "limitations": "Exact-label duration metric on supplied annotations; not mir_eval, and applicability depends on the reference material"}


def smoke(directory: Path) -> dict:
    audio_path, reference_path = create_fixture(directory)
    reference = load_chart(reference_path)
    prediction = detect(audio_path, reference["recording"]["id"])
    prediction["recording"] = reference["recording"].copy()
    write_json(directory / "baseline.json", prediction)
    metrics = agreement(reference, prediction)
    metrics["test_material"] = "Synthetic triads/silence fixture; not real-guitar or mixed-song evidence"
    metrics["environment"] = {"platform": platform.platform(), "architecture": platform.machine(),
                              "python": platform.python_version(), "numpy": np.__version__}
    write_json(directory / "metrics.json", metrics)
    # A synthetic check is a diagnostic, never a claim about mixed songs.
    if metrics["duration_weighted_exact_label_agreement"] < 0.8:
        raise ValueError(f"Synthetic smoke result needs investigation: {metrics}")
    return metrics


class BenchHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = Path(self.translate_path(self.path))
        self._remaining_bytes = None
        if path.suffix.lower() != ".wav":
            return super().send_head()
        try:
            stream = path.open("rb")
        except OSError:
            self.send_error(404, "Audio file not found")
            return None
        size = path.stat().st_size
        start, end = 0, size - 1
        header = self.headers.get("Range")
        if header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
            if not match or not any(match.groups()):
                stream.close()
                self.send_error(416, "Unsupported audio range")
                return None
            if match[1]:
                start = int(match[1])
                end = min(int(match[2]), end) if match[2] else end
            else:
                start = max(0, size - int(match[2]))
            if start >= size or start > end:
                stream.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        stream.seek(start)
        self._remaining_bytes = end - start + 1
        return stream

    def copyfile(self, source, outputfile):
        if self._remaining_bytes is None:
            return super().copyfile(source, outputfile)
        remaining = self._remaining_bytes
        while remaining:
            data = source.read(min(65536, remaining))
            if not data:
                break
            outputfile.write(data)
            remaining -= len(data)

    def do_GET(self) -> None:
        if self.path == "/api/suite":
            folder = GENERATED / "synthetic-suite"
            manifest = folder / "manifest.json"
            if not manifest.exists():
                self.send_error(404, "Generate the synthetic suite first")
                return
            cases = []
            for case in json.loads(manifest.read_text())["cases"]:
                case_id = case["id"]
                if not re_safe_case_id(case_id):
                    continue
                candidates = [{"name": "Known reference", "url": f"/suite/{case_id}/reference.json"}]
                for name in ("baseline", "btc", "crema", "chordmini", "chordino"):
                    path = folder / "cases" / case_id / f"{name}.json"
                    if path.exists():
                        display_name = {"btc": "BTC", "chordmini": "ChordMini / ChordNet"}.get(name, name.title())
                        candidates.append({"name": display_name,
                                           "url": f"/suite/{case_id}/{name}.json"})
                cases.append({"id": case_id, "name": case["name"], "level": case["level"],
                              "condition": case["condition"], "audio_url": f"/suite/{case_id}/audio.wav",
                              "candidates": candidates})
            payload = json.dumps({"cases": cases}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/api/demo":
            payload = json.dumps({"audio_url": "/demo/audio.wav", "candidates": [
                {"name": "Known reference", "url": "/demo/reference.json"},
                {"name": "Template baseline", "url": "/demo/baseline.json"},
            ]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()

    def translate_path(self, path: str) -> str:
        # Resolve via a fixed virtual root. Do not expose repository files/secrets.
        virtual = super().translate_path(path)
        relative = Path(virtual).relative_to(BENCH)
        if relative.parts and relative.parts[0] == "suite":
            allowed = {"audio.wav", "reference.json", "baseline.json", "btc.json", "crema.json", "chordmini.json", "chordino.json"}
            if len(relative.parts) == 3 and re_safe_case_id(relative.parts[1]) and relative.parts[2] in allowed:
                return str(GENERATED / "synthetic-suite" / "cases" / relative.parts[1] / relative.parts[2])
            return str(BENCH / "__not_found__")
        if relative.parts and relative.parts[0] == "demo":
            allowed = {"audio.wav", "reference.json", "baseline.json"}
            if len(relative.parts) == 2 and relative.parts[1] in allowed:
                return str(GENERATED / relative.parts[1])
            return str(BENCH / "__not_found__")
        return virtual

    def list_directory(self, path: str):
        self.send_error(404, "Directory listing disabled")
        return None


def re_safe_case_id(value: str) -> bool:
    return isinstance(value, str) and bool(value) and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in value)


def serve(port: int) -> None:
    if not (BENCH / "index.html").exists():
        raise ValueError("Browser bench has not been created")
    if not all((GENERATED / name).exists() for name in ("audio.wav", "reference.json", "baseline.json")):
        smoke(GENERATED)
    handler = partial(BenchHandler, directory=str(BENCH))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"Guitar bench: http://127.0.0.1:{port}/ — Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def protect_inputs(output: Path, *inputs: Path) -> None:
    if output.resolve() in {path.resolve() for path in inputs}:
        raise ValueError("Output must not overwrite an input recording or reference chart")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture", "smoke"):
        command = sub.add_parser(name)
        command.add_argument("--output-dir", type=Path, default=GENERATED)
    prepare = sub.add_parser("prepare", help="Normalize local audio to mono PCM WAV with FFmpeg")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("output", type=Path)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("audio", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--recording-id")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("reference", type=Path)
    evaluate.add_argument("prediction", type=Path)
    evaluate.add_argument("--output", type=Path)
    server = sub.add_parser("serve")
    server.add_argument("--port", type=int, default=8067)
    args = parser.parse_args()
    try:
        if args.command == "fixture":
            print(create_fixture(args.output_dir))
        elif args.command == "smoke":
            print(json.dumps(smoke(args.output_dir), indent=2))
        elif args.command == "prepare":
            if args.input.resolve() == args.output.resolve() or args.output.exists():
                raise ValueError("Choose a new output path; prepare never overwrites a recording")
            if not shutil.which("ffmpeg"):
                raise ValueError("FFmpeg must be available for prepare")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(args.input),
                            "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(args.output)], check=True)
            print(args.output)
        elif args.command == "analyze":
            protect_inputs(args.output, args.audio)
            result = detect(args.audio, args.recording_id)
            write_json(args.output, result)
            print(f"Saved {len(result['chords'])} events to {args.output}; "
                  f"analysis took {result['analysis']['runtime_seconds']:.3f}s")
        elif args.command == "evaluate":
            if args.output:
                protect_inputs(args.output, args.reference, args.prediction)
            result = agreement(load_chart(args.reference), load_chart(args.prediction))
            if args.output:
                write_json(args.output, result)
            print(json.dumps(result, indent=2))
        elif args.command == "serve":
            serve(args.port)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
