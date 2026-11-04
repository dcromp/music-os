"""Frozen source identity and corrupted controls must remain auditable/safe."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chart_aligner
import wonderwall_guided as guided


class WonderwallGuidedTests(unittest.TestCase):
    def source(self):
        return guided.load_source_chart(guided.DEFAULT_CHART)

    def test_controls_keep_recording_and_count_but_retain_independent_source(self):
        source = self.source()
        before = copy.deepcopy(source)
        controls = guided.build_controls(source)
        self.assertEqual(source, before)
        self.assertEqual(controls['reversed-order']['order'][0], {'section_id': 'chorus', 'repeat': 8})
        self.assertEqual(controls['reversed-order']['order'][-1], {'section_id': 'intro', 'repeat': 2})
        for control in controls.values():
            self.assertEqual(control['recording'], source['recording'])
            self.assertEqual(len(chart_aligner.expand_sections(control)[0]), 167)
            self.assertIn('never a candidate for playback', control['metadata']['review_status'])
        rich = set(chart_aligner.expand_sections(source)[0])
        simple = set(chart_aligner.expand_sections(controls['simplified-quality'])[0])
        self.assertEqual(rich, {'F#m7', 'A', 'Esus4', 'B7sus4', 'Dadd9', 'A/G#'})
        self.assertEqual(simple, {'F#m', 'A', 'E', 'B', 'D'})

    def test_timed_wrong_recording_or_changed_source_cannot_enter_frozen_run(self):
        source = self.source()
        variants = []
        timed = copy.deepcopy(source)
        timed['metadata']['start_seconds'] = 42
        variants.append((timed, 'timing field'))
        wrong = copy.deepcopy(source)
        wrong['recording']['id'] = 'different-edit'
        variants.append((wrong, 'identity'))
        changed = copy.deepcopy(source)
        changed['order'][0]['repeat'] = 3
        variants.append((changed, 'frozen teacher'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'chart.json'
            for value, message in variants:
                path.write_bytes(guided.encoded(value))
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    guided.load_source_chart(path)

    def test_unknown_or_no_chord_is_not_silently_simplified_in_quality_control(self):
        for label in ('N', 'X', 'F#maj7'):
            source = self.source()
            source['sections'][0]['sequence'][0] = label
            # All labels are legal decoder inputs; this frozen control refuses
            # any vocabulary outside its explicitly authored quality mutation.
            chart_aligner.validate_untimed_chart(source)
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'Unknown quality-control'):
                guided.build_controls(source)

    def test_existing_directory_or_alias_is_preserved_before_any_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'results'
            output.mkdir()
            sentinel = output / 'precious.txt'
            sentinel.write_text('keep original evidence')
            alias = root / 'alias'
            alias.symlink_to(output, target_is_directory=True)
            for target in (output, alias):
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'exists'):
                    guided.run(target, root / 'missing-audio.wav', root / 'missing-chart.json')
            self.assertEqual(sentinel.read_text(), 'keep original evidence')
            self.assertTrue(alias.is_symlink())


if __name__ == '__main__':
    unittest.main()
