"""Retrospective core-chord scoring of unchanged saved recognizer outputs.

Core chords are a teaching convention: omit selected extensions, never replace
a suspension by a third. Higher agreement under this easier task is not an
improvement in the detector or proof the substitute suits a particular song.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import lab
import rich_quality_screen
import rich_quality_suite

SCHEMA = "core-chord-screen-1.0"
CORE_REDUCTIONS = {"7": "", "maj7": "", "add9": "", "m7": "m", "7sus4": "sus4"}
CANDIDATES = ("crema", "chordino")
SECONDS = ("reference_harmonic_seconds", "exact_quality_correct_seconds",
    "core_quality_correct_seconds", "root_correct_seconds", "core_with_bass_correct_seconds",
    "harmonic_prediction_seconds", "unknown_seconds", "no_chord_seconds", "unsupported_seconds",
    "missing_prediction_seconds", "reference_reduced_seconds", "prediction_reduced_seconds",
    "extension_difference_ignored_seconds", "suspension_vs_third_error_seconds")


def core_semantics(label: str) -> dict:
    """Copy canonical root/quality/bass, reducing only the declared qualities.

    The source parser deliberately does not accept Harte sus4(7): 7 denotes a
    major seventh. sus4(b7) denotes the dominant seventh and is supported.
    Slash bass is retained; quality metrics may explicitly omit its comparison.
    """
    value = rich_quality_suite.chord_semantics(label)
    if value["status"] == "chord":
        value["quality"] = CORE_REDUCTIONS.get(value["quality"], value["quality"])
    return value


def core_label(label: str) -> str:
    """Display reduction preserves root spelling and explicit slash bass."""
    original = rich_quality_suite.chord_semantics(label)
    if original["status"] != "chord" or original["quality"] not in CORE_REDUCTIONS:
        return label
    match = re.fullmatch(r"([A-G][#b]?)([^/]*)(/[^/]+)?", label)
    return match[1] + CORE_REDUCTIONS[original["quality"]] + (match[3] or "")


def score(reference: dict, prediction: dict) -> dict:
    """Duration overlap on reference harmony; N, X and gaps cannot earn credit."""
    for chart in (reference, prediction):
        lab.validate_chart(chart)
    first, second = reference["recording"], prediction["recording"]
    if (first["id"], first.get("audio_sha256"), first["sample_rate_hz"]) != (
        second["id"], second.get("audio_sha256"), second["sample_rate_hz"]) or abs(
            first["duration_seconds"] - second["duration_seconds"]) > 1e-6:
        raise ValueError("Reference and prediction identify different audio")
    result = {name: 0.0 for name in SECONDS}
    for event in reference["chords"]:
        truth = rich_quality_suite.chord_semantics(event["label"])
        if truth["status"] == "no_chord":
            continue
        if truth["status"] != "chord":
            raise ValueError("Unsupported or unknown reference harmony cannot enter this screen")
        target = core_semantics(event["label"])
        duration = event["end_seconds"] - event["start_seconds"]
        result["reference_harmonic_seconds"] += duration
        if truth["quality"] != target["quality"]:
            result["reference_reduced_seconds"] += duration
        covered = 0.0
        for actual in prediction["chords"]:
            overlap = max(0.0, min(event["end_seconds"], actual["end_seconds"])
                - max(event["start_seconds"], actual["start_seconds"]))
            if not overlap:
                continue
            covered += overlap
            observed = rich_quality_suite.chord_semantics(actual["label"])
            reduced = core_semantics(actual["label"])
            status = observed["status"]
            if status != "chord":
                result[{"unknown": "unknown_seconds", "no_chord": "no_chord_seconds",
                    "unsupported": "unsupported_seconds"}[status]] += overlap
                continue
            result["harmonic_prediction_seconds"] += overlap
            exact = (truth["root"], truth["quality"]) == (observed["root"], observed["quality"])
            core = (target["root"], target["quality"]) == (reduced["root"], reduced["quality"])
            result["exact_quality_correct_seconds"] += overlap * exact
            result["core_quality_correct_seconds"] += overlap * core
            result["root_correct_seconds"] += overlap * (truth["root"] == observed["root"])
            result["core_with_bass_correct_seconds"] += overlap * (core and target["bass"] == reduced["bass"])
            result["prediction_reduced_seconds"] += overlap * (observed["quality"] != reduced["quality"])
            result["extension_difference_ignored_seconds"] += overlap * (core and not exact)
            suspension = (target["quality"] in ("sus2", "sus4")) != (reduced["quality"] in ("sus2", "sus4"))
            result["suspension_vs_third_error_seconds"] += overlap * (truth["root"] == observed["root"] and suspension
                and target["quality"] in ("", "m", "sus2", "sus4") and reduced["quality"] in ("", "m", "sus2", "sus4"))
        result["missing_prediction_seconds"] += max(0.0, duration - covered)
    total = result["reference_harmonic_seconds"]
    if total <= 0:
        raise ValueError("Reference contains no harmonic time")
    for key in ("exact_quality", "core_quality", "root", "core_with_bass"):
        result[key + "_agreement"] = result[key + "_correct_seconds"] / total
    result["harmonic_prediction_coverage"] = result["harmonic_prediction_seconds"] / total
    return result


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Cannot aggregate an empty comparison")
    values = {name: sum(row["metrics"][name] for row in rows) for name in SECONDS}
    total = values["reference_harmonic_seconds"]
    for key in ("exact_quality", "core_quality", "root", "core_with_bass"):
        values[key + "_duration_weighted_agreement"] = values[key + "_correct_seconds"] / total
        values[key + "_mean_case_agreement"] = sum(row["metrics"][key + "_agreement"] for row in rows) / len(rows)
    values["cases"] = len(rows)
    return values


def run(suite: Path, saved: Path, output: Path) -> dict:
    suite, saved, output = suite.resolve(strict=True), saved.resolve(strict=True), output.absolute()
    for source in (suite, saved):
        if output.resolve() == source or output.resolve().is_relative_to(source) or source.is_relative_to(output.resolve()):
            raise ValueError("Output must be outside source packs and their parents")
    manifest = rich_quality_screen.preflight(suite, output)
    old_report_path = saved / "report.json"
    old_report = json.loads(old_report_path.read_text())
    if old_report.get("manifest_sha256") != rich_quality_screen.sha(suite / "manifest.json"):
        raise ValueError("Saved report is for another suite manifest")
    originals = {suite / "manifest.json": rich_quality_screen.sha(suite / "manifest.json"),
        old_report_path: rich_quality_screen.sha(old_report_path)}
    for path in (Path(__file__), Path(rich_quality_suite.__file__), Path(lab.__file__), Path(rich_quality_screen.__file__)):
        originals[path] = rich_quality_screen.sha(path)
    indexed = {}
    for row in old_report["rows"]:
        if row.get("kind") == "recognition" and row.get("candidate") in CANDIDATES:
            key = row["case_id"], row["candidate"]
            if key in indexed:
                raise ValueError("Duplicate saved recognizer result")
            indexed[key] = row
    expected_keys = {(case["id"], candidate) for case in manifest["cases"] for candidate in CANDIDATES}
    if set(indexed) != expected_keys:
        raise ValueError("Saved recognizer results do not cover precisely the requested cases")
    rows = []
    for case in manifest["cases"]:
        audio = suite / case["audio"]
        reference_path = suite / case["reference"]
        originals[audio] = rich_quality_screen.sha(audio)
        originals[reference_path] = rich_quality_screen.sha(reference_path)
        originals[suite / case["untimed"]] = rich_quality_screen.sha(suite / case["untimed"])
        reference = lab.load_chart(reference_path)
        rich_quality_screen.validate_prediction(reference, case["id"], audio)
        for candidate in CANDIDATES:
            old = indexed[case["id"], candidate]
            if old["status"] != "ok":
                raise ValueError("Required raw recognizer output previously failed")
            path = (saved / old["output"]).resolve(strict=True)
            if not path.is_relative_to(saved) or rich_quality_screen.sha(path) != old["output_sha256"]:
                raise ValueError("Saved raw output bytes differ from the previous report")
            prediction = lab.load_chart(path)
            rich_quality_screen.validate_prediction(prediction, case["id"], audio)
            originals[path] = rich_quality_screen.sha(path)
            metrics = score(reference, prediction)
            if abs(metrics["exact_quality_agreement"] - old["metrics"]["exact_chord_quality_agreement"]) > 1e-8:
                raise ValueError("New exact-quality accounting differs from the original saved score")
            rows.append({"case_id": case["id"], "candidate": candidate, "family": case["family"],
                "condition": case["condition"], "split": case["split"], "reference_sha256": originals[reference_path],
                "audio_sha256": originals[audio], "raw_output": str(path.relative_to(saved)),
                "raw_output_sha256": originals[path], "metrics": metrics})
    groups = defaultdict(list)
    for row in rows:
        groups[row["candidate"]].append(row)
        for key in ("family", "condition", "split"):
            groups[f"{row['candidate']}/{key}/{row[key]}"].append(row)
    report = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrospective_diagnostic": True, "new_inference": False, "raw_outputs_modified": False,
        "timings_modified": False, "production_accuracy_established": False,
        "core_reductions": CORE_REDUCTIONS, "requested_comparisons": len(expected_keys),
        "completed_comparisons": len(rows), "manifest_sha256": originals[suite / "manifest.json"],
        "previous_report_sha256": originals[old_report_path], "rows": rows,
        "summary": {key: aggregate(group) for key, group in sorted(groups.items())},
        "input_hashes": {str(path): digest for path, digest in originals.items()},
        "metric_definition": "Equal case means and duration-weighted interval overlap on reference harmonic time; core retains root/minor/suspension distinctions. Exact/core primary metrics omit bass, with bass scored separately. N/X/gaps/unsupported predictions cannot earn quality credit.",
        "limitations": ["This easier teaching task intentionally stops assessing selected extension differences; the detector itself is unchanged.",
            "Removing chord tones is a harmonic convention, not verification of fingering difficulty, song identity or substitute suitability.",
            "D versus Dsus4 and A versus Asus4 stay different; diminished, augmented, power and undeclared qualities stay unchanged.",
            "All 24 procedural recordings were previously scored; this is not fresh validation or real-song accuracy.",
            "Suspensions may be easier shapes than their corresponding major chord. Difficulty needs actual guitar fingerings and transitions.",
            "No source separation, key assistance, alignment or boundary correction is introduced."]}
    if any(rich_quality_screen.sha(path) != digest for path, digest in originals.items()):
        raise ValueError("Source bytes changed during retrospective scoring")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        lab.write_json(stage / "report.json", report)
        (stage / "report.md").write_text(markdown(report))
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during scoring")
        stage.rename(output)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return report


def markdown(report: dict) -> str:
    lines = ["# Core-chord retrospective screen", "",
        f"{report['completed_comparisons']}/{report['requested_comparisons']} saved CREMA/Chordino outputs rescored. No new inference, relabeling of saved charts, timing changes or independent validation.", "",
        "The display rule removes selected extensions: Em7 → Em, Cadd9 → C, A7sus4 → Asus4. Suspensions remain distinct from major/minor chords. This is a simpler teaching task; higher agreement does not mean a more accurate detector.", "",
        "| Candidate / family | Cases | Exact quality | Core quality | Root | Extension differences ignored | Remaining suspension/third errors |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for key, value in report["summary"].items():
        if "/" in key and "/family/" not in key:
            continue
        lines.append(f"| {key} | {value['cases']} | {value['exact_quality_mean_case_agreement']:.1%} | {value['core_quality_mean_case_agreement']:.1%} | {value['root_mean_case_agreement']:.1%} | {value['extension_difference_ignored_seconds']:.3f}s | {value['suspension_vs_third_error_seconds']:.3f}s |")
    lines += ["", report["metric_definition"], "",
        "Additive seconds, duration-weighted rates, bass-aware rates, N/X/gap/unsupported coverage and condition/split subsets are preserved in JSON. Exact-quality accounting is checked against every original saved score, and every source hash is checked again after scoring.", "",
        "## Limits", "", *["- " + item for item in report["limitations"]], "",
        "## Reproduce", "", "```sh", ".venv-analysis/bin/python experiments/analysis/core_chord_screen.py --output experiments/generated/core-chord-screen-new", "```", "",
        "Requires the saved v2 rich-quality fixture and recognition packs; no model environment is needed. Choose a new output directory.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=lab.ROOT / "experiments/generated/rich-quality-suite-v2")
    parser.add_argument("--saved", type=Path, default=lab.ROOT / "experiments/generated/rich-quality-screen-v2")
    parser.add_argument("--output", type=Path, default=lab.ROOT / "experiments/generated/core-chord-screen-v1")
    args = parser.parse_args()
    try:
        report = run(args.suite, args.saved, args.output)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Core-chord screen failed: {error}\n")
    print(json.dumps({"output": str(args.output), "completed_comparisons": report["completed_comparisons"],
        "production_accuracy_established": False}, indent=2))


if __name__ == "__main__":
    main()
