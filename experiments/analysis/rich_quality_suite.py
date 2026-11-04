"""Bounded, reproducible diagnostics for rich guitar chord qualities.

This fixture emitter uses explicit guitar MIDI voicings, not the aligner's
pitch-class templates. Its audio is procedural synthesis, not a guitar model
or evidence of real-song accuracy. The old synthetic suite is untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import wave

import numpy as np

import chart_aligner
import lab

SAMPLE_RATE = 22050
SCHEMA = "rich-quality-suite-1.0"
CONDITIONS = ("clean_sustain", "strummed", "ringing_upper", "distractors")
FAMILIES = ("rich_progression", "plain_control", "same_root_contrasts")
# MIDI notes of playable standard-tuning shapes, from low to high string.
# No chord-template function is used to construct or render these fixtures.
VOICINGS = {
    "Em": {"frets": "022000", "midi": (40, 47, 52, 55, 59, 64)},
    "Em7": {"frets": "022033", "midi": (40, 47, 52, 55, 62, 67)},
    "G": {"frets": "320033", "midi": (43, 47, 50, 55, 62, 67)},
    "D": {"frets": "xx0232", "midi": (50, 57, 62, 66)},
    "Dsus4": {"frets": "xx0233", "midi": (50, 57, 62, 67)},
    "A": {"frets": "x02220", "midi": (45, 52, 57, 61, 64)},
    "A7": {"frets": "x02020", "midi": (45, 52, 55, 61, 64)},
    "A7sus4": {"frets": "x02233", "midi": (45, 52, 57, 62, 67)},
    "C": {"frets": "x32010", "midi": (48, 52, 55, 60, 64)},
    "Cadd9": {"frets": "x32033", "midi": (48, 52, 55, 62, 67)},
}
PROGRESSIONS = {
    "rich_progression": ("Em7", "G", "Dsus4", "A7sus4", "Cadd9"),
    "plain_control": ("Em", "G", "D", "A", "C"),
    "same_root_contrasts": ("Em", "Em7", "D", "Dsus4", "A7", "A7sus4", "C", "Cadd9"),
}
ALIASES = {
    "major": "", "maj": "", "minor": "m", "min": "m",
    "min7": "m7", "minor7": "m7", "major7": "maj7",
    "maj6": "6", "min6": "m6", "minmaj7": "mmaj7",
    "hdim7": "m7b5", "min9": "m9", "min11": "m11", "min13": "m13",
    "sus": "sus4", "sus4(b7)": "7sus4",
    "7sus": "7sus4", "maj(9)": "add9", "maj(add9)": "add9",
    "(1,3,5,9)": "add9", "add2": "add9", "m(9)": "madd9",
}
KNOWN_QUALITIES = frozenset(("", "m", "7", "maj7", "m7", "mmaj7", "6", "m6",
    "dim", "dim7", "m7b5", "aug", "sus2", "sus4", "7sus4", "add9", "madd9",
    "5", "9", "maj9", "m9", "11", "m11", "13", "m13"))
# Frozen audited output vocabularies. These are quality representability, not
# correctness or confidence. CREMA's display conversion table is not its vocab.
SUPPORTED_VOCABULARIES = {
    "crema": frozenset(("", "m", "dim", "aug", "6", "m6", "m7", "maj7", "7",
                        "dim7", "m7b5", "mmaj7", "sus2", "sus4")),
    "chordino": frozenset(("", "m", "m7b5", "6", "7", "maj7", "m7", "m6", "dim", "aug")),
    "baseline": frozenset(("", "m")),
}
EXTENSION_QUALITIES = KNOWN_QUALITIES - frozenset(("", "m", "dim", "aug", "5"))
ROOTS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def chord_semantics(label: str) -> dict:
    """Canonical quality/root/bass, with silence and unknown kept distinct.

    Unsupported qualities retain a parsed root but cannot earn quality credit.
    Named and Harte scale-degree slash basses are resolved to pitch classes.
    """
    if label in ("N", "no_chord"):
        return {"status": "no_chord", "root": None, "quality": None, "bass": None}
    if label == "X":
        return {"status": "unknown", "root": None, "quality": None, "bass": None}
    if not isinstance(label, str):
        return {"status": "unsupported", "root": None, "quality": None, "bass": None}
    match = re.fullmatch(r"([A-G])([#b]?)([^/]*)(?:/([A-G][#b]?|[b#]?[1-7]))?", label)
    if not match:
        return {"status": "unsupported", "root": None, "quality": None, "bass": None}
    root = (ROOTS[match[1]] + {"": 0, "#": 1, "b": -1}[match[2]]) % 12
    suffix = match[3].lstrip(":")
    quality = ALIASES.get(suffix, suffix)
    bass = root
    if match[4]:
        value = match[4]
        if value[0] in ROOTS:
            bass = (ROOTS[value[0]] + {"": 0, "#": 1, "b": -1}[value[1:]]) % 12
        else:
            degree = (0, 2, 4, 5, 7, 9, 11)[int(value[-1]) - 1]
            bass = (root + degree + {"": 0, "#": 1, "b": -1}[value[:-1]]) % 12
    return {"status": "chord" if quality in KNOWN_QUALITIES else "unsupported",
            "root": root, "quality": quality, "bass": bass}


def transpose(label: str, semitones: int) -> str:
    value = chord_semantics(label)
    if value["status"] == "no_chord":
        return "N"
    if value["status"] != "chord":
        raise ValueError(f"Unsupported chord to transpose: {label}")
    result = lab.NOTES[(value["root"] + semitones) % 12] + value["quality"]
    if "/" in label:
        result += "/" + lab.NOTES[(value["bass"] + semitones) % 12]
    return result


def chord_to_plain(label: str) -> str:
    """Diagnostic simplification, explicitly not an improvement to raw output."""
    value = chord_semantics(label)
    if value["status"] in ("no_chord", "unknown"):
        return "N" if value["status"] == "no_chord" else "X"
    if value["status"] != "chord":
        raise ValueError(f"Cannot simplify unsupported label: {label}")
    suffix = "m" if value["quality"].startswith("m") and not value["quality"].startswith("maj") else ""
    return lab.NOTES[value["root"]] + suffix


def chord_to_rich(label: str) -> str:
    """Deliberately over-rich negative control; does not infer missing notes."""
    value = chord_semantics(label)
    if value["status"] in ("no_chord", "unknown"):
        return "N" if value["status"] == "no_chord" else "X"
    if value["status"] != "chord":
        raise ValueError(f"Cannot enrich unsupported label: {label}")
    quality = {"": "add9", "m": "m7", "7": "7sus4"}.get(value["quality"], value["quality"])
    return lab.NOTES[value["root"]] + quality


def recipes() -> list[dict]:
    result = []
    for family_index, family in enumerate(FAMILIES):
        for condition_index, condition in enumerate(CONDITIONS):
            for split, transposition, seed in (("screen", 2, 1729), ("holdout", 5, 7919)):
                result.append({"family": family, "condition": condition, "level": condition_index + 1,
                    "split": split, "transposition": transposition,
                    "seed": seed + family_index * 31 + condition_index,
                    "synthesis": "Explicit MIDI guitar shapes with harmonic oscillators and amplitude envelopes",
                    "distractor_policy": "Bass and melodic distractors are chord tones only; no hidden extension tones"})
    return result


def events_for(recipe: dict, sample_rate: int = SAMPLE_RATE) -> list[dict]:
    labels = PROGRESSIONS[recipe["family"]]
    durations = (2.15, 1.65, 2.45, 1.8, 2.2) if len(labels) == 5 else (1.3, 1.95, 1.6, 2.1, 1.45, 2.25, 1.8, 2.0)
    # A held-out recipe changes timing as well as transposition and oscillator
    # phase. These are diagnostics; the deterministic holdout is not unseen data.
    if recipe["split"] == "holdout":
        durations = tuple(value + (0.17 if index % 2 else -0.13) for index, value in enumerate(durations))
    cursor = round(0.55 * sample_rate)
    events = [{"start_seconds": 0.0, "end_seconds": cursor / sample_rate, "label": "N", "midi_notes": [], "pitch_classes": []}]
    for shape, seconds in zip(labels, durations):
        notes = [note + recipe["transposition"] for note in VOICINGS[shape]["midi"]]
        count = round(seconds * sample_rate)
        events.append({"start_seconds": cursor / sample_rate, "end_seconds": (cursor + count) / sample_rate,
            "label": transpose(shape, recipe["transposition"]), "shape_label": shape,
            "shape_frets": VOICINGS[shape]["frets"], "capo_semitones": recipe["transposition"],
            "midi_notes": notes, "pitch_classes": sorted({note % 12 for note in notes})})
        cursor += count
    events.append({"start_seconds": cursor / sample_rate, "end_seconds": (cursor + round(0.65 * sample_rate)) / sample_rate,
        "label": "N", "midi_notes": [], "pitch_classes": []})
    return events


def _oscillator(note: int, time: np.ndarray, phase: float) -> np.ndarray:
    frequency = 440.0 * 2.0 ** ((note - 69) / 12.0)
    return sum(np.sin(2 * np.pi * frequency * harmonic * time + phase * harmonic) / harmonic**1.8
               for harmonic in range(1, 5))


def _voice(note: int, count: int, sample_rate: int, phase: float, *, plucked: bool, lag: float = 0.0,
           ringing: bool = False) -> np.ndarray:
    t = np.arange(count) / sample_rate
    envelope = np.zeros(count)
    if plucked:
        for stroke in np.arange(0, count / sample_rate, 0.48):
            local = t - stroke - lag
            envelope += np.clip(local / 0.008, 0, 1) * np.exp(-np.maximum(local, 0) / 0.55)
    else:
        envelope = np.clip((t - lag) / 0.015, 0, 1)
        if ringing:
            envelope *= np.exp(-t / 4.5)
    # Exactly stop every voice before a chord boundary unless its MIDI pitch is
    # shared with the following rich voicing (the caller joins that safe run).
    fade = min(round(0.012 * sample_rate), count // 2)
    if fade:
        envelope[-fade:] *= np.linspace(1, 0, fade)
    return _oscillator(note, t, phase) * envelope


def render(recipe: dict, events: list[dict], sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    rng = np.random.default_rng(recipe["seed"])
    signal = np.zeros(round(events[-1]["end_seconds"] * sample_rate), dtype=np.float64)
    condition = recipe["condition"]
    emitted = set()
    for index, event in enumerate(events):
        if event["label"] == "N":
            continue
        start, end = (round(event[key] * sample_rate) for key in ("start_seconds", "end_seconds"))
        for voice_index, note in enumerate(event["midi_notes"]):
            if (index, note) in emitted:
                continue
            rich = recipe["family"] == "rich_progression" or chord_semantics(event["label"])["quality"] in EXTENSION_QUALITIES
            ringing = condition == "ringing_upper" and rich and note >= 60 + recipe["transposition"]
            last = index
            if ringing:
                while last + 1 < len(events):
                    following = events[last + 1]
                    following_rich = recipe["family"] == "rich_progression" or chord_semantics(following["label"])["quality"] in EXTENSION_QUALITIES
                    if note not in following["midi_notes"] or not following_rich:
                        break
                    last += 1
                    emitted.add((last, note))
                end_voice = round(events[last]["end_seconds"] * sample_rate)
            else:
                end_voice = end
            signal[start:end_voice] += _voice(note, end_voice - start, sample_rate, rng.uniform(0, 2 * np.pi),
                plucked=condition != "clean_sustain" and not ringing,
                lag=voice_index * 0.016 if condition != "clean_sustain" and not ringing else 0.0, ringing=ringing)
        if condition == "distractors":
            # A prominent independent bass + changing upper chord-tone melody,
            # not nonchord tones that would invalidate exact fixture labels.
            root = chord_semantics(event["label"])["root"]
            bass = 28 + ((root - 4) % 12)
            signal[start:end] += 1.15 * _voice(bass, end - start, sample_rate, 0.3, plucked=True)
            chunk = max(1, round(0.36 * sample_rate))
            classes = event["pitch_classes"]
            for offset in range(0, end - start, chunk):
                stop = min(end, start + offset + chunk)
                note = 72 + classes[(offset // chunk) % len(classes)]
                signal[start + offset:stop] += 0.65 * _voice(note, stop - start - offset, sample_rate, 1.1, plucked=False)
    peak = np.max(np.abs(signal))
    return signal * (0.78 / peak) if peak else signal


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(directory: Path, sample_rate: int = SAMPLE_RATE) -> dict:
    """Publish a new complete pack; refuse even an existing empty directory."""
    directory = Path(directory)
    if directory.exists() or directory.is_symlink():
        raise ValueError("Rich-quality output directory already exists; choose a new directory")
    if not isinstance(sample_rate, int) or isinstance(sample_rate, bool) or sample_rate < 8000 or sample_rate > 96000:
        raise ValueError("Sample rate must be an integer from 8000 to 96000 Hz")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{directory.name}-", dir=directory.parent))
    cases = []
    try:
        for recipe in recipes():
            identifier = f"{recipe['family']}-{recipe['condition']}-{recipe['split']}"
            folder = staging / "cases" / identifier
            folder.mkdir(parents=True)
            events = events_for(recipe, sample_rate)
            signal = render(recipe, events, sample_rate)
            pcm = np.rint(signal * 32767).astype("<i2").tobytes()
            with wave.open(str(folder / "audio.wav"), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(sample_rate)
                output.writeframes(pcm)
            title = f"{recipe['family'].replace('_', ' ')} / {recipe['condition'].replace('_', ' ')} / capo {recipe['transposition']} / {recipe['split']}"
            audio_hash = sha(folder / "audio.wav")
            reference = {"schema_version": "1.0", "recording": {"id": identifier, "title": title,
                "duration_seconds": len(signal) / sample_rate, "sample_rate_hz": sample_rate,
                "audio_sha256": audio_hash, "provenance": "Original explicit MIDI guitar voicing synthesis; not real guitar audio"},
                "analysis": {"id": f"{identifier}-reference", "algorithm": "fixture-reference", "version": "1.0",
                    "runtime_seconds": 0, "parameters": recipe}, "chords": events}
            lab.validate_chart(reference)
            lab.write_json(folder / "reference.json", reference)
            # Independent recipe label branch: no timestamps, durations, or N
            # markers are passed to a supplied-chart inference path.
            untimed = {"schema_version": chart_aligner.SCHEMA,
                "recording": {"id": identifier, "title": title, "audio_sha256": audio_hash},
                "sequence": [transpose(label, recipe["transposition"]) for label in PROGRESSIONS[recipe["family"]]],
                "mode": "finite", "start_policy": "first", "end_policy": "last",
                "metadata": {"source_references": [{"source": "Original fixture recipe labels only"}],
                    "note": "Correct sequence and count are supplied; no reference times or N markers"}}
            chart_aligner.validate_untimed_chart(untimed)
            lab.write_json(folder / "untimed.json", untimed)
            cases.append({"id": identifier, "name": title, "level": recipe["level"],
                "condition": recipe["condition"], "split": recipe["split"], "recipe": recipe,
                "family": recipe["family"], "audio": f"cases/{identifier}/audio.wav",
                "reference": f"cases/{identifier}/reference.json", "untimed": f"cases/{identifier}/untimed.json",
                "pcm_sha256": hashlib.sha256(pcm).hexdigest(), "audio_sha256": audio_hash,
                "reference_sha256": sha(folder / "reference.json"), "untimed_sha256": sha(folder / "untimed.json")})
        manifest = {"suite_version": SCHEMA, "sample_rate_hz": sample_rate, "cases": cases,
            "generator_sha256": sha(Path(__file__)),
            "limitations": ["Procedural harmonic oscillators and envelopes, not a physical guitar or real song",
                "Two frozen transposed recipes, not statistical estimates of generalization",
                "Bass and melodic distractors use chord tones only; no drum/vocal/full-mix simulation",
                "Supplied-chart paths receive correct finite order/count; recognition is evaluated separately"]}
        lab.write_json(staging / "manifest.json", manifest)
        if directory.exists() or directory.is_symlink():
            raise ValueError("Rich-quality output directory appeared during generation")
        staging.rename(directory)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _family(semantic: dict) -> str | None:
    quality = semantic["quality"]
    if semantic["status"] != "chord":
        return None
    if quality in ("", "7", "maj7", "6", "add9", "9", "maj9", "11", "13"):
        return "major"
    if quality in ("m", "m7", "m6", "m9", "m11", "m13", "mmaj7", "madd9"):
        return "minor"
    return None


def score(reference: dict, prediction: dict, *, candidate: str | None = None,
          vocabulary=None, triad_control: bool = False) -> dict:
    """Duration-weighted semantics, with explicit coverage and no N/X collapse.

    Slash bass is excluded from chord quality but scored separately. A quality
    score cannot hide a vocabulary's omitted classes by reducing to maj/min.
    """
    lab.validate_chart(reference)
    lab.validate_chart(prediction)
    if reference["recording"]["id"] != prediction["recording"]["id"]:
        raise ValueError("Prediction/reference recording IDs differ")
    duration = reference["recording"]["duration_seconds"]
    if abs(duration - prediction["recording"]["duration_seconds"]) > 1e-5:
        raise ValueError("Prediction/reference audio durations differ")
    reference_hash = reference["recording"].get("audio_sha256")
    if reference_hash and prediction["recording"].get("audio_sha256") != reference_hash:
        raise ValueError("Prediction/reference audio hashes differ or prediction hash is absent")
    if vocabulary is None and candidate is not None:
        vocabulary = SUPPORTED_VOCABULARIES.get(candidate)
    values = {key: 0.0 for key in ("strict_label_correct_seconds", "semantic_with_bass_correct_seconds",
        "exact_quality_without_bass_correct_seconds", "exact_chord_quality_correct_seconds", "root_correct_seconds",
        "root_chord_correct_seconds", "chord_reference_seconds", "major_minor_chord_reference_seconds",
        "major_minor_chord_correct_seconds", "no_chord_reference_seconds", "no_chord_correct_seconds",
        "false_no_chord_on_chord_seconds", "unknown_on_chord_seconds", "unsupported_on_chord_seconds",
        "plain_triad_reference_seconds", "plain_triad_false_extension_seconds", "plain_triad_same_root_false_extension_seconds")}
    supported = 0.0
    vocabulary_values = set(vocabulary) if vocabulary is not None else None
    for expected in reference["chords"]:
        e = chord_semantics(expected["label"])
        if e["status"] not in ("chord", "no_chord"):
            raise ValueError("Reference must contain supported explicit chord qualities or N")
        seconds = expected["end_seconds"] - expected["start_seconds"]
        harmonic = e["status"] == "chord"
        family = _family(e)
        values["chord_reference_seconds"] += seconds * harmonic
        values["no_chord_reference_seconds"] += seconds * (not harmonic)
        values["major_minor_chord_reference_seconds"] += seconds * (harmonic and family is not None)
        plain = harmonic and e["quality"] in ("", "m")
        values["plain_triad_reference_seconds"] += seconds * plain
        if harmonic and vocabulary_values is not None and e["quality"] in vocabulary_values:
            supported += seconds
        for actual in prediction["chords"]:
            overlap = max(0.0, min(expected["end_seconds"], actual["end_seconds"])
                          - max(expected["start_seconds"], actual["start_seconds"]))
            if not overlap:
                continue
            a = chord_semantics(actual["label"])
            quality_ok = e["status"] == a["status"] and e["root"] == a["root"] and e["quality"] == a["quality"]
            root_ok = (harmonic and a["root"] == e["root"]) or (not harmonic and a["status"] == "no_chord")
            values["strict_label_correct_seconds"] += overlap * (expected["label"] == actual["label"])
            values["semantic_with_bass_correct_seconds"] += overlap * (quality_ok and e["bass"] == a["bass"])
            values["exact_quality_without_bass_correct_seconds"] += overlap * quality_ok
            values["root_correct_seconds"] += overlap * root_ok
            if harmonic:
                values["exact_chord_quality_correct_seconds"] += overlap * quality_ok
                values["root_chord_correct_seconds"] += overlap * root_ok
                values["major_minor_chord_correct_seconds"] += overlap * (family is not None and family == _family(a) and e["root"] == a["root"])
                values["false_no_chord_on_chord_seconds"] += overlap * (a["status"] == "no_chord")
                values["unknown_on_chord_seconds"] += overlap * (a["status"] == "unknown")
                values["unsupported_on_chord_seconds"] += overlap * (a["status"] == "unsupported")
            else:
                values["no_chord_correct_seconds"] += overlap * (a["status"] == "no_chord")
            if plain and a["status"] == "chord" and a["quality"] in EXTENSION_QUALITIES:
                values["plain_triad_false_extension_seconds"] += overlap
                values["plain_triad_same_root_false_extension_seconds"] += overlap * (a["root"] == e["root"])
    def ratio(numerator: str, denominator: str):
        return values[numerator] / values[denominator] if values[denominator] else None
    values["duration_seconds"] = duration
    values["supported_vocabulary_chord_reference_seconds"] = supported if vocabulary_values is not None else None
    values.update(strict_label_agreement=values["strict_label_correct_seconds"] / duration,
        semantic_with_bass_agreement=values["semantic_with_bass_correct_seconds"] / duration,
        exact_quality_without_bass_agreement=values["exact_quality_without_bass_correct_seconds"] / duration,
        exact_chord_quality_agreement=ratio("exact_chord_quality_correct_seconds", "chord_reference_seconds"),
        root_agreement=values["root_correct_seconds"] / duration,
        root_chord_agreement=ratio("root_chord_correct_seconds", "chord_reference_seconds"),
        major_minor_chord_agreement=ratio("major_minor_chord_correct_seconds", "major_minor_chord_reference_seconds"),
        major_minor_chord_reference_coverage=values["major_minor_chord_reference_seconds"] / duration,
        supported_vocabulary_chord_coverage=(supported / values["chord_reference_seconds"] if vocabulary_values is not None and values["chord_reference_seconds"] else None),
        no_chord_recall=ratio("no_chord_correct_seconds", "no_chord_reference_seconds"),
        plain_triad_false_extension_fraction=ratio("plain_triad_false_extension_seconds", "plain_triad_reference_seconds"),
        plain_triad_same_root_false_extension_fraction=ratio("plain_triad_same_root_false_extension_seconds", "plain_triad_reference_seconds"),
        triad_control=triad_control,
        vocabulary_qualities=sorted(vocabulary_values) if vocabulary_values is not None else None)
    # Descriptive aliases ease use in richer experiment reports.
    values["semantic_quality_agreement"] = values["exact_quality_without_bass_agreement"]
    values["semantic_chord_quality_agreement"] = values["exact_chord_quality_agreement"]
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate",))
    parser.add_argument("--output-dir", type=Path, default=lab.GENERATED / "rich-quality-suite")
    args = parser.parse_args()
    result = generate(args.output_dir)
    print(json.dumps({"cases": len(result["cases"]), "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
