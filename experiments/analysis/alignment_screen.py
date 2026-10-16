"""Conditional timing screen: give the aligner intended labels, withhold times.

The runner reads generated references to make strictly untimed inputs, then
scores boundaries against the held-back timestamps after inference. This is
not an independent recognition evaluation: labels/order are deliberately given.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np

import chart_aligner
import lab


def optimal_boundary_matches(expected: list[float], actual: list[float], tolerance: float) -> list[tuple[int, int, float]]:
    """Ordered maximum-cardinality matching, then minimum summed absolute error."""
    counts = np.zeros((len(expected) + 1, len(actual) + 1), dtype=np.int32)
    costs = np.zeros_like(counts, dtype=float)
    choices = np.zeros_like(counts, dtype=np.uint8)
    choices[0, 1:] = 1
    for first in range(1, len(expected) + 1):
        for second in range(1, len(actual) + 1):
            candidates = [(counts[first - 1, second], costs[first - 1, second], 0),
                          (counts[first, second - 1], costs[first, second - 1], 1)]
            error = abs(expected[first - 1] - actual[second - 1])
            if error <= tolerance:
                candidates.append((counts[first - 1, second - 1] + 1,
                                   costs[first - 1, second - 1] + error, 2))
            count, cost, choice = max(candidates, key=lambda candidate: (candidate[0], -candidate[1], candidate[2]))
            counts[first, second], costs[first, second], choices[first, second] = count, cost, choice
    first, second, matches = len(expected), len(actual), []
    while first or second:
        choice = choices[first, second]
        if choice == 2:
            matches.append((first - 1, second - 1, abs(expected[first - 1] - actual[second - 1])))
            first, second = first - 1, second - 1
        elif choice == 1:
            second -= 1
        else:
            first -= 1
    return list(reversed(matches))


def boundary_metrics(reference: dict, prediction: dict, tolerance: float = 0.15) -> dict:
    lab.validate_chart(reference)
    lab.validate_chart(prediction)
    if reference["recording"]["id"] != prediction["recording"]["id"]:
        raise ValueError("Reference/prediction recording identities differ")
    if abs(reference["recording"]["duration_seconds"] - prediction["recording"]["duration_seconds"]) > 0.001:
        raise ValueError("Reference/prediction recording durations differ")
    if (reference["chords"][0]["start_seconds"] != 0 or
            abs(reference["chords"][-1]["end_seconds"] - reference["recording"]["duration_seconds"]) > 0.001 or
            any(abs(first["end_seconds"] - second["start_seconds"]) > 0.001
                for first, second in zip(reference["chords"], reference["chords"][1:]))):
        raise ValueError("This timing screen requires full contiguous reference coverage; score a fully annotated excerpt")
    expected = [(event["start_seconds"], event["label"] == "N" or reference["chords"][index - 1]["label"] == "N")
                for index, event in enumerate(reference["chords"]) if index]
    actual = [event["start_seconds"] for event in prediction["chords"][1:]]
    matches = optimal_boundary_matches([timestamp for timestamp, _ in expected], actual, tolerance)
    errors = [error for _, _, error in matches]
    precision = len(errors) / len(actual) if actual else 0.0
    recall = len(errors) / len(expected) if expected else 0.0
    expected_n_boundaries = sum(no_chord for _, no_chord in expected)
    actual_n_boundaries = [event["start_seconds"] for index, event in enumerate(prediction["chords"]) if index
                           and (event["label"] == "N" or prediction["chords"][index - 1]["label"] == "N")]
    n_matches = optimal_boundary_matches([timestamp for timestamp, no_chord in expected if no_chord],
                                        actual_n_boundaries, tolerance)
    n_errors = [error for _, _, error in n_matches]
    n_precision = len(n_errors) / len(actual_n_boundaries) if actual_n_boundaries else 0.0
    n_recall = len(n_errors) / expected_n_boundaries if expected_n_boundaries else 0.0
    duration = reference["recording"]["duration_seconds"]
    unknown = sum(event["end_seconds"] - event["start_seconds"] for event in prediction["chords"] if event["label"] == "X")
    predicted_n = sum(event["end_seconds"] - event["start_seconds"] for event in prediction["chords"] if event["label"] == "N")
    reference_n = sum(event["end_seconds"] - event["start_seconds"] for event in reference["chords"] if event["label"] == "N")
    matched_n = 0.0
    false_n = 0.0
    for expected_event in reference["chords"]:
        for actual_event in prediction["chords"]:
            if actual_event["label"] != "N":
                continue
            overlap = max(0.0, min(expected_event["end_seconds"], actual_event["end_seconds"])
                          - max(expected_event["start_seconds"], actual_event["start_seconds"]))
            if expected_event["label"] == "N":
                matched_n += overlap
            else:
                false_n += overlap
    return {"boundary_tolerance_seconds": tolerance,
            "boundary_precision_150ms": precision, "boundary_recall_150ms": recall,
            "boundary_f1_150ms": 2 * precision * recall / (precision + recall) if precision + recall else 0,
            "matched_boundary_mean_error_seconds": sum(errors) / len(errors) if errors else None,
            "reference_boundaries": len(expected), "predicted_boundaries": len(actual),
            "matched_boundaries": len(errors), "missed_reference_boundaries": len(expected) - len(errors),
            "extra_predicted_boundaries": len(actual) - len(errors),
            "reference_no_chord_boundaries": expected_n_boundaries,
            "predicted_no_chord_boundaries": len(actual_n_boundaries),
            "matched_no_chord_boundaries": len(n_errors),
            "missed_reference_no_chord_boundaries": expected_n_boundaries - len(n_errors),
            "no_chord_boundary_precision_150ms": n_precision, "no_chord_boundary_recall_150ms": n_recall,
            "no_chord_boundary_f1_150ms": 2 * n_precision * n_recall / (n_precision + n_recall) if n_precision + n_recall else 0,
            "matched_no_chord_boundary_mean_error_seconds": sum(n_errors) / len(n_errors) if n_errors else None,
            "unknown_duration_seconds": unknown, "unknown_fraction": unknown / duration,
            "predicted_no_chord_duration_seconds": predicted_n,
            "reference_no_chord_duration_seconds": reference_n,
            "reference_no_chord_duration_covered_fraction": matched_n / reference_n if reference_n else None,
            "false_no_chord_duration_on_annotated_harmony_seconds": false_n,
            "reference_coverage_fraction": sum(event["end_seconds"] - event["start_seconds"] for event in reference["chords"]) / duration}


def run(suite: Path, output: Path, *, overwrite: bool = False) -> dict:
    if (output / "report.json").exists() and not overwrite:
        raise ValueError("Screen report exists; use --overwrite to replace it")
    started = time.perf_counter()
    manifest_path = suite / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    protected_inputs = [manifest_path]
    output_paths = [output / "report.json"]
    for case in manifest["cases"]:
        for key in ("audio", "reference"):
            protected_inputs.append(suite / case[key])
        if re.fullmatch(r"[A-Za-z0-9_-]+", case["id"]):
            directory = output / "cases" / case["id"]
            output_paths.extend([directory / "untimed-input.json", directory / "alignment.json"])
    resolved_outputs = [path.resolve() for path in output_paths]
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise ValueError("Screen output artifact paths collide")
    # Preflight the complete batch before creating even the first chart. Each
    # publication checks again and atomically replaces/creates directory entries.
    for path in output_paths:
        chart_aligner.check_output_path(path, protected_inputs, overwrite=overwrite)
    cases = []
    for case in manifest["cases"]:
        result = {key: case[key] for key in ("id", "level", "condition", "split")}
        try:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", case["id"]):
                raise ValueError("Unsafe case ID")
            audio = (suite / case["audio"]).resolve()
            reference_path = (suite / case["reference"]).resolve()
            if not audio.is_relative_to(suite.resolve()) or not reference_path.is_relative_to(suite.resolve()):
                raise ValueError("Suite audio/reference must be inside the suite")
            reference = lab.load_chart(reference_path)
            sequence = [event["label"] for event in reference["chords"] if event["label"] != "N"]
            if not sequence:
                raise ValueError("No intended harmonic labels to align")
            untimed = {"schema_version": chart_aligner.SCHEMA,
                       "recording": {"id": reference["recording"]["id"], "title": reference["recording"]["title"],
                                     "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest()},
                       "sequence": sequence, "mode": "finite", "start_policy": "first", "end_policy": "last",
                       "metadata": {"source_references": [{"source": "procedural intended labels only", "case_id": case["id"]}],
                                    "note": "All reference timestamps and all N events withheld from alignment"}}
            try:
                chart_aligner.validate_untimed_chart(untimed)
            except ValueError as error:
                result.update(status="excluded", reason=f"Unsupported intended sequence: {error}")
                cases.append(result)
                continue
            directory = output / "cases" / case["id"]
            directory.mkdir(parents=True, exist_ok=True)
            input_path, result_path = directory / "untimed-input.json", directory / "alignment.json"
            if input_path.exists() and not overwrite:
                raise ValueError("Untimed input already exists; use --overwrite")
            chart_aligner.write_json_safely(input_path, untimed, protected_inputs, overwrite=overwrite)
            prediction = chart_aligner.align_to_file(audio, input_path, result_path, overwrite=overwrite)
            metrics = boundary_metrics(reference, prediction)
            result.update(status="ok", metrics=metrics,
                          diagnostics=prediction["alignment_evidence"]["diagnostics"],
                          alignment_runtime_seconds=prediction["analysis"]["runtime_seconds"],
                          missed_supplied_sequence_events=len(prediction["alignment_evidence"]["diagnostics"]["unvisited_sequence_indices"]),
                          audio_sha256=prediction["recording"]["audio_sha256"],
                          chart_sha256=prediction["alignment_input"]["chart_sha256"],
                          hidden_reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                          output=f"cases/{case['id']}/alignment.json")
        except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
            result.update(status="error", reason=str(error))
        cases.append(result)
    successful = [case for case in cases if case["status"] == "ok"]
    groups = defaultdict(list)
    for case in successful:
        groups["all"].append(case)
        groups[f"level_{case['level']}"].append(case)
        groups[f"split_{case['split']}"].append(case)
    summaries = {}
    for name, group in groups.items():
        summary = {"cases": len(group)}
        for metric in ("boundary_f1_150ms", "boundary_precision_150ms", "boundary_recall_150ms",
                       "matched_boundary_mean_error_seconds", "unknown_fraction", "reference_coverage_fraction",
                       "reference_no_chord_duration_covered_fraction", "no_chord_boundary_f1_150ms",
                       "matched_no_chord_boundary_mean_error_seconds"):
            values = [case["metrics"][metric] for case in group if case["metrics"][metric] is not None]
            summary[metric] = float(np.mean(values)) if values else None
        for metric in ("reference_boundaries", "predicted_boundaries", "missed_reference_boundaries",
                       "extra_predicted_boundaries", "reference_no_chord_boundaries",
                       "missed_reference_no_chord_boundaries", "unknown_duration_seconds",
                       "false_no_chord_duration_on_annotated_harmony_seconds"):
            summary[metric] = sum(case["metrics"][metric] for case in group)
        summary["missed_supplied_sequence_events"] = sum(case["missed_supplied_sequence_events"] for case in group)
        summary["alignment_runtime_seconds"] = sum(case["alignment_runtime_seconds"] for case in group)
        summary["needs_review_cases"] = sum(case["diagnostics"]["acoustic_fit_status"] != "no_large_mismatch_detected" for case in group)
        summaries[name] = summary
    report = {"schema_version": "conditional-alignment-screen-1.0", "algorithm_version": chart_aligner.VERSION,
              "suite_version": manifest.get("suite_version"),
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "requested_cases": len(cases), "successful_cases": len(successful),
              "excluded_cases": sum(case["status"] == "excluded" for case in cases),
              "failed_cases": sum(case["status"] == "error" for case in cases),
              "runtime_seconds": time.perf_counter() - started,
              "parameters": {"untimed_sequence": "all ordered non-N intended labels; no timestamps or reference N events",
                             "mode": "finite", "start_policy": "first", "end_policy": "last",
                             "aligner_parameters": "fixed chart_aligner v0.1.0 defaults before real-song output review"},
              "metric_definition": "Unweighted case means; all starts after the first event are boundaries, including N/X transitions. Ordered one-to-one matching maximises matched boundary count within150ms, then minimises summed absolute error. N-boundary metrics separately match only boundaries touching an N event. Mean errors include matched boundaries only; missed/extra counts must be read alongside them.",
              "limitations": ["Labels, event count and order are supplied from generated intended harmony; this is conditional timing, not recognition accuracy.",
                              "The scorer reads hidden times after inference; the aligner receives audio and untimed chart only.",
                              "Full finite endpoint constraints may force transitions for a wrong sequence; gap and acoustic-fit diagnostics remain necessary.",
                              "These64 procedural cases have full reference coverage. Partial annotation outside a real excerpt cannot establish whole-song timing accuracy.",
                              "N boundaries are scored separately. Unknown/X duration reduces useful chart coverage even when a nearby boundary matches.",
                              "All screen and holdout recipes share a procedural generator; these results do not demonstrate real-song generalisation."],
              "summary": summaries, "cases": cases}
    chart_aligner.write_json_safely(output / "report.json", report, protected_inputs, overwrite=overwrite)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=lab.GENERATED / "synthetic-suite")
    parser.add_argument("--output", type=Path, default=lab.GENERATED / "alignment-screen")
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    try:
        report = run(arguments.suite, arguments.output, overwrite=arguments.overwrite)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        parser.exit(2, f"Screen failed: {error}\n")
    print(json.dumps({"report": str(arguments.output / "report.json"),
                      "successful_cases": report["successful_cases"], "excluded_cases": report["excluded_cases"],
                      "failed_cases": report["failed_cases"], "summary": report["summary"]}, indent=2))
    if report["failed_cases"] or report["excluded_cases"]:
        parser.exit(2)


if __name__ == "__main__":
    main()
