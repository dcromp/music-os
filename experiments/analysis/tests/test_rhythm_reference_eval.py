import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rhythm_reference_eval as evaluation


def documents():
    recording = {"id": "fresh-guitar", "title": "Reference fixture", "sample_rate_hz": 22050,
                 "duration_seconds": 11., "audio_sha256": "a" * 64}
    beats = [index / 2 for index in range(21)]
    windows = [{"start_seconds": 0., "end_seconds": 1., "expected_beats": 2.,
                "expected_bars": .5, "type": "half_bar"},
               {"start_seconds": 0., "end_seconds": 2., "expected_beats": 4.,
                "expected_bars": 1., "type": "one_bar"},
               {"start_seconds": 0., "end_seconds": 4., "expected_beats": 8.,
                "expected_bars": 2., "type": "two_bars"},
               {"start_seconds": 8., "end_seconds": 10., "expected_beats": 4.,
                "expected_bars": 1., "type": "one_bar"}]
    reference = {"recording": recording, "split": "holdout", "beat_times_seconds": beats,
                 "barlines_seconds": [float(value) for value in range(0, 11, 2)],
                 "beat_reference_semantics": "Independent prescribed backing-track pulse grid",
                 "count_windows": windows}
    prediction = {"recording": copy.deepcopy(recording), "beat_times_seconds": beats.copy(),
                  "pulse_bpm": 120., "analysis": {"downbeats_inferred": False}}
    return ({"schema_version": "rhythm-references-1.0", "cases": [reference]},
            {"schema_version": "playalong-rhythm-1.0", "cases": [prediction]})


def standard_result(*args):
    return {"minimum_beat_time_seconds": 5., "status": "measured",
            "metrics": {"f_measure_70ms": 1., "cemgil_sigma_40ms": 1.,
                        "cemgil_any_metrical_level": 1., "cmlc": 1., "cmlt": 1.,
                        "amlc": 1., "amlt": 1.}}


def saved_documents(folder):
    refs, preds = documents()
    ref_path, pred_path = folder / "references.json", folder / "predictions.json"
    ref_path.write_text(json.dumps(refs))
    pred_path.write_text(json.dumps(preds))
    return refs, preds, ref_path, pred_path, folder / "result.json"


