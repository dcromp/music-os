import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "candidates"))
import chordino_adapter as adapter


def native(events):
    header = {"final_N_is_termination_marker": True}
    return "#" + json.dumps(header) + "\n" + "\n".join(f"{t}\t{label}" for t, label in events)


class ChordinoAdapterTests(unittest.TestCase):
    def test_terminal_marker_is_removed_but_real_silence_remains(self):
        events, _ = adapter.intervals_from_native(native([
            (0, "N"), (0.5, "C"), (2, "N"), (3, "Dm"), (3.9, "N")]), 4)
        self.assertEqual([e["label"] for e in events], ["N", "C", "N", "Dm"])
        self.assertEqual(events[-1]["end_seconds"], 4)
        self.assertEqual(events[2]["end_seconds"], 3)

    def test_repeated_first_label_does_not_create_zero_duration_event(self):
        events, _ = adapter.intervals_from_native(native([
            (-0.1, "C"), (0, "C"), (0.1, "C"), (2, "G7"), (3.9, "N")]), 4)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["start_seconds"], 0)
        self.assertEqual(events[0]["end_seconds"], 2)

    def test_uncovered_initial_range_is_not_invented_harmony(self):
        events, _ = adapter.intervals_from_native(native([(0.2, "C"), (3.9, "N")]), 4)
        self.assertEqual(events[0]["label"], "X")
        self.assertEqual(events[0]["end_seconds"], 0.2)

    def test_missing_sentinel_and_invalid_timing_fail(self):
        for events in ([(0, "C"), (3.9, "G")], [(1, "C"), (0, "G"), (3.9, "N")],
                       [(float("nan"), "C"), (3.9, "N")]):
            with self.assertRaises(ValueError):
                adapter.intervals_from_native(native(events), 4)


if __name__ == "__main__":
    unittest.main()
