"""Known-note audio controls for the descriptive catalogue palette diagnostic."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import wave
import numpy as np
import automatic_drafts as drafts
import catalogue_pitch_check as check
import lab

# Independently declared MIDI notes; scoring templates never generate audio.
MIDI = {"C": (48, 52, 55), "G": (43, 47, 50), "Am": (45, 48, 52), "F": (41, 45, 48)}
RECIPES = (("four-chords-zero", ["C", "G", "Am", "F"] * 2, 0, ["C", "G", "Am", "F"]),
           ("four-chords-plus-two", ["C", "G", "Am", "F"] * 2, 2, ["C", "G", "Am", "F"]),
           ("silence", [None] * 2, 0, ["C", "G", "Am", "F"]),
           ("single-chord-ambiguous-palette", ["C"] * 2, 0, ["C", "F", "G"]))


def render(sequence, shift, audio):
    rate = 22050
    segments = [np.zeros(rate // 2)]
    for label in sequence:
        count = 3 * rate; t = np.arange(count) / rate; value = np.zeros(count)
        if label:
            for midi in MIDI[label]:
                frequency = 440 * 2 ** ((midi + shift - 69) / 12)
                for harmonic, gain in ((1, 1.0), (2, 0.25), (3, 0.11)):
                    value += gain * np.sin(2 * np.pi * frequency * harmonic * t)
            value *= 0.65 / np.max(np.abs(value))
            fade = round(0.02 * rate)
            value[:fade] *= np.linspace(0, 1, fade)
            value[-fade:] *= np.linspace(1, 0, fade)
        segments.append(value)
    segments.append(np.zeros(rate // 2)); value = np.concatenate(segments)
    with wave.open(str(audio), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
        stream.writeframes((value * 32767).astype("<i2").tobytes())
    return len(value) / rate


def run(output):
    output = output.absolute()
    if not output.resolve().is_relative_to(check.ROOT) or output.exists() or output.is_symlink():
        raise ValueError("Use an unused repository-local control output")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".palette-controls-", dir=output.parent))
    rows = []
    try:
        for identifier, sequence, shift, shapes in RECIPES:
            folder = staging / identifier; folder.mkdir(); audio = folder / "audio.wav"
            duration = render(sequence, shift, audio)
            evidence = check.nnls.extract(audio, identifier)
            drafts.write_json(folder / "nnls-evidence.json", evidence)
            methods = {"spectral": check.features_from_spectral(audio), "nnls": check.features_from_nnls(evidence)}
            results = {name: check.score_window(features, shapes, duration) for name, features in methods.items()}
            diagnostics = {}
            if identifier == "four-chords-zero":
                for name, features in methods.items():
                    diagnostics[name] = {"missing_minor_chord": check.score_window(features, ["C", "G", "F"], duration),
                                         "wrong_major_third": check.score_window(features, ["C", "G", "A", "F"], duration)}
            assertions = {}
            for name, value in results.items():
                if identifier == "silence":
                    assertions[name] = value["active_evidence_seconds"] == 0 and value["shift_ranking"] == [] and value["proposed_zero_shift_cosine"] is None
                elif identifier.startswith("four-chords"):
                    assertions[name] = value["best_shifts_semitones"] == [shift]
                else:
                    # An unrestricted source palette sharing C at several shifts
                    # cannot prove a unique physical setup from one C chord.
                    assertions[name] = set((0, 5, 7)).issubset(value["best_shifts_semitones"])
            rows.append({"id": identifier, "audio_sha256": drafts.digest(audio), "nnls_evidence_sha256": drafts.digest(folder / "nnls-evidence.json"),
                         "audio_seconds": duration, "known_note_shift": shift, "sequence": sequence,
                         "source_palette": shapes, "results": results, "diagnostics": diagnostics,
                         "expected_control_behavior": assertions, "is_real_guitar": False})
            print(identifier + ': ' + str(assertions), flush=True)
        report = {"schema_version": "catalogue-palette-controls-1.0", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "policy": check.POLICY, "module_sha256": drafts.digest(Path(check.__file__)),
                  "generator_sha256": drafts.digest(Path(__file__)),
                  "all_expected_controls_passed": all(all(row['expected_control_behavior'].values()) for row in rows),
                  "cases": rows, "semantics": "Procedural MIDI triad controls test direction, silence, ambiguity and diagnostic gaps; no real-recording accuracy or physical setup validation."}
        drafts.write_json(staging / "report.json", report); staging.rename(output)
        return report
    except Exception:
        shutil.rmtree(staging); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print('Controls complete; expected behaviors: ' + str(result['all_expected_controls_passed']))
