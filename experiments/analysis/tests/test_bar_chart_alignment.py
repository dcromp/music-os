import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bar_chart_alignment as check
import chart_aligner


class MusicalInputTests(unittest.TestCase):
    def source(self):
        song = {'bpm': '160', 'time_signature': '3/4'}
        annotation = {'chords': [
            {'start_bar': '1', 'start_fraction': '0', 'end_bar': '2', 'end_fraction': '0',
             'start_time': '1.125', 'end_time': '2.25', 'root': 'C', 'triad': 'min', 'chord': 'C-7', 'is_no_chord': 'False'},
            {'start_bar': '2', 'start_fraction': '0', 'end_bar': '30', 'end_fraction': '.5',
             'start_time': '200', 'end_time': '230', 'root': 'D', 'triad': 'dim', 'chord': 'D-7b5', 'is_no_chord': 'False'}]}
        return annotation, song

    def test_all_musical_rows_are_used_independent_of_wallclock_values(self):
        annotation, song = self.source()
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        poisoned = copy.deepcopy(annotation)
        for row in poisoned['chords']:
            row['start_time'] = 'DO NOT READ'
            row['end_time'] = {'gold_seconds': 99999}
        self.assertEqual(chart, check.musical_chart(poisoned, song, 'fixed', 'a' * 64))
        self.assertEqual(chart['full_source_row_count'], 2)
        self.assertEqual(chart['positions'][-1]['end_quarter_note'], 91.5)
        self.assertEqual(chart['positions'][0]['label'], 'X')
        self.assertEqual(chart['positions'][-1]['label'], 'X')

    def test_three_four_is_three_quarter_notes_per_bar(self):
        annotation, song = self.source()
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        self.assertEqual(chart['quarter_notes_per_bar'], 3)
        self.assertEqual(chart['positions'][1]['start_quarter_note'], 3)
        self.assertEqual(chart['positions'][1]['end_quarter_note'], 6)

    def test_zero_extent_terminal_symbol_is_preserved_without_guessed_hold(self):
        annotation, song = self.source()
        annotation['chords'].append({'start_bar': '30', 'start_fraction': '.5', 'end_bar': '30', 'end_fraction': '.5',
                                     'start_time': 'NOT READ', 'end_time': 'NOT READ', 'root': 'C', 'triad': 'maj',
                                     'chord': 'C6', 'is_no_chord': 'False'})
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        self.assertEqual(len(chart['unresolved_zero_extent_positions']), 1)
        self.assertEqual(chart['unresolved_zero_extent_positions'][0]['source_symbol'], 'C6')
        self.assertEqual(chart['positions'][-1]['end_quarter_note'], 91.5)
        self.assertEqual(chart['full_source_row_count'], 3)

    def test_scoring_excerpt_does_not_demand_timed_terminal_hold_beyond_excerpt(self):
        annotation, _ = self.source()
        annotation['chords'].append({'start_time': '300', 'end_time': '300', 'root': 'C',
                                     'triad': 'maj', 'chord': 'C6', 'is_no_chord': 'False'})
        recording = {'id': 'fixed', 'title': 'First minute', 'audio_sha256': 'b' * 64,
                     'duration_seconds': 60., 'sample_rate_hz': 22050}
        reference = check.reference(annotation, recording)
        self.assertEqual(len(reference['chords']), 1)
        self.assertEqual(reference['chords'][0]['label'], 'C:min')

    def test_model_schema_refuses_gold_fields_even_in_nested_metadata(self):
        annotation, song = self.source()
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        chart['extra'] = {'start_time': '1.125'}
        with self.assertRaisesRegex(ValueError, 'Wallclock/reference'):
            check.validate_chart(chart)

    def test_unsupported_projection_is_unknown_without_symbol_rewriting(self):
        annotation, song = self.source()
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        self.assertEqual(chart['positions'][-1]['label'], 'X')
        self.assertEqual(chart['positions'][-1]['source_symbol'], 'D-7b5')
        chart['positions'][1]['label'] = 'C:7(#5,b9)'
        with self.assertRaisesRegex(ValueError, 'guessed conversion'):
            check.validate_chart(chart)

    def test_negative_controls_preserve_unknowns_and_remove_literal_music_bar(self):
        annotation, song = self.source()
        chart = check.musical_chart(annotation, song, 'fixed', 'a' * 64)
        shifted = check.condition_chart(chart, check.CONDITIONS[1])
        self.assertEqual(shifted['positions'][1]['label'], 'C#:min')
        self.assertEqual(shifted['positions'][-1]['label'], 'X')
        removed = check.condition_chart(chart, check.CONDITIONS[2])
        self.assertEqual(removed['positions'][-1]['end_quarter_note'], chart['positions'][-1]['end_quarter_note'] - 3)
        self.assertEqual(chart['positions'][-1]['end_quarter_note'], 91.5)


