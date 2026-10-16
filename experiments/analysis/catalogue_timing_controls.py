"""Retrospective cached synthetic controls for native timing REVIEW cues.

No extraction or inference runs here. Procedural reference times are consumed
only after native BTC/CREMA review windows have been generated. Agreement never
supplies reference labels, timing truth, or arrangement acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import wave

# Resolve the checkout so the committed runner also works on another Mac.
ROOT = Path(__file__).resolve().parents[2]
import alignment_screen
import automatic_drafts as drafts
import catalogue_timing_review as timing
import curation
import lab

SCHEMA = "catalogue-timing-controls-1.0"
DEFAULT_SUITE = ROOT / "experiments/generated/synthetic-suite"
DEFAULT_SPEC = ROOT / "experiments/fixtures/catalogue-starter-timing-v1.json"
SELECTED_SPEC = ROOT / "experiments/fixtures/selected-workflow-v1.json"
POLICY = {
    "reference_tolerance_seconds": .15,
    "residual_association_tolerance_seconds": .5,
    "expected_cases": 64,
    "review_selection": "unchanged boundary_review all windows and its first 12 priorities",
    "typed_matching": "directed core transitions; monotone maximum count, then minimum total absolute error",
    "untyped_matching": "time-only ordered maximum count, then minimum total absolute error",
    "error_partition": "match at 150ms first; associate remaining compatible directed transitions within 500ms; remaining native points are extras and remaining reference transitions are operational misses",
    "coverage": "closed replay-window containment of point timestamps; half-open audio intervals for union duration",
    "false_positive_flags": "directly flagged native points that match a reference directed transition within 150ms; separate from correct points incidentally inside replay windows",
    "shared_error_shift_seconds": .30,
    "retunes_policy": False,
    "runs_extraction_or_inference": False,
    "selected_pipeline_score": False,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transition_key(item):
    return (item["time_seconds"], tuple(item["from_key"]), tuple(item["to_key"]))


def metric(reference, predicted, *, typed=True):
    tolerance = POLICY["reference_tolerance_seconds"]
    if typed:
        matches = timing.match_transitions(reference, predicted, tolerance)
    else:
        matches = alignment_screen.optimal_boundary_matches(
            [item["time_seconds"] for item in reference],
            [item["time_seconds"] for item in predicted], tolerance)
    used_reference = {i for i, _, _ in matches}
    used_prediction = {j for _, j, _ in matches}
    matched = len(matches)
    precision = matched / len(predicted) if predicted else None
    recall = matched / len(reference) if reference else None
    denominator = len(reference) + len(predicted)
    return {
        "reference_transitions": len(reference), "predicted_transitions": len(predicted),
        "matched_transitions": matched, "extra_native_points": len(predicted) - matched,
        "missed_reference_transitions": len(reference) - matched,
        "precision": precision, "recall": recall,
        "f1": 2 * matched / denominator if denominator else None,
        "matched_absolute_error_sum_seconds": sum(error for _, _, error in matches),
        "matched_mean_absolute_error_seconds": sum(error for _, _, error in matches) / matched if matched else None,
        "matches": [{"reference_index": i, "prediction_index": j, "absolute_error_seconds": error} for i, j, error in matches],
        "unmatched_reference_indices": [i for i in range(len(reference)) if i not in used_reference],
        "unmatched_prediction_indices": [j for j in range(len(predicted)) if j not in used_prediction],
    }


def metrics(reference, predicted):
    harmonic_reference = [value for value in reference if value["harmonic"]]
    harmonic_prediction = [value for value in predicted if value["harmonic"]]
    return {"typed_all": metric(reference, predicted),
            "untyped_all": metric(reference, predicted, typed=False),
            "typed_harmonic": metric(harmonic_reference, harmonic_prediction),
            "untyped_harmonic": metric(harmonic_reference, harmonic_prediction, typed=False)}


def error_partition(reference, predicted, strict_metric):
    """Keep timing errors distinct from extra points and absent transitions.

    The 500ms residual association is bookkeeping, not an enlarged passing
    tolerance. A wrong direction cannot associate even at the same timestamp.
    """
    ref_indices = strict_metric["unmatched_reference_indices"]
    pred_indices = strict_metric["unmatched_prediction_indices"]
    residual = timing.match_transitions([reference[i] for i in ref_indices],
                                        [predicted[j] for j in pred_indices],
                                        POLICY["residual_association_tolerance_seconds"])
    associated_reference = {ref_indices[i] for i, _, _ in residual}
    associated_prediction = {pred_indices[j] for _, j, _ in residual}
    return {
        "error_or_extra_prediction_indices": pred_indices,
        "timestamp_errors": [{"reference_index": ref_indices[i], "prediction_index": pred_indices[j],
                              "absolute_error_seconds": error} for i, j, error in residual],
        "extra_prediction_indices": [i for i in pred_indices if i not in associated_prediction],
        "operational_missed_reference_indices": [i for i in ref_indices if i not in associated_reference],
        "strict_missed_reference_indices": ref_indices,
    }


def union_seconds(windows):
    intervals = sorted((row["start_seconds"], row["end_seconds"]) for row in windows)
    total = 0.0
    if not intervals:
        return total
    start, end = intervals[0]
    for left, right in intervals[1:]:
        if left <= end:
            end = max(end, right)
        else:
            total += end - start
            start, end = left, right
    return total + end - start


def contains(windows, timestamp):
    return any(row["start_seconds"] <= timestamp <= row["end_seconds"] for row in windows)


def flagged_points(windows):
    """Direct source points only; replay padding does not make a point flagged."""
    found = {"primary": set(), "secondary": set()}
    for row in windows:
        if row["kind"] == "model-time-disagreement":
            for name in found:
                found[name].add(transition_key(row["detail"][name]))
        elif row["kind"] in {"unpaired-primary", "unpaired-secondary"}:
            name = row["kind"].removeprefix("unpaired-")
            found[name].add(transition_key(row["detail"]))
    return found


def fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def window_assessment(windows, duration, reference, primary, secondary, primary_metrics, secondary_metrics, partition):
    errors = partition["error_or_extra_prediction_indices"]
    timing_errors = [item["prediction_index"] for item in partition["timestamp_errors"]]
    extras = partition["extra_prediction_indices"]
    misses = partition["operational_missed_reference_indices"]
    strict_misses = partition["strict_missed_reference_indices"]
    def coverage(indices, events):
        count = sum(contains(windows, events[index]["time_seconds"]) for index in indices)
        return {"denominator": len(indices), "covered": count, "fraction": fraction(count, len(indices))}
    direct = flagged_points(windows)
    flagged = {}
    for name, events, values in (("primary", primary, primary_metrics), ("secondary", secondary, secondary_metrics)):
        correct = {item["prediction_index"] for item in values["matches"]}
        indices = [i for i, value in enumerate(events) if transition_key(value) in direct[name]]
        correct_flags = sum(i in correct for i in indices)
        incidental_correct = sum(i in correct and contains(windows, value["time_seconds"]) for i, value in enumerate(events))
        flagged[name] = {"direct_flagged_native_points": len(indices),
                         "reference_correct_flagged_native_points": correct_flags,
                         "reference_correct_flag_fraction": fraction(correct_flags, len(indices)),
                         "erroneous_or_extra_flagged_native_points": len(indices) - correct_flags,
                         "reference_correct_native_points_inside_windows": incidental_correct,
                         "flagged_native_indices": indices}
    seconds = union_seconds(windows)
    return {"window_count": len(windows), "sum_window_seconds": sum(row["end_seconds"] - row["start_seconds"] for row in windows),
            "union_window_seconds": seconds, "audio_seconds": duration, "fraction_of_audio": seconds / duration,
            "primary_errors_or_extras": coverage(errors, primary),
            "primary_timestamp_errors": coverage(timing_errors, primary),
            "primary_extra_native_points": coverage(extras, primary),
            "primary_operational_missed_reference_transitions": coverage(misses, reference),
            "primary_all_strict_missed_reference_transitions": coverage(strict_misses, reference),
            "direct_flags": flagged}


def evaluate_case(reference_chart, primary_chart, secondary_chart):
    # This call sees no reference: selection cannot adapt to known errors.
    review = timing.boundary_review(primary_chart, secondary_chart)
    reference, reference_gaps = timing.transitions(reference_chart)
    primary, primary_gaps = timing.transitions(primary_chart)
    secondary, secondary_gaps = timing.transitions(secondary_chart)
    primary_metrics, secondary_metrics = metrics(reference, primary), metrics(reference, secondary)
    partition = error_partition(reference, primary, primary_metrics["typed_all"])
    duration = primary_chart["recording"]["duration_seconds"]
    windows = {"all": review["all_review_windows"], "selected12": review["selected_review_windows"]}
    status_seconds = {}
    for name, chart in (("reference", reference_chart), ("primary", primary_chart), ("secondary", secondary_chart)):
        ledger = {key: 0.0 for key in ("chord", "no_chord", "unknown", "unsupported")}
        for run in timing.core_timeline(chart):
            ledger[run["status"]] += run["end_seconds"] - run["start_seconds"]
        ledger["uncovered"] = max(0.0, duration - sum(ledger.values()))
        status_seconds[name] = ledger
    return {"recording": primary_chart["recording"], "reference_transitions": reference,
            "primary_transitions": primary, "secondary_transitions": secondary,
            "timeline_status_seconds": status_seconds,
            "gaps": {"reference": reference_gaps, "primary": primary_gaps, "secondary": secondary_gaps},
            "reference_metrics": {"primary": primary_metrics, "secondary": secondary_metrics},
            "primary_error_partition": partition,
            "review": review,
            "window_assessment": {name: window_assessment(values, duration, reference, primary, secondary,
                                                           primary_metrics["typed_all"], secondary_metrics["typed_all"], partition)
                                  for name, values in windows.items()},
            "accepted_arrangement": False, "real_recording_accuracy": None}


def symbolic_chart(identifier, sequence):
    return {"schema_version": "1.0", "recording": {"id": identifier, "title": identifier,
             "duration_seconds": 6.0, "sample_rate_hz": 22050, "audio_sha256": "symbolic-only-no-pcm"},
            "analysis": {"id": "symbolic-control", "algorithm": "symbolic-control", "version": "1.0",
                         "runtime_seconds": 0, "parameters": {}},
            "chords": [{"start_seconds": start, "end_seconds": end, "label": label} for start, end, label in sequence]}


def symbolic_controls():
    reference = symbolic_chart("shared-shift", [(0, 1, "N"), (1, 2, "C"), (2, 3, "G"), (3, 4, "Am"), (4, 5, "C"), (5, 6, "N")])
    shifted = symbolic_chart("shared-shift", [(0, 1.3, "N"), (1.3, 2.3, "C"), (2.3, 3.3, "G"), (3.3, 4.3, "Am"), (4.3, 5.3, "C"), (5.3, 6, "N")])
    shared = evaluate_case(reference, shifted, shifted)
    wrong_first = symbolic_chart("wrong-direction", [(0, 1, "N"), (1, 3, "C"), (3, 5, "G"), (5, 6, "N")])
    wrong_second = symbolic_chart("wrong-direction", [(0, 1, "N"), (1, 3, "G"), (3, 5, "C"), (5, 6, "N")])
    first_transitions, _ = timing.transitions(wrong_first)
    second_transitions, _ = timing.transitions(wrong_second)
    directed = timing.match_transitions(first_transitions, second_transitions)
    untyped = alignment_screen.optimal_boundary_matches([item["time_seconds"] for item in first_transitions], [item["time_seconds"] for item in second_transitions], .15)
    silence = symbolic_chart("silence-preserved", [(0, 1, "C"), (1, 2, "N"), (2, 3, "C"), (3, 4, "X"), (4, 5, "C"), (5.5, 6, "C")])
    timeline = timing.core_timeline(silence)
    silence_transitions, gaps = timing.transitions(silence)
    assertions = {
        "shared_shift_models_pair_every_transition": shared["review"]["paired_boundaries"] == 5,
        "shared_shift_has_zero_pair_difference": shared["review"]["maximum_pair_difference_seconds"] == 0,
        "shared_shift_has_no_priority_windows": not shared["review"]["all_review_windows"],
        "shared_shift_fails_all_150ms_reference_matches": shared["reference_metrics"]["primary"]["typed_all"]["matched_transitions"] == 0 and shared["reference_metrics"]["primary"]["untyped_all"]["matched_transitions"] == 0,
        "wrong_direction_is_not_a_typed_pair": not directed,
        "wrong_direction_still_matches_by_time": len(untyped) == 3,
        "silence_unknown_and_gap_split_core_runs": len(timeline) == 6 and [row["status"] for row in timeline] == ["chord", "no_chord", "chord", "unknown", "chord", "chord"] and gaps == [{"start_seconds": 5, "end_seconds": 5.5}],
        "silence_unknown_transitions_remain_nonharmonic": len(silence_transitions) == 4 and not any(row["harmonic"] for row in silence_transitions),
    }
    return {"assertions": assertions, "all_expected_behaviors_passed": all(assertions.values()),
            "shared_both_plus_300ms": shared, "wrong_direction": {"typed_pairs": directed, "untyped_pairs": untyped},
            "silence_unknown_gap": {"timeline": timeline, "transitions": silence_transitions, "gaps": gaps},
            "scope": "Symbolic chart mechanics only; these controls contain no recorded or synthesized PCM."}


def aggregate(rows):
    output = {"case_count": len(rows), "audio_seconds": sum(row["recording"]["duration_seconds"] for row in rows),
              "reference_metrics": {}, "window_assessment": {}, "timeline_status_seconds": {}}
    for name in ("reference", "primary", "secondary"):
        output["timeline_status_seconds"][name] = {key: sum(row["timeline_status_seconds"][name][key] for row in rows)
                                                  for key in ("chord", "no_chord", "unknown", "unsupported", "uncovered")}
    for name in ("primary", "secondary"):
        output["reference_metrics"][name] = {}
        for kind in ("typed_all", "untyped_all", "typed_harmonic", "untyped_harmonic"):
            values = [row["reference_metrics"][name][kind] for row in rows]
            counts = {field: sum(value[field] for value in values) for field in ("reference_transitions", "predicted_transitions", "matched_transitions", "extra_native_points", "missed_reference_transitions", "matched_absolute_error_sum_seconds")}
            r, p, m = (counts[key] for key in ("reference_transitions", "predicted_transitions", "matched_transitions"))
            output["reference_metrics"][name][kind] = {**counts, "precision": fraction(m, p), "recall": fraction(m, r), "f1": fraction(2*m, r+p),
                "matched_mean_absolute_error_seconds": fraction(counts["matched_absolute_error_sum_seconds"], m)}
    for kind in ("all", "selected12"):
        values = [row["window_assessment"][kind] for row in rows]
        result = {field: sum(value[field] for value in values) for field in ("window_count", "sum_window_seconds", "union_window_seconds", "audio_seconds")}
        result["fraction_of_audio"] = fraction(result["union_window_seconds"], result["audio_seconds"])
        for field in ("primary_errors_or_extras", "primary_timestamp_errors", "primary_extra_native_points", "primary_operational_missed_reference_transitions", "primary_all_strict_missed_reference_transitions"):
            denominator = sum(value[field]["denominator"] for value in values)
            covered = sum(value[field]["covered"] for value in values)
            result[field] = {"denominator": denominator, "covered": covered, "fraction": fraction(covered, denominator)}
        result["direct_flags"] = {}
        for name in ("primary", "secondary"):
            counts = {field: sum(value["direct_flags"][name][field] for value in values) for field in ("direct_flagged_native_points", "reference_correct_flagged_native_points", "erroneous_or_extra_flagged_native_points", "reference_correct_native_points_inside_windows")}
            counts["reference_correct_flag_fraction"] = fraction(counts["reference_correct_flagged_native_points"], counts["direct_flagged_native_points"])
            result["direct_flags"][name] = counts
        output["window_assessment"][kind] = result
    return output


def provenance(charts, selected):
    groups = {}
    for model, values in charts.items():
        seen = {}
        for chart in values:
            analysis = chart["analysis"]
            parameters = analysis.get("parameters", {})
            if model == "btc":
                keys = ("device", "threads", "hop_samples", "chunk_seconds", "smoothing", "timing", "upstream_revision", "checkpoint_sha256", "torch_version", "librosa_version", "numpy_version")
                settings = selected["btc_settings"]
                compatible = (parameters.get("upstream_revision") == selected.get("btc_upstream_revision") and parameters.get("checkpoint_sha256") == selected.get("btc_checkpoint_sha256") and all(parameters.get(key) == settings.get(key) for key in ("device", "threads", "smoothing")))
                descriptions = {"timing": {"selected": settings.get("timing"), "cached": parameters.get("timing")},
                                "vocabulary": {"selected": settings.get("labels"), "cached": parameters.get("vocabulary")}}
            else:
                keys = ("model_version", "device", "intraop_threads", "inter_op_threads", "postprocessing")
                settings = selected["crema_settings"]
                compatible = parameters.get("model_version") == settings.get("model") and parameters.get("device") == settings.get("device") and all(str(parameters.get(key)) == str(settings.get(key)) for key in ("intraop_threads", "inter_op_threads")) and analysis.get("version", "").split("/")[0] == settings.get("package")
                descriptions = {"postprocessing": {"selected": settings.get("postprocessing"), "cached": parameters.get("postprocessing")}}
            value = {"algorithm": analysis.get("algorithm"), "version": analysis.get("version"), "parameters": {key: parameters.get(key) for key in keys}, "selected_declared_execution_settings_match": compatible,
                     "descriptive_fields": descriptions, "historical_execution_module_hashes_present": False,
                     "recording_provenance": chart["recording"].get("provenance")}
            key = json.dumps(value, sort_keys=True)
            if key not in seen: seen[key] = {**value, "cases": 0}
            seen[key]["cases"] += 1
        groups[model] = list(seen.values())
    return {"classification": "retrospective cached synthetic diagnostics; not a fresh selected-pipeline score",
            "selected_pipeline_score": False, "groups": groups,
            "limitations": ["Cached outputs were produced by earlier executions, not rerun through the selected catalogue pipeline.",
                           "Matching declared checkpoint/settings does not establish identical historical module bytes or a fresh validation split.",
                           "Synthetic audio is procedural; inherited native recording provenance strings are not proof of real music or human annotations."]}


def preflight(suite, spec_path, output):
    suite, spec_path = suite.resolve(strict=True), spec_path.resolve(strict=True)
    output = output.absolute()
    destination = output.resolve(strict=False)
    generated = ROOT / "experiments/generated"
    if not suite.is_relative_to(ROOT) or not spec_path.is_relative_to(ROOT):
        raise ValueError("Suite and frozen specification must stay inside canonical repository")
    if output.exists() or output.is_symlink() or not destination.is_relative_to(generated) or destination.is_relative_to(suite) or suite.is_relative_to(destination):
        raise ValueError("Use an unused repository generated output outside the input suite")
    manifest_path = suite / "manifest.json"
    manifest = curation.read(manifest_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != POLICY["expected_cases"] or len({row["id"] for row in cases}) != len(cases):
        raise ValueError("Expected all 64 unique cached synthetic cases")
    spec = curation.read(spec_path)
    if spec.get("schema_version") != "catalogue-timing-review-spec-1.0" or spec.get("policy") != timing.POLICY:
        raise ValueError("Timing spec must freeze the exact current native review policy")
    if timing.POLICY["max_priority_windows"] != 12:
        raise ValueError("This frozen control evaluates exactly the existing selected12 policy")
    selected = curation.read(SELECTED_SPEC)
    sources = {path: digest(path) for path in (manifest_path, spec_path, SELECTED_SPEC, Path(__file__).resolve())}
    for module in (timing, alignment_screen, drafts, curation, lab, timing.pitch):
        path = Path(module.__file__).resolve()
        sources[path] = digest(path)
    # Core semantics directly affects transition identity and must be pinned too.
    import core_chord_screen
    sources[Path(core_chord_screen.__file__).resolve()] = digest(core_chord_screen.__file__)
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename:
            path = Path(filename).resolve()
            if path.suffix == ".py" and path.is_relative_to(ROOT / "experiments/analysis"):
                sources[path] = digest(path)
    for path in (ROOT / "experiments/analysis/synthetic_suite.py", suite / "btc-batch-summary.json", suite / "crema-batch-summary.json"):
        if path.is_file(): sources[path] = digest(path)
    for relative, expected in selected["frozen_files"].items():
        path = ROOT / relative
        actual = digest(path)
        if actual != expected: raise ValueError("Stage 1 frozen pin changed: " + relative)
        sources[path] = actual
    jobs = []
    for row in cases:
        identifier = row["id"]
        if not curation.review_pack.safe_id(identifier): raise ValueError("Unsafe synthetic case ID")
        paths = {name: suite / relative for name, relative in (("audio", row["audio"]), ("reference", row["reference"]), ("btc", "cases/" + identifier + "/btc.json"), ("crema", "cases/" + identifier + "/crema.json"))}
        for path in paths.values():
            if not path.resolve(strict=True).is_relative_to(suite): raise ValueError("Case path escapes suite")
            sources[path] = digest(path)
        if sources[paths["audio"]] != row["audio_sha256"]: raise ValueError("Synthetic audio hash mismatch")
        reference, first, second = (curation.read(paths[name]) for name in ("reference", "btc", "crema"))
        for value in (reference, first, second):
            lab.validate_chart(value)
            if value["recording"]["id"] != identifier: raise ValueError("Case recording ID mismatch")
        if not curation.identity(first["recording"], second["recording"]): raise ValueError("Cached models are not exact paired")
        for chart in (first, second):
            if chart["recording"].get("audio_sha256") != sources[paths["audio"]]: raise ValueError("Prediction audio hash mismatch")
        with wave.open(str(paths["audio"]), "rb") as audio:
            rate, frames = audio.getframerate(), audio.getnframes()
            duration = frames / rate
            if rate != 22050 or audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE": raise ValueError("Expected exact prepared mono 22050Hz PCM16")
        if any(value["recording"]["sample_rate_hz"] != rate or abs(value["recording"]["duration_seconds"] - duration) > 1/rate for value in (reference, first, second)):
            raise ValueError("Reference/prediction does not share the exact prepared timeline")
        jobs.append((row, reference, first, second))
    return suite, output, selected, sources, jobs


def markdown_report(report):
    group = report["aggregate"]
    lines = ["# Cached synthetic native-timing review controls", "", "Retrospective procedural diagnostics; no extraction, model inference, retuning or accepted arrangements.", "",
             "Reference tolerance is fixed at 150 ms. Typed matches require the same directed core transition. Untyped matches use only timestamps. All includes N/X/unsupported edges; harmonic requires supported chords on both sides. Alternate power-chord acceptable-label sets are not applied to directed core matching; unsupported duration is retained in JSON.", "",
             "| Model / target | Matches / reference | Emitted | F1 | Extra / missed |", "|---|---:|---:|---:|---:|"]
    for model, values in group["reference_metrics"].items():
        for kind, value in values.items():
            f1 = f"{value['f1']:.3f}" if value["f1"] is not None else "—"
            lines.append(f"| {model} / {kind} | {value['matched_transitions']} / {value['reference_transitions']} | {value['predicted_transitions']} | {f1} | {value['extra_native_points']} / {value['missed_reference_transitions']} |")
    lines += ["", "| Review windows | Count | Union seconds / audio | Primary error-or-extra points covered | Operational misses covered | Direct primary flags correct at 150ms |", "|---|---:|---:|---:|---:|---:|"]
    for kind, value in group["window_assessment"].items():
        errors, misses, flags = value["primary_errors_or_extras"], value["primary_operational_missed_reference_transitions"], value["direct_flags"]["primary"]
        lines.append(f"| {kind} | {value['window_count']} | {value['union_window_seconds']:.3f} / {value['audio_seconds']:.3f} | {errors['covered']} / {errors['denominator']} | {misses['covered']} / {misses['denominator']} | {flags['reference_correct_flagged_native_points']} / {flags['direct_flagged_native_points']} |")
    lines += ["", "Operational misses are strict reference misses left after associating remaining compatible native points within 500 ms. That association is bookkeeping, not a relaxed passing tolerance. Wrong-direction points remain extra/missing even at an exact timestamp.", "",
              "False-positive flags above are directly flagged native points supported by the reference at 150 ms. Correct points incidentally covered by replay padding are reported separately in JSON. A replay can still be useful for context.", "",
              "Both models shifted +300 ms still pair perfectly and create no priorities while every 150 ms reference match fails. All symbolic expected behaviors: **" + str(report["symbolic_controls"]["all_expected_behaviors_passed"]) + "**.", "",
              "Agreement cannot reveal shared errors. Cached synthetic outputs are historical, and these results are not a fresh selected-workflow or popular-recording accuracy estimate. No policy was retuned. Per-case transitions, matches, error partitions, windows, provenance and all source hashes are retained beside this report."]
    return "\n".join(lines) + "\n"


def run(suite, spec_path, output):
    suite, output, selected, sources, jobs = preflight(suite, spec_path, output)
    started = time.perf_counter()
    snapshot = {str(path): value for path, value in sorted(sources.items(), key=lambda item: str(item[0]))}
    # Policy/source snapshot is fixed before any per-case diagnostic is computed.
    frozen = {"schema_version": SCHEMA, "control_policy": POLICY, "native_review_policy": timing.POLICY,
              "source_sha256": snapshot, "frozen_before": "native review generation and reference scoring"}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".timing-controls-", dir=output.parent))
    try:
        drafts.write_json(staging / "source-snapshot.json", frozen)
        rows, compact = [], []
        model_charts = {"btc": [], "crema": []}
        (staging / "cases").mkdir()
        for entry, reference, first, second in jobs:
            row = evaluate_case(reference, first, second)
            row.update(id=entry["id"], condition=entry["condition"], split=entry["split"], level=entry["level"])
            rows.append(row)
            relative = "cases/" + entry["id"] + ".json"
            drafts.write_json(staging / relative, row)
            compact.append({"id": entry["id"], "condition": entry["condition"], "split": entry["split"], "path": relative, "sha256": digest(staging / relative)})
            model_charts["btc"].append(first); model_charts["crema"].append(second)
        symbolic = symbolic_controls()
        if not symbolic["all_expected_behaviors_passed"]: raise ValueError("A symbolic negative control failed")
        drafts.write_json(staging / "symbolic-controls.json", symbolic)
        if any(not path.is_file() or digest(path) != expected for path, expected in sources.items()):
            raise ValueError("A source/spec/module changed during cached control evaluation")
        report = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "status": "retrospective cached synthetic native-timing REVIEW diagnostics", "gold": False,
                  "policy": POLICY, "native_review_policy": timing.POLICY, "suite": str(suite.relative_to(ROOT)),
                  "source_snapshot_sha256": digest(staging / "source-snapshot.json"), "runtime_seconds": time.perf_counter() - started,
                  "source_files_modified": False, "extraction_or_inference_run": False,
                  "accepted_arrangements": 0, "real_recording_accuracy": None, "selected_pipeline_score": False,
                  "aggregate": aggregate(rows),
                  "by_split": {split: aggregate([row for row in rows if row["split"] == split]) for split in sorted({row["split"] for row in rows})},
                  "by_condition": {condition: aggregate([row for row in rows if row["condition"] == condition]) for condition in sorted({row["condition"] for row in rows})},
                  "cached_output_provenance": provenance(model_charts, selected),
                  "symbolic_controls": {"path": "symbolic-controls.json", "sha256": digest(staging / "symbolic-controls.json"), "assertions": symbolic["assertions"], "all_expected_behaviors_passed": symbolic["all_expected_behaviors_passed"]},
                  "cases": compact,
                  "limits": ["Procedural reference events are known synthetic boundaries, not real-guitar or commercial-recording truth.",
                             "Typed scores include direction/core quality; untyped time proximity can credit a wrong label or silence edge.",
                             "Primary operational misses may include mislabelled transitions; no physical cause is inferred.",
                             "Replay windows are generated without references; coverage is measured afterward, with time budgets and direct false-positive flags kept separate.",
                             "The existing selected12 ordering is evaluated unchanged; no reference-derived reranking or retuning.",
                             "Cached earlier outputs and previously exposed procedural splits are retrospective diagnostics, not fresh selected-pipeline validation."]}
        drafts.write_json(staging / "report.json", report)
        (staging / "report.md").write_text(markdown_report(report))
        # Refuse a destination created while analysis was running.
        if output.exists() or output.is_symlink(): raise ValueError("Output appeared during evaluation")
        staging.rename(output)
        return report
    except Exception:
        shutil.rmtree(staging)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.suite, args.spec, args.output)
    print(json.dumps({"cases": len(result["cases"]), "symbolic_controls_passed": result["symbolic_controls"]["all_expected_behaviors_passed"], "runtime_seconds": result["runtime_seconds"], "output": str(args.output)}))
