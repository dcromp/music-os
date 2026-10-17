"""Build and serve short, local listening reviews without creating timing gold.

Prepared PCM samples are copied exactly. Model identities stay in a private key;
manual annotations begin empty in the separate browser interface. This utility
does not infer chords, section bounds, or permission to distribute recordings.
"""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
import random
import shutil
import tempfile
from urllib.parse import unquote, urlsplit
import wave

import chart_aligner
import lab

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "review"
DEFAULT_OUTPUT = ROOT / "generated" / "listening-review"
SCHEMA = "listening-review-1.0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def safe_id(value: str) -> bool:
    return lab.re_safe_case_id(value) and len(value) <= 80


def input_path(value: str, source_root: Path) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("Input paths must be explicit project-relative paths")
    result = (source_root / value).resolve(strict=True)
    if not result.is_relative_to(source_root.resolve()) or not result.is_file():
        raise ValueError("Input paths must identify files inside the project")
    return result


def clip_pcm(source: Path, target: Path, start: float, end: float) -> dict:
    if not finite(start) or not finite(end) or start < 0 or not start < end or end - start > 30:
        raise ValueError("Choose a finite listening window of up to 30 seconds")
    with wave.open(str(source), "rb") as audio:
        if audio.getsampwidth() != 2 or audio.getnchannels() != 1 or audio.getcomptype() != "NONE":
            raise ValueError("Review inputs must be prepared mono PCM16 WAV")
        rate = audio.getframerate()
        frames = audio.getnframes()
        # Round each endpoint once to the source sample grid, and persist it.
        first, last = round(start * rate), round(end * rate)
        if last > frames or first >= last:
            raise ValueError("Listening window is outside the prepared audio")
        audio.setpos(first)
        samples = audio.readframes(last - first)
    if len(samples) != (last - first) * 2:
        raise ValueError("Incomplete source audio")
    with wave.open(str(target), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(samples)
    return {"source_start_frame": first, "source_end_frame": last,
            "source_offset_seconds": first / rate, "source_end_seconds": last / rate,
            "duration_seconds": (last - first) / rate, "sample_rate_hz": rate,
            "source_duration_seconds": frames / rate, "source_audio_sha256": digest(source),
            "audio_sha256": digest(target), "sample_policy": "exact prepared PCM frames; no resampling"}


def clipped_candidate(chart: dict, source_id: str, recording: dict, origin: dict, name: str) -> dict:
    lab.validate_chart(chart)
    original = chart["recording"]
    if (original["id"] != source_id or original["audio_sha256"] != origin["source_audio_sha256"]
            or abs(original["duration_seconds"] - origin["source_duration_seconds"]) > 1 / origin["sample_rate_hz"]
            or original["sample_rate_hz"] != origin["sample_rate_hz"]):
        raise ValueError("Prediction must match source ID, hash, duration and sample rate")
    start, end = origin["source_offset_seconds"], origin["source_end_seconds"]
    events = [{"start_seconds": max(event["start_seconds"], start) - start,
               "end_seconds": min(event["end_seconds"], end) - start, "label": event["label"]}
              for event in chart["chords"] if event["end_seconds"] > start and event["start_seconds"] < end]
    if not events:
        raise ValueError("Prediction has no events in the listening window")
    result = {"schema_version": "1.0", "recording": recording,
              "analysis": {"id": f"{recording['id']}-{name}", "algorithm": name,
                           "version": "blinded-review-1", "runtime_seconds": 0,
                           "parameters": {"status": "unreviewed model output; never timing gold"}},
              "chords": events}
    lab.validate_chart(result)
    return result


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def build(spec: dict, output: Path, source_root: Path = ROOT.parent) -> dict:
    if (not isinstance(spec, dict) or spec.get("schema_version") != SCHEMA
            or not isinstance(spec.get("cases"), list) or not 1 <= len(spec["cases"]) <= 64):
        raise ValueError(f"Expected a nonempty {SCHEMA} specification")
    if not safe_id(spec.get("pack_id", "listening-review")):
        raise ValueError("A safe pack ID is required")
    if spec.get("bounds_status") != "frozen-listening-windows":
        raise ValueError("Freeze listening bounds before building; these are not verified section boundaries")
    output = output.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory; existing reviews are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".listening-review-", dir=output.parent))
    manifest = {"schema_version": SCHEMA, "pack_id": spec.get("pack_id", "listening-review"),
                "status": "listening drafts; no timing gold", "cases": [],
                "annotation_policy": "Blank audio-only annotation first; candidate exposure is recorded. Human labels require independent verification before evaluation."}
    key = {"schema_version": SCHEMA, "cases": []}
    seen = set()
    try:
        for case in spec["cases"]:
            if not isinstance(case, dict):
                raise ValueError("Review cases must be objects")
            case_id = case.get("id")
            if not safe_id(case_id) or case_id in seen:
                raise ValueError("Review case IDs must be unique safe identifiers")
            seen.add(case_id)
            title = case.get("title")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("A review title is required")
            folder = staging / "cases" / case_id
            folder.mkdir(parents=True)
            audio = input_path(case["audio"], source_root)
            source_id = case["source_recording_id"]
            if not safe_id(source_id):
                raise ValueError("A source recording ID is required")
            if digest(audio) != case["source_audio_sha256"]:
                raise ValueError("Source audio hash does not match the frozen specification")
            origin = clip_pcm(audio, folder / "audio.wav", case["start_seconds"], case["end_seconds"])
            recording = {"id": case_id, "title": title, "duration_seconds": origin["duration_seconds"],
                         "sample_rate_hz": origin["sample_rate_hz"], "audio_sha256": origin["audio_sha256"]}
            paths = case.get("candidates", [])
            if not isinstance(paths, list) or not 1 <= len(paths) <= 8:
                raise ValueError("Choose 1–8 distinct prediction files")
            normalized = []
            for item in paths:
                candidate = {"path": item, "time_origin": "source"} if isinstance(item, str) else item
                if (not isinstance(candidate, dict) or set(candidate) != {"path", "time_origin"}
                        or not isinstance(candidate["path"], str) or not candidate["path"]
                        or candidate["time_origin"] not in ("source", "excerpt")):
                    raise ValueError("Candidates need a project-relative path and explicit source/excerpt time_origin")
                normalized.append(candidate)
            if len({candidate["path"] for candidate in normalized}) != len(normalized):
                raise ValueError("Prediction files must be distinct")
            paths = normalized
            random.Random(hashlib.sha256(case_id.encode()).hexdigest()).shuffle(paths)
            candidates, answers = [], []
            for index, candidate in enumerate(paths):
                relative = candidate["path"]
                chart_path = input_path(relative, source_root)
                chart = json.loads(chart_path.read_text(encoding="utf-8"))
                name = f"Candidate {chr(65 + index)}"
                filename = f"candidate-{chr(97 + index)}.json"
                if candidate["time_origin"] == "excerpt":
                    candidate_origin = {**origin, "source_audio_sha256": origin["audio_sha256"],
                                        "source_duration_seconds": origin["duration_seconds"],
                                        "source_offset_seconds": 0, "source_end_seconds": origin["duration_seconds"]}
                    blinded = clipped_candidate(chart, case_id, recording, candidate_origin, name)
                else:
                    blinded = clipped_candidate(chart, source_id, recording, origin, name)
                write_json(folder / filename, blinded)
                candidates.append({"name": name, "url": f"/cases/{case_id}/{filename}"})
                answers.append({"candidate": name, "source_prediction": relative,
                                "prediction_sha256": digest(chart_path), "analysis": chart["analysis"],
                                "time_origin": candidate["time_origin"]})
            if "untimed_chart" in case:
                chart = json.loads(input_path(case["untimed_chart"], source_root).read_text(encoding="utf-8"))
                chart_aligner.validate_untimed_chart(chart)
                if chart.get("mode", "finite") != "finite":
                    raise ValueError("Listening packs require separate finite untimed chart inputs")
                chart["recording"] = {"id": case_id, "title": title, "audio_sha256": origin["audio_sha256"]}
                # This file is private, separate from source offsets and annotation times.
                write_json(folder / "untimed-chart.json", chart)
            write_json(folder / "origin.json", {"source_recording_id": source_id, **origin})
            manifest["cases"].append({"id": case_id, "name": title, "recording": recording,
                                       "origin": {"source_recording_id": source_id, **origin},
                                       "split": case.get("split", "unassigned"),
                                       "bounds_description": case.get("bounds_description", "Frozen listening window, not a verified musical section"),
                                       "audio_url": f"/cases/{case_id}/audio.wav", "candidates": candidates})
            key["cases"].append({"id": case_id, "candidates": answers})
        write_json(staging / "manifest.json", manifest)
        write_json(staging / "private-candidate-key.json", key)
        write_json(staging / "build-spec.json", spec)
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging)
        raise
    return manifest


