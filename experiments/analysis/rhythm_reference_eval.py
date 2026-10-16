"""Frozen pulse/count diagnostics against paired independent recording references.

References are read only after pulse extraction. This scorer neither tunes a
tracker nor promotes a grid to a verified meter, downbeat or song arrangement.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import tempfile

SCHEMA = "rhythm-reference-evaluation-1.0"
VERSION = "0.1.0"
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,127}")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")
WINDOW_BARS = {"half_bar": .5, "one_bar": 1., "two_bars": 2.}
TOLERANCES = (.07, .15)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _load(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError(f"Nonfinite JSON number: {value}")
    packet = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    if not isinstance(packet, dict):
        raise ValueError("Expected a JSON object")
    return packet, hashlib.sha256(raw).hexdigest()


def _times(values, duration: float, name: str, *, minimum: int = 2) -> None:
    if (not isinstance(values, list) or len(values) < minimum
            or any(not _number(value) or not 0 <= value < duration for value in values)
            or any(left >= right for left, right in zip(values, values[1:]))):
        raise ValueError(f"{name} must be finite, strictly increasing times inside the recording")


def pulse_position(times: list[float], timestamp: float) -> float | None:
    """Interpolate an ordinal pulse coordinate only inside observed coverage."""
    if timestamp < times[0] or timestamp > times[-1]:
        return None
    if timestamp == times[-1]:
        return float(len(times) - 1)
    index = bisect_right(times, timestamp) - 1
    return index + (timestamp - times[index]) / (times[index + 1] - times[index])


def _recording(recording: dict) -> None:
    if not isinstance(recording, dict):
        raise ValueError("Recording identity is required")
    identifier = recording.get("id")
    if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
        raise ValueError("Recording needs a safe ID")
    if (recording.get("sample_rate_hz") != 22050
            or not isinstance(recording.get("sample_rate_hz"), int)
            or isinstance(recording.get("sample_rate_hz"), bool)):
        raise ValueError("Recording sample rate must be 22050 Hz")
    if not _number(recording.get("duration_seconds")) or recording["duration_seconds"] <= 0:
        raise ValueError("Recording duration must be positive and finite")
    if not isinstance(recording.get("audio_sha256"), str) or not SHA_PATTERN.fullmatch(recording["audio_sha256"]):
        raise ValueError("Recording needs its exact audio SHA-256")


def validate(references: dict, predictions: dict) -> list[tuple[dict, dict]]:
    if references.get("schema_version") != "rhythm-references-1.0":
        raise ValueError("Expected rhythm-references-1.0 references")
    if predictions.get("schema_version") != "playalong-rhythm-1.0":
        raise ValueError("Expected playalong-rhythm-1.0 predictions")
    packets = []
    for document, is_reference in ((references, True), (predictions, False)):
        cases = document.get("cases")
        if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
            raise ValueError("Each document needs 1–64 recording cases")
        mapped = {}
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError("Every case must be an object")
            recording = case.get("recording")
            _recording(recording)
            identifier, duration = recording["id"], recording["duration_seconds"]
            if identifier in mapped:
                raise ValueError("Duplicate recording ID")
            _times(case.get("beat_times_seconds"), duration, "Beat times")
            if is_reference:
                if case.get("split") not in ("development", "holdout"):
                    raise ValueError("Reference split must be development or holdout")
                semantics = case.get("beat_reference_semantics")
                if not isinstance(semantics, str) or not semantics.strip():
                    raise ValueError("Reference beat semantics are required")
                if "barlines_seconds" in case:
                    _times(case["barlines_seconds"], duration, "Reference barlines", minimum=0)
                windows = case.get("count_windows", [])
                if not isinstance(windows, list):
                    raise ValueError("Reference count_windows must be a list")
                for window in windows:
                    if not isinstance(window, dict) or window.get("type") not in WINDOW_BARS:
                        raise ValueError("Reference count window needs a known type")
                    start, end = window.get("start_seconds"), window.get("end_seconds")
                    if not _number(start) or not _number(end) or not 0 <= start < end < duration:
                        raise ValueError("Count window endpoints must be ordered inside the recording")
                    expected, bars = window.get("expected_beats"), window.get("expected_bars")
                    if (not _number(expected) or expected <= 0 or not _number(bars)
                            or bars != WINDOW_BARS[window["type"]]):
                        raise ValueError("Count window needs positive beats and matching expected bars")
                    first = pulse_position(case["beat_times_seconds"], start)
                    last = pulse_position(case["beat_times_seconds"], end)
                    if first is None or last is None or abs(last - first - expected) > 1e-7:
                        raise ValueError("Count window expected beats disagree with reference pulse endpoints")
            mapped[identifier] = case
        packets.append(mapped)
    reference_cases, prediction_cases = packets
    if set(reference_cases) != set(prediction_cases):
        raise ValueError("Reference and prediction recording sets must match exactly")
    paired = []
    for identifier, reference in reference_cases.items():
        prediction = prediction_cases[identifier]
        first, second = reference["recording"], prediction["recording"]
        if first["audio_sha256"] != second["audio_sha256"]:
            raise ValueError(f"Recording {identifier} audio SHA-256 mismatch")
        if (first["sample_rate_hz"] != second["sample_rate_hz"]
                or abs(first["duration_seconds"] - second["duration_seconds"]) > 1 / first["sample_rate_hz"]):
            raise ValueError(f"Recording {identifier} duration/sample rate mismatch")
        paired.append((reference, prediction))
    return paired


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (position - lower)


def match_pulses(reference: list[float], estimated: list[float], tolerance: float) -> dict:
    """Maximum-cardinality chronological one-to-one matching, not nearest reuse.

    Earliest compatible pairs give maximum matches for sorted timestamps and a
    fixed symmetric tolerance. Error summaries describe those declared pairs;
    there is no offset fitting or global minimum-error reassignment.
    """
    if not _number(tolerance) or tolerance <= 0:
        raise ValueError("Matching tolerance must be positive and finite")
    first = second = 0
    errors = []
    while first < len(reference) and second < len(estimated):
        delta = estimated[second] - reference[first]
        if delta < -tolerance - 1e-12:
            second += 1
        elif delta > tolerance + 1e-12:
            first += 1
        else:
            errors.append(abs(delta))
            first += 1
            second += 1
    matches = len(errors)
    denominator = len(reference) + len(estimated)
    return {"tolerance_seconds": tolerance, "matched_pulses": matches,
            "missed_reference_pulses": len(reference) - matches,
            "extra_estimated_pulses": len(estimated) - matches,
            "precision": matches / len(estimated) if estimated else 0.,
            "recall": matches / len(reference) if reference else 0.,
            "f_measure": 2 * matches / denominator if denominator else 0.,
            "matched_error_median_seconds": percentile(errors, .5),
            "matched_error_p90_seconds": percentile(errors, .9),
            "matched_error_max_seconds": max(errors) if errors else None}


def standard_metrics(reference: list[float], estimated: list[float]) -> dict:
    """Lazy, pinned mir_eval metrics; the default warm-up trim is explicit."""
    import mir_eval
    import numpy as np
    refs = mir_eval.beat.trim_beats(np.asarray(reference, dtype=float), min_beat_time=5.)
    estimates = mir_eval.beat.trim_beats(np.asarray(estimated, dtype=float), min_beat_time=5.)
    result = {"minimum_beat_time_seconds": 5., "reference_pulses": len(refs),
              "estimated_pulses": len(estimates), "library": "mir_eval",
              "library_version": importlib.metadata.version("mir_eval")}
    if len(refs) < 2 or len(estimates) < 2:
        return {**result, "status": "insufficient_pulses_after_trim", "metrics": None}
    cemgil, cemgil_any = mir_eval.beat.cemgil(refs, estimates, cemgil_sigma=.04)
    cmlc, cmlt, amlc, amlt = mir_eval.beat.continuity(refs, estimates,
        continuity_phase_threshold=.175, continuity_period_threshold=.175)
    return {**result, "status": "measured", "metrics": {
        "f_measure_70ms": float(mir_eval.beat.f_measure(refs, estimates, f_measure_threshold=.07)),
        "cemgil_sigma_40ms": float(cemgil), "cemgil_any_metrical_level": float(cemgil_any),
        "cmlc": float(cmlc), "cmlt": float(cmlt), "amlc": float(amlc), "amlt": float(amlt)}}


def count_diagnostics(windows: list[dict], estimated: list[float]) -> dict:
    rows = []
    for window in windows:
        first = pulse_position(estimated, window["start_seconds"])
        last = pulse_position(estimated, window["end_seconds"])
        if first is None or last is None:
            rows.append({**window, "status": "unsupported_pulse_coverage", "estimated_beats": None,
                         "beat_count_error": None, "equivalent_bar_length_error": None})
        else:
            count = last - first
            error = count - window["expected_beats"]
            rows.append({**window, "status": "measured", "estimated_beats": count,
                         "beat_count_error": error,
                         "equivalent_bar_length_error": error * window["expected_bars"] / window["expected_beats"]})
    def summary(selected):
        measured = [row for row in selected if row["status"] == "measured"]
        errors = [abs(row["beat_count_error"]) for row in measured]
        return {"requested_windows": len(selected), "supported_windows": len(measured),
                "unsupported_windows": len(selected) - len(measured),
                "absolute_beat_count_error_mean": sum(errors) / len(errors) if errors else None,
                "absolute_beat_count_error_p90": percentile(errors, .9),
                "absolute_equivalent_bar_length_error_mean": (
                    sum(abs(row["equivalent_bar_length_error"]) for row in measured) / len(measured) if measured else None)}
    return {"summary": summary(rows), "by_type": {kind: summary([row for row in rows if row["type"] == kind])
            for kind in WINDOW_BARS}, "windows": rows}


def score_case(reference: dict, prediction: dict) -> dict:
    refs, estimates = reference["beat_times_seconds"], prediction["beat_times_seconds"]
    nearest = [min(abs(value - pulse) for pulse in estimates) for value in refs]
    return {"recording": reference["recording"], "split": reference["split"],
            "beat_reference_semantics": reference["beat_reference_semantics"],
            "prediction_analysis": prediction.get("analysis"),
            "reference_pulses": len(refs), "estimated_pulses": len(estimates),
            "coverage": {"first_reference_pulse_seconds": refs[0], "last_reference_pulse_seconds": refs[-1],
                "first_estimated_pulse_seconds": estimates[0], "last_estimated_pulse_seconds": estimates[-1],
                "reference_pulses_inside_estimated_coverage": sum(estimates[0] <= value <= estimates[-1] for value in refs),
                "reference_pulses_outside_estimated_coverage": sum(value < estimates[0] or value > estimates[-1] for value in refs)},
            "whole_recording": {f"f1_{round(tolerance * 1000)}ms": match_pulses(refs, estimates, tolerance)
                                for tolerance in TOLERANCES},
            "nearest_reference_error_seconds": {"median": percentile(nearest, .5),
                "p90": percentile(nearest, .9), "max": max(nearest),
                "semantics": "All reference pulses, including misses; nearest estimate may be reused for this diagnostic only."},
            "standard_after_5s": standard_metrics(refs, estimates),
            "count_windows": count_diagnostics(reference.get("count_windows", []), estimates),
            "downbeat_accuracy": {"status": "not_measured", "reason": "The tracker produces pulses, not downbeat predictions."},
            "bar_phase_accuracy": {"status": "not_measured", "reason": "Reference windows measure lengths; no predicted bar starts are supplied."}}


def aggregate(cases: list[dict]) -> dict:
    result = {"recordings": len(cases), "duration_seconds": sum(row["recording"]["duration_seconds"] for row in cases),
              "whole_recording": {}}
    for tolerance in TOLERANCES:
        key = f"f1_{round(tolerance * 1000)}ms"
        rows = [row["whole_recording"][key] for row in cases]
        matched = sum(row["matched_pulses"] for row in rows)
        missed = sum(row["missed_reference_pulses"] for row in rows)
        extras = sum(row["extra_estimated_pulses"] for row in rows)
        result["whole_recording"][key] = {"matched_pulses": matched, "missed_reference_pulses": missed,
            "extra_estimated_pulses": extras, "micro_f_measure": 2 * matched / (2 * matched + missed + extras) if rows else None,
            "macro_f_measure": sum(row["f_measure"] for row in rows) / len(rows) if rows else None}
    metrics = [row["standard_after_5s"]["metrics"] for row in cases if row["standard_after_5s"]["metrics"] is not None]
    result["standard_after_5s_macro"] = {"measured_recordings": len(metrics), "metrics": {
        name: sum(row[name] for row in metrics) / len(metrics) for name in metrics[0]} if metrics else None}
    windows = [window for row in cases for window in row["count_windows"]["windows"]]
    result["count_windows"] = count_diagnostics([], [0., 1.])["summary"]
    measured = [window for window in windows if window["status"] == "measured"]
    result["count_windows"].update(requested_windows=len(windows), supported_windows=len(measured),
        unsupported_windows=len(windows) - len(measured),
        absolute_beat_count_error_mean=sum(abs(window["beat_count_error"]) for window in measured) / len(measured) if measured else None,
        absolute_beat_count_error_p90=percentile([abs(window["beat_count_error"]) for window in measured], .9),
        absolute_equivalent_bar_length_error_mean=sum(abs(window["equivalent_bar_length_error"]) for window in measured) / len(measured) if measured else None)
    return result


def _output_available(output: Path, inputs: list[Path]) -> None:
    if output.is_symlink() or any(output.resolve() == source.resolve() for source in inputs):
        raise ValueError("Output cannot alias an input or be a symlink")
    if output.exists():
        raise ValueError("Output exists; use a fresh evaluation path")


def evaluate(references_path: Path, predictions_path: Path, output: Path, condition: str) -> dict:
    if not isinstance(condition, str) or not ID_PATTERN.fullmatch(condition):
        raise ValueError("Condition must be a safe name")
    inputs = [references_path, predictions_path]
    _output_available(output, inputs)
    references, reference_hash = _load(references_path)
    predictions, prediction_hash = _load(predictions_path)
    pairs = validate(references, predictions)
    cases = [score_case(reference, prediction) for reference, prediction in pairs]
    result = {"schema_version": SCHEMA, "version": VERSION, "condition": condition,
        "reference_sha256": reference_hash, "predictions_sha256": prediction_hash,
        "evaluator_sha256": digest(Path(__file__)),
        "method": {"matching": "chronological maximum-cardinality one-to-one; no offset fit",
            "whole_recording_tolerances_seconds": list(TOLERANCES), "standard_trim_seconds": 5.,
            "reference_times_used_to_modify_predictions": False, "parameters_fitted_here": False,
            "count_windows": "Reference-defined half/one/two-bar intervals; pulse ordinal interpolation without extrapolation",
            "downbeats_evaluated": False, "bar_starts_evaluated": False},
        "limitations": ["Any-metrical-level metrics may reward half/double/offbeat pulses; they do not validate bar lengths.",
            "Guided tempo conditions use declared priors and are not uninformed beat recognition.",
            "This diagnostic does not validate chord boundaries, strumming transcriptions or full song arrangements."],
        "cases": cases, "aggregate": aggregate(cases),
        "by_split": {split: aggregate([case for case in cases if case["split"] == split])
                     for split in ("development", "holdout")}}
    if digest(references_path) != reference_hash or digest(predictions_path) != prediction_hash:
        raise ValueError("Evaluation inputs changed during scoring")
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
        _output_available(output, inputs)
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.references, args.predictions, args.output, args.condition)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(2, f"Rhythm reference evaluation failed: {error}\n")
    print(json.dumps({"output": str(args.output), "condition": result["condition"],
                      "recordings": len(result["cases"]), "aggregate": result["aggregate"]}, allow_nan=False))


if __name__ == "__main__":
    main()
