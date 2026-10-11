"""Develop and freeze a chart-acceptance policy, then evaluate without retuning.

The bounded development sweep consumes only the old suite's screen split. A
separate validation command verifies the frozen configuration and module hashes
before inferring or scoring historical holdout/fresh cases. Labels and order are
supplied; timing scores are conditional, not recognition accuracy. Raw model
inference never occurs here. Frozen old outputs and cached NNLS are unchanged.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import shutil
import tempfile
import time

import numpy as np

import alignment_comparison
import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import lab
import rich_quality_screen
import rich_quality_suite

SCHEMA = "chart-acceptance-screen-1.0"
FREEZE_SCHEMA = "chart-acceptance-freeze-1.0"
BACKENDS = ("spectral", "nnls-chroma")
# Declared before observing any development outcomes. No threshold is derived
# from Wonderwall: there is no independent timed/quality reference for it.
GUARD_COMMON = copy.deepcopy(alignment_comparison.DEFAULTS)
OPTIONS = (
    {"id": "lenient", "quality_margin": .12, "added_tone_ratio": .08, "added_tone_fraction": .35},
    {"id": "balanced", "quality_margin": .08, "added_tone_ratio": .12, "added_tone_fraction": .50},
    {"id": "strict", "quality_margin": .04, "added_tone_ratio": .20, "added_tone_fraction": .65},
    {"id": "very-strict", "quality_margin": .02, "added_tone_ratio": .28, "added_tone_fraction": .75},
)
SELECTION_RULE = (
    "Require all requested development runs to succeed and mean correct-chart "
    "semantic chord-quality loss versus frozen old correct charts <=10 percentage "
    "points for each acoustic backend separately. Among eligible options minimize "
    "corrupt retained wrong-label seconds, then maximize correct coverage, then "
    "prefer declared option order. If none qualifies, report no acceptable policy; "
    "freeze the all-success option with least maximum per-backend quality loss "
    "solely for diagnostic validation, without relaxing the eligibility constraint. "
    "No validation tuning or Wonderwall calibration."
)
ERRORS = (ValueError, OSError, KeyError, TypeError, IndexError, json.JSONDecodeError)


def guarded_module():
    import guarded_aligner
    return guarded_aligner


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hashes() -> dict:
    return {"runner": sha(Path(__file__)), "guarded_aligner": sha(Path(guarded_module().__file__)),
        "old_aligner": sha(Path(chart_aligner.__file__)), "fixture_scorer": sha(Path(rich_quality_suite.__file__)),
        "nnls_adapter": sha(Path(nnls_chroma_adapter.__file__))}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_manifest(suite: Path, *, split: str | None) -> tuple[dict, list[dict]]:
    suite = suite.resolve(strict=True)
    manifest = json.loads((suite / "manifest.json").read_text())
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Suite requires nonempty cases")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or any(not isinstance(value, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,127}", value) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("Unsafe or colliding case identifiers")
    selected = [case for case in cases if split is None or case.get("split") == split]
    if not selected:
        raise ValueError(f"Suite has no cases for requested split {split}")
    for case in selected:
        for key in ("audio", "reference", "untimed"):
            value = case.get(key)
            if not isinstance(value, str):
                raise ValueError(f"Case {case['id']} requires {key}")
            path = (suite / value).resolve()
            if not path.is_relative_to(suite) or not path.is_file():
                raise ValueError("Inputs must be regular files inside the suite")
            declared = case.get(key + "_sha256")
            if declared is not None and declared != sha(path):
                raise ValueError(f"Case {case['id']} {key} hash mismatch")
        chart = json.loads((suite / case["untimed"]).read_text())
        chart_aligner.validate_untimed_chart(chart)
        if chart["recording"]["id"] != case["id"] or chart["recording"].get("audio_sha256") != sha(suite / case["audio"]):
            raise ValueError("Untimed chart identity/audio hash mismatch")
    return manifest, selected


def validate_output(output: Path, sources: list[Path]) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError("Output exists; choose a fresh directory (no overwrite)")
    for source in sources:
        if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(output.resolve()):
            raise ValueError("Output must be separate from source inputs")


@contextmanager
def cached_spectral_features(signal: np.ndarray, rate: int):
    """Reuse byte-identical PCM arrays across old/new calls; serial only."""
    original = chart_aligner.features
    features = original(signal, rate, GUARD_COMMON["hop_seconds"], GUARD_COMMON["window_seconds"])
    for value in features.values():
        if isinstance(value, np.ndarray):
            value.flags.writeable = False
    digest = alignment_comparison.array_digest(features)

    def cached(actual, sample_rate, hop_seconds, window_seconds):
        if sample_rate != rate or hop_seconds != GUARD_COMMON["hop_seconds"] or window_seconds != GUARD_COMMON["window_seconds"] or not np.array_equal(actual, signal):
            raise ValueError("Attempt to reuse spectral cache for different audio/grid")
        return dict(features)

    chart_aligner.features = cached
    try:
        yield digest
    finally:
        chart_aligner.features = original


def proposed_chart(prediction: dict) -> dict:
    events = prediction.get("alignment_evidence", {}).get("proposed_path_events_before_gap_mask")
    if not isinstance(events, list) or not events:
        raise ValueError("Aligner must preserve a nonempty proposed path before masking")
    proposed = copy.deepcopy(prediction)
    proposed["chords"] = copy.deepcopy(events)
    lab.validate_chart(proposed)
    return proposed


def label_same(expected: str, actual: str) -> bool:
    first, second = rich_quality_suite.chord_semantics(expected), rich_quality_suite.chord_semantics(actual)
    return first["status"] == second["status"] == "chord" and (first["root"], first["quality"]) == (second["root"], second["quality"])


def discard_metrics(reference: dict, raw: dict, accepted: dict) -> dict:
    """Measure correct raw labels removed, not merely total X coverage."""
    lab.validate_chart(raw)
    lab.validate_chart(accepted)
    correct_raw = discarded = unknown = false_n = 0.0
    for expected in reference["chords"]:
        if rich_quality_suite.chord_semantics(expected["label"])["status"] != "chord":
            continue
        for original in raw["chords"]:
            if not label_same(expected["label"], original["label"]):
                continue
            start = max(expected["start_seconds"], original["start_seconds"])
            end = min(expected["end_seconds"], original["end_seconds"])
            if end <= start:
                continue
            correct_raw += end - start
            for final in accepted["chords"]:
                overlap = max(0, min(end, final["end_seconds"]) - max(start, final["start_seconds"]))
                if not overlap or label_same(expected["label"], final["label"]):
                    continue
                discarded += overlap
                unknown += overlap * (final["label"] == "X")
                false_n += overlap * (final["label"] == "N")
    return {"raw_true_correct_label_seconds": correct_raw,
        "true_correct_labels_discarded_seconds": discarded,
        "true_correct_labels_discarded_fraction": discarded / correct_raw if correct_raw else 0.0,
        "true_correct_labels_discarded_to_X_seconds": unknown,
        "true_correct_labels_discarded_to_N_seconds": false_n}


def progress_metrics(prediction: dict) -> dict:
    evidence = prediction.get("alignment_evidence", {})
    columns = evidence.get("frame_columns", [])
    frames = evidence.get("frames", [])
    silent_advances = None
    if "sequence_index" in columns and "silent" in columns and frames:
        position, silent = columns.index("sequence_index"), columns.index("silent")
        silent_advances = sum(second[position] != first[position] and second[silent]
            for first, second in zip(frames, frames[1:]))
    proposed = evidence.get("proposed_path_events_before_gap_mask", [])
    empty_positions = [event.get("sequence_index") for event in proposed
        if event.get("evidence", {}).get("active_frames") == 0 and event.get("label") not in ("N", "X")]
    diagnostics = evidence.get("diagnostics", {})
    return {"silent_frame_position_transitions": silent_advances,
        "no_active_harmonic_evidence_proposed_event_count": len(empty_positions),
        "unvisited_supplied_position_count": len(diagnostics.get("unvisited_sequence_indices", [])),
        "path_transitions": diagnostics.get("path_transitions"),
        "guard_rejected_event_count": diagnostics.get("rejected_event_count"),
        "guard_silent_advance_count": diagnostics.get("silent_position_advance_count")}


METRIC_KEYS = ("duration_seconds", "chord_reference_seconds", "exact_chord_quality_correct_seconds",
    "semantic_chord_quality_agreement", "root_chord_agreement", "major_minor_chord_agreement",
    "major_minor_chord_reference_coverage", "plain_triad_false_extension_seconds",
    "plain_triad_false_extension_fraction", "no_chord_recall", "false_no_chord_on_chord_seconds",
    "unknown_on_chord_seconds", "boundary_f1_150ms", "matched_boundary_mean_error_seconds",
    "reference_boundaries", "predicted_boundaries", "matched_boundaries", "missed_reference_boundaries",
    "extra_predicted_boundaries", "unknown_duration_seconds", "unknown_fraction",
    "reference_no_chord_duration_covered_fraction", "false_no_chord_duration_on_annotated_harmony_seconds")
RAW_METRIC_KEYS = ("chord_reference_seconds", "exact_chord_quality_correct_seconds",
    "semantic_chord_quality_agreement", "root_chord_agreement", "boundary_f1_150ms",
    "matched_boundary_mean_error_seconds", "matched_boundaries", "missed_reference_boundaries", "extra_predicted_boundaries")
DIAGNOSTIC_KEYS = ("acoustic_fit_status", "active_frames", "active_mismatch_fraction", "unvisited_sequence_indices",
    "path_transitions", "endpoint_reached", "partial", "rejected_quality_frames", "rejected_quality_seconds",
    "retained_harmonic_seconds", "supplied_positions_without_minimum_evidence_count", "no_active_evidence_position_count",
    "silent_position_advance_count", "accepted_for_playback", "arrangement_verified")


def score_prediction(reference: dict, prediction: dict, *, plain_control: bool) -> dict:
    raw = proposed_chart(prediction)
    accepted_metrics = {**rich_quality_suite.score(reference, prediction, triad_control=plain_control),
        **alignment_screen.boundary_metrics(reference, prediction)}
    raw_metrics = {**rich_quality_suite.score(reference, raw, triad_control=plain_control),
        **alignment_screen.boundary_metrics(reference, raw)}
    return {"metrics": {key: accepted_metrics[key] for key in METRIC_KEYS},
        "raw_metrics": {key: raw_metrics[key] for key in RAW_METRIC_KEYS},
        "residual_errors": rich_quality_screen.retained_error_metrics(reference, prediction),
        "raw_errors": rich_quality_screen.retained_error_metrics(reference, raw),
        "discard": discard_metrics(reference, raw, prediction), "progress": progress_metrics(prediction)}


def aggregate(rows: list[dict]) -> dict:
    good = [row for row in rows if row["status"] == "ok"]
    result = {"requested_cases": len(rows), "successful_cases": len(good), "failed_cases": len(rows) - len(good)}
    for group in ("metrics", "raw_metrics", "residual_errors", "raw_errors", "discard", "progress"):
        names = set().union(*(row.get(group, {}) for row in good)) if good else set()
        measurements = {}
        for name in sorted(names):
            values = [row[group][name] for row in good if isinstance(row.get(group, {}).get(name), (int, float))
                and not isinstance(row[group][name], bool) and math.isfinite(row[group][name])]
            if not values:
                continue
            additive = (name.endswith("_seconds") and name not in (
                "boundary_tolerance_seconds", "matched_boundary_mean_error_seconds", "matched_no_chord_boundary_mean_error_seconds"))
            additive |= name.endswith("_boundaries") or name.endswith("_count") or name in ("path_transitions", "silent_frame_position_transitions")
            measurements[name] = sum(values) if additive else sum(values) / len(values)
        result[group] = measurements
    harmonic = result.get("metrics", {}).get("chord_reference_seconds", 0)
    result["duration_weighted_correct_harmonic_fraction"] = result.get("metrics", {}).get("exact_chord_quality_correct_seconds", 0) / harmonic if harmonic else None
    result["duration_weighted_accepted_harmonic_fraction"] = (harmonic - result.get("metrics", {}).get("unknown_on_chord_seconds", 0)
        - result.get("metrics", {}).get("false_no_chord_on_chord_seconds", 0)) / harmonic if harmonic else None
    result["duration_weighted_wrong_label_fraction"] = result.get("residual_errors", {}).get("retained_erroneous_label_seconds", 0) / harmonic if harmonic else None
    raw_correct = result.get("discard", {}).get("raw_true_correct_label_seconds", 0)
    result["duration_weighted_raw_correct_discard_fraction"] = result.get("discard", {}).get("true_correct_labels_discarded_seconds", 0) / raw_correct if raw_correct else 0
    result["wrong_chart_cases_with_wrong_labels_surviving"] = sum(row.get("control") != "correct" and row.get("residual_errors", {}).get("retained_erroneous_label_seconds", 0) > 1e-9 for row in good)
    return result


def summarize(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        prefix = f"{row['policy']}/{row['backend']}/{row['control']}"
        for suffix in ("all", f"dataset/{row['dataset']}", f"family/{row['family']}", f"condition/{row['condition']}"):
            groups[f"{prefix}/{suffix}"].append(row)
    return {key: aggregate(values) for key, values in sorted(groups.items())}


def option_summary(rows: list[dict], options: tuple | list = OPTIONS) -> list[dict]:
    result = []
    for option in options:
        selected = [row for row in rows if row["policy"] == option["id"]]
        correct = aggregate([row for row in selected if row["control"] == "correct"])
        corrupt = aggregate([row for row in selected if row["control"] != "correct"])
        success = bool(selected) and all(row["status"] == "ok" for row in selected)
        backend_losses = {}
        for backend in BACKENDS:
            baseline = aggregate([row for row in rows if row["policy"] == "old-frozen" and row["control"] == "correct" and row["backend"] == backend])
            guarded = aggregate([row for row in selected if row["control"] == "correct" and row["backend"] == backend])
            first = baseline.get("metrics", {}).get("semantic_chord_quality_agreement")
            second = guarded.get("metrics", {}).get("semantic_chord_quality_agreement")
            backend_losses[backend] = first - second if first is not None and second is not None else None
        baseline_complete = all(row["status"] == "ok" for row in rows if row["policy"] == "old-frozen")
        eligible = success and baseline_complete and all(value is not None and value <= .10 + 1e-12 for value in backend_losses.values())
        result.append({"id": option["id"], "parameters": {**GUARD_COMMON, **{key: value for key, value in option.items() if key != "id"}},
            "correct_charts": correct, "corrupt_charts": corrupt, "all_runs_successful": success,
            "per_backend_semantic_quality_loss": backend_losses,
            "maximum_semantic_quality_loss": max((value for value in backend_losses.values() if value is not None), default=None),
            "eligible_quality_loss": eligible})
    return result


def select_option(options: list[dict]) -> tuple[dict, str]:
    available = [(index, option) for index, option in enumerate(options) if option["all_runs_successful"]]
    if not available:
        raise ValueError("No all-success development policy; cannot freeze configuration")
    eligible = [(index, option) for index, option in available if option["eligible_quality_loss"]]
    if eligible:
        selected = min(eligible, key=lambda pair: (pair[1]["corrupt_charts"]["residual_errors"]["retained_erroneous_label_seconds"],
            -pair[1]["correct_charts"]["duration_weighted_correct_harmonic_fraction"], pair[0]))[1]
        return selected, "development per-backend quality-loss gate met"
    selected = min(available, key=lambda pair: (pair[1]["maximum_semantic_quality_loss"] if pair[1]["maximum_semantic_quality_loss"] is not None else float("inf"), pair[0]))[1]
    return selected, "no acceptable development policy; least-loss option frozen only for diagnostic validation"


def case_controls(suite: Path, case: dict, untimed: dict, family: str) -> dict:
    base = copy.deepcopy(untimed)
    if untimed["schema_version"] == chart_aligner.SECTION_SCHEMA:
        sequence, _ = chart_aligner.expand_sections(untimed)
        base = {key: value for key, value in base.items() if key not in ("sections", "order")}
        base.update(schema_version=chart_aligner.SCHEMA, sequence=sequence)
    controls = rich_quality_screen.control_charts(base, family)
    controls["correct"] = copy.deepcopy(untimed)
    controls["correct"].setdefault("metadata", {})["screen_control"] = "correct"
    for name, entry in case.get("untimed_controls", {}).items():
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", name) or name in controls or not isinstance(entry, dict):
            raise ValueError("Unsafe or colliding fixture control")
        path = (suite / entry["path"]).resolve()
        if not path.is_relative_to(suite.resolve()) or not path.is_file() or entry.get("sha256") != sha(path):
            raise ValueError("Fixture control path/hash mismatch")
        chart = json.loads(path.read_text())
        chart_aligner.validate_untimed_chart(chart)
        if chart["recording"] != untimed["recording"]:
            raise ValueError("Fixture control recording identity mismatch")
        controls[name] = chart
    return controls


def infer_dataset(suite: Path, cache: Path, stage: Path, *, dataset: str, split: str | None,
                  options: tuple | list, old_cached: bool) -> tuple[list[dict], dict]:
    """Finish all inference before loading this dataset's reference charts."""
    manifest, cases = source_manifest(suite, split=split)
    pending, inputs = [], []
    for index, case in enumerate(cases, 1):
        identifier = case["id"]
        audio = (suite / case["audio"]).resolve()
        untimed = json.loads((suite / case["untimed"]).read_text())
        family = case.get("recipe", {}).get("family", case.get("family", "unspecified"))
        charts = case_controls(suite, case, untimed, family)
        evidence_path = (cache / "cases" / identifier / "nnls-evidence.json").resolve()
        evidence_error, evidence_hash = None, None
        try:
            packet = json.loads(evidence_path.read_text())
            nnls_chroma_adapter.validate_evidence(packet, audio)
            if packet["recording"]["id"] != identifier:
                raise ValueError("NNLS evidence case identity mismatch")
            evidence_hash = sha(evidence_path)
        except ERRORS as error:
            evidence_error = str(error)
        base = {"case_id": identifier, "dataset": dataset, "split": case.get("split"),
            "family": family, "condition": case.get("condition", "unspecified"),
            "audio_sha256": sha(audio), "untimed_sha256": sha(suite / case["untimed"]),
            "reference_sha256": sha(suite / case["reference"]), "nnls_evidence_sha256": evidence_hash}
        inputs.append(copy.deepcopy(base))
        directory = stage / "cases" / dataset / identifier
        directory.mkdir(parents=True, exist_ok=True)
        signal, rate = lab.read_wav(audio)
        with cached_spectral_features(signal, rate) as feature_hash:
            for control, chart in charts.items():
                chart_path = directory / f"{control}-untimed.json"
                chart_aligner.write_json_safely(chart_path, chart, [audio, evidence_path])
                for backend in BACKENDS:
                    for option in ({"id": "old-frozen"}, *options):
                        row = {**base, "backend": backend, "control": control, "policy": option["id"],
                            "status": "error", "chart_sha256": sha(chart_path), "spectral_feature_arrays_sha256": feature_hash}
                        try:
                            if backend == "nnls-chroma" and evidence_error:
                                raise ValueError(f"Cached NNLS unavailable: {evidence_error}")
                            kwargs = {"evidence_json": evidence_path} if backend == "nnls-chroma" else {}
                            start = time.perf_counter()
                            if option["id"] == "old-frozen" and old_cached:
                                old_chart = cache / "cases" / identifier / f"{control}-untimed.json"
                                if json.loads(old_chart.read_text()) != chart:
                                    raise ValueError("Frozen old untimed input differs from declared control")
                                old_path = cache / "cases" / identifier / f"{control}-{backend}.json"
                                prediction = lab.load_chart(old_path)
                                if prediction.get("alignment_input", {}).get("chart_sha256") != sha(old_chart):
                                    raise ValueError("Old prediction untimed input hash mismatch")
                                if backend == "nnls-chroma" and prediction.get("alignment_evidence", {}).get("acoustic_input", {}).get("evidence_sha256") != evidence_hash:
                                    raise ValueError("Old prediction NNLS evidence hash mismatch")
                                old_parameters = prediction.get("analysis", {}).get("parameters", {})
                                if any(old_parameters.get(key) != alignment_comparison.DEFAULTS[key] for key in ("min_chord_seconds", "transition_penalty", "unknown_score", "mismatch_margin")):
                                    raise ValueError("Old cached decoder parameters differ from frozen baseline")
                                row["old_cached_output_sha256"] = sha(old_path)
                                row["old_cached_source"] = str(old_path)
                            elif option["id"] == "old-frozen":
                                prediction = chart_aligner.align(audio, chart_path, **alignment_comparison.DEFAULTS, **kwargs)
                            else:
                                parameters = {**GUARD_COMMON, **{key: value for key, value in option.items() if key != "id"}}
                                prediction = guarded_module().align(audio, chart_path, **parameters, **kwargs)
                            rich_quality_screen.validate_prediction(prediction, identifier, audio)
                            output = directory / f"{control}-{backend}-{option['id']}.json"
                            if option["id"] == "old-frozen" and old_cached:
                                shutil.copyfile(old_path, output)
                            else:
                                chart_aligner.write_json_safely(output, prediction, [audio, evidence_path, chart_path])
                            row.update(status="inferred", output=str(output.relative_to(stage)), output_sha256=sha(output),
                                runtime_seconds=time.perf_counter() - start,
                                diagnostics={key: value for key, value in prediction.get("alignment_evidence", {}).get("diagnostics", {}).items() if key in DIAGNOSTIC_KEYS})
                            pending.append((case, row, prediction))
                        except ERRORS as error:
                            row["reason"] = str(error)
                            pending.append((case, row, None))
        print(f"Inferred {dataset} {index}/{len(cases)}: {identifier}", flush=True)
    rows = []
    for case, row, prediction in pending:
        if prediction is not None:
            try:
                reference = lab.load_chart(suite / case["reference"])
                rich_quality_screen.validate_prediction(reference, case["id"], suite / case["audio"])
                row.update(score_prediction(reference, prediction, plain_control=row["family"] == "plain_control"), status="ok")
            except ERRORS as error:
                row.update(status="error", reason=f"Scoring failed: {error}")
        rows.append(row)
    return rows, {"name": dataset, "suite_version": manifest.get("suite_version"),
        "manifest_sha256": sha(suite / "manifest.json"), "selected_split": split,
        "case_ids": [case["id"] for case in cases], "input_hashes": inputs,
        "cached_evidence_root": str(cache), "old_outputs_reused_byte_identically": old_cached}