def public_files(pack: Path) -> dict[str, Path]:
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("Invalid review pack manifest")
    files = {"/": STATIC / "index.html", "/index.html": STATIC / "index.html",
             "/app.js": STATIC / "app.js", "/style.css": STATIC / "style.css",
             "/manifest.json": pack / "manifest.json"}
    seen = set()
    for case in manifest["cases"]:
        identifier = case["id"]
        if not safe_id(identifier) or identifier in seen:
            raise ValueError("Invalid or duplicate review case ID")
        seen.add(identifier)
        expected_audio = f"/cases/{identifier}/audio.wav"
        if case["audio_url"] != expected_audio:
            raise ValueError("Unexpected review audio URL")
        files[expected_audio] = pack / "cases" / identifier / "audio.wav"
        for index, candidate in enumerate(case["candidates"]):
            expected = f"/cases/{identifier}/candidate-{chr(97 + index)}.json"
            if candidate["url"] != expected:
                raise ValueError("Unexpected review candidate URL")
            files[expected] = pack / "cases" / identifier / f"candidate-{chr(97 + index)}.json"
    for path in files.values():
        root = STATIC.resolve() if path.is_relative_to(STATIC) else pack.resolve()
        if not safe_public_file(path, root, pack.resolve()):
            raise ValueError("Review public assets must be regular files inside their fixed root")
    return files


