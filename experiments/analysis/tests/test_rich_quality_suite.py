import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chart_aligner
import lab
import rich_quality_suite as suite


def chart(labels, durations=None):
    durations = durations or [1.0] * len(labels)
    cursor = 0.0
    chords = []
    for label, seconds in zip(labels, durations):
        chords.append({"start_seconds": cursor, "end_seconds": cursor + seconds, "label": label})
        cursor += seconds
    return {"schema_version": "1.0", "recording": {"id": "test", "title": "test",
        "sample_rate_hz": 22050, "duration_seconds": cursor},
        "analysis": {"id": "test", "algorithm": "fixture", "version": "1", "runtime_seconds": 0},
        "chords": chords}


class RichQualitySuiteTests(unittest.TestCase):
    def test_bounded_frozen_factorial_contains_24_cases(self):
        recipes = suite.recipes()
        self.assertEqual(len(recipes), 24)
        self.assertEqual({(r["family"], r["condition"], r["split"]) for r in recipes},
            {(family, condition, split) for family in suite.FAMILIES for condition in suite.CONDITIONS
             for split in ("screen", "holdout")})
        self.assertEqual({r["transposition"] for r in recipes}, {2, 5})

    def test_voicings_match_real_frets_and_expected_fundamental_pitch_classes(self):
        tuning = (40, 45, 50, 55, 59, 64)
        expected = {"Em": {4, 7, 11}, "Em7": {4, 7, 11, 2}, "G": {7, 11, 2},
            "D": {2, 6, 9}, "Dsus4": {2, 7, 9}, "A": {9, 1, 4}, "A7": {9, 1, 4, 7},
            "A7sus4": {9, 2, 4, 7}, "C": {0, 4, 7}, "Cadd9": {0, 2, 4, 7}}
        for label, voicing in suite.VOICINGS.items():
            actual = tuple(note + int(fret) for note, fret in zip(tuning, voicing["frets"]) if fret != "x")
            self.assertEqual(actual, voicing["midi"], label)
            self.assertEqual({note % 12 for note in actual}, expected[label], label)

    def test_plain_controls_emit_no_extension_notes_even_with_ringing_or_distractors(self):
        for recipe in [r for r in suite.recipes() if r["family"] == "plain_control"]:
            for event in suite.events_for(recipe):
                if event["label"] == "N":
                    continue
                emitted = []
                def voice(note, count, sample_rate, phase, **kwargs):
                    emitted.append(note)
                    return np.zeros(count)
                isolated = copy.deepcopy(event)
                isolated["end_seconds"] -= isolated["start_seconds"]
                isolated["start_seconds"] = 0.0
                with patch.object(suite, "_voice", side_effect=voice):
                    suite.render(recipe, [isolated])
                self.assertTrue(emitted)
                self.assertLessEqual({note % 12 for note in emitted}, set(event["pitch_classes"]), event["label"])
                self.assertEqual(suite.chord_semantics(event["label"])["quality"],
                                 "m" if event["shape_label"] == "Em" else "")

    def test_ringing_carries_only_shared_pitches_and_never_plain_transition_tails(self):
        recipe = next(r for r in suite.recipes() if r["family"] == "rich_progression" and r["condition"] == "ringing_upper")
        events = suite.events_for(recipe, 8000)
        emitted = []
        def voice(note, count, sample_rate, phase, **kwargs):
            emitted.append((note, count, kwargs["ringing"]))
            return np.zeros(count)
        with patch.object(suite, "_voice", side_effect=voice):
            suite.render(recipe, events, 8000)
        shared = (62 + recipe["transposition"], 67 + recipe["transposition"])
        total = round((events[-2]["end_seconds"] - events[1]["start_seconds"]) * 8000)
        for note in shared:
            self.assertEqual([count for emitted_note, count, ringing in emitted if emitted_note == note and ringing], [total])
        # All carried pitches belong to every event in the joined run.
        for event in events[1:-1]:
            self.assertLessEqual(set(shared), set(event["midi_notes"]))

    def test_generated_packs_are_identical_hashed_and_have_true_silence(self):
        with tempfile.TemporaryDirectory() as temporary:
            first_dir, second_dir = Path(temporary) / "first", Path(temporary) / "second"
            first, second = suite.generate(first_dir, 8000), suite.generate(second_dir, 8000)
            self.assertEqual(first, second)
            self.assertEqual(len({case["id"] for case in first["cases"]}), 24)
            for case in first["cases"]:
                reference = lab.load_chart(first_dir / case["reference"])
                untimed = json.loads((first_dir / case["untimed"]).read_text())
                chart_aligner.validate_untimed_chart(untimed)
                self.assertEqual(untimed["sequence"], [event["label"] for event in reference["chords"] if event["label"] != "N"])
                self.assertNotIn("start_seconds", json.dumps(untimed))
                self.assertNotIn("duration_seconds", json.dumps(untimed))
                for key in ("audio", "reference", "untimed"):
                    self.assertEqual(suite.sha(first_dir / case[key]), case[f"{key}_sha256"])
                    self.assertEqual((first_dir / case[key]).read_bytes(), (second_dir / case[key]).read_bytes())
                with wave.open(str(first_dir / case["audio"]), "rb") as source:
                    signal = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
                intro = round(reference["chords"][0]["end_seconds"] * 8000)
                outro = round(reference["chords"][-1]["start_seconds"] * 8000)
                self.assertFalse(np.any(signal[:intro]))
                self.assertFalse(np.any(signal[outro:]))
                self.assertTrue(np.any(signal[intro:outro]))
                self.assertEqual(hashlib.sha256(signal.tobytes()).hexdigest(), case["pcm_sha256"])
                self.assertAlmostEqual(len(signal) / 8000, reference["recording"]["duration_seconds"])

    def test_generation_refuses_existing_directory_and_cleans_failure_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            existing = Path(temporary) / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                suite.generate(existing)
            output = Path(temporary) / "failure"
            with patch.object(suite, "render", side_effect=RuntimeError("deliberate render failure")):
                with self.assertRaisesRegex(RuntimeError, "deliberate"):
                    suite.generate(output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [existing])

    def test_aliases_enharmonic_and_named_or_relative_slash_basses_are_semantic(self):
        for a, b in (("Db:min7/Ab", "C#m7/G#"), ("C:maj(9)/E", "Cadd9/3"),
                     ("A:sus4(b7)/G", "A7sus4/b7"), ("C:min7/Eb", "Cm7/b3")):
            self.assertEqual(suite.chord_semantics(a), suite.chord_semantics(b))
        self.assertNotEqual(suite.chord_semantics("X"), suite.chord_semantics("N"))
        self.assertEqual(suite.chord_semantics("C:not-a-quality")["status"], "unsupported")

    def test_quality_score_preserves_richness_but_ignores_inversion(self):
        reference = chart(["Em7", "Dsus4", "A7sus4", "Cadd9"])
        reduced = copy.deepcopy(reference)
        for event in reduced["chords"]:
            event["label"] = suite.chord_to_plain(event["label"])
        result = suite.score(reference, reduced)
        self.assertEqual(result["root_chord_agreement"], 1)
        self.assertEqual(result["exact_chord_quality_agreement"], 0)
        self.assertEqual(result["major_minor_chord_agreement"], 1)
        self.assertEqual(result["major_minor_chord_reference_coverage"], 0.5)
        inversion = copy.deepcopy(reference)
        inversion["chords"][0]["label"] = "E:min7/G"
        result = suite.score(reference, inversion)
        self.assertEqual(result["exact_quality_without_bass_agreement"], 1)
        self.assertEqual(result["strict_label_agreement"], 0.75)
        self.assertEqual(result["semantic_with_bass_agreement"], 0.75)

    def test_harte_major_seventh_cannot_match_a_dominant_suspended_seventh(self):
        reference = chart(["A7sus4"])
        major_seventh_modifier = chart(["A:sus4(7)"])
        result = suite.score(reference, major_seventh_modifier)
        self.assertEqual(result["root_chord_agreement"], 1)
        self.assertEqual(result["exact_chord_quality_agreement"], 0)
        self.assertEqual(result["unsupported_on_chord_seconds"], 1)
        dominant_modifier = chart(["A:sus4(b7)"])
        self.assertEqual(suite.score(reference, dominant_modifier)["exact_chord_quality_agreement"], 1)

    def test_all_rich_output_is_penalized_on_plain_controls_but_inversions_are_not(self):
        reference = chart(["Em", "G", "D", "A", "C"], [1, 2, 3, 4, 5])
        bad = copy.deepcopy(reference)
        for event in bad["chords"]:
            event["label"] = suite.chord_to_rich(event["label"])
        result = suite.score(reference, bad, triad_control=True)
        self.assertEqual(result["plain_triad_false_extension_fraction"], 1)
        self.assertEqual(result["plain_triad_same_root_false_extension_fraction"], 1)
        self.assertEqual(result["plain_triad_false_extension_seconds"], 15)
        inverse = copy.deepcopy(reference)
        inverse["chords"][-1]["label"] = "C/E"
        result = suite.score(reference, inverse, triad_control=True)
        self.assertEqual(result["plain_triad_false_extension_fraction"], 0)
        self.assertEqual(result["exact_chord_quality_agreement"], 1)

    def test_scores_are_duration_weighted_and_silence_does_not_hide_chord_failure(self):
        reference = chart(["N", "Cadd9", "N"], [1, 8, 1])
        prediction = chart(["N"], [10])
        result = suite.score(reference, prediction)
        self.assertEqual(result["exact_quality_without_bass_agreement"], 0.2)
        self.assertEqual(result["exact_chord_quality_agreement"], 0)
        self.assertEqual(result["false_no_chord_on_chord_seconds"], 8)
        self.assertEqual(result["no_chord_recall"], 1)
        unknown = chart(["X"], [10])
        result = suite.score(reference, unknown)
        self.assertEqual(result["no_chord_recall"], 0)
        self.assertEqual(result["root_agreement"], 0)
        self.assertEqual(result["unknown_on_chord_seconds"], 8)

    def test_vocabulary_coverage_is_explicit_and_cannot_be_invented_from_output(self):
        reference = chart(["Em7", "Dsus4", "A7sus4", "Cadd9"], [1, 2, 3, 4])
        self.assertAlmostEqual(suite.score(reference, reference, candidate="crema")["supported_vocabulary_chord_coverage"], 0.3)
        self.assertAlmostEqual(suite.score(reference, reference, candidate="chordino")["supported_vocabulary_chord_coverage"], 0.1)
        self.assertIsNone(suite.score(reference, reference, candidate="unverified-model")["supported_vocabulary_chord_coverage"])
        self.assertEqual(suite.score(reference, reference)["exact_chord_quality_agreement"], 1)

    def test_input_identity_and_hash_mismatch_are_rejected(self):
        reference = chart(["C"])
        prediction = copy.deepcopy(reference)
        prediction["recording"]["id"] = "other"
        with self.assertRaisesRegex(ValueError, "IDs differ"):
            suite.score(reference, prediction)
        prediction = copy.deepcopy(reference)
        reference["recording"]["audio_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "hashes"):
            suite.score(reference, prediction)


if __name__ == "__main__":
    unittest.main()
