"""Six follow-up recordings: setup-aware palette checks or descriptive riff spectra.

This adds no recogniser. It reuses frozen acoustic extraction and all twelve
uniform-shift comparisons, without coercing riff tasks into major/minor grips.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import tempfile
import time

import numpy as np

import catalogue_pitch_check as pitch

ROOT = pitch.ROOT
SCHEMA = "catalogue-remaining-pitch-check-1.0"
SPEC_SCHEMA = "catalogue-first-ten-pitch-scope-1.0"


def native_dependencies():
    assets = pitch.nnls.ROOT / "experiments/candidate-assets"
    return [assets / "nnls-chroma-evidence-native/nnls-chroma-host", assets / "nnls-chroma-evidence-native/buildinfo.json",
            assets / "chordino-native/nnls-chroma.dylib"]


def sounding_labels(shapes, shift):
    """Preserve supported suffixes; canonical sharp root spelling is descriptive."""
    pitch.palette_templates(shapes, shift)
    result = []
    for shape in shapes:
        match = re.fullmatch(r"([A-G])([#b]?)([^/]*)", shape)
        if not match:
            raise ValueError("Explicit root/quality labels without slash bass are required")
        root = (pitch.chart_aligner.ROOTS[match[1]] + {"": 0, "#": 1, "b": -1}[match[2]] + shift) % 12
        result.append(pitch.lab.NOTES[root] + match[3])
    return result


def pitch_inventory(features, duration, start=0.0, end=None):
    """Duration-weighted L2 chroma activity; neither note sequence nor key score."""
    end = duration if end is None else end
    # Reuse all finite, normalized-vector, silence, time and window guards.
    checked = pitch.score_window(features, ["C"], duration, start, end)
    starts, ends = pitch.frame_cells(features["times"], duration)
    chroma, silent = np.asarray(features["chroma"]), np.asarray(features["silent"])
    active = ~silent & (np.linalg.norm(chroma, axis=1) > 0)
    weights = np.maximum(0, np.minimum(ends, end) - np.maximum(starts, start)) * active
    seconds = checked["active_evidence_seconds"]
    mean = (np.einsum("i,ij->j", weights, chroma, optimize=False) / seconds).tolist() if seconds else None
    return {key: checked[key] for key in ("start_seconds", "end_seconds", "audio_seconds", "active_evidence_seconds", "silent_seconds", "non_silent_zero_evidence_seconds")} | {
        "pitch_classes_c_first": list(pitch.lab.NOTES), "mean_l2_chroma": mean,
        "descending_activity": sorted((({"pitch_class": name, "mean_l2_chroma": mean[i]} for i, name in enumerate(pitch.lab.NOTES)) if mean else []), key=lambda row: (-row["mean_l2_chroma"], row["pitch_class"])),
        "semantics": "Full-mix pitch-class activity only; no pitch sequence, octave, key, tuning, chord quality or attack direction is identified."}


def score_palette(features, shapes, shift, duration, start=0.0, end=None):
    result = pitch.score_window(features, shapes, duration, start, end)
    expected = next((row["mean_nearest_palette_cosine"] for row in result["shift_ranking"] if row["shift_semitones"] == shift), None)
    result.update(expected_sounding_shift_semitones=shift, expected_shift_cosine=expected,
                  best_minus_expected_score=result["shift_ranking"][0]["mean_nearest_palette_cosine"] - expected if expected is not None else None)
    return result


def native_inventory(chart):
    pitch.lab.validate_chart(chart)
    duration = chart["recording"]["duration_seconds"]
    if any(event["end_seconds"] > duration for event in chart["chords"]):
        raise ValueError("Native intervals must remain within the recording")
    labels = {}
    for event in chart["chords"]:
        label = event["label"]
        labels[label] = labels.get(label, 0.0) + event["end_seconds"] - event["start_seconds"]
    return {"labels": [{"label": label, "seconds": seconds} for label, seconds in sorted(labels.items(), key=lambda item: (-item[1], item[0]))],
            "uncovered_seconds": max(0.0, duration - sum(labels.values())),
            "semantics": "Unmodified native detector labels; a major/minor output over riff material does not establish an instructed grip."}


def preflight(pack, spec, output, root=ROOT):
    pack, spec, root = pack.resolve(strict=True), spec.resolve(strict=True), root.resolve()
    output = output.absolute()
    if not all(path.is_relative_to(root) for path in (pack, spec, output.resolve())):
        raise ValueError("Keep diagnostics inside the repository")
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(pack) or pack.is_relative_to(output.resolve()):
        raise ValueError("Use an unused separate output directory")
    files, manifest = pitch.curation.public_files(pack)
    config = pitch.curation.read(spec)
    if config.get("schema_version") != SPEC_SCHEMA or config.get("policy") != pitch.POLICY or config.get("pack_manifest_sha256") != pitch.drafts.digest(pack / "manifest.json"):
        raise ValueError("Diagnostic policy or exact input pack changed")
    profiles = config.get("cases")
    if not isinstance(profiles, list) or any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in profiles):
        raise ValueError("Explicit case profiles are required")
    profiles_by_id = {row["id"]: row for row in profiles}
    cases = {row["id"]: row for row in manifest["cases"]}
    if len(profiles_by_id) != len(profiles) or set(profiles_by_id) != set(cases):
        raise ValueError("Scope must account for every exact case once")
    selected = config.get("selected_case_ids")
    if not isinstance(selected, list) or not selected or any(not isinstance(item, str) for item in selected) or len(set(selected)) != len(selected) or not set(selected) <= set(cases):
        raise ValueError("Select explicit unique recordings")
    originals = {path: pitch.drafts.digest(path) for path in files.values()}
    originals[spec] = pitch.drafts.digest(spec)
    jobs = []
    for identifier, profile in profiles_by_id.items():
        case = cases[identifier]; folder = pack / "cases" / identifier
        review = pitch.curation.read(folder / "review.json")
        context = review["source_context"]
        if (profile.get("review_sha256") != pitch.drafts.digest(folder / "review.json") or profile.get("recording") != case["recording"]
                or profile.get("shape_palette") != context["entry_shapes"] or profile.get("source_setup") != context["setup"]):
            raise ValueError("Source context or exact recording changed")
        shapes, shift = profile["shape_palette"], profile.get("expected_sounding_shift_semitones")
        if shapes is None:
            if profile.get("analysis_kind") != "riff-pitch-class-inventory" or shift is not None:
                raise ValueError("Riff material must remain without an invented harmonic palette")
        else:
            pitch.palette_templates(shapes, shift)
            if profile.get("analysis_kind") != "source-palette-compatibility":
                raise ValueError("Use explicit palette compatibility for harmonic profiles")
        fixed = [row for row in review["points"] if row["kind"] == "coverage-sample"]
        if profile.get("fixed_samples") != len(fixed):
            raise ValueError("Retain the fixed coverage sample policy")
        historical = profile.get("historical_evidence")
        if historical:
            path = root / historical["path"]
            if not path.resolve(strict=True).is_relative_to(root) or pitch.drafts.digest(path) != historical["sha256"]:
                raise ValueError("Historical evidence changed")
            originals[path] = pitch.drafts.digest(path)
        if identifier in selected:
            jobs.append((case, folder, review, profile))
    private = pack / "private-drafts"
    if private.exists():
        if private.is_symlink(): raise ValueError("Do not follow private draft aliases")
        for path in private.glob("*.json"):
            if path.is_symlink(): raise ValueError("Do not follow private draft aliases")
            originals[path] = pitch.drafts.digest(path)
    return manifest, config, jobs, originals


def run(pack, spec, output, root=ROOT):
    pack, spec = pack.resolve(strict=True), spec.resolve(strict=True)
    manifest, config, jobs, originals = preflight(pack, spec, output, root)
    dependencies = [Path(__file__), Path(pitch.__file__), Path(pitch.chart_aligner.__file__), Path(pitch.nnls.__file__),
                    Path(pitch.curation.__file__), Path(pitch.lab.__file__), Path(pitch.core_semantics.__code__.co_filename),
                    Path(pitch.rich_quality_suite.__file__), Path(pitch.drafts.__file__), Path(pitch.curation.review_pack.__file__),
                    Path(pitch.nnls.__file__).with_name("nnls-chroma-host.cpp")]
    pins = {str(path.relative_to(root)) if path.is_relative_to(root) else str(path): pitch.drafts.digest(path) for path in dependencies}
    native_paths = native_dependencies()
    native_pins = {str(path.relative_to(root)) if path.is_relative_to(root) else str(path): pitch.drafts.digest(path) for path in native_paths}
    originals.update({path: pitch.drafts.digest(path) for path in dependencies + native_paths})
    output = output.absolute(); output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".remaining-pitch-", dir=output.parent))
    started = time.perf_counter(); rows = []
    try:
        for case, folder, review, profile in jobs:
            case_started = time.perf_counter(); identifier = case["id"]; duration = case["recording"]["duration_seconds"]
            destination = staging / identifier; destination.mkdir()
            evidence = pitch.nnls.extract(folder / "audio.wav", identifier)
            pitch.nnls.validate_evidence(evidence, folder / "audio.wav")
            if not pitch.curation.identity(evidence["recording"], case["recording"]): raise ValueError("Evidence identity changed")
            pitch.drafts.write_json(destination / "nnls-evidence.json", evidence)
            methods = {"spectral": pitch.features_from_spectral(folder / "audio.wav"), "nnls": pitch.features_from_nnls(evidence)}
            windows = [(float(start), min(duration, float(start) + pitch.POLICY["window_seconds"])) for start in np.arange(0, duration, pitch.POLICY["window_seconds"])]
            fixed = [point for point in review["points"] if point["kind"] == "coverage-sample"]
            shapes, shift = profile["shape_palette"], profile["expected_sounding_shift_semitones"]
            charts = {name: pitch.curation.read(folder / filename) for name, filename in (("btc", "primary.json"), ("crema", "crema.json"))}
            checks = {}
            for name, features in methods.items():
                scorer = (lambda first, last: score_palette(features, shapes, shift, duration, first, last)) if shapes is not None else (lambda first, last: pitch_inventory(features, duration, first, last))
                checks[name] = {"parameters": features["parameters"], "full_recording": scorer(0, duration),
                                "fixed_coverage_samples": [{"id": point["id"], **scorer(point["start_seconds"], point["end_seconds"])} for point in fixed],
                                "all_20_second_windows": [scorer(first, last) for first, last in windows]}
            memberships = {name: pitch.model_palette(chart, shapes, shift) for name, chart in charts.items()} if shapes is not None else None
            cues = {name: pitch.cue_diagnostics(chart, memberships[name], methods, sounding_labels(shapes, shift)) for name, chart in charts.items()} if shapes is not None else None
            row = {"id": identifier, "title": case["name"], "recording": case["recording"], "profile": profile,
                   "native_artifacts": case["artifacts"], "nnls_evidence_sha256": pitch.drafts.digest(destination / "nnls-evidence.json"),
                   "analysis_runtime_seconds": time.perf_counter() - case_started, "acoustic_compatibility" if shapes is not None else "pitch_class_activity": checks,
                   "sounding_palette_proposal": sounding_labels(shapes, shift) if shapes is not None else None,
                   "native_model_palette_membership": memberships, "retrospective_cue_audit": cues,
                   "native_model_inventory": {name: native_inventory(chart) for name, chart in charts.items()},
                   "exact_setup_verified": False, "accepted_arrangement": False, "accuracy_score": None, "human_correction_seconds": None}
            pitch.drafts.write_json(destination / "report.json", row); rows.append(row)
            print(f"Checked {len(rows)}/{len(jobs)}: {case['name']}", flush=True)
        private = pack / "private-drafts"
        previous_drafts = {path for path in originals if path.parent == private}
        current_drafts = set(private.glob("*.json")) if private.exists() else set()
        if private.is_symlink() or previous_drafts != current_drafts or any(not path.exists() or pitch.drafts.digest(path) != digest for path, digest in originals.items()):
            raise ValueError("Inputs or saved private drafts changed during diagnostic")
        report = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "Six follow-up diagnostic cases; no arrangements accepted",
                  "gold": False, "policy": pitch.POLICY, "spec_sha256": pitch.drafts.digest(spec), "pack_manifest_sha256": pitch.drafts.digest(pack / "manifest.json"),
                  "method_code_sha256": pins, "native_assets_sha256": native_pins,
                  "native_build_provenance": "Each saved NNLS evidence analysis.build records source revisions and binary hashes; nnls.extract validates those against actual host, plugin and host source. These native asset snapshots additionally remain unchanged through publication.",
                  "completed_cases": len(rows), "runtime_seconds": time.perf_counter() - started,
                  "raw_inputs_modified": False, "private_drafts_modified": False, "human_correction_seconds": None,
                  "limits": ["Cosine compatibility and model palette membership are not calibrated confidence or accuracy.",
                             "Teacher shape-to-sounding mappings remain proposals, not physical capo/tuning/voicing recognition.",
                             "All twelve relative shifts remain visible; the expected shift never relabels native charts.",
                             "No triad palette or shift winner is imposed on riff tasks; descriptive full-mix chroma cannot recover note sequences or articulation.",
                             "No physical chord-change timing, section extent, stroke direction, muting or whole-song strumming is accepted.",
                             "NNLS global tuning compensation prevents any concert-pitch or cents claim."], "cases": rows}
        pitch.drafts.write_json(staging / "report.json", report); staging.rename(output)
        return report
    except Exception:
        shutil.rmtree(staging); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=pitch.DEFAULT_PACK)
    parser.add_argument("--spec", type=Path, default=ROOT / "experiments/fixtures/catalogue-first-ten-pitch-v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pack, args.spec, args.output)
    print({"completed_cases": result["completed_cases"], "runtime_seconds": result["runtime_seconds"]})


if __name__ == "__main__": main()
