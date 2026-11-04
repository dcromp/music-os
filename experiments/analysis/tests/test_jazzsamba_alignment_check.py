import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chart_aligner
import jazzsamba_alignment_check as check


class WithheldGridTests(unittest.TestCase):
    def reference(self):
        return {'schema_version': '1.0',
                'recording': {'id': 'paired', 'title': 'Paired excerpt',
                              'audio_sha256': 'a' * 64, 'duration_seconds': 6, 'sample_rate_hz': 22050},
                'analysis': {'id': 'ref', 'algorithm': 'reference', 'version': '1', 'runtime_seconds': 0},
                'chords': [{'start_seconds': 1, 'end_seconds': 2, 'label': 'C:maj'},
                           {'start_seconds': 2, 'end_seconds': 3, 'label': 'C:maj'},
                           {'start_seconds': 3, 'end_seconds': 4, 'label': 'G:maj'},
                           {'start_seconds': 4, 'end_seconds': 5, 'label': 'X'}]}

    def test_unknown_source_and_gap_positions_are_retained(self):
        reference = self.reference()
        before = copy.deepcopy(reference)
        runs = check.projected_runs(reference)
        self.assertEqual([(row['label'], row['start_seconds'], row['end_seconds']) for row in runs],
                         [('X', 0, 1), ('C:maj', 1, 3), ('G:maj', 3, 4), ('X', 4, 6)])
        self.assertEqual(reference, before)

    def test_timestamp_fields_never_enter_aligner_input(self):
        reference = self.reference()
        reference['chords'][0]['source_fields'] = {'start_time': '1', 'bpm': '120'}
        chart = check.untimed(reference, 'b' * 64, check.CONDITIONS[0])
        chart_aligner.validate_untimed_chart(chart)
        self.assertEqual(chart['sequence'], ['X', 'C:maj', 'G:maj', 'X'])
        chart['metadata']['timestamp'] = 1
        with self.assertRaisesRegex(ValueError, 'timing field'):
            chart_aligner.validate_untimed_chart(chart)

    def test_unsupported_rich_quality_is_not_silently_simplified(self):
        reference = self.reference()
        reference['chords'][0]['label'] = 'C:7(#5,b9)'
        with self.assertRaisesRegex(ValueError, 'declared major/minor'):
            check.projected_runs(reference)

    def test_negative_control_keeps_quality_and_unknown_positions(self):
        chart = check.untimed(self.reference(), 'b' * 64, check.CONDITIONS[1])
        self.assertEqual(chart['sequence'], ['X', 'C#:maj', 'G#:maj', 'X'])
        self.assertEqual(check.corrupt_root('Bb:min'), 'B:min')

    def test_boundary_diagnostic_excludes_identical_and_unknown_edges(self):
        prediction = self.reference()
        # Exactly one supported harmonic change, even though source has four edges.
        result = check.boundary_score(self.reference(), prediction)
        self.assertEqual(result['reference_grid_boundaries_seconds'], [3])
        self.assertEqual(result['predicted_harmonic_boundaries_seconds'], [3])
        self.assertEqual(result['grid_boundary_f1_150ms'], 1)
        self.assertEqual(result['physical_attack_accuracy'], 'not measured')

    def test_abstention_edge_cannot_earn_boundary_credit(self):
        prediction = self.reference()
        prediction['chords'][1]['label'] = 'X'
        result = check.boundary_score(self.reference(), prediction)
        self.assertEqual(result['matched_grid_boundaries_150ms'], 0)
        self.assertEqual(result['reference_supported_grid_boundaries'], 1)

    @unittest.skipUnless(importlib.util.find_spec('mir_eval'), 'Requires pinned mir_eval')
    def test_retained_wrong_labels_are_separate_from_unknown_reference(self):
        reference = self.reference()
        prediction = copy.deepcopy(reference)
        prediction['chords'] = [{'start_seconds': 0, 'end_seconds': 6, 'label': 'C:maj'}]
        result = check.agreement(reference, prediction, 'frozen-nnls')
        self.assertEqual(result['majmin_eligible_seconds'], 3)
        self.assertEqual(result['retained_correct_majmin_seconds'], 2)
        self.assertEqual(result['retained_wrong_majmin_seconds'], 1)
        self.assertEqual(result['retained_harmonic_on_unknown_reference_seconds'], 3)


if __name__ == '__main__':
    unittest.main()
