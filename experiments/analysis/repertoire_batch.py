"""Prepare the reviewed first ten recordings without supplying teaching charts.

Reuse exactly the two audited pilot recordings and their saved detector outputs.
Import the other eight explicit public URLs through the isolated YouTube importer.
Every case is verified in staging; complete manifests are published only after all
ten cases succeed. A safe status report survives individual acquisition failures.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
import wave

import youtube_import

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW = ROOT / "catalogue" / "first-ten-review.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "generated" / "repertoire-first-ten-v1"
DEFAULT_CACHE = ROOT / "experiments" / "generated" / "youtube-pilot" / "manifest.json"
VERSION = "0.2.0"
SCHEMA = "first-ten-review-1.0"
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
CACHED_IDS = frozenset({"radiohead-creep-youtube-20261010", "oasis-wonderwall-youtube-20261010"})
SOURCE_USE = "Requested local founder algorithm experiment; recording explicitly selected in the reviewed first-ten catalogue; commercial clearance not established"


class BatchFailure(ValueError):
    """Only fixed, safe local diagnostics are exposed to the caller."""


def finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def sha256(path: Path) -> str:
    return youtube_import.sha256(path)


def no_symlinks(path: Path, root: Path) -> None:
    absolute = path.absolute()
    if not absolute.is_relative_to(root.absolute()):
        raise BatchFailure("Inputs and outputs must stay inside the selected project")
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink():
            raise BatchFailure("Symlink inputs and output directories are unsupported")
        if candidate == root.absolute():
            break


def project_file(path: Path, root: Path) -> Path:
    no_symlinks(path, root)
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise BatchFailure("Expected an existing regular project-local input file") from error
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise BatchFailure("Expected a regular project-local input file")
    return resolved


def load_json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise BatchFailure("A local JSON input could not be read") from error
    if not isinstance(result, dict):
        raise BatchFailure("Expected a JSON object")
    return result


def reviewed_songs(review: dict) -> list[dict]:
    songs = review.get("songs")
    if review.get("schema_version") != SCHEMA or not isinstance(songs, list) or len(songs) != 10:
        raise BatchFailure("Expected exactly ten songs in a first-ten-review-1.0 catalogue")
    song_ids, recording_ids, video_ids, cached_ids = set(), set(), set(), set()
    for song in songs:
        if not isinstance(song, dict) or not isinstance(song.get("id"), str) or not SAFE_ID.fullmatch(song["id"]):
            raise BatchFailure("Song IDs must contain 1–64 safe letters, digits, underscores or hyphens")
        for field in ("title", "artist"):
            if not isinstance(song.get(field), str) or not song[field].strip() or len(song[field]) > 500:
                raise BatchFailure("Every reviewed song needs a bounded title and artist")
        selected = song.get("selected_recording")
        if not isinstance(selected, dict) or not isinstance(selected.get("recording_id"), str) or not SAFE_ID.fullmatch(selected["recording_id"]):
            raise BatchFailure("Every selected recording needs a safe 1–64 character recording ID")
        if not isinstance(selected.get("url"), str):
            raise BatchFailure("Every selected recording needs an explicit YouTube URL")
        url, video_id = youtube_import.canonical_url(selected["url"])
        if selected.get("video_id") != video_id:
            raise BatchFailure("Selected video ID and explicit YouTube URL disagree")
        if song["id"] in song_ids or selected["recording_id"] in recording_ids or video_id in video_ids:
            raise BatchFailure("Song, recording and selected video IDs must each be unique")
        song_ids.add(song["id"]); recording_ids.add(selected["recording_id"]); video_ids.add(video_id)
        expected = selected.get("expected_uploader")
        if expected is not None and not (isinstance(expected, str) and expected.strip() or
                isinstance(expected, list) and expected and all(isinstance(item, str) and item.strip() for item in expected)):
            raise BatchFailure("Expected uploader must be one name or a nonempty list of names")
        cached = song.get("cached_example")
        if cached is not None:
            if (not isinstance(cached, dict) or cached.get("recording_id") != selected["recording_id"] or
                    cached.get("recording_id") not in CACHED_IDS or
                    not isinstance(cached.get("audio_sha256"), str) or not HASH.fullmatch(cached["audio_sha256"]) or
                    not finite_number(cached.get("duration_seconds")) or not 0 < cached["duration_seconds"] <= 600):
                raise BatchFailure("Cached rows must pin the audited Creep or Wonderwall ID, audio hash and duration")
            cached_ids.add(cached["recording_id"])
    if cached_ids != CACHED_IDS:
        raise BatchFailure("The first-ten batch must reuse exactly the audited Creep and Wonderwall recordings")
    return songs


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = re.sub(r"\(official artist channel\)|\bofficial\b|\btopic\b", "", value)
    value = re.sub(r"vevo\Z", "", value.strip())
    return "".join(char for char in value if char.isalnum())


def normalized_title(value: str) -> str:
    return normalized_name(re.sub(r"^the\s+", "", value, flags=re.IGNORECASE))


def verify_source(source: dict, song: dict, audio: Path) -> None:
    selected = song["selected_recording"]
    recording, metadata = source.get("recording", {}), source.get("source", {})
    if (source.get("schema_version") != "1.0" or source.get("status") != "prepared" or
            not isinstance(recording, dict) or not isinstance(metadata, dict) or
            recording.get("id") != selected["recording_id"] or recording.get("audio") != "audio.wav"):
        raise BatchFailure("Prepared source manifest has the wrong recording identity")
    if not isinstance(metadata.get("url"), str):
        raise BatchFailure("Prepared source has no selected YouTube URL")
    url, video_id = youtube_import.canonical_url(metadata["url"])
    if metadata.get("video_id") != video_id or video_id != selected["video_id"]:
        raise BatchFailure("Prepared source does not match the selected video")
    if not isinstance(metadata.get("uploader"), str) or not metadata["uploader"].strip():
        raise BatchFailure("Selected recording metadata has no identifiable uploader")
    uploader = normalized_name(metadata["uploader"])
    expected = selected.get("expected_uploader")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        matches = uploader in {normalized_name(item) for item in allowed}
    else:
        artist = normalized_name(song["artist"])
        matches = bool(artist) and artist in uploader
    if not matches:
        raise BatchFailure("Selected recording uploader does not match the reviewed artist or channel")
    if (not isinstance(metadata.get("title"), str) or
            normalized_title(song["title"]) not in normalized_title(metadata["title"])):
        raise BatchFailure("Selected recording title does not match the reviewed song")
    duration = recording.get("duration_seconds")
    if (not finite_number(duration) or not 0 < duration <= 600 or
            recording.get("sample_rate_hz") != 22050 or
            not isinstance(recording.get("audio_sha256"), str) or not HASH.fullmatch(recording["audio_sha256"]) or
            not audio.is_file() or audio.is_symlink() or sha256(audio) != recording["audio_sha256"]):
        raise BatchFailure("Prepared audio format, duration or SHA-256 does not match its source")
    with wave.open(str(audio), "rb") as handle:
        if (handle.getnchannels(), handle.getframerate(), handle.getsampwidth(), handle.getcomptype()) != (1, 22050, 2, "NONE"):
            raise BatchFailure("Prepared audio must be mono 22050 Hz PCM16")
        actual_duration = handle.getnframes() / handle.getframerate()
    if abs(actual_duration - duration) > 0.000001:
        raise BatchFailure("Prepared waveform duration does not match its source")
    cached = song.get("cached_example")
    if cached and (recording["audio_sha256"] != cached["audio_sha256"] or abs(duration - cached["duration_seconds"]) > 0.000001):
        raise BatchFailure("Cached recording hash or duration differs from the reviewed pin")


def verify_chart(chart: dict, recording: dict) -> None:
    paired = chart.get("recording", {})
    if (chart.get("schema_version") != "1.0" or not isinstance(paired, dict) or
            paired.get("id") != recording["id"] or paired.get("audio_sha256") != recording["audio_sha256"] or
            paired.get("sample_rate_hz") != recording["sample_rate_hz"] or
            not finite_number(paired.get("duration_seconds")) or
            abs(paired["duration_seconds"] - recording["duration_seconds"]) > 0.000001 or
            not isinstance(chart.get("chords"), list) or not chart["chords"]):
        raise BatchFailure("A cached detector output does not match the exact recording")
    end = 0.0
    for event in chart["chords"]:
        if (not isinstance(event, dict) or not finite_number(event.get("start_seconds")) or
                not finite_number(event.get("end_seconds")) or not end <= event["start_seconds"] < event["end_seconds"] <= recording["duration_seconds"] or
                not isinstance(event.get("label"), str) or not event["label"]):
            raise BatchFailure("A cached detector output contains malformed timing events")
        end = event["end_seconds"]


def verified_copy(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        raise BatchFailure("Refusing to overwrite an existing batch file")
    shutil.copyfile(source, target)
    if sha256(source) != sha256(target):
        raise BatchFailure("A staged copy did not preserve the original bytes")


def cached_inputs(song: dict, cache_manifest: Path, cache: dict, root: Path) -> tuple[dict, list[Path], dict]:
    identifier = song["selected_recording"]["recording_id"]
    matches = [case for case in cache.get("cases", []) if isinstance(case, dict) and case.get("id") == identifier]
    if len(matches) != 1:
        raise BatchFailure("Expected exactly one matching cached pilot case")
    case = matches[0]
    relative = case.get("audio")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise BatchFailure("Cached audio path must stay inside its pilot pack")
    audio = project_file(cache_manifest.parent / relative, root)
    if not audio.is_relative_to(cache_manifest.parent) or audio.name != "audio.wav":
        raise BatchFailure("Cached audio path must stay inside its pilot pack")
    source_path = project_file(audio.parent / "source.json", root)
    source = load_json(source_path)
    if source != case.get("source"):
        raise BatchFailure("Cached source file and pilot manifest disagree")
    verify_source(source, song, audio)
    charts = {}
    for name in ("crema.json", "chordino.json"):
        path = project_file(audio.parent / name, root)
        verify_chart(load_json(path), source["recording"])
        charts[name] = path
    return source, [audio, source_path, *charts.values()], {
        "cache_manifest_sha256": sha256(cache_manifest),
        "cached_detector_sha256": {name: sha256(path) for name, path in charts.items()}}


def copy_inputs(paths: list[Path], folder: Path, expected_hashes: dict | None = None) -> None:
    folder.mkdir(exist_ok=False)
    for path in paths:
        if expected_hashes is not None and sha256(path) != expected_hashes.get(path.name):
            raise BatchFailure("Prepared reuse source changed after its preflight hash check")
        verified_copy(path, folder / path.name)


def cached_case(song: dict, cache_manifest: Path, cache: dict, staging: Path, root: Path) -> tuple[dict, dict]:
    source, paths, details = cached_inputs(song, cache_manifest, cache, root)
    copy_inputs(paths, staging / song["selected_recording"]["recording_id"])
    return source, details


def prepared_inputs(pack: Path, item: dict, song: dict, cache_manifest: Path, cache: dict,
                    root: Path) -> tuple[dict, list[Path], dict]:
    identifier = song["selected_recording"]["recording_id"]
    folder = pack / "cases" / identifier
    no_symlinks(folder, root)
    if not folder.is_dir():
        raise BatchFailure("A prepared reuse case directory is missing")
    source_path = project_file(folder / "source.json", root)
    source = load_json(source_path)
    audio = project_file(folder / "audio.wav", root)
    verify_source(source, song, audio)
    if (item.get("audio_sha256") != source["recording"]["audio_sha256"] or
            not finite_number(item.get("duration_seconds")) or
            abs(item["duration_seconds"] - source["recording"]["duration_seconds"]) > 0.000001):
        raise BatchFailure("Prepared reuse audio differs from its previous status pins")
    paths, details = [audio, source_path], {}
    if song.get("cached_example"):
        original_source, originals, details = cached_inputs(song, cache_manifest, cache, root)
        if source != original_source or item.get("cached_detector_sha256") != details["cached_detector_sha256"]:
            raise BatchFailure("Prepared cached detector outputs differ from the original status pins")
        for original in originals:
            prepared = project_file(folder / original.name, root)
            if sha256(prepared) != sha256(original):
                raise BatchFailure("Prepared cached files differ from the original audited pilot bytes")
        paths = [project_file(folder / original.name, root) for original in originals]
    else:
        manifest = project_file(folder / "manifest.json", root)
        if load_json(manifest) != source:
            raise BatchFailure("Prepared reuse source and import manifest disagree")
        encoded = source["source"].get("file")
        if not isinstance(encoded, str) or Path(encoded).name != encoded:
            raise BatchFailure("Prepared reuse encoded source filename is unsafe")
        encoded_path = project_file(folder / encoded, root)
        if sha256(encoded_path) != source["source"].get("sha256"):
            raise BatchFailure("Prepared reuse encoded source hash differs from its provenance")
        paths.extend([manifest, encoded_path])
        for name in ("crema.json", "chordino.json"):
            path = folder / name
            if path.exists() or path.is_symlink():
                path = project_file(path, root)
                verify_chart(load_json(path), source["recording"])
                paths.append(path)
    if {path.name for path in paths} != {path.name for path in folder.iterdir()}:
        raise BatchFailure("Prepared reuse case contains unexpected files")
    details["reused_file_sha256"] = {path.name: sha256(path) for path in paths}
    return source, paths, details


def reuse_preflight(pack: Path, songs: list[dict], review_hash: str, cache_manifest: Path,
                    cache: dict, root: Path) -> tuple[dict, dict]:
    no_symlinks(pack, root)
    pack = pack.resolve(strict=True)
    if not pack.is_dir() or not pack.is_relative_to(root / "experiments" / "generated"):
        raise BatchFailure("Prepared reuse pack must be a project-local generated directory")
    status_path = project_file(pack / "batch-status.json", root)
    no_symlinks(pack / "cases", root)
    if not (pack / "cases").is_dir():
        raise BatchFailure("Prepared reuse pack has no regular cases directory")
    previous = load_json(status_path)
    rows = previous.get("cases")
    if (previous.get("schema_version") != "repertoire-batch-status-1.0" or
            previous.get("status") not in {"prepared", "incomplete"} or previous.get("requested") != 10 or
            previous.get("review_sha256") != review_hash or not isinstance(rows, list) or len(rows) != 10):
        raise BatchFailure("Prepared reuse requires a completed status report with the exact same reviewed catalogue hash")
    expected = {song["selected_recording"]["recording_id"]: song for song in songs}
    seen, jobs = set(), {}
    completed = failed = 0
    for item in rows:
        if not isinstance(item, dict) or item.get("recording_id") not in expected or item["recording_id"] in seen:
            raise BatchFailure("Prepared reuse status has unexpected or duplicate recording IDs")
        identifier = item["recording_id"]
        seen.add(identifier)
        song = expected[identifier]
        if item.get("song_id") != song["id"] or item.get("video_id") != song["selected_recording"]["video_id"]:
            raise BatchFailure("Prepared reuse status differs from the selected song or video identity")
        if item.get("status") == "prepared":
            completed += 1
            jobs[identifier] = prepared_inputs(pack, item, song, cache_manifest, cache, root)
        elif item.get("status") == "failed":
            failed += 1
            if (pack / "cases" / identifier).exists() or (pack / "cases" / identifier).is_symlink():
                raise BatchFailure("Failed reuse case unexpectedly has a published recording directory")
        else:
            raise BatchFailure("Prepared reuse status contains an unfinished case")
    if (previous.get("completed") != completed or previous.get("failed") != failed or
            (previous["status"] == "prepared") != (completed == 10 and failed == 0)):
        raise BatchFailure("Prepared reuse completion totals disagree with its cases")
    if {path.name for path in (pack / "cases").iterdir()} != set(jobs):
        raise BatchFailure("Prepared reuse pack contains an unexpected case directory")
    return jobs, {"pack": str(pack.relative_to(root)), "batch_status_sha256": sha256(status_path)}


def safe_failure(error: Exception) -> str:
    if isinstance(error, BatchFailure):
        return str(error)
    if isinstance(error, youtube_import.ImportFailure):
        return "Import failed: " + youtube_import.failure_detail(str(error))
    return "Local import, filesystem or audio validation failed; raw diagnostics were discarded"


def write_json_atomic(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".batch-json-", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(review_path: Path, output: Path, python: Path, node: Path, ffmpeg: Path,
            cache_manifest: Path = DEFAULT_CACHE, root: Path = ROOT, importer=None, progress=None,
            reuse_prepared: Path | None = None) -> dict:
    root = root.resolve()
    review_path = project_file(review_path, root)
    review = load_json(review_path)
    songs = reviewed_songs(review)
    cache_manifest = project_file(cache_manifest, root)
    cache = load_json(cache_manifest)
    if not isinstance(cache.get("cases"), list):
        raise BatchFailure("Cached pilot manifest has no recording cases")
    review_hash = sha256(review_path)
    reused, reuse_details = ({}, None) if reuse_prepared is None else reuse_preflight(
        reuse_prepared, songs, review_hash, cache_manifest, cache, root)
    no_symlinks(output, root)
    output = output.resolve()
    allowed = root / "experiments" / "generated"
    if output == allowed or not output.is_relative_to(allowed):
        raise BatchFailure("Batch output must be a new directory inside experiments/generated")
    if output.is_relative_to(cache_manifest.parent) or (reuse_prepared is not None and output.is_relative_to(reuse_prepared.resolve())):
        raise BatchFailure("Fresh output must not be inside an original cache or prepared reuse pack")
    if output.exists() or output.is_symlink():
        raise BatchFailure("Batch output already exists; choose a fresh directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    (output / "cases").mkdir()
    import_recording = importer or youtube_import.import_recording
    report = {"schema_version": "repertoire-batch-status-1.0", "version": VERSION,
              "status": "preparing", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "review_sha256": review_hash, "requested": 10, "completed": 0,
              "failed": 0, "cases": [], "gold": False}
    if reuse_details:
        report["reuse_prepared"] = reuse_details
    status_path = output / "batch-status.json"
    write_json_atomic(status_path, report)
    cases, inference = [], []
    with tempfile.TemporaryDirectory(prefix=".batch-staging-", dir=output) as staging_name:
        staging = Path(staging_name)
        for song in songs:
            selected = song["selected_recording"]
            identifier = selected["recording_id"]
            item = {"song_id": song["id"], "recording_id": identifier, "video_id": selected["video_id"],
                    "workflow": "reuse-prepared" if identifier in reused else
                    "reuse-cache" if song.get("cached_example") else "import-selected-url"}
            try:
                if identifier in reused:
                    source, paths, reuse = reused[identifier]
                    copy_inputs(paths, staging / identifier, reuse["reused_file_sha256"])
                    item.update(reuse)
                    item["reused_batch_status_sha256"] = reuse_details["batch_status_sha256"]
                elif song.get("cached_example"):
                    source, reuse = cached_case(song, cache_manifest, cache, staging, root)
                    item.update(reuse)
                else:
                    import_recording(selected["url"], identifier, SOURCE_USE, staging, python, node, ffmpeg)
                    folder = staging / identifier
                    no_symlinks(folder, root)
                    source_path = project_file(folder / "manifest.json", root)
                    source = load_json(source_path)
                    audio = project_file(folder / "audio.wav", root)
                    verify_source(source, song, audio)
                    encoded = source.get("source", {}).get("file")
                    if not isinstance(encoded, str) or Path(encoded).name != encoded:
                        raise BatchFailure("Prepared encoded source file has an unsafe filename")
                    encoded_path = project_file(folder / encoded, root)
                    if sha256(encoded_path) != source["source"].get("sha256"):
                        raise BatchFailure("Prepared encoded source hash does not match its provenance")
                    verified_copy(source_path, folder / "source.json")
                folder = staging / identifier
                # All importer sidecars are rejected rather than silently published.
                allowed_names = {"audio.wav", "source.json", "crema.json", "chordino.json", "manifest.json", source["source"].get("file")}
                if any(path.is_symlink() or not path.is_file() or path.name not in allowed_names for path in folder.iterdir()):
                    raise BatchFailure("Staged recording contains unexpected files")
                target = output / "cases" / identifier
                if target.exists() or target.is_symlink():
                    raise BatchFailure("Refusing to replace an existing batch case")
                folder.rename(target)
                case = {"id": identifier, "name": f"{song['artist']} - {song['title']}",
                        "audio": f"cases/{identifier}/audio.wav", "source": source}
                cases.append(case)
                if not song.get("cached_example"):
                    inference.append(case)
                item.update({"status": "prepared", "audio_sha256": source["recording"]["audio_sha256"],
                             "duration_seconds": source["recording"]["duration_seconds"]})
                report["completed"] += 1
            except Exception as error:
                item.update({"status": "failed", "error": safe_failure(error)})
                report["failed"] += 1
            report["cases"].append(item)
            write_json_atomic(status_path, report)
            if progress:
                progress({"recording_id": identifier, "status": item["status"],
                          "completed": report["completed"], "failed": report["failed"]})
    report["status"] = "prepared" if report["completed"] == 10 and not report["failed"] else "incomplete"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    if report["status"] == "prepared":
        manifest = {"pilot_version": "1.0", "repertoire_batch_version": VERSION,
                    "review_sha256": report["review_sha256"], "status": "prepared", "cases": cases,
                    "limitations": "Ten selected recordings; cached outputs reused without modification. No verified timing gold or accuracy claim."}
        inference_manifest = {"pilot_version": "1.0", "status": "audio-only-inference-ready", "cases": inference,
                              "semantics": "Eight new recording inputs only. Teaching chords, keys, structures and timings are excluded."}
        write_json_atomic(output / "audio-only-inference-manifest.json", inference_manifest)
        write_json_atomic(output / "manifest.json", manifest)
        report["manifest_sha256"] = sha256(output / "manifest.json")
        report["inference_manifest_sha256"] = sha256(output / "audio-only-inference-manifest.json")
    write_json_atomic(status_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("prepare", help="Prepare exactly ten reviewed recordings in a fresh local pack")
    command.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    command.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    command.add_argument("--cache-manifest", type=Path, default=DEFAULT_CACHE)
    command.add_argument("--reuse-prepared", type=Path, help="Verify and copy successes from a prior batch with the identical review hash")
    command.add_argument("--python", type=Path, default=ROOT / ".venv-youtube" / "bin" / "python")
    command.add_argument("--node", type=Path, default=Path(shutil.which("node") or "/missing-node"))
    command.add_argument("--ffmpeg", type=Path, default=Path(shutil.which("ffmpeg") or "/missing-ffmpeg"))
    args = parser.parse_args()
    try:
        result = prepare(args.review, args.output, args.python, args.node, args.ffmpeg, args.cache_manifest,
                         progress=lambda item: print(json.dumps(item, allow_nan=False), flush=True),
                         reuse_prepared=args.reuse_prepared)
        print(json.dumps({"status": result["status"], "completed": result["completed"],
                          "failed": result["failed"], "output": str(args.output.resolve())}, allow_nan=False))
        if result["status"] != "prepared":
            raise SystemExit(1)
    except (BatchFailure, youtube_import.ImportFailure, OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": safe_failure(error)}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
