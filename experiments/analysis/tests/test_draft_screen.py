"""Duration denominators, warning unions and shared-error limitations."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import draft_screen as screen


def chart(events, candidate='reference'):
    return {'schema_version': '1.0', 'recording': {'id': 'test', 'title': 'test', 'duration_seconds': 10,
            'sample_rate_hz': 22050, 'audio_sha256': 'a' * 64},
            'analysis': {'id': candidate, 'algorithm': candidate, 'version': 'test', 'runtime_seconds': 0},
            'chords': [{'start_seconds': a, 'end_seconds': b, 'label': label, 'native_label': label}
                       for a, b, label in events]}


@unittest.skipUnless(importlib.util.find_spec('mir_eval'), 'Requires pinned mir_eval evaluation environment')
class DraftScreenTests(unittest.TestCase):
    def test_same_root_wrong_quality_detected_as_quality_disagreement(self):
        ref = chart([(0, 10, 'C:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'Cm')], 'chordino')
        result = screen.score_pair(ref, primary, secondary)
        self.assertEqual(result['root']['raw_disagreement_seconds_on_reference_eligible'], 0)
        self.assertEqual(result['majmin']['raw_disagreement_seconds_on_reference_eligible'], 10)
        self.assertEqual(result['majmin']['raw_disagreement_error_precision'], 0)
        self.assertEqual(result['majmin']['raw_disagreement_correct_primary_seconds'], 10)

    def test_shared_wrong_consensus_survives_warning_signal(self):
        ref = chart([(0, 10, 'F:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        result = screen.score_pair(ref, primary, secondary)
        self.assertEqual(result['majmin']['primary_accuracy'], 0)
        self.assertEqual(result['majmin']['shared_agreement_wrong_fraction_of_primary_errors'], 1)
        self.assertEqual(result['majmin']['raw_disagreement_error_capture_fraction'], 0)

    def test_unsupported_reference_quality_excluded_without_hiding_root(self):
        ref = chart([(0, 8, 'C:sus4'), (8, 10, 'D:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        result = screen.score_pair(ref, primary, secondary)
        self.assertEqual(result['root']['eligible_seconds'], 10)
        self.assertEqual(result['majmin']['eligible_seconds'], 2)
        self.assertEqual(result['majmin']['reference_coverage_fraction'], .2)

    def test_overlapping_flags_count_once_and_fractional_edges_exact(self):
        ref = chart([(0, 4, 'F:maj'), (4, 10, 'C:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        flags = [{'start_seconds': 1.2, 'end_seconds': 3}, {'start_seconds': 2, 'end_seconds': 5.5}]
        result = screen.score_pair(ref, primary, secondary, flags)
        self.assertAlmostEqual(result['flagged_seconds'], 4.3)
        self.assertAlmostEqual(result['majmin']['flagged_primary_error_seconds'], 2.8)
        self.assertAlmostEqual(result['majmin']['flagged_primary_correct_seconds'], 1.5)

    def test_unknown_prediction_never_earns_no_chord_credit(self):
        ref = chart([(0, 2, 'N'), (2, 10, 'C:maj')])
        primary, secondary = chart([(2, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        result = screen.score_pair(ref, primary, secondary)
        self.assertEqual(result['majmin']['primary_accuracy'], .8)
        self.assertEqual(result['majmin']['primary_error_seconds'], 2)
        self.assertEqual(result['majmin']['raw_pair_compared_seconds_on_reference_eligible'], 8)

    def test_mismatched_audio_or_interval_rejected(self):
        ref = chart([(0, 10, 'C:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        secondary['recording']['audio_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            screen.score_pair(ref, primary, secondary)
        with self.assertRaises(ValueError):
            screen.flag_union([{'start_seconds': -1, 'end_seconds': 3}], 10)

    def test_aggregate_duration_weighted_not_case_average(self):
        ref = chart([(0, 10, 'C:maj')])
        primary, secondary = chart([(0, 10, 'C:maj')], 'crema'), chart([(0, 10, 'C')], 'chordino')
        first = screen.score_pair(ref, primary, secondary)
        ref2 = chart([(0, 5, 'F:maj')]); ref2['recording']['duration_seconds'] = 5
        p2, s2 = chart([(0, 5, 'C:maj')], 'crema'), chart([(0, 5, 'C')], 'chordino')
        p2['recording']['duration_seconds'] = s2['recording']['duration_seconds'] = 5
        second = screen.score_pair(ref2, p2, s2)
        result = screen.aggregate([{'reference_kind': 'intended', 'metrics': m} for m in [first, second]], 'intended')
        self.assertAlmostEqual(result['majmin']['primary_accuracy'], 2 / 3)

    def test_known_extension_and_consensus_checks_remain_visible(self):
        import automatic_drafts
        checks = screen.synthetic_checks(automatic_drafts.compare_charts)
        self.assertEqual(len(checks), 3)
        self.assertTrue(checks[1]['pair_triads_agree'])
        self.assertFalse(checks[1]['primary_sevenths_correct'])
        self.assertTrue(checks[2]['pair_triads_agree'])
        self.assertEqual(checks[2]['metrics']['majmin']['primary_accuracy'], 0)


if __name__ == '__main__':
    unittest.main()
