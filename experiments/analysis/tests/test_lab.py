"""Known-input checks for experiment plumbing, not real-song benchmarks."""

import copy
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.directory = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_known_triads_and_silence_end_to_end(self):
        audio, reference_path = lab.create_fixture(self.directory)
        reference = lab.load_chart(reference_path)
        result = lab.detect(audio, reference["recording"]["id"])
        metrics = lab.agreement(reference, result)
        self.assertGreater(metrics["duration_weighted_exact_label_agreement"], 0.9)
        self.assertEqual(result["chords"][0]["start_seconds"], 0)
        self.assertEqual(result["chords"][-1]["end_seconds"], 22)
        self.assertTrue(any(c["label"] == "N" for c in result["chords"]))

    def test_silence_does_not_invent_a_chord(self):
        audio = self.directory / "silence.wav"
        with wave.open(str(audio), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes(np.zeros(22050, dtype="<i2").tobytes())
        self.assertEqual(lab.detect(audio)["chords"], [
            {"start_seconds": 0, "end_seconds": 1, "label": "N"}])

    def test_score_penalizes_shifted_boundaries(self):
        _, reference_path = lab.create_fixture(self.directory)
        reference = lab.load_chart(reference_path)
        shifted = copy.deepcopy(reference)
        shifted["chords"][0]["end_seconds"] += 0.5
        shifted["chords"][1]["start_seconds"] += 0.5
        self.assertAlmostEqual(lab.agreement(reference, shifted)[
            "duration_weighted_exact_label_agreement"], 21.5 / 22)

    def test_rejects_overlap_nonfinite_and_wrong_recording(self):
        _, reference_path = lab.create_fixture(self.directory)
        reference = lab.load_chart(reference_path)
        for mutation in ("overlap", "nonfinite", "negative"):
            broken = copy.deepcopy(reference)
            if mutation == "overlap":
                broken["chords"][1]["start_seconds"] = 0
            elif mutation == "nonfinite":
                broken["chords"][0]["end_seconds"] = float("nan")
            else:
                broken["chords"][0]["start_seconds"] = -1
            with self.assertRaises(ValueError):
                lab.validate_chart(broken)
        different = copy.deepcopy(reference)
        different["recording"]["id"] = "another-recording"
        with self.assertRaises(ValueError):
            lab.agreement(reference, different)

    def test_malformed_metadata_rejected_before_bench_import(self):
        _, reference_path = lab.create_fixture(self.directory)
        reference = lab.load_chart(reference_path)
        variants = [None, {"schema_version": "1.0", "recording": []}]
        for field in ("sample_rate_hz", "title"):
            broken = copy.deepcopy(reference)
            del broken["recording"][field]
            variants.append(broken)
        for field in ("algorithm", "version", "runtime_seconds"):
            broken = copy.deepcopy(reference)
            del broken["analysis"][field]
            variants.append(broken)
        broken = copy.deepcopy(reference)
        broken["chords"] = [None]
        variants.append(broken)
        for broken in variants:
            with self.assertRaises(ValueError):
                lab.validate_chart(broken)

    def test_analyze_refuses_to_overwrite_source_audio(self):
        audio, _ = lab.create_fixture(self.directory)
        original = audio.read_bytes()
        result = subprocess.run([sys.executable, str(Path(lab.__file__)), "analyze", str(audio),
                                 "--output", str(audio)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not overwrite", result.stderr)
        self.assertEqual(audio.read_bytes(), original)

    def test_evaluate_refuses_to_overwrite_reference(self):
        _, reference = lab.create_fixture(self.directory)
        original = reference.read_bytes()
        result = subprocess.run([sys.executable, str(Path(lab.__file__)), "evaluate", str(reference),
                                 str(reference), "--output", str(reference)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(reference.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