def report_base(rows: list[dict], datasets: list[dict]) -> dict:
    return {"schema_version": SCHEMA, "created_at_utc": utc_now(), "rows": rows,
        "datasets": datasets, "summary": summarize(rows), "requested_attempts": len(rows),
        "successful_attempts": sum(row["status"] == "ok" for row in rows),
        "failed_attempts": sum(row["status"] != "ok" for row in rows),
        "implementation_sha256": implementation_hashes(),
        "old_decoder_parameters": alignment_comparison.DEFAULTS,
        "cached_feature_policy": "One spectral extraction per case; immutable same arrays shared by old/new calls. Existing frozen old outputs retain original bytes. Hash-paired native NNLS packets reused without extraction/model inference.",
        "reference_timestamps_used_during_inference": False,
        "metric_definition": "Duration-weighted exact quality/root scores retain extensions and suspensions, exclude slash-bass from quality and report N/X separately. Correct-chart timing is conditional on supplied labels/order/count. Boundary F1 uses ordered one-to-one 150ms matching including N/X gaps; matched timing error excludes missed/extra boundaries. Correct raw labels discarded are computed by three-way interval overlap. Group rates are successful-case means except explicitly duration_weighted values; seconds/counts are additive. Failures remain requested denominators.",
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "limitations": ["No independent full-song/Wonderwall quality or timing gold is available; Wonderwall is not calibration data.",
            "Historical holdout outcomes were reported in the prior screen, so it is not a pristine blind holdout. This runner never uses its outcomes to select thresholds.",
            "Fresh procedural cases may share synthesis/scoring conventions; success does not establish real guitar or catalogue accuracy.",
            "Supplying labels and order makes this acceptance/conditional alignment evaluation, not chord recognition.",
            "Rejection can reduce wrong labels by discarding correct labels; report both accepted coverage and true-correct-label loss.",
            "Cosine/added-note scores are uncalibrated acoustic evidence, not probabilities. Native NNLS windows limit physical boundary precision."],
        "gates": {"all_requested_inference_and_scoring_complete": all(row["status"] == "ok" for row in rows),
            "production_accuracy_or_readiness_established": False}}


