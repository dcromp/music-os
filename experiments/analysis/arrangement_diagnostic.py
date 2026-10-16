"""Descriptive, unrestricted-sequence evidence for an untimed chart hypothesis.

Saved guarded frame argmaxes come from the global acoustic vocabulary, never
the supplied sequence or decoded position. They share the aligner's features
and templates and are therefore correlated evidence, not an independent model
or timing reference. A mechanically complete path is never an accepted chart.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import chart_aligner
from core_chord_screen import core_semantics, CORE_REDUCTIONS

VERSION = "0.1.0"
# Declared before inspecting any arrangement diagnostic outputs. This deletes
# short runs; it does not smooth, substitute, fill gaps, or calibrate confidence.
STABLE_RUN_SECONDS = .15
MAX_EDIT_CELLS = 4_000_000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_key(label: str) -> tuple[int, str] | None:
    semantics = core_semantics(label)
    if semantics["status"] != "chord":
        return None
    # This chroma diagnostic deliberately does not claim inversion identity.
    return semantics["root"], semantics["quality"]


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_events(events: list[dict], duration: float) -> None:
    if not _number(duration) or duration <= 0:
        raise ValueError("Duration must be finite and positive")
    previous = 0.0
    for event in events:
        start, end = event["start_seconds"], event["end_seconds"]
        if not all(_number(value) for value in (start, end)) or start < previous - 1e-8 or not 0 <= start < end <= duration + 1e-8:
            raise ValueError("Events must be ordered, nonoverlapping and within audio duration")
        if not isinstance(event["label"], str):
            raise ValueError("Event labels must be strings")
        previous = end


def events_from_guarded(result: dict) -> list[dict]:
    """Read only global argmax, time and silence from saved guarded frames."""
    evidence = result["alignment_evidence"]
    columns, frames = evidence["frame_columns"], evidence["frames"]
    required = ("time_seconds", "best_vocabulary_label", "silent")
    if any(columns.count(name) != 1 for name in required) or not frames:
        raise ValueError("Saved global acoustic frame columns are missing or ambiguous")
    index = {name: columns.index(name) for name in required}
    duration = result["recording"]["duration_seconds"]
    if not _number(duration) or duration <= 0:
        raise ValueError("Duration must be finite and positive")
    if any(not isinstance(row, list) or len(row) != len(columns) for row in frames):
        raise ValueError("Frame rows must match declared columns")
    times = [row[index["time_seconds"]] for row in frames]
    if any(not _number(value) or not 0 <= value < duration for value in times) or times[0] != 0 or any(
            left >= right for left, right in zip(times, times[1:])):
        raise ValueError("Frame times must start at zero and increase within audio duration")
    events = []
    for position, row in enumerate(frames):
        start = row[index["time_seconds"]]
        end = frames[position + 1][index["time_seconds"]] if position + 1 < len(frames) else duration
        if not isinstance(row[index["silent"]], bool):
            raise ValueError("Silence evidence must be Boolean")
        label = "N" if row[index["silent"]] else row[index["best_vocabulary_label"]]
        if events and events[-1]["label"] == label and abs(events[-1]["end_seconds"] - start) < 1e-8:
            events[-1]["end_seconds"] = end
        else:
            events.append({"start_seconds": start, "end_seconds": end, "label": label})
    validate_events(events, duration)
    return events


def core_runs(events: list[dict], duration: float) -> tuple[list[dict], dict]:
    """Collapse adjacent same-core events only; N/X and gaps split raw runs."""
    validate_events(events, duration)
    runs = []
    coverage = {"harmonic_seconds": 0.0, "no_chord_seconds": 0.0,
                "unknown_seconds": 0.0, "unsupported_seconds": 0.0,
                "uncovered_seconds": duration - sum(e["end_seconds"] - e["start_seconds"] for e in events)}
    bridge_allowed = False
    for event in events:
        seconds = event["end_seconds"] - event["start_seconds"]
        semantic = core_semantics(event["label"])
        key = core_key(event["label"])
        if key is None:
            kind = {"no_chord": "no_chord_seconds", "unknown": "unknown_seconds"}.get(semantic["status"], "unsupported_seconds")
            coverage[kind] += seconds
            bridge_allowed = False
            continue
        coverage["harmonic_seconds"] += seconds
        if runs and bridge_allowed and runs[-1]["core"] == list(key) and abs(runs[-1]["end_seconds"] - event["start_seconds"]) < 1e-8:
            runs[-1]["end_seconds"] = event["end_seconds"]
            runs[-1]["seconds"] += seconds
            if event["label"] not in runs[-1]["source_labels"]:
                runs[-1]["source_labels"].append(event["label"])
        else:
            runs.append({"start_seconds": event["start_seconds"], "end_seconds": event["end_seconds"],
                         "seconds": seconds, "core": list(key), "source_labels": [event["label"]]})
        bridge_allowed = True
    return runs, coverage


def chart_runs(sequence: list[str]) -> tuple[list[dict], dict]:
    runs, ignored, repeated = [], [], []
    bridge_allowed = False
    for index, label in enumerate(sequence):
        key = core_key(label)
        if key is None:
            ignored.append(index)
            bridge_allowed = False
            continue
        if runs and bridge_allowed and runs[-1]["core"] == list(key):
            runs[-1]["sequence_indices"].append(index)
            runs[-1]["source_labels"].append(label)
            repeated.append(index)
        else:
            runs.append({"core": list(key), "sequence_indices": [index], "source_labels": [label]})
        bridge_allowed = True
    return runs, {"ignored_nonharmonic_or_unsupported_positions": ignored,
                  "indistinguishable_repeated_core_positions": repeated,
                  "original_position_count": len(sequence), "measurable_core_run_count": len(runs)}


def edit_alignment(observed: list[dict], proposed: list[dict], *, max_cells: int = MAX_EDIT_CELLS) -> dict:
    """Unit-cost Levenshtein trace; deterministic match/substitution priority.

    Insertions are observed acoustic runs absent from the chart. Deletions are
    proposed chart runs absent from the acoustic sequence. This does not decide
    whether a chart or recognizer is wrong. No reference timestamps are read.
    """
    m, n = len(observed), len(proposed)
    if isinstance(max_cells, bool) or not isinstance(max_cells, int) or max_cells < 1 or (m + 1) * (n + 1) > max_cells:
        raise ValueError("Edit-distance matrix exceeds its declared bound")
    costs = [list(range(n + 1))] + [[i] + [0] * n for i in range(1, m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            equal = observed[i - 1]["core"] == proposed[j - 1]["core"]
            costs[i][j] = min(costs[i - 1][j - 1] + (not equal), costs[i - 1][j] + 1, costs[i][j - 1] + 1)
    trace, i, j = [], m, n
    while i or j:
        if i and j and costs[i][j] == costs[i - 1][j - 1] + (observed[i - 1]["core"] != proposed[j - 1]["core"]):
            operation = "match" if observed[i - 1]["core"] == proposed[j - 1]["core"] else "substitution"
            trace.append({"operation": operation, "observed_run_index": i - 1, "chart_run_index": j - 1})
            i, j = i - 1, j - 1
        elif i and costs[i][j] == costs[i - 1][j] + 1:
            trace.append({"operation": "observed_insertion", "observed_run_index": i - 1, "chart_run_index": None})
            i -= 1
        else:
            trace.append({"operation": "chart_deletion", "observed_run_index": None, "chart_run_index": j - 1})
            j -= 1
    trace.reverse()
    counts = {operation: sum(step["operation"] == operation for step in trace)
              for operation in ("match", "substitution", "observed_insertion", "chart_deletion")}
    matched_seconds = sum(observed[step["observed_run_index"]]["seconds"] for step in trace if step["operation"] == "match")
    observed_seconds = sum(run["seconds"] for run in observed)
    return {"edit_distance": costs[m][n], "normalized_edit_distance": costs[m][n] / max(m, n) if max(m, n) else None,
            "observed_run_count": m, "chart_run_count": n, "operations": counts,
            "matched_observed_seconds": matched_seconds, "observed_seconds": observed_seconds,
            "matched_fraction_of_observed_harmonic_seconds": matched_seconds / observed_seconds if observed_seconds else None,
            "matched_fraction_of_measurable_chart_runs": counts["match"] / n if n else None,
            "trace": trace}


def compare(events: list[dict], duration: float, sequence: list[str], *, stable_seconds: float = STABLE_RUN_SECONDS) -> dict:
    if not _number(stable_seconds) or stable_seconds <= 0:
        raise ValueError("Stable duration must be finite and positive")
    observed, coverage = core_runs(events, duration)
    proposed, chart_coverage = chart_runs(sequence)
    stable = [run for run in observed if run["seconds"] + 1e-10 >= stable_seconds]
    # Distinct same-core runs separated by silence/unknown/short discarded runs
    # remain distinct here. They may be acoustic rearticulations, not chart changes.
    discarded = coverage["harmonic_seconds"] - sum(run["seconds"] for run in stable)
    return {"coverage": {**coverage, "stable_harmonic_seconds": sum(run["seconds"] for run in stable),
                         "discarded_short_run_seconds": discarded,
                         "harmonic_fraction_of_audio": coverage["harmonic_seconds"] / duration,
                         "stable_fraction_of_audio": sum(run["seconds"] for run in stable) / duration},
            "chart_coverage": chart_coverage, "raw": edit_alignment(observed, proposed),
            "stable": edit_alignment(stable, proposed), "raw_runs": observed,
            "stable_runs": stable, "chart_runs": proposed}


def diagnose(result: dict, chart: dict, *, source_kind: str = "guarded-global-argmax") -> dict:
    chart_aligner.validate_untimed_chart(chart)
    recording = result["recording"]
    if recording["id"] != chart["recording"]["id"]:
        raise ValueError("Recognition and chart recording IDs differ")
    if not recording.get("audio_sha256") or recording["audio_sha256"] != chart["recording"].get("audio_sha256"):
        raise ValueError("Recognition and chart audio hashes differ or are missing")
    if source_kind == "guarded-global-argmax":
        events = events_from_guarded(result)
        diagnostic = result["alignment_evidence"]["diagnostics"]
        flags = []
        if diagnostic.get("partial") or diagnostic.get("endpoint_reached") is False:
            flags.append("partial_constrained_path")
        if diagnostic.get("unvisited_sequence_indices"):
            flags.append("unvisited_chart_positions")
        if diagnostic.get("active_frames") == 0 or diagnostic.get("no_active_evidence_supplied_position_count", 0) > 0:
            flags.append("positions_without_active_evidence")
        mechanical = {"flags": flags, "endpoint_reached": diagnostic.get("endpoint_reached"),
                      "unvisited_sequence_indices": diagnostic.get("unvisited_sequence_indices"),
                      "no_active_evidence_supplied_position_count": diagnostic.get("no_active_evidence_supplied_position_count"),
                      "active_mismatch_fraction": diagnostic.get("active_mismatch_fraction"),
                      "retained_harmonic_seconds": diagnostic.get("retained_harmonic_seconds")}
    elif source_kind == "raw-recognizer":
        events = result["chords"]
        mechanical = {"flags": [], "constrained_path_available": False}
    else:
        raise ValueError("Unsupported acoustic source kind")
    sequence = chart_aligner.expand_sections(chart)[0] if chart["schema_version"] == chart_aligner.SECTION_SCHEMA else chart["sequence"]
    compared = compare(events, recording["duration_seconds"], sequence)
    if compared["coverage"]["harmonic_seconds"] <= 1e-12 and "no_unrestricted_harmonic_evidence" not in mechanical["flags"]:
        mechanical["flags"].append("no_unrestricted_harmonic_evidence")
    return {"schema_version": "arrangement-diagnostic-1.0", "version": VERSION,
            "recording": recording, "source_kind": source_kind,
            "parameters": {"stable_run_seconds": STABLE_RUN_SECONDS, "core_reductions": CORE_REDUCTIONS,
                           "slash_bass_in_comparison": False, "edit_costs": {"insertion": 1, "deletion": 1, "substitution": 1},
                           "short_run_action": "discard without substitution, merging across gaps, or filling",
                           "silence_unknown_action": "exclude from harmonic sequence; preserve coverage and split raw runs",
                           "quality_or_cosine_selection_threshold": None, "acceptance_score_threshold": None},
            "mechanical_status": {**mechanical, "failed": bool(mechanical["flags"])},
            "comparison": compared, "accepted_for_playback": False, "arrangement_verified": False,
            "score_is_calibrated_confidence": False,
            "limitations": ["Descriptive sequence disagreement cannot tell whether a recognizer or proposed chart is wrong.",
                "Global argmax uses the same acoustic frames/templates as constrained timing; independent of chart order, but not an independent model.",
                "Short-run filtering can discard genuine fast changes; raw runs and removed duration are reported alongside.",
                "Root and retained quality are compared. Removed extensions and slash bass are not verified.",
                "Adjacent identical core chart positions are acoustically indistinguishable and collapsed; rearticulation/repeat timing is not verified.",
                "No chart timing gold, beat alignment, key prior, song-section classifier, accuracy benchmark or tuned confidence gate is used."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--chart", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-kind", choices=("guarded-global-argmax", "raw-recognizer"), default="guarded-global-argmax")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("Output already exists; diagnostics must use a new path")
    evidence, chart = json.loads(args.evidence.read_text()), json.loads(args.chart.read_text())
    result = diagnose(evidence, chart, source_kind=args.source_kind)
    result["provenance"] = {"module_sha256": sha(Path(__file__)), "evidence_sha256": sha(args.evidence),
                            "chart_sha256": sha(args.chart), "core_policy_module_sha256": sha(Path(__file__).with_name("core_chord_screen.py"))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "mechanical_failure": result["mechanical_status"]["failed"],
                      "stable_edit_distance": result["comparison"]["stable"]["edit_distance"],
                      "accepted_for_playback": False}))


if __name__ == "__main__":
    main()
