"""Section/repeat constraints are declared inputs, never inferred timing gold."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chart_aligner as aligner
from candidates import nnls_chroma_adapter
from test_chart_aligner import render


def section_chart():
    return {"schema_version": aligner.SECTION_SCHEMA,
            "recording": {"id": "section-test", "title": "Section diagnostic"},
            "sections": [{"id": "intro", "name": "Intro", "sequence": ["G", "B", "C", "Cm"]}],
            "order": [{"section_id": "intro", "repeat": 2}]}


class SectionAlignmentTests(unittest.TestCase):
    def test_declared_repeats_align_without_unbounded_cycle(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            chart = section_chart()
            durations = [.93, 1.37, 1.09, 1.61, 1.17, .87, 1.43, 1.21]
            audio, _ = render(directory, list(zip(["G", "B", "C", "Cm"] * 2, durations)))
            path = directory / "untimed.json"
            path.write_text(json.dumps(chart))
            result = aligner.align(audio, path)
            diagnostics = result["alignment_evidence"]["diagnostics"]
            self.assertEqual(diagnostics["path_transitions"], 7)
            self.assertEqual(diagnostics["cycle_wraps_observed"], 0)
            sections = result["alignment_evidence"]["section_intervals_from_proposed_path"]
            self.assertEqual([event["repeat_index"] for event in sections], [0, 1])
            self.assertAlmostEqual(sections[1]["start_seconds"], sum(durations[:4]), delta=.10)
            self.assertEqual(result["alignment_input"]["order"], chart["order"])
            self.assertTrue(diagnostics["always_requires_human_review"])

    def test_partial_prefix_does_not_force_the_last_section(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("G", 1.2), ("B", 1.4)])
            chart = section_chart()
            chart["end_policy"] = "any"
            path = directory / "untimed.json"
            path.write_text(json.dumps(chart))
            result = aligner.align(audio, path)
            self.assertLessEqual(result["alignment_evidence"]["diagnostics"]["path_transitions"], 2)
            self.assertTrue(result["alignment_evidence"]["diagnostics"]["unvisited_sequence_indices"])

    def test_ambiguous_or_timed_section_inputs_are_rejected(self):
        original = section_chart()
        variants = [dict(mode="cyclic"), dict(sequence=["G"]), dict(order=[{"section_id": "missing"}]),
                    dict(order=[{"section_id": "intro", "repeat": True}]),
                    dict(order=[{"section_id": "intro", "repeat": 0}]),
                    dict(order=[{"section_id": "intro", "repeat": 65}]),
                    dict(order=[{"section_id": "intro", "repeat": 64}] * 3),
                    dict(sections=original["sections"] * 2),
                    dict(sections=[{**original["sections"][0], "start_seconds": 0}])]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                aligner.validate_untimed_chart({**copy.deepcopy(original), **variant})

    def test_native_interpolation_is_hash_validated_and_not_a_new_resolution_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "features.json"
            vectors = np.zeros((2, 12))
            vectors[0, 0], vectors[1, 7] = 1, 1
            packet = {"recording": {"id": "recording"}, "times_seconds": [0, .05],
                      "chroma_c_first": vectors.tolist(), "analysis": {"native_host": {"hop_size": 2048}}}
            path.write_text(json.dumps(packet))
            original = {"chroma": np.zeros((4, 12)), "hop_samples": 551}
            audio = Path(folder) / "audio.wav"
            with patch.object(nnls_chroma_adapter, "validate_evidence") as validator:
                chroma, metadata = aligner.acoustic_evidence(audio, path, "recording", original, 22050)
                validator.assert_called_once_with(packet, audio)
            self.assertTrue(np.allclose(np.linalg.norm(chroma, axis=1), 1))
            self.assertTrue(np.array_equal(chroma[-1], vectors[-1]))
            self.assertGreater(chroma[1, 0], .70)
            self.assertGreater(chroma[1, 7], .70)
            self.assertIn("does not improve", metadata["note"])
            with patch.object(nnls_chroma_adapter, "validate_evidence"), self.assertRaisesRegex(ValueError, "recording ID"):
                aligner.acoustic_evidence(audio, path, "different", original, 22050)

    def test_output_cannot_replace_acoustic_input(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("C", 1)])
            path = directory / "chart.json"
            chart = {"schema_version": aligner.SCHEMA, "recording": {"id": "x", "title": "x"}, "sequence": ["C"]}
            path.write_text(json.dumps(chart))
            evidence = directory / "features.json"
            evidence.write_text("preserve this input")
            with self.assertRaisesRegex(ValueError, "input"):
                aligner.align_to_file(audio, path, evidence, evidence_json=evidence, overwrite=True)
            self.assertEqual(evidence.read_text(), "preserve this input")


if __name__ == "__main__":
    unittest.main()
