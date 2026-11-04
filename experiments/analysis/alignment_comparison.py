"""Frozen paired acoustic-backend comparison on strictly untimed known charts.

The benchmark gives both paths only ordered non-N intended labels, never gold
timestamps. Native NNLS extraction consumes audio and an ID only. References
are used for scoring after inference. This serial experiment does not tune any
features, decoder settings, silence masks or mismatch thresholds.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

import numpy as np

import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import lab

SCHEMA = "paired-acoustic-alignment-comparison-1.0"
BACKENDS = ("spectral", "nnls-chroma")
DEFAULTS = {"hop_seconds": 0.025, "window_seconds": 0.18,
            "min_chord_seconds": 0.15, "transition_penalty": 0.12,
            "unknown_score": 0.45, "mismatch_margin": 0.30, "max_audio_seconds": 600}
MEANS = ("boundary_f1_150ms", "boundary_precision_150ms", "boundary_recall_150ms",
         "matched_boundary_mean_error_seconds", "unknown_fraction",
         "reference_no_chord_duration_covered_fraction", "no_chord_boundary_f1_150ms",
         "matched_no_chord_boundary_mean_error_seconds", "reference_coverage_fraction")
SUMS = ("reference_boundaries", "predicted_boundaries", "matched_boundaries",
        "missed_reference_boundaries", "extra_predicted_boundaries",
        "reference_no_chord_boundaries", "matched_no_chord_boundaries",
        "missed_reference_no_chord_boundaries", "unknown_duration_seconds",
        "false_no_chord_duration_on_annotated_harmony_seconds")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_digest(features: dict) -> str:
    """Hash exact spectral arrays plus their shape, dtype and grid metadata."""
    digest = hashlib.sha256()
    for name in ("chroma", "rms", "silent"):
        value = np.ascontiguousarray(features[name])
        digest.update(json.dumps([name, value.dtype.str, value.shape]).encode())
        digest.update(value.tobytes())
    digest.update(json.dumps({name: features[name] for name in (
        "hop_samples", "frame_size", "silence_rms_threshold")}, sort_keys=True).encode())
    return digest.hexdigest()


@contextmanager
def measured_acoustic_calls():
    """Time existing functions without modifying their arguments or arrays.

    This is intentionally serial instrumentation. The references are restored
    even on failure; this runner must not share concurrent aligner calls.
    """
    original_features, original_evidence = chart_aligner.features, chart_aligner.acoustic_evidence
    measurement = {"original_pcm_features_wall_seconds": 0.0,
                   "cached_evidence_resampling_wall_seconds": 0.0}

    def measured_features(*arguments, **keywords):
        started = time.perf_counter()
        result = original_features(*arguments, **keywords)
        measurement["original_pcm_features_wall_seconds"] += time.perf_counter() - started
        measurement["spectral_feature_arrays_sha256"] = array_digest(result)
        return result

    def measured_evidence(*arguments, **keywords):
        started = time.perf_counter()
        result = original_evidence(*arguments, **keywords)
        measurement["cached_evidence_resampling_wall_seconds"] += time.perf_counter() - started
        return result

    chart_aligner.features, chart_aligner.acoustic_evidence = measured_features, measured_evidence
    try:
        yield measurement
    finally:
        chart_aligner.features, chart_aligner.acoustic_evidence = original_features, original_evidence


def untimed_input(reference: dict, audio: Path, case_id: str) -> dict:
    sequence = [event["label"] for event in reference["chords"] if event["label"] != "N"]
    if not sequence:
        raise ValueError("No non-N intended labels to align")
    result = {"schema_version": chart_aligner.SCHEMA,
              "recording": {"id": reference["recording"]["id"],
                            "title": reference["recording"]["title"], "audio_sha256": sha(audio)},
              "sequence": sequence, "mode": "finite", "start_policy": "first", "end_policy": "last",
              "metadata": {"source_references": [{"source": "procedural intended labels only", "case_id": case_id}],
                           "note": "All reference timestamps and all N events withheld from inference"}}
    chart_aligner.validate_untimed_chart(result)
    return result


def preflight(suite: Path, output: Path, overwrite: bool) -> tuple[dict, list[Path]]:
    suite = suite.resolve()
    manifest_path = suite / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Suite manifest needs a nonempty case list")
    identifiers = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(identifiers) != len(cases) or any(not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", value) for value in identifiers):
        raise ValueError("Suite contains unsafe case IDs")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Suite case IDs collide")
    for case in cases:
        for key in ("audio", "reference"):
            value = case.get(key)
            if not isinstance(value, str):
                raise ValueError(f"Case {case['id']} needs {key} path")
            path = (suite / value).resolve()
            if not path.is_relative_to(suite) or not path.is_file():
                raise ValueError("Suite audio/reference must be files inside the suite")
    # Every existing file in the suite is protected, including another case's
    # inputs and cached auxiliary files, before even the first publication.
    protected = [path for path in suite.rglob("*") if path.is_file()]
    outputs = [output / "report.json"]
    for identifier in identifiers:
        directory = output / "cases" / identifier
        outputs.extend(directory / name for name in (
            "untimed-input.json", "spectral-alignment.json", "nnls-evidence.json", "nnls-alignment.json"))
    resolved = [path.resolve() for path in outputs]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Output artifact paths collide")
    existing = [path for path in outputs if path.exists()]
    for index, path in enumerate(existing):
        if any(path.samefile(other) for other in existing[index + 1:]):
            raise ValueError("Output artifacts alias each other")
    for path in outputs:
        chart_aligner.check_output_path(path, protected, overwrite=overwrite)
    return manifest, protected


def summarize(rows: list[dict]) -> dict:
    result = {"cases": len(rows)}
    for metric in MEANS:
        values = [row["metrics"][metric] for row in rows if row["metrics"][metric] is not None]
        result[metric] = float(np.mean(values)) if values else None
    for metric in SUMS:
        result[metric] = sum(row["metrics"][metric] for row in rows)
    for metric in ("feature_extraction_wall_seconds", "align_call_wall_seconds",
                   "original_pcm_features_wall_seconds", "cached_evidence_resampling_wall_seconds",
                   "decoder_and_other_alignment_wall_seconds", "end_to_end_inference_wall_seconds"):
        result[metric] = sum(row["timing"][metric] for row in rows)
    result["needs_review_cases"] = sum(row["diagnostics"]["acoustic_fit_status"] != "no_large_mismatch_detected" for row in rows)
    result["missed_supplied_sequence_events"] = sum(len(row["diagnostics"]["unvisited_sequence_indices"]) for row in rows)
    return result


def inference(audio: Path, chart_path: Path, backend: str, evidence_path: Path,
              protected: list[Path], overwrite: bool) -> tuple[dict, dict, str | None]:
    extraction_seconds, evidence_hash = 0.0, None
    if backend == "nnls-chroma":
        identifier = json.loads(chart_path.read_text())["recording"]["id"]
        started = time.perf_counter()
        # Acoustic extraction receives neither chart labels nor gold reference.
        evidence = nnls_chroma_adapter.extract(audio, identifier)
        extraction_seconds = time.perf_counter() - started
        nnls_chroma_adapter.validate_evidence(evidence, audio)
        chart_aligner.write_json_safely(evidence_path, evidence, protected + [chart_path], overwrite=overwrite)
        evidence_hash = sha(evidence_path)
    with measured_acoustic_calls() as measured:
        started = time.perf_counter()
        parameters = {**DEFAULTS, **({"evidence_json": evidence_path} if backend == "nnls-chroma" else {})}
        prediction = chart_aligner.align(audio, chart_path, **parameters)
        align_seconds = time.perf_counter() - started
    pcm_seconds = measured["original_pcm_features_wall_seconds"]
    resample_seconds = measured["cached_evidence_resampling_wall_seconds"]
    if backend == "spectral":
        extraction_seconds = pcm_seconds
    timing = {"feature_extraction_wall_seconds": extraction_seconds,
              "align_call_wall_seconds": align_seconds,
              "original_pcm_features_wall_seconds": pcm_seconds,
              "cached_evidence_resampling_wall_seconds": resample_seconds,
              "decoder_and_other_alignment_wall_seconds": max(0.0, align_seconds - pcm_seconds - resample_seconds),
              "end_to_end_inference_wall_seconds": align_seconds + (extraction_seconds if backend == "nnls-chroma" else 0),
              "spectral_feature_arrays_sha256": measured.get("spectral_feature_arrays_sha256")}
    return prediction, timing, evidence_hash


def run(suite: Path, output: Path, *, overwrite: bool = False) -> dict:
    started = time.perf_counter()
    manifest, protected = preflight(suite, output, overwrite)
    cases = []
    for case in manifest["cases"]:
        result = {key: case.get(key) for key in ("id", "level", "condition", "split")}
        result["backends"] = {}
        audio, reference_path = suite / case["audio"], suite / case["reference"]
        try:
            reference = lab.load_chart(reference_path)
            try:
                chart = untimed_input(reference, audio, case["id"])
            except ValueError as error:
                result.update(status="excluded", reason=f"Unsupported untimed input: {error}")
                cases.append(result)
                continue
            directory = output / "cases" / case["id"]
            chart_path, evidence_path = directory / "untimed-input.json", directory / "nnls-evidence.json"
            chart_aligner.write_json_safely(chart_path, chart, protected, overwrite=overwrite)
            result.update(audio_sha256=sha(audio), chart_sha256=sha(chart_path),
                          hidden_reference_sha256=sha(reference_path))
            for backend in BACKENDS:
                row = {"status": "error"}
                try:
                    prediction, timing, evidence_hash = inference(audio, chart_path, backend,
                                                                 evidence_path, protected, overwrite)
                    result_path = directory / ("spectral-alignment.json" if backend == "spectral" else "nnls-alignment.json")
                    chart_aligner.write_json_safely(result_path, prediction,
                                                   protected + [chart_path, evidence_path], overwrite=overwrite)
                    # Hidden timestamp-bearing reference is consumed by the
                    # scorer only after this backend's inference has completed.
                    metrics = alignment_screen.boundary_metrics(reference, prediction)
                    row.update(status="ok", metrics=metrics, timing=timing,
                               diagnostics=prediction["alignment_evidence"]["diagnostics"],
                               acoustic_input=prediction["alignment_evidence"]["acoustic_input"],
                               evidence_sha256=evidence_hash,
                               output_sha256=sha(result_path),
                               output=str(result_path.relative_to(output)))
                except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                    row["reason"] = str(error)
                result["backends"][backend] = row
            result["status"] = "ok" if all(row["status"] == "ok" for row in result["backends"].values()) else "partial_error"
        except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            result.update(status="error", reason=str(error))
        cases.append(result)
        print(f"{len(cases)}/{len(manifest['cases'])}: {case['id']} {result['status']}", flush=True)
    paired = [case for case in cases if case["status"] == "ok"]
    grouped = defaultdict(list)
    for case in paired:
        grouped["all"].append(case)
        grouped[f"level_{case['level']}"].append(case)
        grouped[f"split_{case['split']}"].append(case)
    summary = {group: {backend: summarize([case["backends"][backend] for case in group_cases])
                       for backend in BACKENDS} for group, group_cases in grouped.items()}
    successful = {backend: sum(case["backends"].get(backend, {}).get("status") == "ok" for case in cases)
                  for backend in BACKENDS}
    failed = {backend: sum(case["backends"].get(backend, {}).get("status") == "error" for case in cases)
              for backend in BACKENDS}
    report = {"schema_version": SCHEMA, "algorithm_version": chart_aligner.VERSION,
              "suite_version": manifest.get("suite_version"),
              "manifest_sha256": sha(suite / "manifest.json"),
              "implementation_sha256": {"runner": sha(Path(__file__)), "aligner": sha(Path(chart_aligner.__file__)),
                                        "nnls_adapter": sha(Path(nnls_chroma_adapter.__file__))},
              "requested_cases": len(cases), "paired_successful_cases": len(paired),
              "excluded_cases": sum(case["status"] == "excluded" for case in cases),
              "failed_or_partial_cases": sum(case["status"] in ("error", "partial_error") for case in cases),
              "backend_successful_cases": successful, "backend_failed_attempts": failed,
              "parameters": {"decoder_defaults": DEFAULTS, "mode": "finite", "start_policy": "first", "end_policy": "last",
                             "untimed_input": "All ordered non-N labels; no timestamps, reference silence events or durations",
                             "nnls_frozen_parameters": nnls_chroma_adapter.FROZEN_PARAMETERS},
              "metric_definition": "Unweighted case means on the exact paired-successful set; ordered one-to-one boundary matches within 150ms. Means of matched errors omit misses; read extra/missed counts alongside them. Boundaries include N/X transitions; N-only boundary scoring is separate.",
              "runtime_definition": "Exact unmodified feature calls timed by serial wrappers. Spectral extraction is already included in align_call; native NNLS extraction is separate. NNLS align_call also computes original PCM features for the unchanged short-window silence mask. Decoder/other time excludes measured PCM features and evidence loading/resampling but includes chart/audio I/O, scoring templates, path decoding and output construction. End-to-end inference excludes evidence serialization, subsequent output publication and evaluation; no double-counting of spectral extraction.",
              "limitations": ["Correct labels, event count and order are supplied: conditional timing, not independent chord recognition accuracy.",
                              "No settings tuned on this run; both paths use the same decoder, silence mask and mismatch thresholds.",
                              "NNLS uses an approximately 743ms native window and 93ms hop at 22050Hz; interpolation to a 25ms decoder grid does not create finer acoustic resolution.",
                              "Features are offline with global tuning; cosine scores and mismatch heuristics are not calibrated confidence.",
                              "Finite start/end constraints can force a wrong chart to complete; X gaps, boundary errors and sequence diagnostics must be inspected.",
                              "All 64 recipes share a procedural generator; named screen/holdout splits do not establish real-song generalisation.",
                              "A smaller matched-boundary error can coexist with missed changes; no real-song or application readiness claim follows."],
              "runtime_seconds": time.perf_counter() - started, "summary": summary, "cases": cases}
    chart_aligner.write_json_safely(output / "report.json", report, protected, overwrite=overwrite)
    return report


def markdown_report(report: dict) -> str:
    lines = ["# Frozen spectral versus NNLS acoustic alignment", "",
             f"{report['paired_successful_cases']}/{report['requested_cases']} cases completed as pairs; "
             f"{report['excluded_cases']} excluded and {report['failed_or_partial_cases']} failed/partial cases. "
             f"Both paths use chart_aligner {report['algorithm_version']} and the same frozen defaults.", "",
             "Correct ordered chord labels and their event count are supplied. All reference timestamps and N events are withheld from inference. This measures conditional timing on procedural audio, not recognition or real-song accuracy.", "",
             "| Backend | Mean boundary F1 | Precision | Recall | Extra / missed | Matched error | Mean X | Silence-duration coverage | Feature / align time |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for backend, row in report["summary"].get("all", {}).items():
        error = row["matched_boundary_mean_error_seconds"]
        silence = row["reference_no_chord_duration_covered_fraction"]
        lines.append(f"| {backend} | {row['boundary_f1_150ms']:.4f} | {row['boundary_precision_150ms']:.4f} | "
                     f"{row['boundary_recall_150ms']:.4f} | {row['extra_predicted_boundaries']} / {row['missed_reference_boundaries']} | "
                     f"{error * 1000:.1f} ms | {row['unknown_fraction']:.2%} | {silence:.2%} | "
                     f"{row['feature_extraction_wall_seconds']:.3f}s / {row['align_call_wall_seconds']:.3f}s |")
    lines.extend(["", "Metrics are unweighted case means on paired successful cases. Errors cover matched boundaries only. The 150ms matching tolerance and decoder settings were frozen before this comparison; failures remain visible in JSON/CSV.", "",
                  report["runtime_definition"], "", "## Interpretation limits", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(["", "## Reproduce", "", "```sh",
                  ".venv-analysis/bin/python experiments/analysis/alignment_comparison.py",
                  "```", "", "The native acoustic host must first be built as described in [NNLS_CHROMA_EVIDENCE.md](NNLS_CHROMA_EVIDENCE.md). The generated 64-case suite must already exist. Default outputs are ignored local artifacts under `experiments/generated/acoustic-alignment-comparison/`; choose a new `--output` directory or explicitly use `--overwrite`. The complete suite is protected against output aliases. The original alignment screen is untouched.", "",
                  "Publish a review snapshot after inference:", "", "```sh",
                  ".venv-analysis/bin/python experiments/analysis/alignment_comparison.py --publish-docs",
                  "```", "", "The machine report records audio, untimed-chart, hidden-reference, feature/evidence, output and implementation hashes. Native build/source provenance is preserved in each evidence packet. Fixed NNLS metadata and audio pairing are validated before alignment. Settings were not adjusted using Creep or other real recordings.", ""])
    return "\n".join(lines)


def csv_report(report: dict) -> str:
    stream = io.StringIO()
    fields = ["id", "level", "condition", "split", "backend", "status", "reason",
              "audio_sha256", "chart_sha256", "hidden_reference_sha256", "evidence_sha256", "output_sha256",
              *MEANS, *SUMS, "feature_extraction_wall_seconds", "align_call_wall_seconds",
              "end_to_end_inference_wall_seconds"]
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    for case in report["cases"]:
        for backend in BACKENDS:
            row = case["backends"].get(backend, {"status": case["status"], "reason": case.get("reason", "")})
            record = {key: case.get(key, "") for key in fields if key in case and key != "backends"}
            record.update(backend=backend, status=row["status"], reason=row.get("reason", ""),
                          evidence_sha256=row.get("evidence_sha256"), output_sha256=row.get("output_sha256"))
            record.update({key: value for key, value in row.get("metrics", {}).items() if key in fields})
            record.update({key: value for key, value in row.get("timing", {}).items() if key in fields})
            writer.writerow(record)
    return stream.getvalue()


def publish_docs(report: dict, suite: Path, output: Path, *, overwrite: bool = False) -> None:
    docs = lab.ROOT / "docs"
    paths = [docs / f"ACOUSTIC_ALIGNMENT_COMPARISON.{suffix}" for suffix in ("json", "md", "csv")]
    protected = [path for path in suite.rglob("*") if path.is_file()] + [path for path in output.rglob("*") if path.is_file()]
    for path in paths:
        chart_aligner.check_output_path(path, protected, overwrite=overwrite)
    chart_aligner.write_json_safely(paths[0], report, protected, overwrite=overwrite)
    # Publish text through new temporary files and atomic directory entries,
    # preserving the same alias/exclusive-creation policy as JSON artifacts.
    for path, contents in zip(paths[1:], (markdown_report(report), csv_report(report))):
        write_text_safely(path, contents, protected + [paths[0]], overwrite=overwrite)


def write_text_safely(path: Path, contents: str, protected: list[Path], *, overwrite: bool) -> None:
    chart_aligner.check_output_path(path, protected, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        chart_aligner.check_output_path(path, protected, overwrite=overwrite)
        if overwrite:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError as error:
                raise ValueError("Output appeared concurrently; refusing to overwrite it") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=lab.GENERATED / "synthetic-suite")
    parser.add_argument("--output", type=Path, default=lab.GENERATED / "acoustic-alignment-comparison")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--publish-docs", action="store_true", help="Publish existing report JSON/Markdown/CSV without rerunning inference")
    arguments = parser.parse_args()
    try:
        if arguments.publish_docs:
            report = json.loads((arguments.output / "report.json").read_text())
            publish_docs(report, arguments.suite, arguments.output, overwrite=arguments.overwrite)
        else:
            report = run(arguments.suite, arguments.output, overwrite=arguments.overwrite)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Comparison failed: {error}\n")
    print(json.dumps({key: report[key] for key in ("paired_successful_cases", "excluded_cases",
                                                   "failed_or_partial_cases", "backend_failed_attempts", "summary")}, indent=2))
    if report["failed_or_partial_cases"] or report["excluded_cases"]:
        parser.exit(2)


if __name__ == "__main__":
    main()
