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
import acceptance_fixtures as fixtures
import chart_aligner
import lab
import rich_quality_screen
import rich_quality_suite as original


class AcceptanceFixturesTests(unittest.TestCase):
    def test_frozen_bounded_design_is_fresh_relative_to_original_suite(self):
        recipes = fixtures.recipes()
        self.assertEqual(len(recipes), 16)
        self.assertEqual({(r["family"], r["condition"]) for r in recipes},
                         {(f, c) for f in fixtures.FAMILIES for c in fixtures.CONDITIONS})
        self.assertEqual({r["transposition"] for r in recipes}, {0, 3, 7, 10})
        self.assertFalse({r["transposition"] for r in recipes} & {2, 5})
        self.assertFalse(set(fixtures.CONDITIONS) & set(original.CONDITIONS))
        self.assertEqual({r["split"] for r in recipes}, {"fresh_validation"})
        self.assertEqual(len({r["seed"] for r in recipes}), 16)
        recipes[0]["seed"] = -1
        self.assertGreater(fixtures.recipes()[0]["seed"], 0)

    def test_explicit_voicings_contain_exact_defining_pitch_sets(self):
        expected = {"Dm": {2, 5, 9}, "Dm7": {2, 5, 9, 0}, "F": {5, 9, 0},
                    "G": {7, 11, 2}, "Gsus4": {7, 0, 2}, "A": {9, 1, 4},
                    "A7": {9, 1, 4, 7}, "A7sus4": {9, 2, 4, 7},
                    "Bb": {10, 2, 5}, "Bbadd9": {10, 0, 2, 5}}
        old = {tuple(value["midi"]) for value in original.VOICINGS.values()}
        for bank in fixtures.VOICINGS.values():
            for label, notes in bank.items():
                self.assertEqual({note % 12 for note in notes}, expected[label], label)
                self.assertEqual(notes[0] % 12, original.chord_semantics(label)["root"])
                self.assertNotIn(notes, old)

    def test_plain_control_renderer_adds_only_declared_chord_tones(self):
        for recipe in fixtures.recipes():
            if recipe["family"] != "plain_control":
                continue
            for event in fixtures.events_for(recipe, 8000):
                if event["label"] == "N":
                    continue
                isolated = copy.deepcopy(event)
                isolated["end_seconds"] -= isolated["start_seconds"]
                isolated["start_seconds"] = 0.0
                emitted = []
                def voice(note, count, *args, **kwargs):
                    emitted.append(note)
                    return np.zeros(count)
                with patch.object(fixtures, "_voice", side_effect=voice):
                    fixtures.render(recipe, [isolated], 8000)
                self.assertTrue(emitted)
                self.assertEqual({note % 12 for note in emitted}, set(event["pitch_classes"]))
                self.assertIn(original.chord_semantics(event["label"])["quality"], ("", "m"))

    def test_untimed_chart_branch_does_not_receive_times_or_silence_markers(self):
        for recipe in fixtures.recipes():
            chart = fixtures.untimed_for(recipe, "test", "test", "a" * 64)
            chart_aligner.validate_untimed_chart(chart)
            self.assertEqual(chart["sequence"], [e["label"] for e in fixtures.events_for(recipe)
                                                if e["label"] != "N"])
            self.assertNotIn("N", chart["sequence"])
            text = json.dumps(chart)
            for key in ("start_seconds", "end_seconds", "duration_seconds", "sample_rate_hz",
                        "middle_seconds", "intro_seconds", "silence_role", "midi_notes"):
                self.assertNotIn(key, text)

    def test_silences_are_long_and_section_case_repeats_with_wrong_count_hypotheses(self):
        for recipe in fixtures.recipes():
            events = fixtures.events_for(recipe)
            silences = [e for e in events if e["label"] == "N"]
            self.assertEqual(silences[0]["silence_role"], "intro")
            self.assertEqual(silences[-1]["silence_role"], "outro")
            self.assertTrue(all(e["end_seconds"] - e["start_seconds"] > 2.2 for e in silences))
            chart = fixtures.untimed_for(recipe, "test", "test", "a" * 64)
            controls = fixtures.count_controls(chart, recipe["family"])
            if recipe["family"] == "section_repeat":
                self.assertEqual(len(silences), 4)
                self.assertEqual(chart["sequence"][:3], chart["sequence"][-3:])
                self.assertEqual({name: len(value["sequence"]) for name, value in controls.items()},
                                 {"missing_repeat": 6, "extra_repeat": 12})
                for value in controls.values():
                    chart_aligner.validate_untimed_chart(value)
                    self.assertNotIn("start_seconds", json.dumps(value))
            else:
                self.assertEqual(len(silences), 3)
                self.assertEqual(controls, {})

    def test_render_is_independent_of_aligner_pitch_templates(self):
        recipe = fixtures.recipes()[0]
        with patch.object(chart_aligner, "chord_template", side_effect=AssertionError("template used")):
            events = fixtures.events_for(recipe, 8000)
            signal = fixtures.render(recipe, events, 8000)
        self.assertTrue(np.any(signal))
        self.assertTrue(np.all(np.isfinite(signal)))
        self.assertLessEqual(np.max(np.abs(signal)), 0.73 + 1e-10)

    def test_complete_packs_are_reproducible_hashed_and_preflight_compatible(self):
        with tempfile.TemporaryDirectory() as temporary:
            first_dir, second_dir = Path(temporary) / "first", Path(temporary) / "second"
            first, second = fixtures.generate(first_dir, 8000), fixtures.generate(second_dir, 8000)
            self.assertEqual(first, second)
            self.assertEqual(len(first["cases"]), 16)
            self.assertEqual(len({case["audio_sha256"] for case in first["cases"]}), 16)
            self.assertEqual(first["generator_sha256"], fixtures.sha(Path(fixtures.__file__)))
            self.assertEqual(rich_quality_screen.preflight(first_dir, Path(temporary) / "unused"), first)
            for case in first["cases"]:
                reference = lab.load_chart(first_dir / case["reference"])
                for key in ("audio", "reference", "untimed"):
                    self.assertEqual(fixtures.sha(first_dir / case[key]), case[f"{key}_sha256"])
                    self.assertEqual((first_dir / case[key]).read_bytes(), (second_dir / case[key]).read_bytes())
                for control in case["untimed_controls"].values():
                    self.assertEqual(fixtures.sha(first_dir / control["path"]), control["sha256"])
                    self.assertEqual((first_dir / control["path"]).read_bytes(),
                                     (second_dir / control["path"]).read_bytes())
                with wave.open(str(first_dir / case["audio"]), "rb") as audio:
                    self.assertEqual(audio.getframerate(), 8000)
                    signal = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
                self.assertEqual(hashlib.sha256(signal.tobytes()).hexdigest(), case["pcm_sha256"])
                self.assertAlmostEqual(len(signal) / 8000, reference["recording"]["duration_seconds"])
                for event in reference["chords"]:
                    interval = signal[round(event["start_seconds"] * 8000):round(event["end_seconds"] * 8000)]
                    self.assertEqual(bool(np.any(interval)), event["label"] != "N")
                self.assertEqual(original.score(reference, reference)["exact_quality_without_bass_agreement"], 1)

    def test_generation_refuses_existing_output_invalid_rate_and_cleans_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            existing = Path(temporary) / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                fixtures.generate(existing)
            for invalid in (True, 0, 7999, 96001, 8000.0):
                with self.assertRaisesRegex(ValueError, "Sample rate"):
                    fixtures.generate(Path(temporary) / "invalid", invalid)
            output = Path(temporary) / "failure"
            with patch.object(fixtures, "render", side_effect=RuntimeError("deliberate failure")):
                with self.assertRaisesRegex(RuntimeError, "deliberate"):
                    fixtures.generate(output, 8000)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [existing])


if __name__ == "__main__":
    unittest.main()
