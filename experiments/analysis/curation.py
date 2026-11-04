"""Prepare a source-paired review workspace; save corrections separately.

Worklists are investigation hints, not truth. Review exports remain model-exposed
drafts. No saved correction or checked replay automatically becomes a lesson.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import unquote, urlsplit

import automatic_drafts as drafts
import review_pack
import practice_grips

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "experiments/curation"
DEFAULT_SOURCE = ROOT / "experiments/generated/automatic-first-ten-selected-v1"
DEFAULT_CONTEXT = ROOT / "docs/FIRST_TEN_ARRANGEMENT_CHECK.json"
DEFAULT_OUTPUT = ROOT / "experiments/generated/catalogue-curation-20261014"
DEFAULT_UPDATES = ROOT / "catalogue/curation-source-updates.json"
SCHEMA = "catalogue-curation-1.0"
DRAFT_SCHEMA = "catalogue-curation-draft-1.0"
VERSION = "0.1.0"
MAX_BODY = 262144
SAVE_LOCK = threading.Lock()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def text(value, limit, empty=False):
    return isinstance(value, str) and len(value) <= limit and (empty or bool(value.strip()))


def identity(first, second):
    return isinstance(first, dict) and isinstance(second, dict) and all(
        first.get(key) == second.get(key) for key in ("id", "audio_sha256", "duration_seconds", "sample_rate_hz"))


def merged_duration(spans):
    end = total = 0.0
    for first, last in sorted(spans):
        if last > end:
            total += last - max(first, end)
            end = last
    return total


def worklist(primary, secondary, context):
    evidence = drafts.compare_charts(primary, secondary)
    duration = primary["recording"]["duration_seconds"]
    points = [{**point, "kind": "model-disagreement", "checked": False} for point in evidence["review_points"]]
    # Fixed positions also inspect agreement: a shared model error raises no flag.
    for index, fraction in enumerate((0.10, 0.35, 0.60, 0.85), 1):
        center = duration * fraction
        points.append({"id": f"sample-{index}", "start_seconds": max(0.0, center - 3),
                       "end_seconds": min(duration, center + 3), "kind": "coverage-sample",
                       "reason": "Fixed sample, including possible shared model errors", "checked": False})
    events = primary["chords"]
    short = [event for event in events if event["label"] not in {"N", "X"}
             and event["end_seconds"] - event["start_seconds"] < 0.5]
    return {"schema_version": SCHEMA, "recording": primary["recording"], "status": "unreviewed-worklist",
            "gold": False, "semantics": "Disagreements, short events and source proposals are review hints, not errors or verified timings.",
            "statistics": {"primary_intervals": len(events), "secondary_intervals": len(secondary["chords"]),
                           "flags": len(evidence["flags"]), "short_primary_events": len(short),
                           "flagged_seconds": merged_duration([(item["start_seconds"], item["end_seconds"]) for item in evidence["flags"]]),
                           "no_chord_seconds": sum(event["end_seconds"] - event["start_seconds"] for event in events if event["label"] == "N"),
                           "unknown_seconds": sum(event["end_seconds"] - event["start_seconds"] for event in events if event["label"] == "X")},
            "points": points, "short_events": short, "source_context": context,
            "practice_palette": practice_grips.source_palette(context),
            "correction_effort": {"human_seconds": None, "agent_seconds": None,
                                  "status": "unmeasured; automated preparation is not review/correction time"}}


def build(source, context_path, output, root=ROOT, updates=None):
    root = root.resolve()
    source = source.resolve(strict=True)
    context_path = drafts.project_input(context_path, root)
    output = output.absolute()
    if not source.is_relative_to(root) or not output.resolve().is_relative_to(root):
        raise ValueError("Curation inputs and output must stay inside the project")
    if output.exists() or output.is_symlink():
        raise ValueError("Choose an unused curation directory")
    native_manifest = read(source / "manifest.json")
    if native_manifest.get("model_selection") != {"primary": "btc", "secondary": "crema"} or native_manifest.get("gold") is not False:
        raise ValueError("Expected the selected unreviewed BTC/CREMA pack")
    drafts.public_files(source)
    context = read(context_path)
    if context.get("schema_version") != "first-ten-arrangement-check-1.0":
        raise ValueError("Expected first-ten source context")
    contexts = {item["recording"]["id"]: item for item in context["cases"]}
    if len(contexts) != len(context["cases"]):
        raise ValueError("Duplicate source context")
    source_by_id = {item["id"]: item for item in context["sources"]}
    updates_hash = None
    if updates is not None:
        updates = drafts.project_input(updates, root)
        update = read(updates)
        if update.get("schema_version") != "curation-source-updates-1.0" or update.get("context_sha256") != drafts.digest(context_path):
            raise ValueError("Source updates must identify their exact historical context")
        seen_updates = set()
        for item in update["cases"]:
            identifier = item["recording"]["id"]
            if identifier in seen_updates or identifier not in contexts or not identity(item["recording"], contexts[identifier]["recording"]):
                raise ValueError("Source update belongs to another exact recording")
            if (not isinstance(item.get("correction_needs"), list) or not item["correction_needs"]
                    or any(not text(value, 1000) for value in item["correction_needs"])
                    or not text(item.get("review_role"), 200) or not text(item.get("note"), 2000)):
                raise ValueError("Invalid source correction notes")
            seen_updates.add(identifier)
            contexts[identifier] = {**contexts[identifier], "correction_needs": item["correction_needs"],
                                    "review_role": item["review_role"],
                                    "context_update": {"checked_date": update["checked_date"], "note": item["note"], "sources": update["sources"]}}
        updates_hash = drafts.digest(updates)
    # Complete pairing preflight before making any output.
    jobs = []
    for case in native_manifest["cases"]:
        identifier = case["id"]
        source_case = source / "cases" / identifier
        primary = read(source_case / "primary.json")
        secondary = read(source_case / "crema.json")
        drafts.paired_recording(primary, secondary)
        if not identity(case["recording"], primary["recording"]) or identifier not in contexts or not identity(contexts[identifier]["recording"], case["recording"]):
            raise ValueError("Source context and exact selected recording must match")
        for filename, field in (("primary.json", "primary_sha256"), ("crema.json", "crema_sha256")):
            if drafts.digest(source_case / filename) != case["artifacts"][field]:
                raise ValueError("Selected native chart hash changed")
        drafts.verified_audio(source_case / "audio.wav", case["recording"])
        ctx = dict(contexts[identifier])
        ctx["sources"] = [source_by_id[item] for item in ctx["source_ids"]]
        jobs.append((case, primary, secondary, ctx))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".curation-", dir=output.parent))
    result = {"schema_version": SCHEMA, "version": VERSION, "pack_id": output.name,
              "status": "review workspace; no accepted lessons", "gold": False,
              "source_manifest_sha256": drafts.digest(source / "manifest.json"),
              "context_sha256": drafts.digest(context_path), "source_updates_sha256": updates_hash, "cases": []}
    try:
        for case, primary, secondary, ctx in jobs:
            identifier = case["id"]
            folder = staging / "cases" / identifier
            folder.mkdir(parents=True)
            for filename in ("audio.wav", "primary.json", "crema.json"):
                original = source / "cases" / identifier / filename
                shutil.copyfile(original, folder / filename)
                if drafts.digest(original) != drafts.digest(folder / filename):
                    raise ValueError("Curation copy changed native bytes")
            review = worklist(primary, secondary, ctx)
            drafts.write_json(folder / "review.json", review)
            result["cases"].append({"id": identifier, "name": case["name"], "recording": case["recording"],
                                    "artifacts": case["artifacts"], "statistics": review["statistics"],
                                    "audio_url": f"/cases/{identifier}/audio.wav", "primary_url": f"/cases/{identifier}/primary.json",
                                    "secondary_url": f"/cases/{identifier}/crema.json", "review_url": f"/cases/{identifier}/review.json",
                                    "draft_url": f"/api/drafts/{identifier}"})
        drafts.write_json(staging / "manifest.json", result)
        drafts.write_json(staging / "build-spec.json", {"source": str(source.relative_to(root)), "context": str(context_path.relative_to(root))})
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging)
        raise
    return result


def blank_draft(manifest, case):
    return {"schema_version": DRAFT_SCHEMA, "status": "model-exposed-curation-draft", "gold": False,
            "pack_id": manifest["pack_id"], "recording": case["recording"], "base_artifacts": case["artifacts"],
            "revision": 0, "chord_edits": [], "sections": [], "checked_points": [], "sessions": [],
            "setup_notes": "", "rhythm_notes": "", "review_notes": ""}


def validate_draft(value, manifest, case, review):
    if not isinstance(value, dict) or value.get("schema_version") != DRAFT_SCHEMA or value.get("status") != "model-exposed-curation-draft" or value.get("gold") is not False:
        raise ValueError("Corrections remain a model-exposed draft")
    if value.get("pack_id") != manifest["pack_id"] or not identity(value.get("recording", {}), case["recording"]) or value.get("base_artifacts") != case["artifacts"]:
        raise ValueError("Draft belongs to a different recording, source chart or pack")
    if isinstance(value.get("revision"), bool) or not isinstance(value.get("revision"), int) or value["revision"] < 0:
        raise ValueError("Invalid draft revision")
    duration = case["recording"]["duration_seconds"]
    for key, label_key, maximum in (("chord_edits", "label", 500), ("sections", "name", 100)):
        intervals = value.get(key)
        if not isinstance(intervals, list) or len(intervals) > maximum:
            raise ValueError("Too many draft intervals")
        previous = 0.0
        for item in intervals:
            if (not isinstance(item, dict) or not number(item.get("start_seconds")) or not number(item.get("end_seconds"))
                    or not previous <= item["start_seconds"] < item["end_seconds"] <= duration
                    or not text(item.get(label_key), 100) or not text(item.get("note", ""), 1000, True)):
                raise ValueError("Draft intervals must be bounded, ordered and non-overlapping")
            previous = item["end_seconds"]
        if key == "chord_edits":
            import re
            if any(not re.fullmatch(r"(?:N|X|[A-G][#b]?[A-Za-z0-9#b():,./+*\-]*)", item["label"]) for item in intervals):
                raise ValueError("Use a sounding chord label, N or X")
    points = value.get("checked_points")
    allowed = {item["id"] for item in review["points"]}
    if not isinstance(points, list) or any(not isinstance(item, str) or item not in allowed for item in points) or len(points) != len(set(points)):
        raise ValueError("Checked points must identify existing review windows")
    sessions = value.get("sessions")
    if not isinstance(sessions, list) or len(sessions) > 1000:
        raise ValueError("Invalid review sessions")
    session_ids = set()
    for item in sessions:
        if (not isinstance(item, dict) or not review_pack.safe_id(item.get("id", "")) or item["id"] in session_ids
                or item.get("actor") not in {"human", "agent", "qa"} or not number(item.get("active_seconds"))
                or not 0 <= item["active_seconds"] <= 1800 or not text(item.get("task"), 100)):
            raise ValueError("Review sessions need an explicit actor and bounded active time")
        for field in ("started_at", "ended_at"):
            try:
                parsed = datetime.fromisoformat(item[field].replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError()
            except (KeyError, TypeError, AttributeError, ValueError) as error:
                raise ValueError("Review sessions need UTC-aware dates") from error
        first = datetime.fromisoformat(item["started_at"].replace("Z", "+00:00"))
        last = datetime.fromisoformat(item["ended_at"].replace("Z", "+00:00"))
        if last < first or item["active_seconds"] > (last - first).total_seconds() + 1:
            raise ValueError("Review session ends before its start")
        session_ids.add(item["id"])
    for key in ("setup_notes", "rhythm_notes", "review_notes"):
        if not text(value.get(key), 5000, True):
            raise ValueError("Draft notes must be bounded text")
    # Prevent extra fields such as accepted:true from acquiring apparent authority.
    if set(value) != set(blank_draft(manifest, case)):
        raise ValueError("Unexpected draft fields")
    json.dumps(value, allow_nan=False)
    return value


def effort(draft):
    return {actor + "_seconds": (sum(item["active_seconds"] for item in draft["sessions"] if item["actor"] == actor)
                                 if any(item["actor"] == actor for item in draft["sessions"]) else None)
            for actor in ("human", "agent", "qa")}


def public_files(pack):
    pack = pack.resolve(strict=True)
    manifest = read(pack / "manifest.json")
    if manifest.get("schema_version") != SCHEMA or manifest.get("gold") is not False or not isinstance(manifest.get("cases"), list) or not 1 <= len(manifest["cases"]) <= 64:
        raise ValueError("Invalid curation workspace")
    files = {"/": STATIC / "index.html", "/index.html": STATIC / "index.html", "/app.js": STATIC / "app.js", "/style.css": STATIC / "style.css", "/manifest.json": pack / "manifest.json"}
    seen = set()
    for case in manifest["cases"]:
        identifier = case["id"]
        if not review_pack.safe_id(identifier) or identifier in seen:
            raise ValueError("Invalid curation case identity")
        seen.add(identifier)
        for field, filename in (("audio_url", "audio.wav"), ("primary_url", "primary.json"), ("secondary_url", "crema.json"), ("review_url", "review.json")):
            url = f"/cases/{identifier}/{filename}"
            if case.get(field) != url:
                raise ValueError("Unexpected curation asset route")
            files[url] = pack / "cases" / identifier / filename
        if case.get("draft_url") != f"/api/drafts/{identifier}":
            raise ValueError("Unexpected draft API route")
    for path in files.values():
        root = STATIC.resolve() if path.is_relative_to(STATIC) else pack
        if not review_pack.safe_public_file(path, root, pack):
            raise ValueError("Curation public asset leaves its fixed root or aliases private data")
    for case in manifest["cases"]:
        folder = pack / "cases" / case["id"]
        primary, secondary, review = (read(folder / name) for name in ("primary.json", "crema.json", "review.json"))
        drafts.paired_recording(primary, secondary)
        if not all(identity(value.get("recording"), case["recording"]) for value in (primary, secondary, review)):
            raise ValueError("Curation assets belong to different recordings")
        for filename, field in (("primary.json", "primary_sha256"), ("crema.json", "crema_sha256")):
            if drafts.digest(folder / filename) != case["artifacts"][field]:
                raise ValueError("Curation native chart hash changed")
        drafts.verified_audio(folder / "audio.wav", case["recording"])
    return files, manifest


class CurationHandler(review_pack.ReviewHandler):
    def __init__(self, *args, files, manifest, pack, **kwargs):
        self.manifest = manifest
        self.cases = {case["id"]: case for case in manifest["cases"]}
        self.pack = pack.resolve()
        super().__init__(*args, files=files, **kwargs)

    @property
    def pack_root(self):
        return self.pack

    def own_request(self, writing=False):
        host = self.headers.get("Host", "")
        if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            return False
        origin = self.headers.get("Origin")
        return (origin is None and not writing) or origin == "http://" + host

    def translate_path(self, path):
        url = urlsplit(path)
        decoded = unquote(url.path)
        candidate = self.public_files.get(decoded)
        if not candidate or url.query or ".." in decoded.split("/") or "\\" in decoded:
            return str(STATIC / "__not_found__")
        root = STATIC.resolve() if candidate.is_relative_to(STATIC) else self.pack
        if not review_pack.safe_public_file(candidate, root, self.pack):
            return str(STATIC / "__not_found__")
        # A later hardlink to a private draft must not become public.
        for private in (self.pack / "private-drafts").glob("*.json"):
            if private.is_file() and candidate.samefile(private):
                return str(STATIC / "__not_found__")
        return str(candidate)

    def api_case(self):
        url = urlsplit(self.path)
        if url.query or unquote(url.path) != url.path:
            return None
        prefix = "/api/drafts/"
        return self.cases.get(url.path[len(prefix):]) if url.path.startswith(prefix) else None

    def respond(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def saved(self, case):
        directory = self.pack / "private-drafts"
        path = directory / (case["id"] + ".json")
        if directory.is_symlink() or path.is_symlink():
            raise ValueError("Private drafts must not be symlinks")
        value = read(path) if path.exists() else blank_draft(self.manifest, case)
        review = read(self.pack / "cases" / case["id"] / "review.json")
        return validate_draft(value, self.manifest, case, review)

    def do_GET(self):
        if not self.own_request():
            return self.respond(403, {"error": "Local same-origin requests only"})
        case = self.api_case()
        if case:
            try:
                value = self.saved(case)
                return self.respond(200, {"draft": value, "effort": effort(value)})
            except (ValueError, KeyError, OSError, json.JSONDecodeError):
                return self.respond(400, {"error": "Saved draft is invalid; existing bytes retained"})
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if not self.own_request(writing=True):
            return self.respond(403, {"error": "Local same-origin requests only"})
        case = self.api_case()
        if not case or self.headers.get("Content-Type") != "application/json":
            return self.respond(400, {"error": "Expected the fixed draft route and JSON"})
        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 < length <= MAX_BODY:
                raise ValueError("Invalid body size")
            def reject(value):
                raise ValueError("Nonfinite JSON")
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        raise ValueError("Duplicate JSON fields")
                    result[key] = value
                return result
            value = json.loads(self.rfile.read(length), parse_constant=reject, object_pairs_hook=pairs)
            review = read(self.pack / "cases" / case["id"] / "review.json")
            validate_draft(value, self.manifest, case, review)
            with SAVE_LOCK:
                previous = self.saved(case)
                if value["revision"] != previous["revision"]:
                    return self.respond(409, {"error": "Draft changed in another tab; reload before saving"})
                value["revision"] += 1
                directory = self.pack / "private-drafts"
                directory.mkdir(exist_ok=True)
                path = directory / (case["id"] + ".json")
                # Atomic separate revision; no raw audio/chart paths are writable.
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(mode="w", dir=directory, encoding="utf-8", delete=False) as stream:
                        temporary = Path(stream.name)
                        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    if temporary and temporary.exists():
                        temporary.unlink()
            return self.respond(200, {"draft": value, "effort": effort(value)})
        except (ValueError, KeyError, OSError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return self.respond(400, {"error": "Invalid draft; source charts and saved revision retained"})


def serve(pack, port):
    files, manifest = public_files(pack)
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(CurationHandler, files=files, manifest=manifest, pack=pack))
    print(f"Catalogue reviewer: http://127.0.0.1:{port}/ — separate drafts; normal player unchanged", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build")
    builder.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    builder.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    builder.add_argument("--updates", type=Path, default=DEFAULT_UPDATES)
    builder.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    server = sub.add_parser("serve")
    server.add_argument("--pack", type=Path, default=DEFAULT_OUTPUT)
    server.add_argument("--port", type=int, default=8073)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build(args.source, args.context, args.output, updates=args.updates)
            print(json.dumps({"cases": len(result["cases"]), "pack": str(args.output), "status": result["status"]}))
        else:
            serve(args.pack, args.port)
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Catalogue curation failed: {error}\n")


if __name__ == "__main__":
    main()
