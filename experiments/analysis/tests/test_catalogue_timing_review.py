"""Timing review keeps concordance, acoustic context and physical truth separate."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_timing_review as review


def chart(events, duration=10.0):
    return {"schema_version": "1.0", "recording": {"id": "declared-fixture", "title": "Declared fixture",
            "duration_seconds": duration, "sample_rate_hz": 22050, "audio_sha256": "a" * 64},
            "analysis": {"id": "declared", "algorithm": "symbolic-fixture", "version": "1",
                         "runtime_seconds": 0, "parameters": {}},
            "chords": [{"start_seconds": start, "end_seconds": end, "label": label}
                       for start, end, label in events]}


def boundary(time, source="C", target="G"):
    return {"time_seconds": time, "from_key": review.key_for(source), "to_key": review.key_for(target)}


def features(pitches=(2, 7, 11), silent=False):
    # Independently declared G-major notes by default, without extraction.
    vector = np.zeros(12); vector[list(pitches)] = 1 / np.sqrt(len(pitches))
    return {"times": np.asarray([0, 2, 6], dtype=float), "chroma": np.asarray([vector] * 3),
            "silent": np.asarray([silent] * 3, dtype=bool), "parameters": {"fixture": "declared notes"}}


class CatalogueTimingReviewTests(unittest.TestCase):
    @contextmanager
    def small_run(self):
        """Mock extraction/preflight, retaining the real frozen-input guard."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); pack = root / "pack"; folder = pack / "cases/declared-fixture"
            evidence_root = root / "evidence"; evidence_folder = evidence_root / "declared-fixture"
            folder.mkdir(parents=True); evidence_folder.mkdir(parents=True)
            primary = chart([(0, 4, "C"), (4, 10, "G")]); secondary = copy.deepcopy(primary)
            secondary["chords"][0]["end_seconds"] = 4.2; secondary["chords"][1]["start_seconds"] = 4.2
            case = {"id": "declared-fixture", "name": "Declared fixture", "recording": primary["recording"], "artifacts": {}}
            write = review.drafts.write_json; digest = review.drafts.digest
            write(pack / "manifest.json", {"cases": [case]})
            for filename, value in (("primary.json", primary), ("crema.json", secondary)):
                write(folder / filename, value)
            (folder / "audio.wav").write_bytes(b"mock preflight fixture: not acoustic evidence")
            coverage = [{"id": str(i), "kind": "coverage-sample", "start_seconds": float(i * 2), "end_seconds": float(i * 2 + 1)} for i in range(4)]
            write(folder / "review.json", {"points": coverage})
            private = pack / "private-drafts/declared-fixture.json"; private.parent.mkdir(); write(private, {"private": "retained"})
            pitch_spec = root / "pitch-spec.json"; write(pitch_spec, {"fixture": "mock preflight"})
            evidence_path = evidence_folder / "nnls-evidence.json"; write(evidence_path, {"recording": primary["recording"]})
            write(evidence_root / "report.json", {"schema_version": review.pitch.SCHEMA,
                  "pack_manifest_sha256": digest(pack / "manifest.json"), "spec_sha256": digest(pitch_spec),
                  "module_sha256": digest(Path(review.pitch.__file__)), "policy": review.pitch.POLICY,
                  "cases": [{**case, "nnls_evidence_sha256": digest(evidence_path)}]})
            profile = {"hold_rules": [{"label": "C", "minimum_seconds": 2, "purpose": "declared review target"}],
                       "acoustic_labels": ["C", "G"], "response_labels": []}
            spec = root / "spec.json"; write(spec, {"schema_version": "catalogue-timing-review-spec-1.0",
                  "policy": review.POLICY, "pitch_spec_sha256": digest(pitch_spec),
                  "evidence_report_sha256": digest(evidence_root / "report.json"), "profiles": {case["id"]: profile}})
            pinned = [pack / "manifest.json", pitch_spec, private] + list(folder.iterdir())
            originals = {path: digest(path) for path in pinned}
            with patch.object(review.pitch, "preflight", return_value=({"cases": [case]}, {}, [(case, folder, {})], originals)), \
                 patch.object(review.pitch.nnls, "validate_evidence"), \
                 patch.object(review.pitch.nnls, "extract", side_effect=AssertionError("Saved-evidence review must not extract")), \
                 patch.object(review.pitch, "features_from_nnls", return_value=features()):
                yield {"root": root, "pack": pack, "pitch_spec": pitch_spec, "evidence_root": evidence_root,
                       "spec": spec, "output": root / "output", "folder": folder, "private": private,
                       "evidence_path": evidence_path, "pinned": pinned + [spec, evidence_path, evidence_root / "report.json"]}

    def run_small(self, paths):
        return review.run(paths["pack"], paths["pitch_spec"], paths["evidence_root"], paths["spec"], paths["output"], paths["root"])

    def test_maximum_match_count_precedes_nearest_boundary_choice(self):
        # Nearest-first picks 1->1.1, stranding 1.4. The monotone two-pair
        # solution is 1->.6 and 1.4->1.1, despite its larger first error.
        first = [boundary(1), boundary(1.4)]
        second = [boundary(.6), boundary(1.1)]
        pairs = review.match_transitions(first, second, .5)
        self.assertEqual([(i, j) for i, j, _ in pairs], [(0, 0), (1, 1)])
        self.assertAlmostEqual(sum(error for _, _, error in pairs), .7)

    def test_equal_count_chooses_minimum_total_error_across_the_full_path(self):
        first = [boundary(1), boundary(3)]
        second = [boundary(.6), boundary(1.1), boundary(2.9)]
        pairs = review.match_transitions(first, second, .5)
        self.assertEqual([(i, j) for i, j, _ in pairs], [(0, 1), (1, 2)])
        self.assertAlmostEqual(sum(error for _, _, error in pairs), .2)

    def test_pairing_cannot_cross_time_order_even_when_labels_allow_two_pairs(self):
        first = [boundary(1, "C", "G"), boundary(2, "G", "Am")]
        second = [boundary(1, "G", "Am"), boundary(2, "C", "G")]
        pairs = review.match_transitions(first, second, 2)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(first[pairs[0][0]]["from_key"], second[pairs[0][1]]["from_key"])

    def test_reverse_direction_and_other_target_remain_unmatched(self):
        first = [boundary(1, "C", "G")]
        for second in ([boundary(1, "G", "C")], [boundary(1, "C", "Am")]):
            with self.subTest(second=second): self.assertEqual(review.match_transitions(first, second), [])

    def test_pairing_tolerance_is_inclusive_and_empty_sides_are_valid(self):
        self.assertEqual(review.match_transitions([boundary(1)], [boundary(1.5)], .5), [(0, 0, .5)])
        self.assertEqual(review.match_transitions([boundary(1)], [boundary(1.500001)], .5), [])
        for first, second in (([], []), ([boundary(1)], []), ([], [boundary(1)])):
            self.assertEqual(review.match_transitions(first, second), [])

    def test_bad_pair_times_tolerances_and_unbounded_work_are_rejected(self):
        for values in ([boundary(-1)], [boundary(float("nan"))], [boundary(True)],
                       [boundary(1), boundary(1)], [boundary(2), boundary(1)]):
            with self.subTest(values=values), self.assertRaises(ValueError): review.match_transitions(values, [])
        for tolerance in (-1, True, float("nan"), float("inf")):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError): review.match_transitions([], [], tolerance)
        with patch.dict(review.POLICY, {"max_pair_cells": 3}), self.assertRaises(ValueError):
            review.match_transitions([boundary(1)], [boundary(1)])

    def test_contiguous_am_sevenths_merge_without_mutating_native_labels(self):
        original = chart([(0, 1, "Am"), (1, 2, "Am7"), (2, 3, "Am7/G"), (3, 10, "C")])
        before = copy.deepcopy(original); timeline = review.core_timeline(original)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["start_seconds"], 0)
        self.assertEqual(timeline[0]["end_seconds"], 3)
        self.assertEqual(timeline[0]["source_labels"], ["Am", "Am7", "Am7/G"])
        self.assertEqual(timeline[0]["key"], review.key_for("Am"))
        self.assertEqual(original, before)

    def test_n_x_and_gaps_never_join_same_harmony_into_a_hold(self):
        original = chart([(0, 1, "Am"), (1, 2, "N"), (2, 3, "Am"), (3, 4, "X"),
                          (4, 5, "Am"), (6, 10, "Am7")])
        timeline = review.core_timeline(original); boundaries, gaps = review.transitions(original)
        self.assertEqual([(row["start_seconds"], row["end_seconds"]) for row in timeline if row["key"] == review.key_for("Am")],
                         [(0, 1), (2, 3), (4, 5), (6, 10)])
        self.assertEqual(gaps, [{"start_seconds": 5, "end_seconds": 6}])
        self.assertEqual(len(boundaries), 4)
        self.assertTrue(all(not row["harmonic"] for row in boundaries))

    def test_leading_and_trailing_uncovered_time_are_retained_as_gap_cues(self):
        original = chart([(1, 3, "C"), (3, 9, "G")])
        boundaries, gaps = review.transitions(original)
        self.assertEqual([row["time_seconds"] for row in boundaries], [3])
        self.assertEqual(gaps, [{"start_seconds": 0.0, "end_seconds": 1},
                                {"start_seconds": 9, "end_seconds": 10.0}])
        result = review.boundary_review(original, copy.deepcopy(original))
        self.assertEqual(sum(row["kind"].endswith("coverage-gap") for row in result["all_review_windows"]), 4)

    def test_suspensions_remain_distinct_from_major_and_minor_thirds(self):
        original = chart([(0, 2, "A7sus4"), (2, 4, "Asus4"), (4, 6, "A"), (6, 10, "Am")])
        timeline = review.core_timeline(original)
        self.assertEqual([row["key"] for row in timeline], [review.key_for("Asus4"), review.key_for("A"), review.key_for("Am")])
        self.assertEqual([row["time_seconds"] for row in review.transitions(original)[0]], [4, 6])

    def test_even_tiny_out_of_audio_span_and_wrong_recording_cannot_enter_review(self):
        with self.assertRaises(ValueError): review.core_timeline(chart([(0, 10.0001, "C")]))
        original = chart([(0, 5, "C"), (5, 10, "G")]); other = copy.deepcopy(original)
        other["recording"]["audio_sha256"] = "b" * 64
        with self.assertRaises(ValueError): review.boundary_review(original, other)

    def test_wrong_direction_produces_both_unpaired_review_cues(self):
        original = chart([(0, 4, "C"), (4, 10, "G")]); other = chart([(0, 4, "G"), (4, 10, "C")])
        result = review.boundary_review(original, other)
        self.assertEqual(result["paired_boundaries"], 0)
        self.assertIsNone(result["median_pair_difference_seconds"])
        self.assertEqual({row["kind"] for row in result["all_review_windows"]}, {"unpaired-primary", "unpaired-secondary"})
        self.assertNotIn("accuracy", result)

    def test_hold_inventory_merges_harmony_but_never_counts_attacks_or_bars(self):
        original = chart([(0, 2, "Am"), (2, 3, "Am7"), (3, 6, "C"), (6, 10, "Am")])
        profile = {"hold_rules": [{"label": "Am", "minimum_seconds": 3, "purpose": "review held response"}],
                   "acoustic_labels": ["Am", "C"], "response_labels": ["Am"]}
        with patch.object(review.pitch, "features_from_nnls", return_value=features()):
            result = review.contrast_inventory(original, copy.deepcopy(original), profile, {"recording": original["recording"]})
        self.assertEqual([row["span_seconds"] for row in result["candidate_holds"]], [3, 4, 3, 4])
        self.assertEqual(len(result["selected_response_runs"]["btc"]), 2)
        self.assertTrue(all(not row["accepted_section"] for row in result["candidate_holds"]))
        for row in result["candidate_holds"]:
            self.assertEqual(row["other_model_same_core_seconds"], row["span_seconds"])
            self.assertFalse(any("attack" in key or "bar" in key or "repeat" in key for key in row))

    def test_acoustic_context_favouring_g_never_relabels_native_g_minor(self):
        original = chart([(0, 10, "Gm")]); other = copy.deepcopy(original); before = copy.deepcopy(original)
        profile = {"hold_rules": [{"label": "Gm", "minimum_seconds": 2, "purpose": "unresolved native hold"}],
                   "acoustic_labels": ["G", "Gm"], "response_labels": ["Gm"]}
        with patch.object(review.pitch, "features_from_nnls", return_value=features()):
            result = review.contrast_inventory(original, other, profile, {"recording": original["recording"]})
        for row in result["candidate_holds"]:
            self.assertGreater(row["nnls_cosine_by_label"]["G"], row["nnls_cosine_by_label"]["Gm"])
            self.assertEqual(row["native_span"]["source_labels"], ["Gm"])
            self.assertEqual(row["native_span"]["key"], review.key_for("Gm"))
            self.assertFalse(row["accepted_section"])
        self.assertEqual(original, before); self.assertEqual(other, before)

    def test_silent_contrast_keeps_native_hold_and_null_acoustic_scores(self):
        original = chart([(0, 10, "C")])
        profile = {"hold_rules": [{"label": "C", "minimum_seconds": 2, "purpose": "unresolved native hold"}],
                   "acoustic_labels": ["C", "G"], "response_labels": []}
        with patch.object(review.pitch, "features_from_nnls", return_value=features(silent=True)):
            result = review.contrast_inventory(original, copy.deepcopy(original), profile, {"recording": original["recording"]})
        for row in result["candidate_holds"]:
            self.assertEqual(row["nnls_active_evidence_seconds"], 0)
            self.assertEqual(row["nnls_cosine_by_label"], {"C": None, "G": None})
            self.assertEqual(row["native_span"]["source_labels"], ["C"])

    def test_shared_clock_error_has_perfect_concordance_but_fails_declared_reference(self):
        reference = chart([(0, 2, "C"), (2, 5, "G"), (5, 8, "Am"), (8, 10, "F")])
        # Independently declared physical-change anchors stay at 2, 5 and 8s;
        # both model timelines share a +.30s error in this negative control.
        shifted = chart([(0, 2.30, "C"), (2.30, 5.30, "G"), (5.30, 8.30, "Am"), (8.30, 10, "F")])
        common = review.boundary_review(shifted, copy.deepcopy(shifted))
        self.assertEqual(common["paired_boundaries"], 3)
        self.assertEqual(common["maximum_pair_difference_seconds"], 0)
        self.assertEqual(common["all_review_windows"], [])
        truth, _ = review.transitions(reference); predicted, _ = review.transitions(shifted)
        self.assertEqual(review.match_transitions(truth, predicted, .15), [])
        pairs = review.match_transitions(truth, predicted, .5)
        self.assertEqual(len(pairs), 3)
        self.assertTrue(all(abs(error - .3) < 1e-12 for _, _, error in pairs))
        self.assertNotIn("physical_timing_accuracy", common)

    def test_saved_evidence_run_retains_all_inputs_and_declares_no_acceptance(self):
        with self.small_run() as paths:
            before = {path: path.read_bytes() for path in paths["pinned"]}
            result = self.run_small(paths)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse(result["gold"]); self.assertFalse(result["raw_charts_modified"])
            self.assertFalse(result["private_drafts_modified"])
            self.assertIsNone(result["physical_timing_accuracy"]); self.assertIsNone(result["human_correction_seconds"])
            self.assertEqual(len(result["cases"][0]["fixed_coverage_samples"]), 4)
            self.assertFalse(result["cases"][0]["accepted_arrangement"])

    def test_concurrent_input_or_private_draft_mutation_aborts_without_publishing(self):
        for target in ("spec", "evidence_path", "primary", "private", "new-private", "deleted-private"):
            with self.subTest(target=target), self.small_run() as paths:
                original_contrast = review.contrast_inventory
                def mutate(*args):
                    result = original_contrast(*args)
                    if target == "deleted-private": paths["private"].unlink()
                    else:
                        path = paths["folder"] / "primary.json" if target == "primary" else \
                               paths["private"].with_name("concurrent.json") if target == "new-private" else paths[target]
                        path.write_text('{"concurrent":"retained by guard"}\n')
                    return result
                with patch.object(review, "contrast_inventory", side_effect=mutate), self.assertRaisesRegex(ValueError, "Inputs or saved drafts changed"):
                    self.run_small(paths)
                self.assertFalse(paths["output"].exists())
                self.assertFalse(list(paths["root"].glob(".timing-review-*")))
                if target == "deleted-private": self.assertFalse(paths["private"].exists())
                else:
                    path = paths["folder"] / "primary.json" if target == "primary" else \
                           paths["private"].with_name("concurrent.json") if target == "new-private" else paths[target]
                    self.assertEqual(path.read_text(), '{"concurrent":"retained by guard"}\n')


if __name__ == "__main__": unittest.main()
