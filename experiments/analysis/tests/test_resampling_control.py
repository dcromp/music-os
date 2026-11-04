import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resampling_control as control


class ControlFreezeTests(unittest.TestCase):
    def test_any_derivative_output_prevents_preinference_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            control.require_unexposed(pack)
            folder = pack / 'cases/a'; folder.mkdir(parents=True)
            (folder / 'minus-drums-btc.json').write_text('{}')
            with self.assertRaises(ValueError):
                control.require_unexposed(pack)

    def test_attempt_packet_also_prevents_retroactive_freeze(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary); (pack / 'btc-attempt.json').write_text('{}')
            with self.assertRaises(ValueError):
                control.require_unexposed(pack)

    def test_control_failures_remain_requested_in_same_aggregation(self):
        rows = [{'reference_kind': kind, 'condition': control.CONDITION, 'status': 'error'}
                for kind in control.separation.KINDS]
        result = control.summarize_controls(rows)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r['failed_cases'] == 1 and r['scored_audio_coverage'] == 0
                            and r['condition'] == control.CONDITION for r in result))

    @unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('julius'),
                         'Requires pinned Demucs/Torch/Julius environment')
    def test_actual_roundtrip_preserves_extent_and_impulse_time_origin(self):
        samples = np.zeros(22050, dtype=np.float32); samples[11025] = 1
        result = control.roundtrip(samples, 22050)
        self.assertEqual((len(result), result.dtype), (len(samples), samples.dtype))
        self.assertEqual(int(np.argmax(np.abs(result))), 11025)
        self.assertTrue(np.isfinite(result).all())


if __name__ == '__main__':
    unittest.main()
