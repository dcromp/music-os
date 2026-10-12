import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nominal_downbeat_eval as evaluation


def documents():
    recording = {"id": "nominal-guitar", "sample_rate_hz": 22050,
                 "duration_seconds": 8.1, "audio_sha256": "a" * 64}
    beats = [index / 2 for index in range(17)]
    bars = [0., 2., 4., 6., 8.]
    reference = {"recording": recording, "split": "holdout", "beat_times_seconds": beats,
                 "barlines_seconds": bars, "beat_reference_semantics": "Nominal metronome/lead-sheet grid"}
    prediction = {"recording": copy.deepcopy(recording), "beat_times_seconds": beats.copy(),
                  "downbeat_times_seconds": bars.copy(), "raw_downbeat_times_seconds": bars.copy(),
                  "outside_recording_downbeat_times_seconds": [],
                  "analysis": {"id": "beat-this-fixture", "downbeats_inferred": True}}
    return ({"schema_version": "rhythm-references-1.0", "cases": [reference]},
            {"schema_version": "playalong-rhythm-1.0", "cases": [prediction]})


def set_raw(prediction, raw):
    duration = prediction["recording"]["duration_seconds"]
    prediction["raw_downbeat_times_seconds"] = raw
    prediction["downbeat_times_seconds"] = [value for value in raw if 0 <= value < duration]
    prediction["outside_recording_downbeat_times_seconds"] = [value for value in raw if not 0 <= value < duration]


def saved(folder):
    refs, preds = documents()
    ref_path, pred_path = folder / "references.json", folder / "predictions.json"
    ref_path.write_text(json.dumps(refs))
    pred_path.write_text(json.dumps(preds))
    return ref_path, pred_path, folder / "report.json"


