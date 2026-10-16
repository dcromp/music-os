import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_chord_screen as core
import lab
import rich_quality_screen
import rich_quality_suite


def chart(labels):
    return {"schema_version": "1.0", "recording": {"id": "test", "title": "Test",
        "sample_rate_hz": 22050, "duration_seconds": len(labels), "audio_sha256": "abc"},
        "analysis": {"id": "test", "algorithm": "test", "version": "1", "runtime_seconds": 0},
        "chords": [{"start_seconds": i, "end_seconds": i + 1, "label": label} for i, label in enumerate(labels)]}


class CoreChordTests(unittest.TestCase):
    def test_removable_extensions_preserve_minor_and_bass(self):
        labels = ["C7/Bb", "Cmaj7/7", "Dadd9/F#", "F#:min7/A", "B:sus4(b7)/b7"]
        self.assertEqual([core.core_label(label) for label in labels],
            ["C/Bb", "C/7", "D/F#", "F#m/A", "Bsus4/b7"])
        for label in labels:
            before = rich_quality_suite.chord_semantics(label)
            after = core.core_semantics(label)
            self.assertEqual((before['root'], before['bass']), (after['root'], after['bass']))

    def test_suspensions_are_not_major_or_minor(self):
        score = core.score(chart(['D', 'Dsus4', 'A7', 'A7sus4']),
            chart(['Dsus4', 'D', 'A7sus4', 'A7']))
        self.assertEqual(score['root_agreement'], 1)
        self.assertEqual(score['core_quality_agreement'], 0)
        self.assertEqual(score['suspension_vs_third_error_seconds'], 4)

    def test_exact_score_is_separate_and_inputs_unchanged(self):
        reference = chart(['Em7', 'Cadd9', 'Dsus4', 'A7sus4', 'G7', 'N'])
        prediction = chart(['Em', 'C', 'Dsus4', 'Asus4', 'G', 'X'])
        before = copy.deepcopy((reference, prediction))
        score = core.score(reference, prediction)
        self.assertEqual(score['reference_harmonic_seconds'], 5)
        self.assertEqual(score['exact_quality_agreement'], .2)
        self.assertEqual(score['core_quality_agreement'], 1)
        self.assertEqual(score['extension_difference_ignored_seconds'], 4)
        self.assertEqual((reference, prediction), before)

    def test_unknown_missing_and_unsupported_cannot_earn_credit(self):
        reference = chart(['C', 'Am', 'D', 'G', 'F'])
        prediction = chart(['N', 'X', 'Dbanana', 'G', 'F'])
        prediction['chords'].pop()
        score = core.score(reference, prediction)
        self.assertEqual(score['core_quality_agreement'], .2)
        self.assertEqual(score['root_agreement'], .2)
        for key in ('unknown_seconds', 'no_chord_seconds', 'unsupported_seconds', 'missing_prediction_seconds'):
            self.assertEqual(score[key], 1)
        self.assertEqual(sum(score[key] for key in ('harmonic_prediction_seconds', 'unknown_seconds',
            'no_chord_seconds', 'unsupported_seconds', 'missing_prediction_seconds')), 5)

    def test_preserves_undeclared_qualities_and_ambiguous_harte(self):
        for label in ('Cdim7', 'Caug', 'C5', 'Cm7b5', 'C6', 'Cm6', 'Cmmaj7', 'Csus4(7)', 'Cbanana', 'N', 'X'):
            self.assertEqual(core.core_label(label), label)
        self.assertEqual(core.core_semantics('Csus4(7)')['status'], 'unsupported')
        self.assertEqual(core.core_semantics('Csus4(b7)')['quality'], 'sus4')

    def test_named_and_degree_bass_and_enharmonic_roots(self):
        score = core.score(chart(['Dbmaj7/F', 'C7/b7']), chart(['C#/F', 'C/Bb']))
        self.assertEqual(score['core_quality_agreement'], 1)
        self.assertEqual(score['core_with_bass_agreement'], 1)
        score = core.score(chart(['C7/Bb']), chart(['C/G']))
        self.assertEqual(score['core_quality_agreement'], 1)
        self.assertEqual(score['core_with_bass_agreement'], 0)

    def test_duration_overlap_and_macro_mean_are_not_the_same(self):
        reference = chart(['C', 'Am', 'D'])
        prediction = chart(['C', 'Am', 'D'])
        prediction['chords'] = [{'start_seconds': 0, 'end_seconds': 1.5, 'label': 'C'},
            {'start_seconds': 1.5, 'end_seconds': 3, 'label': 'Am'}]
        score = core.score(reference, prediction)
        self.assertAlmostEqual(score['core_quality_agreement'], .5)
        group = core.aggregate([{'metrics': score}, {'metrics': core.score(chart(['G']), chart(['G']))}])
        self.assertAlmostEqual(group['core_quality_mean_case_agreement'], .75)
        self.assertAlmostEqual(group['core_quality_duration_weighted_agreement'], .625)

    def test_invalid_audio_identity_overlap_or_reference_rejected(self):
        expected = chart(['C', 'G'])
        wrong = chart(['C', 'G']); wrong['recording']['audio_sha256'] = 'different'
        with self.assertRaises(ValueError): core.score(expected, wrong)
        wrong = chart(['C', 'G']); wrong['chords'][1]['start_seconds'] = .5
        with self.assertRaises(ValueError): core.score(expected, wrong)
        with self.assertRaises(ValueError): core.score(chart(['X']), chart(['C']))
        with self.assertRaises(ValueError): core.score(chart(['N']), chart(['N']))
        with self.assertRaises(ValueError): core.aggregate([])

    def test_cached_runner_checks_hashes_and_refuses_overwrite(self):
        from test_rich_quality_screen import fixture_suite
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, audio, refpath, reference = fixture_suite(root)
            manifest_path = source / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['cases'][0]['family'] = 'plain_control'
            lab.write_json(manifest_path, manifest)
            saved = root / 'saved'
            rows = []
            for candidate in core.CANDIDATES:
                path = saved / f'cases/fixture/{candidate}.json'
                lab.write_json(path, reference)
                metrics = rich_quality_suite.score(reference, reference)
                rows.append({'kind': 'recognition', 'case_id': 'fixture', 'candidate': candidate, 'status': 'ok',
                    'output': str(path.relative_to(saved)), 'output_sha256': rich_quality_screen.sha(path), 'metrics': metrics})
            lab.write_json(saved / 'report.json', {'manifest_sha256': rich_quality_screen.sha(manifest_path), 'rows': rows})
            report = core.run(source, saved, root / 'out')
            self.assertEqual(report['completed_comparisons'], 2)
            self.assertEqual(report['summary']['crema']['core_quality_mean_case_agreement'], 1)
            self.assertFalse(report['production_accuracy_established'])
            with self.assertRaises(ValueError): core.run(source, saved, root / 'out')
            path.write_text(path.read_text() + '\n')
            with self.assertRaises(ValueError): core.run(source, saved, root / 'out-new')
            self.assertFalse((root / 'out-new').exists())


if __name__ == '__main__':
    unittest.main()
