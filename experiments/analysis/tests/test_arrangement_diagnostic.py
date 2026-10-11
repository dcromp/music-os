import copy
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arrangement_diagnostic as diagnostic
import chart_aligner


def events(labels, seconds=1.0):
    return [{"start_seconds": index * seconds, "end_seconds": (index + 1) * seconds, "label": label}
            for index, label in enumerate(labels)]


def result(labels):
    return {"recording": {"id": "test", "audio_sha256": "a" * 64, "duration_seconds": float(len(labels))},
            "alignment_evidence": {"frame_columns": ["time_seconds", "best_vocabulary_label", "silent", "sequence_index", "assigned_cosine"],
                "frames": [[float(i), label, label == "N", i, 1.] for i, label in enumerate(labels)],
                "diagnostics": {"partial": False, "endpoint_reached": True, "active_frames": len(labels),
                    "unvisited_sequence_indices": [], "no_active_evidence_supplied_position_count": 0}}}


def chart(labels):
    return {"schema_version": chart_aligner.SCHEMA,
            "recording": {"id": "test", "title": "Test", "audio_sha256": "a" * 64}, "sequence": labels}


class ArrangementDiagnosticTests(unittest.TestCase):
    def test_extensions_removed_without_changing_minor_or_suspension(self):
        self.assertEqual(diagnostic.core_key("Em7"), diagnostic.core_key("Em"))
        self.assertEqual(diagnostic.core_key("Cadd9"), diagnostic.core_key("C"))
        self.assertEqual(diagnostic.core_key("A7sus4"), diagnostic.core_key("Asus4"))
        self.assertNotEqual(diagnostic.core_key("A7sus4"), diagnostic.core_key("A"))
        self.assertNotEqual(diagnostic.core_key("Em7"), diagnostic.core_key("E"))
        self.assertNotEqual(diagnostic.core_key("Cdim7"), diagnostic.core_key("Cdim"))
        self.assertNotEqual(diagnostic.core_key("C5"), diagnostic.core_key("C"))

    def test_bass_excluded_and_aliases_preserve_suspension(self):
        self.assertEqual(diagnostic.core_key("C/E"), diagnostic.core_key("C"))
        self.assertEqual(diagnostic.core_key("C:sus4(b7)"), diagnostic.core_key("Csus4"))
        self.assertIsNone(diagnostic.core_key("C:sus4(7)"))

    def test_guarded_evidence_does_not_use_chart_induced_columns(self):
        source = result(["C", "G", "Am"])
        original = diagnostic.events_from_guarded(source)
        changed = copy.deepcopy(source)
        for row in changed["alignment_evidence"]["frames"]:
            row[3:] = [999, -1000.0]
        self.assertEqual(original, diagnostic.events_from_guarded(changed))

    def test_raw_core_runs_do_not_bridge_silence_unknown_or_uncovered_gap(self):
        heard = events(["C", "C7", "N", "C", "X", "C"])
        runs, coverage = diagnostic.core_runs(heard, 6)
        self.assertEqual([run["seconds"] for run in runs], [2, 1, 1])
        self.assertEqual(coverage["no_chord_seconds"], 1)
        self.assertEqual(coverage["unknown_seconds"], 1)
        gap = [{"start_seconds": 0, "end_seconds": 1, "label": "C"},
               {"start_seconds": 2, "end_seconds": 3, "label": "C"}]
        runs, coverage = diagnostic.core_runs(gap, 3)
        self.assertEqual(len(runs), 2)
        self.assertEqual(coverage["uncovered_seconds"], 1)

    def test_short_runs_discarded_without_replacement_or_gap_fill(self):
        heard = [{"start_seconds": 0, "end_seconds": 1, "label": "C"},
                 {"start_seconds": 1, "end_seconds": 1.1, "label": "G"},
                 {"start_seconds": 1.1, "end_seconds": 2.1, "label": "C"}]
        compared = diagnostic.compare(heard, 2.1, ["C", "G", "C"])
        self.assertEqual(len(compared["raw_runs"]), 3)
        self.assertEqual(len(compared["stable_runs"]), 2)
        self.assertAlmostEqual(compared["coverage"]["discarded_short_run_seconds"], .1)
        self.assertEqual(compared["stable_runs"][0]["end_seconds"], 1)
        self.assertEqual(compared["stable_runs"][1]["start_seconds"], 1.1)

    def test_repeat_counts_and_reversed_order_leave_visible_edits(self):
        heard = ["C", "G", "Am", "F", "C", "G"]
        correct = diagnostic.compare(events(heard), 6, heard)
        missing = diagnostic.compare(events(heard), 6, heard[:-2])
        extra = diagnostic.compare(events(heard), 6, heard + ["C", "G"])
        reverse = diagnostic.compare(events(heard), 6, list(reversed(heard)))
        self.assertEqual(correct["stable"]["edit_distance"], 0)
        self.assertEqual(missing["stable"]["operations"]["observed_insertion"], 2)
        self.assertEqual(extra["stable"]["operations"]["chart_deletion"], 2)
        self.assertGreater(reverse["stable"]["edit_distance"], 0)

    def test_chart_adjacent_identical_core_positions_are_unmeasurable(self):
        runs, coverage = diagnostic.chart_runs(["C", "C7", "Cadd9", "G", "G"])
        self.assertEqual(len(runs), 2)
        self.assertEqual(coverage["indistinguishable_repeated_core_positions"], [1, 2, 4])
        self.assertEqual(runs[0]["sequence_indices"], [0, 1, 2])
        runs, _ = diagnostic.chart_runs(["C", "N", "C", "X", "C"])
        self.assertEqual(len(runs), 3)

    def test_duration_agreement_does_not_count_unknown_as_harmonic_match(self):
        compared = diagnostic.compare(events(["C", "N", "X", "G"]), 4, ["C", "G"])
        self.assertEqual(compared["stable"]["matched_observed_seconds"], 2)
        self.assertEqual(compared["stable"]["matched_fraction_of_observed_harmonic_seconds"], 1)
        self.assertEqual(compared["coverage"]["stable_fraction_of_audio"], .5)

    def test_mechanically_complete_perfect_match_is_not_accepted(self):
        reported = diagnostic.diagnose(result(["C", "G"]), chart(["C", "G"]))
        self.assertFalse(reported["mechanical_status"]["failed"])
        self.assertFalse(reported["accepted_for_playback"])
        self.assertFalse(reported["arrangement_verified"])
        self.assertFalse(reported["score_is_calibrated_confidence"])

    def test_partial_and_unvisited_are_mechanical_failures(self):
        source = result(["C", "G"])
        source["alignment_evidence"]["diagnostics"].update(partial=True, endpoint_reached=False, unvisited_sequence_indices=[2])
        reported = diagnostic.diagnose(source, chart(["C", "G", "Am"]))
        self.assertTrue(reported["mechanical_status"]["failed"])
        self.assertEqual(reported["mechanical_status"]["flags"], ["partial_constrained_path", "unvisited_chart_positions"])

    def test_all_silence_has_no_agreement_score_and_fails_mechanically(self):
        source = result(["N", "N"])
        reported = diagnostic.diagnose(source, chart(["C"]))
        self.assertIn("no_unrestricted_harmonic_evidence", reported["mechanical_status"]["flags"])
        self.assertIsNone(reported["comparison"]["stable"]["matched_fraction_of_observed_harmonic_seconds"])
        self.assertEqual(reported["comparison"]["stable"]["operations"]["chart_deletion"], 1)

    def test_raw_recognition_requires_matching_audio_identity(self):
        source = result(["C", "G"])
        source["chords"] = events(["C", "G"])
        reported = diagnostic.diagnose(source, chart(["C", "G"]), source_kind="raw-recognizer")
        self.assertFalse(reported["mechanical_status"]["constrained_path_available"])
        source["recording"]["audio_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "hashes"):
            diagnostic.diagnose(source, chart(["C", "G"]), source_kind="raw-recognizer")

    def test_timed_chart_rejected_and_bad_time_axis_rejected(self):
        proposed = chart(["C", "G"])
        proposed["timestamps"] = [0, 1]
        with self.assertRaises(ValueError):
            diagnostic.diagnose(result(["C", "G"]), proposed)
        source = result(["C", "G"])
        source["alignment_evidence"]["frames"][1][0] = -1
        with self.assertRaises(ValueError):
            diagnostic.events_from_guarded(source)
        source = result(["C", "C"])
        source["alignment_evidence"]["frames"][1][0] = -1
        with self.assertRaises(ValueError): diagnostic.events_from_guarded(source)
        source = result(["C", "C"])
        source["alignment_evidence"]["frames"][1].pop()
        with self.assertRaises(ValueError): diagnostic.events_from_guarded(source)

    def test_edit_distance_empty_and_bounded_inputs(self):
        self.assertIsNone(diagnostic.edit_alignment([], [])["normalized_edit_distance"])
        with self.assertRaises(ValueError):
            diagnostic.edit_alignment([{}], [{}], max_cells=1)
        with self.assertRaises(ValueError):
            diagnostic.compare(events(["C"]), 1, ["C"], stable_seconds=float("nan"))

    def test_edit_trace_consumes_every_run_with_independent_short_sequences(self):
        # Exhaust all binary sequences up to length three. A distinct simple
        # recurrence verifies cost, while the trace verifies consumption.
        sequences = [list(values) for length in range(4) for values in itertools.product(("C", "G"), repeat=length)]
        def independent(left, right):
            if not left or not right:
                return max(len(left), len(right))
            return min(independent(left[:-1], right) + 1,
                       independent(left, right[:-1]) + 1,
                       independent(left[:-1], right[:-1]) + (left[-1] != right[-1]))
        for left in sequences:
            for right in sequences:
                observed, _ = diagnostic.core_runs(events(left), max(len(left), 1))
                proposed = [{"core": list(diagnostic.core_key(label))} for label in right]
                reported = diagnostic.edit_alignment(observed, proposed)
                collapsed_left = [run["source_labels"][0] for run in observed]
                self.assertEqual(reported["edit_distance"], independent(collapsed_left, right))
                observed_indices = [step["observed_run_index"] for step in reported["trace"] if step["observed_run_index"] is not None]
                chart_indices = [step["chart_run_index"] for step in reported["trace"] if step["chart_run_index"] is not None]
                self.assertEqual(observed_indices, list(range(len(observed))))
                self.assertEqual(chart_indices, list(range(len(proposed))))


if __name__ == "__main__":
    unittest.main()
