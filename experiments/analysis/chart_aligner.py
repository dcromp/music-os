"""Experimental audio alignment of a supplied, strictly untimed chord sequence.

This is a small NumPy baseline, not a recogniser or a validated song aligner.
Only adjacent chart positions are allowed. Cycles, partial starts and partial
ends require explicit input assumptions; no verse/chorus order is inferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time

import numpy as np

import lab

VERSION = "0.2.0"
SCHEMA = "untimed-chart-1.0"
SECTION_SCHEMA = "untimed-chart-1.1"
QUALITIES = {
    "": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "5": (0, 7),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "dim": (0, 3, 6),
    "dim7": (0, 3, 6, 9), "aug": (0, 4, 8),
    "7sus4": (0, 5, 7, 10), "add9": (0, 4, 7, 2),
}
ALIASES = {"maj": "", "major": "", "min": "m", "minor": "m",
           "min7": "m7", "major7": "maj7", "minor7": "m7", "sus4(7)": "7sus4"}
ROOTS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
TIMING_KEYS = {"start", "end", "time", "times", "timing", "timestamp",
               "timestamps", "start_seconds", "end_seconds", "duration",
               "duration_seconds", "beats_seconds", "downbeats_seconds"}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def chord_template(label: str) -> np.ndarray | None:
    """Return equal pitch-class weights; slash bass is deliberately ignored."""
    if not isinstance(label, str) or not label.strip() or label != label.strip():
        raise ValueError("Chord labels must be nonempty strings without surrounding whitespace")
    if label in ("N", "X"):
        return None
    match = re.fullmatch(r"([A-G])([#b]?)([^/]*)(?:/([A-G][#b]?|[b#]?[1-7]))?", label)
    if not match:
        raise ValueError(f"Unsupported chord label: {label}")
    root = (ROOTS[match[1]] + {"": 0, "#": 1, "b": -1}[match[2]]) % 12
    suffix = match[3].lstrip(":")
    suffix = ALIASES.get(suffix, suffix)
    if suffix not in QUALITIES:
        raise ValueError(f"Unsupported chord quality in {label}; no silent major/minor simplification")
    template = np.zeros(12)
    template[(root + np.array(QUALITIES[suffix])) % 12] = 1 / math.sqrt(len(QUALITIES[suffix]))
    return template


def validate_untimed_chart(chart: dict) -> None:
    """Reject timed references rather than accidentally consuming their gold."""
    def reject_times(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in TIMING_KEYS or str(key).lower().endswith("_timestamp"):
                    raise ValueError(f"Untimed charts cannot contain timing field {key}")
                reject_times(child)
        elif isinstance(value, list):
            for child in value:
                reject_times(child)

    if not isinstance(chart, dict) or chart.get("schema_version") not in (SCHEMA, SECTION_SCHEMA):
        raise ValueError(f"Expected schema_version {SCHEMA} or {SECTION_SCHEMA}")
    reject_times(chart)
    sectional = chart["schema_version"] == SECTION_SCHEMA
    allowed = {"schema_version", "recording", "mode", "start_policy", "end_policy", "metadata"}
    allowed.update(("sections", "order") if sectional else ("sequence",))
    if set(chart) - allowed:
        raise ValueError(f"Unsupported untimed chart fields: {sorted(set(chart) - allowed)}")
    recording = chart.get("recording")
    if not isinstance(recording, dict) or any(
        not isinstance(recording.get(key), str) or not recording[key].strip() for key in ("id", "title")
    ):
        raise ValueError("recording.id and recording.title are required")
    if sectional:
        sequence, _ = expand_sections(chart)
    else:
        sequence = chart.get("sequence")
    if not isinstance(sequence, list) or not 1 <= len(sequence) <= 512:
        raise ValueError("sequence must contain 1–512 ordered chord strings")
    for label in sequence:
        chord_template(label)
    mode = chart.get("mode", "finite")
    if mode not in ("finite", "cyclic"):
        raise ValueError("mode must be finite or explicitly cyclic")
    if sectional and mode != "finite":
        raise ValueError("Section charts are finite; declare each repeat explicitly")
    if chart.get("start_policy", "first") not in ("first", "any"):
        raise ValueError("start_policy must be first or explicitly any")
    if chart.get("end_policy", "last" if mode == "finite" else "any") not in ("last", "any"):
        raise ValueError("end_policy must be last or explicitly any")
    if "metadata" in chart and not isinstance(chart["metadata"], dict):
        raise ValueError("metadata must be an object; it is preserved without influencing alignment")
    # Reject nonfinite metadata, and ensure hashes/outputs have stable JSON representations.
    try:
        json.dumps(chart, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Untimed chart must contain finite JSON data") from error


def expand_sections(chart: dict) -> tuple[list[str], list[dict]]:
    """Compile declared section order/repeats without inventing timings or loops."""
    sections, order = chart.get("sections"), chart.get("order")
    if not isinstance(sections, list) or not 1 <= len(sections) <= 128:
        raise ValueError("sections must contain 1–128 section definitions")
    if not isinstance(order, list) or not 1 <= len(order) <= 128:
        raise ValueError("order must contain 1–128 declared section occurrences")
    definitions = {}
    for section in sections:
        if not isinstance(section, dict) or set(section) - {"id", "name", "sequence"}:
            raise ValueError("Each section accepts only id, name and sequence")
        identifier = section.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Section IDs must be 1–64 letters, digits, underscores or hyphens")
        if identifier in definitions:
            raise ValueError("Section IDs must be unique")
        name = section.get("name", identifier)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Section name must be a nonempty string")
        labels = section.get("sequence")
        if not isinstance(labels, list) or not 1 <= len(labels) <= 512:
            raise ValueError("Each section needs 1–512 ordered chord strings")
        for label in labels:
            chord_template(label)
        definitions[identifier] = {"name": name, "sequence": labels}
    sequence, mapping = [], []
    for order_index, occurrence in enumerate(order):
        if not isinstance(occurrence, dict) or set(occurrence) - {"section_id", "repeat"}:
            raise ValueError("Each order entry accepts only section_id and repeat")
        identifier, repeats = occurrence.get("section_id"), occurrence.get("repeat", 1)
        if not isinstance(identifier, str) or identifier not in definitions:
            raise ValueError("Section order refers to an undefined section")
        if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 64:
            raise ValueError("repeat must be an integer from 1 to 64")
        section = definitions[identifier]
        if len(sequence) + repeats * len(section["sequence"]) > 512:
            raise ValueError("Expanded section chart exceeds 512 chord positions")
        for repeat_index in range(repeats):
            for chord_index, label in enumerate(section["sequence"]):
                sequence.append(label)
                mapping.append({"section_id": identifier, "section_name": section["name"],
                                "order_index": order_index, "repeat_index": repeat_index,
                                "chord_index": chord_index})
    return sequence, mapping


def features(signal: np.ndarray, sample_rate: int, hop_seconds: float, window_seconds: float) -> dict:
    frame_size = 2 ** math.ceil(math.log2(max(2, sample_rate * window_seconds)))
    hop = max(1, round(sample_rate * hop_seconds))
    padded = np.pad(signal, (frame_size // 2, frame_size // 2))
    window = np.hanning(frame_size)
    frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    selected = np.flatnonzero((frequencies >= 65) & (frequencies <= 2000))
    if not len(selected):
        raise ValueError("Audio sample rate is too low for the spectral baseline")
    pitch_classes = np.rint(69 + 12 * np.log2(frequencies[selected] / 440)).astype(int) % 12
    chroma, rms = [], []
    for offset in range(0, len(signal), hop):
        frame = padded[offset:offset + frame_size]
        rms.append(float(np.sqrt(np.mean(frame ** 2))))
        powers = np.abs(np.fft.rfft(frame * window))[selected] ** 2
        vector = np.bincount(pitch_classes, weights=powers, minlength=12)
        norm = np.linalg.norm(vector)
        chroma.append(vector / norm if norm else vector)
    threshold = max(1e-5, float(np.max(np.abs(signal))) * 0.025)
    return {"chroma": np.array(chroma), "rms": np.array(rms),
            "silent": np.array(rms) < threshold, "silence_rms_threshold": threshold,
            "hop_samples": hop, "frame_size": frame_size}


def acoustic_evidence(audio: Path, evidence_path: Path, recording_id: str, original: dict,
                      sample_rate: int) -> tuple[np.ndarray, dict]:
    """Resample hash-paired native acoustic features, never chord annotations."""
    from candidates import nnls_chroma_adapter
    raw = evidence_path.read_bytes()
    packet = json.loads(raw)
    try:
        nnls_chroma_adapter.validate_evidence(packet, audio)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Malformed acoustic evidence packet") from error
    if packet["recording"]["id"] != recording_id:
        raise ValueError("Acoustic evidence recording ID differs from untimed chart")
    native_times = np.asarray(packet["times_seconds"], dtype=float)
    native_chroma = np.asarray(packet["chroma_c_first"], dtype=float)
    grid = np.arange(len(original["chroma"])) * original["hop_samples"] / sample_rate
    interpolated = np.column_stack([np.interp(grid, native_times, native_chroma[:, pitch])
                                    for pitch in range(12)])
    norms = np.linalg.norm(interpolated, axis=1)
    normalized = np.divide(interpolated, norms[:, None], out=np.zeros_like(interpolated),
                           where=norms[:, None] > 0)
    return normalized, {"backend": "nnls-chroma", "evidence_sha256": hashlib.sha256(raw).hexdigest(),
                        "native_analysis": packet["analysis"], "native_frames": len(native_times),
                        "sampling": "linear interpolation of native frame centers to decoder grid; nearest edge outside centers; L2 renormalize",
                        "silence_mask": "unchanged original PCM RMS on decoder's short analysis window",
                        "note": "Interpolation does not improve native temporal resolution; features are offline/global-tuned"}


def constrained_path(emissions: np.ndarray, minimum_frames: int, transition_penalty: float,
                     mode: str, start_policy: str, end_policy: str,
                     terminal_minimum_frames: int | None = None) -> tuple[np.ndarray, float]:
    """Adjacent-only Viterbi with a minimum dwell and no fixed duration or beat grid.

    The last age bucket caps the required terminal age. This keeps memory
    proportional to frames × chart positions, without setting a maximum dwell.
    """
    frame_count, positions = emissions.shape
    terminal_minimum_frames = max(minimum_frames, terminal_minimum_frames or minimum_frames)
    age_buckets = terminal_minimum_frames
    if frame_count < terminal_minimum_frames:
        raise ValueError("Audio is shorter than the minimum chord duration")
    scores = np.full((positions, age_buckets), -np.inf)
    starts = np.arange(positions) if start_policy == "any" else np.array([0])
    scores[starts, 0] = emissions[0, starts]
    choices = np.zeros((frame_count, positions), dtype=bool)
    advance_ages = np.zeros((frame_count, positions), dtype=np.uint32)
    for frame in range(1, frame_count):
        mature_ages = np.argmax(scores[:, minimum_frames - 1:], axis=1) + minimum_frames - 1
        previous_mature = scores[np.arange(positions), mature_ages]
        advances = np.roll(previous_mature, 1) - transition_penalty
        advance_ages[frame] = np.roll(mature_ages, 1)
        if mode == "finite":
            advances[0] = -np.inf
        if age_buckets == 1:
            choices[frame] = advances > previous_mature
            next_scores = np.maximum(previous_mature, advances)[:, None]
        else:
            next_scores = np.full_like(scores, -np.inf)
            next_scores[:, 0] = advances
            if age_buckets > 2:
                next_scores[:, 1:-1] = scores[:, :-2]
            choices[frame] = scores[:, -2] > scores[:, -1]
            next_scores[:, -1] = np.maximum(scores[:, -1], scores[:, -2])
        scores = next_scores + emissions[frame, :, None]
    ends = np.arange(positions) if end_policy == "any" else np.array([positions - 1])
    position = int(ends[np.argmax(scores[ends, -1])])
    total = float(scores[position, -1])
    if not math.isfinite(total):
        raise ValueError("No path satisfies this finite sequence, endpoint policies and minimum duration")
    age, path = age_buckets - 1, np.empty(frame_count, dtype=np.int32)
    for frame in range(frame_count - 1, -1, -1):
        path[frame] = position
        if not frame:
            break
        if age_buckets == 1:
            if choices[frame, position]:
                position = (position - 1) % positions
        elif age == 0:
            previous_age = int(advance_ages[frame, position])
            position = (position - 1) % positions
            age = previous_age
        elif age == age_buckets - 1:
            if choices[frame, position]:
                age -= 1
        else:
            age -= 1
    return path, total


def _events(labels: list[str], path: np.ndarray, hop: int, sample_rate: int, duration: float,
            *, preserve_path_positions: bool = True) -> list[dict]:
    events = []
    for index, label in enumerate(labels):
        position = int(path[index])
        # Keep repeated identical chart positions separate when the supplied
        # sequence explicitly contains adjacent identical chords.
        if events and events[-1]["label"] == label and (events[-1]["sequence_index"] == position or (
                not preserve_path_positions and label in ("N", "X"))):
            events[-1]["end_seconds"] = min(duration, (index + 1) * hop / sample_rate)
            events[-1]["_frame_end"] = index + 1
            if position not in events[-1]["sequence_indices"]:
                events[-1]["sequence_indices"].append(position)
                events[-1]["sequence_index"] = None
        else:
            events.append({"start_seconds": index * hop / sample_rate,
                           "end_seconds": min(duration, (index + 1) * hop / sample_rate),
                           "label": label, "sequence_index": position,
                           "sequence_indices": [position],
                           "_frame_start": index, "_frame_end": index + 1})
    return events


def align(audio_path: Path, chart_path: Path, *, hop_seconds: float = 0.025,
          window_seconds: float = 0.18, min_chord_seconds: float = 0.15,
          transition_penalty: float = 0.12, unknown_score: float = 0.45,
          mismatch_margin: float = 0.30, max_audio_seconds: float = 600,
          evidence_json: Path | None = None) -> dict:
    started = time.perf_counter()
    for name, value in (("hop_seconds", hop_seconds), ("window_seconds", window_seconds),
                        ("min_chord_seconds", min_chord_seconds), ("max_audio_seconds", max_audio_seconds)):
        if not _number(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if not _number(transition_penalty) or transition_penalty < 0:
        raise ValueError("transition_penalty must be finite and nonnegative")
    if not _number(unknown_score) or not 0 <= unknown_score <= 1:
        raise ValueError("unknown_score must be between zero and one")
    if not _number(mismatch_margin) or not 0 <= mismatch_margin <= 1:
        raise ValueError("mismatch_margin must be between zero and one")
    chart_bytes = chart_path.read_bytes()
    chart = json.loads(chart_bytes)
    validate_untimed_chart(chart)
    signal, sample_rate = lab.read_wav(audio_path)
    if not len(signal):
        raise ValueError("Audio is empty")
    audio_hash = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    expected_hash = chart["recording"].get("audio_sha256")
    if expected_hash is not None and expected_hash != audio_hash:
        raise ValueError("recording.audio_sha256 does not match the supplied audio")
    duration = len(signal) / sample_rate
    if duration + 1e-12 < min_chord_seconds:
        raise ValueError("Audio duration is shorter than the requested minimum chord duration")
    if duration > max_audio_seconds:
        raise ValueError(f"Audio exceeds the experimental {max_audio_seconds:g}-second bound")
    evidence = features(signal, sample_rate, hop_seconds, window_seconds)
    chroma, silent = evidence["chroma"], evidence["silent"]
    acoustic_input = {"backend": "spectral", "sampling": "direct spectral chroma on decoder grid",
                      "silence_mask": "original PCM RMS on decoder analysis window"}
    if evidence_json is not None:
        chroma, acoustic_input = acoustic_evidence(audio_path, evidence_json, chart["recording"]["id"],
                                                  evidence, sample_rate)
    if chart["schema_version"] == SECTION_SCHEMA:
        sequence, section_mapping = expand_sections(chart)
    else:
        sequence, section_mapping = chart["sequence"], []
    harmonic_templates = [chord_template(label) for label in sequence]
    acoustic = np.zeros((len(chroma), len(sequence)))
    emissions = np.zeros_like(acoustic)
    for position, template in enumerate(harmonic_templates):
        if template is not None:
            acoustic[:, position] = np.einsum("ij,j->i", chroma, template)
            emissions[:, position] = np.where(silent, 0, acoustic[:, position])
        elif sequence[position] == "N":
            emissions[:, position] = np.where(silent, 1, -1)
        # Explicit X has neutral acoustic emission, and stays X in the output.
    vocabulary = [(root + suffix, chord_template(root + suffix))
                  for root in lab.NOTES for suffix in QUALITIES]
    vocabulary_scores = np.einsum("ij,kj->ik", chroma, np.array([template for _, template in vocabulary]))
    best_positions = np.argmax(vocabulary_scores, axis=1)
    best_scores = vocabulary_scores[np.arange(len(chroma)), best_positions]
    mode = chart.get("mode", "finite")
    start_policy = chart.get("start_policy", "first")
    end_policy = chart.get("end_policy", "last" if mode == "finite" else "any")
    minimum_frames = max(1, math.ceil(min_chord_seconds * sample_rate / evidence["hop_samples"]))
    hop_duration = evidence["hop_samples"] / sample_rate
    final_interval = duration - (len(chroma) - 1) * hop_duration
    terminal_minimum_frames = max(minimum_frames, math.ceil((min_chord_seconds - final_interval) / hop_duration - 1e-10) + 1)
    path, path_score = constrained_path(emissions, minimum_frames, transition_penalty,
                                       mode, start_policy, end_policy, terminal_minimum_frames)
    assigned_scores = acoustic[np.arange(len(path)), path]
    deficits = best_scores - assigned_scores
    supplied_labels = [sequence[int(position)] for position in path]
    harmonic_assigned = np.array([harmonic_templates[int(position)] is not None for position in path])
    # These are conservative, tunable screening rules, not probability estimates.
    acoustic_mismatch = (~silent & harmonic_assigned
                         & ((assigned_scores < unknown_score) | (deficits > mismatch_margin)))
    explicit_n_conflict = ~silent & np.array([label == "N" for label in supplied_labels])
    acoustic_mismatch |= explicit_n_conflict
    output_labels = ["N" if silent[frame] else "X" if acoustic_mismatch[frame]
                     else label for frame, label in enumerate(supplied_labels)]
    proposed = _events(supplied_labels, path, evidence["hop_samples"], sample_rate, duration)
    output = _events(output_labels, path, evidence["hop_samples"], sample_rate, duration,
                     preserve_path_positions=False)

    def attach_raw_scores(event):
        start, end = event.pop("_frame_start"), event.pop("_frame_end")
        active = ~silent[start:end]
        rows = np.arange(start, end)[active]
        event["evidence"] = {
            "score_kind": "template cosine similarity (not probability)",
            "active_frames": int(active.sum()),
            "assigned_cosine_mean": float(assigned_scores[rows].mean()) if len(rows) else None,
            "best_vocabulary_cosine_mean": float(best_scores[rows].mean()) if len(rows) else None,
            "best_minus_assigned_cosine_mean": float(deficits[rows].mean()) if len(rows) else None,
            "acoustic_mismatch_fraction": float(acoustic_mismatch[rows].mean()) if len(rows) else None,
        }
    for event in proposed + output:
        attach_raw_scores(event)
    active = ~silent
    active_count = int(active.sum())
    mismatch_fraction = float(acoustic_mismatch[active].mean()) if active_count else None
    conflicting_events = [index for index, event in enumerate(proposed)
                          if event["evidence"]["acoustic_mismatch_fraction"] is not None
                          and event["evidence"]["acoustic_mismatch_fraction"] > 0.4]
    unvisited = sorted(set(range(len(sequence))) - set(map(int, path)))
    indistinguishable_pairs = []
    for position in range(len(sequence) if mode == "cyclic" and len(sequence) > 1 else len(sequence) - 1):
        following = (position + 1) % len(sequence)
        first, second = harmonic_templates[position], harmonic_templates[following]
        if (first is None and second is None and sequence[position] == sequence[following]) or (
                first is not None and second is not None and np.array_equal(first, second)):
            indistinguishable_pairs.append([position, following])
    transitions = int(np.count_nonzero(path[1:] != path[:-1]))
    wraps = int(np.count_nonzero((path[:-1] == len(sequence) - 1) & (path[1:] == 0))) if len(sequence) > 1 else 0
    if not active_count:
        fit_status = "no_harmonic_evidence"
    elif mismatch_fraction > 0.1 or conflicting_events or unvisited or indistinguishable_pairs:
        fit_status = "needs_review"
    else:
        fit_status = "no_large_mismatch_detected"
    metadata = chart.get("metadata", {})
    source_references = metadata.get("source_references", [])
    result = {
        "schema_version": "1.0",
        "recording": {**chart["recording"], "duration_seconds": duration,
                      "sample_rate_hz": sample_rate,
                      "audio_sha256": audio_hash,
                      "provenance": "Local audio; acquisition/permission tracked separately from this aligner"},
        "analysis": {"id": f"known-chart-viterbi-{VERSION}", "algorithm": "known-chart-viterbi",
                     "version": VERSION, "runtime_seconds": time.perf_counter() - started,
                     "parameters": {"hop_samples": evidence["hop_samples"], "frame_size": evidence["frame_size"],
                                    "min_chord_seconds": min_chord_seconds, "minimum_frames": minimum_frames,
                                    "nominal_interior_grid_dwell_seconds": minimum_frames * evidence["hop_samples"] / sample_rate,
                                    "terminal_minimum_frames": terminal_minimum_frames,
                                    "minimum_dwell_applies_to": "proposed chart positions; N/X acoustic masks may be shorter",
                                    "transition_penalty": transition_penalty, "unknown_score": unknown_score,
                                    "mismatch_margin": mismatch_margin, "silence_rms_threshold": evidence["silence_rms_threshold"],
                                    "maximum_audio_seconds": max_audio_seconds, "forced_beat_grid": False,
                                    "acoustic_backend": acoustic_input["backend"],
                                    "runtime_semantics": ("spectral feature extraction and alignment" if evidence_json is None
                                                          else "alignment, original PCM silence mask and cached-evidence loading; native extraction measured separately"),
                                    "key_or_capo_adjustment": "none; supplied labels must already be sounding chords",
                                    "source_separation": "none"}},
        "chords": output,
        "alignment_input": {"schema_version": chart["schema_version"], "sequence": sequence, "mode": mode,
                            "start_policy": start_policy, "end_policy": end_policy, "metadata": metadata,
                            "chart_sha256": hashlib.sha256(chart_bytes).hexdigest(),
                            "source_references_sha256": hashlib.sha256(json.dumps(source_references, sort_keys=True,
                                                                  ensure_ascii=False).encode()).hexdigest()},
        "alignment_evidence": {
            "acoustic_input": acoustic_input,
            "diagnostics": {"acoustic_fit_status": fit_status, "always_requires_human_review": True,
                            "score_is_calibrated_confidence": False, "active_frames": active_count,
                            "silent_frame_fraction": float(silent.mean()), "active_mismatch_fraction": mismatch_fraction,
                            "conflicting_proposed_event_indices": conflicting_events,
                            "unvisited_sequence_indices": unvisited, "path_transitions": transitions,
                            "acoustically_indistinguishable_sequence_position_pairs": indistinguishable_pairs,
                            "cycle_wraps_observed": wraps, "viterbi_objective": path_score},
            "proposed_path_events_before_gap_mask": proposed,
            "frame_columns": ["time_seconds", "sequence_index", "assigned_cosine", "best_vocabulary_label",
                              "best_vocabulary_cosine", "rms", "silent", "acoustic_mismatch"],
            "frames": [[frame * evidence["hop_samples"] / sample_rate, int(path[frame]),
                        float(assigned_scores[frame]), vocabulary[int(best_positions[frame])][0],
                        float(best_scores[frame]), float(evidence["rms"][frame]),
                        bool(silent[frame]), bool(acoustic_mismatch[frame])] for frame in range(len(path))],
            "limitations": ["Labels and sequence are given inputs; agreement with those labels is not recognition accuracy.",
                            "This template-scored alignment has not been validated on a representative catalogue.",
                            "Cyclic mode assumes the exact ordered loop; it cannot discover verse/chorus structure.",
                            "Frame resolution and analysis windows limit boundary precision; no beat grid is imposed.",
                            "Cosine scores, mismatch thresholds and endpoint constraints require review; there is no calibrated confidence.",
                            "Templates ignore slash-bass voicing, tuning deviation, instrument identity and key/capo metadata.",
                            "A missing or wrong chart may produce a forced path; inspect X gaps, proposed events and diagnostics."]},
    }
    if section_mapping:
        result["alignment_input"].update(sections=chart["sections"], order=chart["order"],
                                         expanded_position_sections=section_mapping)
        intervals = []
        for frame, position in enumerate(path):
            section = section_mapping[int(position)]
            key = (section["order_index"], section["repeat_index"])
            end = min(duration, (frame + 1) * evidence["hop_samples"] / sample_rate)
            if intervals and (intervals[-1]["order_index"], intervals[-1]["repeat_index"]) == key:
                intervals[-1]["end_seconds"] = end
            else:
                intervals.append({key: value for key, value in section.items() if key != "chord_index"}
                                 | {"start_seconds": frame * evidence["hop_samples"] / sample_rate,
                                    "end_seconds": end, "status": "proposed; requires listening review"})
        result["alignment_evidence"]["section_intervals_from_proposed_path"] = intervals
        result["alignment_evidence"]["limitations"].append(
            "Section order and repeat counts are declared inputs, not discovered song structure; wrong repeats can force drift.")
    lab.validate_chart(result)
    return result


def check_output_path(output_path: Path, protected_inputs: list[Path], *, overwrite: bool) -> None:
    for source in protected_inputs:
        if output_path.resolve() == source.resolve() or (
                output_path.exists() and source.exists() and output_path.samefile(source)):
            raise ValueError("Output cannot overwrite or alias an input file")
    if output_path.is_symlink():
        raise ValueError("Output cannot be a symlink")
    if output_path.exists() and not overwrite:
        raise ValueError("Output exists; use --overwrite to replace a prior result")
    if output_path.exists() and not output_path.is_file():
        raise ValueError("Output must be a regular file")


def write_json_safely(output_path: Path, value: dict, protected_inputs: list[Path], *, overwrite: bool = False) -> None:
    """Publish a complete JSON file without following aliases or racing creation."""
    check_output_path(output_path, protected_inputs, overwrite=overwrite)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{output_path.name}.",
                                         dir=output_path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        check_output_path(output_path, protected_inputs, overwrite=overwrite)
        if overwrite:
            # Replaces the directory entry atomically; never writes through a
            # symlink or existing hardlink inode, even if one appears now.
            os.replace(temporary, output_path)
        else:
            # Creation is exclusive. A concurrent new file must remain intact.
            try:
                os.link(temporary, output_path)
            except FileExistsError as error:
                raise ValueError("Output appeared concurrently; refusing to overwrite it") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def align_to_file(audio_path: Path, chart_path: Path, output_path: Path, *, overwrite: bool = False, **parameters) -> dict:
    protected = [audio_path, chart_path]
    if parameters.get("evidence_json") is not None:
        protected.append(parameters["evidence_json"])
    check_output_path(output_path, protected, overwrite=overwrite)
    result = align(audio_path, chart_path, **parameters)
    write_json_safely(output_path, result, protected, overwrite=overwrite)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("align")
    command.add_argument("--audio", type=Path, required=True)
    command.add_argument("--chart", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--overwrite", action="store_true")
    command.add_argument("--evidence-json", type=Path,
                         help="Optional hash-paired NNLS-Chroma acoustic evidence; default is direct spectral chroma")
    command.add_argument("--hop-seconds", type=float, default=0.025)
    command.add_argument("--window-seconds", type=float, default=0.18)
    command.add_argument("--min-chord-seconds", type=float, default=0.15)
    command.add_argument("--transition-penalty", type=float, default=0.12)
    command.add_argument("--unknown-score", type=float, default=0.45)
    command.add_argument("--mismatch-margin", type=float, default=0.30)
    command.add_argument("--max-audio-seconds", type=float, default=600)
    arguments = vars(parser.parse_args())
    arguments.pop("command")
    audio, chart, output = (arguments.pop(key) for key in ("audio", "chart", "output"))
    try:
        result = align_to_file(audio, chart, output, **arguments)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Alignment failed: {error}\n")
    print(json.dumps({"output": str(output), "runtime_seconds": result["analysis"]["runtime_seconds"],
                      "diagnostics": result["alignment_evidence"]["diagnostics"]}, indent=2))


if __name__ == "__main__":
    main()
