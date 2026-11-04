import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import separation_check as check


class ResidualSignalTests(unittest.TestCase):
    def stems(self):
        return {name: np.full((12, 2), value, dtype=np.float32)
                for name, value in [('drums', .25), ('bass', .125), ('other', .5), ('vocals', .125)]}

    def test_residual_uses_original_not_reconstructed_accompaniment(self):
        source = np.full((12, 2), 1.5, dtype=np.float32)
        original = source.copy(); stems = self.stems()
        result = check.residuals(source, stems)
        np.testing.assert_array_equal(result['minus-drums'], np.full((12, 2), 1.25))
        np.testing.assert_array_equal(result['minus-drums-vocals'], np.full((12, 2), 1.125))
        np.testing.assert_array_equal(source, original)
        self.assertFalse(np.array_equal(result['minus-drums-vocals'], stems['bass'] + stems['other']))

    def test_native_dimension_change_or_nonfinite_stem_is_rejected(self):
        for altered in (np.zeros((11, 2)), np.full((12, 2), np.nan)):
            stems = self.stems(); stems['drums'] = altered
            with self.assertRaises(ValueError):
                check.residuals(np.ones((12, 2)), stems)

    def test_guitar_or_missing_source_not_silently_accepted(self):
        stems = self.stems(); stems['guitar'] = stems.pop('other')
        with self.assertRaises(ValueError):
            check.residuals(np.ones((12, 2)), stems)

    def test_amplitude_keeps_overrange_samples_without_limiter(self):
        samples = np.array([[-2., .5], [2., -.5]])
        report = check.amplitude(samples)
        self.assertEqual(report['peak_abs'], 2)
        self.assertEqual(report['samples_above_unit_fraction'], .5)
        self.assertEqual(report['frames'], 2)
        self.assertEqual(report['channels'], 2)
        np.testing.assert_array_equal(samples, [[-2., .5], [2., -.5]])


class LineageTests(unittest.TestCase):
    def paired(self):
        source = {'id': 'a', 'audio_sha256': 'original', 'sample_rate_hz': 22050,
                  'duration_seconds': 60, 'frames': 1323000}
        derivative = {**source, 'audio_sha256': 'derivative', 'source_audio_sha256': 'original',
                      'condition': 'minus-drums'}
        reference = {'recording': {k: source[k] for k in ('id', 'audio_sha256', 'sample_rate_hz', 'duration_seconds')}}
        prediction = {'recording': {k: derivative[k] for k in ('id', 'audio_sha256', 'sample_rate_hz', 'duration_seconds')},
                      'analysis': {'source_separation': {'condition': 'minus-drums', 'protocol_sha256': 'p',
                      'inference_inputs_sha256': 'i', 'source_audio_sha256': 'original', 'accepted_for_playback': False}}}
        return reference, prediction, source, derivative

    def test_derivative_pairing_preserves_immutable_original_reference(self):
        ref, pred, source, derivative = self.paired(); frozen = copy.deepcopy(ref)
        check.validate_derivative(ref, pred, source, derivative, 'p', 'i')
        self.assertEqual(ref, frozen)
        self.assertNotEqual(ref['recording']['audio_sha256'], pred['recording']['audio_sha256'])

    def test_same_duration_wrong_audio_or_source_lineage_rejected(self):
        for target, field, value in [('prediction', 'audio_sha256', 'wrong'),
                                     ('derivative', 'source_audio_sha256', 'other-song'),
                                     ('derivative', 'frames', 1322999),
                                     ('reference', 'sample_rate_hz', 44100)]:
            ref, pred, source, derivative = self.paired()
            obj = {'prediction': pred['recording'], 'reference': ref['recording'], 'derivative': derivative}[target]
            obj[field] = value
            with self.assertRaises(ValueError):
                check.validate_derivative(ref, pred, source, derivative, 'p', 'i')

    def test_changed_protocol_or_promoted_output_rejected(self):
        for field, value in [('protocol_sha256', 'changed'), ('accepted_for_playback', True),
                             ('condition', 'minus-drums-vocals')]:
            ref, pred, source, derivative = self.paired()
            pred['analysis']['source_separation'][field] = value
            with self.assertRaises(ValueError):
                check.validate_derivative(ref, pred, source, derivative, 'p', 'i')


class FrozenPacketTests(unittest.TestCase):
    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                check.confined(Path(temporary), '../outside.wav')

    def test_condition_or_setting_change_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            packet = {'conditions': list(check.CONDITIONS), 'settings': copy.deepcopy(check.SETTINGS),
                      'frozen_source_files': {}, 'cases': []}
            packet['settings']['shifts'] = 1
            path = pack / 'protocol.json'; path.write_text(json.dumps(packet))
            with self.assertRaises(ValueError):
                check.validate_protocol(pack, check.pilot.sha(path))

    def test_changed_protocol_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary); (pack / 'protocol.json').write_text('{}')
            with self.assertRaises(ValueError):
                check.validate_protocol(pack, 'not-the-hash')

    def test_failed_condition_counts_requested_coverage_without_success_bias(self):
        rows = [{'reference_kind': kind, 'condition': 'minus-drums', 'status': 'error'} for kind in check.KINDS]
        summaries = check.summarize(rows)
        row = next(r for r in summaries if r['reference_kind'] == check.KINDS[0] and r['condition'] == 'minus-drums')
        self.assertEqual((row['failed_cases'], row['scored_audio_coverage'], row['majmin']), (1, 0, None))


if __name__ == '__main__':
    unittest.main()
