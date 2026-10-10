import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
import synthetic_suite as suite


class SyntheticSuiteTests(unittest.TestCase):
    def test_generator_has_all_roots_and_qualities_and_distinct_cases(self):
        recipes = suite.recipes()
        clean = [recipe for recipe in recipes if recipe["level"] == 1]
        self.assertEqual({(r["root"], r["quality"]) for r in clean},
                         {(root, quality) for root in range(12) for quality in ("", "m")})
        self.assertEqual({r["level"] for r in recipes}, {1, 2, 3, 4, 5})
        self.assertEqual(len(recipes), 64)

    def test_generated_audio_and_references_are_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            first = suite.generate(directory)
            second = suite.generate(directory)
            self.assertEqual(first, second)
            self.assertEqual(len({c["id"] for c in first["cases"]}), 64)
            for case in first["cases"]:
                chart = lab.load_chart(directory / case["reference"])
                self.assertEqual(chart["chords"][0]["start_seconds"], 0)
                self.assertEqual(chart["chords"][-1]["end_seconds"], chart["recording"]["duration_seconds"])

    def test_power_chords_accept_quality_ambiguity_but_wrong_root_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            audio, path = lab.create_fixture(Path(folder))
            reference = lab.load_chart(path)
            reference["chords"] = [{"start_seconds": 0, "end_seconds": 22, "label": "C5",
                                    "acceptable_labels": ["C", "Cm", "C5"]}]
            prediction = copy.deepcopy(reference)
            prediction["chords"][0]["label"] = "Cm"
            metrics = suite.score(reference, prediction)
            self.assertEqual(metrics["exact_agreement"], 0)
            self.assertEqual(metrics["acceptable_agreement"], 1)
            self.assertEqual(metrics["root_agreement"], 1)
            self.assertIsNone(metrics["major_minor_core_agreement"])
            prediction["chords"][0]["label"] = "D"
            self.assertEqual(suite.score(reference, prediction)["root_agreement"], 0)

    def test_minor_major_and_unknown_are_not_conflated(self):
        self.assertEqual(suite.triad_family("Db:maj7/3"), "C#")
        self.assertEqual(suite.triad_family("C:min7"), "Cm")
        self.assertIsNone(suite.triad_family("C:sus4"))
        self.assertIsNone(suite.triad_family("X"))
        self.assertEqual(suite.triad_family("N"), "N")

    def test_extra_boundaries_are_penalised(self):
        with tempfile.TemporaryDirectory() as folder:
            _, path = lab.create_fixture(Path(folder))
            reference = lab.load_chart(path)
            prediction = copy.deepcopy(reference)
            event = prediction["chords"].pop(0)
            prediction["chords"][:0] = [dict(event, end_seconds=1), dict(event, start_seconds=1)]
            self.assertEqual(suite.score(reference, prediction)["exact_agreement"], 1)
            self.assertLess(suite.score(reference, prediction)["boundary_f1_150ms"], 1)


if __name__ == "__main__":
    unittest.main()
