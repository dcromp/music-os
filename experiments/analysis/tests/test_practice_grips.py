"""Symbolic grip correctness and setup uncertainty remain separate from audio."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import practice_grips as grips


class PracticeGripTests(unittest.TestCase):
    def test_each_project_grip_contains_declared_quality_and_lowest_bass(self):
        for name, frets in grips.GRIPS.items():
            with self.subTest(name=name): self.assertTrue(grips.verify_grip(name, frets)["symbolic_notes_checked"])

    def test_wrong_third_and_wrong_slash_bass_reject(self):
        with self.assertRaises(ValueError): grips.verify_grip("Am", grips.GRIPS["A"])
        with self.assertRaises(ValueError): grips.verify_grip("G/F#", grips.GRIPS["G"])
        with self.assertRaises(ValueError): grips.verify_grip("A7sus4", grips.GRIPS["A"])

    def test_wonderwall_caps_preserve_richer_quality_without_claiming_audio_verification(self):
        context = {"entry_shapes": ["Em7", "Dsus4", "A7sus4", "Cadd9"], "setup": {"tuning": "EADGBE", "capo": 2}}
        result = grips.source_palette(context)
        self.assertFalse(result["exact_audio_pitch_verified"])
        self.assertEqual(result["grips"][0]["sounding_pitch_classes_if_setup_applies"], [1, 4, 6, 9])
        self.assertEqual(result["grips"][2]["sounding_pitch_classes_if_setup_applies"], [4, 6, 9, 11])

    def test_unconfirmed_capo_does_not_become_verified_zero(self):
        result = grips.source_palette({"entry_shapes": ["G"], "setup": {"tuning": "EADGBE", "capo": None}})
        self.assertIsNone(result["grips"][0]["sounding_pitch_classes_if_setup_applies"])

    def test_uniform_retuning_and_nonuniform_unknown_are_distinguished(self):
        result = grips.source_palette({"entry_shapes": ["G"], "setup": {"tuning": "DGCFAD", "capo": 0}})
        self.assertEqual(result["grips"][0]["sounding_pitch_classes_if_setup_applies"], [0, 5, 9])
        result = grips.source_palette({"entry_shapes": ["G"], "setup": {"tuning": "Open A", "capo": 0}})
        self.assertIsNone(result["grips"][0]["sounding_pitch_classes_if_setup_applies"])

    def test_riff_tracks_receive_no_invented_complete_shape_palette(self):
        self.assertEqual(grips.source_palette({"entry_shapes": None})["grips"], [])


if __name__ == "__main__": unittest.main()
