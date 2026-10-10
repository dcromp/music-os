"""Bounded, local-only import of one explicitly selected public YouTube video.

This is experiment tooling, not a catalogue crawler. It neither establishes
commercial permission nor supplies credentials, proxies or remote components.
Raw extractor metadata and signed media URLs are never persisted or printed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlsplit
import wave

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "experiments" / "local-audio" / "youtube"
ALLOWED_OUTPUTS = (ROOT / "experiments" / "local-audio", ROOT / "experiments" / "generated")
VERSION = "0.1.0"
FORMAT = "bestaudio[ext=m4a]/bestaudio"
MAX_SECONDS = 600
MAX_BYTES = 32 * 1024 * 1024
METADATA_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 180
LOG_LIMIT = 16 * 1024 * 1024
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}\Z")


class ImportFailure(ValueError):
    """An intentionally safe message without upstream URLs or credentials."""


def canonical_url(value: str) -> tuple[str, str]:
    """Reject collections and ambiguous URLs; discard timestamps/tracking."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ImportFailure("Invalid YouTube URL") from error
    if parsed.scheme != "https" or parsed.username or parsed.password or port is not None:
        raise ImportFailure("Use an HTTPS YouTube URL without credentials or a port")
    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query, keep_blank_values=True)
    if any(key in query for key in ("list", "index", "playlist", "search_query")):
        raise ImportFailure("Playlists, collections and search URLs are not supported")
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.removeprefix("/")
        if "v" in query:
            raise ImportFailure("Ambiguous video ID")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch" and len(query.get("v", [])) == 1:
            video_id = query["v"][0]
        elif re.fullmatch(r"/(?:shorts|embed)/[A-Za-z0-9_-]{11}", parsed.path) and "v" not in query:
            video_id = parsed.path.rsplit("/", 1)[1]
        else:
            raise ImportFailure("Select one watch, shorts, embed or youtu.be video URL")
    else:
        raise ImportFailure("Only explicit youtube.com and youtu.be video URLs are supported")
    if not ID_PATTERN.fullmatch(video_id):
        raise ImportFailure("YouTube video ID must contain exactly 11 valid characters")
    return f"https://www.youtube.com/watch?v={video_id}", video_id


def safe_text(value: object, limit: int = 500) -> str | None:
    if not isinstance(value, str):
        return None
    value = re.sub(r"https?://\S+", "[link omitted]", value)
    return "".join(char for char in value if char.isprintable()).strip()[:limit] or None


