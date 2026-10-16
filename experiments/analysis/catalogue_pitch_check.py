"""Bounded source-palette compatibility, never setup recognition or acceptance.

All pitch shifts and full recording/windows are reported. No source chord
order, reference timings or saved corrections enter extraction or scoring.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np

import automatic_drafts as drafts
import chart_aligner
from core_chord_screen import core_semantics
import curation
import lab
import rich_quality_suite
sys.path.insert(0, str(Path(__file__).resolve().parent / "candidates"))
import nnls_chroma_adapter as nnls

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "catalogue-palette-check-1.0"
VERSION = "0.1.0"
POLICY = {"shifts_semitones": list(range(12)), "spectral_hop_seconds": 0.05,
          "spectral_window_seconds": 0.18, "window_seconds": 20.0,
          "tie_tolerance": 1e-12, "max_outside_examples_per_model": 8,
          "template": "equal pitch-class weights, L2-normalized; slash bass omitted",
          "score": "duration-weighted nearest source-palette cosine on non-silent, nonzero frames",
          "frame_duration": "cells split at adjacent feature-center midpoints, bounded to audio",
          "acceptance_threshold": None, "automatic_corrections": False,
          "tuning_cents_estimation": False, "physical_capo_recognition": False}
DEFAULT_SPEC = ROOT / "experiments/fixtures/catalogue-starter-four-v1.json"
DEFAULT_PACK = ROOT / "experiments/generated/catalogue-curation-20261014"


def palette_templates(shapes, shift=0):
    if (not isinstance(shapes, list) or not 1 <= len(shapes) <= 12
            or any(not isinstance(value, str) for value in shapes) or len(set(shapes)) != len(shapes)
            or isinstance(shift, bool) or not isinstance(shift, int) or shift not in range(12)):
        raise ValueError("Use a small explicit palette and uniform pitch shift")
    templates = [chart_aligner.chord_template(label) for label in shapes]
    if any(value is None for value in templates):
        raise ValueError("Source palette must contain harmonic chords")
    return np.array([np.roll(value, shift) for value in templates])


def frame_cells(times, duration):
    times = np.asarray(times, dtype=float)
    if (not curation.number(duration) or duration <= 0 or times.ndim != 1 or not len(times)
            or not np.all(np.isfinite(times)) or times[0] < 0 or times[-1] >= duration
            or np.any(np.diff(times) <= 0)):
        raise ValueError("Feature centers must be finite, increasing and inside audio")
    edges = np.concatenate(([0.0], (times[:-1] + times[1:]) / 2, [duration]))
    return edges[:-1], edges[1:]


def features_from_spectral(audio):
    signal, rate = lab.read_wav(audio)
    value = chart_aligner.features(signal, rate, POLICY["spectral_hop_seconds"], POLICY["spectral_window_seconds"])
    return {"times": np.arange(len(value["chroma"])) * value["hop_samples"] / rate,
            "chroma": value["chroma"], "silent": value["silent"],
            "method": "existing spectral chroma", "parameters": {key: value[key] for key in ("hop_samples", "frame_size", "silence_rms_threshold")}}


def features_from_nnls(evidence):
    nnls.validate_evidence(evidence)
    return {"times": np.asarray(evidence["times_seconds"]), "chroma": np.asarray(evidence["chroma_c_first"]),
            "silent": np.asarray(evidence["silent"], dtype=bool), "method": "frozen NNLS-Chroma",
            "parameters": {"hop_samples": 2048, "frame_size": 16384, "global_tuning_compensation": True,
                           "evidence_analysis_id": evidence["analysis"]["id"]}}


def score_window(features, shapes, duration, start=0.0, end=None):
    end = duration if end is None else end
    if not all(curation.number(value) for value in (start, end)) or not 0 <= start < end <= duration:
        raise ValueError("Window must be inside the exact recording")
    starts, ends = frame_cells(features["times"], duration)
    chroma, silent = np.asarray(features["chroma"], dtype=float), np.asarray(features["silent"])
    if (chroma.shape != (len(starts), 12) or silent.shape != starts.shape or silent.dtype != bool
            or not np.all(np.isfinite(chroma)) or np.any(chroma < 0)):
        raise ValueError("Use finite nonnegative C-first chroma and boolean silence")
    norms = np.linalg.norm(chroma, axis=1)
    if np.any((norms != 0) & ~np.isclose(norms, 1, rtol=0, atol=1e-8)):
        raise ValueError("Feature vectors must be zero or L2-normalized")
    weights = np.maximum(0, np.minimum(ends, end) - np.maximum(starts, start))
    active = ~silent & (norms > 0)
    active_weights = weights * active
    active_seconds = float(active_weights.sum())
    result = {"start_seconds": start, "end_seconds": end, "audio_seconds": end - start,
              "active_evidence_seconds": active_seconds,
              "silent_seconds": float(weights[silent].sum()),
              "non_silent_zero_evidence_seconds": float(weights[~silent & (norms == 0)].sum()),
              "shift_ranking": [], "best_shifts_semitones": [], "best_minus_next_distinct_score": None,
              "unrestricted_24_triad_cosine": None, "proposed_zero_shift_cosine": None,
              "unrestricted_minus_zero_shift": None}
    templates = palette_templates(shapes)
    if active_seconds <= 0:
        return result
    all_triads = np.array([chart_aligner.chord_template(name + suffix) for name in lab.NOTES for suffix in ("", "m")])
    # Explicit 12-bin sums avoid platform BLAS floating-status warnings on
    # bounded normalized vectors; no warning suppression or score clamping.
    unrestricted = float(np.sum(active_weights * np.einsum("ij,kj->ik", chroma, all_triads, optimize=False).max(axis=1)) / active_seconds)
    ranking = []
    for shift in POLICY["shifts_semitones"]:
        similarities = np.einsum("ij,kj->ik", chroma, np.roll(templates, shift, axis=1), optimize=False).max(axis=1)
        mean = float(np.sum(active_weights * similarities) / active_seconds)
        ranking.append({"shift_semitones": shift, "mean_nearest_palette_cosine": mean})
    ranking.sort(key=lambda item: (-item["mean_nearest_palette_cosine"], item["shift_semitones"]))
    best = ranking[0]["mean_nearest_palette_cosine"]
    ties = [item["shift_semitones"] for item in ranking if best - item["mean_nearest_palette_cosine"] <= POLICY["tie_tolerance"]]
    next_distinct = next((item["mean_nearest_palette_cosine"] for item in ranking if item["shift_semitones"] not in ties), None)
    zero = next(item["mean_nearest_palette_cosine"] for item in ranking if item["shift_semitones"] == 0)
    result.update(shift_ranking=ranking, best_shifts_semitones=ties,
                  best_minus_next_distinct_score=best - next_distinct if next_distinct is not None else None,
                  unrestricted_24_triad_cosine=unrestricted, proposed_zero_shift_cosine=zero,
                  unrestricted_minus_zero_shift=unrestricted - zero)
    return result


def model_palette(chart, shapes, shift=0):
    """Major/minor/core family membership; never a correctness denominator."""
    lab.validate_chart(chart)
    duration = chart["recording"]["duration_seconds"]
    if any(event["end_seconds"] > duration for event in chart["chords"]):
        raise ValueError("Native palette ledger cannot extend beyond audio")
    palette_templates(shapes, shift)
    keys = set()
    for shape in shapes:
        value = core_semantics(shape)
        keys.add(((value["root"] + shift) % 12, value["quality"]))
    ledger = {key: 0.0 for key in ("in_palette_seconds", "outside_palette_seconds", "no_chord_seconds", "unknown_seconds", "unsupported_seconds", "uncovered_seconds", "extension_reduced_seconds", "explicit_slash_bass_seconds")}
    outside = []
    for event in chart["chords"]:
        seconds = event["end_seconds"] - event["start_seconds"]
        value = core_semantics(event["label"])
        if value["status"] == "chord":
            membership = (value["root"], value["quality"]) in keys
            ledger["in_palette_seconds" if membership else "outside_palette_seconds"] += seconds
            if not membership: outside.append(dict(event))
            original = rich_quality_suite.chord_semantics(event["label"])
            ledger["extension_reduced_seconds"] += seconds * (original["quality"] != value["quality"])
            ledger["explicit_slash_bass_seconds"] += seconds * ("/" in event["label"])
        else:
            ledger[{"no_chord": "no_chord_seconds", "unknown": "unknown_seconds", "unsupported": "unsupported_seconds"}[value["status"]]] += seconds
    ledger["uncovered_seconds"] = max(0.0, duration - sum(event["end_seconds"] - event["start_seconds"] for event in chart["chords"]))
    eligible = ledger["in_palette_seconds"] + ledger["outside_palette_seconds"]
    return {"ledger": ledger, "harmonic_family_seconds": eligible,
            "fraction_of_harmonic_families_in_palette": ledger["in_palette_seconds"] / eligible if eligible else None,
            "outside_palette_intervals": len(outside), "outside_examples": sorted(outside, key=lambda item: (-(item["end_seconds"] - item["start_seconds"]), item["start_seconds"]))[:POLICY["max_outside_examples_per_model"]],
            "semantics": "Core family membership ignores inversion and selected extensions; no reference harmony is present. Unsupported qualities, N/X and gaps remain separate."}


def cue_diagnostics(chart, membership, methods, shapes):
    """Retrospective cues only; native span bounds are not physical truth."""
    duration = chart["recording"]["duration_seconds"]
    chunk = chart["analysis"].get("parameters", {}).get("chunk_seconds")
    boundaries = np.arange(chunk, duration, chunk) if curation.number(chunk) and chunk > 0 else []
    rows = []
    for event in membership["outside_examples"]:
        midpoint = (event["start_seconds"] + event["end_seconds"]) / 2
        nearest = float(min(boundaries, key=lambda value: abs(value - midpoint))) if len(boundaries) else None
        acoustic = {}
        try:
            palette_templates([event["label"]])
            raw_template_supported = True
        except ValueError:
            raw_template_supported = False
        for name, features in methods.items():
            palette = score_window(features, shapes, duration, event["start_seconds"], event["end_seconds"])
            native = score_window(features, [event["label"]], duration, event["start_seconds"], event["end_seconds"]) if raw_template_supported else None
            acoustic[name] = {"active_evidence_seconds": palette["active_evidence_seconds"],
                              "source_palette_zero_shift_cosine": palette["proposed_zero_shift_cosine"],
                              "raw_label_cosine": native["proposed_zero_shift_cosine"] if native else None,
                              "raw_template_status": "supported" if native else "unsupported; native quality retained without coercion",
                              "source_minus_raw_cosine": (palette["proposed_zero_shift_cosine"] - native["proposed_zero_shift_cosine"])
                              if native and palette["active_evidence_seconds"] else None}
        rows.append({"native_event": event, "replay_start_seconds": max(0.0, midpoint - 3),
                     "replay_end_seconds": min(duration, midpoint + 3),
                     "nearest_internal_chunk_boundary_seconds": nearest,
                     "midpoint_distance_to_chunk_boundary_seconds": abs(midpoint - nearest) if nearest is not None else None,
                     "acoustic_comparison": acoustic})
    return {"selection": "up to eight longest native out-of-main-palette intervals; retrospective descriptive comparison",
            "semantics": "Source palettes can omit valid contrast, and wide acoustic windows mix changes. These differences neither prove an error nor supply corrected labels/timings.",
            "chunk_seconds": chunk, "cues": rows}


def preflight(pack, spec, output, root=ROOT):
    pack, spec, output, root = pack.resolve(strict=True), spec.resolve(strict=True), output.absolute(), root.resolve()
    if not pack.is_relative_to(root) or not spec.is_relative_to(root) or not output.resolve().is_relative_to(root):
        raise ValueError("Keep the palette diagnostic inside the repository")
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(pack) or pack.is_relative_to(output.resolve()):
        raise ValueError("Use an unused, separate output directory")
    files, manifest = curation.public_files(pack)
    config = curation.read(spec)
    if config.get("schema_version") != "catalogue-starter-palette-spec-1.0" or config.get("policy") != POLICY or config.get("pack_manifest_sha256") != drafts.digest(pack / "manifest.json"):
        raise ValueError("Diagnostic policy/input pack differs from the frozen specification")
    case_ids = config.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids or len(set(case_ids)) != len(case_ids):
        raise ValueError("Explicit unique recording IDs are required")
    if not isinstance(config.get("review_sha256"), dict) or set(config["review_sha256"]) != set(case_ids):
        raise ValueError("Pin every selected source context")
    cases = {case["id"]: case for case in manifest["cases"]}
    jobs, originals = [], {path: drafts.digest(path) for path in files.values()}
    originals[spec] = drafts.digest(spec)
    for identifier in case_ids:
        if identifier not in cases: raise ValueError("Recording absent from pinned pack")
        case = cases[identifier]; folder = pack / "cases" / identifier
        if drafts.digest(folder / "review.json") != config["review_sha256"][identifier]:
            raise ValueError("Source context differs from the frozen specification")
        review = curation.read(folder / "review.json")
        shapes = review["source_context"]["entry_shapes"]
        palette_templates(shapes)
        jobs.append((case, folder, review))
    private = pack / "private-drafts"
    if private.exists():
        if private.is_symlink(): raise ValueError("Do not follow private draft aliases")
        for path in private.glob("*.json"):
            if path.is_symlink(): raise ValueError("Do not follow private draft aliases")
            originals[path] = drafts.digest(path)
    return manifest, config, jobs, originals


def run(pack, spec, output, root=ROOT):
    pack, spec = pack.resolve(strict=True), spec.resolve(strict=True)
    manifest, config, jobs, originals = preflight(pack, spec, output, root)
    module_sha256 = drafts.digest(Path(__file__))
    output = output.absolute(); output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".palette-", dir=output.parent))
    started = time.perf_counter(); rows = []
    try:
        for case, folder, review in jobs:
            audio = folder / "audio.wav"; identifier = case["id"]
            case_folder = staging / identifier; case_folder.mkdir()
            extraction_started = time.perf_counter()
            evidence = nnls.extract(audio, identifier)
            nnls.validate_evidence(evidence, audio)
            if not curation.identity(evidence["recording"], case["recording"]): raise ValueError("Evidence belongs to other audio")
            drafts.write_json(case_folder / "nnls-evidence.json", evidence)
            methods = {"spectral": features_from_spectral(audio), "nnls": features_from_nnls(evidence)}
            duration = case["recording"]["duration_seconds"]; shapes = review["source_context"]["entry_shapes"]
            windows = [(float(start), min(duration, float(start) + POLICY["window_seconds"])) for start in np.arange(0, duration, POLICY["window_seconds"])]
            fixed = [point for point in review["points"] if point["kind"] == "coverage-sample"]
            checks = {}
            for name, features in methods.items():
                checks[name] = {"parameters": features["parameters"], "full_recording": score_window(features, shapes, duration),
                                "fixed_coverage_samples": [{"id": point["id"], **score_window(features, shapes, duration, point["start_seconds"], point["end_seconds"])} for point in fixed],
                                "all_20_second_windows": [score_window(features, shapes, duration, first, last) for first, last in windows]}
            charts = {name: curation.read(folder / filename) for name, filename in (("btc", "primary.json"), ("crema", "crema.json"))}
            memberships = {name: model_palette(chart, shapes) for name, chart in charts.items()}
            row = {"id": identifier, "title": case["name"], "recording": case["recording"], "source_shapes": shapes,
                   "source_setup": review["source_context"]["setup"], "proposed_relative_shift_semitones": 0,
                   "review_sha256": originals[folder / "review.json"], "native_artifacts": case["artifacts"],
                   "nnls_evidence_sha256": drafts.digest(case_folder / "nnls-evidence.json"),
                   "analysis_runtime_seconds": time.perf_counter() - extraction_started,
                   "acoustic_compatibility": checks,
                   "native_model_palette_membership": memberships,
                   "retrospective_cue_audit": {name: cue_diagnostics(chart, memberships[name], methods, shapes) for name, chart in charts.items()},
                   "exact_setup_verified": False, "accepted_arrangement": False, "accuracy_score": None,
                   "human_correction_seconds": None}
            drafts.write_json(case_folder / "report.json", row); rows.append(row)
            print(f"Checked {len(rows)}/{len(jobs)}: {case['name']}", flush=True)
        private = pack / "private-drafts"
        previous_drafts = {path for path in originals if path.parent == private}
        current_drafts = set(private.glob("*.json")) if private.exists() else set()
        if private.is_symlink() or previous_drafts != current_drafts or drafts.digest(Path(__file__)) != module_sha256 or any(not path.exists() or drafts.digest(path) != digest for path, digest in originals.items()):
            raise ValueError("Source inputs or saved private drafts changed during the diagnostic")
        report = {"schema_version": SCHEMA, "version": VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "status": "automated pitch-class/source-palette diagnostic; arrangements unaccepted", "gold": False,
                  "policy": POLICY, "spec_sha256": drafts.digest(spec), "pack_manifest_sha256": drafts.digest(pack / "manifest.json"),
                  "module_sha256": module_sha256, "completed_cases": len(rows),
                  "runtime_seconds": time.perf_counter() - started, "raw_inputs_modified": False,
                  "private_drafts_modified": False, "human_correction_seconds": None,
                  "limits": ["Scores are uncalibrated cosine compatibility, not confidence or accuracy.",
                             "No chord order, section boundaries, physical change timings or strumming are inferred.",
                             "Pitch-class matches cannot prove octave, guitar voicing, tuning or physical capo position.",
                             "NNLS uses global tuning compensation; no cents or concert-pitch result is claimed.",
                             "Source palettes may omit real contrasting material; vocals/bass/harmonics can affect full-mix chroma.",
                             "No shift is used to relabel raw charts or approve an arrangement."],
                  "cases": rows}
        drafts.write_json(staging / "report.json", report); staging.rename(output)
        return report
    except Exception:
        shutil.rmtree(staging); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.pack, args.spec, args.output)
        print(json.dumps({"cases": report["completed_cases"], "runtime_seconds": report["runtime_seconds"], "output": str(args.output)}))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Palette diagnostic failed: {error}\n")


if __name__ == "__main__": main()
