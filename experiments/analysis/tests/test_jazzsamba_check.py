import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jazzsamba_check as check


class FrozenProjectionTests(unittest.TestCase):
    def references(self):
        rich = {'recording': {'id': 'a'}, 'chords': [{'start_seconds': 0, 'end_seconds': 1,
                'label': 'X', 'native_label': 'C7alt',
                'source_fields': {'root': 'C', 'triad': 'maj', 'is_no_chord': 'False'}}]}
        core = copy.deepcopy(rich); core['chords'][0]['label'] = 'C:maj'
        return rich, core

    def test_declared_projection_is_checked_against_pinned_source_fields(self):
        rich, core = self.references()
        check.validate_core_reference(rich, core)
        core['chords'][0]['label'] = 'D:maj'
        with self.assertRaises(ValueError):
            check.validate_core_reference(rich, core)

    def test_core_timing_and_source_changes_are_rejected(self):
        for field, value in (('end_seconds', .8), ('native_label', 'changed')):
            rich, core = self.references(); core['chords'][0][field] = value
            with self.assertRaises(ValueError):
                check.validate_core_reference(rich, core)


@unittest.skipUnless(importlib.util.find_spec('mir_eval'), 'Requires pinned mir_eval')
class JazzReferenceTests(unittest.TestCase):
    def test_conversion_preserves_original_and_unknowns(self):
        reference = {'chords': [{'label': 'C:min7', 'native_label': 'Cm7'},
                                {'label': 'X', 'native_label': 'C7alt'}]}
        original = copy.deepcopy(reference)
        converted = check.harte_reference(reference)
        self.assertEqual(reference, original)
        self.assertEqual(converted['chords'][0]['native_label'], 'C:min7')
        self.assertEqual(converted['chords'][0]['source_native_symbol'], 'Cm7')
        self.assertEqual(converted['chords'][1]['native_label'], 'X')

    def test_invalid_harte_conversion_is_not_guessed(self):
        with self.assertRaises(Exception):
            check.harte_reference({'chords': [{'label': 'not-a-chord', 'native_label': 'bad'}]})


if __name__ == '__main__':
    unittest.main()
