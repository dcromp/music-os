"""Research acceptance guards for timing a supplied, strictly untimed chart.

The frozen chart_aligner remains the control. This variant uses its unchanged
acoustic features and templates, but cannot spend silent frames traversing a
harmonic sequence. Quality checks can abstain to X; they never invent a replacement
chord. Passing these uncalibrated checks does not verify a song arrangement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time

import numpy as np

import chart_aligner as frozen
import lab

VERSION = "0.1.0"
ADDED_TONE_BASE = {"7": "", "maj7": "", "m7": "m", "dim7": "dim",
                   "7sus4": "sus4", "add9": ""}
DEFAULTS = {"hop_seconds": .025, "window_seconds": .18,
            "min_chord_seconds": .15, "transition_penalty": .12,
            "unknown_score": .45, "mismatch_margin": .30,
            "quality_margin": .04, "added_tone_ratio": .12,
            "added_tone_fraction": .50, "max_audio_seconds": 600}


def _semantics(label: str) -> tuple[int, str] | None:
    frozen.chord_template(label)  # Validate with the frozen supported vocabulary.
    if label in ("N", "X"):
        return None
    match = re.fullmatch(r"([A-G])([#b]?)([^/]*)(?:/([A-G][#b]?|[b#]?[1-7]))?", label)
    root = (frozen.ROOTS[match[1]] + {"": 0, "#": 1, "b": -1}[match[2]]) % 12
    if match[3].lstrip(":") == "sus4(7)":
        raise ValueError("sus4(7) is unsupported: scale-degree 7 is not dominant flat-7; use explicit 7sus4 for that quality")
    quality = frozen.ALIASES.get(match[3].lstrip(":"), match[3].lstrip(":"))
    return root, quality


def _validate_parameters(parameters: dict) -> None:
    for name in ("hop_seconds", "window_seconds", "min_chord_seconds", "max_audio_seconds"):
        if not frozen._number(parameters[name]) or parameters[name] <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if not frozen._number(parameters["transition_penalty"]) or parameters["transition_penalty"] < 0:
        raise ValueError("transition_penalty must be finite and nonnegative")
    for name in ("unknown_score", "mismatch_margin", "quality_margin", "added_tone_ratio", "added_tone_fraction"):
        if not frozen._number(parameters[name]) or not 0 <= parameters[name] <= 1:
            raise ValueError(f"{name} must be between zero and one")


def _local_fraction(values: np.ndarray, active: np.ndarray, window_frames: int) -> np.ndarray:
    """Centered active-frame proportion, with clipped edges and no silence votes."""
    frames = len(active)
    left = np.maximum(0, np.arange(frames) - window_frames // 2)
    right = np.minimum(frames, np.arange(frames) + (window_frames + 1) // 2)
    numerator = np.r_[0, np.cumsum(values & active)]
    denominator = np.r_[0, np.cumsum(active)]
    count = denominator[right] - denominator[left]
    return np.divide(numerator[right] - numerator[left], count,
                     out=np.zeros(frames, dtype=float), where=count > 0)


def quality_evidence(chroma: np.ndarray, silent: np.ndarray, sequence: list[str], *,
                     quality_margin: float, added_tone_ratio: float,
                     added_tone_fraction: float, support_window_frames: int) -> dict:
    """Uncalibrated same-root competition and extra-tone support, never gold.

    A same-root alternative may win by no more than quality_margin. For an
    extension, every added pitch class must exceed added_tone_ratio times the
    median base-chord activation in enough local active frames. A failed guard
    produces X, not the highest-scoring alternative. Slash bass is not modeled.
    """
    chroma = np.asarray(chroma, dtype=float)
    silent = np.asarray(silent, dtype=bool)
    if chroma.ndim != 2 or chroma.shape[1] != 12 or len(silent) != len(chroma) or not len(chroma):
        raise ValueError("Expected nonempty frames × 12 chroma and matching silence mask")
    if not np.isfinite(chroma).all() or np.any(chroma < 0):
        raise ValueError("Chroma must be finite and nonnegative")
    if isinstance(support_window_frames, bool) or not isinstance(support_window_frames, int) or support_window_frames < 1:
        raise ValueError("support_window_frames must be a positive integer")
    for name, value in (("quality_margin", quality_margin), ("added_tone_ratio", added_tone_ratio),
                        ("added_tone_fraction", added_tone_fraction)):
        if not frozen._number(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be between zero and one")
    shape = (len(chroma), len(sequence))
    deficits, ratios, fractions = np.zeros(shape), np.ones(shape), np.ones(shape)
    competing_labels = np.empty(shape, dtype=object)
    margin_reject = np.zeros(shape, dtype=bool)
    tone_reject = np.zeros(shape, dtype=bool)
    cache = {}
    for position, label in enumerate(sequence):
        semantics = _semantics(label)
        if semantics is None:
            competing_labels[:, position] = label
            continue
        root, quality = semantics
        if root not in cache:
            names = [lab.NOTES[root] + suffix for suffix in frozen.QUALITIES]
            templates = np.array([frozen.chord_template(name) for name in names])
            scores = np.einsum("ij,kj->ik", chroma, templates)
            winners = np.argmax(scores, axis=1)
            cache[root] = scores[np.arange(len(chroma)), winners], np.array(names, dtype=object)[winners]
        best_scores, names = cache[root]
        assigned = np.einsum("ij,j->i", chroma, frozen.chord_template(label))
        deficits[:, position] = np.maximum(0, best_scores - assigned)
        competing_labels[:, position] = names
        margin_reject[:, position] = ~silent & (deficits[:, position] > quality_margin + 1e-12)
        if quality in ADDED_TONE_BASE:
            base_quality = ADDED_TONE_BASE[quality]
            base = (root + np.array(frozen.QUALITIES[base_quality])) % 12
            extras = sorted(set((root + np.array(frozen.QUALITIES[quality])) % 12) - set(base))
            base_activation = np.median(chroma[:, base], axis=1)
            extra_activation = np.min(chroma[:, extras], axis=1)
            ratio = np.divide(extra_activation, base_activation,
                              out=np.zeros(len(chroma)), where=base_activation > 1e-12)
            # Zero base activation is unsupported, even when the threshold is zero.
            supported = (base_activation > 1e-12) & (ratio + 1e-12 >= added_tone_ratio)
            fraction = _local_fraction(supported, ~silent, support_window_frames)
            ratios[:, position], fractions[:, position] = ratio, fraction
            tone_reject[:, position] = ~silent & (fraction + 1e-12 < added_tone_fraction)
    return {"same_root_deficit": deficits, "same_root_best_label": competing_labels,
            "added_tone_ratio": ratios, "added_tone_support_fraction": fractions,
            "same_root_quality_reject": margin_reject, "added_tone_reject": tone_reject}


def evidence_path(emissions: np.ndarray, supports: np.ndarray, pause: np.ndarray, *,
                  minimum_frames: int, terminal_minimum_frames: int,
                  transition_penalty: float, mode: str, start_policy: str,
                  end_policy: str, max_decoder_cells: int = 80_000_000) -> tuple[np.ndarray, float, dict]:
    """Adjacent-only path with active matched dwell; infeasible ends abstain.

    A support increments age, a pause preserves age, and a conflict resets age.
    Promotion needs a mature predecessor AND support on the new position's
    current frame. Harmonic silence is always a pause, never a support. The
    finite endpoint is never satisfied merely by spending time in silence.
    """
    emissions = np.asarray(emissions, dtype=float)
    supports, pause = np.asarray(supports, dtype=bool), np.asarray(pause, dtype=bool)
    if emissions.ndim != 2 or not emissions.size or supports.shape != emissions.shape or pause.shape != emissions.shape:
        raise ValueError("Expected nonempty equally sized emissions, support and pause matrices")
    if not np.isfinite(emissions).all() or np.any(supports & pause):
        raise ValueError("Emissions must be finite and support/pause disjoint")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
           for value in (minimum_frames, terminal_minimum_frames, max_decoder_cells)):
        raise ValueError("Dwell and decoder bound must be positive integers")
    if mode not in ("finite", "cyclic") or start_policy not in ("first", "any") or end_policy not in ("last", "any"):
        raise ValueError("Unsupported path policies")
    if not frozen._number(transition_penalty) or transition_penalty < 0:
        raise ValueError("transition_penalty must be finite and nonnegative")
    count, positions = emissions.shape
    cap = max(minimum_frames, terminal_minimum_frames)
    if 2 * cap + 1 >= np.iinfo(np.uint16).max or count * positions * (cap + 1) > max_decoder_cells:
        raise ValueError("Active-evidence decoder exceeds its bounded backpointer allocation")
    unavailable = np.iinfo(np.uint16).max
    previous = np.full((positions, cap + 1), -np.inf)
    starts = np.arange(positions) if start_policy == "any" else np.array([0])
    previous[starts, supports[0, starts].astype(int)] = emissions[0, starts]
    back = np.full((count, positions, cap + 1), unavailable, dtype=np.uint16)
    ages = np.arange(cap + 1, dtype=np.uint16)
    for frame in range(1, count):
        following = np.full_like(previous, -np.inf)
        parents = back[frame]
        matched, paused = supports[frame], pause[frame]
        reset = ~(matched | paused)
        following[paused] = previous[paused]
        parents[paused] = ages
        following[matched, 1:] = previous[matched, :-1]
        parents[matched, 1:] = ages[:-1]
        capped_stay = matched & (previous[:, cap] >= previous[:, cap - 1])
        following[capped_stay, cap] = previous[capped_stay, cap]
        parents[capped_stay, cap] = cap
        reset_ages = np.argmax(previous, axis=1)
        following[reset, 0] = previous[np.flatnonzero(reset), reset_ages[reset]]
        parents[reset, 0] = reset_ages[reset]
        mature_ages = np.argmax(previous[:, minimum_frames:], axis=1) + minimum_frames
        mature = previous[np.arange(positions), mature_ages]
        advances = np.roll(mature, 1) - transition_penalty
        if mode == "finite":
            advances[0] = -np.inf
        advanced = matched & (advances > following[:, 1])
        following[advanced, 1] = advances[advanced]
        # A flag plus the mature predecessor's age supports cap > minimum_frames.
        parents[advanced, 1] = cap + 1 + np.roll(mature_ages, 1)[advanced]
        previous = following + emissions[frame, :, None]
    ends = np.arange(positions) if end_policy == "any" else np.array([positions - 1])
    terminal = previous[ends, terminal_minimum_frames:]
    reachable = bool(np.isfinite(terminal).any())
    if reachable:
        flat = int(np.argmax(terminal))
        endpoint, age = np.unravel_index(flat, terminal.shape)
        position, age = int(ends[endpoint]), int(age + terminal_minimum_frames)
    else:
        # Prefer the highest-scoring partial path. No artificial unseen positions
        # are appended and no final endpoint is claimed.
        position, age = map(int, np.unravel_index(np.argmax(previous), previous.shape))
    total = float(previous[position, age])
    if not math.isfinite(total):
        raise ValueError("No starting state is reachable")
    terminal_age, final_position = age, position
    path = np.empty(count, dtype=np.int32)
    for frame in range(count - 1, -1, -1):
        path[frame] = position
        if not frame:
            break
        parent = int(back[frame, position, age])
        if parent == unavailable:
            raise ValueError("Unreachable active-evidence backpointer")
        if parent > cap:
            age = parent - cap - 1
            position = (position - 1) % positions
        else:
            age = parent
    return path, total, {"endpoint_reached": reachable, "partial": not reachable,
                         "terminal_sequence_index": final_position,
                         "terminal_active_evidence_age_frames": terminal_age}


def align(audio_path: Path, chart_path: Path, *, hop_seconds: float = .025,
          window_seconds: float = .18, min_chord_seconds: float = .15,
          transition_penalty: float = .12, unknown_score: float = .45,
          mismatch_margin: float = .30, quality_margin: float = .04,
          added_tone_ratio: float = .12, added_tone_fraction: float = .50,
          max_audio_seconds: float = 600, evidence_json: Path | None = None) -> dict:
    started = time.perf_counter()
    parameters = {name: value for name, value in locals().copy().items() if name in DEFAULTS}
    _validate_parameters(parameters)
    chart_bytes = chart_path.read_bytes()
    chart = json.loads(chart_bytes)
    frozen.validate_untimed_chart(chart)
    signal, sample_rate = lab.read_wav(audio_path)
    if not len(signal):
        raise ValueError("Audio is empty")
    duration = len(signal) / sample_rate
    if duration > max_audio_seconds:
        raise ValueError("Audio exceeds the experimental bound")
    audio_hash = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    if chart["recording"].get("audio_sha256") not in (None, audio_hash):
        raise ValueError("recording.audio_sha256 does not match supplied audio")
    # Deliberately call the frozen function so a serial evaluator can cache the
    # identical spectral evidence for old and guarded paths without re-extraction.
    evidence = frozen.features(signal, sample_rate, hop_seconds, window_seconds)
    chroma, silent = evidence["chroma"], evidence["silent"]
    acoustic_input = {"backend": "spectral", "sampling": "unchanged frozen spectral chroma on decoder grid",
                      "silence_mask": "unchanged original PCM RMS on frozen analysis window"}
    if evidence_json is not None:
        chroma, acoustic_input = frozen.acoustic_evidence(audio_path, evidence_json,
                                                         chart["recording"]["id"], evidence, sample_rate)
    if chart["schema_version"] == frozen.SECTION_SCHEMA:
        sequence, section_mapping = frozen.expand_sections(chart)
    else:
        sequence, section_mapping = chart["sequence"], []
    for label in sequence:
        _semantics(label)
    count, positions = len(chroma), len(sequence)
    templates = [frozen.chord_template(label) for label in sequence]
    acoustic = np.zeros((count, positions))
    emissions = np.zeros_like(acoustic)
    for position, template in enumerate(templates):
        if template is not None:
            acoustic[:, position] = np.einsum("ij,j->i", chroma, template)
            emissions[:, position] = np.where(silent, 0, acoustic[:, position])
        elif sequence[position] == "N":
            emissions[:, position] = np.where(silent, 1, -1)
    vocabulary = [(root + suffix, frozen.chord_template(root + suffix))
                  for root in lab.NOTES for suffix in frozen.QUALITIES]
    scores = np.einsum("ij,kj->ik", chroma, np.array([template for _, template in vocabulary]))
    best = np.argmax(scores, axis=1)
    best_scores = scores[np.arange(count), best]
    harmonic = np.array([template is not None for template in templates])
    base_match = (~silent[:, None] & harmonic[None, :]
                  & (acoustic >= unknown_score)
                  & (best_scores[:, None] - acoustic <= mismatch_margin))
    support = base_match.copy()
    pauses = np.zeros_like(support)
    for position, label in enumerate(sequence):
        if label == "N":
            support[:, position] = silent
        elif label == "X":
            support[:, position] = ~silent
            pauses[:, position] = silent
        else:
            pauses[:, position] = silent
    hop = evidence["hop_samples"]
    hop_duration = hop / sample_rate
    minimum_frames = max(1, math.ceil(min_chord_seconds / hop_duration))
    final_interval = duration - (count - 1) * hop_duration
    terminal_minimum = max(minimum_frames, math.ceil((min_chord_seconds - final_interval) / hop_duration - 1e-10) + 1)
    mode = chart.get("mode", "finite")
    start_policy = chart.get("start_policy", "first")
    end_policy = chart.get("end_policy", "last" if mode == "finite" else "any")
    path, objective, endpoint = evidence_path(emissions, support, pauses,
        minimum_frames=minimum_frames, terminal_minimum_frames=terminal_minimum,
        transition_penalty=transition_penalty, mode=mode,
        start_policy=start_policy, end_policy=end_policy)
    quality = quality_evidence(chroma, silent, sequence, quality_margin=quality_margin,
                               added_tone_ratio=added_tone_ratio,
                               added_tone_fraction=added_tone_fraction,
                               support_window_frames=minimum_frames)
    rows = np.arange(count)
    supplied = [sequence[int(position)] for position in path]
    assigned = acoustic[rows, path]
    same_root_deficit = quality["same_root_deficit"][rows, path]
    quality_reject = (quality["same_root_quality_reject"] | quality["added_tone_reject"])[rows, path]
    selected_support = support[rows, path]
    durations = np.minimum(hop_duration, duration - rows * hop_duration)
    active_seconds, matched_seconds = [], []
    for position in range(positions):
        selected = path == position
        active_seconds.append(float(durations[selected & ~silent].sum()))
        matched_seconds.append(float(durations[selected & support[:, position]].sum()))
    visited = sorted(set(map(int, path)))
    insufficient = [position for position in visited if matched_seconds[position] + 1e-9 < min_chord_seconds]
    reasons, output_labels = [], []
    for frame, position in enumerate(path):
        label, flags = supplied[frame], []
        if silent[frame]:
            output_labels.append("N")
            reasons.append(["explicit_no_chord" if label == "N" else "original_pcm_silence"])
            continue
        if label == "X":
            flags.append("explicit_unknown")
        elif label == "N":
            flags.append("explicit_no_chord_conflicts_with_active_audio")
        else:
            if not selected_support[frame]:
                flags.append("insufficient_global_template_fit")
            if quality["same_root_quality_reject"][frame, position]:
                flags.append("competing_same_root_quality")
            if quality["added_tone_reject"][frame, position]:
                flags.append("unsupported_added_tones")
            if position in insufficient:
                flags.append("insufficient_active_evidence_dwell")
        output_labels.append("X" if flags else label)
        reasons.append(flags)
    rejected = np.array([label == "X" for label in output_labels])
    proposed = frozen._events(supplied, path, hop, sample_rate, duration)
    output = frozen._events(output_labels, path, hop, sample_rate, duration, preserve_path_positions=False)

    def attach(event):
        start, end = event.pop("_frame_start"), event.pop("_frame_end")
        selected = np.arange(start, end)
        active = selected[~silent[selected]]
        event["evidence"] = {"score_kind": "uncalibrated template cosine and pitch-class activation ratios",
            "active_frames": len(active), "active_seconds": float(durations[active].sum()),
            "matched_evidence_seconds": float(durations[selected[selected_support[selected]]].sum()),
            "assigned_cosine_mean": float(assigned[active].mean()) if len(active) else None,
            "best_vocabulary_cosine_mean": float(best_scores[active].mean()) if len(active) else None,
            "best_minus_assigned_cosine_mean": float((best_scores[active] - assigned[active]).mean()) if len(active) else None,
            "same_root_quality_deficit_mean": float(same_root_deficit[active].mean()) if len(active) else None,
            "acoustic_mismatch_fraction": float(rejected[active].mean()) if len(active) else None,
            "reasons": sorted({reason for frame in selected for reason in reasons[frame]})}
    for event in proposed + output:
        attach(event)
    unvisited = sorted(set(range(positions)) - set(visited))
    silent_advances = [frame for frame in range(1, count)
                       if path[frame] != path[frame - 1] and silent[frame] and harmonic[path[frame]]]
    indistinguishable = []
    for position in range(positions if mode == "cyclic" and positions > 1 else positions - 1):
        next_position = (position + 1) % positions
        first, second = templates[position], templates[next_position]
        if (first is not None and second is not None and np.array_equal(first, second)) or (
            first is None and second is None and sequence[position] == sequence[next_position]):
            indistinguishable.append([position, next_position])
    active = ~silent
    active_count = int(active.sum())
    flags_present = bool(np.any(rejected & active) or insufficient or unvisited or indistinguishable)
    if not active_count:
        fit_status = "no_active_harmonic_evidence"
    elif endpoint["partial"]:
        fit_status = "partial_endpoint_abstention"
    elif flags_present:
        fit_status = "needs_review_with_abstentions"
    else:
        fit_status = "no_guard_failure_detected_research_only"
    metadata = chart.get("metadata", {})
    result = {"schema_version": "1.0",
        "recording": {**chart["recording"], "duration_seconds": duration, "sample_rate_hz": sample_rate,
            "audio_sha256": audio_hash, "provenance": "Local research input; acquisition tracked separately"},
        "analysis": {"id": f"guarded-known-chart-{VERSION}", "algorithm": "guarded-known-chart",
            "version": VERSION, "runtime_seconds": time.perf_counter() - started,
            "parameters": {**parameters, "hop_samples": hop, "frame_size": evidence["frame_size"],
                "minimum_frames": minimum_frames, "terminal_minimum_frames": terminal_minimum,
                "silence_rms_threshold": evidence["silence_rms_threshold"],
                "acoustic_backend": acoustic_input["backend"], "forced_beat_grid": False,
                "dwell_semantics": "consecutive supporting active frames, silence pauses, active mismatch resets; N counts silence and X counts active RMS only",
                "promotion_requires": "mature evidence dwell at previous position and support at new position; no harmonic promotion during silence",
                "quality_margin_semantics": "maximum allowed best-same-root-minus-assigned cosine deficit; not probability",
                "added_tone_ratio_semantics": "all extra tones / median base-chord activation",
                "added_tone_fraction_semantics": "minimum centered local active-frame extra-tone support proportion",
                "quality_support_window_frames": minimum_frames,
                "threshold_calibration": "explicit research parameters; default is not tuned to or validated on this input",
                "key_or_capo_adjustment": "none; labels already sounding", "source_separation": "none"}},
        "chords": output,
        "alignment_input": {"schema_version": chart["schema_version"], "sequence": sequence, "mode": mode,
            "start_policy": start_policy, "end_policy": end_policy, "metadata": metadata,
            "chart_sha256": hashlib.sha256(chart_bytes).hexdigest(),
            "source_references_sha256": hashlib.sha256(json.dumps(metadata.get("source_references", []), sort_keys=True,
                 ensure_ascii=False).encode()).hexdigest()},
        "alignment_evidence": {"acoustic_input": acoustic_input,
            "diagnostics": {**endpoint, "acoustic_fit_status": fit_status, "always_requires_human_review": True,
                "accepted_for_playback": False, "arrangement_verified": False,
                "score_is_calibrated_confidence": False, "active_frames": active_count,
                "silent_frame_fraction": float(silent.mean()),
                "active_mismatch_fraction": float(rejected[active].mean()) if active_count else None,
                "rejected_quality_frames": int(quality_reject.sum()),
                "rejected_quality_seconds": float(durations[quality_reject].sum()),
                "quality_abstention_fraction_of_active_audio": float(durations[quality_reject].sum() / durations[active].sum()) if active_count else None,
                "retained_harmonic_seconds": float(sum(durations[frame] for frame, label in enumerate(output_labels) if label not in ("N", "X"))),
                "unvisited_sequence_indices": unvisited, "insufficient_active_evidence_sequence_indices": insufficient,
                "supplied_positions_without_minimum_evidence_count": len(set(insufficient) | set(unvisited)),
                "no_active_evidence_position_count": sum(active_seconds[position] <= 1e-12 for position in visited if harmonic[position]),
                "no_active_evidence_supplied_position_count": sum(active_seconds[position] <= 1e-12 for position in range(positions) if harmonic[position]),
                "near_minimum_active_evidence_sequence_indices": [position for position in visited
                    if harmonic[position] and matched_seconds[position] <= 1.5 * min_chord_seconds + 1e-9],
                "near_minimum_dwell_semantics": "At most 1.5 times the declared minimum supporting evidence; density diagnostic only, not a verified compression error",
                "silent_position_advance_count": len(silent_advances),
                "path_transitions": int(np.count_nonzero(path[1:] != path[:-1])),
                "cycle_wraps_observed": int(np.count_nonzero((path[:-1] == positions - 1) & (path[1:] == 0))) if positions > 1 else 0,
                "acoustically_indistinguishable_sequence_position_pairs": indistinguishable,
                "viterbi_objective": objective,
                "position_active_seconds": active_seconds, "position_matched_evidence_seconds": matched_seconds,
                "compression_warning": "Minimum dwell prevents unsupported silent traversal; extra repeats may still compress across active music. No section correctness guarantee."},
            "proposed_path_events_before_gap_mask": proposed,
            "frame_columns": ["time_seconds", "sequence_index", "assigned_cosine", "best_vocabulary_label",
                "best_vocabulary_cosine", "rms", "silent", "acoustic_mismatch", "same_root_best_label",
                "same_root_quality_deficit", "added_tone_ratio", "added_tone_support_fraction", "matched_dwell_support", "reasons"],
            "frames": [[frame * hop_duration, int(path[frame]), float(assigned[frame]), vocabulary[int(best[frame])][0],
                float(best_scores[frame]), float(evidence["rms"][frame]), bool(silent[frame]), bool(rejected[frame]),
                str(quality["same_root_best_label"][frame, path[frame]]), float(same_root_deficit[frame]),
                float(quality["added_tone_ratio"][frame, path[frame]]), float(quality["added_tone_support_fraction"][frame, path[frame]]),
                bool(selected_support[frame]), reasons[frame]] for frame in range(count)],
            "limitations": ["Supplied labels and order are assumptions; these guards are not independent recognition or calibrated confidence.",
                "Passing heuristics does not verify section order, repeat counts, chart completeness or a recording-specific arrangement.",
                "Plain/rich quality tradeoffs must be reported on independent references; abstention can hide correct chords.",
                "Slash-bass voicing, octave, instrument identity and rearticulation of identical chords are not identifiable in these templates.",
                "An infeasible endpoint produces a partial path with unvisited positions, not invented timing through silence.",
                "The offline centered added-tone window and acoustic windows constrain timing resolution."]}}
    if section_mapping:
        result["alignment_input"].update(sections=chart["sections"], order=chart["order"], expanded_position_sections=section_mapping)
        intervals = []
        for frame, position in enumerate(path):
            section = section_mapping[int(position)]
            key = (section["order_index"], section["repeat_index"])
            end = min(duration, (frame + 1) * hop_duration)
            if intervals and (intervals[-1]["order_index"], intervals[-1]["repeat_index"]) == key:
                intervals[-1]["end_seconds"] = end
                intervals[-1]["active_evidence_seconds"] += float(durations[frame] if selected_support[frame] else 0)
                intervals[-1]["harmonic_active_seconds"] += float(durations[frame] if active[frame] else 0)
            else:
                intervals.append({key: value for key, value in section.items() if key != "chord_index"} | {
                    "start_seconds": frame * hop_duration, "end_seconds": end,
                    "active_evidence_seconds": float(durations[frame] if selected_support[frame] else 0),
                    "harmonic_active_seconds": float(durations[frame] if active[frame] else 0),
                    "status": "unverified research hypothesis"})
        for interval in intervals:
            interval["active_evidence_fraction"] = interval["active_evidence_seconds"] / (interval["end_seconds"] - interval["start_seconds"])
            section_positions = [position for position, mapping in enumerate(section_mapping)
                                 if (mapping["order_index"], mapping["repeat_index"]) == (interval["order_index"], interval["repeat_index"])]
            interval["declared_positions"] = len(section_positions)
            interval["visited_positions"] = sum(position in visited for position in section_positions)
            interval["active_evidence_seconds_per_declared_position"] = interval["active_evidence_seconds"] / len(section_positions)
            interval["near_minimum_evidence_position_count"] = sum(position in visited and harmonic[position]
                and matched_seconds[position] <= 1.5 * min_chord_seconds + 1e-9 for position in section_positions)
        result["alignment_evidence"]["section_intervals_from_proposed_path"] = intervals
        result["alignment_evidence"]["diagnostics"]["zero_active_section_interval_count"] = sum(interval["harmonic_active_seconds"] <= 1e-12 for interval in intervals)
    lab.validate_chart(result)
    return result


def align_to_file(audio_path: Path, chart_path: Path, output_path: Path, *, overwrite: bool = False, **parameters) -> dict:
    protected = [audio_path, chart_path]
    if parameters.get("evidence_json") is not None:
        protected.append(parameters["evidence_json"])
    frozen.check_output_path(output_path, protected, overwrite=overwrite)
    result = align(audio_path, chart_path, **parameters)
    frozen.write_json_safely(output_path, result, protected, overwrite=overwrite)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("align")
    for name in ("audio", "chart", "output"):
        command.add_argument(f"--{name}", type=Path, required=True)
    command.add_argument("--evidence-json", type=Path)
    command.add_argument("--overwrite", action="store_true")
    for name, default in DEFAULTS.items():
        command.add_argument("--" + name.replace("_", "-"), type=float, default=default)
    arguments = vars(parser.parse_args())
    arguments.pop("command")
    audio, chart, output = (arguments.pop(name) for name in ("audio", "chart", "output"))
    try:
        result = align_to_file(audio, chart, output, **arguments)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Guarded alignment failed: {error}\n")
    print(json.dumps({"output": str(output), "diagnostics": result["alignment_evidence"]["diagnostics"]}, indent=2))


if __name__ == "__main__":
    main()
