"""Frozen rich-chord recognition and conditional timing screen.

Raw recognizers receive audio only. Chart aligners receive an independently
published untimed sequence, never reference timestamps. Correct-chart scores
are conditional on supplied labels; deliberately corrupt charts test whether
wrong labels survive the unchanged mismatch mask. Synthetic success is not a
production-readiness claim.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time

import numpy as np

import alignment_comparison
import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import lab

SCHEMA = "rich-quality-screen-1.0"
RECOGNIZERS = ("crema", "chordino")
BACKENDS = ("spectral", "nnls-chroma")
DEFAULTS = copy.deepcopy(alignment_comparison.DEFAULTS)
ERRORS = (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired,
          json.JSONDecodeError)


def suite_module():
    # The independent fixture/scoring module has no model imports.
    import rich_quality_suite
    return rich_quality_suite


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight(suite: Path, output: Path) -> dict:
    suite = suite.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; choose a new output directory (no overwrite)")
    resolved_output = output.resolve()
    if resolved_output == suite or resolved_output.is_relative_to(suite):
        raise ValueError("Output must be outside the source suite")
    manifest = json.loads((suite / "manifest.json").read_text())
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Suite needs a nonempty cases list")
    identifiers = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(identifiers) != len(cases) or any(not isinstance(value, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,127}", value) for value in identifiers):
        raise ValueError("Case IDs must be safe identifiers")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Case IDs collide")
    for case in cases:
        for key in ("audio", "reference", "untimed"):
            value = case.get(key)
            if not isinstance(value, str):
                raise ValueError(f"Case {case['id']} needs {key} path")
            path = (suite / value).resolve()
            if not path.is_relative_to(suite) or not path.is_file():
                raise ValueError("Suite inputs must be files inside the suite")
            declared = case.get(f"{key}_sha256")
            if declared is not None and declared != sha(path):
                raise ValueError(f"Case {case['id']} {key} hash differs from manifest")
        chart = json.loads((suite / case["untimed"]).read_text())
        chart_aligner.validate_untimed_chart(chart)
        if chart["recording"]["id"] != case["id"]:
            raise ValueError("Untimed recording identity differs from case")
        if chart["recording"].get("audio_sha256") != sha(suite / case["audio"]):
            raise ValueError("Untimed audio hash differs from source")
        if chart.get("mode", "finite") != "finite" or chart.get("start_policy", "first") != "first" or chart.get("end_policy", "last") != "last":
            raise ValueError("Screen requires frozen finite first/last constraints")
    return manifest


def control_charts(untimed: dict, family: str) -> dict[str, dict]:
    """Corrupt only untimed labels/order; never consult timed references."""
    fixture = suite_module()
    sequence = untimed["sequence"]
    variants = {"correct": list(sequence)}
    if family == "plain_control":
        variants["extra_extensions"] = [fixture.chord_to_rich(label) for label in sequence]
    else:
        variants["simplified_quality"] = [fixture.chord_to_plain(label) for label in sequence]
        # Keep roots fixed but change quality. This is deliberately wrong,
        # independent of any expected boundary or audio feature.
        altered = []
        for label in sequence:
            plain = fixture.chord_to_plain(label)
            match = re.fullmatch(r"([A-G][#b]?)(m)?(?:/.*)?", plain)
            if not match:
                raise ValueError(f"Cannot make same-root wrong-quality control: {label}")
            altered.append(match[1] + ("maj7" if match[2] else "m7"))
        variants["wrong_quality"] = altered
    # Rotate section-sized halves while retaining count. It is a declared
    # wrong order, not an inferred arrangement or a hidden-timing edit.
    midpoint = max(1, len(sequence) // 2)
    rotated = list(sequence[midpoint:]) + list(sequence[:midpoint])
    if rotated == list(sequence):
        rotated = list(reversed(sequence))
    if rotated != list(sequence):
        variants["wrong_section_order"] = rotated
    result = {}
    for name, labels in variants.items():
        if name != "correct" and labels == list(sequence):
            continue
        chart = copy.deepcopy(untimed)
        chart["sequence"] = labels
        chart.setdefault("metadata", {})["screen_control"] = name
        chart_aligner.validate_untimed_chart(chart)
        result[name] = chart
    return result


def raw_batches(source_manifest: Path, stage: Path, *, timeout: float) -> dict:
    """Existing adapters/models, exact defaults; no reference passed to either."""
    metadata = {}
    for candidate in RECOGNIZERS:
        adapter = Path(__file__).parent / "candidates" / f"{candidate}_adapter.py"
        python = lab.ROOT / f".venv-{'crema' if candidate == 'crema' else 'analysis'}" / "bin/python"
        started = time.perf_counter()
        row = {"status": "error", "adapter_sha256": sha(adapter), "python": str(python)}
        if not python.is_file():
            row["reason"] = "Isolated Python environment unavailable"
        else:
            log = ""
            command = [str(python), str(adapter), "--batch-manifest", str(source_manifest),
                       "--output-root", str(stage)]
            try:
                process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
                log = process.stdout + process.stderr
                row.update(status="ok" if process.returncode == 0 else "partial_error",
                           returncode=process.returncode)
            except subprocess.TimeoutExpired as error:
                def as_text(value):
                    return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
                log = as_text(error.stdout) + as_text(error.stderr)
                row["reason"] = f"Batch timed out after {timeout:g} seconds"
            except OSError as error:
                row["reason"] = f"Adapter invocation failed: {error}"
                log = str(error)
            log_path = stage / f"{candidate}-batch.log"
            log_path.write_text(log)
            row["log_sha256"] = sha(log_path)
            summary = stage / f"{candidate}-batch-summary.json"
            if summary.is_file():
                row["summary_sha256"] = sha(summary)
                row["summary"] = json.loads(summary.read_text())
        row["wall_seconds"] = time.perf_counter() - started
        metadata[candidate] = row
    return metadata


def validate_prediction(prediction: dict, recording_id: str, audio: Path) -> None:
    lab.validate_chart(prediction)
    samples, rate = lab.read_wav(audio)
    recording = prediction["recording"]
    if recording["id"] != recording_id or recording.get("audio_sha256") != sha(audio):
        raise ValueError("Prediction identity/audio hash differs from source")
    if recording["sample_rate_hz"] != rate or abs(recording["duration_seconds"] - len(samples) / rate) > 1 / rate:
        raise ValueError("Prediction sample rate/duration differs from source")


def retained_error_metrics(reference: dict, prediction: dict) -> dict:
    """Measure incorrect harmonic labels surviving X/N masks, not script success."""
    fixture = suite_module()
    harmonic = error = unknown = no_chord = rich_error = false_rich = plain_seconds = 0.0
    for expected in reference["chords"]:
        truth = fixture.chord_semantics(expected["label"])
        if truth["status"] != "chord":
            continue
        amount = expected["end_seconds"] - expected["start_seconds"]
        harmonic += amount
        plain = truth["quality"] in ("", "m")
        if plain:
            plain_seconds += amount
        covered = 0.0
        for actual in prediction["chords"]:
            overlap = max(0.0, min(expected["end_seconds"], actual["end_seconds"])
                          - max(expected["start_seconds"], actual["start_seconds"]))
            if not overlap:
                continue
            covered += overlap
            observed = fixture.chord_semantics(actual["label"])
            if observed["status"] == "unknown":
                unknown += overlap
            elif observed["status"] == "no_chord":
                no_chord += overlap
            elif (truth["root"], truth["quality"]) != (observed["root"], observed["quality"]):
                error += overlap
                rich = observed["quality"] in fixture.EXTENSION_QUALITIES
                rich_error += overlap * rich
                false_rich += overlap * (plain and rich)
        unknown += max(0.0, amount - covered)
    return {"reference_harmonic_seconds": harmonic,
            "retained_erroneous_label_seconds": error,
            "retained_erroneous_label_fraction": error / harmonic if harmonic else None,
            "retained_erroneous_rich_label_seconds": rich_error,
            "retained_erroneous_rich_label_fraction": rich_error / harmonic if harmonic else None,
            "plain_reference_seconds": plain_seconds,
            "erroneous_rich_on_plain_seconds": false_rich,
            "erroneous_rich_on_plain_fraction": false_rich / plain_seconds if plain_seconds else None,
            "unknown_on_reference_harmony_seconds": unknown,
            "false_no_chord_on_reference_harmony_seconds": no_chord}


def aggregate(rows: list[dict]) -> dict:
    """Transparent case means plus duration totals, with failure denominators."""
    good = [row for row in rows if row["status"] == "ok"]
    result = {"requested_cases": len(rows), "successful_cases": len(good),
              "failed_cases": sum(row["status"] == "error" for row in rows),
              "excluded_cases": sum(row["status"] == "excluded" for row in rows)}
    if not good:
        return result
    for group in ("metrics", "timing", "residual_errors"):
        names = set().union(*(row.get(group, {}).keys() for row in good))
        values = {}
        for name in sorted(names):
            measurements = [row.get(group, {}).get(name) for row in good]
            measurements = [value for value in measurements if isinstance(value, (int, float))
                            and not isinstance(value, bool) and math.isfinite(value)]
            if measurements:
                # Rates are never summed. Report unweighted means explicitly;
                # all additive seconds/counts remain available beside them.
                additive = name.endswith("_seconds") and not ("mean_error" in name or name.startswith("boundary_tolerance"))
                additive |= name.endswith("_boundaries") or name == "missed_supplied_sequence_events"
                values[name] = sum(measurements) if additive else sum(measurements) / len(measurements)
        result[group] = values
    result["needs_review_cases"] = sum(row.get("diagnostics", {}).get("acoustic_fit_status")
                                       not in (None, "no_large_mismatch_detected") for row in good)
    result["corrupt_cases_with_retained_errors"] = sum(row.get("control") not in (None, "correct") and row.get("residual_errors", {}).get("retained_erroneous_label_seconds", 0) > 1e-9 for row in good)
    result["missed_supplied_sequence_events"] = sum(row.get("missed_supplied_sequence_events", 0) for row in good)
    result["corrupt_cases_without_large_mismatch_warning"] = sum(
        row.get("control") != "correct" and row.get("diagnostics", {}).get("acoustic_fit_status") == "no_large_mismatch_detected"
        for row in good)
    return result


def summarize(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        base = row["candidate"] if row["kind"] == "recognition" else f"{row['candidate']}/{row['control']}"
        for subset in ("all", f"split/{row['split']}", f"family/{row['family']}", f"condition/{row['condition']}"):
            groups[f"{base}/{subset}"].append(row)
    return {name: aggregate(group) for name, group in sorted(groups.items())}


def corrupt_charts_rejected(rows: list[dict]) -> bool:
    controls = [row for row in rows if row.get("control") not in (None, "correct")]
    if not controls:
        return False
    for row in controls:
        value = row.get("residual_errors", {}).get("retained_erroneous_label_seconds")
        if row.get("status") != "ok" or not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value > 1e-9 or value < 0:
            return False
    return True


def _execute(suite: Path, stage: Path, manifest: dict, *, timeout: float) -> dict:
    started = time.perf_counter()
    inference_manifest = {"suite_version": manifest.get("suite_version"), "cases": []}
    prepared = []
    # Materialise byte-identical audio-only model inputs. No reference paths,
    # labels, times, recipe labels or durations appear in the adapter manifest.
    for case in manifest["cases"]:
        identifier = case["id"]
        audio = stage / "audio-only-inputs" / "cases" / identifier / "audio.wav"
        audio.parent.mkdir(parents=True)
        shutil.copyfile(suite / case["audio"], audio)
        if sha(audio) != sha(suite / case["audio"]):
            raise ValueError("Copied inference audio differs from source")
        inference_manifest["cases"].append({"id": identifier, "audio": f"cases/{identifier}/audio.wav"})
        untimed = json.loads((suite / case["untimed"]).read_text())
        prepared.append((case, audio, control_charts(untimed, case["recipe"]["family"])))
    manifest_path = stage / "audio-only-inputs" / "manifest.json"
    lab.write_json(manifest_path, inference_manifest)
    batches = raw_batches(manifest_path, stage, timeout=timeout)
    pending = []
    input_hashes = []
    for index, (case, audio, charts) in enumerate(prepared, 1):
        identifier = case["id"]
        directory = stage / "cases" / identifier
        directory.mkdir(parents=True, exist_ok=True)
        base = {"case_id": identifier, "condition": case["condition"], "split": case["split"],
                "family": case["recipe"]["family"], "audio_sha256": sha(audio),
                "hidden_reference_sha256": sha(suite / case["reference"]),
                "untimed_source_sha256": sha(suite / case["untimed"])}
        input_hashes.append(copy.deepcopy(base))
        for candidate in RECOGNIZERS:
            row = {**base, "kind": "recognition", "candidate": candidate, "status": "error"}
            path = directory / f"{candidate}.json"
            try:
                prediction = lab.load_chart(path)
                validate_prediction(prediction, identifier, audio)
                row.update(status="inferred", output=f"cases/{identifier}/{path.name}", output_sha256=sha(path),
                           timing={"inference_wall_seconds": prediction["analysis"]["runtime_seconds"]})
                pending.append((case, row, prediction))
            except ERRORS as error:
                row["reason"] = str(error)
                pending.append((case, row, None))
        evidence_path = directory / "nnls-evidence.json"
        evidence_error = None
        extraction_seconds = 0.0
        try:
            extraction_start = time.perf_counter()
            evidence = nnls_chroma_adapter.extract(audio, identifier)
            extraction_seconds = time.perf_counter() - extraction_start
            nnls_chroma_adapter.validate_evidence(evidence, audio)
            chart_aligner.write_json_safely(evidence_path, evidence, [audio])
        except ERRORS as error:
            evidence_error = str(error)
        for control, chart in charts.items():
            chart_path = directory / f"{control}-untimed.json"
            chart_aligner.write_json_safely(chart_path, chart, [audio])
            for backend in BACKENDS:
                row = {**base, "kind": "conditional_alignment", "candidate": backend,
                       "control": control, "status": "error", "chart_sha256": sha(chart_path)}
                try:
                    if backend == "nnls-chroma" and evidence_error:
                        raise ValueError(f"Native acoustic evidence failed: {evidence_error}")
                    parameters = {**DEFAULTS, **({"evidence_json": evidence_path} if backend == "nnls-chroma" else {})}
                    with alignment_comparison.measured_acoustic_calls() as measured:
                        inference_start = time.perf_counter()
                        prediction = chart_aligner.align(audio, chart_path, **parameters)
                        alignment_seconds = time.perf_counter() - inference_start
                    validate_prediction(prediction, identifier, audio)
                    result_path = directory / f"{control}-{backend}.json"
                    chart_aligner.write_json_safely(result_path, prediction, [audio, chart_path, evidence_path])
                    row.update(status="inferred", output=f"cases/{identifier}/{result_path.name}",
                               output_sha256=sha(result_path), diagnostics=prediction["alignment_evidence"]["diagnostics"],
                               acoustic_input=prediction["alignment_evidence"]["acoustic_input"],
                               evidence_sha256=sha(evidence_path) if backend == "nnls-chroma" else None,
                               missed_supplied_sequence_events=len(prediction["alignment_evidence"]["diagnostics"]["unvisited_sequence_indices"]),
                               timing={"align_call_wall_seconds": alignment_seconds,
                                       "native_feature_extraction_wall_seconds": extraction_seconds if backend == "nnls-chroma" and control == "correct" else 0.0,
                                       **measured})
                    pending.append((case, row, prediction))
                except ERRORS as error:
                    row["reason"] = str(error)
                    pending.append((case, row, None))
        print(f"Inferred {index}/{len(prepared)}: {identifier}", flush=True)
    # Only now read any timed chart. Both model batches and all alignment
    # inference finish before any hidden reference reaches a scoring function.
    rows = []
    for case, row, prediction in pending:
        if prediction is not None:
            try:
                reference = lab.load_chart(suite / case["reference"])
                validate_prediction(reference, case["id"], suite / case["audio"])
                metrics = suite_module().score(reference, prediction,
                                              candidate=row["candidate"] if row["kind"] == "recognition" else None,
                                              triad_control=case["recipe"]["family"] == "plain_control")
                metrics.update(alignment_screen.boundary_metrics(reference, prediction))
                row.update(status="ok", metrics=metrics)
                if row["kind"] == "conditional_alignment":
                    row["residual_errors"] = retained_error_metrics(reference, prediction)
            except ERRORS as error:
                row.update(status="error", reason=f"Scoring failed: {error}")
        rows.append(row)
    report = {"schema_version": SCHEMA, "suite_version": manifest.get("suite_version"),
              "manifest_sha256": sha(suite / "manifest.json"), "input_hashes": input_hashes,
              "requested_cases": len(manifest["cases"]), "rows": rows, "summary": summarize(rows),
              "successful_attempts": sum(row["status"] == "ok" for row in rows),
              "failed_attempts": sum(row["status"] == "error" for row in rows),
              "batch_runs": batches, "runtime_seconds": time.perf_counter() - started,
              "parameters": {"decoder_defaults": DEFAULTS, "native_frozen_parameters": nnls_chroma_adapter.FROZEN_PARAMETERS,
                             "mode": "finite", "start_policy": "first", "end_policy": "last",
                             "reference_timestamps_consumed_during_inference": False,
                             "model_reference_labels_consumed": False},
              "implementation_sha256": {"runner": sha(Path(__file__)), "fixture_and_scorer": sha(Path(suite_module().__file__)),
                                        "aligner": sha(Path(chart_aligner.__file__)),
                                        "nnls_adapter": sha(Path(nnls_chroma_adapter.__file__))},
              "runtime_definition": "Native extraction occurs once per case; its cost is allocated only to the correct NNLS row, while every control retains the same evidence hash. Spectral PCM extraction remains inside each unchanged alignment call. No repeated extraction cost is summed across cached controls.",
              "environment": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__},
              "gates": {"all_requested_inference_and_scoring_complete": all(row["status"] == "ok" for row in rows),
                        "wrong_charts_fully_rejected": corrupt_charts_rejected(rows),
                        "production_accuracy_or_readiness_established": False},
              "metric_definition": "Quality/root rates are unweighted successful case means; their additive duration totals are also preserved. Exact quality ignores slash-bass only and retains suspensions/extensions. Major/minor reports eligible coverage separately. Boundary matching is ordered one-to-one within 150ms, including N/X transitions; errors cover matched boundaries only. Failed attempts stay in every requested subset denominator.",
              "limitations": ["Raw CREMA/Chordino are independent recognition; correct-chart labels/order/count are supplied, so their alignment scores are conditional timing, not recognition accuracy.",
                              "Both aligners use existing frozen defaults; native feature extraction is cached once per audio and reused unchanged across controls.",
                              "Wrong-chart residual errors measure false labels surviving X/N masking. A successful run or no-large-mismatch diagnostic does not validate the chart.",
                              "Template cosine scores and mismatch diagnostics are not calibrated probabilities; finite endpoint constraints can force wrong charts.",
                              "Synthetic screen and holdout share one procedural generator. They do not demonstrate real guitar, full-song, production or catalogue accuracy.",
                              "NNLS native frames have approximately 93ms spacing and 743ms support at 22050Hz; resampling cannot create physical onset precision.",
                              "Native recognizer output is preserved; no chart relabeling, key/capo fix, extension upgrade or consensus is applied."]}
    lab.write_json(stage / "report.json", report)
    (stage / "report.md").write_text(markdown_report(report))
    return report


def run(suite: Path, output: Path, *, timeout: float = 600) -> dict:
    suite = suite.resolve(strict=True)
    output = output.absolute()
    manifest = preflight(suite, output)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be positive and finite")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        report = _execute(suite, stage, manifest, timeout=timeout)
        publish_directory_exclusively(stage, output)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def publish_directory_exclusively(stage: Path, output: Path) -> None:
    """Atomic directory publication with the OS no-replace primitive.

    A plain rename can overwrite another owner's empty directory. Fail closed
    if the native exclusive rename is unavailable rather than accept that race.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    if platform.system() == "Darwin":
        operation = libc.renamex_np
        operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        result = operation(os.fsencode(stage), os.fsencode(output), 0x00000004)  # RENAME_EXCL
    elif platform.system() == "Linux" and hasattr(libc, "renameat2"):
        operation = libc.renameat2
        operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        result = operation(-100, os.fsencode(stage), -100, os.fsencode(output), 1)  # RENAME_NOREPLACE
    else:
        raise ValueError("Exclusive atomic directory publication unavailable on this platform")
    if result:
        error = ctypes.get_errno()
        if error in (17, 39, 66):
            raise ValueError("Output appeared concurrently; refusing to overwrite it")
        raise OSError(error, os.strerror(error), str(output))


