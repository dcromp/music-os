"""Bounded Wonderwall diagnostics with a previously frozen acceptance policy.

Reuses the old section hypotheses and cached NNLS unchanged; does not select
thresholds, alter repeat counts, infer a new chart, or measure accuracy. The
original wonderwall_guided wrapper and its six cached outputs are controls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import statistics
import tempfile

import acceptance_screen
from candidates import nnls_chroma_adapter
import chart_aligner
import guarded_aligner
import lab
import wonderwall_guided as original

SCHEMA = "wonderwall-guarded-diagnostics-1.0"
DEFAULT_POLICY = lab.GENERATED / "acceptance-development-v1/frozen-policy.json"
POLICY_SHA256 = "7a75786e45528622a86b5a6998452ef252c908f43a796c80d447c81b259c9ff3"
DEFAULT_OLD = lab.GENERATED / "wonderwall-guided-20261011"
DEFAULT_OUTPUT = lab.GENERATED / "wonderwall-guarded-20261011"


def diagnostics(path: Path, prediction: dict) -> dict:
    """Descriptive coverage/progress, with no hidden correctness denominator."""
    lab.validate_chart(prediction)
    duration = prediction["recording"]["duration_seconds"]
    evidence, chords = prediction["alignment_evidence"], prediction["chords"]
    checks = evidence["diagnostics"]
    proposed = evidence["proposed_path_events_before_gap_mask"]
    dwells = [event["end_seconds"] - event["start_seconds"] for event in proposed]
    masked = {label: sum(event["end_seconds"] - event["start_seconds"] for event in chords
                       if event["label"] == label) for label in ("N", "X")}
    labeled = sum(event["end_seconds"] - event["start_seconds"] for event in chords
                  if event["label"] not in ("N", "X"))
    columns, frames = evidence["frame_columns"], evidence["frames"]
    position_index, silent_index = columns.index("sequence_index"), columns.index("silent")
    silent_advances = sum(current[position_index] != previous[position_index] and current[silent_index]
                          for previous, current in zip(frames, frames[1:]))
    visited = {index for event in proposed for index in event["sequence_indices"]}
    return {"output": str(path.resolve()), "output_sha256": original.sha(path),
        "backend": prediction["analysis"]["parameters"]["acoustic_backend"],
        "input_chart_sha256": prediction["alignment_input"]["chart_sha256"],
        "duration_seconds": duration, "runtime_seconds": prediction["analysis"]["runtime_seconds"],
        "labeled_seconds": labeled, "labeled_coverage_fraction": labeled / duration,
        "masked_seconds": masked, "output_events": len(chords),
        "x_gap_events": sum(event["label"] == "X" for event in chords),
        "x_gap_events_below_150ms": sum(event["label"] == "X" and event["end_seconds"] - event["start_seconds"] < .15 for event in chords),
        "sequence_positions": len(prediction["alignment_input"]["sequence"]), "visited_positions": len(visited),
        "unvisited_sequence_indices": checks["unvisited_sequence_indices"],
        "path_transitions": checks["path_transitions"], "silent_position_transitions": int(silent_advances),
        "endpoint_reached": checks.get("endpoint_reached"), "partial": checks.get("partial"),
        "terminal_active_evidence_age_frames": checks.get("terminal_active_evidence_age_frames"),
        "proposed_minimum_dwell_seconds": min(dwells), "proposed_median_dwell_seconds": statistics.median(dwells),
        "proposed_maximum_dwell_seconds": max(dwells), "positions_below_350ms": sum(value < .35 for value in dwells),
        "positions_over_8_seconds": sum(value > 8 for value in dwells),
        "positions_with_no_active_frames": sum(event["evidence"]["active_frames"] == 0 for event in proposed),
        "near_minimum_active_evidence_sequence_indices": checks.get("near_minimum_active_evidence_sequence_indices"),
        "insufficient_active_evidence_sequence_indices": checks.get("insufficient_active_evidence_sequence_indices"),
        "no_active_evidence_supplied_position_count": checks.get("no_active_evidence_supplied_position_count"),
        "rejected_quality_seconds": checks.get("rejected_quality_seconds"),
        "quality_abstention_fraction_of_active_audio": checks.get("quality_abstention_fraction_of_active_audio"),
        "active_mismatch_fraction": checks["active_mismatch_fraction"], "fit_status": checks["acoustic_fit_status"],
        "section_intervals": [dict(event, span_seconds=event["end_seconds"] - event["start_seconds"])
                              for event in evidence.get("section_intervals_from_proposed_path", [])],
        "acoustically_indistinguishable_pairs": checks["acoustically_indistinguishable_sequence_position_pairs"],
        "accuracy_measured": False, "arrangement_verified": False, "accepted_for_primary_playback": False}


def run(output: Path = DEFAULT_OUTPUT, *, policy: Path = DEFAULT_POLICY,
        policy_sha256: str = POLICY_SHA256, old: Path = DEFAULT_OLD,
        audio: Path = original.DEFAULT_AUDIO, chart: Path = original.DEFAULT_CHART) -> dict:
    output, old, audio, chart = output.absolute(), old.resolve(strict=True), audio.resolve(strict=True), chart.resolve(strict=True)
    acceptance_screen.validate_output(output, [old, audio, chart, policy])
    # Hash/module checks happen before any new inference; no policy selection.
    frozen = acceptance_screen.load_frozen(policy, policy_sha256)
    source = original.verify_inputs(audio, chart)
    original.summarize(old, audio, chart)  # Verify all six frozen controls first.
    paths = {"guided": chart, **{kind: old / f"{kind}-input.json" for kind in original.KINDS[1:]}}
    source_hashes = {str(path): original.sha(path) for path in [audio, chart, policy, *old.glob("*.json")]}
    evidence_path = old / "nnls-evidence.json"
    packet = json.loads(evidence_path.read_text())
    nnls_chroma_adapter.validate_evidence(packet, audio)
    if packet["recording"]["id"] != original.RECORDING_ID:
        raise ValueError("Cached NNLS recording ID differs")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        shutil.copyfile(policy, stage / "frozen-policy.json")
        shutil.copyfile(evidence_path, stage / "nnls-evidence.json")
        for kind, path in paths.items():
            shutil.copyfile(path, stage / f"{kind}-input.json")
        cases = []
        signal, rate = lab.read_wav(audio)
        with acceptance_screen.cached_spectral_features(signal, rate) as feature_hash:
            for kind in original.KINDS:
                for backend in original.BACKENDS:
                    kwargs = {"evidence_json": stage / "nnls-evidence.json"} if backend == "nnls" else {}
                    destination = stage / f"{kind}-{backend}.json"
                    prediction = guarded_aligner.align_to_file(audio, stage / f"{kind}-input.json",
                        destination, **frozen["parameters"], **kwargs)
                    if prediction["recording"]["id"] != original.RECORDING_ID:
                        raise ValueError("Guarded output identity differs")
                    old_path = old / f"{kind}-{backend}.json"
                    previous = json.loads(old_path.read_text())
                    current = diagnostics(destination, prediction)
                    current["output"] = str((output / destination.name).resolve())
                    baseline = diagnostics(old_path, previous)
                    cases.append({"kind": kind, "backend": backend, "guarded": current, "old_frozen": baseline,
                        "labeled_coverage_change_percentage_points": 100 * (current["labeled_coverage_fraction"] - baseline["labeled_coverage_fraction"]),
                        "accuracy_comparison_available": False})
                    print(f"Completed {kind}/{backend}: {current['labeled_coverage_fraction']:.1%} retained, {current['silent_position_transitions']} silent advances, partial={current['partial']}", flush=True)
        if any(original.sha(Path(path)) != expected for path, expected in source_hashes.items()):
            raise ValueError("Frozen source inputs/outputs changed during diagnostic")
        report = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_at_utc": frozen["frozen_at_utc"], "frozen_policy_sha256": policy_sha256,
            "selected_policy": frozen["selected_policy"], "parameters": frozen["parameters"],
            "wrapper_sha256": original.sha(Path(__file__)), "frozen_implementation_sha256": frozen["implementation_sha256"],
            "audio_sha256": original.sha(audio), "source_chart_sha256": original.sha(chart),
            "nnls_evidence_sha256": original.sha(evidence_path), "spectral_feature_arrays_sha256": feature_hash,
            "source_hashes_unchanged": source_hashes, "cases": cases,
            "timing_reference_consumed": False, "quality_reference_consumed": False,
            "thresholds_tuned_on_wonderwall": False, "repeat_counts_changed": False,
            "accuracy_measured": False, "accepted_for_playback": False,
            "all_six_guarded_inferences_complete": len(cases) == 6,
            "no_silent_harmonic_position_progress": bool(cases) and all(case["guarded"]["silent_position_transitions"] == 0 for case in cases),
            "limitations": ["No independent recording-specific timing or rich-quality gold; coverage and completion are not correctness",
                "The teacher-section order/count remains a recording-unverified hypothesis; deliberately reversed/simplified controls remain unaccepted",
                "Active evidence dwell uses global template fit before quality masking; endpoint completion does not verify rich qualities",
                "Short/long bins and near-minimum evidence are descriptive compression warnings, not calibrated correctness gates",
                "The centered offline acoustic/added-tone windows constrain timing resolution; source separation is not used"]}
        lab.write_json(stage / "summary.json", report)
        (stage / "summary.md").write_text(markdown(report))
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during inference")
        stage.rename(output)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def markdown(report: dict) -> str:
    lines = ["# Wonderwall frozen-policy diagnostic", "",
        "Six guarded runs compare with the exact previous guided/reversed/simplified controls. No independent full-recording timing or rich-quality reference exists, so **accuracy is not measured** and no output is accepted for playback.", "",
        f"Policy `{report['selected_policy']}` was frozen at `{report['frozen_at_utc']}`, before this diagnostic; SHA-256 `{report['frozen_policy_sha256']}`. Parameters are unchanged: `{json.dumps(report['parameters'], sort_keys=True)}`.", "",
        "| Hypothesis / evidence | Old labeled coverage | Guarded labeled coverage | N seconds | X seconds / gaps | Old / guarded silent advances | Partial / unvisited | <350ms positions | Near minimum active support |", 
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for case in report["cases"]:
        new, old = case["guarded"], case["old_frozen"]
        lines.append(f"| {case['kind']} / {case['backend']} | {old['labeled_coverage_fraction']:.1%} | {new['labeled_coverage_fraction']:.1%} | {new['masked_seconds']['N']:.2f} | {new['masked_seconds']['X']:.2f} / {new['x_gap_events']} | {old['silent_position_transitions']} / {new['silent_position_transitions']} | {new['partial']} / {len(new['unvisited_sequence_indices'])} | {new['positions_below_350ms']} | {len(new['near_minimum_active_evidence_sequence_indices'] or [])} |")
    lines.extend(["", "The silent traversal bug is checked independently from rich-quality retention. Reduced coverage may remove bad chords or discard correct chords; this recording cannot distinguish them. Even a fully reached endpoint with zero silent advances does not validate the supplied section order or repeats.", "",
        "## Provenance", "", f"- Prepared audio SHA-256: `{report['audio_sha256']}`.",
        f"- Source section hypothesis SHA-256: `{report['source_chart_sha256']}`.",
        f"- Reused NNLS bytes SHA-256: `{report['nnls_evidence_sha256']}`.",
        f"- Shared frozen spectral arrays SHA-256: `{report['spectral_feature_arrays_sha256']}`.",
        f"- Wrapper SHA-256: `{report['wrapper_sha256']}`.", "- All prior JSON/audio/policy bytes rechecked after inference; no prior output is overwritten.", "",
        "## Limits", "", *["- " + item for item in report["limitations"]], "",
        "## Reproduce", "", "```sh", 
        ".venv-analysis/bin/python experiments/analysis/wonderwall_guarded.py --output experiments/generated/wonderwall-guarded-new --policy-sha256 " + report["frozen_policy_sha256"],
        "```", "", "Use a new output directory. Existing policy, old paired controls and native NNLS evidence are required; model inference, new acquisition and threshold tuning do not occur.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--policy-sha256", default=POLICY_SHA256)
    parser.add_argument("--old", type=Path, default=DEFAULT_OLD)
    parser.add_argument("--audio", type=Path, default=original.DEFAULT_AUDIO)
    parser.add_argument("--chart", type=Path, default=original.DEFAULT_CHART)
    arguments = parser.parse_args()
    try:
        report = run(arguments.output, policy=arguments.policy, policy_sha256=arguments.policy_sha256,
                     old=arguments.old, audio=arguments.audio, chart=arguments.chart)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Wonderwall guarded diagnostic failed: {error}\n")
    print(json.dumps({"output": str(arguments.output), "cases": len(report["cases"]),
                      "summary_sha256": original.sha(arguments.output / "summary.json"),
                      "accuracy_measured": False, "accepted_for_playback": False}, indent=2))


if __name__ == "__main__":
    main()