def safe_public_file(path: Path, root: Path, pack: Path) -> bool:
    """Reject symlinks and hard-link aliases to private review assets."""
    if not path.is_file() or not path.resolve().is_relative_to(root):
        return False
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root)):
        return False
    public_stat = path.stat()
    private_paths = [pack / "private-candidate-key.json", pack / "build-spec.json"]
    private_paths.extend((pack / "cases").glob("*/origin.json"))
    private_paths.extend((pack / "cases").glob("*/untimed-chart.json"))
    for private in private_paths:
        if private.is_file():
            private_stat = private.stat()
            if (public_stat.st_dev, public_stat.st_ino) == (private_stat.st_dev, private_stat.st_ino):
                return False
    return True


class ReviewHandler(lab.BenchHandler):
    def __init__(self, *args, files: dict[str, Path], **kwargs):
        self.public_files = files
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def translate_path(self, path: str) -> str:
        url = urlsplit(path)
        decoded = unquote(url.path)
        candidate = self.public_files.get(decoded)
        if not candidate or url.query or ".." in decoded.split("/") or "\\" in decoded:
            return str(STATIC / "__not_found__")
        # Recheck on each request in case a regular file was replaced by a symlink.
        root = STATIC.resolve() if candidate.is_relative_to(STATIC) else self.pack_root
        if not safe_public_file(candidate, root, self.pack_root):
            return str(STATIC / "__not_found__")
        return str(candidate)

    @property
    def pack_root(self) -> Path:
        return self.public_files["/manifest.json"].parent.resolve()

    def send_head(self):
        path = Path(self.translate_path(self.path))
        mapped = self.public_files.get(unquote(urlsplit(self.path).path))
        if path.name != "primary.json" or path != mapped:
            return super().send_head()
        # Hash the response bytes, not a separately reopened chart. The client
        # can verify its optional overlay even without browser WebCrypto.
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "Chart file not found")
            return None
        self._remaining_bytes = None
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Music-OS-Chart-SHA256", hashlib.sha256(body).hexdigest())
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        return io.BytesIO(body)

    def do_GET(self):
        SimpleHTTPRequestHandler.do_GET(self)

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; media-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


def serve(pack: Path, port: int) -> None:
    files = public_files(pack.resolve())
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(ReviewHandler, files=files))
    print(f"Listening review: http://127.0.0.1:{port}/ — local files only; Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build")
    builder.add_argument("--spec", type=Path, required=True)
    builder.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    server = sub.add_parser("serve")
    server.add_argument("--pack", type=Path, default=DEFAULT_OUTPUT)
    server.add_argument("--port", type=int, default=8068)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build(json.loads(args.spec.read_text(encoding="utf-8")), args.output)
            print(json.dumps({"pack": str(args.output.resolve()), "cases": len(result["cases"]), "status": result["status"]}))
        else:
            serve(args.pack, args.port)
    except (ValueError, KeyError, OSError, json.JSONDecodeError, wave.Error) as error:
        parser.exit(2, f"Review pack failed: {error}\n")


if __name__ == "__main__":
    main()
