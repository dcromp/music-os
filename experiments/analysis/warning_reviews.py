"""Attach bounded review dispositions to a new online warning report.

This offline metadata step preserves every original finding and native chart.
Proposals remain model-exposed review notes, never player chord corrections.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "online-warning-reviews-1.0"
REVIEW_SCHEMA = "online-finding-review-1.0"
STATUSES = {"covered-by-provisional-guide", "local-evidence-proposal", "inconclusive"}
BINDING_FIELDS = {"id", "kind", "start_seconds", "end_seconds", "native_label", "source_ids"}
REVIEW_FIELDS = {"schema_version", "status", "gold", "candidate_exposure", "actor", "reviewed_at_utc",
                 "note", "guide_correction_ids", "proposal", "evidence_refs"}
MAX_BYTES = 1048576


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value, limit):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def project_file(value, root, *, existing=True):
    """Preserve path spelling below the root so aliases cannot hide symlinks."""
    root = Path(root).resolve(strict=True)
    path = Path(value)
    path = path if path.is_absolute() else root / path
    if not path.is_relative_to(root):
        raise ValueError("Use a project-local regular metadata file")
    relative = path.relative_to(root)
    if not relative.parts or any(part in {"", ".", ".."} or part.startswith(".") for part in relative.parts):
        raise ValueError("Private or aliased metadata paths are not allowed")
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("Metadata paths must not contain symlinks")
    if existing and (not path.is_file() or path.stat().st_size > MAX_BYTES):
        raise ValueError("Expected a bounded regular metadata file")
    return path


def json_snapshot(path):
    """Parse and hash the same bounded bytes, rather than reopening a source."""
    body = path.read_bytes()
    if len(body) > MAX_BYTES:
        raise ValueError("Expected a bounded regular metadata file")
    return json.loads(body.decode("utf-8")), hashlib.sha256(body).hexdigest()


def validate_binding(binding, finding):
    if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
        raise ValueError("Review needs the complete exact finding binding")
    for field in BINDING_FIELDS - {"source_ids"}:
        if binding.get(field) != finding.get(field):
            raise ValueError("Review belongs to a different source-check finding")
    sources = binding.get("source_ids")
    if (not isinstance(sources, list) or not 1 <= len(sources) <= 32
            or any(not text(value, 80) for value in sources) or len(set(sources)) != len(sources)
            or set(sources) != set(finding.get("source_ids", []))):
        raise ValueError("Review source identities changed")
    if (not number(binding.get("start_seconds")) or not number(binding.get("end_seconds"))
            or not 0 <= binding["start_seconds"] < binding["end_seconds"]):
        raise ValueError("Review finding bounds must remain finite")


def validate_review(review, root):
    if (not isinstance(review, dict) or set(review) != REVIEW_FIELDS
            or review.get("schema_version") != REVIEW_SCHEMA or review.get("status") not in STATUSES
            or review.get("gold") is not False or review.get("candidate_exposure") != "model-exposed"
            or review.get("actor") != "agent" or not text(review.get("note"), 1500)):
        raise ValueError("Review dispositions remain bounded model-exposed agent notes")
    stamp = review.get("reviewed_at_utc")
    try:
        if not text(stamp, 64) or datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Review needs a timezone-aware date") from error
    guides = review.get("guide_correction_ids")
    if (not isinstance(guides, list) or len(guides) > 16 or any(not text(value, 100) for value in guides)
            or len(set(guides)) != len(guides)
            or bool(guides) != (review["status"] == "covered-by-provisional-guide")):
        raise ValueError("Only a covered finding may identify provisional guide corrections")
    proposal = review.get("proposal")
    if review["status"] == "local-evidence-proposal":
        if (not isinstance(proposal, dict) or set(proposal) != {"label", "timing_status"}
                or not text(proposal.get("label"), 40)
                or not re.fullmatch(r"[A-G][#b]?[A-Za-z0-9#b():,./+*\-]*", proposal["label"])
                or proposal.get("timing_status") != "native-boundaries-unverified"):
            raise ValueError("A local proposal needs a chord label with unverified native bounds")
    elif proposal is not None:
        raise ValueError("Only a local-evidence proposal may suggest a chord")
    refs = review.get("evidence_refs")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 16:
        raise ValueError("Reviews need bounded project evidence references")
    seen = set()
    for ref in refs:
        if (not isinstance(ref, dict) or set(ref) != {"path", "sha256"}
                or not text(ref.get("path"), 300) or not re.fullmatch(r"[a-f0-9]{64}", ref.get("sha256", ""))):
            raise ValueError("Invalid evidence reference")
        path = Path(ref["path"])
        if (path.is_absolute() or not path.parts or path.parts[0] not in {"docs", "catalogue"}
                or path.suffix not in {".json", ".md"} or ref["path"] in seen):
            raise ValueError("Evidence references must name public catalogue/docs metadata, not media or sessions")
        evidence = project_file(path, root)
        if digest(evidence) != ref["sha256"]:
            raise ValueError("Review evidence hash changed")
        seen.add(ref["path"])


def apply_reviews(report, reviews, *, root=ROOT):
    """Return a copy; never mutate the source report or its warning count."""
    if (not isinstance(report, dict) or report.get("schema_version") != "online-chord-checks-1.0"
            or not text(report.get("pack_id"), 100) or not isinstance(report.get("cases"), list)
            or not isinstance(reviews, dict) or reviews.get("schema_version") != SCHEMA
            or reviews.get("pack_id") != report["pack_id"] or not isinstance(reviews.get("cases"), list)
            or not 1 <= len(reviews["cases"]) <= 64):
        raise ValueError("Review input must identify this online report's pack")
    result = copy.deepcopy(report)
    cases = {}
    for case in result["cases"]:
        identifier = case.get("recording", {}).get("id")
        if not text(identifier, 80) or identifier in cases or not isinstance(case.get("findings"), list):
            raise ValueError("Invalid or duplicate online report recording")
        cases[identifier] = case
        if any("review" in finding or "review_binding" in finding for finding in case["findings"]):
            raise ValueError("Use an original report without previous review annotations")
    seen_cases = set()
    for reviewed in reviews["cases"]:
        if not isinstance(reviewed, dict):
            raise ValueError("Invalid recording review")
        recording = reviewed.get("recording", {})
        identifier = recording.get("id") if isinstance(recording, dict) else None
        if identifier not in cases or identifier in seen_cases:
            raise ValueError("Review identifies an unknown or duplicate recording")
        seen_cases.add(identifier)
        case = cases[identifier]
        if (any(recording.get(key) != case["recording"].get(key)
                for key in ("id", "audio_sha256", "sample_rate_hz", "duration_seconds"))
                or reviewed.get("primary_sha256") != case.get("primary_sha256")
                or reviewed.get("analysis_id") != case.get("analysis_id")
                or not re.fullmatch(r"[a-f0-9]{64}", reviewed.get("primary_sha256", ""))):
            raise ValueError("Review belongs to different exact audio or native chart")
        entries = reviewed.get("findings")
        if not isinstance(entries, list) or not 1 <= len(entries) <= 512:
            raise ValueError("Review needs bounded finding entries")
        findings = {finding["id"]: finding for finding in case["findings"]}
        if len(findings) != len(case["findings"]):
            raise ValueError("Duplicate native warning identities")
        seen_findings = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"finding_binding", "review"}:
                raise ValueError("Invalid finding review entry")
            binding = entry["finding_binding"]
            fid = binding.get("id") if isinstance(binding, dict) else None
            if fid not in findings or fid in seen_findings:
                raise ValueError("Unknown or duplicate finding review")
            seen_findings.add(fid)
            validate_binding(binding, findings[fid])
            validate_review(entry["review"], root)
            findings[fid]["review"] = copy.deepcopy(entry["review"])
            findings[fid]["review_binding"] = copy.deepcopy(binding)
    return result


def prepare(report_path, reviews_path, output_path, *, root=ROOT):
    report_path = project_file(report_path, root)
    reviews_path = project_file(reviews_path, root)
    output_path = project_file(output_path, root, existing=False)
    if output_path.exists() or output_path.is_symlink():
        raise ValueError("Use a new output file; existing reports are never overwritten")
    report, report_sha256 = json_snapshot(report_path)
    reviews, reviews_sha256 = json_snapshot(reviews_path)
    result = apply_reviews(report, reviews, root=root)
    inputs = {report_path: report_sha256, reviews_path: reviews_sha256}
    for case in result["cases"]:
        for finding in case["findings"]:
            for ref in finding.get("review", {}).get("evidence_refs", []):
                path = project_file(ref["path"], root)
                if path in inputs and inputs[path] != ref["sha256"]:
                    raise ValueError("Conflicting input or evidence hashes")
                inputs[path] = ref["sha256"]
    result["review_inputs"] = {"report_sha256": report_sha256, "reviews_sha256": reviews_sha256,
                              "builder_sha256": digest(Path(__file__))}
    body = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if len(body.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Enriched report exceeds the existing online metadata size limit")
    # Recheck every source and evidence pin immediately before publication.
    # Revalidating paths also rejects files replaced with symlink aliases.
    if any(digest(project_file(path, root)) != expected for path, expected in inputs.items()):
        raise ValueError("Inputs or evidence changed during review preparation; no report published")
    output_path = project_file(output_path, root, existing=False)
    # No directory creation or overwrite; callers select an existing project folder.
    with output_path.open("x", encoding="utf-8") as handle:
        handle.write(body)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.report, args.reviews, args.output)
        print(json.dumps({"report": str(args.output), "reviewed_findings": sum(
            "review" in finding for case in result["cases"] for finding in case["findings"])}))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Warning review preparation failed: {error}\n")


if __name__ == "__main__":
    main()