class RhythmReferenceTests(unittest.TestCase):
    def test_perfect_pulses_count_windows_and_pairing(self):
        refs, preds = documents()
        evaluation.validate(refs, preds)
        with patch.object(evaluation, "standard_metrics", side_effect=standard_result):
            row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        self.assertEqual(row["whole_recording"]["f1_70ms"]["f_measure"], 1.)
        self.assertEqual(row["count_windows"]["summary"]["supported_windows"], 4)
        self.assertEqual(row["count_windows"]["summary"]["absolute_beat_count_error_mean"], 0.)
        self.assertEqual(row["downbeat_accuracy"]["status"], "not_measured")
        self.assertEqual(row["bar_phase_accuracy"]["status"], "not_measured")

    def test_half_tempo_count_error_is_not_repaired_by_any_level_metrics(self):
        refs, preds = documents()
        preds["cases"][0]["beat_times_seconds"] = [float(index) for index in range(11)]
        alternate = standard_result()
        alternate["metrics"].update(f_measure_70ms=2/3, cmlc=0., cmlt=0., amlc=1., amlt=1.)
        with patch.object(evaluation, "standard_metrics", return_value=alternate):
            row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        self.assertEqual(row["standard_after_5s"]["metrics"]["amlt"], 1.)
        self.assertLess(row["whole_recording"]["f1_70ms"]["f_measure"], .7)
        one_bar = row["count_windows"]["windows"][1]
        self.assertEqual(one_bar["beat_count_error"], -2.)
        self.assertEqual(one_bar["equivalent_bar_length_error"], -.5)

    def test_double_tempo_keeps_extra_pulses_and_bar_count_error(self):
        refs, preds = documents()
        preds["cases"][0]["beat_times_seconds"] = [index / 4 for index in range(41)]
        with patch.object(evaluation, "standard_metrics", side_effect=standard_result):
            row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        self.assertEqual(row["whole_recording"]["f1_70ms"]["extra_estimated_pulses"], 20)
        self.assertEqual(row["count_windows"]["windows"][1]["beat_count_error"], 4.)

    def test_trimmed_final_pulses_leave_unsupported_windows_visible(self):
        refs, preds = documents()
        preds["cases"][0]["beat_times_seconds"] = preds["cases"][0]["beat_times_seconds"][:-2]
        with patch.object(evaluation, "standard_metrics", side_effect=standard_result):
            row = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        self.assertEqual(row["coverage"]["reference_pulses_outside_estimated_coverage"], 2)
        self.assertEqual(row["count_windows"]["summary"]["unsupported_windows"], 1)
        self.assertEqual(row["whole_recording"]["f1_70ms"]["missed_reference_pulses"], 2)
        self.assertEqual(row["nearest_reference_error_seconds"]["max"], 1.)

    def test_latency_distinguishes_70ms_and_150ms(self):
        reference = [1., 2., 3., 4.]
        estimated = [value + .1 for value in reference]
        strict = evaluation.match_pulses(reference, estimated, .07)
        broad = evaluation.match_pulses(reference, estimated, .15)
        self.assertEqual(strict["matched_pulses"], 0)
        self.assertEqual(broad["matched_pulses"], 4)
        self.assertAlmostEqual(broad["matched_error_p90_seconds"], .1)

    def test_matching_is_one_to_one_and_does_not_reuse_close_estimate(self):
        result = evaluation.match_pulses([1., 1.1], [1.05], .07)
        self.assertEqual(result["matched_pulses"], 1)
        self.assertEqual(result["missed_reference_pulses"], 1)

    def test_chronological_matching_avoids_nearest_greedy_cardinality_loss(self):
        result = evaluation.match_pulses([1., 1.1], [.96, 1.04], .07)
        self.assertEqual(result["matched_pulses"], 2)
        self.assertAlmostEqual(result["matched_error_max_seconds"], .06)

    def test_matching_threshold_inclusive_with_roundoff(self):
        self.assertEqual(evaluation.match_pulses([1.], [1.07], .07)["matched_pulses"], 1)
        self.assertEqual(evaluation.match_pulses([1.], [1.071], .07)["matched_pulses"], 0)

    def test_interpolation_handles_fractional_positions_and_exact_last_pulse(self):
        self.assertEqual(evaluation.pulse_position([0., 1., 3.], 2.), 1.5)
        self.assertEqual(evaluation.pulse_position([0., 1., 3.], 3.), 2.)
        self.assertIsNone(evaluation.pulse_position([0., 1., 3.], 3.01))
        self.assertIsNone(evaluation.pulse_position([0., 1., 3.], -.01))

    def test_pairing_rejects_wrong_hash_duration_id_or_sample_rate(self):
        variants = [{"audio_sha256": "b" * 64}, {"duration_seconds": 11.01},
                    {"id": "other-guitar"}, {"sample_rate_hz": 44100}]
        for variant in variants:
            with self.subTest(variant=variant):
                refs, preds = documents()
                preds["cases"][0]["recording"].update(variant)
                with self.assertRaises(ValueError):
                    evaluation.validate(refs, preds)

    def test_missing_extra_or_duplicate_cases_fail(self):
        for mode in ("missing", "extra", "duplicate"):
            with self.subTest(mode=mode):
                refs, preds = documents()
                if mode == "missing":
                    preds["cases"] = []
                else:
                    added = copy.deepcopy(preds["cases"][0])
                    if mode == "extra":
                        added["recording"]["id"] = "other-guitar"
                    preds["cases"].append(added)
                with self.assertRaises(ValueError):
                    evaluation.validate(refs, preds)

    def test_nonfinite_bool_unordered_out_of_bounds_or_short_pulses_fail(self):
        variants = [[0.], [0., 0.], [.5, 0.], [False, .5], [0., float("nan")],
                    [0., float("inf")], [-.1, .5], [0., 11.]]
        for beats in variants:
            with self.subTest(beats=beats):
                refs, preds = documents()
                preds["cases"][0]["beat_times_seconds"] = beats
                with self.assertRaises(ValueError):
                    evaluation.validate(refs, preds)

    def test_reference_semantics_split_and_window_integrity_are_required(self):
        variants = [lambda case: case.update(split="test"),
                    lambda case: case.update(beat_reference_semantics=""),
                    lambda case: case["count_windows"][0].update(expected_beats=99),
                    lambda case: case["count_windows"][0].update(expected_bars=2),
                    lambda case: case["count_windows"][0].update(start_seconds=-1),
                    lambda case: case["count_windows"][0].update(end_seconds=11),
                    lambda case: case["count_windows"][0].update(type="unknown"),
                    lambda case: case.update(barlines_seconds=[1., 0.])]
        for mutate in variants:
            refs, preds = documents()
            mutate(refs["cases"][0])
            with self.assertRaises(ValueError):
                evaluation.validate(refs, preds)

    def test_split_aggregates_keep_micro_and_macro_distinct(self):
        refs, preds = documents()
        with patch.object(evaluation, "standard_metrics", side_effect=standard_result):
            first = evaluation.score_case(refs["cases"][0], preds["cases"][0])
            preds["cases"][0]["beat_times_seconds"] = [1., 2.]
            second = evaluation.score_case(refs["cases"][0], preds["cases"][0])
        result = evaluation.aggregate([first, second])
        score = result["whole_recording"]["f1_70ms"]
        self.assertNotEqual(score["macro_f_measure"], score["micro_f_measure"])
        self.assertEqual(result["recordings"], 2)
        self.assertIsNone(evaluation.aggregate([])["whole_recording"]["f1_70ms"]["micro_f_measure"])

    def test_report_hashes_inputs_retains_conditions_and_never_modifies_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, refs, preds, output = saved_documents(Path(directory))
            reference_raw, prediction_raw = refs.read_bytes(), preds.read_bytes()
            with patch.object(evaluation, "standard_metrics", side_effect=standard_result):
                result = evaluation.evaluate(refs, preds, output, "default-120")
            self.assertEqual(result["condition"], "default-120")
            self.assertEqual(result["reference_sha256"], hashlib.sha256(reference_raw).hexdigest())
            self.assertEqual(result["predictions_sha256"], hashlib.sha256(prediction_raw).hexdigest())
            self.assertEqual(refs.read_bytes(), reference_raw)
            self.assertEqual(preds.read_bytes(), prediction_raw)
            self.assertEqual(result, json.loads(output.read_text()))
            self.assertEqual(result["by_split"]["holdout"]["recordings"], 1)
            self.assertEqual(result["by_split"]["development"]["recordings"], 0)

    def test_existing_output_input_alias_symlink_and_bad_condition_fail_before_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, refs, preds, output = saved_documents(Path(directory))
            output.write_text("Keep prior report")
            with patch.object(evaluation, "score_case") as scorer:
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, preds, output, "default-120")
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, preds, refs, "default-120")
                output.unlink()
                output.symlink_to(refs)
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, preds, output, "default-120")
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, preds, Path(directory) / "new.json", "../unsafe")
                scorer.assert_not_called()

    def test_duplicate_and_nonfinite_json_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, refs, preds, output = saved_documents(Path(directory))
            for text in ('{"cases":[],"cases":[]}', '{"cases":NaN}'):
                refs.write_text(text)
                with self.assertRaises(ValueError):
                    evaluation.evaluate(refs, preds, output, "default-120")

    def test_input_mutation_during_scoring_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, refs, preds, output = saved_documents(Path(directory))
            def mutate(*args):
                preds.write_text(preds.read_text() + " ")
                return standard_result()
            with patch.object(evaluation, "standard_metrics", side_effect=mutate), self.assertRaisesRegex(ValueError, "changed"):
                evaluation.evaluate(refs, preds, output, "default-120")
            self.assertFalse(output.exists())

    def test_standard_metrics_forward_frozen_tolerances_and_trim(self):
        beat = types.SimpleNamespace(trim_beats=lambda values, min_beat_time: values[values >= min_beat_time],
            cemgil=Mock(return_value=(.8, .95)), continuity=Mock(return_value=(.6, .7, .9, .95)),
            f_measure=Mock(return_value=.85))
        fake = types.SimpleNamespace(beat=beat)
        with patch.dict(sys.modules, {"mir_eval": fake}), patch.object(evaluation.importlib.metadata, "version", return_value="0.8.2"):
            result = evaluation.standard_metrics([0., 5., 6., 7.], [0., 5.01, 6.01, 7.01])
        np.testing.assert_equal(beat.cemgil.call_args.args[0], [5., 6., 7.])
        self.assertEqual(beat.cemgil.call_args.kwargs, {"cemgil_sigma": .04})
        self.assertEqual(beat.f_measure.call_args.kwargs, {"f_measure_threshold": .07})
        self.assertEqual(result["metrics"]["cmlt"], .7)
        self.assertEqual(result["metrics"]["amlt"], .95)

    def test_insufficient_trimmed_pulses_has_no_fabricated_metric(self):
        beat = types.SimpleNamespace(trim_beats=lambda values, min_beat_time: values[values >= min_beat_time])
        with patch.dict(sys.modules, {"mir_eval": types.SimpleNamespace(beat=beat)}), patch.object(evaluation.importlib.metadata, "version", return_value="0.8.2"):
            result = evaluation.standard_metrics([0., 1., 2.], [0., 1., 2.])
        self.assertEqual(result["status"], "insufficient_pulses_after_trim")
        self.assertIsNone(result["metrics"])


if __name__ == "__main__":
    unittest.main()