def minimal_metadata(info: dict, video_id: str) -> dict:
    if not isinstance(info, dict) or info.get("id") != video_id:
        raise ImportFailure("Extractor returned a different recording ID")
    if info.get("_type", "video") not in {"video", None} or "entries" in info:
        raise ImportFailure("Extractor returned a collection instead of one recording")
    duration = info.get("duration")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
        raise ImportFailure(f"Recording must have a known duration of at most {MAX_SECONDS} seconds")
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
        raise ImportFailure("Live, upcoming and not-yet-finished live recordings are unsupported")
    if info.get("availability") not in {None, "public"}:
        raise ImportFailure("Only public recordings without access restrictions are supported")
    if info.get("age_limit", 0) not in {None, 0}:
        raise ImportFailure("Age-restricted recordings are unsupported")
    if info.get("vcodec") != "none":
        raise ImportFailure("No audio-only format was selected")
    format_id, extension = info.get("format_id"), info.get("ext")
    if not isinstance(format_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", format_id):
        raise ImportFailure("Unexpected audio format identifier")
    if not isinstance(extension, str) or not re.fullmatch(r"[a-z0-9]{1,10}", extension):
        raise ImportFailure("Unexpected audio file extension")
    for field in ("filesize", "filesize_approx"):
        size = info.get(field)
        if isinstance(size, (int, float)) and not isinstance(size, bool) and size > MAX_BYTES:
            raise ImportFailure("Selected audio exceeds the 32 MiB download limit")
    result = {
        "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": safe_text(info.get("title")) or video_id,
        "uploader": safe_text(info.get("uploader")),
        "duration_seconds": float(duration), "availability": info.get("availability"),
        "live_status": safe_text(info.get("live_status"), 30),
        "format_id": format_id, "extension": extension,
        "audio_codec": safe_text(info.get("acodec"), 40),
    }
    date = info.get("upload_date")
    if isinstance(date, str) and re.fullmatch(r"[0-9]{8}", date):
        result["upload_date"] = date
    return result


def common_command(python: Path, node: Path) -> list[str]:
    for path, name in ((python, "isolated Python"), (node, "Node runtime")):
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ImportFailure(f"Missing executable {name}; follow the local setup instructions")
    return [str(python), "-m", "yt_dlp", "--ignore-config", "--no-plugin-dirs",
            "--no-remote-components", "--no-js-runtimes", "--js-runtimes", f"node:{node}",
            "--no-playlist", "--no-cache-dir", "--no-cookies", "--no-cookies-from-browser",
            "--no-geo-bypass", "--proxy", "", "--socket-timeout", "15", "--retries", "1",
            "--fragment-retries", "1", "--extractor-retries", "1", "--no-progress"]


def failure_detail(stderr: str) -> str:
    """Report recognisable failure categories without reproducing raw logs."""
    lower = stderr.lower()
    if "429" in lower or "too many requests" in lower:
        return "upstream rate limit (HTTP 429)"
    if "403" in lower or "forbidden" in lower:
        return "upstream access refusal (HTTP 403)"
    if "sign in" in lower or "login" in lower or "private video" in lower:
        return "upstream requires authentication or restricted access"
    if "not available" in lower or "unavailable" in lower:
        return "recording or selected format is unavailable"
    if "timed out" in lower or "timeout" in lower:
        return "network timeout"
    if "name resolution" in lower or "network is unreachable" in lower:
        return "network connectivity failure"
    return "subprocess failure; raw upstream diagnostics were discarded"


def run_bounded(command: list[str], timeout: int, step: str, directory: Path | None = None,
                disk_limit: int = MAX_BYTES) -> tuple[str, int]:
    """Bound runtime, output logs and total bytes while discarding sensitive logs."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        deadline = time.monotonic() + timeout
        violation = None
        try:
            while process.poll() is None:
                if time.monotonic() > deadline:
                    violation = f"{step} exceeded its {timeout}-second time limit"
                elif os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > LOG_LIMIT:
                    violation = f"{step} exceeded its diagnostic-output limit"
                elif directory and sum(path.stat().st_size for path in directory.rglob("*") if path.is_file()) > disk_limit:
                    violation = f"{step} exceeded its local file-size limit"
                if violation:
                    raise ImportFailure(violation)
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > LOG_LIMIT:
            raise ImportFailure(f"{step} exceeded its diagnostic-output limit")
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read(LOG_LIMIT).decode("utf-8", errors="replace")
        diagnostic = stderr.read(LOG_LIMIT).decode("utf-8", errors="replace")
        if process.returncode:
            raise ImportFailure(f"{step} failed: {failure_detail(diagnostic)} (exit {process.returncode})")
        if directory and sum(path.stat().st_size for path in directory.rglob("*") if path.is_file()) > disk_limit:
            raise ImportFailure(f"{step} exceeded its local file-size limit")
        return output, sum(line.startswith("WARNING:") for line in diagnostic.splitlines())


def inspect(url: str, python: Path, node: Path) -> tuple[dict, str]:
    url, video_id = canonical_url(url)
    command = common_command(python, node)
    version, _ = run_bounded([str(python), "-m", "yt_dlp", "--ignore-config", "--version"], 10, "Version check")
    version = version.strip()
    if not re.fullmatch(r"[A-Za-z0-9._+-]{1,80}", version):
        raise ImportFailure("Unexpected yt-dlp version response")
    output, warnings = run_bounded(command + ["--skip-download", "--dump-single-json", "--no-check-formats",
                                              "--format", FORMAT, url], METADATA_TIMEOUT, "Metadata inspection")
    try:
        info = json.loads(output)
    except json.JSONDecodeError as error:
        raise ImportFailure("Metadata inspection returned invalid JSON") from error
    result = minimal_metadata(info, video_id)
    result["extractor_warning_count"] = warnings
    return result, version


def validate_output(output_root: Path, recording_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", recording_id):
        raise ImportFailure("Recording ID must be 1–64 letters, digits, underscores or hyphens")
    root = output_root.resolve()
    if not any(root.is_relative_to(allowed.resolve()) for allowed in ALLOWED_OUTPUTS):
        raise ImportFailure("Output must stay in experiments/local-audio or experiments/generated")
    target = root / recording_id
    if target.exists() or target.is_symlink():
        raise ImportFailure("Recording output already exists; choose a new ID (nothing is overwritten)")
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_recording(url: str, recording_id: str, source_use: str, output_root: Path,
                     python: Path, node: Path, ffmpeg: Path) -> dict:
    target = validate_output(output_root, recording_id)
    if not isinstance(source_use, str) or not source_use.strip() or len(source_use) > 2000:
        raise ImportFailure("Record a nonempty source-use/provenance note of at most 2000 characters")
    if not ffmpeg.is_file() or not os.access(ffmpeg, os.X_OK):
        raise ImportFailure("FFmpeg must be available for audio preparation")
    metadata, downloader_version = inspect(url, python, node)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".youtube-import-", dir=target.parent) as staging_name:
        staging = Path(staging_name)
        source = staging / f"source.{metadata['extension']}"
        download = common_command(python, node) + [
            "--no-overwrites", "--no-continue", "--format", metadata["format_id"],
            "--max-filesize", str(MAX_BYTES), "--concurrent-fragments", "1", "--limit-rate", "1M",
            "--match-filters", f"!is_live & duration <= {MAX_SECONDS} & age_limit <= 0",
            "--output", str(staging / "source.%(ext)s"), metadata["url"],
        ]
        _, warnings = run_bounded(download, DOWNLOAD_TIMEOUT, "Audio download", staging)
        if not source.is_file() or source.is_symlink() or source.stat().st_size == 0:
            raise ImportFailure("Audio download produced no complete selected-format file")
        prepared = staging / "audio.wav"
        run_bounded([str(ffmpeg), "-nostdin", "-v", "error", "-n", "-i", str(source),
                     "-vn", "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(prepared)],
                    45, "Audio preparation", staging, MAX_BYTES + MAX_SECONDS * 22050 * 2 + 4096)
        with wave.open(str(prepared), "rb") as audio:
            if (audio.getnchannels(), audio.getframerate(), audio.getsampwidth(), audio.getcomptype()) != (1, 22050, 2, "NONE"):
                raise ImportFailure("Prepared audio does not have the required mono 22050 Hz PCM16 format")
            duration = audio.getnframes() / audio.getframerate()
        if not 0 < duration <= MAX_SECONDS or abs(duration - metadata["duration_seconds"]) > max(3, metadata["duration_seconds"] * 0.01):
            raise ImportFailure("Prepared audio duration disagrees with the selected complete recording")
        manifest = {
            "schema_version": "1.0", "status": "prepared", "importer_version": VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "recording": {"id": recording_id, "title": metadata["title"], "duration_seconds": duration,
                          "sample_rate_hz": 22050, "audio": "audio.wav", "audio_sha256": sha256(prepared),
                          "provenance": source_use.strip()},
            "source": {**metadata, "file": source.name, "sha256": sha256(source), "bytes": source.stat().st_size},
            "import": {"yt_dlp_version": downloader_version, "download_warning_count": warnings,
                       "duration_limit_seconds": MAX_SECONDS, "download_byte_limit": MAX_BYTES,
                       "metadata_timeout_seconds": METADATA_TIMEOUT, "download_timeout_seconds": DOWNLOAD_TIMEOUT,
                       "credentials": "none", "proxy": "none", "remote_components": "disabled",
                       "scope": "one explicit public video; no playlists or search"},
            "preparation": {"channels": 1, "sample_rate_hz": 22050, "codec": "pcm_s16le",
                            "analysis_and_playback": "Use this exact audio.wav; do not substitute embedded playback"},
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        # Exclusive directory creation protects a concurrent import or any source
        # folder that appeared after the initial check. Never rename over it.
        target.mkdir(exist_ok=False)
        # Publish the completed manifest last; unexpected downloader sidecars or
        # partial files are not retained.
        for path in (source, prepared, staging / "manifest.json"):
            shutil.move(str(path), target / path.name)
    return {"status": "prepared", "recording_id": recording_id, "video_id": metadata["video_id"],
            "duration_seconds": duration, "audio": str(target / "audio.wav"),
            "manifest": str(target / "manifest.json"), "audio_sha256": manifest["recording"]["audio_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=ROOT / ".venv-youtube" / "bin" / "python")
    parser.add_argument("--node", type=Path, default=Path(shutil.which("node") or "/missing-node"))
    sub = parser.add_subparsers(dest="command", required=True)
    metadata = sub.add_parser("metadata", help="Inspect one video without downloading audio; print minimal metadata")
    metadata.add_argument("url")
    acquire = sub.add_parser("import", help="Download and prepare one selected recording, with local provenance")
    acquire.add_argument("url")
    acquire.add_argument("--recording-id", required=True)
    acquire.add_argument("--source-use", required=True)
    acquire.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    acquire.add_argument("--ffmpeg", type=Path, default=Path(shutil.which("ffmpeg") or "/missing-ffmpeg"))
    args = parser.parse_args()
    try:
        if args.command == "metadata":
            result, version = inspect(args.url, args.python, args.node)
            result = {"status": "metadata-only", "yt_dlp_version": version, **result}
        else:
            result = import_recording(args.url, args.recording_id, args.source_use, args.output_root,
                                      args.python, args.node, args.ffmpeg)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ImportFailure, OSError, wave.Error) as error:
        # OSError filenames can contain temporary signed metadata only in logs;
        # never copy a raw external diagnostic into the terminal.
        message = str(error) if isinstance(error, ImportFailure) else "Local filesystem or audio preparation failed"
        print(json.dumps({"status": "failed", "error": message}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