class AcousticSearchTests(unittest.TestCase):
    def chart(self):
        return {'schema_version': 'full-musical-chart-1.0', 'recording_id': 'fixed',
                'declared_bpm': 120., 'quarter_notes_per_bar': 4,
                'positions': [{'start_quarter_note': 0., 'end_quarter_note': 4., 'label': 'C:maj'},
                              {'start_quarter_note': 4., 'end_quarter_note': 8., 'label': 'G:maj'},
                              {'start_quarter_note': 8., 'end_quarter_note': 200., 'label': 'F:maj'}]}

    def evidence(self):
        times = np.arange(0, 4., .25)
        chroma = np.stack([chart_aligner.chord_template('C:maj' if time < 2 else 'G:maj') for time in times])
        return {'recording': {'id': 'fixed', 'title': 'Exact paired toy', 'audio_sha256': 'b' * 64,
                              'duration_seconds': 4., 'sample_rate_hz': 22050},
                'times_seconds': times.tolist(), 'chroma_c_first': chroma.tolist(), 'silent': [False] * len(times)}

    def test_full_chart_is_not_forced_into_audio_prefix(self):
        prediction = check.infer(self.chart(), self.evidence(), check.CANDIDATES[0])
        self.assertFalse(prediction['diagnostics']['accepted_for_playback'])
        self.assertTrue(prediction['diagnostics']['partial_full_chart_prefix'])
        self.assertEqual([row['label'] for row in prediction['chords']], ['C:maj', 'G:maj'])
        self.assertEqual(prediction['chords'][1]['start_seconds'], 2.)
        self.assertNotIn(2, prediction['diagnostics']['visited_full_chart_positions'])

    def test_wrong_audio_identity_is_rejected(self):
        evidence = self.evidence()
        evidence['recording']['id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            check.infer(self.chart(), evidence, check.CANDIDATES[0])

    def test_unknown_hypothesis_does_not_gain_acoustic_credit(self):
        chart = self.chart()
        chart['positions'][0]['label'] = 'X'
        coordinates = np.asarray(self.evidence()['times_seconds']) * 2
        self.assertAlmostEqual(check.score_hypothesis(chart, self.evidence(), coordinates), .5)

    def test_pulse_mapping_never_extrapolates_unobserved_endpoints(self):
        pulses = {'recording': self.evidence()['recording'],
                  'pulse': {'beat_times_seconds': [.5, 1., 1.5, 2., 2.5, 3., 3.5], 'pulse_bpm': 120.}}
        prediction = check.infer(self.chart(), self.evidence(), check.CANDIDATES[1], pulses)
        self.assertEqual(prediction['chords'][0], {'start_seconds': 0., 'end_seconds': .5, 'label': 'X'})
        self.assertEqual(prediction['chords'][-1], {'start_seconds': 3.5, 'end_seconds': 4., 'label': 'X'})


if __name__ == '__main__':
    unittest.main()
