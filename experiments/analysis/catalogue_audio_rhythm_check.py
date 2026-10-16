"""Exact-audio attack/energy diagnostics; no strum transcription or chart edits.

Full-mix attacks may belong to drums, vocals, bass or guitar. A nearby attack is
neither a harmonic transition nor proof that a proposed chord time is correct.
The short-window clock is tested on synthesized PCM, independently of charts.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import wave
import numpy as np
import catalogue_timing_review as timing
import curation
import rhythm_grid

ROOT = curation.ROOT
SCHEMA = "catalogue-audio-rhythm-check-1.0"
POLICY = {"sample_rate_hz": 22050, "frame_samples": 512, "hop_samples": 128,
          "log_magnitude_gain": 20.0, "local_baseline_seconds": .25,
          "local_mad_multiplier": 2.5, "global_peak_floor_fraction": .05,
          "minimum_attack_separation_seconds": .08,
          "synthetic_match_tolerance_seconds": .04,
          "phase_histogram_bins": 12, "minimum_harmonic_hold_seconds": 5.0,
          "boundary_energy_gap_seconds": .04, "boundary_energy_window_seconds": .12,
          "uses_source_separation": False, "snaps_or_refines_events": False,
          "infers_guitar_or_stroke_direction": False, "accepts_arrangements": False}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and np.isfinite(value)


def signal_features(signal, rate=22050):
    """Centered, zero-padded windows; peak times retain their native frame clock."""
    y = np.asarray(signal, dtype=float)
    if rate != POLICY["sample_rate_hz"] or y.ndim != 1 or not len(y) or not np.all(np.isfinite(y)) or len(y) > rate * 600:
        raise ValueError("Use finite mono PCM, 22050 Hz, at most 600 seconds")
    frame, hop = POLICY["frame_samples"], POLICY["hop_samples"]
    padded = np.pad(y, (frame // 2, frame // 2))
    windows = np.lib.stride_tricks.sliding_window_view(padded, frame)[::hop]
    times = np.arange(len(windows)) * hop / rate
    keep = times < len(y) / rate
    windows, times = windows[keep], times[keep]
    rms = np.empty(len(windows)); flux = np.zeros(len(windows)); previous = None
    for offset in range(0, len(windows), 1024):
        block = windows[offset:offset+1024]
        rms[offset:offset+len(block)] = np.sqrt(np.mean(block * block, axis=1))
        magnitude = abs(np.fft.rfft(block * np.hanning(frame), axis=1)) / frame
        logged = np.log1p(POLICY["log_magnitude_gain"] * magnitude)
        if previous is not None:
            flux[offset] = np.maximum(0, logged[0] - previous).sum()
        flux[offset+1:offset+len(block)] = np.maximum(0, np.diff(logged, axis=0)).sum(axis=1)
        previous = logged[-1]
    radius = max(1, round(POLICY["local_baseline_seconds"] * rate / hop / 2))
    local = np.lib.stride_tricks.sliding_window_view(np.pad(flux, (radius, radius), mode="edge"), 2 * radius + 1)
    median = np.median(local, axis=1)
    mad = np.median(abs(local - median[:, None]), axis=1)
    threshold = median + POLICY["local_mad_multiplier"] * mad + float(flux.max()) * POLICY["global_peak_floor_fraction"]
    candidates = [i for i in range(1, len(flux) - 1)
                  if flux[i] > threshold[i] and flux[i] >= flux[i-1] and flux[i] > flux[i+1]]
    # Fixed strongest-first suppression; do not shift peaks toward chart events.
    separation = POLICY["minimum_attack_separation_seconds"]
    selected = []; suppressed = np.zeros(len(flux), dtype=bool)
    for index in sorted(candidates, key=lambda i: (-flux[i], i)):
        if not suppressed[index]:
            selected.append(index)
            suppressed[np.searchsorted(times, times[index]-separation, side="right"):
                       np.searchsorted(times, times[index]+separation, side="left")] = True
    selected.sort()
    return {"times": times, "rms": rms, "flux": flux,
            "attack_times_seconds": [float(times[i]) for i in selected],
            "attack_flux": [float(flux[i]) for i in selected],
            "duration_seconds": len(y) / rate}


def read_pcm(path, recording):
    rhythm_grid.verify_audio(path, recording)
    with wave.open(str(path), "rb") as stream:
        return np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(float) / 32768


def energy_change(features, at):
    """Adjacent bounded RMS, excluding the central attack/mute neighborhood."""
    if not finite_number(at) or not 0 <= at <= features["duration_seconds"]:
        raise ValueError("Energy target must be inside the exact signal")
    gap, width = POLICY["boundary_energy_gap_seconds"], POLICY["boundary_energy_window_seconds"]
    times, rms = features["times"], features["rms"]
    ranges = ((max(0.0, at-gap-width), max(0.0, at-gap)),
              (min(features["duration_seconds"], at+gap), min(features["duration_seconds"], at+gap+width)))
    values = []
    for first, last in ranges:
        part = rms[(times >= first) & (times < last)]
        values.append(float(np.sqrt(np.mean(part ** 2))) if len(part) else None)
    before, after = values
    return {"at_seconds": at, "before_window_seconds": list(ranges[0]), "after_window_seconds": list(ranges[1]),
            "before_rms": before, "after_rms": after,
            "after_over_before_rms": after / before if before is not None and before > 1e-12 and after is not None else None,
            "semantics": "Full-mix local energy contrast; not an identified guitar mute or harmonic change"}


def match_attacks(reference, prediction, tolerance=None):
    """Ordered maximum-cardinality matching with min total error, not nearest reuse."""
    tolerance = POLICY["synthetic_match_tolerance_seconds"] if tolerance is None else tolerance
    for values in (reference, prediction):
        if any(not finite_number(t) or t < 0 for t in values) or any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError("Attack times must be finite, nonnegative and strictly ordered")
    if not finite_number(tolerance) or tolerance < 0:
        raise ValueError("Use a finite nonnegative match tolerance")
    first = [{"time_seconds": t, "from_key": [0], "to_key": [1]} for t in reference]
    second = [{"time_seconds": t, "from_key": [0], "to_key": [1]} for t in prediction]
    pairs = timing.match_transitions(first, second, tolerance)
    count = len(pairs); errors = [prediction[j] - reference[i] for i, j, _ in pairs]
    return {"reference_attacks": len(reference), "detected_attacks": len(prediction), "matched": count,
            "misses": len(reference) - count, "extras": len(prediction) - count,
            "f1": 2 * count / (len(reference) + len(prediction)) if reference or prediction else 1.0,
            "median_signed_error_seconds": float(np.median(errors)) if errors else None,
            "maximum_absolute_error_seconds": max(map(abs, errors)) if errors else None,
            "pairs": [{"reference_seconds": reference[i], "detected_seconds": prediction[j],
                       "signed_error_seconds": prediction[j] - reference[i]} for i, j, _ in pairs]}


def phase_inventory(attacks, pulses):
    if len(pulses) < 2 or any(not finite_number(t) or t < 0 for t in pulses) or any(a >= b for a, b in zip(pulses, pulses[1:])):
        raise ValueError("Use ordered cached guided pulses")
    phases = []
    for at in attacks:
        i = int(np.searchsorted(pulses, at, side="right")) - 1
        if 0 <= i < len(pulses) - 1:
            phases.append((at - pulses[i]) / (pulses[i+1] - pulses[i]))
    counts, edges = np.histogram(phases, bins=POLICY["phase_histogram_bins"], range=(0, 1))
    return {"covered_attacks": len(phases), "outside_cached_pulse_span": len(attacks) - len(phases),
            "phase_bin_edges": edges.tolist(), "phase_counts": counts.tolist(),
            "semantics": "Full-mix attacks within cached pulse intervals; pulse phase/level is unverified; no swing, subdivision, stroke or downbeat acceptance"}


def plucked_pcm(attacks, *, duration=5.0, decay=.18, slow_attack=0.002, mute_at=None, noise=0.0):
    rate = POLICY["sample_rate_hz"]
    y = np.zeros(round(duration * rate)); rng = np.random.default_rng(3817)
    # C-major harmonic partials; repeated attacks retain identical harmony.
    for at in attacks:
        index = round(at * rate); t = np.arange(len(y) - index) / rate
        envelope = (1 - np.exp(-t / slow_attack)) * np.exp(-t / decay)
        chord = sum(np.sin(2*np.pi*f*t) + .3*np.sin(4*np.pi*f*t) for f in (130.8128, 164.8138, 195.9977)) / 3.9
        y[index:] += .4 * chord * envelope
    if mute_at is not None:
        start = round(mute_at * rate); t = np.arange(len(y)-start) / rate
        y[start:] *= np.maximum(0, 1 - t/.003)
    y += rng.normal(0, noise, len(y))
    return np.rint(np.clip(y, -1, 32767/32768) * 32768).astype("<i2")


def synthetic_controls():
    regular = [.5 + .5*i for i in range(8)]
    eighth = [.5 + .25*i for i in range(16)]
    swing = sorted(.5 + .5*i + offset for i in range(8) for offset in (0, 1/3))
    cases = [("quarter-attacks-same-harmony", regular, {}, "same chord can contain repeated attacks"),
             ("eighth-attacks-same-harmony", eighth, {}, "no harmonic changes implied"),
             ("swung-pair-attacks", swing, {}, "known 2:1 attack spacing, not estimated real-guitar swing"),
             ("skipped-eighth-attack", [t for i, t in enumerate(eighth) if i == 0 or i % 4 != 2], {}, "missing attack does not command muting"),
             ("regular-low-noise", regular, {"noise": .0005}, "bounded seeded noise"),
             ("slow-attack-limitation", regular, {"slow_attack": .08}, "40ms clock tolerance can fail for soft attacks; report without retuning")]
    rows = []
    for name, attacks, options, purpose in cases:
        pcm = plucked_pcm(attacks, **options)
        features = signal_features(pcm.astype(float)/32768)
        row = {"id": name, "purpose": purpose, "reference_attack_times_seconds": attacks,
               "synthesis_parameters": {"duration_seconds": 5.0, "decay_seconds": .18,
                                        "attack_rise_seconds": options.get("slow_attack", .002),
                                        "noise_std": options.get("noise", 0.0), "seed": 3817,
                                        "triad_frequencies_hz": [130.8128, 164.8138, 195.9977]},
               "detected_attack_times_seconds": features["attack_times_seconds"],
               "pcm_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(),
               "pcm_samples": len(pcm), "pcm_format": "mono little-endian PCM16 / 22050 Hz",
               "score": match_attacks(attacks, features["attack_times_seconds"]),
               "phase": phase_inventory(features["attack_times_seconds"], [.5 + .5*i for i in range(10)])}
        rows.append(row)
    energy = []
    for name, muted in (("skipped-attack-continues-ringing", False), ("explicit-three-ms-damp", True)):
        pcm = plucked_pcm([.5], duration=3.0, decay=8.0, mute_at=1.5 if muted else None)
        features = signal_features(pcm.astype(float)/32768)
        energy.append({"id": name, "pcm_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(),
                       "reference_attack_times_seconds": [.5], "reference_damp_seconds": 1.5 if muted else None,
                       "detected_attack_times_seconds": features["attack_times_seconds"],
                       "energy": energy_change(features, 1.5)})
    # Positive-flux detects attacks, not every physical energy change. A mute can
    # have zero detected positive attack; its separate energy ledger remains.
    shifted = match_attacks(regular, [t+.10 for t in regular])
    return {"schema_version": SCHEMA, "policy": POLICY, "cases": rows, "energy_controls": energy,
            "shifted_clock_negative_control": {"shift_seconds": .10, "score": shifted},
            "detector_status": "Exploratory only: substantial extras from harmonic beating and failures on soft attacks; not suitable for automatic strumming transcription",
            "limits": "Procedural PCM mechanics only; no guitar/full-mix transcription accuracy or learned detector selection follows"}


def nearest_attack(at, attacks):
    if not attacks: return {"nearest_attack_seconds": None, "attack_minus_native_seconds": None}
    selected = min(attacks, key=lambda value: (abs(value-at), value))
    return {"nearest_attack_seconds": selected, "attack_minus_native_seconds": selected-at}


def window_diagnostics(features, start, end):
    if not all(finite_number(t) for t in (start, end)) or not 0 <= start < end <= features["duration_seconds"]:
        raise ValueError("Diagnostic window must be inside exact audio")
    mask = (features["times"] >= start) & (features["times"] < end)
    values = features["rms"][mask]; times = features["times"][mask]
    if not len(values): raise ValueError("Diagnostic window needs an RMS frame")
    median = float(np.median(values)); minimum_index = int(np.argmin(values))
    return {"start_seconds": start, "end_seconds": end,
            "full_mix_attack_times_seconds": [t for t in features["attack_times_seconds"] if start <= t < end],
            "rms_minimum": float(values[minimum_index]), "rms_minimum_center_seconds": float(times[minimum_index]),
            "rms_q10": float(np.quantile(values, .1)), "rms_median": median,
            "rms_minimum_over_window_median": float(values[minimum_index])/median if median > 1e-12 else None,
            "start_energy": energy_change(features, start), "end_energy": energy_change(features, end),
            "semantics": "Full-mix transient and local energy observations; no guitar mute, stroke or harmonic-time acceptance"}


def summarize_recording(case, primary, secondary, review, pulse, features, targets=None):
    duration = case["recording"]["duration_seconds"]
    attacks = features["attack_times_seconds"]
    boundaries = {}
    holds = []
    for model, chart in (("btc", primary), ("crema", secondary)):
        changes, _ = timing.transitions(chart)
        values = [{**event, **nearest_attack(event["time_seconds"], attacks),
                   "energy": energy_change(features, event["time_seconds"])} for event in changes]
        offsets = [abs(row["attack_minus_native_seconds"]) for row in values if row["attack_minus_native_seconds"] is not None]
        boundaries[model] = {"native_events": values,
                             "median_nearest_full_mix_attack_distance_seconds": float(np.median(offsets)) if offsets else None,
                             "within_40ms": sum(value <= .04 for value in offsets),
                             "within_150ms": sum(value <= .15 for value in offsets),
                             "semantics": "Descriptive distances to full-mix attacks; no reference timing accuracy or confidence"}
        for span in timing.core_timeline(chart):
            if span["status"] != "chord" or span["end_seconds"]-span["start_seconds"] < POLICY["minimum_harmonic_hold_seconds"]: continue
            start, end = span["start_seconds"], span["end_seconds"]
            local = [t for t in attacks if start <= t < end]
            holds.append({"model": model, "native_span": span, "full_mix_attack_count": len(local),
                          "full_mix_attack_times_seconds": local,
                          "start_energy": energy_change(features, start), "end_energy": energy_change(features, end),
                          "accepted_section_or_rhythm": False})
    windows = []
    # Retain every pre-existing fixed sample/disagreement work item as selected;
    # do not relabel its meaning from this audio feature.
    for point in review["points"]:
        start, end = point["start_seconds"], point["end_seconds"]
        windows.append({"source_point": point, "full_mix_attack_times_seconds": [t for t in attacks if start <= t < end]})
    target_rows = []
    if targets is not None:
        if not curation.identity(case["recording"], targets["recording"]): raise ValueError("Review targets must identify the exact recording")
        for target in targets["source_guided_hold_candidates"]:
            span = target["native_span"]
            target_rows.append({"source_candidate": target, "diagnostics": window_diagnostics(features, span["start_seconds"], span["end_seconds"])})
        for window in targets["boundary_review"]["selected_review_windows"]:
            target_rows.append({"source_selected_timing_window": window, "diagnostics": window_diagnostics(features, window["start_seconds"], window["end_seconds"])})
    return {"id": case["id"], "name": case["name"], "recording": case["recording"],
            "analysis_status": "descriptive full-mix diagnostics; arrangement unaccepted", "gold": False,
            "duration_seconds": duration, "full_mix_attacks": len(attacks),
            "full_mix_attacks_per_second": len(attacks)/duration,
            "attack_times_seconds": attacks, "attack_flux": features["attack_flux"],
            "guided_pulse_bpm": pulse["pulse_bpm"], "guided_pulse_meter_status": pulse["analysis"]["config_status"],
            "phase": phase_inventory(attacks, pulse["beat_times_seconds"]),
            "native_boundaries": boundaries, "native_harmonic_holds": holds,
            "source_guided_and_native_timing_targets": target_rows,
            "existing_review_windows": windows, "physical_timing_accuracy": None,
            "guitar_attack_accuracy": None, "accepted_rhythm": False}


def make_spec(pack, pulses, learner_manifest, config, practice, timing_review):
    return {"schema_version": "catalogue-audio-rhythm-spec-1.0", "policy": POLICY,
            "pack_manifest_sha256": digest(pack / "manifest.json"), "pulse_grid_sha256": digest(pulses),
            "learner_manifest_sha256": digest(learner_manifest), "rhythm_config_sha256": digest(config),
            "practice_sha256": digest(practice),
            "native_timing_review_sha256": digest(timing_review),
            "case_ids": [case["id"] for case in curation.read(pack/"manifest.json")["cases"]],
            "scope": "Retrospective exact-audio diagnostics; no knob tuning against recording outcomes or auto acceptance"}


def run(pack, pulses, learner_manifest, config, practice, spec, output, *, root=ROOT, timing_review=None):
    started = time.perf_counter(); root = root.resolve()
    pack, pulses, learner_manifest, config, practice, spec = (Path(p).resolve(strict=True) for p in (pack, pulses, learner_manifest, config, practice, spec))
    timing_review = (timing_review or root/"experiments/generated/catalogue-change-check-20261016/report.json").resolve(strict=True)
    output = Path(output).absolute()
    if any(not path.is_relative_to(root) for path in (pack, pulses, learner_manifest, config, practice, spec, timing_review, output.resolve())):
        raise ValueError("Keep diagnostics in the repository")
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(pack) or pack.is_relative_to(output.resolve()):
        raise ValueError("Use an unused output separate from input pack")
    files, manifest = curation.public_files(pack)
    expected = make_spec(pack, pulses, learner_manifest, config, practice, timing_review)
    if curation.read(spec) != expected: raise ValueError("Policy or pinned input differs from specification")
    pulse_packet = curation.read(pulses)
    if pulse_packet.get("schema_version") != rhythm_grid.SCHEMA or pulse_packet.get("manifest_sha256") != digest(learner_manifest) or pulse_packet.get("config_sha256") != digest(config):
        raise ValueError("Cached pulses must identify the exact frozen learner manifest and config")
    pulse_cases = {row["recording"]["id"]: row for row in pulse_packet["cases"]}
    if len(pulse_cases) != len(pulse_packet["cases"]) or set(pulse_cases) != set(expected["case_ids"]):
        raise ValueError("Unique pulses for every exact recording required")
    target_packet = curation.read(timing_review)
    if target_packet.get("schema_version") != "catalogue-change-check-1.0": raise ValueError("Use the pinned native timing review")
    target_cases = {row["id"]: row for row in target_packet["cases"]}
    if len(target_cases) != len(target_packet["cases"]) or set(target_cases) != set(expected["case_ids"]):
        raise ValueError("Native targets must identify every exact recording")
    private = pack / "private-drafts"
    if private.is_symlink(): raise ValueError("Private drafts cannot alias another directory")
    original_private = set(private.glob("*.json"))
    if any(path.is_symlink() or not path.is_file() for path in original_private):
        raise ValueError("Private draft snapshots must be regular, non-symlink files")
    methods = [Path(__file__), Path(timing.__file__), Path(curation.__file__), Path(rhythm_grid.__file__),
               Path(timing.core_chord_screen.__file__), Path(timing.lab.__file__),
               Path(curation.review_pack.__file__), Path(curation.drafts.__file__),
               Path(timing.core_chord_screen.rich_quality_suite.__file__)]
    protected = {*files.values(), pulses, learner_manifest, config, practice, spec, timing_review, *original_private, *methods}
    snapshot = {path: digest(path) for path in protected}
    loaded = []
    for case in manifest["cases"]:
        folder = pack / "cases" / case["id"]; pulse = pulse_cases[case["id"]]
        if not curation.identity(case["recording"], pulse["recording"]): raise ValueError("Pulse recording differs from diagnostic input")
        target = target_cases[case["id"]]
        if not curation.identity(case["recording"], target["recording"]) or target.get("native_artifacts") != case.get("artifacts"):
            raise ValueError("Native timing targets differ from exact recording/chart artifacts")
        rhythm_grid.validate_pulses({"pulse_bpm": pulse["pulse_bpm"], "beat_times_seconds": pulse["beat_times_seconds"], "library_version": pulse["analysis"]["library_version"]}, case["recording"]["duration_seconds"])
        loaded.append((case, folder, pulse))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".audio-rhythm-", dir=output.parent))
    try:
        controls = synthetic_controls()
        (staging/"synthetic-controls.json").write_text(json.dumps(controls, indent=2, allow_nan=False)+"\n")
        rows = []
        for case, folder, pulse in loaded:
            y = read_pcm(folder/"audio.wav", case["recording"])
            features = signal_features(y)
            row = summarize_recording(case, curation.read(folder/"primary.json"), curation.read(folder/"crema.json"), curation.read(folder/"review.json"), pulse, features, target_cases[case["id"]])
            (staging/(case["id"]+".json")).write_text(json.dumps(row, indent=2, allow_nan=False)+"\n")
            rows.append({key: row[key] for key in ("id", "name", "recording", "duration_seconds", "full_mix_attacks", "full_mix_attacks_per_second", "guided_pulse_bpm", "guided_pulse_meter_status", "phase")})
            rows[-1]["native_boundary_summary"] = {model: {key: value for key, value in row["native_boundaries"][model].items() if key != "native_events"} for model in ("btc", "crema")}
            rows[-1]["harmonic_hold_windows"] = len(row["native_harmonic_holds"])
        if private.is_symlink() or set(private.glob("*.json")) != original_private or any(path.is_symlink() for path in original_private) or any(not path.exists() or digest(path) != value for path, value in snapshot.items()):
            raise ValueError("Inputs or saved drafts changed during audio diagnostics")
        report = {"schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "policy": POLICY, "status": "unaccepted model-exposed audio diagnostics", "gold": False,
                  "spec_sha256": digest(spec), "method_file_sha256": {str(path.relative_to(root)): snapshot[path] for path in methods},
                  "input_file_sha256": {str(path.relative_to(root)): snapshot[path] for path in protected if path not in methods},
                  "synthetic_controls_sha256": digest(staging/"synthetic-controls.json"),
                  "detector_status": controls["detector_status"],
                  "runtime_seconds": time.perf_counter()-started, "cases": rows,
                  "raw_charts_modified": False, "private_drafts_modified": False,
                  "physical_timing_accuracy": None, "guitar_rhythm_accuracy": None, "human_correction_seconds": None,
                  "limits": ["Attack clocks tested on procedural PCM, not independent real-recording guitar annotations.",
                             "Full-mix transients and RMS can be drums, voice, bass, guitar or overlapping parts.",
                             "Nearest attack is not harmonic evidence; repeated attacks do not require chord changes.",
                             "Energy continuation and damp controls differ; real mix cannot uniquely identify guitar mute.",
                             "Pulse phases are relative to unverified cached metrical hypotheses; no bar, swing or stroke acceptance.",
                             "No chord/pulse times refined, no source-separated inference, no lessons promoted."]}
        (staging/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
        staging.rename(output); return report
    except Exception:
        shutil.rmtree(staging); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=ROOT/"experiments/generated/catalogue-curation-20261014")
    parser.add_argument("--pulses", type=Path, default=ROOT/"experiments/review/rhythm.json")
    parser.add_argument("--learner-manifest", type=Path, default=ROOT/"experiments/generated/automatic-first-ten-v1/manifest.json")
    parser.add_argument("--config", type=Path, default=ROOT/"experiments/fixtures/rhythm-first-ten.json")
    parser.add_argument("--practice", type=Path, default=ROOT/"experiments/review/practice.json")
    parser.add_argument("--timing-review", type=Path, default=ROOT/"experiments/generated/catalogue-change-check-20261016/report.json")
    parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pack, args.pulses, args.learner_manifest, args.config, args.practice, args.spec, args.output, timing_review=args.timing_review)
    print(json.dumps({"cases": len(result["cases"]), "runtime_seconds": result["runtime_seconds"], "output": str(args.output)}, indent=2))


if __name__ == "__main__": main()
