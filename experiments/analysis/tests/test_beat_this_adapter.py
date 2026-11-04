from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import beat_this_adapter as adapter


class NativeBeatTests(unittest.TestCase):
    def test_native_times_are_preserved_without_offset_or_snap(self):
        result = adapter.convert_native([.1, .6, 1.1, 1.6], [.1], 2)
        self.assertEqual(result['beat_times_seconds'], [.1, .6, 1.1, 1.6])
        self.assertEqual(result['downbeat_times_seconds'], [.1])
        self.assertEqual(result['pulse_bpm'], 120)

    def test_invalid_pulses_are_rejected_instead_of_sorted_or_trimmed(self):
        for beats in ([.6, .1], [.1, .1], [.1, float('nan')], [.1]):
            with self.assertRaises(ValueError):
                adapter.convert_native(beats, [], 2)

    def test_unvalidated_downbeats_still_need_finite_ordered_coverage(self):
        for downbeats in ([float('nan')], [1., .5]):
            with self.assertRaises(ValueError):
                adapter.convert_native([.1, .6, 1.1], downbeats, 2)

    def test_endpoint_and_outside_events_are_preserved_for_extra_pulse_audit(self):
        result = adapter.convert_native([-.1, .1, .6, 2.], [2.], 2)
        self.assertEqual(result['beat_times_seconds'], [.1, .6])
        self.assertEqual(result['raw_beat_times_seconds'], [-.1, .1, .6, 2.])
        self.assertEqual(result['outside_recording_beat_times_seconds'], [-.1, 2.])
        self.assertEqual(result['outside_recording_downbeat_times_seconds'], [2.])
        self.assertEqual(result['downbeat_times_seconds'], [])


if __name__ == '__main__':
    unittest.main()
