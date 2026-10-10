"""Reproducible synthetic screening. Synthetic success is not real-song accuracy."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import time
import wave

import numpy as np

import lab

SUITE = lab.GENERATED / "synthetic-suite"
SAMPLE_RATE = 22050
LEVELS = {1: "Clean triads", 2: "Voicings and timbres", 3: "Guitar-like attacks",
          4: "Controlled distractors", 5: "Temporal and vocabulary complexity"}


def events_for(recipe: dict) -> list[dict]:
    if recipe["level"] == 1:
        roots = [(recipe["root"], recipe["quality"], 3.0)]
    else:
        transposition = recipe["root"]
        roots = [((root + transposition) % 12, quality, duration) for root, quality, duration in
                 [(0, "", 2.0), (9, "m", 2.0), (5, "", 2.0), (7, "", 2.0)]]
        if recipe["condition"] == "fast_changes":
            roots = [(root, quality, 0.5) for root, quality, _ in roots] * 3
        elif recipe["condition"] == "offbeat_changes":
            roots = [(root, quality, duration) for (root, quality, _), duration in
                     zip(roots, [1.75, 2.25, 1.25, 2.75])]
        elif recipe["condition"] == "tempo_ramp":
            roots = [(root, quality, duration) for (root, quality, _), duration in
                     zip(roots, [2.5, 2.0, 1.5, 1.0])]
    events, start = [{"start_seconds": 0.0, "end_seconds": 0.5, "label": "N"}], 0.5
    for root, quality, duration in roots:
        label = lab.NOTES[root] + quality
        acceptable = None
        if recipe["condition"] == "power_chords":
            label = lab.NOTES[root] + "5"
            acceptable = [lab.NOTES[root], lab.NOTES[root] + "m", label]
        elif recipe["condition"] == "sevenths":
            label = lab.NOTES[root] + ("m7" if quality == "m" else "maj7")
        event = {"start_seconds": start, "end_seconds": start + duration, "label": label,
                 "root_pitch_class": root, "quality": quality}
        if acceptable:
            event["acceptable_labels"] = acceptable
            event["ambiguity"] = "No third; major/minor quality is unspecified"
        events.append(event)
        start += duration
    events.append({"start_seconds": start, "end_seconds": start + 0.5, "label": "N"})
    return events


def oscillator(note: int, t: np.ndarray, timbre: str) -> np.ndarray:
    frequency = 440 * 2 ** ((note - 69) / 12)
    partials = 1 if timbre == "sine" else 5 if timbre == "bright" else 3
    return sum(np.sin(2 * np.pi * frequency * h * t) / (h if timbre == "bright" else h**2)
               for h in range(1, partials + 1))


def render(recipe: dict, events: list[dict]) -> np.ndarray:
    rng = np.random.default_rng(recipe["seed"])
    audio = np.zeros(round(events[-1]["end_seconds"] * SAMPLE_RATE))
    condition = recipe["condition"]
    for event in events:
        if event["label"] == "N":
            continue
        root, quality = event["root_pitch_class"], event["quality"]
        intervals = [0, 3 if quality == "m" else 4, 7]
        if condition == "power_chords":
            intervals = [0, 7, 12]
        elif condition == "sevenths":
            intervals.append(10 if quality == "m" else 11)
        notes = [48 + root + interval for interval in intervals]
        if condition in ("inversion", "spread_voicing"):
            notes[0] += 12
        if condition == "spread_voicing":
            notes[-1] += 12
        if condition == "low_register":
            notes = [note - 12 for note in notes]
        if condition == "high_register":
            notes = [note + 12 for note in notes]
        start = round(event["start_seconds"] * SAMPLE_RATE)
        count = round((event["end_seconds"] - event["start_seconds"]) * SAMPLE_RATE)
        t = np.arange(count) / SAMPLE_RATE
        timbre = "sine" if condition == "sine" else "bright" if condition == "bright" else "harmonic"
        segment = np.zeros(count)
        guitar_like = recipe["level"] >= 3
        period = 0.5 if condition != "tempo_ramp" else (event["end_seconds"] - event["start_seconds"]) / 4
        for index, note in enumerate(notes):
            if guitar_like:
                # Procedural amplitude envelopes/attack staggering, not a physical guitar model.
                lag = index * (0.018 if condition in ("strum", "accented", "spread_voicing") else 0.003)
                voice = np.zeros(count)
                for stroke in np.arange(0, count / SAMPLE_RATE, period):
                    local = t - stroke - lag
                    envelope = np.where(local >= 0, np.exp(-np.maximum(local, 0) / 0.45), 0)
                    envelope *= np.clip(local / 0.008, 0, 1)
                    accent = 0.6 if condition == "accented" and int(round(stroke / period)) % 2 else 1.0
                    voice += accent * oscillator(note, local, timbre) * envelope
                segment += voice
            else:
                segment += oscillator(note, t, timbre)
        if recipe["level"] == 4:
            if condition in ("bass", "combined"):
                segment += 0.8 * oscillator(36 + root, t, "harmonic")
            if condition in ("melody", "combined"):
                segment += 0.35 * oscillator(72 + (root + 2) % 12, t, "sine")
            if condition in ("drums", "combined"):
                for beat in np.arange(0, count / SAMPLE_RATE, 0.5):
                    local = t - beat
                    kick = np.sin(2 * np.pi * 65 * local) * np.exp(-np.maximum(local, 0) / 0.05)
                    noise = rng.normal(size=count) * np.exp(-np.maximum(local, 0) / 0.025)
                    segment += np.where(local >= 0, 1.2 * kick + 0.35 * noise, 0)
            if condition == "noise_10db":
                segment += rng.normal(size=count) * np.sqrt(np.mean(segment**2) / 10)
            if condition == "distortion":
                segment = np.tanh(3 * segment)
        fade = min(round(0.012 * SAMPLE_RATE), count // 2)
        segment[:fade] *= np.linspace(0, 1, fade)
        segment[-fade:] *= np.linspace(1, 0, fade)
        audio[start:start + count] += segment[:len(audio[start:start + count])]
    peak = np.max(np.abs(audio))
    return audio * (0.75 / peak) if peak else audio


def recipes() -> list[dict]:
    result = []
    for root in range(12):
        for quality in ("", "m"):
            result.append({"level": 1, "condition": "harmonic", "root": root, "quality": quality,
                           "seed": 100 + root, "split": "screen"})
    conditions = {2: ["sine", "bright", "inversion", "spread_voicing", "low_register", "high_register"],
                  3: ["pluck", "strum", "accented"],
                  4: ["bass", "drums", "melody", "noise_10db", "distortion", "combined"],
                  5: ["fast_changes", "offbeat_changes", "tempo_ramp", "power_chords", "sevenths"]}
    for level, variants in conditions.items():
        for index, condition in enumerate(variants):
            for split, seed, root in (("screen", 101, index % 12), ("holdout", 907, (index + 6) % 12)):
                result.append({"level": level, "condition": condition, "root": root, "quality": "",
                               "seed": seed + index, "split": split})
    return result


def generate(directory: Path) -> dict:
    cases = []
    for index, recipe in enumerate(recipes()):
        case_id = f"l{recipe['level']}-{recipe['condition']}-{index:03d}"
        folder = directory / "cases" / case_id
        folder.mkdir(parents=True, exist_ok=True)
        events = events_for(recipe)
        signal = render(recipe, events)
        pcm = (signal * 32767).astype("<i2").tobytes()
        with wave.open(str(folder / "audio.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(SAMPLE_RATE)
            output.writeframes(pcm)
        reference = {"schema_version": "1.0",
                     "recording": {"id": case_id, "title": f"{LEVELS[recipe['level']]} / {recipe['condition']} / {recipe['split']}",
                                   "duration_seconds": len(signal) / SAMPLE_RATE, "sample_rate_hz": SAMPLE_RATE,
                                   "provenance": "Original procedural synthetic audio; intended harmony is known; not a real guitar"},
                     "analysis": {"id": "synthetic-suite-reference-v1", "algorithm": "fixture-reference",
                                  "version": "1.0", "runtime_seconds": 0, "parameters": recipe},
                     "chords": events}
        lab.validate_chart(reference)
        lab.write_json(folder / "reference.json", reference)
        cases.append({"id": case_id, "name": reference["recording"]["title"], "level": recipe["level"],
                      "condition": recipe["condition"], "split": recipe["split"], "recipe": recipe,
                      "audio": f"cases/{case_id}/audio.wav", "reference": f"cases/{case_id}/reference.json",
                      "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
                      "audio_sha256": hashlib.sha256((folder / "audio.wav").read_bytes()).hexdigest()})
    manifest = {"suite_version": "1.0", "sample_rate_hz": SAMPLE_RATE, "cases": cases,
                "limitations": "Screen/holdout recipes are synthetic diagnostics, not real-recording generalization evidence"}
    lab.write_json(directory / "manifest.json", manifest)
    return manifest


def root_of(label: str) -> int | None:
    if label in ("N", "X", "no_chord"):
        return None
    match = re.match(r"^([A-G])([#b]?)", label)
    if not match:
        return None
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[match[1]]
    return (base + (1 if match[2] == "#" else -1 if match[2] == "b" else 0)) % 12


def canonical(label: str) -> str:
    root = root_of(label)
    if root is None:
        return "N" if label in ("N", "no_chord") else label
    suffix = re.sub(r"^[A-G][#b]?", "", label).lstrip(":")
    suffix = {"maj": "", "major": "", "min": "m", "minor": "m", "min7": "m7"}.get(suffix, suffix)
    return lab.NOTES[root] + suffix


def triad_family(label: str) -> str | None:
    """Major/minor core for a custom teaching comparison; not mir_eval."""
    label = canonical(label).split("/")[0]
    if label == "N":
        return "N"
    match = re.match(r"^([A-G][#]?)(.*)$", label)
    if not match:
        return None
    root, suffix = match.groups()
    if suffix in ("", "maj7", "7", "6", "9", "maj9", "11", "13"):
        return root
    if suffix in ("m", "m7", "m6", "m9", "m11", "m13", "mmaj7"):
        return root + "m"
    return None


def score(reference: dict, prediction: dict) -> dict:
    lab.validate_chart(reference)
    lab.validate_chart(prediction)
    if reference["recording"]["id"] != prediction["recording"]["id"]:
        raise ValueError("Prediction/reference recording IDs differ")
    duration = reference["recording"]["duration_seconds"]
    if abs(duration - prediction["recording"]["duration_seconds"]) > 0.05:
        raise ValueError("Prediction/reference audio durations differ")
    exact = root = acceptable = covered = quality = major_minor = major_minor_covered = 0.0
    for expected in reference["chords"]:
        covered += expected["end_seconds"] - expected["start_seconds"]
        expected_family = triad_family(expected["label"])
        if expected_family is not None:
            major_minor_covered += expected["end_seconds"] - expected["start_seconds"]
        accepted = {canonical(label) for label in expected.get("acceptable_labels", [expected["label"]])}
        for actual in prediction["chords"]:
            overlap = max(0.0, min(expected["end_seconds"], actual["end_seconds"])
                          - max(expected["start_seconds"], actual["start_seconds"]))
            exact += overlap * (canonical(expected["label"]) == canonical(actual["label"]))
            quality += overlap * (canonical(expected["label"]).split("/")[0] == canonical(actual["label"]).split("/")[0])
            if expected_family is not None:
                major_minor += overlap * (expected_family == triad_family(actual["label"]))
            acceptable += overlap * (canonical(actual["label"]) in accepted)
            # Unknown X is not a correct no-chord prediction; ambiguity is explicit.
            root += overlap * ((root_of(expected["label"]) == root_of(actual["label"]))
                               and (root_of(actual["label"]) is not None or actual["label"] in ("N", "no_chord")))
    reference_boundaries = [c["start_seconds"] for c in reference["chords"][1:]]
    detected = [c["start_seconds"] for c in prediction["chords"][1:]]
    unused, matched, errors = set(range(len(detected))), 0, []
    for expected in reference_boundaries:
        nearest = min(unused, key=lambda i: abs(detected[i] - expected), default=None)
        if nearest is not None and abs(detected[nearest] - expected) <= 0.15:
            matched += 1
            errors.append(abs(detected[nearest] - expected))
            unused.remove(nearest)
    precision = matched / len(detected) if detected else 0.0
    recall = matched / len(reference_boundaries) if reference_boundaries else 0.0
    return {"exact_agreement": exact / covered, "root_agreement": root / covered,
            "quality_without_bass_agreement": quality / covered,
            "major_minor_core_agreement": major_minor / major_minor_covered if major_minor_covered else None,
            "major_minor_reference_coverage": major_minor_covered / covered,
            "acceptable_agreement": acceptable / covered,
            "boundary_f1_150ms": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "matched_boundary_mean_error_seconds": sum(errors) / len(errors) if errors else None,
            "reference_events": len(reference["chords"]), "predicted_events": len(prediction["chords"]),
            "extra_events": len(prediction["chords"]) - len(reference["chords"]),
            "analysis_runtime_seconds": prediction["analysis"]["runtime_seconds"]}


def run(directory: Path, candidates: list[str], timeout: float = 600, reuse_existing: bool = False) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text()) if (directory / "manifest.json").exists() else generate(directory)
    rows = []
    commands = {
        "btc": [lab.ROOT / ".venv-btc/bin/python", Path(__file__).parent / "candidates/btc_adapter.py"],
        "crema": [lab.ROOT / ".venv-crema/bin/python", Path(__file__).parent / "candidates/crema_adapter.py"],
        "chordmini": [lab.ROOT / ".venv-chordmini/bin/python", Path(__file__).parent / "candidates/chordmini_adapter.py"],
    }
    unavailable = {}
    for candidate in candidates:
        if candidate != "baseline" and (candidate not in commands or (not reuse_existing and not all(p.exists() for p in commands[candidate]))):
            unavailable[candidate] = "Adapter or isolated Python environment not available"
    batch_runs = {}
    for candidate in candidates:
        if candidate == "baseline" or candidate in unavailable or reuse_existing:
            continue
        for case in manifest["cases"]:
            output = directory / "cases" / case["id"] / f"{candidate}.json"
            if output.exists():
                output.unlink()
        command = [str(p) for p in commands[candidate]] + ["--batch-manifest", str(directory / "manifest.json"),
                                                         "--output-root", str(directory)]
        print(f"Running {candidate} batch ({len(manifest['cases'])} cases)…", flush=True)
        started = time.perf_counter()
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            (directory / f"{candidate}-batch.log").write_text(process.stdout + process.stderr)
            batch_runs[candidate] = {"returncode": process.returncode, "wall_seconds": time.perf_counter() - started}
        except subprocess.TimeoutExpired:
            batch_runs[candidate] = {"error": "batch timeout", "wall_seconds": time.perf_counter() - started}
    for case in manifest["cases"]:
        reference = lab.load_chart(directory / case["reference"])
        for candidate in candidates:
            if candidate in unavailable:
                continue
            output = directory / "cases" / case["id"] / f"{candidate}.json"
            row = {"case_id": case["id"], "level": case["level"], "condition": case["condition"],
                   "split": case["split"], "candidate": candidate, "status": "ok"}
            started = time.perf_counter()
            try:
                if candidate == "baseline":
                    prediction = lab.detect(directory / case["audio"], case["id"])
                    prediction["recording"] = reference["recording"].copy()
                    prediction["recording"]["audio_sha256"] = hashlib.sha256((directory / case["audio"]).read_bytes()).hexdigest()
                    lab.write_json(output, prediction)
                else:
                    if not output.exists():
                        raise ValueError(f"No {candidate} prediction; see batch log or setup documentation")
                    prediction = lab.load_chart(output)
                    expected_hash = hashlib.sha256((directory / case["audio"]).read_bytes()).hexdigest()
                    if prediction["recording"].get("audio_sha256") != expected_hash:
                        raise ValueError("Prediction audio hash missing or differs; rerun this candidate")
                scoring_started = time.perf_counter()
                row.update(score(reference, prediction))
                row["scoring_runtime_seconds"] = time.perf_counter() - scoring_started
                row["screening_flag"] = "investigate" if case["level"] == 1 and row["acceptable_agreement"] < 0.8 else "diagnostic"
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                row.update({"status": "error", "error": str(error), "screening_flag": "integration-failure"})
                # Never expose stale successful output after an unsuccessful rerun.
                if output.exists():
                    output.unlink()
            rows.append(row)
        print(f"Completed {case['id']}", flush=True)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["candidate"], row["level"], row["split"])].append(row)
    summary = []
    for (candidate, level, split), group in groups.items():
        good = [r for r in group if r["status"] == "ok"]
        entry = {"candidate": candidate, "level": level, "level_name": LEVELS[level], "split": split,
                 "successful_cases": len(good), "failed_cases": len(group) - len(good)}
        for metric in ("exact_agreement", "root_agreement", "acceptable_agreement", "quality_without_bass_agreement", "major_minor_core_agreement", "major_minor_reference_coverage", "boundary_f1_150ms", "extra_events", "analysis_runtime_seconds", "scoring_runtime_seconds"):
            measured = [r[metric] for r in good if r[metric] is not None]
            entry[metric] = sum(measured) / len(measured) if measured else None
        summary.append(entry)
    report = {"suite_version": manifest["suite_version"], "candidate_requests": candidates,
              "unavailable_candidates": unavailable, "batch_runs": batch_runs, "reused_predictions": reuse_existing,
              "environment": {"platform": platform.platform(),
              "python": platform.python_version(), "numpy": np.__version__}, "summary": summary, "cases": rows,
              "limitations": "Custom duration/boundary screening metrics on procedural audio. No real-recording validation or production selection."}
    report["candidate_batch_summaries"] = {}
    for candidate in candidates:
        path = directory / f"{candidate}-batch-summary.json"
        if path.exists():
            raw = json.loads(path.read_text())
            report["candidate_batch_summaries"][candidate] = {key: value for key, value in raw.items()
                                                             if key not in ("manifest", "cases") or not isinstance(value, (list, str))}
    lab.write_json(directory / "report.json", report)
    columns = sorted({key for row in rows for key in row})
    with (directory / "report.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "run"])
    parser.add_argument("--output-dir", type=Path, default=SUITE)
    parser.add_argument("--candidates", default="baseline")
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--reuse-existing", action="store_true", help="Score existing valid outputs; do not rerun pretrained models")
    args = parser.parse_args()
    if args.command == "generate":
        manifest = generate(args.output_dir)
        print(f"Generated {len(manifest['cases'])} deterministic cases in {args.output_dir}")
    else:
        report = run(args.output_dir, args.candidates.split(","), args.timeout_seconds, args.reuse_existing)
        print(json.dumps({"summary": report["summary"], "unavailable_candidates": report["unavailable_candidates"]}, indent=2))
        if report["unavailable_candidates"] or any(row["status"] != "ok" for row in report["cases"]):
            raise SystemExit(2)


if __name__ == "__main__":
    main()
