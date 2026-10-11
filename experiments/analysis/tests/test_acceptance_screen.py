import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acceptance_screen as screen
import chart_aligner
import lab
import rich_quality_screen


def chart(labels, lengths=None):
    lengths = lengths or [1] * len(labels)
    cursor, events = 0.0, []
    for label, seconds in zip(labels, lengths):
        events.append({'start_seconds': cursor, 'end_seconds': cursor + seconds, 'label': label})
        cursor += seconds
    return {'schema_version': '1.0', 'recording': {'id': 'sample', 'title': 'Sample',
        'duration_seconds': cursor, 'sample_rate_hz': 22050},
        'analysis': {'id': 'test', 'algorithm': 'test', 'version': '1', 'runtime_seconds': 0},
        'chords': events}


def score_row(policy, backend='spectral', control='correct', quality=.9, wrong=0, status='ok'):
    return {'policy': policy, 'backend': backend, 'control': control, 'status': status,
        'metrics': {'semantic_chord_quality_agreement': quality,
            'chord_reference_seconds': 10, 'exact_chord_quality_correct_seconds': quality * 10,
            'unknown_on_chord_seconds': (1 - quality) * 10, 'false_no_chord_on_chord_seconds': 0},
        'residual_errors': {'retained_erroneous_label_seconds': wrong},
        'discard': {'raw_true_correct_label_seconds': 10, 'true_correct_labels_discarded_seconds': (1-quality)*10}}


