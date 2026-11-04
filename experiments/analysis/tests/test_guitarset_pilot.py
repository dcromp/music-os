"""Checks semantic mistakes that would make real-guitar scores misleading."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import guitarset_pilot as pilot

HAS_MIR_EVAL = importlib.util.find_spec('mir_eval') is not None


def chart(events, candidate='reference'):
    return {'schema_version': '1.0', 'recording': {'id': 'test', 'title': 'test', 'duration_seconds': 10,
            'sample_rate_hz': 22050}, 'analysis': {'id': candidate, 'algorithm': candidate, 'version': 'test',
            'runtime_seconds': 0}, 'chords': [{'start_seconds': a, 'end_seconds': b, 'label': label,
            'native_label': label} for a, b, label in events]}


@unittest.skipUnless(HAS_MIR_EVAL, 'Run pilot tests in an environment with pinned mir_eval 0.8.2')
class PilotTests(unittest.TestCase):
    def test_native_relative_and_display_absolute_bass(self):
        import mir_eval
        native = pilot.to_harte('C:maj/3', True)
        display = pilot.to_harte('C/E')
        self.assertEqual(native, display)
        self.assertEqual(pilot.to_harte('Db/F'), 'Db:maj/3')
        self.assertEqual(mir_eval.chord.encode(native)[2], 4)
        self.assertEqual(pilot.prediction_label({'native_label': 'E:min/5', 'label': 'Em/B'}, 'crema'), 'E:min/5')

    def test_no_guessed_quality_or_numeric_display_bass(self):
        for label in ['Csomequality', 'C/3', 'Am/B/C', 'unknown']:
            with self.assertRaises(ValueError):
                pilot.to_harte(label)
        self.assertEqual(pilot.to_harte('Cm7b5'), 'C:hdim7')
        self.assertEqual(pilot.to_harte('Bb:min7'), 'Bb:min7')

    def test_ambiguous_reference_excluded_only_from_quality(self):
        reference = chart([(0, 8, 'C:(1,5)/1'), (8, 10, 'D:maj/1')])
        predicted = chart([(0, 8, 'Cm'), (8, 10, 'D')])
        result = pilot.score(reference, predicted, 'baseline')
        self.assertEqual(result['root'], 1)
        self.assertEqual(result['majmin'], 1)
        self.assertAlmostEqual(result['majmin_reference_coverage'], .2)
        self.assertEqual(result['majmin_eligible_seconds'], 2)

    def test_silence_credit_separated_from_chord_score(self):
        reference = chart([(0, 2, 'N'), (2, 10, 'C:maj')])
        predicted = chart([(0, 10, 'N')])
        result = pilot.score(reference, predicted, 'baseline')
        self.assertAlmostEqual(result['root'], .2)
        self.assertEqual(result['root_chord_only'], 0)
        self.assertEqual(result['estimated_no_chord_seconds_on_reference_chords'], 8)
        self.assertNotIn('boundary_f1_150ms', result)

    def test_missing_prediction_and_unknown_never_become_silence(self):
        reference = chart([(0, 2, 'N'), (2, 10, 'C:maj')])
        predicted = chart([(2, 10, 'C')])
        result = pilot.score(reference, predicted, 'baseline')
        self.assertAlmostEqual(result['root'], .8)
        self.assertEqual(result['estimated_unknown_seconds'], 2)
        self.assertEqual(result['root_chord_only'], 1)

    def test_extended_native_reference_not_reduced_to_intended(self):
        reference = chart([(0, 10, 'C:sus4/4')])
        predicted = chart([(0, 10, 'C')])
        result = pilot.score(reference, predicted, 'baseline')
        self.assertEqual(result['root'], 1)
        self.assertIsNone(result['majmin'])
        self.assertEqual(result['majmin_reference_coverage'], 0)

    def test_wrong_identity_and_overlaps_fail(self):
        reference = chart([(0, 10, 'C:maj')])
        predicted = chart([(0, 10, 'C')]); predicted['recording']['id'] = 'different'
        with self.assertRaises(ValueError): pilot.score(reference, predicted, 'baseline')
        predicted = chart([(0, 6, 'C'), (5, 10, 'G')])
        with self.assertRaises(ValueError): pilot.score(reference, predicted, 'baseline')

    def test_prepare_refuses_unverified_orphan_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, output = root / 'assets', root / 'output'
            stem = pilot.SELECTED[0]
            audio = assets / 'audio' / (stem + '_mic.wav')
            jams = assets / 'annotations' / (stem + '.jams')
            audio.parent.mkdir(parents=True); jams.parent.mkdir(parents=True)
            audio.write_bytes(b'original input'); jams.write_text('{}')
            case_id = 'guitarset-' + stem.lower().replace('#', 'sharp').replace('_', '-')
            orphan = output / 'cases' / case_id / 'audio.wav'
            orphan.parent.mkdir(parents=True); orphan.write_bytes(b'unverified orphan')
            with patch.object(pilot, 'SELECTED', [stem]), \
                 patch.object(pilot, 'EXPECTED_AUDIO_HASHES', [pilot.sha(audio)]), \
                 patch.object(pilot, 'EXPECTED_JAMS_HASHES', [pilot.sha(jams)]), \
                 patch('subprocess.run') as converter:
                with self.assertRaisesRegex(ValueError, 'unverified orphan'):
                    pilot.prepare(assets, output)
                converter.assert_not_called()
            self.assertEqual(orphan.read_bytes(), b'unverified orphan')


if __name__ == '__main__': unittest.main()
