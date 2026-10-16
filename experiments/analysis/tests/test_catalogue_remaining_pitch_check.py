"""Setup mappings and riff diagnostics must not manufacture harmony or truth."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_remaining_pitch_check as followup
import test_catalogue_pitch_check as fixtures
import test_curation as curation_fixtures


class RemainingPitchCheckTests(unittest.TestCase):
    @contextmanager
    def workspace(self, riff=False):
        with curation_fixtures.CurationTests().pack() as values:
            root, source, pack, manifest, _, _ = values
            path = pack / "cases/song/review.json"
            review = followup.pitch.curation.read(path)
            if riff:
                # Update the immutable reviewer fixture consistently before pinning.
                review["source_context"]["entry_shapes"] = None
                followup.pitch.drafts.write_json(path, review)
            context = review["source_context"]
            profile = {"id": "song", "recording": manifest["cases"][0]["recording"],
                       "review_sha256": followup.pitch.drafts.digest(path), "shape_palette": context["entry_shapes"],
                       "source_setup": context["setup"], "expected_sounding_shift_semitones": None if riff else 0,
                       "analysis_kind": "riff-pitch-class-inventory" if riff else "source-palette-compatibility", "fixed_samples": 4}
            spec = root / "spec.json"
            followup.pitch.drafts.write_json(spec, {"schema_version": followup.SPEC_SCHEMA, "policy": followup.pitch.POLICY,
                "pack_manifest_sha256": followup.pitch.drafts.digest(pack / "manifest.json"), "selected_case_ids": ["song"], "cases": [profile]})
            yield root, pack, spec, manifest

    @contextmanager
    def symbolic_run(self, case, callback=None):
        features = fixtures.feature_packet([0, 4, 8], [fixtures.vector([0, 4, 7])] * 3)
        def extract(audio, identifier):
            if callback: callback()
            return {"recording": copy.deepcopy(case["recording"]), "fixture": "No acoustic extraction in this unit test"}
        with patch.object(followup, "native_dependencies", return_value=[]), \
             patch.object(followup.pitch.nnls, "extract", side_effect=extract), \
             patch.object(followup.pitch.nnls, "validate_evidence"), \
             patch.object(followup.pitch, "features_from_nnls", return_value=features), \
             patch.object(followup.pitch, "features_from_spectral", return_value=features):
            yield

    def test_capo_two_preserves_extended_and_suspended_quality(self):
        labels = followup.sounding_labels(["Em7", "G", "Dsus4", "A7sus4", "Cadd9"], 2)
        self.assertEqual(labels, ["F#m7", "A", "Esus4", "B7sus4", "Dadd9"])
        for shape, sounding in zip(["Em7", "G", "Dsus4", "A7sus4", "Cadd9"], labels):
            np.testing.assert_allclose(np.roll(followup.pitch.chart_aligner.chord_template(shape), 2), followup.pitch.chart_aligner.chord_template(sounding))
        with self.assertRaises(ValueError): followup.sounding_labels(["C/G"], 2)

    def test_expected_shift_is_reported_without_selecting_or_relabelling_it(self):
        features = fixtures.feature_packet([0], [fixtures.vector([2, 6, 9])])
        result = followup.score_palette(features, ["C"], 0, 1)
        self.assertEqual(result["best_shifts_semitones"], [2])
        self.assertEqual(result["expected_sounding_shift_semitones"], 0)
        self.assertEqual(result["expected_shift_cosine"], 0)
        self.assertAlmostEqual(result["best_minus_expected_score"], 1)
        self.assertEqual(len(result["shift_ranking"]), 12)

    def test_pitch_inventory_keeps_pitch_classes_without_key_chord_or_shift_winner(self):
        features = fixtures.feature_packet([0, 2, 6], [fixtures.vector([4]), fixtures.vector([7]), np.zeros(12)])
        result = followup.pitch_inventory(features, 10)
        self.assertEqual(result["active_evidence_seconds"], 4)
        self.assertEqual(result["non_silent_zero_evidence_seconds"], 6)
        self.assertEqual(result["descending_activity"][0]["pitch_class"], "G")
        self.assertAlmostEqual(result["mean_l2_chroma"][4], .25)
        self.assertAlmostEqual(result["mean_l2_chroma"][7], .75)
        self.assertFalse({"key", "chord", "best_shifts_semitones", "accuracy"} & result.keys())

    def test_silence_inventory_cannot_imply_a_pitch(self):
        result = followup.pitch_inventory(fixtures.feature_packet([0], [np.zeros(12)], [True]), 1)
        self.assertEqual(result["active_evidence_seconds"], 0)
        self.assertIsNone(result["mean_l2_chroma"])
        self.assertEqual(result["descending_activity"], [])

    def test_pitch_inventory_window_ledger_and_invalid_inputs(self):
        features = fixtures.feature_packet([0, 2, 6], [fixtures.vector([0]), fixtures.vector([4]), fixtures.vector([7])])
        whole = followup.pitch_inventory(features, 10)
        a, b = followup.pitch_inventory(features, 10, 0, 3), followup.pitch_inventory(features, 10, 3, 10)
        np.testing.assert_allclose(np.array(a["mean_l2_chroma"]) * 3 + np.array(b["mean_l2_chroma"]) * 7, np.array(whole["mean_l2_chroma"]) * 10)
        with self.assertRaises(ValueError): followup.pitch_inventory(features, 10, 1, 11)
        with self.assertRaises(ValueError): followup.pitch_inventory(fixtures.feature_packet([0], [[1] * 12]), 1)

    def test_native_inventory_preserves_n_x_rich_and_minor_labels(self):
        chart = fixtures.chart([(0, 1, "E"), (1, 3, "Em"), (3, 4, "E7sus4"), (4, 5, "N"), (5, 6, "X")])
        before = copy.deepcopy(chart)
        result = followup.native_inventory(chart)
        self.assertEqual({row["label"]: row["seconds"] for row in result["labels"]}, {"E": 1, "Em": 2, "E7sus4": 1, "N": 1, "X": 1})
        self.assertEqual(result["uncovered_seconds"], 4)
        self.assertEqual(chart, before)
        with self.assertRaises(ValueError): followup.native_inventory(fixtures.chart([(0, 10.0005, "C")]))

    def test_preflight_rejects_profile_source_pitch_or_riff_coercion_changes(self):
        for field, value in (("shape_palette", ["D"]), ("source_setup", {}), ("recording", {}), ("expected_sounding_shift_semitones", True), ("analysis_kind", "riff-pitch-class-inventory"), ("fixed_samples", 3)):
            with self.subTest(field=field), self.workspace() as (root, pack, spec, manifest):
                config = followup.pitch.curation.read(spec); config["cases"][0][field] = value; followup.pitch.drafts.write_json(spec, config)
                with self.assertRaises(ValueError): followup.preflight(pack, spec, root / "output", root)

    def test_preflight_rejects_existing_or_input_ancestry_output(self):
        with self.workspace() as (root, pack, spec, manifest):
            for output in (pack, root, pack / "child"):
                with self.subTest(output=output), self.assertRaises(ValueError): followup.preflight(pack, spec, output, root)

    def test_palette_run_retains_raw_and_private_bytes_and_has_no_approval(self):
        with self.workspace() as (root, pack, spec, manifest):
            private = pack / "private-drafts/song.json"; private.parent.mkdir(); private.write_text('{"saved":"keep"}\n')
            paths = [pack / "manifest.json", pack / "cases/song/audio.wav", pack / "cases/song/primary.json", private, spec]
            before = {path: path.read_bytes() for path in paths}
            with self.symbolic_run(manifest["cases"][0]): report = followup.run(pack, spec, root / "output", root)
            case = report["cases"][0]
            self.assertIn("acoustic_compatibility", case)
            self.assertIsNotNone(case["native_model_palette_membership"])
            self.assertEqual(len(case["acoustic_compatibility"]["nnls"]["fixed_coverage_samples"]), 4)
            self.assertFalse(case["exact_setup_verified"]); self.assertFalse(case["accepted_arrangement"]); self.assertFalse(report["gold"])
            self.assertIsNone(case["accuracy_score"]); self.assertIsNone(report["human_correction_seconds"])
            self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_concurrent_spec_edit_aborts_and_does_not_replace_edited_bytes(self):
        with self.workspace() as (root, pack, spec, manifest):
            def change(): spec.write_text('{"concurrent":"edit"}\n')
            with self.symbolic_run(manifest["cases"][0], change), self.assertRaisesRegex(ValueError, "Inputs or saved private drafts changed"):
                followup.run(pack, spec, root / "output", root)
            self.assertFalse((root / "output").exists()); self.assertFalse(list(root.glob(".remaining-pitch-*")))
            self.assertEqual(spec.read_text(), '{"concurrent":"edit"}\n')

    def test_riff_run_has_no_palette_shift_winner_or_major_minor_membership(self):
        with self.workspace(riff=True) as (root, pack, spec, manifest):
            with self.symbolic_run(manifest["cases"][0]): report = followup.run(pack, spec, root / "output", root)
            case = report["cases"][0]
            self.assertIsNone(case["native_model_palette_membership"])
            self.assertIsNone(case["retrospective_cue_audit"])
            self.assertIsNone(case["sounding_palette_proposal"])
            self.assertNotIn("acoustic_compatibility", case)
            self.assertNotIn("best_shifts_semitones", case["pitch_class_activity"]["nnls"]["full_recording"])
            self.assertIn("native_model_inventory", case)


if __name__ == "__main__": unittest.main()
