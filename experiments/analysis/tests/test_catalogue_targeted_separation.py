"""Paired acoustic support stays explicit; no separator inference in these tests."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_targeted_separation as targeted


def vector(pitches):
    values = np.zeros(12)
    values[list(pitches)] = 1 / np.sqrt(len(pitches))
    return values


def features(vectors, silent=None, times=(0, 2, 6)):
    return {"times": np.asarray(times, dtype=float), "chroma": np.asarray(vectors, dtype=float),
            "silent": np.asarray([False] * len(times) if silent is None else silent, dtype=bool),
            "parameters": {"source": "symbolic fixture"}}


class TargetedSeparationSupportTests(unittest.TestCase):
    def test_pairwise_support_uses_intersection_and_retains_original_inputs(self):
        major, minor = vector([2, 7, 11]), vector([2, 7, 10])
        original = features([major] * 3, [False, True, False])
        condition = features([minor] * 3, [False, False, True])
        original_before, condition_before = copy.deepcopy(original), copy.deepcopy(condition)
        paired_original, paired_condition = targeted.paired_support(original, condition)
        np.testing.assert_array_equal(paired_original["silent"], [False, True, True])
        np.testing.assert_array_equal(paired_condition["silent"], [False, True, True])
        for actual, before in ((original, original_before), (condition, condition_before)):
            for key in ("times", "chroma", "silent"): np.testing.assert_array_equal(actual[key], before[key])

    def test_zero_evidence_is_excluded_even_when_the_silence_flag_is_false(self):
        major = vector([2, 7, 11])
        original = features([major, np.zeros(12), major])
        condition = features([major, major, np.zeros(12)])
        paired_original, paired_condition = targeted.paired_support(original, condition)
        np.testing.assert_array_equal(paired_original["silent"], [False, True, True])
        np.testing.assert_array_equal(paired_condition["silent"], [False, True, True])
        self.assertEqual(targeted.chord_comparison(paired_original, 10, 0, 10)["active_evidence_seconds"], 1)
        self.assertEqual(targeted.chord_comparison(paired_condition, 10, 0, 10)["active_evidence_seconds"], 1)

    def test_own_and_matched_denominators_expose_discarded_active_time(self):
        major, minor = vector([2, 7, 11]), vector([2, 7, 10])
        original = features([major] * 3, [False, True, False])
        condition = features([minor] * 3, [False, False, True])
        paired_original, paired_condition = targeted.paired_support(original, condition)
        own_original = targeted.chord_comparison(original, 10, 0, 10)
        own_condition = targeted.chord_comparison(condition, 10, 0, 10)
        matched_original = targeted.chord_comparison(paired_original, 10, 0, 10)
        matched_condition = targeted.chord_comparison(paired_condition, 10, 0, 10)
        self.assertEqual(own_original["active_evidence_seconds"], 7)
        self.assertEqual(own_condition["active_evidence_seconds"], 4)
        self.assertEqual(matched_original["active_evidence_seconds"], 1)
        self.assertEqual(matched_condition["active_evidence_seconds"], 1)
        self.assertEqual(own_original["active_evidence_seconds"] - matched_original["active_evidence_seconds"], 6)
        self.assertEqual(own_condition["active_evidence_seconds"] - matched_condition["active_evidence_seconds"], 3)

    def test_partial_cue_windows_share_exact_weighted_support_not_frame_counts(self):
        major = vector([2, 7, 11])
        original = features([major] * 3)
        condition = features([major, np.zeros(12), np.zeros(12)])
        paired_original, paired_condition = targeted.paired_support(original, condition)
        for packet in (paired_original, paired_condition):
            # Midpoint cell for the first frame ends at1s; its overlap is0.5s.
            result = targeted.chord_comparison(packet, 10, .5, 3)
            self.assertEqual(result["active_evidence_seconds"], .5)
            self.assertAlmostEqual(result["G_cosine"], 1)

    def test_zero_matched_support_returns_null_scores_instead_of_a_winning_chord(self):
        major = vector([2, 7, 11])
        original = features([major] * 3)
        condition = features([np.zeros(12)] * 3)
        paired_original, paired_condition = targeted.paired_support(original, condition)
        for packet in (paired_original, paired_condition):
            result = targeted.chord_comparison(packet, 10, 0, 10)
            self.assertEqual(result["active_evidence_seconds"], 0)
            for key in ("G_cosine", "Gm_cosine", "G_minus_Gm_cosine"): self.assertIsNone(result[key])
            self.assertNotIn("accuracy", result)

    def test_identical_frame_counts_with_different_centers_cannot_be_paired(self):
        major = vector([2, 7, 11])
        original = features([major] * 3)
        for times in ((0, 2, 6.000000000001), (.1, 2.1, 6.1), (0, 6, 2), (0, 2)):
            condition = features([major] * len(times), times=times)
            with self.subTest(times=times), self.assertRaises(ValueError): targeted.paired_support(original, condition)

    def test_direct_major_minor_sign_is_not_the_best_whole_palette_score(self):
        major = targeted.chord_comparison(features([vector([2, 7, 11])] * 3), 10, 0, 10)
        minor = targeted.chord_comparison(features([vector([2, 7, 10])] * 3), 10, 0, 10)
        self.assertAlmostEqual(major["G_cosine"], 1)
        self.assertAlmostEqual(major["Gm_cosine"], 2 / 3)
        self.assertAlmostEqual(major["G_minus_Gm_cosine"], 1 / 3)
        self.assertAlmostEqual(minor["G_cosine"], 2 / 3)
        self.assertAlmostEqual(minor["Gm_cosine"], 1)
        self.assertAlmostEqual(minor["G_minus_Gm_cosine"], -1 / 3)
        self.assertNotIn("accepted_arrangement", major)
        self.assertNotIn("confidence", major)

    def test_pairing_a_condition_to_itself_preserves_its_own_eligible_denominator(self):
        major = vector([2, 7, 11])
        original = features([major, np.zeros(12), major], [False, False, True])
        left, right = targeted.paired_support(original, original)
        own = targeted.chord_comparison(original, 10, 0, 10)
        self.assertEqual(targeted.chord_comparison(left, 10, 0, 10), own)
        self.assertEqual(targeted.chord_comparison(right, 10, 0, 10), own)


if __name__ == "__main__": unittest.main()
