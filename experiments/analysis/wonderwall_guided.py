"""Reproduce the frozen, unaccepted Wonderwall section-alignment experiment.

This wrapper supplies no new decoder or timing reference. It delegates to the
existing chart aligner and NNLS adapter, verifies the exact frozen inputs, and
keeps deliberately altered controls separate from the source hypothesis.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import statistics

import chart_aligner
import lab
from candidates import nnls_chroma_adapter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIO = ROOT / "experiments/generated/youtube-pilot/cases/oasis-wonderwall-youtube-20261010/audio.wav"
DEFAULT_CHART = ROOT / "experiments/fixtures/section-charts/wonderwall-full-guided.json"
RECORDING_ID = "oasis-wonderwall-youtube-20261010"
AUDIO_SHA256 = "88e1649a3efa33647b8a07a7fc5feab2540c588ce35e2f27a3a682f2c4553462"
CHART_SHA256 = "002054d85d182279118ac6673352f5221c0f4a873590f58bf0a30351437d2a3b"
ALIGNER_SHA256 = "e21dc021cc8c508fea583ca4e11d293e6cfaf443535c4c370532cd9ff6a8a3e9"
ADAPTER_SHA256 = "6e0970496adb5d20c42dc3400d9a87db3d7b991463740d39813c5e621cd8a7a5"
DURATION = 277.78031746031746
PARAMETERS = {"hop_seconds": .025, "window_seconds": .18, "min_chord_seconds": .15,
              "transition_penalty": .12, "unknown_score": .45, "mismatch_margin": .30,
              "max_audio_seconds": 600}
KINDS = ("guided", "reversed-order", "simplified-quality")
BACKENDS = ("spectral", "nnls")
SIMPLIFIED = {"F#m7": "F#m", "A": "A", "Esus4": "E", "B7sus4": "B", "Dadd9": "D", "A/G#": "A"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def load_source_chart(path: Path) -> dict:
    raw = path.read_bytes()
    chart = json.loads(raw)
    chart_aligner.validate_untimed_chart(chart)
    recording = chart["recording"]
    if recording["id"] != RECORDING_ID or recording.get("audio_sha256") != AUDIO_SHA256:
        raise ValueError("Source chart recording identity/hash is not the frozen Wonderwall input")
    if hashlib.sha256(raw).hexdigest() != CHART_SHA256:
        raise ValueError("Source chart differs from frozen teacher-section hypothesis 0.1.0")
    return chart


def verify_inputs(audio: Path, chart: Path) -> dict:
    source = load_source_chart(chart)
    if sha(audio) != AUDIO_SHA256:
        raise ValueError("Audio hash differs from the exact frozen prepared official-video WAV")
    signal, rate = lab.read_wav(audio)
    if rate != 22050 or len(signal) / rate != DURATION:
        raise ValueError("Audio sample identity differs from the frozen recording")
    if sha(Path(chart_aligner.__file__)) != ALIGNER_SHA256 or sha(Path(nnls_chroma_adapter.__file__)) != ADAPTER_SHA256:
        raise ValueError("Aligner/adapter source changed; this wrapper only reproduces the frozen experiment")
    return source


def build_controls(source: dict) -> dict[str, dict]:
    """Deterministic mutations; preserve identity, count and untimed provenance."""
    chart_aligner.validate_untimed_chart(source)
    unexpected = {label for section in source["sections"] for label in section["sequence"]} - SIMPLIFIED.keys()
    if unexpected:
        raise ValueError(f"Unknown quality-control labels, refusing simplification: {sorted(unexpected)}")
    controls = {}
    for kind in KINDS[1:]:
        chart = copy.deepcopy(source)
        chart["metadata"]["control_kind"] = kind
        chart["metadata"]["review_status"] = "Deliberately altered control; never a candidate for playback or a timing reference"
        if kind == "reversed-order":
            chart["order"] = list(reversed(chart["order"]))
        else:
            for section in chart["sections"]:
                section["sequence"] = [SIMPLIFIED[label] for label in section["sequence"]]
        chart_aligner.validate_untimed_chart(chart)
        controls[kind] = chart
    return controls


def _verify_saved_case(result: dict, source: dict, expected_chart_hash: str, backend: str, evidence_hash: str) -> None:
    lab.validate_chart(result)
    record, data, analysis = result["recording"], result["alignment_input"], result["analysis"]
    if record["id"] != RECORDING_ID or record["audio_sha256"] != AUDIO_SHA256 or record["duration_seconds"] != DURATION:
        raise ValueError("Cached output recording identity differs from frozen audio")
    if data["chart_sha256"] != expected_chart_hash:
        raise ValueError("Cached output chart hash differs from its frozen input")
    sequence, mapping = chart_aligner.expand_sections(source)
    for key, expected in (("sequence", sequence), ("sections", source["sections"]), ("order", source["order"]),
                          ("metadata", source["metadata"]), ("expanded_position_sections", mapping),
                          ("mode", "finite"), ("start_policy", "first"), ("end_policy", "last")):
        if data.get(key) != expected:
            raise ValueError(f"Cached output differs from declared input: {key}")
    parameters = analysis["parameters"]
    checks = {"hop_samples": 551, "frame_size": 4096, "minimum_frames": 7, "min_chord_seconds": .15,
              "transition_penalty": .12, "unknown_score": .45, "mismatch_margin": .30,
              "maximum_audio_seconds": 600, "forced_beat_grid": False, "acoustic_backend": backend}
    if analysis["version"] != "0.2.0" or any(parameters.get(key) != value for key, value in checks.items()):
        raise ValueError("Cached output did not use the frozen decoder arguments")
    acoustic = result["alignment_evidence"]["acoustic_input"]
    if acoustic["backend"] != backend or (backend == "nnls-chroma" and acoustic["evidence_sha256"] != evidence_hash):
        raise ValueError("Cached output acoustic backend/evidence identity differs")


def summarize_case(path: Path, result: dict) -> dict:
    duration = result["recording"]["duration_seconds"]
    evidence = result["alignment_evidence"]
    diagnostics = evidence["diagnostics"]
    proposed = evidence["proposed_path_events_before_gap_mask"]
    dwells = [event["end_seconds"] - event["start_seconds"] for event in proposed]
    floor = result["analysis"]["parameters"]["nominal_interior_grid_dwell_seconds"]
    chords = result["chords"]
    labeled = sum(event["end_seconds"] - event["start_seconds"] for event in chords if event["label"] not in ("N", "X"))
    return {
        "output": str(path.resolve()), "output_sha256": sha(path),
        "input_chart_sha256": result["alignment_input"]["chart_sha256"],
        "backend": result["analysis"]["parameters"]["acoustic_backend"],
        "runtime_seconds": result["analysis"]["runtime_seconds"],
        "duration_seconds": duration, "labeled_seconds": labeled, "labeled_coverage_fraction": labeled / duration,
        "masked_seconds": {label: sum(event["end_seconds"] - event["start_seconds"] for event in chords if event["label"] == label) for label in ("N", "X")},
        "active_mismatch_fraction": diagnostics["active_mismatch_fraction"],
        "sequence_positions": len(result["alignment_input"]["sequence"]),
        "visited_positions": len({position for event in proposed for position in event["sequence_indices"]}),
        "unvisited_sequence_indices": diagnostics["unvisited_sequence_indices"], "path_transitions": diagnostics["path_transitions"],
        "proposed_minimum_dwell_seconds": min(dwells), "proposed_median_dwell_seconds": statistics.median(dwells),
        "proposed_maximum_dwell_seconds": max(dwells), "decoder_interior_dwell_floor_seconds": floor,
        "positions_near_decoder_minimum": sum(value <= floor + 1e-8 for value in dwells),
        "positions_below_350ms": sum(value < .35 for value in dwells),
        "positions_below_300ms": sum(value < .30 for value in dwells),
        "positions_with_no_active_frames": sum(event["evidence"]["active_frames"] == 0 for event in proposed),
        "output_events_after_gap_mask": len(chords), "x_gap_events": sum(event["label"] == "X" for event in chords),
        "x_gap_events_below_150ms": sum(event["label"] == "X" and event["end_seconds"] - event["start_seconds"] < .15 for event in chords),
        "output_events_below_150ms": sum(event["end_seconds"] - event["start_seconds"] < .15 for event in chords),
        "positions_over_8_seconds": sum(value > 8 for value in dwells),
        "acoustically_indistinguishable_pairs": diagnostics["acoustically_indistinguishable_sequence_position_pairs"],
        "viterbi_objective": diagnostics["viterbi_objective"], "fit_status": diagnostics["acoustic_fit_status"],
        "section_intervals": [dict(event, span_seconds=event["end_seconds"] - event["start_seconds"]) for event in evidence.get("section_intervals_from_proposed_path", [])],
        "long_positions": [dict(event, span_seconds=event["end_seconds"] - event["start_seconds"]) for event in proposed if event["end_seconds"] - event["start_seconds"] > 8],
        "accepted_for_primary_playback": False,
    }


def summarize(directory: Path, audio: Path = DEFAULT_AUDIO, chart: Path = DEFAULT_CHART) -> dict:
    source = verify_inputs(audio, chart)
    controls = build_controls(source)
    evidence_path = directory / "nnls-evidence.json"
    native = json.loads(evidence_path.read_text())
    nnls_chroma_adapter.validate_evidence(native, audio)
    if native["recording"]["id"] != RECORDING_ID:
        raise ValueError("Cached NNLS evidence recording ID differs")
    evidence_hash = sha(evidence_path)
    cases = []
    for kind in KINDS:
        expected = source if kind == "guided" else controls[kind]
        if kind == "guided":
            chart_hash = sha(chart)
        else:
            control_path = directory / f"{kind}-input.json"
            if control_path.read_bytes() != encoded(expected):
                raise ValueError("Cached control input differs from deterministic frozen mutation")
            chart_hash = sha(control_path)
        for backend in BACKENDS:
            path = directory / f"{kind}-{backend}.json"
            result = json.loads(path.read_text())
            _verify_saved_case(result, expected, chart_hash, "nnls-chroma" if backend == "nnls" else backend, evidence_hash)
            cases.append(summarize_case(path, result))
    return {
        "schema_version": "wonderwall-guided-diagnostics-1.0", "experiment_id": "wonderwall-guided-20261011",
        "original_experiment_date": "2026-10-11", "report_method": "Recomputed from exact hash-paired outputs; original runtime/output bytes retained",
        "inputs": {"audio_sha256": sha(audio), "chart_sha256": sha(chart),
                   "aligner_sha256": sha(Path(chart_aligner.__file__)), "nnls_adapter_sha256": sha(Path(nnls_chroma_adapter.__file__)),
                   "nnls_evidence_sha256": evidence_hash, "wrapper_sha256": sha(Path(__file__))},
        "frozen_decoder_parameters": dict(PARAMETERS, mode="finite", start_policy="first", end_policy="last"),
        "timing_reference_consumed": False, "model_timestamps_consumed": False,
        "source_repeat_counts_verified_against_exact_recording": False, "accuracy_measured": False, "deployed_as_default": False,
        "descriptive_dwell_thresholds": {"short_seconds": .35, "long_seconds": 8,
                                       "note": "Inspection bins only; not learned, calibrated or accuracy gates. Long positions can include source silence or held chords."},
        "recommendation": "Retain as unaccepted research candidate. Reversed-order control obtains high coverage and complete progress; endpoint-forced completion and low mismatch cannot establish valid timing.",
        "cases": cases,
    }


def run(output: Path, audio: Path = DEFAULT_AUDIO, chart: Path = DEFAULT_CHART, evidence_json: Path | None = None) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("Output directory exists; choose a new directory, no overwrite is supported")
    source = verify_inputs(audio, chart)
    controls = build_controls(source)
    if evidence_json is not None:
        native = json.loads(evidence_json.read_text())
        nnls_chroma_adapter.validate_evidence(native, audio)
        if native["recording"]["id"] != RECORDING_ID:
            raise ValueError("Cached NNLS evidence recording ID differs")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # exclusive creation; an existing directory is never replaced
    try:
        paths = {"guided": chart}
        for kind, control in controls.items():
            paths[kind] = output / f"{kind}-input.json"
            chart_aligner.write_json_safely(paths[kind], control, [audio, chart])
        evidence_path = output / "nnls-evidence.json"
        if evidence_json is None:
            nnls_chroma_adapter.extract_to_file(audio, RECORDING_ID, evidence_path)
        else:
            # Exclusive output publication preserves existing evidence bytes.
            with evidence_path.open("xb") as stream:
                stream.write(evidence_json.read_bytes())
        for kind in KINDS:
            for backend in BACKENDS:
                kwargs = dict(PARAMETERS)
                if backend == "nnls":
                    kwargs["evidence_json"] = evidence_path
                chart_aligner.align_to_file(audio, paths[kind], output / f"{kind}-{backend}.json", **kwargs)
        report = summarize(output, audio, chart)
        chart_aligner.write_json_safely(output / "summary.json", report, [audio, chart, evidence_path])
    except Exception:
        shutil.rmtree(output)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "summarize"):
        command = commands.add_parser(name)
        command.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
        command.add_argument("--chart", type=Path, default=DEFAULT_CHART)
        command.add_argument("--output", type=Path, required=True, help="New directory for run; new report file for summarize")
        if name == "run":
            command.add_argument("--evidence-json", type=Path, help="Optional exact cached NNLS evidence, validated then copied")
        else:
            command.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            report = run(args.output, args.audio, args.chart, args.evidence_json)
        else:
            inputs = [args.audio, args.chart, *args.directory.glob("*.json")]
            chart_aligner.check_output_path(args.output, inputs, overwrite=False)
            report = summarize(args.directory, args.audio, args.chart)
            chart_aligner.write_json_safely(args.output, report, inputs)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Wonderwall guided experiment failed: {error}\n")
    print(json.dumps({"output": str(args.output), "cases": len(report["cases"]),
                      "accepted_for_playback": False, "accuracy_measured": False}, indent=2))


if __name__ == "__main__":
    main()
