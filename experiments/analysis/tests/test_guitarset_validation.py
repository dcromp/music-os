import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import guitarset_validation as validation


class FreshValidationTests(unittest.TestCase):
    def test_native_reference_pair_preserves_sheet_derived_boundaries(self):
        intended = {'namespace': 'chord', 'annotation_metadata': {'annotation_rules': ''},
                    'data': [{'time': 0, 'duration': 2, 'value': 'C:maj'}]}
        performed = copy.deepcopy(intended)
        performed['annotation_metadata']['annotation_rules'] = validation.PERFORMED_RULE
        performed['data'][0]['value'] = 'C:maj7'
        pair = validation.annotation_pair({'annotations': [performed, intended]})
        self.assertIs(pair[0], intended)
        self.assertIs(pair[1], performed)

    def test_native_boundary_or_root_changes_are_rejected(self):
        for change in ({'time': .1}, {'value': 'D:maj'}):
            intended = {'namespace': 'chord', 'annotation_metadata': {'annotation_rules': ''},
                        'data': [{'time': 0, 'duration': 2, 'value': 'C:maj'}]}
            performed = copy.deepcopy(intended)
            performed['annotation_metadata']['annotation_rules'] = validation.PERFORMED_RULE
            performed['data'][0].update(change)
            with self.assertRaises(ValueError):
                validation.annotation_pair({'annotations': [intended, performed]})

    def test_ambiguous_annotation_semantics_are_rejected(self):
        row = {'namespace': 'chord', 'annotation_metadata': {'annotation_rules': ''}, 'data': []}
        with self.assertRaises(ValueError):
            validation.annotation_pair({'annotations': [row, row]})

    def test_pairing_rejects_same_duration_different_audio(self):
        reference = {'recording': {'id': 'a', 'audio_sha256': 'a' * 64,
                                  'sample_rate_hz': 22050, 'duration_seconds': 2}}
        prediction = copy.deepcopy(reference)
        prediction['recording']['audio_sha256'] = 'b' * 64
        with patch.object(validation.pilot, 'score') as scorer:
            with self.assertRaises(ValueError):
                validation.checked_score(reference, prediction, 'crema')
            scorer.assert_not_called()

    def test_pairing_delegates_only_after_exact_identity(self):
        reference = {'recording': {'id': 'a', 'audio_sha256': 'a' * 64,
                                  'sample_rate_hz': 22050, 'duration_seconds': 2}}
        with patch.object(validation.pilot, 'score', return_value={'score': .5}) as scorer:
            self.assertEqual(validation.checked_score(reference, copy.deepcopy(reference), 'crema'), {'score': .5})
            scorer.assert_called_once()

    def test_protocol_replay_checks_code_but_does_not_require_models(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            selection = root / 'selection.json'; selection.write_text('{}')
            source = root / 'experiments/analysis/a.py'; source.parent.mkdir(parents=True); source.write_text('code')
            protocol = {'schema_version': 'guitarset-chord-protocol-1.0',
                        'selection_sha256': validation.pilot.sha(selection),
                        'candidates': list(validation.CANDIDATES),
                        'frozen_files': {'experiments/analysis/a.py': validation.pilot.sha(source),
                                         '.venv-crema/missing-model': 'a' * 64}}
            path = root / 'protocol.json'; path.write_text(json.dumps(protocol))
            validation.validate_protocol(path, selection, root, verify_model_assets=False)
            with self.assertRaises(FileNotFoundError):
                validation.validate_protocol(path, selection, root)
            source.write_text('changed')
            with self.assertRaises(ValueError):
                validation.validate_protocol(path, selection, root, verify_model_assets=False)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'base'; base.mkdir()
            outside = Path(d) / 'outside'; outside.write_text('data')
            with self.assertRaises(ValueError):
                validation.confined(base, '../outside')

    def test_failed_holdout_is_counted_with_requested_audio_coverage(self):
        cases = [{'id': 'a', 'split': 'holdout', 'performance_type': 'solo',
                  'recording': {'duration_seconds': 2}}]
        rows = [{'candidate': 'crema', 'reference_kind': kind, 'split': 'holdout',
                 'performance_type': 'solo', 'status': 'error'} for kind in ('intended', 'performed')]
        results = validation.summarize(rows, ['crema'], cases)
        row = next(r for r in results if r['split'] == 'holdout' and r['performance_type'] == 'solo'
                   and r['reference_kind'] == 'intended')
        self.assertEqual((row['failed_cases'], row['scored_audio_coverage'], row['majmin']), (1, 0, None))


if __name__ == '__main__':
    unittest.main()
