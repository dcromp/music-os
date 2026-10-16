import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chart_aligner as aligner
import alignment_screen
import lab


def render(directory, events):
    """A deterministic diagnostic generator; expected times stay in the test."""
    rate = 22050
    segments, reference, offset = [], [], 0
    for label, seconds in events:
        count = round(seconds * rate)
        time = np.arange(count) / rate
        template = aligner.chord_template(label)
        signal = np.zeros(count)
        if template is not None:
            for pitch in np.flatnonzero(template):
                frequency = 440 * 2 ** ((48 + int(pitch) - 69) / 12)
                signal += sum(np.sin(2 * np.pi * frequency * harmonic * time) / harmonic**2
                              for harmonic in (1, 2, 3))
            signal *= 0.65 / np.max(np.abs(signal))
            fade = min(round(0.012 * rate), count // 2)
            signal[:fade] *= np.linspace(0, 1, fade)
            signal[-fade:] *= np.linspace(1, 0, fade)
        segments.append(signal)
        reference.append({"label": label, "start_seconds": offset / rate,
                          "end_seconds": (offset + count) / rate})
        offset += count
    path = directory / "audio.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((np.concatenate(segments) * 32767).astype("<i2").tobytes())
    return path, reference


def write_chart(directory, sequence, **fields):
    chart = {"schema_version": aligner.SCHEMA,
             "recording": {"id": "known-sequence-test", "title": "Procedural alignment diagnostic"},
             "sequence": sequence, **fields}
    path = directory / "untimed.json"
    path.write_text(json.dumps(chart), encoding="utf-8")
    return path, chart


def boundary_report(reference, predicted, tolerance=0.15):
    """Evaluate detected transitions, not agreement with the supplied labels."""
    expected = [event["start_seconds"] for event in reference[1:]]
    actual = [event["start_seconds"] for event in predicted[1:]]
    unmatched = set(range(len(actual)))
    errors = []
    for boundary in expected:
        if unmatched:
            candidate = min(unmatched, key=lambda index: abs(actual[index] - boundary))
            error = abs(actual[candidate] - boundary)
            if error <= tolerance:
                unmatched.remove(candidate)
                errors.append(error)
    precision = len(errors) / len(actual) if actual else 0
    recall = len(errors) / len(expected) if expected else 0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
            "matched_mean_error_seconds": sum(errors) / len(errors) if errors else None}


