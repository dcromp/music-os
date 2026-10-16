"""Native timing/contrast REVIEW cues, without snapping, refinement or approval.

Model agreement is not a timing reference. Chroma is context only and cannot
replace a native label. No supplied chord order or pulse grid is consumed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import time
import numpy as np
import automatic_drafts as drafts
import catalogue_pitch_check as pitch
import core_chord_screen
from core_chord_screen import core_semantics
import curation
import lab

ROOT = pitch.ROOT
SCHEMA = "catalogue-timing-review-1.0"
POLICY = {"pair_tolerance_seconds": .5, "review_difference_seconds": .15,
          "replay_padding_seconds": 1.5, "max_pair_cells": 1_000_000,
          "max_priority_windows": 12, "seam_annotation_radius_seconds": .5,
          "core_merge": "contiguous equivalent core only; no N/X/gap bridging",
          "matching": "monotone maximum count of compatible directed transitions, then minimum total absolute time difference",
          "uses_pulses": False, "refines_native_times": False, "accepts_arrangements": False}
DEFAULT_SPEC = ROOT / "experiments/fixtures/catalogue-starter-timing-v1.json"
DEFAULT_EVIDENCE = ROOT / "experiments/generated/catalogue-starter-four-pitch-v3-20261014"


def core_timeline(chart):
    lab.validate_chart(chart)
    duration = chart["recording"]["duration_seconds"]
    if any(event["end_seconds"] > duration for event in chart["chords"]):
        raise ValueError("Native timing must stay inside audio")
    result = []
    for event in chart["chords"]:
        value = core_semantics(event["label"])
        key = [value["root"], value["quality"]] if value["status"] == "chord" else [value["status"], event["label"]]
        if result and result[-1]["key"] == key and result[-1]["end_seconds"] == event["start_seconds"]:
            result[-1]["end_seconds"] = event["end_seconds"]
            if event["label"] not in result[-1]["source_labels"]: result[-1]["source_labels"].append(event["label"])
        else:
            result.append({"start_seconds": event["start_seconds"], "end_seconds": event["end_seconds"],
                           "key": key, "status": value["status"], "source_labels": [event["label"]]})
    return result


def transitions(chart):
    timeline = core_timeline(chart); events, gaps = [], []
    if timeline[0]["start_seconds"] > 0:
        gaps.append({"start_seconds": 0.0, "end_seconds": timeline[0]["start_seconds"]})
    for first, second in zip(timeline, timeline[1:]):
        if first["end_seconds"] < second["start_seconds"]:
            gaps.append({"start_seconds": first["end_seconds"], "end_seconds": second["start_seconds"]})
            continue
        events.append({"time_seconds": second["start_seconds"], "from_key": first["key"], "to_key": second["key"],
                       "from_labels": first["source_labels"], "to_labels": second["source_labels"],
                       "harmonic": first["status"] == second["status"] == "chord"})
    if timeline[-1]["end_seconds"] < chart["recording"]["duration_seconds"]:
        gaps.append({"start_seconds": timeline[-1]["end_seconds"], "end_seconds": chart["recording"]["duration_seconds"]})
    return events, gaps


def match_transitions(primary, secondary, tolerance=None):
    tolerance = POLICY["pair_tolerance_seconds"] if tolerance is None else tolerance
    if not curation.number(tolerance) or tolerance < 0:
        raise ValueError("Use a finite nonnegative pairing tolerance")
    for values in (primary, secondary):
        if any(not curation.number(item["time_seconds"]) or item["time_seconds"] < 0 for item in values) or any(a["time_seconds"] >= b["time_seconds"] for a, b in zip(values, values[1:])):
            raise ValueError("Boundary times must be finite and strictly increasing")
    m, n = len(primary), len(secondary)
    if (m + 1) * (n + 1) > POLICY["max_pair_cells"]: raise ValueError("Boundary pairing exceeds its fixed bound")
    counts = np.zeros((m + 1, n + 1), dtype=int); costs = np.zeros((m + 1, n + 1)); choices = np.zeros((m + 1, n + 1), dtype=np.uint8)
    choices[0, 1:] = 1
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            candidates = [(counts[i-1,j], costs[i-1,j], 0), (counts[i,j-1], costs[i,j-1], 1)]
            a, b = primary[i-1], secondary[j-1]; error = abs(a["time_seconds"] - b["time_seconds"])
            if a["from_key"] == b["from_key"] and a["to_key"] == b["to_key"] and error <= tolerance:
                candidates.append((counts[i-1,j-1] + 1, costs[i-1,j-1] + error, 2))
            counts[i,j], costs[i,j], choices[i,j] = max(candidates, key=lambda value: (value[0], -value[1], value[2]))
    i, j = m, n; matched = []
    while i or j:
        choice = choices[i,j]
        if choice == 2:
            matched.append((i-1, j-1, abs(primary[i-1]["time_seconds"] - secondary[j-1]["time_seconds"]))); i -= 1; j -= 1
        elif choice == 1: j -= 1
        else: i -= 1
    return list(reversed(matched))


def boundary_review(primary_chart, secondary_chart):
    if not curation.identity(primary_chart["recording"], secondary_chart["recording"]):
        raise ValueError("Pair only exact recordings")
    first, first_gaps = transitions(primary_chart); second, second_gaps = transitions(secondary_chart)
    matches = match_transitions(first, second); used_first = {i for i, _, _ in matches}; used_second = {j for _, j, _ in matches}
    duration = primary_chart["recording"]["duration_seconds"]
    chunk = primary_chart["analysis"].get("parameters", {}).get("chunk_seconds")
    seams = np.arange(chunk, duration, chunk).tolist() if curation.number(chunk) and chunk > 0 else []
    paired, priorities = [], []
    def cue(kind, times, detail):
        nearest = min(seams, key=lambda value: min(abs(value - t) for t in times)) if seams else None
        distance = min(abs(nearest - t) for t in times) if nearest is not None else None
        return {"kind": kind, "start_seconds": max(0.0, min(times) - POLICY["replay_padding_seconds"]),
                "end_seconds": min(duration, max(times) + POLICY["replay_padding_seconds"]),
                "near_btc_chunk_seam": distance is not None and distance <= POLICY["seam_annotation_radius_seconds"],
                "nearest_chunk_seam_seconds": nearest, "detail": detail}
    for i, j, error in matches:
        row = {"primary": first[i], "secondary": second[j], "absolute_difference_seconds": error}
        paired.append(row)
        if error > POLICY["review_difference_seconds"]: priorities.append(cue("model-time-disagreement", [first[i]["time_seconds"], second[j]["time_seconds"]], row))
    for name, values, used in (("primary", first, used_first), ("secondary", second, used_second)):
        for index, item in enumerate(values):
            if index not in used: priorities.append(cue("unpaired-" + name, [item["time_seconds"]], item))
    for name, gaps in (("primary", first_gaps), ("secondary", second_gaps)):
        for gap in gaps: priorities.append(cue(name + "-coverage-gap", [gap["start_seconds"], gap["end_seconds"]], gap))
    priorities.sort(key=lambda row: (0 if row["kind"] == "model-time-disagreement" else 1, -row["detail"].get("absolute_difference_seconds", 0), row["start_seconds"], row["kind"]))
    errors = [row["absolute_difference_seconds"] for row in paired]
    return {"primary_boundaries": len(first), "secondary_boundaries": len(second), "paired_boundaries": len(paired),
            "median_pair_difference_seconds": float(np.median(errors)) if errors else None,
            "maximum_pair_difference_seconds": max(errors) if errors else None, "pairs": paired,
            "all_review_windows": priorities, "selected_review_windows": priorities[:POLICY["max_priority_windows"]],
            "semantics": "Directed core-transition concordance and review workload, not timing accuracy or confidence; matching pairs are not verified boundaries."}


def key_for(label):
    value = core_semantics(label)
    if value["status"] != "chord": raise ValueError("Contrast labels must be harmonic")
    return [value["root"], value["quality"]]


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {"hold_rules", "acoustic_labels", "response_labels"}:
        raise ValueError("Use explicit review target rules, acoustic labels and optional responses")
    if not isinstance(profile["hold_rules"], list) or len(profile["hold_rules"]) > 8:
        raise ValueError("Too many hold rules")
    for rule in profile["hold_rules"]:
        if not isinstance(rule, dict) or set(rule) != {"label", "minimum_seconds", "purpose"} or not curation.number(rule["minimum_seconds"]) or not 0 < rule["minimum_seconds"] <= 600 or not curation.text(rule["purpose"], 400):
            raise ValueError("Use bounded native-hold review rules")
        key_for(rule["label"])
    for field in ("acoustic_labels", "response_labels"):
        values = profile[field]
        if not isinstance(values, list) or len(values) > 12 or any(not isinstance(value, str) for value in values) or len(set(values)) != len(values):
            raise ValueError("Use a small unique harmonic-label inventory")
        for value in values:
            key_for(value)
            pitch.palette_templates([value])
    if not profile["acoustic_labels"]: raise ValueError("Declare acoustic comparison labels")


def contrast_inventory(primary_chart, secondary_chart, profile, evidence):
    if not curation.identity(primary_chart["recording"], secondary_chart["recording"]): raise ValueError("Contrast charts must identify the same recording")
    if not curation.identity(evidence.get("recording"), primary_chart["recording"]): raise ValueError("Contrast evidence belongs to another recording")
    validate_profile(profile)
    features = pitch.features_from_nnls(evidence)
    duration = primary_chart["recording"]["duration_seconds"]
    inventories = []
    for name, chart, other in (("btc", primary_chart, secondary_chart), ("crema", secondary_chart, primary_chart)):
        other_timeline = core_timeline(other)
        for rule in profile["hold_rules"]:
            key = key_for(rule["label"])
            for run in core_timeline(chart):
                start, end = run["start_seconds"], run["end_seconds"]
                if run["key"] != key or end - start < rule["minimum_seconds"]: continue
                covered = sum(max(0.0, min(end, value["end_seconds"]) - max(start, value["start_seconds"])) for value in other_timeline if value["key"] == key)
                scores = {label: pitch.score_window(features, [label], duration, start, end)["proposed_zero_shift_cosine"] for label in profile["acoustic_labels"]}
                active = pitch.score_window(features, [rule["label"]], duration, start, end)["active_evidence_seconds"]
                inventories.append({"model": name, "native_span": run, "purpose": rule["purpose"],
                                    "other_model_same_core_seconds": covered, "span_seconds": end - start,
                                    "nnls_active_evidence_seconds": active, "nnls_cosine_by_label": scores,
                                    "accepted_section": False})
    response = {}
    if profile.get("response_labels"):
        keys = [key_for(label) for label in profile["response_labels"]]
        for name, chart in (("btc", primary_chart), ("crema", secondary_chart)):
            response[name] = [run for run in core_timeline(chart) if run["key"] in keys]
    return {"candidate_holds": inventories, "selected_response_runs": response,
            "semantics": "Native harmonic spans and a selected response inventory, not formal sections, attack/repeat counts or verified performance. Chroma is context; it never relabels."}


def run(pack, pitch_spec, evidence_root, spec_path, output, root=ROOT):
    pack, pitch_spec, evidence_root, spec_path = (path.resolve(strict=True) for path in (pack, pitch_spec, evidence_root, spec_path))
    root = root.resolve(); output = output.absolute()
    for path in (evidence_root, spec_path):
        if not path.is_relative_to(root): raise ValueError("Keep evidence and specification inside repository")
    if output.resolve().is_relative_to(evidence_root) or evidence_root.is_relative_to(output.resolve()):
        raise ValueError("Use an output separate from saved evidence")
    manifest, _, jobs, originals = pitch.preflight(pack, pitch_spec, output, root)
    spec = curation.read(spec_path); prior = curation.read(evidence_root / "report.json")
    if spec.get("schema_version") != "catalogue-timing-review-spec-1.0" or spec.get("policy") != POLICY or spec.get("pitch_spec_sha256") != drafts.digest(pitch_spec) or spec.get("evidence_report_sha256") != drafts.digest(evidence_root / "report.json"):
        raise ValueError("Timing policy or pinned input changed")
    if prior["pack_manifest_sha256"] != drafts.digest(pack / "manifest.json"): raise ValueError("Evidence belongs to another pack")
    previous = {case["id"]: case for case in prior["cases"]}
    if len(previous) != len(prior["cases"]) or set(spec["profiles"]) != {case["id"] for case, _, _ in jobs}:
        raise ValueError("Profiles and evidence must identify unique exact cases")
    for profile in spec["profiles"].values(): validate_profile(profile)
    originals.update({spec_path: drafts.digest(spec_path), evidence_root / "report.json": drafts.digest(evidence_root / "report.json"), Path(__file__): drafts.digest(Path(__file__))})
    dependencies = [Path(module.__file__) for module in (pitch, core_chord_screen, pitch.rich_quality_suite, pitch.nnls, pitch.chart_aligner, curation, curation.review_pack, drafts, lab)]
    originals.update({path: drafts.digest(path) for path in dependencies})
    loaded = []
    for case, folder, _ in jobs:
        path = evidence_root / case["id"] / "nnls-evidence.json"
        if not path.resolve().is_relative_to(evidence_root) or drafts.digest(path) != previous[case["id"]]["nnls_evidence_sha256"]: raise ValueError("Cached evidence changed")
        evidence = curation.read(path); pitch.nnls.validate_evidence(evidence, folder / "audio.wav")
        if not curation.identity(evidence["recording"], case["recording"]): raise ValueError("Evidence is not the exact recording")
        originals[path] = drafts.digest(path); loaded.append((case, folder, evidence))
    output.parent.mkdir(parents=True, exist_ok=True); staging = Path(tempfile.mkdtemp(prefix=".timing-review-", dir=output.parent)); started = time.perf_counter()
    try:
        cases = []
        for case, folder, evidence in loaded:
            first, second = (curation.read(folder / filename) for filename in ("primary.json", "crema.json"))
            review = curation.read(folder / "review.json")
            row = {"id": case["id"], "name": case["name"], "recording": case["recording"],
                   "native_artifacts": case["artifacts"], "boundaries": boundary_review(first, second),
                   "fixed_coverage_samples": [point for point in review["points"] if point["kind"] == "coverage-sample"],
                   "contrast": contrast_inventory(first, second, spec["profiles"][case["id"]], evidence),
                   "accepted_arrangement": False, "physical_timing_accuracy": None}
            cases.append(row); drafts.write_json(staging / (case["id"] + ".json"), row)
        private = pack / "private-drafts"
        if private.is_symlink() or set(private.glob("*.json")) != {path for path in originals if path.parent == private} or any(not path.exists() or drafts.digest(path) != digest for path, digest in originals.items()):
            raise ValueError("Inputs or saved drafts changed during review generation")
        result = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "unaccepted model-exposed timing/contrast review candidates", "gold": False,
                  "policy": POLICY, "module_sha256": originals[Path(__file__)], "spec_sha256": originals[spec_path],
                  "method_file_sha256": {str(path.relative_to(ROOT)): originals[path] for path in dependencies},
                  "pack_manifest_sha256": drafts.digest(pack / "manifest.json"), "evidence_report_sha256": drafts.digest(evidence_root / "report.json"),
                  "runtime_seconds": time.perf_counter() - started, "raw_charts_modified": False, "private_drafts_modified": False,
                  "physical_timing_accuracy": None, "human_correction_seconds": None, "cases": cases,
                  "limits": ["Agreement can share systematic timing/label errors; it is not a reference.",
                             "NNLS uses ~743ms windows/~93ms hops, unsuitable for verifying precise physical change times.",
                             "Repeated chord attacks do not make harmonic boundaries; holds do not determine strumming or bar counts.",
                             "Source-guided contrast targets do not identify complete formal sections.",
                             "No pulses, forced chord order, timestamp refinement or automatic lesson promotion."]}
        drafts.write_json(staging / "report.json", result); staging.rename(output); return result
    except Exception:
        shutil.rmtree(staging); raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=pitch.DEFAULT_PACK)
    parser.add_argument("--pitch-spec", type=Path, default=pitch.DEFAULT_SPEC)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pack, args.pitch_spec, args.evidence, args.spec, args.output)
    print(json.dumps({"cases": len(result["cases"]), "runtime_seconds": result["runtime_seconds"], "output": str(args.output)}))