def percent(value) -> str:
    return f"{value:.1%}" if isinstance(value, (float, int)) else "—"


def markdown_report(report: dict) -> str:
    lines = ["# Rich-quality synthetic screen", "", f"{report['requested_cases']} generated cases; {report['successful_attempts']} successful attempts and {report['failed_attempts']} failures.", "",
             "Raw recognizers infer labels from audio alone. Correct-chart aligners receive the ordered labels and count in advance: those results measure conditional timing, not recognition accuracy. Corrupt-chart runs report wrong labels remaining after unchanged X/N masks.", "",
             "| Method / scenario | Cases ok / requested | Exact chord quality | Root | Maj/min | Maj/min coverage | Vocabulary coverage | False rich on plain | Boundary F1 | Extra / missed | X | Retained wrong labels |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, group in report["summary"].items():
        if not name.endswith("/all"):
            continue
        metrics, errors = group.get("metrics", {}), group.get("residual_errors", {})
        retained = f"{errors["retained_erroneous_label_seconds"]:.3f}s" if "retained_erroneous_label_seconds" in errors else "—"
        lines.append(f"| {name[:-4]} | {group['successful_cases']} / {group['requested_cases']} | {percent(metrics.get('semantic_chord_quality_agreement'))} | {percent(metrics.get('root_chord_agreement'))} | {percent(metrics.get('major_minor_chord_agreement'))} | {percent(metrics.get('major_minor_chord_reference_coverage'))} | {percent(metrics.get('supported_vocabulary_chord_coverage'))} | {percent(metrics.get('plain_triad_false_extension_fraction'))} | {percent(metrics.get('boundary_f1_150ms'))} | {metrics.get('extra_predicted_boundaries', '—')} / {metrics.get('missed_reference_boundaries', '—')} | {percent(metrics.get('unknown_fraction'))} | {retained} |")
    lines.extend(["", report["metric_definition"], "", "## Corrupt-chart safeguards", "",
                  "Completion is an integration check only. Residual wrong-label seconds and cases without large-mismatch warnings are the substantive tests; guards are not presumed safe because inference succeeds.", ""])
    for name, group in report["summary"].items():
        if name.endswith("/all") and any(f"/{control}/" in name for control in ("extra_extensions", "simplified_quality", "wrong_quality", "wrong_section_order")):
            errors = group.get("residual_errors", {})
            lines.append(f"- {name[:-4]}: {errors.get('retained_erroneous_label_seconds', 0):.3f}s retained incorrect labels; {errors.get('retained_erroneous_rich_label_seconds', 0):.3f}s incorrect rich labels; {group.get('corrupt_cases_with_retained_errors', 0)} cases with residual errors; {group.get('corrupt_cases_without_large_mismatch_warning', 0)} cases without a large-mismatch warning.")
    lines.extend(["", "## Recipe subsets", "", "| Raw recognizer / subset | Cases ok / requested | Exact chord quality | Root | Maj/min | Maj/min coverage | Vocabulary coverage | False rich on plain |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for candidate in RECOGNIZERS:
        for subset in ("family/rich_progression", "family/plain_control", "family/same_root_contrasts", "split/screen", "split/holdout"):
            group = report["summary"].get(f"{candidate}/{subset}", {})
            if not group:
                continue
            metrics = group.get("metrics", {})
            lines.append(f"| {candidate}/{subset} | {group['successful_cases']} / {group['requested_cases']} | {percent(metrics.get('exact_chord_quality_agreement'))} | {percent(metrics.get('root_chord_agreement'))} | {percent(metrics.get('major_minor_chord_agreement'))} | {percent(metrics.get('major_minor_chord_reference_coverage'))} | {percent(metrics.get('supported_vocabulary_chord_coverage'))} | {percent(metrics.get('plain_triad_false_extension_fraction'))} |")
    lines.extend(["", "Vocabulary coverage is the fraction of reference harmonic seconds representable by the audited native output vocabulary; it is not model accuracy. Every family/condition and screen/holdout subset is recorded separately in JSON. These splits are recipe variants of one generator, not an independent real-song holdout.", "", "## Failures", ""])
    failures = [row for row in report["rows"] if row["status"] != "ok"]
    lines.extend(f"- {row['case_id']} / {row['candidate']} / {row.get('control', 'raw')}: {row.get('reason', row['status'])}" for row in failures)
    if not failures:
        lines.append("No integration/scoring failures.")
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(["", "## Reproduce", "", "```sh", ".venv-analysis/bin/python experiments/analysis/rich_quality_suite.py generate --output-dir experiments/generated/rich-quality-suite-v2", ".venv-analysis/bin/python experiments/analysis/rich_quality_screen.py --suite experiments/generated/rich-quality-suite-v2 --output experiments/generated/rich-quality-screen-v2", "```", "", "Choose fresh output directories. The screen never overwrites a previous suite/screen. Existing CREMA and Chordino environments/native assets are required; no model download or training occurs. Audio bytes, independently untimed charts, hidden reference, raw predictions, evidence, implementations and native/model provenance remain in the machine report/artifacts. All reference timestamp scoring happens after all inference.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=lab.GENERATED / "rich-quality-suite-v2")
    parser.add_argument("--output", type=Path, default=lab.GENERATED / "rich-quality-screen-v2")
    parser.add_argument("--timeout-seconds", type=float, default=600)
    args = parser.parse_args()
    try:
        report = run(args.suite, args.output, timeout=args.timeout_seconds)
    except ERRORS as error:
        parser.exit(2, f"Screen failed: {error}\n")
    print(json.dumps({"successful_attempts": report["successful_attempts"], "failed_attempts": report["failed_attempts"], "gates": report["gates"]}, indent=2))
    if report["failed_attempts"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
