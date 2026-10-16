"""Retrospective structure diagnostic on existing section-repeat controls.

No inference, reference timing, policy selection or threshold fitting occurs.
The chart-independent global argmax must be identical across each recording's
controls. A correct chart can lose to a wrong one; that is reported, not tuned.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

import arrangement_diagnostic as diagnostic
import core_chord_screen
import lab

CONTROLS = ("correct", "missing_repeat", "extra_repeat", "wrong_section_order")
KINDS = ("guided", "reversed-order", "simplified-quality")


def protected_file(root: Path, relative: str, expected: str | None = None) -> Path:
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Cached input must be a file within its pack")
    if expected is not None and diagnostic.sha(path) != expected:
        raise ValueError("Cached input bytes differ from original report")
    return path


def summary_row(row: dict, result: dict) -> dict:
    comparison, coverage = result["comparison"], result["comparison"]["coverage"]
    return {**row, "mechanical_failure": result["mechanical_status"]["failed"],
        "mechanical_flags": result["mechanical_status"]["flags"],
        "mechanical_check_available": result["source_kind"] == "guarded-global-argmax",
        "raw": {key: value for key, value in comparison["raw"].items() if key != "trace"},
        "stable": {key: value for key, value in comparison["stable"].items() if key != "trace"},
        "coverage": coverage, "chart_coverage": comparison["chart_coverage"],
        "accepted_for_playback": False, "accuracy_measured": False}


def run(output: Path, validation: Path, wonderwall: Path, song: Path) -> dict:
    sources = [root.resolve(strict=True) for root in (validation, wonderwall, song)]
    validation, wonderwall, song = sources
    output = output.absolute()
    if output.exists() or output.is_symlink() or any(output.resolve().is_relative_to(source) or
        source.is_relative_to(output.resolve()) for source in sources):
        raise ValueError("Choose a fresh output directory outside source packs and their parents")
    originals = {}
    def read(path: Path):
        originals[path] = diagnostic.sha(path)
        return json.loads(path.read_text())
    for path in (Path(__file__), Path(diagnostic.__file__), Path(core_chord_screen.__file__)):
        originals[path] = diagnostic.sha(path)
    prior = read(validation / "report.json")
    full_prior = read(wonderwall / "summary.json")
    rows = [row for row in prior["rows"] if row["dataset"] == "fresh-validation" and
        row["family"] == "section_repeat" and row["policy"] == prior["selected_policy"] and
        row["backend"] == "nnls-chroma" and row["control"] in CONTROLS]
    if len(rows) != 16 or len({(row['case_id'], row['control']) for row in rows}) != 16:
        raise ValueError("Expected four section recordings with all four declared controls")
    recording_ids = sorted({row["case_id"] for row in rows})
    if len(recording_ids) != 4 or any({row["control"] for row in rows if row["case_id"] == identity} != set(CONTROLS)
            for identity in recording_ids):
        raise ValueError("Section control matrix is incomplete")
    full_cases = {(row["kind"], row["backend"]): row for row in full_prior["cases"]}
    if any((kind, "nnls") not in full_cases for kind in KINDS):
        raise ValueError("Full-song NNLS controls are incomplete")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        outcomes, acoustic = [], {}
        for row in rows:
            if row["status"] != "ok":
                raise ValueError("Required prior control failed")
            path = protected_file(validation, row["output"], row["output_sha256"])
            chart_path = protected_file(path.parent, row["control"] + "-untimed.json", row["chart_sha256"])
            result, chart = read(path), read(chart_path)
            events = diagnostic.events_from_guarded(result)
            if row["case_id"] in acoustic and acoustic[row["case_id"]] != events:
                raise ValueError("Global argmax was changed by supplied chart control")
            acoustic[row["case_id"]] = events
            measured = diagnostic.diagnose(result, chart)
            name = f"section/{row['case_id']}/{row['control']}.json"
            lab.write_json(stage / name, measured)
            outcomes.append(summary_row({"dataset": "previously-exposed-synthetic-sections", "case_id": row["case_id"],
                "control": row["control"], "source_kind": "guarded-global-argmax", "output": name,
                "output_sha256": diagnostic.sha(stage / name), "input_sha256": originals[path],
                "chart_sha256": originals[chart_path]}, measured))
        raw_predictions = {candidate: read(protected_file(song, candidate + ".json")) for candidate in ("crema", "chordino")}
        full_events = None
        for kind in KINDS:
            prior_case = full_cases[kind, "nnls"]
            path = protected_file(wonderwall, f"{kind}-nnls.json", prior_case["guarded"]["output_sha256"])
            chart_path = protected_file(wonderwall, f"{kind}-input.json", prior_case["guarded"]["input_chart_sha256"])
            result, chart = read(path), read(chart_path)
            events = diagnostic.events_from_guarded(result)
            if full_events is not None and full_events != events:
                raise ValueError("Full-song global argmax was changed by the chart")
            full_events = events
            for source_kind, source in [("global-argmax", result), *raw_predictions.items()]:
                measured = diagnostic.diagnose(source, chart, source_kind=("guarded-global-argmax" if source_kind == "global-argmax" else "raw-recognizer"))
                name = f"wonderwall/{kind}-{source_kind}.json"
                lab.write_json(stage / name, measured)
                outcomes.append(summary_row({"dataset": "wonderwall-no-gold", "case_id": result["recording"]["id"],
                    "control": kind, "source_kind": source_kind, "output": name,
                    "output_sha256": diagnostic.sha(stage / name), "chart_sha256": originals[chart_path],
                    "input_sha256": originals[path] if source_kind == "global-argmax" else originals[song / f"{source_kind}.json"]}, measured))
        rankings = []
        for identity in recording_ids:
            subset = [row for row in outcomes if row["case_id"] == identity]
            correct = next(row for row in subset if row["control"] == "correct")
            for view in ("raw", "stable"):
                distance = correct[view]["edit_distance"]
                alternatives = {row["control"]: row[view]["edit_distance"] for row in subset if row["control"] != "correct"}
                rankings.append({"case_id": identity, "view": view, "correct_edit_distance": distance,
                    "alternative_edit_distances": alternatives, "correct_strictly_lowest": all(distance < value for value in alternatives.values()),
                    "wrong_controls_with_lower_distance": [name for name, value in alternatives.items() if value < distance],
                    "wrong_controls_with_equal_distance": [name for name, value in alternatives.items() if value == distance]})
        report = {"schema_version": "arrangement-screen-1.0", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "completed_comparisons": len(outcomes), "requested_comparisons": 25, "rows": outcomes,
            "synthetic_rankings": rankings, "global_argmax_identical_across_controls": True,
            "parameters": {"stable_run_seconds": diagnostic.STABLE_RUN_SECONDS, "core_reductions": core_chord_screen.CORE_REDUCTIONS,
                "acceptance_score_threshold": None, "parameters_fitted_on_this_screen": False},
            "input_hashes": {str(path): digest for path, digest in originals.items()},
            "new_inference": False, "retrospective_diagnostic": True, "timing_reference_consumed": False,
            "production_accuracy_established": False, "accepted_for_playback": False,
            "limitations": ["Four procedural section recordings and Wonderwall were already exposed; this is a diagnostic, not fresh validation.",
                "Global argmax is independent of supplied chart order but uses the same chroma/templates; CREMA/Chordino are additional imperfect evidence, not gold.",
                "Unit-cost edit distance favors fewer edits, not verified arrangements; a wrong control can rank best. No threshold or filter is fitted here.",
                "Stable view discards runs below the declared 150ms without relabeling, bridging gaps or merging across discarded runs; real fast changes may be lost.",
                "Silence, unknown and unsupported intervals are excluded from harmonic comparison with duration coverage retained; confidence and correctness cannot follow from agreement.",
                "Bass and removed extensions are not verified; adjacent identical core positions cannot supply a repeat count.",
                "Mechanical failures make the constrained path incomplete. Mechanical success never approves playback.",
                "The full Wonderwall chart is a teacher-based, version-unverified section/count hypothesis with no timing reference."]}
        if len(outcomes) != report["requested_comparisons"]:
            raise ValueError("Diagnostic outcome matrix is incomplete")
        if any(diagnostic.sha(path) != digest for path, digest in originals.items()):
            raise ValueError("Source bytes changed during diagnostic")
        lab.write_json(stage / "report.json", report)
        (stage / "report.md").write_text(markdown(report))
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during diagnostic")
        stage.rename(output)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def markdown(report: dict) -> str:
    lines = ["# Arrangement sequence diagnostic", "", f"{report['completed_comparisons']}/{report['requested_comparisons']} cached comparisons completed. No chart is approved for playback.", "",
        "The unrestricted acoustic chord sequence receives no chart order or repeat counts. Its global argmax is verified identical across each recording's controls. The stable view deletes runs shorter than 150ms; it never replaces labels or fills gaps. These are descriptive comparisons, not calibrated acceptance.", "",
        "| Recording / chart | Source | Stable runs / chart runs | Raw / stable edits | Stable audio coverage | Matched stable duration | Mechanical failure |",
        "|---|---|---:|---:|---:|---:|---|"]
    for row in report["rows"]:
        stable, coverage = row["stable"], row["coverage"]
        matched = stable["matched_fraction_of_observed_harmonic_seconds"]
        mechanical = str(row['mechanical_failure']) if row['mechanical_check_available'] else "—"
        lines.append(f"| {row['case_id']} / {row['control']} | {row['source_kind']} | {stable['observed_run_count']} / {stable['chart_run_count']} | {row['raw']['edit_distance']} / {stable['edit_distance']} | {coverage['stable_fraction_of_audio']:.1%} | {matched:.1%} | {mechanical} |" if matched is not None else
            f"| {row['case_id']} / {row['control']} | {row['source_kind']} | {stable['observed_run_count']} / {stable['chart_run_count']} | {row['raw']['edit_distance']} / {stable['edit_distance']} | {coverage['stable_fraction_of_audio']:.1%} | — | {mechanical} |")
    lines += ["", "## Synthetic ranking check", ""]
    for view in ("raw", "stable"):
        subset = [row for row in report["synthetic_rankings"] if row["view"] == view]
        lines.append(f"- {view}: correct chart strictly has fewer edits than all three corrupt controls in {sum(row['correct_strictly_lowest'] for row in subset)}/{len(subset)} recordings; {sum(bool(row['wrong_controls_with_lower_distance']) for row in subset)} recordings have a wrong control with fewer edits, and {sum(bool(row['wrong_controls_with_equal_distance']) for row in subset)} have ties.")
    lines += ["", "Lower edit distance and a mechanically complete path do not identify a correct chart. No score threshold is selected, and the raw/stable outcomes both remain in the report. A dash denotes no constrained-path mechanical check for a raw recognizer. Full edit traces, ignored duration and indistinguishable chart positions are saved in each diagnostic beside the summary, with hashes in the committed compact JSON.", "",
        "## Limits", "", *["- " + item for item in report["limitations"]], "",
        "## Reproduce", "", "```sh", ".venv-analysis/bin/python experiments/analysis/arrangement_screen.py --output experiments/generated/arrangement-screen-new", "```", "",
        "Uses the saved acceptance-validation, verified Wonderwall guard and original song detector packs. Choose a new directory; no models, acquisition, reference editing or founder transcription are required.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=lab.ROOT / "experiments/generated/arrangement-screen-v2")
    parser.add_argument("--validation", type=Path, default=lab.ROOT / "experiments/generated/acceptance-validation-screen-v1")
    parser.add_argument("--wonderwall", type=Path, default=lab.ROOT / "experiments/generated/wonderwall-guarded-verified-20261011")
    parser.add_argument("--song", type=Path, default=lab.ROOT / "experiments/generated/youtube-pilot/cases/oasis-wonderwall-youtube-20261010")
    args = parser.parse_args()
    try:
        report = run(args.output, args.validation, args.wonderwall, args.song)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Arrangement screen failed: {error}\n")
    print(json.dumps({"output": str(args.output), "completed_comparisons": report["completed_comparisons"], "accepted_for_playback": False}, indent=2))


if __name__ == '__main__':
    main()