class AcceptanceScreenTests(unittest.TestCase):
    def test_discard_counts_only_correct_raw_labels_and_distinguishes_X_N(self):
        reference = chart(['Cadd9', 'G'])
        raw = chart(['Cadd9', 'F'])
        final = chart(['X', 'N', 'X'], [.6, .4, 1])
        result = screen.discard_metrics(reference, raw, final)
        self.assertEqual(result['raw_true_correct_label_seconds'], 1)
        self.assertEqual(result['true_correct_labels_discarded_seconds'], 1)
        self.assertAlmostEqual(result['true_correct_labels_discarded_to_X_seconds'], .6)
        self.assertAlmostEqual(result['true_correct_labels_discarded_to_N_seconds'], .4)
        self.assertEqual(result['true_correct_labels_discarded_fraction'], 1)

    def test_correct_kept_and_enharmonic_equivalents_are_not_discarded(self):
        reference = chart(['C#add9', 'D'])
        raw = chart(['Dbadd9', 'D'])
        result = screen.discard_metrics(reference, raw, chart(['Dbadd9', 'D']))
        self.assertEqual(result['raw_true_correct_label_seconds'], 2)
        self.assertEqual(result['true_correct_labels_discarded_seconds'], 0)
        self.assertFalse(screen.label_same('Cadd9', 'C'))
        self.assertFalse(screen.label_same('N', 'N'))

    def test_weighted_coverage_failure_denominators_and_wrong_cases(self):
        first = score_row('strict', control='extra_extensions', quality=.5, wrong=4)
        second = score_row('strict', control='extra_extensions', quality=1, wrong=0)
        second['metrics']['chord_reference_seconds'] = 30
        second['metrics']['exact_chord_quality_correct_seconds'] = 30
        failed = {'status': 'error', 'control': 'extra_extensions'}
        result = screen.aggregate([first, second, failed])
        self.assertEqual(result['requested_cases'], 3)
        self.assertEqual(result['failed_cases'], 1)
        self.assertEqual(result['wrong_chart_cases_with_wrong_labels_surviving'], 1)
        self.assertAlmostEqual(result['duration_weighted_correct_harmonic_fraction'], 35/40)
        self.assertAlmostEqual(result['duration_weighted_wrong_label_fraction'], .1)
        self.assertEqual(result['metrics']['semantic_chord_quality_agreement'], .75)

    def test_reject_all_cannot_win_and_quality_loss_is_per_backend(self):
        rows = []
        for backend in screen.BACKENDS:
            rows.append(score_row('old-frozen', backend, quality=.95))
            for option in screen.OPTIONS:
                quality = .9 if option['id'] == 'lenient' else .2
                rows += [score_row(option['id'], backend, quality=quality),
                    score_row(option['id'], backend, 'wrong_quality', quality=quality,
                        wrong=2 if option['id'] == 'lenient' else 0)]
        summaries = screen.option_summary(rows)
        selected, reason = screen.select_option(summaries)
        self.assertEqual(selected['id'], 'lenient')
        self.assertTrue(selected['eligible_quality_loss'])
        self.assertIn('gate met', reason)
        rows = [row for row in rows if row['policy'] != 'lenient']
        for backend in screen.BACKENDS:
            rows += [score_row('lenient', backend, quality=.9 if backend == 'spectral' else .7),
                score_row('lenient', backend, 'wrong_quality', quality=.8, wrong=0)]
        selected, reason = screen.select_option(screen.option_summary(rows))
        self.assertFalse(selected['eligible_quality_loss'])
        self.assertIn('no acceptable development policy', reason)

    def test_eligible_selection_minimizes_corrupt_seconds_then_correct_coverage(self):
        rows = []
        for backend in screen.BACKENDS:
            rows.append(score_row('old-frozen', backend, quality=.95))
            for option in screen.OPTIONS:
                rows += [score_row(option['id'], backend, quality=.9 if option['id']=='strict' else .85),
                    score_row(option['id'], backend, 'wrong_quality', wrong=1 if option['id'] in ('strict','very-strict') else 2)]
        selected, _ = screen.select_option(screen.option_summary(rows))
        self.assertEqual(selected['id'], 'strict')

    def test_no_successful_option_cannot_create_freeze(self):
        summaries = screen.option_summary([score_row('lenient', status='error')])
        with self.assertRaisesRegex(ValueError, 'No all-success'):
            screen.select_option(summaries)

    def test_spectral_cache_is_immutable_exact_grid_and_restores_on_failure(self):
        signal = np.sin(np.arange(22050) * .02)
        original = chart_aligner.features
        with self.assertRaisesRegex(ValueError, 'different audio/grid'):
            with screen.cached_spectral_features(signal, 22050) as digest:
                self.assertEqual(len(digest), 64)
                first = chart_aligner.features(signal, 22050, .025, .18)
                second = chart_aligner.features(signal.copy(), 22050, .025, .18)
                self.assertIs(first['chroma'], second['chroma'])
                self.assertFalse(first['chroma'].flags.writeable)
                chart_aligner.features(signal, 22050, .025, .12)
        self.assertIs(chart_aligner.features, original)

    def test_progress_separates_silence_advances_and_no_active_events(self):
        prediction = {'alignment_evidence': {'frame_columns': ['time_seconds','sequence_index','silent'],
            'frames': [[0,0,True],[.025,1,True],[.05,1,False],[.075,2,False]],
            'proposed_path_events_before_gap_mask': [{'label':'C','sequence_index':1,'evidence':{'active_frames':0}}],
            'diagnostics': {'unvisited_sequence_indices':[3], 'path_transitions':2}}}
        result = screen.progress_metrics(prediction)
        self.assertEqual(result['silent_frame_position_transitions'], 1)
        self.assertEqual(result['no_active_harmonic_evidence_proposed_event_count'], 1)
        self.assertEqual(result['unvisited_supplied_position_count'], 1)

    def test_declaration_is_exclusive_and_module_or_grid_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(screen, 'implementation_hashes', return_value={'runner':'a'}):
            path = Path(folder)/'declaration.json'
            screen.declare(path, 'b'*64)
            digest = screen.sha(path)
            value = screen.load_declaration(path, digest)
            self.assertFalse(value['development_outcomes_consumed'])
            with self.assertRaisesRegex(ValueError, 'exists'):
                screen.declare(path, 'b'*64)
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                screen.load_declaration(path, 'c'*64)
            with patch.object(screen, 'implementation_hashes', return_value={'runner':'changed'}):
                with self.assertRaisesRegex(ValueError, 'changed before development'):
                    screen.load_declaration(path, digest)

    def test_frozen_hash_and_module_checks_precede_validation_manifest_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            frozen_path = folder/'freeze.json'
            frozen_path.write_text('{}')
            with patch.object(screen, 'source_manifest') as manifest, self.assertRaisesRegex(ValueError, 'SHA differs'):
                screen.validate(frozen_path, '0'*64, folder/'historical', folder/'cache', folder/'fresh', folder/'fresh-cache', folder/'output')
            manifest.assert_not_called()

    def test_output_inside_source_or_existing_empty_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder/'source'
            source.mkdir()
            with self.assertRaisesRegex(ValueError, 'separate'):
                screen.validate_output(source/'nested', [source])
            output = folder/'output'
            output.mkdir()
            with self.assertRaisesRegex(ValueError, 'no overwrite'):
                screen.validate_output(output, [source])

    def test_fixture_repeat_controls_are_hash_checked_and_not_replaced_by_quality_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            base = {'schema_version':chart_aligner.SCHEMA,'recording':{'id':'test','title':'Test'},
                'sequence':['Em7','G','Em7']}
            missing = copy.deepcopy(base)
            missing['sequence'] = ['Em7','G']
            path = folder/'missing.json'
            lab.write_json(path, missing)
            case = {'untimed_controls':{'missing_repeat':{'path':'missing.json','sha256':screen.sha(path)}}}
            controls = screen.case_controls(folder, case, base, 'section_repeat')
            self.assertEqual(controls['missing_repeat']['sequence'], ['Em7','G'])
            self.assertEqual(controls['correct']['sequence'], base['sequence'])
            case['untimed_controls']['missing_repeat']['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                screen.case_controls(folder, case, base, 'section_repeat')

    def test_all_dataset_inference_precedes_reference_load_and_old_bytes_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, cache, stage = folder/'suite', folder/'cache', folder/'stage'
            audio, reference_path = lab.create_fixture(source)
            reference = lab.load_chart(reference_path)
            reference['recording'].update(id='fixture', audio_sha256=screen.sha(audio))
            lab.write_json(reference_path, reference)
            untimed = {'schema_version':chart_aligner.SCHEMA,'recording':{'id':'fixture','title':'Test', 'audio_sha256':screen.sha(audio)},
                'sequence':[event['label'] for event in reference['chords'] if event['label']!='N'],
                'mode':'finite','start_policy':'first','end_policy':'last'}
            lab.write_json(source/'untimed.json',untimed)
            case = {'id':'fixture','split':'screen','condition':'clean_sustain','recipe':{'family':'plain_control'},
                'audio':audio.name,'reference':reference_path.name,'untimed':'untimed.json'}
            lab.write_json(source/'manifest.json', {'suite_version':'test','cases':[case]})
            cache_case = cache/'cases/fixture'
            cache_case.mkdir(parents=True)
            evidence = cache_case/'nnls-evidence.json'
            evidence.write_text(json.dumps({'recording':{'id':'fixture'}}))
            old_bytes = {}
            for control, value in rich_quality_screen.control_charts(untimed,'plain_control').items():
                untimed_path = cache_case/f'{control}-untimed.json'
                lab.write_json(untimed_path,value)
                for backend in screen.BACKENDS:
                    prediction = chart_aligner.align(audio,untimed_path,**screen.GUARD_COMMON)
                    if backend=='nnls-chroma':
                        prediction['alignment_evidence']['acoustic_input']['evidence_sha256']=screen.sha(evidence)
                    path = cache_case/f'{control}-{backend}.json'
                    lab.write_json(path,prediction)
                    old_bytes[path.name]=path.read_bytes()
            actual_load = lab.load_chart
            actual_align = chart_aligner.align
            calls = []
            def align(audio_path, chart_path, **parameters):
                self.assertNotIn('reference', calls)
                calls.append('inference')
                parameters.pop('evidence_json',None)
                for name in ('quality_margin','added_tone_ratio','added_tone_fraction'):
                    parameters.pop(name)
                return actual_align(audio_path,chart_path,**parameters)
            def load(path):
                if Path(path)==reference_path:
                    self.assertEqual(calls.count('inference'),6)
                    calls.append('reference')
                return actual_load(path)
            guard = SimpleNamespace(align=align,__file__=__file__)
            with patch.object(screen,'guarded_module',return_value=guard), \
                patch.object(screen.nnls_chroma_adapter,'validate_evidence'), \
                patch.object(lab,'load_chart',side_effect=load):
                rows, provenance = screen.infer_dataset(source,cache,stage,dataset='development',split='screen',options=[screen.OPTIONS[0]],old_cached=True)
            self.assertEqual(len(rows),12)
            self.assertTrue(all(row['status']=='ok' for row in rows),[(row['control'],row['policy'],row.get('reason')) for row in rows if row['status']!='ok'])
            self.assertEqual(calls[:6],['inference']*6)
            hashes = {row['spectral_feature_arrays_sha256'] for row in rows}
            self.assertEqual(len(hashes),1)
            for row in rows:
                if row['policy']=='old-frozen':
                    path = stage/row['output']
                    old_name = f"{row['control']}-{row['backend']}.json"
                    self.assertEqual(path.read_bytes(),old_bytes[old_name])
            self.assertTrue(provenance['old_outputs_reused_byte_identically'])


if __name__ == '__main__':
    unittest.main()