class NominalDownbeatTests(unittest.TestCase):
    def test_perfect_nominal_agreement_keeps_physical_accuracy_unmeasured(self):
        refs, preds = documents()
        condition, pairs = evaluation.validate(refs, preds)
        row = evaluation.score_case(*pairs[0])
        self.assertEqual(condition, "beat-this-fixture")
        self.assertEqual(row["whole_recording"]["f1_70ms"]["f_measure"], 1.)
        self.assertEqual(row["physical_downbeat_accuracy"]["status"], "not_measured")

    def test_one_beat_phase_error_is_never_shifted_into_correct_barlines(self):
        refs, preds = documents()
        set_raw(preds["cases"][0], [.5, 2.5, 4.5, 6.5, 8.5])
        row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        score = row["whole_recording"]["f1_150ms"]
        self.assertEqual(score["matched_barlines"], 0)
        self.assertEqual(score["missed_reference_barlines"], 5)
        self.assertEqual(score["extra_estimated_downbeats"], 5)
        self.assertEqual(score["invalid_outside_recording_downbeats"], 1)

    def test_half_and_double_bar_rates_keep_misses_and_extras(self):
        refs, preds = documents()
        for raw, misses, extras in [([0., 4., 8.], 2, 0),
                                  ([float(index) for index in range(9)], 0, 4)]:
            with self.subTest(raw=raw):
                set_raw(preds["cases"][0], raw)
                row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
                score = row["whole_recording"]["f1_70ms"]
                self.assertEqual(score["missed_reference_barlines"], misses)
                self.assertEqual(score["extra_estimated_downbeats"], extras)
                self.assertLess(score["f_measure"], 1.)

    def test_negative_endpoint_and_beyond_endpoint_never_match_even_near_reference(self):
        refs, preds = documents()
        raw = [-.02, 2., 4., 6., 8.1, 8.12]
        set_raw(preds["cases"][0], raw)
        evaluation.validate(refs, preds)
        row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        score = row["whole_recording"]["f1_150ms"]
        self.assertEqual(score["matched_barlines"], 3)
        self.assertEqual(score["missed_reference_barlines"], 2)
        self.assertEqual(score["extra_estimated_downbeats"], 3)
        self.assertEqual(score["invalid_outside_recording_downbeats"], 3)
        self.assertEqual(row["saved_native_downbeat_times_seconds"], raw)
        self.assertAlmostEqual(score["f_measure"], 6/11)

    def test_empty_predictions_keep_all_reference_misses(self):
        refs, preds = documents()
        set_raw(preds["cases"][0], [])
        evaluation.validate(refs, preds)
        row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        self.assertEqual(row["whole_recording"]["f1_70ms"]["missed_reference_barlines"], 5)
        self.assertEqual(row["whole_recording"]["f1_70ms"]["f_measure"], 0.)
        self.assertIsNone(row["nearest_reference_error_seconds"]["max"])

    def test_artbeat_style_missing_bar_positions_is_refused_not_invented(self):
        for bars in (None, []):
            refs, preds = documents()
            if bars is None:
                del refs["cases"][0]["barlines_seconds"]
            else:
                refs["cases"][0]["barlines_seconds"] = bars
            with self.assertRaisesRegex(ValueError, "explicit nonempty reference bar positions"):
                evaluation.validate(refs, preds)

    def test_bar_positions_must_be_ordered_in_recording_and_on_reference_grid(self):
        for bars in ([2., 0.], [-.1, 2.], [0., 8.1], [.1, 2.], [True, 2.]):
            refs, preds = documents()
            refs["cases"][0]["barlines_seconds"] = bars
            with self.assertRaises(ValueError):
                evaluation.validate(refs, preds)

    def test_exact_recording_hash_sample_duration_id_and_split_are_enforced(self):
        for change in ({"audio_sha256": "b" * 64}, {"sample_rate_hz": 44100},
                       {"duration_seconds": 8.2}, {"duration_seconds": 8.1 + 1/22050}, {"id": "different"}):
            refs, preds = documents()
            preds["cases"][0]["recording"].update(change)
            with self.assertRaises(ValueError):
                evaluation.validate(refs, preds)
        refs, preds = documents()
        refs["cases"][0]["split"] = "other"
        with self.assertRaises(ValueError):
            evaluation.validate(refs, preds)

    def test_inconsistent_raw_bounded_or_outside_audit_is_refused(self):
        for change in ({"downbeat_times_seconds": [0., 2.]},
                       {"outside_recording_downbeat_times_seconds": [8.1]},
                       {"raw_downbeat_times_seconds": [0., 2., 4., 6., 8., 8.1]}):
            refs, preds = documents()
            preds["cases"][0].update(change)
            with self.assertRaisesRegex(ValueError, "disagree"):
                evaluation.validate(refs, preds)

    def test_nonfinite_bool_duplicate_unsorted_or_absent_native_values_fail(self):
        for raw in ([0., float("nan")], [0., float("inf")], [False, 2.],
                    [0., 0.], [2., 0.], None):
            refs, preds = documents()
            preds["cases"][0]["raw_downbeat_times_seconds"] = raw
            with self.assertRaises(ValueError):
                evaluation.validate(refs, preds)

    def test_legacy_saved_output_is_scored_with_raw_completeness_caveat(self):
        refs, preds = documents()
        prediction = preds["cases"][0]
        del prediction["raw_downbeat_times_seconds"]
        del prediction["outside_recording_downbeat_times_seconds"]
        prediction["downbeat_times_seconds"].append(8.1)
        evaluation.validate(refs, preds)
        row = evaluation.score_case(refs["cases"][0], prediction)
        self.assertEqual(row["native_provenance"], "legacy_saved_list_raw_completeness_unverified")
        self.assertEqual(row["whole_recording"]["f1_70ms"]["extra_estimated_downbeats"], 1)
        prediction["outside_recording_downbeat_times_seconds"] = [8.1]
        with self.assertRaisesRegex(ValueError, "complete raw"):
            evaluation.validate(refs, preds)

    def test_condition_and_inferred_downbeat_declarations_are_required(self):
        for analysis in ({}, {"id": "../bad", "downbeats_inferred": True},
                         {"id": "beat-this-fixture", "downbeats_inferred": False}):
            refs, preds = documents()
            preds["cases"][0]["analysis"] = analysis
            with self.assertRaises(ValueError):
                evaluation.validate(refs, preds)
        refs, preds = documents()
        refs["cases"][0]["beat_reference_semantics"] = "Manually marked physical bar starts"
        with self.assertRaisesRegex(ValueError, "explicitly nominal"):
            evaluation.validate(refs, preds)

    def test_split_aggregates_keep_micro_macro_and_empty_distinct(self):
        refs, preds = documents()
        good = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        set_raw(preds["cases"][0], [])
        bad = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        measured = evaluation.aggregate([good, bad])["whole_recording"]["f1_70ms"]
        self.assertEqual(measured["macro_f_measure"], .5)
        self.assertAlmostEqual(measured["micro_f_measure"], 2/3)
        self.assertIsNone(evaluation.aggregate([])["whole_recording"]["f1_70ms"]["micro_f_measure"])

    def test_read_only_report_pins_inputs_matching_code_and_exposes_splits(self):
        with tempfile.TemporaryDirectory() as directory:
            refs, preds, output = saved(Path(directory))
            before = [path.read_bytes() for path in (refs, preds)]
            report = evaluation.evaluate(refs, [preds], output)
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertEqual(report["reference_sha256"], hashlib.sha256(before[0]).hexdigest())
            self.assertEqual(report["conditions"][0]["predictions_sha256"], hashlib.sha256(before[1]).hexdigest())
            self.assertEqual(report["matching_evaluator_sha256"], evaluation.pulse.digest(Path(evaluation.pulse.__file__)))
            self.assertEqual(report["conditions"][0]["by_split"]["holdout"]["recordings"], 1)
            self.assertEqual(report["conditions"][0]["by_split"]["development"]["recordings"], 0)
            self.assertFalse(report["method"]["model_inference_run_here"])
            self.assertFalse(report["method"]["parameters_fitted_here"])
            self.assertFalse(report["method"]["production_downbeats_promoted"])
            self.assertEqual([path.read_bytes() for path in (refs, preds)], before)

    def test_duplicate_condition_existing_alias_symlink_or_no_predictions_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            refs, preds, output = saved(Path(directory))
            with self.assertRaisesRegex(ValueError, "Duplicate prediction"):
                evaluation.evaluate(refs, [preds, preds], output)
            output.write_text("Keep prior report")
            with self.assertRaises(ValueError):
                evaluation.evaluate(refs, [preds], output)
            with self.assertRaises(ValueError):
                evaluation.evaluate(refs, [preds], refs)
            output.unlink()
            output.symlink_to(refs)
            with self.assertRaises(ValueError):
                evaluation.evaluate(refs, [preds], output)
            with self.assertRaises(ValueError):
                evaluation.evaluate(refs, [], Path(directory) / "empty.json")

    def test_duplicate_json_nonfinite_json_and_changed_input_refuse_report(self):
        with tempfile.TemporaryDirectory() as directory:
            refs, preds, output = saved(Path(directory))
            for invalid in ('{"cases": [], "cases": []}', '{"value": NaN}'):
                preds.write_text(invalid)
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, [preds], output)
                self.assertFalse(output.exists())
            refs, preds, output = saved(Path(directory))
            actual = evaluation.score_case
            def score_then_change(*args):
                row = actual(*args)
                preds.write_text(preds.read_text() + " ")
                return row
            with patch.object(evaluation, "score_case", side_effect=score_then_change):
                with self.assertRaisesRegex(ValueError, "changed during scoring"):
                    evaluation.evaluate(refs, [preds], output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
