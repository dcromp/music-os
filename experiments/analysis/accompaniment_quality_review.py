"""Bounded accompaniment-quality evidence, without corrections or acceptance.

This reads frozen native charts and NNLS evidence alongside original audio.
Candidate templates and midpoint-cell scores describe full-mix compatibility;
none is calibrated confidence, a guitar-only label or a physical change time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import catalogue_pitch_check as pitch

ROOT = Path(__file__).resolve().parents[2]
SPEC_SCHEMA = "accompaniment-quality-spec-1.0"
SCHEMA = "accompaniment-quality-review-1.0"
TRIADS = [note + suffix for note in pitch.lab.NOTES for suffix in ("", "m")]
INPUT_NAMES = ("audio", "primary", "btc", "chordino", "nnls")
LIMITS = [
    "Uncalibrated full-mix compatibility, not chord accuracy or confidence.",
    "Voice, organ, bass and harmonics can affect the evidence; no isolated guitar or played grip is identified.",
    "Centered analysis windows and native chart boundaries are not verified physical chord-change times.",
    "Model agreement is not an independent reference. No thresholds, automatic corrections or accepted arrangements are produced.",
    "No tuning, capo, downbeat, numbered bar, attack direction or recorded strumming is verified.",
    "Agent processing seconds are compute runtime, not human review or correction time.",
]


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _candidate_templates(candidates):
    if (not isinstance(candidates, list) or not 1 <= len(candidates) <= 12
            or any(not isinstance(label, str) or not label.strip() for label in candidates)
            or len(set(candidates)) != len(candidates)):
        raise ValueError("Use one to twelve unique explicit harmonic candidates")
    try:
        templates = [pitch.chart_aligner.chord_template(label) for label in candidates]
    except (TypeError, KeyError) as error:
        raise ValueError("Use supported harmonic candidate labels") from error
    if any(template is None for template in templates):
        raise ValueError("Candidates require supported harmonic templates, not N or X")
    return np.asarray(templates)


def window_evidence(features, candidates, duration, start, end, *, sample_rate_hz, interior_only=False):
    """Score a bounded region, optionally excluding every boundary-straddling FFT.

    Feature-center midpoint cells supply duration weights. In interior mode a
    cell contributes only when its frame's entire centered analysis window fits
    inside the requested region. Excluded cells are reported, never interpolated.
    """
    if (not all(_number(value) for value in (duration, start, end, sample_rate_hz))
            or not 0 <= start < end <= duration or sample_rate_hz <= 0
            or type(interior_only) is not bool):
        raise ValueError("Use finite audio duration, rate and an interior region")
    templates = _candidate_templates(candidates)
    times = np.asarray(features["times"], dtype=float)
    left, right = pitch.frame_cells(times, duration)
    chroma = np.asarray(features["chroma"], dtype=float)
    silent = np.asarray(features["silent"])
    frame_size = features.get("parameters", {}).get("frame_size")
    if not isinstance(frame_size, int) or isinstance(frame_size, bool) or frame_size <= 0:
        raise ValueError("A positive integer analysis frame size is required")
    if (chroma.shape != (len(times), 12) or silent.shape != times.shape or silent.dtype != bool
            or not np.all(np.isfinite(chroma)) or np.any(chroma < 0)):
        raise ValueError("Use finite nonnegative C-first chroma and boolean silence")
    norms = np.linalg.norm(chroma, axis=1)
    if np.any((norms != 0) & ~np.isclose(norms, 1, rtol=0, atol=1e-8)):
        raise ValueError("Feature vectors must be zero or L2-normalized")
    weights = np.maximum(0, np.minimum(right, end) - np.maximum(left, start))
    half_window = frame_size / sample_rate_hz / 2
    eligible = ((times - half_window >= start) & (times + half_window <= end)
                if interior_only else np.ones(len(times), dtype=bool))
    active = eligible & ~silent & (norms > 0)
    active_weights = weights * active
    active_seconds = float(active_weights.sum())
    result = {
        "start_seconds": start, "end_seconds": end, "audio_seconds": end - start,
        "full_analysis_window_inside_region": interior_only,
        "analysis_half_window_seconds": half_window,
        "active_evidence_seconds": active_seconds,
        "active_frame_count": int(np.count_nonzero(active_weights)),
        "silent_seconds": float(weights[eligible & silent].sum()),
        "non_silent_zero_evidence_seconds": float(weights[eligible & ~silent & (norms == 0)].sum()),
        "boundary_excluded_cell_seconds": float(weights[~eligible].sum()),
        "mean_l2_chroma_c_first": None,
        "candidate_scores": [{"label": label, "mean_cosine": None} for label in candidates],
        "triad_ranking": [],
    }
    if not active_seconds:
        return result
    # Explicit sums avoid platform BLAS floating-status warnings on bounded vectors.
    means = np.einsum("i,ij->j", active_weights, chroma, optimize=False) / active_seconds
    candidate_scores = np.einsum("ij,j->i", templates, means, optimize=False)
    triad_templates = np.array([pitch.chart_aligner.chord_template(label) for label in TRIADS])
    triad_scores = np.einsum("ij,j->i", triad_templates, means, optimize=False)
    result["mean_l2_chroma_c_first"] = means.tolist()
    result["candidate_scores"] = [{"label": label, "mean_cosine": float(score)}
                                  for label, score in zip(candidates, candidate_scores)]
    result["triad_ranking"] = sorted(
        ({"label": label, "mean_cosine": float(score)} for label, score in zip(TRIADS, triad_scores)),
        key=lambda row: (-row["mean_cosine"], row["label"]))
    return result


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_path(value, root, *, exists):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("Use an explicit project-local path")
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("Parent traversal is not permitted")
    path = path if path.is_absolute() else root / path
    if not path.is_relative_to(root):
        raise ValueError("Keep all inputs and outputs inside the project")
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("Do not follow input or output symlink aliases")
    resolved = path.resolve(strict=exists)
    if not resolved.is_relative_to(root):
        raise ValueError("Keep all inputs and outputs inside the project")
    if exists and not resolved.is_file():
        raise ValueError("Inputs must be regular files")
    return resolved


def _read_json(path):
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def preflight(spec, output, root=ROOT):
    """Validate a complete bounded run before creating any output."""
    root = Path(root).resolve(strict=True)
    spec = _project_path(spec, root, exists=True)
    output = _project_path(output, root, exists=False)
    if output.exists():
        raise ValueError("Use an unused report path; existing files are never overwritten")
    spec_digest = _digest(spec)
    config = _read_json(spec)
    if not isinstance(config, dict) or config.get("schema_version") != SPEC_SCHEMA:
        raise ValueError(f"Expected {SPEC_SCHEMA}")
    cases = config.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        raise ValueError("Use one to thirty-two explicit recording cases")
    inputs = {spec: spec_digest}
    jobs = []
    identifiers = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each recording case must be an object")
        identifier = case.get("recording_id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("Recording IDs must be unique nonempty strings")
        identifiers.add(identifier)
        paths = {name: _project_path(case.get(name), root, exists=True) for name in INPUT_NAMES}
        inputs.update({path: _digest(path) for path in paths.values()})
        charts = {name: _read_json(paths[name]) for name in ("primary", "btc", "chordino")}
        signal, rate = pitch.lab.read_wav(paths["audio"])
        if not len(signal) or len(signal) > rate * 600:
            raise ValueError("Use nonempty original PCM audio no longer than 600 seconds")
        duration = len(signal) / rate
        identity = {"id": identifier, "audio_sha256": inputs[paths["audio"]],
                    "sample_rate_hz": rate, "duration_seconds": duration}
        evidence = _read_json(paths["nnls"])
        pitch.nnls.validate_evidence(evidence, paths["audio"])
        for name, value in list(charts.items()) + [("nnls", evidence)]:
            if name != "nnls":
                pitch.lab.validate_chart(value)
                if any(event["end_seconds"] > duration for event in value["chords"]):
                    raise ValueError("Native intervals must remain strictly inside audio duration")
            recording = value.get("recording", {})
            if any(recording.get(key) != expected for key, expected in identity.items()):
                raise ValueError(f"{name} recording identity differs from exact audio")
        regions = case.get("regions")
        if not isinstance(regions, list) or not 1 <= len(regions) <= 128:
            raise ValueError("Use one to 128 bounded regions per recording")
        region_ids = set()
        for region in regions:
            if not isinstance(region, dict):
                raise ValueError("Each region must be an object")
            region_id = region.get("id")
            if not isinstance(region_id, str) or not region_id.strip() or region_id in region_ids:
                raise ValueError("Region IDs must be unique nonempty strings per recording")
            region_ids.add(region_id)
            start, end = region.get("start_seconds"), region.get("end_seconds")
            if not all(_number(value) for value in (start, end)) or not 0 <= start < end <= duration:
                raise ValueError("Regions must be finite, positive intervals inside exact audio")
            _candidate_templates(region.get("candidates"))
        jobs.append({"identity": identity, "paths": paths, "charts": charts,
                     "evidence": evidence, "regions": regions})
    pins = config.get("inputs", {})
    if not isinstance(pins, dict):
        raise ValueError("Optional inputs must map project-relative file paths to SHA256 values")
    for value, expected in pins.items():
        path = _project_path(value, root, exists=True)
        if (path not in inputs or path == spec or not isinstance(expected, str)
                or len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected)
                or inputs[path] != expected):
            raise ValueError("An optional declared input hash differs or names an undeclared input")
    if output in inputs:
        raise ValueError("The output must be separate from every input")
    return root, spec, output, jobs, inputs


def run(spec, output, root=ROOT):
    """Build a new diagnostic JSON report without changing inputs or guidance."""
    started = time.perf_counter()
    root, spec, output, jobs, inputs = preflight(spec, output, root)
    cases = []
    for job in jobs:
        paths, charts, identity = job["paths"], job["charts"], job["identity"]
        methods = {"spectral": pitch.features_from_spectral(paths["audio"]),
                   "nnls": pitch.features_from_nnls(job["evidence"])}
        regions = []
        for region in job["regions"]:
            start, end = region["start_seconds"], region["end_seconds"]
            overlaps = {}
            for name, chart in charts.items():
                overlaps[name] = [dict(event, overlap_seconds=min(end, event["end_seconds"]) - max(start, event["start_seconds"]))
                                  for event in chart["chords"]
                                  if event["start_seconds"] < end and event["end_seconds"] > start]
            scored = {}
            for method, features in methods.items():
                options = {"sample_rate_hz": identity["sample_rate_hz"]}
                scored[method] = {
                    "parameters": features["parameters"],
                    "whole_region": window_evidence(features, region["candidates"], identity["duration_seconds"], start, end, **options),
                    "interior_only": window_evidence(features, region["candidates"], identity["duration_seconds"], start, end,
                                                     interior_only=True, **options),
                }
            regions.append({**region, "model_overlaps": overlaps, "features": scored})
        cases.append({"recording": identity,
                      "analyses": {name: chart["analysis"] for name, chart in charts.items()},
                      "inputs": {name: {"path": str(path.relative_to(root)), "sha256": inputs[path]}
                                 for name, path in paths.items()},
                      "regions": regions, "accepted_arrangement": False,
                      "physical_timing_verified": False, "accuracy_score": None})
    # Refuse publication if any audio, native chart, evidence or specification changed.
    if any(not path.is_file() or path.is_symlink() or _digest(path) != expected for path, expected in inputs.items()):
        raise ValueError("Inputs changed during the quality review; no report published")
    output = _project_path(output, root, exists=False)
    report = {
        "schema_version": SCHEMA, "gold": False,
        "spec": {"path": str(spec.relative_to(root)), "sha256": inputs[spec]},
        "implementation_sha256": _digest(Path(__file__)),
        "feature_modules_sha256": {Path(module.__file__).name: _digest(Path(module.__file__))
                                   for module in (pitch, pitch.chart_aligner, pitch.nnls)},
        "pitch_classes_c_first": pitch.lab.NOTES,
        "method": {"weighting": "non-silent nonzero frames, clipped adjacent-center-midpoint duration cells",
                   "templates": "existing equal-weight L2-normalized chord pitch classes; slash bass omitted",
                   "interior_only": "entire centered analysis window must fit within requested region",
                   "automatic_corrections": False, "acceptance_threshold": None},
        "cases": cases, "human_correction_seconds": None,
        "agent_processing_seconds": time.perf_counter() - started, "limits": LIMITS,
    }
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also refuses a report created after preflight.
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.spec, args.output)
    print(json.dumps({"cases": len(report["cases"]), "agent_processing_seconds": report["agent_processing_seconds"],
                      "accepted_arrangements": 0}))


if __name__ == "__main__":
    main()