def declare(output: Path, fresh_manifest_sha256: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", fresh_manifest_sha256):
        raise ValueError("Fresh validation manifest requires SHA256")
    value = {"schema_version": "chart-acceptance-declaration-1.0", "declared_at_utc": utc_now(),
        "options": OPTIONS, "common_parameters": GUARD_COMMON, "selection_rule": SELECTION_RULE,
        "development_split": "screen", "fresh_manifest_sha256": fresh_manifest_sha256,
        "implementation_sha256": implementation_hashes(), "development_outcomes_consumed": False}
    chart_aligner.write_json_safely(output, value, [])
    return value


def load_declaration(path: Path, required_sha256: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", required_sha256) or sha(path) != required_sha256:
        raise ValueError("Declaration SHA mismatch")
    value = json.loads(path.read_text())
    if value.get("schema_version") != "chart-acceptance-declaration-1.0" or value.get("development_outcomes_consumed") is not False:
        raise ValueError("Invalid pre-development declaration")
    if value.get("options") != list(OPTIONS) or value.get("common_parameters") != GUARD_COMMON or value.get("selection_rule") != SELECTION_RULE or value.get("implementation_sha256") != implementation_hashes():
        raise ValueError("Declared grid/rule/implementations changed before development")
    return value


def develop(suite: Path, cached: Path, output: Path, declaration_path: Path, declaration_sha256: str) -> dict:
    suite, cached, output = suite.resolve(strict=True), cached.resolve(strict=True), output.absolute()
    validate_output(output, [suite, cached, declaration_path])
    declaration = load_declaration(declaration_path, declaration_sha256)
    source_manifest(suite, split="screen")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        shutil.copyfile(declaration_path, stage / "declared-sweep.json")
        rows, dataset = infer_dataset(suite, cached, stage, dataset="development", split="screen", options=OPTIONS, old_cached=True)
        report = report_base(rows, [dataset])
        summaries = option_summary(rows)
        selected, reason = select_option(summaries)
        report.update(stage="development", selection_rule=SELECTION_RULE, options=summaries,
            selected_policy=selected["id"], selection_reason=reason,
            acceptable_development_policy=selected["eligible_quality_loss"],
            validation_outcomes_consumed=False, declared_sweep_sha256=sha(stage / "declared-sweep.json"))
        lab.write_json(stage / "development-report.json", report)
        frozen = {"schema_version": FREEZE_SCHEMA, "frozen_at_utc": utc_now(), "selected_policy": selected["id"],
            "parameters": selected["parameters"], "selection_rule": SELECTION_RULE, "selection_reason": reason,
            "acceptable_development_policy": selected["eligible_quality_loss"],
            "development_report_sha256": sha(stage / "development-report.json"),
            "declared_sweep_sha256": sha(stage / "declared-sweep.json"),
            "development_datasets": [dataset], "implementation_sha256": implementation_hashes(),
            "validation_outcomes_consumed_before_freeze": False,
            "fresh_manifest_sha256": declaration["fresh_manifest_sha256"]}
        lab.write_json(stage / "frozen-policy.json", frozen)
        report["frozen_policy_sha256"] = sha(stage / "frozen-policy.json")
        # report.json adds freeze provenance; development-report.json is the
        # non-circular, immutable scored artifact whose hash is frozen above.
        lab.write_json(stage / "report.json", report)
        (stage / "report.md").write_text(markdown_report(report))
        rich_quality_screen.publish_directory_exclusively(stage, output)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def load_frozen(path: Path, expected_sha256: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or sha(path) != expected_sha256:
        raise ValueError("Frozen policy SHA differs from required pre-validation hash")
    frozen = json.loads(path.read_text())
    if frozen.get("schema_version") != FREEZE_SCHEMA or frozen.get("validation_outcomes_consumed_before_freeze") is not False:
        raise ValueError("Missing valid pre-validation freeze record")
    if frozen.get("implementation_sha256") != implementation_hashes():
        raise ValueError("Implementations differ from frozen configuration; do not silently retune")
    if frozen.get("selection_rule") != SELECTION_RULE:
        raise ValueError("Frozen selection rule mismatch")
    parameters = frozen.get("parameters", {})
    declared = [{**GUARD_COMMON, **{key: value for key, value in option.items() if key != "id"}} for option in OPTIONS]
    if parameters not in declared:
        raise ValueError("Frozen policy was not one of the declared development options")
    return frozen


def validate(frozen_path: Path, required_sha256: str, historical_suite: Path, historical_cache: Path,
             fresh_suite: Path, fresh_cache: Path, output: Path) -> dict:
    output = output.absolute()
    sources = [historical_suite, historical_cache, fresh_suite, fresh_cache, frozen_path]
    validate_output(output, sources)
    # Verify the frozen bytes/modules before reading validation manifests or
    # outcomes. The CLI forces the caller to record/pass the prior-stage SHA.
    frozen = load_frozen(frozen_path, required_sha256)
    policy = {"id": frozen["selected_policy"], **{key: value for key, value in frozen["parameters"].items() if key not in GUARD_COMMON}}
    source_manifest(historical_suite, split="holdout")
    if sha(fresh_suite / "manifest.json") != frozen["fresh_manifest_sha256"]:
        raise ValueError("Fresh validation manifest differs from pre-development declaration")
    source_manifest(fresh_suite, split=None)
    historical_ids = set(frozen["development_datasets"][0]["case_ids"])
    _, fresh_cases = source_manifest(fresh_suite, split=None)
    if historical_ids.intersection(case["id"] for case in fresh_cases):
        raise ValueError("Fresh validation case IDs overlap development")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        shutil.copyfile(frozen_path, stage / "frozen-policy.json")
        # Record the frozen provenance before any validation inference or score.
        lab.write_json(stage / "validation-start.json", {"started_at_utc": utc_now(),
            "frozen_policy_sha256": required_sha256, "parameters": frozen["parameters"], "retuning_allowed": False})
        historical_rows, historical = infer_dataset(historical_suite, historical_cache, stage,
            dataset="historical-holdout", split="holdout", options=[policy], old_cached=True)
        fresh_rows, fresh = infer_dataset(fresh_suite, fresh_cache, stage,
            dataset="fresh-validation", split=None, options=[policy], old_cached=False)
        rows = historical_rows + fresh_rows
        report = report_base(rows, [historical, fresh])
        report.update(stage="validation", selected_policy=policy["id"], frozen_policy_sha256=required_sha256,
            frozen_at_utc=frozen["frozen_at_utc"], frozen_parameters=frozen["parameters"],
            acceptable_development_policy=frozen["acceptable_development_policy"],
            development_datasets=frozen["development_datasets"], selection_rule=SELECTION_RULE,
            retuned_after_validation=False, validation_start_sha256=sha(stage / "validation-start.json"))
        new_controls = [row for row in rows if row["policy"] != "old-frozen" and row["control"] != "correct"]
        report["gates"]["all_corrupt_chart_wrong_labels_removed"] = rich_quality_screen.corrupt_charts_rejected(new_controls)
        new_rows = [row for row in rows if row["policy"] != "old-frozen"]
        report["gates"]["no_silent_harmonic_position_progress"] = bool(new_rows) and all(row["status"] == "ok" and row.get("progress", {}).get("silent_frame_position_transitions") == 0 for row in new_rows)
        lab.write_json(stage / "report.json", report)
        (stage / "report.md").write_text(markdown_report(report))
        rich_quality_screen.publish_directory_exclusively(stage, output)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def percentage(value) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "—"


def markdown_report(report: dict) -> str:
    lines = ["# Chart acceptance evaluation", "", f"Stage: **{report['stage']}**. {report['successful_attempts']} / {report['requested_attempts']} attempts succeeded; {report['failed_attempts']} failed.", "",
        "Correct-chart results measure conditional timing with supplied labels/order/count. Corrupt charts test retained wrong labels. Guarding is not assumed safe because it runs successfully.", "",
        f"Frozen policy: `{report.get('selected_policy')}`; SHA-256 `{report.get('frozen_policy_sha256')}`.", "", "## Split and freeze record", "",
        report["selection_rule"], ""]
    for dataset in report["datasets"]:
        lines.append(f"- {dataset['name']}: {len(dataset['case_ids'])} cases; manifest `{dataset['manifest_sha256']}`; consumed split `{dataset['selected_split'] or 'all fresh cases'}`.")
    if report["stage"] == "development":
        lines.extend(["", "The following declared variants all ran on development only. No validation result was used before freezing.", "",
            "| Option | All successful | Correct harmony retained correctly | Correct raw labels discarded | Corrupt wrong labels retained | Spectral / NNLS quality loss | Eligible ≤10pp loss each |", "|---|---:|---:|---:|---:|---:|---:|"])
        for option in report["options"]:
            lines.append(f"| {option['id']} | {option['all_runs_successful']} | {percentage(option['correct_charts']['duration_weighted_correct_harmonic_fraction'])} | {percentage(option['correct_charts']['duration_weighted_raw_correct_discard_fraction'])} | {percentage(option['corrupt_charts']['duration_weighted_wrong_label_fraction'])} | {percentage(option['per_backend_semantic_quality_loss']['spectral'])} / {percentage(option['per_backend_semantic_quality_loss']['nnls-chroma'])} | {option['eligible_quality_loss']} |")
        lines.extend(["", f"Selection: {report['selection_reason']}."])
    else:
        lines.extend(["", f"Frozen at `{report['frozen_at_utc']}` before this validation run; parameters `{json.dumps(report['frozen_parameters'], sort_keys=True)}`. Configuration and implementation hashes are verified before validation reads. No retuning."])
    lines.extend(["", "## Correct and corrupt charts remain separate", "", "| Policy / backend / supplied chart | Successful / requested | Correct harmony | Accepted harmony | Raw wrong seconds | Retained wrong seconds | Correct raw seconds discarded | Boundary F1 | Extra / missed | X seconds | Silent position advances | Wrong cases surviving |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for name, group in report["summary"].items():
        if not name.endswith("/all"):
            continue
        metrics, errors, raw, discard, progress = (group.get(key, {}) for key in ("metrics", "residual_errors", "raw_errors", "discard", "progress"))
        lines.append(f"| {name[:-4]} | {group['successful_cases']} / {group['requested_cases']} | {percentage(group['duration_weighted_correct_harmonic_fraction'])} | {percentage(group['duration_weighted_accepted_harmonic_fraction'])} | {raw.get('retained_erroneous_label_seconds', 0):.3f} | {errors.get('retained_erroneous_label_seconds', 0):.3f} | {discard.get('true_correct_labels_discarded_seconds', 0):.3f} | {percentage(metrics.get('boundary_f1_150ms'))} | {metrics.get('extra_predicted_boundaries', '—')} / {metrics.get('missed_reference_boundaries', '—')} | {metrics.get('unknown_duration_seconds', 0):.3f} | {progress.get('silent_frame_position_transitions', '—')} | {group['wrong_chart_cases_with_wrong_labels_surviving']} |")
    lines.extend(["", report["metric_definition"], "", report["cached_feature_policy"], "", "## Failures", ""])
    failures = [row for row in report["rows"] if row["status"] != "ok"]
    lines.extend(f"- {row['dataset']} / {row['case_id']} / {row['policy']} / {row['backend']} / {row['control']}: {row.get('reason', row['status'])}" for row in failures)
    if not failures:
        lines.append("No inference/scoring failures.")
    lines.extend(["", "## Limits", "", *["- " + value for value in report["limitations"]], ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    declare_parser = commands.add_parser("declare")
    declare_parser.add_argument("--output", type=Path, required=True)
    declare_parser.add_argument("--fresh-manifest-sha256", required=True)
    develop_parser = commands.add_parser("develop")
    develop_parser.add_argument("--suite", type=Path, required=True)
    develop_parser.add_argument("--cached-screen", type=Path, required=True)
    develop_parser.add_argument("--output", type=Path, required=True)
    develop_parser.add_argument("--declaration", type=Path, required=True)
    develop_parser.add_argument("--declaration-sha256", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--frozen-policy", type=Path, required=True)
    validate_parser.add_argument("--frozen-sha256", required=True)
    validate_parser.add_argument("--historical-suite", type=Path, required=True)
    validate_parser.add_argument("--historical-cache", type=Path, required=True)
    validate_parser.add_argument("--fresh-suite", type=Path, required=True)
    validate_parser.add_argument("--fresh-cache", type=Path, required=True)
    validate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "declare":
            declare(args.output, args.fresh_manifest_sha256)
            print(json.dumps({"declaration_sha256": sha(args.output)}, indent=2))
            return
        if args.command == "develop":
            report = develop(args.suite, args.cached_screen, args.output, args.declaration, args.declaration_sha256)
        else:
            report = validate(args.frozen_policy, args.frozen_sha256, args.historical_suite,
                args.historical_cache, args.fresh_suite, args.fresh_cache, args.output)
    except ERRORS as error:
        parser.exit(2, f"Acceptance evaluation failed: {error}\n")
    print(json.dumps({key: report.get(key) for key in ("stage", "selected_policy", "frozen_policy_sha256", "successful_attempts", "failed_attempts", "gates")}, indent=2))
    if report["failed_attempts"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
