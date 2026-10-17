"""Find teaching-source chord coverage gaps; never rewrite native predictions.

Online references describe teaching arrangements. Their palettes and short
explicit intro orders can suggest a review, but cannot certify a recording's
chords or physical change times. Results are a separately served sidecar.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit

import automatic_drafts as drafts
import core_chord_screen
import rich_quality_suite
import online_sources

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "online-chord-checks-1.0"
TARGET_SCHEMA = "online-chord-targets-1.0"
DEFAULT_PACK = ROOT / "experiments/generated/automatic-first-ten-v1"
DEFAULT_TARGETS = ROOT / "catalogue/online-chord-targets.json"
DEFAULT_CACHE = ROOT / "experiments/generated/online-source-cache-v1"
LIMITS = [
    "Teaching-source coverage is not chord accuracy or an accepted arrangement. Missing chords may belong to another section or variant.",
    "Two different source groups need not be independent transcriptions. Identical content and shared publisher groups are counted once.",
    "Unknown source setup abstains unless an explicitly recorded seed-specific teaching hypothesis supplies the missing fields.",
    "Replay windows retain native cue boundaries; untimed source order supplies no physical chord-change timestamps.",
    "No native chord, timing, lesson guide, model setting or practice/feedback storage is changed."
]


def canonical_url(value):
    """Compare seed identity without query/fragment or www spelling."""
    parsed = urlsplit(online_sources.canonical_url(value))
    return parsed.hostname.removeprefix("www.").lower() + parsed.path.rstrip("/")


def core_key(label):
    chord = core_chord_screen.core_semantics(label)
    return (chord["root"], chord["quality"]) if chord["status"] == "chord" else None


def normalize_source(source, seed=None):
    """Keep source facts; record every assumption used for sounding pitches."""
    result = {**source, "sounding_chords": [], "normalized_sections": []}
    setup = (seed or {}).get("comparison_setup", {})
    capo, tuning = source.get("capo"), source.get("tuning_shift_semitones")
    capo_basis = "source" if capo is not None else "unknown"
    tuning_basis = "source" if tuning is not None else "unknown"
    if capo is None and "capo" in setup:
        capo, capo_basis = setup["capo"], "catalogue-teaching-hypothesis"
    if tuning is None and "tuning_shift_semitones" in setup:
        tuning, tuning_basis = setup["tuning_shift_semitones"], "catalogue-teaching-hypothesis"
    result["normalization"] = {"capo": capo, "capo_basis": capo_basis,
                               "tuning_shift_semitones": tuning, "tuning_basis": tuning_basis}
    if source.get("status") != "extracted" or source.get("arrangement_variant"):
        result["comparison_status"] = "excluded-source"
        return result
    if (type(capo) is not int or not 0 <= capo <= 12 or type(tuning) is not int or not -12 <= tuning <= 12
            or source.get("label_basis") != "played-shapes"):
        result["comparison_status"] = "unknown-setup"
        return result
    shift = capo + tuning
    def sounding(label):
        return rich_quality_suite.transpose(label, shift)
    supported = [label for label in source.get("chord_shapes", [])
                 if rich_quality_suite.chord_semantics(label)["status"] == "chord"]
    result["sounding_chords"] = list(dict.fromkeys(sounding(label) for label in supported))
    for section in source.get("ordered_sections", []):
        chords = section.get("chords", [])
        if (section.get("name", "").lower() == "intro" and 3 <= len(chords) <= 16
                and all(rich_quality_suite.chord_semantics(label)["status"] == "chord" for label in chords)):
            result["normalized_sections"].append({"name": "intro", "chords": [sounding(label) for label in chords]})
    result["comparison_status"] = "teaching-hypothesis" if "catalogue-teaching-hypothesis" in (capo_basis, tuning_basis) else "source-setup"
    return result


def source_groups(sources):
    """A publisher or identical fetched page cannot supply extra votes."""
    usable = [source for source in sources if source.get("sounding_chords")]
    groups = []
    for source in usable:
        matches = [group for group in groups if any(
            other.get("origin_group") == source.get("origin_group")
            or (source.get("content_sha256") and other.get("content_sha256") == source["content_sha256"])
            for other in group)]
        merged = [source]
        for group in matches:
            merged.extend(group)
            groups.remove(group)
        groups.append(merged)
    return groups


def collapsed_events(chart):
    events = []
    for event in chart["chords"]:
        key = core_key(event["label"])
        if key is None:
            continue
        if events and events[-1]["key"] == key and events[-1]["end_seconds"] == event["start_seconds"]:
            events[-1]["end_seconds"] = event["end_seconds"]
        else:
            events.append({**event, "key": key})
    return events


def intro_findings(chart, groups):
    """Compare only an anchored opening prefix; do not force an alignment."""
    candidates = defaultdict(list)
    for index, group in enumerate(groups):
        for source in group:
            for section in source.get("normalized_sections", []):
                sequence = tuple(core_key(label) for label in section["chords"])
                candidates[sequence].append((index, source["id"]))
    # Multiple corroborated but conflicting intros are unresolved, not a vote.
    agreed = [(sequence, entries) for sequence, entries in candidates.items()
              if len({index for index, _ in entries}) >= 2]
    if len(agreed) != 1:
        return []
    sequence, entries = agreed[0]
    actual = collapsed_events(chart)
    if len(actual) < 3 or actual[0]["start_seconds"] > 5:
        return []
    prefix_end = actual[min(len(sequence), len(actual)) - 1]["end_seconds"]
    if any(core_key(event["label"]) is None and event["start_seconds"] >= actual[0]["start_seconds"]
           and event["start_seconds"] < prefix_end for event in chart["chords"]):
        return []
    matched = 0
    for expected, event in zip(sequence, actual):
        if event["key"] != expected:
            break
        matched += 1
    if matched < 3 or matched == len(sequence) or matched == len(actual):
        return []
    start = actual[matched - 1]["start_seconds"]
    end = prefix_end
    return [{"kind": "source-order-conflict", "start_seconds": start, "end_seconds": end,
             "native_label": actual[matched]["label"], "source_ids": sorted({sid for _, sid in entries}),
             "reason": f"Two source groups give the same intro order, but this draft diverges after {matched} opening changes. Replay this native window; section extent and missing-change times are unknown."}]


def check_case(case, primary, primary_sha256, sources, search=None, harmony_task=True):
    drafts.lab.validate_chart(primary)
    if any(case["recording"][key] != primary["recording"][key]
           for key in ("id", "audio_sha256", "duration_seconds", "sample_rate_hz")):
        raise ValueError("Source checks must identify the exact native recording")
    if case.get("artifacts", {}).get("primary_sha256") not in (None, primary_sha256):
        raise ValueError("Native primary chart bytes changed")
    groups = source_groups(sources) if harmony_task else []
    findings = []
    if len(groups) >= 2:
        palette = {core_key(label) for group in groups for source in group for label in source["sounding_chords"]}
        source_ids = sorted({source["id"] for group in groups for source in group})
        for event in primary["chords"]:
            key = core_key(event["label"])
            if key is None or key in palette:
                continue
            quality = any(root == key[0] for root, _ in palette)
            findings.append({"kind": "quality-conflict" if quality else "outside-source-palette",
                "start_seconds": event["start_seconds"], "end_seconds": event["end_seconds"],
                "native_label": event["label"], "source_ids": source_ids,
                "reason": f"Native {event['label']} is not covered by the extracted sounding-chord palettes from {len(groups)} source groups. It may be another section, voicing or teaching variant; check before correcting."})
        findings.extend(intro_findings(primary, groups))
    findings.sort(key=lambda finding: (finding["start_seconds"], finding["kind"]))
    for index, finding in enumerate(findings, 1):
        finding["id"] = f"online-{index:03d}"
    return {"recording": case["recording"], "primary_sha256": primary_sha256,
            "analysis_id": primary["analysis"]["id"], "status": "not-harmony-task" if not harmony_task else "source-checks" if len(groups) >= 2 else "insufficient-sources",
            "sources": sources, "search": search,
            "findings": findings, "summary": {"independent_source_groups": len(groups), "flagged_spans": len(findings),
                "source_count": len(sources), "sources_with_sounding_palette": sum(bool(s.get("sounding_chords")) for s in sources)},
            "limits": LIMITS}


def prepare(pack, targets_path, output, cache, *, root=ROOT, offline=False, refresh=False):
    pack = pack.resolve(strict=True)
    root = root.resolve(strict=True)
    if not pack.is_relative_to(root):
        raise ValueError("Pack must stay inside the project")
    # Reuse the guarded pack validation; never alter its manifest or native files.
    drafts.public_files(pack)
    targets_path = drafts.project_input(targets_path, root)
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    if targets.get("schema_version") != TARGET_SCHEMA or not isinstance(targets.get("cases"), list):
        raise ValueError("Invalid online chord targets")
    by_id = {target["recording_id"]: target for target in targets["cases"]}
    if len(by_id) != len(targets["cases"]):
        raise ValueError("Duplicate search target")
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if set(by_id) != {case["id"] for case in manifest["cases"]}:
        raise ValueError("Search targets must match the selected pack")
    output, cache = output.absolute(), cache.absolute()
    if (not output.resolve().is_relative_to(root) or not cache.resolve().is_relative_to(root)
            or output.exists() or output.is_symlink()):
        raise ValueError("Use a new project-local output directory and project-local cache")
    output.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".online-chords-", dir=output.parent))
    report = {"schema_version": SCHEMA, "pack_id": manifest["pack_id"],
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "gold": False,
              "status": "source-linked review hints; no automatic corrections", "cases": [],
              "inputs": {"pack_manifest_sha256": drafts.digest(pack / "manifest.json"), "targets_sha256": drafts.digest(targets_path)},
              "limits": LIMITS}
    try:
        for case in manifest["cases"]:
            target = by_id[case["id"]]
            primary_path = drafts.project_input(pack / "cases" / case["id"] / "primary.json", root)
            primary = json.loads(primary_path.read_text(encoding="utf-8"))
            if not target.get("harmony_task", True):
                report["cases"].append(check_case(case, primary, drafts.digest(primary_path), [], harmony_task=False))
                print(f"{case['id']}: riff case; harmony palette check skipped", flush=True)
                continue
            title, artist = target["title"], target["artist"]
            query = f"{artist} {title} guitar chords lesson"
            search = online_sources.discover(query, cache, refresh=refresh, offline=offline)
            seeds = target.get("seeds", [])
            if len(seeds) > 4:
                raise ValueError("At most four seed sources per song")
            seed_by_url = {canonical_url(seed["url"]): seed for seed in seeds}
            urls, seen = [], set()
            for url in [seed["url"] for seed in seeds] + search.get("urls", []):
                try:
                    canonical = canonical_url(url)
                    allowed = online_sources.allowed_source_url(url)
                except (ValueError, AttributeError):
                    continue
                # Explicit but unsupported seeds remain visible as abstentions;
                # arbitrary discovered domains are never fetched.
                if (allowed or canonical in seed_by_url) and canonical not in seen:
                    urls.append(url)
                    seen.add(canonical)
                if len(urls) >= 6:
                    break
            sources = []
            source_ids = set()
            for url in urls:
                source = online_sources.fetch_source(url, title, artist, cache, refresh=refresh, offline=offline)
                if source["id"] in source_ids:
                    continue
                source_ids.add(source["id"])
                source["discovery"] = "seed-and-search" if canonical_url(url) in seed_by_url and url in search.get("urls", []) else "catalogue-seed" if canonical_url(url) in seed_by_url else "online-search"
                sources.append(normalize_source(source, seed_by_url.get(canonical_url(url))))
            item = check_case(case, primary, drafts.digest(primary_path), sources, search)
            report["cases"].append(item)
            print(f"{case['id']}: search {search['status']}, {item['summary']['independent_source_groups']} source groups, {len(item['findings'])} hints", flush=True)
        drafts.write_json(staging / "report.json", report)
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--offline", action="store_true", help="Use fresh cached facts only; never make network requests")
    parser.add_argument("--refresh", action="store_true", help="Retrieve sources again instead of using fresh cache entries")
    args = parser.parse_args()
    if args.offline and args.refresh:
        parser.error("--offline and --refresh cannot be combined")
    try:
        report = prepare(args.pack, args.targets, args.output, args.cache, offline=args.offline, refresh=args.refresh)
        print(json.dumps({"report": str(args.output / "report.json"), "cases": len(report["cases"]),
                          "findings": sum(len(case["findings"]) for case in report["cases"])}))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Online chord preparation failed: {error}\n")


if __name__ == "__main__":
    main()
