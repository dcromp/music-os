"""Retrospective nominal barline agreement; never physical downbeat validation.

This adds a metric after model outputs were exposed. It uses every saved native
downbeat, including invalid endpoint/outside events as forced extras, without
phase fitting, trimming, snapping or changing the original pulse evaluator.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import rhythm_reference_eval as pulse

SCHEMA = "nominal-downbeat-evaluation-1.0"
VERSION = "0.1.0"


def _ordered(values, name: str) -> None:
    if (not isinstance(values, list)
            or any(not pulse._number(value) for value in values)
            or any(left >= right for left, right in zip(values, values[1:]))):
        raise ValueError(f"{name} must be finite strictly increasing times; empty estimates are allowed")


def native_downbeats(prediction: dict) -> tuple[list[float], str]:
    """Preserve saved raw values; refuse inconsistent bounded/raw interfaces."""
    saved = prediction.get("downbeat_times_seconds")
    _ordered(saved, "Saved downbeats")
    duration = prediction["recording"]["duration_seconds"]
    if "raw_downbeat_times_seconds" not in prediction:
        if "outside_recording_downbeat_times_seconds" in prediction:
            raise ValueError("Outside-event audit requires its complete raw downbeat list")
        return saved, "legacy_saved_list_raw_completeness_unverified"
    raw = prediction["raw_downbeat_times_seconds"]
    _ordered(raw, "Raw downbeats")
    inside = [value for value in raw if 0 <= value < duration]
    outside = [value for value in raw if not 0 <= value < duration]
    if (saved != inside
            or prediction.get("outside_recording_downbeat_times_seconds") != outside):
        raise ValueError("Bounded downbeats/outside audit disagree with the complete raw list")
    return raw, "raw_native_list_with_consistent_bounded_and_outside_audit"


def validate(references: dict, predictions: dict) -> tuple[str, list[tuple[dict, dict]]]:
    pairs = pulse.validate(references, predictions)
    conditions = set()
    for reference, prediction in pairs:
        if reference["recording"]["duration_seconds"] != prediction["recording"]["duration_seconds"]:
            raise ValueError("Nominal downbeat comparison requires the exact saved recording duration")
        if "nominal" not in reference["beat_reference_semantics"].lower():
            raise ValueError("Nominal downbeat comparison requires explicitly nominal reference semantics")
        bars = reference.get("barlines_seconds")
        if not isinstance(bars, list) or not bars:
            raise ValueError("Nominal downbeat evaluation requires explicit nonempty reference bar positions; beats alone cannot supply them")
        pulse._times(bars, reference["recording"]["duration_seconds"], "Nominal bar positions", minimum=1)
        beats = reference["beat_times_seconds"]
        if any(not any(abs(bar - beat) <= 1e-8 for beat in beats) for bar in bars):
            raise ValueError("Reference bar positions must occur on the supplied reference beat grid")
        native_downbeats(prediction)
        analysis = prediction.get("analysis")
        if not isinstance(analysis, dict) or analysis.get("downbeats_inferred") is not True:
            raise ValueError("Prediction must explicitly declare inferred downbeats")
        identifier = analysis.get("id")
        if not isinstance(identifier, str) or not pulse.ID_PATTERN.fullmatch(identifier):
            raise ValueError("Each prediction needs a safe analysis condition ID")
        conditions.add(identifier)
    if len(conditions) != 1:
        raise ValueError("Each prediction packet must contain exactly one analysis condition")
    return conditions.pop(), pairs


def match_barlines(reference: list[float], raw: list[float], duration: float, tolerance: float) -> dict:
    inside = [value for value in raw if 0 <= value < duration]
    invalid = len(raw) - len(inside)
    measured = pulse.match_pulses(reference, inside, tolerance)
    matched = measured["matched_pulses"]
    return {"tolerance_seconds": tolerance, "matched_barlines": matched,
            "missed_reference_barlines": len(reference) - matched,
            "extra_estimated_downbeats": len(raw) - matched,
            "invalid_outside_recording_downbeats": invalid,
            "precision": matched / len(raw) if raw else 0.,
            "recall": matched / len(reference),
            "f_measure": 2 * matched / (len(reference) + len(raw)),
            "matched_error_median_seconds": measured["matched_error_median_seconds"],
            "matched_error_p90_seconds": measured["matched_error_p90_seconds"],
            "matched_error_max_seconds": measured["matched_error_max_seconds"]}


def score_case(reference: dict, prediction: dict) -> dict:
    bars = reference["barlines_seconds"]
    raw, provenance = native_downbeats(prediction)
    duration = reference["recording"]["duration_seconds"]
    inside = [value for value in raw if 0 <= value < duration]
    outside = [value for value in raw if not 0 <= value < duration]
    nearest = [min(abs(bar - estimate) for estimate in inside) for bar in bars] if inside else []
    return {"recording": reference["recording"], "split": reference["split"],
        "beat_reference_semantics": reference["beat_reference_semantics"],
        "source": reference.get("source"), "prediction_analysis": prediction["analysis"],
        "native_provenance": provenance, "reference_bar_positions_seconds": bars,
        "saved_native_downbeat_times_seconds": raw,
        "invalid_outside_recording_downbeat_times_seconds": outside,
        "reference_barlines": len(bars), "estimated_downbeats_including_invalid": len(raw),
        "whole_recording": {f"f1_{round(tolerance * 1000)}ms":
            match_barlines(bars, raw, duration, tolerance) for tolerance in pulse.TOLERANCES},
        "nearest_reference_error_seconds": {"median": pulse.percentile(nearest, .5),
            "p90": pulse.percentile(nearest, .9), "max": max(nearest) if nearest else None,
            "semantics": "Every nominal reference barline, including misses; nearest in-recording estimate may be reused only for this diagnostic; null without an in-recording estimate."},
        "physical_downbeat_accuracy": {"status": "not_measured",
            "reason": "Reference bar positions are nominal metronome/lead-sheet events, not manually marked physical bar starts."}}


def aggregate(cases: list[dict]) -> dict:
    result = {"recordings": len(cases),
        "duration_seconds": sum(row["recording"]["duration_seconds"] for row in cases),
        "reference_barlines": sum(row["reference_barlines"] for row in cases),
        "estimated_downbeats_including_invalid": sum(row["estimated_downbeats_including_invalid"] for row in cases),
        "whole_recording": {}}
    for tolerance in pulse.TOLERANCES:
        key = f"f1_{round(tolerance * 1000)}ms"
        rows = [row["whole_recording"][key] for row in cases]
        matches = sum(row["matched_barlines"] for row in rows)
        misses = sum(row["missed_reference_barlines"] for row in rows)
        extras = sum(row["extra_estimated_downbeats"] for row in rows)
        refs, estimates = matches + misses, matches + extras
        result["whole_recording"][key] = {"matched_barlines": matches,
            "missed_reference_barlines": misses, "extra_estimated_downbeats": extras,
            "invalid_outside_recording_downbeats": sum(row["invalid_outside_recording_downbeats"] for row in rows),
            "micro_precision": matches / estimates if estimates else (0. if rows else None),
            "micro_recall": matches / refs if refs else None,
            "micro_f_measure": 2 * matches / (refs + estimates) if rows else None,
            "macro_f_measure": sum(row["f_measure"] for row in rows) / len(rows) if rows else None}
    return result


def evaluate(references_path: Path, prediction_paths: list[Path], output: Path) -> dict:
    if not prediction_paths:
        raise ValueError("At least one prediction packet is required")
    inputs = [references_path, *prediction_paths]
    pulse._output_available(output, inputs)
    references, reference_hash = pulse._load(references_path)
    conditions = []
    hashes = {}
    for path in prediction_paths:
        predictions, prediction_hash = pulse._load(path)
        condition, pairs = validate(references, predictions)
        if condition in hashes:
            raise ValueError("Duplicate prediction condition")
        hashes[condition] = prediction_hash
        cases = [score_case(reference, prediction) for reference, prediction in pairs]
        conditions.append({"condition": condition, "predictions_sha256": prediction_hash,
            "checkpoint_sha256": predictions.get("checkpoint_sha256"),
            "cases": cases, "aggregate": aggregate(cases),
            "by_split": {split: aggregate([row for row in cases if row["split"] == split])
                for split in ("development", "holdout")}})
    result = {"schema_version": SCHEMA, "version": VERSION,
        "reference_sha256": reference_hash, "evaluator_sha256": pulse.digest(Path(__file__)),
        "matching_evaluator_sha256": pulse.digest(Path(pulse.__file__)),
        "method": {"metric_timing": "Retrospective extra metric added after these model outputs were exposed",
            "reference_basis": "Nominal metronome/lead-sheet bar positions; physical bar starts are not gold",
            "matching": "Existing chronological maximum-cardinality one-to-one pulse matching; no offset/phase fit",
            "whole_recording_tolerances_seconds": list(pulse.TOLERANCES),
            "trim_seconds": None, "outside_recording_events": "Preserved and counted as forced extras, never matches",
            "reference_times_used_to_modify_predictions": False, "parameters_fitted_here": False,
            "model_inference_run_here": False, "production_downbeats_promoted": False},
        "limitations": ["Experiment holdouts were selected before inference, but this additional metric was not frozen before outputs were exposed.",
            "Nominal grid agreement does not establish physical bar-start accuracy, popular-song accuracy, chord boundaries, meter or strumming transcription.",
            "Model-training exclusion is unproven; this report is not a fresh model-generalisation claim.",
            "Legacy prediction packets without a raw list may have previously filtered events; every saved downbeat is scored, but native completeness is unverified.",
            "No acceptance threshold or product promotion is introduced."],
        "conditions": conditions}
    if pulse.digest(references_path) != reference_hash:
        raise ValueError("Reference input changed during scoring")
    for path, condition in zip(prediction_paths, conditions):
        if pulse.digest(path) != condition["predictions_sha256"]:
            raise ValueError("Prediction input changed during scoring")
    raw = json.dumps(result, indent=2, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                prefix=f".{output.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        pulse._output_available(output, inputs)
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.references, args.predictions, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Nominal downbeat evaluation failed: {error}\n")
    print(json.dumps({"output": str(args.output), "conditions": [
        {"condition": row["condition"], "aggregate": row["aggregate"]}
        for row in result["conditions"]]}, allow_nan=False))


if __name__ == "__main__":
    main()