class ChartAlignerTests(unittest.TestCase):
    def test_nonuniform_offbeat_sequence_without_reading_timing_gold(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            events = [("C", 0.73), ("Am", 1.13), ("F", 0.91), ("G", 1.49),
                      ("N", 0.46), ("Dm", 0.89), ("Em", 1.27)]
            audio, reference = render(directory, events)
            chart_path, chart = write_chart(directory, [label for label, _ in events],
                                           metadata={"key": "C", "capo": 0, "source_references": ["procedural test"]})
            # A timed reference exists only in this test process. The aligner
            # reads the untimed JSON and audio, and must not call lab.load_chart.
            with patch.object(lab, "load_chart", side_effect=AssertionError("Timing gold was read")):
                result = aligner.align(audio, chart_path)
            metrics = boundary_report(reference, result["chords"])
            self.assertGreaterEqual(metrics["f1"], 0.9, metrics)
            self.assertLess(metrics["matched_mean_error_seconds"], 0.09)
            self.assertFalse(result["analysis"]["parameters"]["forced_beat_grid"])
            self.assertEqual(result["alignment_input"]["metadata"], chart["metadata"])
            self.assertEqual(result["recording"]["audio_sha256"], hashlib.sha256(audio.read_bytes()).hexdigest())
            self.assertEqual(result["alignment_input"]["chart_sha256"], hashlib.sha256(chart_path.read_bytes()).hexdigest())
            self.assertFalse(result["alignment_evidence"]["diagnostics"]["score_is_calibrated_confidence"])
            self.assertTrue(all("confidence" not in event for event in result["chords"]))

    def test_explicit_cyclic_progression_and_silent_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            sequence = ["G", "B", "C", "Cm"]
            events = [("N", 0.31)] + list(zip(sequence * 2, [0.93, 1.37, 1.09, 1.61, 1.17, 0.87, 1.43, 1.21])) + [("N", 0.27)]
            audio, reference = render(directory, events)
            chart_path, _ = write_chart(directory, sequence, mode="cyclic")
            result = aligner.align(audio, chart_path)
            metrics = boundary_report(reference, result["chords"])
            self.assertGreaterEqual(metrics["f1"], 0.9, metrics)
            self.assertEqual(result["alignment_evidence"]["diagnostics"]["cycle_wraps_observed"], 1)
            self.assertEqual(result["chords"][0]["label"], "N")
            self.assertEqual(result["chords"][-1]["label"], "N")

    def test_wrong_chords_and_wrong_order_flag_acoustic_conflicts(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("C", 1.13), ("Am", 1.39), ("F", 1.17), ("G", 1.31)])
            for sequence in (["D", "Em", "Bb", "A"], ["C", "F", "Am", "G"]):
                with self.subTest(sequence=sequence):
                    chart_path, _ = write_chart(directory, sequence)
                    result = aligner.align(audio, chart_path)
                    self.assertEqual(result["alignment_evidence"]["diagnostics"]["acoustic_fit_status"], "needs_review")
                    self.assertTrue(result["alignment_evidence"]["diagnostics"]["conflicting_proposed_event_indices"])
                    self.assertIn("X", [event["label"] for event in result["chords"]])

    def test_silence_has_no_harmonic_success_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("N", 2)])
            chart_path, _ = write_chart(directory, ["C", "G"])
            result = aligner.align(audio, chart_path)
            self.assertEqual(set(event["label"] for event in result["chords"]), {"N"})
            diagnostics = result["alignment_evidence"]["diagnostics"]
            self.assertEqual(diagnostics["acoustic_fit_status"], "no_harmonic_evidence")
            self.assertIsNone(diagnostics["active_mismatch_fraction"])

    def test_timed_inputs_malformed_charts_and_unsupported_labels_rejected(self):
        chart = {"schema_version": aligner.SCHEMA, "recording": {"id": "x", "title": "x"}, "sequence": ["C"]}
        for changes in ({"sequence": [{"label": "C", "start_seconds": 0}]},
                        {"metadata": {"reference": {"end_seconds": 5}}},
                        {"sequence": []}, {"sequence": ["Cmystery"]},
                        {"mode": "auto"}, {"start_policy": "guess"},
                        {"metadata": {"score": float("nan")}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                aligner.validate_untimed_chart({**chart, **changes})
        self.assertTrue(np.array_equal(aligner.chord_template("Db:maj7/3"), aligner.chord_template("C#maj7")))

    def test_output_overwrite_source_pairing_and_infeasible_constraints(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("C", 0.41), ("G", 0.39)])
            chart_path, chart = write_chart(directory, ["C", "G"])
            audio_bytes, chart_bytes = audio.read_bytes(), chart_path.read_bytes()
            for output in (audio, chart_path):
                with self.assertRaises(ValueError):
                    aligner.align_to_file(audio, chart_path, output, overwrite=True)
            self.assertEqual(audio.read_bytes(), audio_bytes)
            self.assertEqual(chart_path.read_bytes(), chart_bytes)
            output = directory / "result.json"
            aligner.align_to_file(audio, chart_path, output)
            with self.assertRaises(ValueError):
                aligner.align_to_file(audio, chart_path, output)
            with self.assertRaises(ValueError):
                aligner.align(audio, chart_path, min_chord_seconds=0.6)
            wrong_hash_chart = copy.deepcopy(chart)
            wrong_hash_chart["recording"]["audio_sha256"] = "0" * 64
            chart_path.write_text(json.dumps(wrong_hash_chart))
            with self.assertRaisesRegex(ValueError, "sha256"):
                aligner.align(audio, chart_path)

    def test_endpoint_policies_and_minimum_dwell_are_explicit(self):
        emissions = np.array([[0, 1, 0], [0, 1, 0], [0, 0, 1], [0, 0, 1]], dtype=float)
        path, _ = aligner.constrained_path(emissions, 2, 0.1, "finite", "any", "last")
        self.assertEqual(list(path), [1, 1, 2, 2])
        with self.assertRaises(ValueError):
            aligner.constrained_path(emissions, 2, 0.1, "finite", "first", "last")
        path, _ = aligner.constrained_path(emissions, 1, 0.1, "finite", "first", "any")
        self.assertEqual(list(path), [0, 1, 2, 2])

    def test_suspended_sevenths_keep_the_fourth_without_inventing_a_third(self):
        self.assertEqual(list(np.flatnonzero(aligner.chord_template("B7sus4"))), [4, 6, 9, 11])
        self.assertEqual(list(np.flatnonzero(aligner.chord_template("E:sus4"))), [4, 9, 11])
        self.assertEqual(list(np.flatnonzero(aligner.chord_template("Cadd9"))), [0, 2, 4, 7])
        self.assertNotIn(3, np.flatnonzero(aligner.chord_template("B7sus4")))

    def test_viterbi_objective_matches_exhaustive_small_paths(self):
        emissions = np.random.default_rng(914).random((7, 3))
        policies = (("finite", "first", "last"), ("finite", "any", "any"),
                    ("cyclic", "first", "any"), ("cyclic", "any", "last"))
        for mode, start_policy, end_policy, terminal in [(*policy, terminal) for policy in policies for terminal in (2, 3)]:
            objectives = []
            for path in itertools.product(range(3), repeat=7):
                if start_policy == "first" and path[0] != 0 or end_policy == "last" and path[-1] != 2:
                    continue
                if any(second != first and (second != (first + 1) % 3 or mode == "finite" and first == 2)
                       for first, second in zip(path, path[1:])):
                    continue
                dwell_lengths = [len(list(group)) for _, group in itertools.groupby(path)]
                if any(dwell < 2 for dwell in dwell_lengths) or dwell_lengths[-1] < terminal:
                    continue
                transitions = sum(first != second for first, second in zip(path, path[1:]))
                objectives.append(sum(emissions[index, position] for index, position in enumerate(path)) - 0.12 * transitions)
            path, actual = aligner.constrained_path(emissions, 2, 0.12, mode, start_policy, end_policy,
                                                   terminal_minimum_frames=terminal)
            self.assertAlmostEqual(actual, max(objectives), places=10)

    def test_silence_boundary_metric_does_not_accept_a_nearby_unknown_boundary(self):
        def timed(events):
            return {"schema_version": "1.0", "recording": {"id": "x", "title": "x", "duration_seconds": 3,
                                                           "sample_rate_hz": 22050},
                    "analysis": {"id": "x", "algorithm": "x", "version": "x", "runtime_seconds": 0},
                    "chords": [{"label": label, "start_seconds": start, "end_seconds": end} for label, start, end in events]}
        reference = timed([("N", 0, 0.5), ("C", 0.5, 2.5), ("N", 2.5, 3)])
        prediction = timed([("N", 0, 0.2), ("X", 0.2, 0.5), ("C", 0.5, 2.5), ("X", 2.5, 2.8), ("N", 2.8, 3)])
        metrics = alignment_screen.boundary_metrics(reference, prediction)
        self.assertEqual(metrics["matched_boundaries"], 2)
        self.assertEqual(metrics["matched_no_chord_boundaries"], 0)
        self.assertEqual(metrics["missed_reference_no_chord_boundaries"], 2)
        self.assertAlmostEqual(metrics["unknown_duration_seconds"], 0.6)
        partial = copy.deepcopy(reference)
        partial["chords"][0]["start_seconds"] = 0.1
        with self.assertRaisesRegex(ValueError, "coverage"):
            alignment_screen.boundary_metrics(partial, prediction)

    def test_screen_passes_only_untimed_non_silence_labels_and_records_exclusions(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            suite, output = directory / "suite", directory / "screen"
            audio, reference_path = lab.create_fixture(suite)
            reference = lab.load_chart(reference_path)
            lab.write_json(suite / "manifest.json", {"suite_version": "test", "cases": [{
                "id": "fixture", "level": 5, "condition": "offbeat", "split": "holdout",
                "audio": audio.name, "reference": reference_path.name}]})
            actual_align = aligner.align_to_file
            calls = []

            def audited_call(audio_path, chart_path, result_path, **kwargs):
                input_chart = json.loads(chart_path.read_text())
                self.assertEqual(input_chart["sequence"], [event["label"] for event in reference["chords"] if event["label"] != "N"])
                self.assertNotIn("start_seconds", chart_path.read_text())
                self.assertNotIn("end_seconds", chart_path.read_text())
                self.assertEqual(input_chart["mode"], "finite")
                calls.append(chart_path)
                return actual_align(audio_path, chart_path, result_path, **kwargs)

            with patch.object(aligner, "align_to_file", side_effect=audited_call):
                report = alignment_screen.run(suite, output)
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["successful_cases"], 1)
            self.assertEqual(report["failed_cases"], 0)
            with self.assertRaises(ValueError):
                alignment_screen.run(suite, output)
            reference["chords"][0]["label"] = "Cmystery"
            lab.write_json(reference_path, reference)
            report = alignment_screen.run(suite, output, overwrite=True)
            self.assertEqual(report["excluded_cases"], 1)
            self.assertEqual(report["successful_cases"], 0)
            self.assertIn("Unsupported", report["cases"][0]["reason"])

    def test_hardlink_aliases_and_concurrent_publication_preserve_existing_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("C", 1)])
            chart_path, _ = write_chart(directory, ["C"])
            for source in (audio, chart_path):
                alias = directory / "alias.json"
                os.link(source, alias)
                before = source.read_bytes()
                with self.assertRaisesRegex(ValueError, "alias"):
                    aligner.align_to_file(audio, chart_path, alias, overwrite=True)
                self.assertEqual(source.read_bytes(), before)
                alias.unlink()
            output = directory / "concurrent.json"
            original_link = os.link

            def create_competing_output(source, target):
                Path(target).write_text("concurrent owner's data")
                original_link(source, target)

            with patch.object(aligner.os, "link", side_effect=create_competing_output):
                with self.assertRaisesRegex(ValueError, "concurrently"):
                    aligner.write_json_safely(output, {"test": True}, [audio, chart_path])
            self.assertEqual(output.read_text(), "concurrent owner's data")
            self.assertEqual(list(directory.glob(".concurrent.json.*")), [])

    def test_screen_preflights_symlink_and_hardlink_collisions_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            suite, output = directory / "suite", directory / "screen"
            audio, reference_path = lab.create_fixture(suite)
            lab.write_json(suite / "manifest.json", {"suite_version": "test", "cases": [{
                "id": "fixture", "level": 5, "condition": "offbeat", "split": "holdout",
                "audio": audio.name, "reference": reference_path.name}]})
            before = {path: path.read_bytes() for path in (audio, reference_path, suite / "manifest.json")}
            case_output = output / "cases" / "fixture"
            case_output.mkdir(parents=True)
            alias = case_output / "alignment.json"
            alias.symlink_to(reference_path)
            with self.assertRaisesRegex(ValueError, "alias"):
                alignment_screen.run(suite, output, overwrite=True)
            self.assertFalse((case_output / "untimed-input.json").exists())
            alias.unlink()
            os.link(audio, output / "report.json")
            with self.assertRaisesRegex(ValueError, "alias"):
                alignment_screen.run(suite, output, overwrite=True)
            self.assertFalse((case_output / "untimed-input.json").exists())
            for path, expected in before.items():
                self.assertEqual(path.read_bytes(), expected)

    def test_terminal_clipping_cannot_evade_requested_minimum_dwell(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            audio, _ = render(directory, [("C", 0.16)])
            chart_path, _ = write_chart(directory, ["C"])
            with self.assertRaisesRegex(ValueError, "shorter"):
                aligner.align(audio, chart_path, hop_seconds=0.05, min_chord_seconds=0.2)
            emissions = np.array([[1, 0], [1, 0], [1, 0], [1, 0], [0, 1], [0, 1]], dtype=float)
            path, _ = aligner.constrained_path(emissions, 2, 0.12, "finite", "first", "last", terminal_minimum_frames=3)
            self.assertEqual(list(path), [0, 0, 0, 1, 1, 1])
            # Actual clipped terminal intervals are checked from audio length,
            # so the final proposed chord satisfies the requested duration.
            audio, _ = render(directory, [("C", 0.32), ("G", 0.12)])
            chart_path, _ = write_chart(directory, ["C", "G"])
            result = aligner.align(audio, chart_path, hop_seconds=0.05, min_chord_seconds=0.15)
            final = result["alignment_evidence"]["proposed_path_events_before_gap_mask"][-1]
            self.assertGreaterEqual(final["end_seconds"] - final["start_seconds"], 0.15 - 1e-12)

    def test_dense_boundaries_use_maximum_cardinality_then_minimum_error(self):
        matches = alignment_screen.optimal_boundary_matches([1, 1.2], [0.86, 1.1], 0.15)
        self.assertEqual([(first, second) for first, second, _ in matches], [(0, 0), (1, 1)])
        self.assertAlmostEqual(sum(error for _, _, error in matches), 0.24)
        matches = alignment_screen.optimal_boundary_matches([1], [0.86, 1.01], 0.15)
        self.assertEqual([(first, second) for first, second, _ in matches], [(0, 1)])


if __name__ == "__main__":
    unittest.main()
