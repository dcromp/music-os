import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import lab
import rich_quality_screen as screen
import rich_quality_suite as suite


def fixture_suite(folder):
    source = folder / 'suite'
    audio, reference_path = lab.create_fixture(source)
    reference = lab.load_chart(reference_path)
    reference['recording']['id'] = 'fixture'
    reference['recording']['audio_sha256'] = screen.sha(audio)
    lab.write_json(reference_path, reference)
    untimed = {'schema_version': chart_aligner.SCHEMA,
        'recording': {'id': 'fixture', 'title': 'Fixture', 'audio_sha256': screen.sha(audio)},
        'sequence': [event['label'] for event in reference['chords'] if event['label'] != 'N'],
        'mode': 'finite', 'start_policy': 'first', 'end_policy': 'last'}
    lab.write_json(source / 'untimed.json', untimed)
    case = {'id': 'fixture', 'condition': 'clean_sustain', 'split': 'screen',
        'recipe': {'family': 'plain_control'}, 'audio': audio.name,
        'reference': reference_path.name, 'untimed': 'untimed.json',
        'audio_sha256': screen.sha(audio), 'reference_sha256': screen.sha(reference_path),
        'untimed_sha256': screen.sha(source / 'untimed.json')}
    lab.write_json(source / 'manifest.json', {'suite_version': 'test', 'cases': [case]})
    return source, audio, reference_path, reference


class RichQualityScreenTests(unittest.TestCase):
    def test_control_inputs_keep_roots_and_never_contain_times(self):
        chart = {'schema_version': chart_aligner.SCHEMA,
            'recording': {'id': 'test', 'title': 'Untimed'},
            'sequence': ['Em7', 'Dsus4', 'A7sus4', 'Cadd9']}
        variants = screen.control_charts(chart, 'rich_progression')
        self.assertEqual(set(variants), {'correct', 'simplified_quality', 'wrong_quality', 'wrong_section_order'})
        for name, value in variants.items():
            chart_aligner.validate_untimed_chart(value)
            self.assertNotIn('start_seconds', json.dumps(value))
            if name not in ('correct', 'wrong_section_order'):
                self.assertEqual([suite.chord_semantics(label)['root'] for label in value['sequence']],
                                 [suite.chord_semantics(label)['root'] for label in chart['sequence']])
        self.assertEqual(chart['sequence'], ['Em7', 'Dsus4', 'A7sus4', 'Cadd9'])
        plain = copy.deepcopy(chart)
        plain['sequence'] = ['Em', 'D', 'A', 'C']
        self.assertIn('extra_extensions', screen.control_charts(plain, 'plain_control'))

    def test_residual_metric_catches_upgrade_even_when_root_is_correct(self):
        with tempfile.TemporaryDirectory() as folder:
            _, _, _, reference = fixture_suite(Path(folder))
            prediction = copy.deepcopy(reference)
            harmonic = 0.0
            for event in prediction['chords']:
                if event['label'] != 'N':
                    harmonic += event['end_seconds'] - event['start_seconds']
                    event['label'] = suite.chord_to_rich(event['label'])
            errors = screen.retained_error_metrics(reference, prediction)
            self.assertAlmostEqual(errors['retained_erroneous_label_seconds'], harmonic)
            self.assertAlmostEqual(errors['retained_erroneous_rich_label_seconds'], harmonic)
            self.assertEqual(errors['erroneous_rich_on_plain_fraction'], 1)
            for event in prediction['chords']:
                if event['label'] != 'N':
                    event['label'] = 'X'
            errors = screen.retained_error_metrics(reference, prediction)
            self.assertEqual(errors['retained_erroneous_label_seconds'], 0)
            self.assertAlmostEqual(errors['unknown_on_reference_harmony_seconds'], harmonic)

    def test_all_inference_precedes_hidden_reference_scoring_and_raw_bytes_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, audio, reference_path, reference = fixture_suite(folder)
            stages, chart_variants, original_bytes = [], [], {}
            actual_align = chart_aligner.align
            actual_score = suite.score

            def batches(manifest_path, stage, timeout):
                manifest = json.loads(manifest_path.read_text())
                self.assertEqual(set(manifest['cases'][0]), {'id', 'audio'})
                self.assertNotIn('reference', manifest_path.read_text())
                self.assertNotIn('sequence', manifest_path.read_text())
                stages.append('raw-inference')
                for candidate in screen.RECOGNIZERS:
                    prediction = copy.deepcopy(reference)
                    prediction['analysis']['parameters'] = {'unchanged_native': candidate}
                    output = stage / 'cases/fixture' / f'{candidate}.json'
                    lab.write_json(output, prediction)
                    original_bytes[candidate] = output.read_bytes()
                return {name: {'status': 'ok'} for name in screen.RECOGNIZERS}

            def extract(audio_path, identifier):
                stages.append('extract')
                self.assertEqual(screen.sha(audio_path), screen.sha(audio))
                self.assertEqual(identifier, 'fixture')
                return {'schema_version': 'mock-native'}

            def align(audio_path, chart_path, **parameters):
                self.assertNotIn('score', stages)
                chart = json.loads(chart_path.read_text())
                chart_variants.append(chart)
                for key in chart_aligner.TIMING_KEYS:
                    self.assertNotIn(f'"{key}"', chart_path.read_text())
                self.assertEqual({key: value for key, value in parameters.items() if key != 'evidence_json'}, screen.DEFAULTS)
                stages.append('align')
                parameters.pop('evidence_json', None)
                prediction = actual_align(audio_path, chart_path, **parameters)
                return prediction

            def score(expected, predicted, **keywords):
                stages.append('score')
                return actual_score(expected, predicted, **keywords)

            def guarded_load(path):
                if Path(path) == reference_path:
                    self.assertEqual(stages.count('align'), 6)
                    self.assertIn('raw-inference', stages)
                return json.loads(Path(path).read_text())

            output = folder / 'screen'
            with patch.object(screen, 'raw_batches', side_effect=batches), \
                 patch.object(nnls_chroma_adapter, 'extract', side_effect=extract), \
                 patch.object(nnls_chroma_adapter, 'validate_evidence'), \
                 patch.object(chart_aligner, 'align', side_effect=align), \
                 patch.object(suite, 'score', side_effect=score), \
                 patch.object(lab, 'load_chart', side_effect=guarded_load):
                report = screen.run(source, output)
            self.assertEqual(report['failed_attempts'], 0)
            self.assertEqual(report['successful_attempts'], 8)
            self.assertEqual(stages[:8], ['raw-inference', 'extract'] + ['align'] * 6)
            self.assertEqual(stages[8:], ['score'] * 8)
            for candidate in screen.RECOGNIZERS:
                self.assertEqual((output / f'cases/fixture/{candidate}.json').read_bytes(), original_bytes[candidate])
            for first, second in zip(chart_variants[::2], chart_variants[1::2]):
                self.assertEqual(first, second)
            self.assertTrue(report['gates']['all_requested_inference_and_scoring_complete'])
            self.assertFalse(report['gates']['wrong_charts_fully_rejected'])
            self.assertFalse(report['gates']['production_accuracy_or_readiness_established'])
            self.assertTrue((output / 'report.json').is_file())
            self.assertEqual(list(folder.glob('.screen.*')), [])
            self.assertEqual(screen.sha(audio), report['input_hashes'][0]['audio_sha256'])
            self.assertEqual(screen.sha(reference_path), report['input_hashes'][0]['hidden_reference_sha256'])
            self.assertIn('crema/family/plain_control', report['summary'])
            self.assertIn('conditional timing, not recognition accuracy', (output / 'report.md').read_text())

    def test_native_timeout_preserves_spectral_results_and_failed_denominators(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, _, _, _ = fixture_suite(folder)
            with patch.object(screen, 'raw_batches', return_value={}), \
                 patch.object(nnls_chroma_adapter, 'extract', side_effect=subprocess.TimeoutExpired('host', 180)):
                report = screen.run(source, folder / 'screen')
            self.assertEqual(report['successful_attempts'], 3)
            self.assertEqual(report['failed_attempts'], 5)
            summary = report['summary']['nnls-chroma/correct/all']
            self.assertEqual(summary['successful_cases'], 0)
            self.assertEqual(summary['failed_cases'], 1)
            self.assertFalse(report['gates']['all_requested_inference_and_scoring_complete'])
            self.assertFalse(report['gates']['wrong_charts_fully_rejected'])
            errors = [row['reason'] for row in report['rows'] if row['status'] == 'error']
            self.assertTrue(any('timed out' in error for error in errors))

    def test_existing_output_rejected_before_any_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, _, _, _ = fixture_suite(folder)
            output = folder / 'screen'
            output.mkdir()
            (output / 'report.json').write_text('other owner')
            with patch.object(screen, 'raw_batches') as batches, self.assertRaisesRegex(ValueError, 'no overwrite'):
                screen.run(source, output)
            batches.assert_not_called()
            self.assertEqual((output / 'report.json').read_text(), 'other owner')

    def test_complete_preflight_refuses_duplicate_ids_escape_and_bad_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, _, _, _ = fixture_suite(folder)
            manifest_path = source / 'manifest.json'
            original = json.loads(manifest_path.read_text())
            bad = copy.deepcopy(original)
            bad['cases'] *= 2
            lab.write_json(manifest_path, bad)
            with self.assertRaisesRegex(ValueError, 'collide'):
                screen.preflight(source, folder / 'screen')
            bad = copy.deepcopy(original)
            bad['cases'][0]['untimed'] = '../outside.json'
            (folder / 'outside.json').write_text('{}')
            lab.write_json(manifest_path, bad)
            with self.assertRaisesRegex(ValueError, 'inside the suite'):
                screen.preflight(source, folder / 'screen')
            bad = copy.deepcopy(original)
            bad['cases'][0]['audio_sha256'] = '0' * 64
            lab.write_json(manifest_path, bad)
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                screen.preflight(source, folder / 'screen')
            lab.write_json(manifest_path, original)
            with self.assertRaisesRegex(ValueError, 'outside the source'):
                screen.preflight(source, source / 'screen')

    def test_atomic_publication_rejects_even_empty_concurrent_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            stage, target = folder / 'stage', folder / 'target'
            stage.mkdir()
            (stage / 'report.json').write_text('ours')
            target.mkdir()
            with self.assertRaisesRegex(ValueError, 'concurrently'):
                screen.publish_directory_exclusively(stage, target)
            self.assertEqual((stage / 'report.json').read_text(), 'ours')
            self.assertEqual(list(target.iterdir()), [])
            target.rmdir()
            screen.publish_directory_exclusively(stage, target)
            self.assertFalse(stage.exists())
            self.assertEqual((target / 'report.json').read_text(), 'ours')

    def test_corrupt_gate_cannot_pass_for_missing_failed_or_nonfinite_results(self):
        base = {'status': 'ok', 'control': 'extra_extensions',
                'residual_errors': {'retained_erroneous_label_seconds': 0.0}}
        self.assertTrue(screen.corrupt_charts_rejected([base]))
        self.assertFalse(screen.corrupt_charts_rejected([]))
        self.assertFalse(screen.corrupt_charts_rejected([{'status': 'ok', 'control': 'extra_extensions'}]))
        for status, value in [('error', 0), ('ok', float('nan')), ('ok', True), ('ok', -1), ('ok', .01)]:
            changed = copy.deepcopy(base)
            changed['status'] = status
            changed['residual_errors']['retained_erroneous_label_seconds'] = value
            self.assertFalse(screen.corrupt_charts_rejected([changed]))

    def test_aggregation_reports_failure_denominator_and_no_fake_null_means(self):
        rows = [{'status': 'ok', 'metrics': {'root_chord_agreement': .9,
            'supported_vocabulary_chord_coverage': None, 'chord_reference_seconds': 10},
            'residual_errors': {'retained_erroneous_label_seconds': 4}},
            {'status': 'error', 'reason': 'native unavailable'}]
        summary = screen.aggregate(rows)
        self.assertEqual(summary['requested_cases'], 2)
        self.assertEqual(summary['successful_cases'], 1)
        self.assertEqual(summary['failed_cases'], 1)
        self.assertNotIn('supported_vocabulary_chord_coverage', summary['metrics'])
        self.assertEqual(summary['residual_errors']['retained_erroneous_label_seconds'], 4)


if __name__ == '__main__':
    unittest.main()
