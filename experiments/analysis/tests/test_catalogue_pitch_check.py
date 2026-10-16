"""Source-palette diagnostics keep pitch evidence, setup and truth separate."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_pitch_check as diagnostic
import test_curation as curation_fixtures


def vector(pitches):
    value = np.zeros(12)
    value[list(pitches)] = 1.0 / np.sqrt(len(pitches))
    return value


def feature_packet(times, vectors, silent=None):
    return {"times": np.asarray(times, dtype=float), "chroma": np.asarray(vectors, dtype=float),
            "silent": np.asarray(silent if silent is not None else [False] * len(times), dtype=bool),
            "parameters": {"fixture": "declared symbolic vectors; no acoustic extraction"}}


def chart(events, duration=10.0):
    return {"schema_version": "1.0", "recording": {"id": "test", "title": "Ledger fixture", "duration_seconds": duration, "sample_rate_hz": 22050},
            "analysis": {"id": "fixture", "algorithm": "declared-test", "version": "1", "runtime_seconds": 0, "parameters": {}},
            "chords": [{"start_seconds": first, "end_seconds": last, "label": label} for first, last, label in events]}


class CataloguePitchCheckTests(unittest.TestCase):
    @contextmanager
    def workspace(self):
        with curation_fixtures.CurationTests().pack() as values:
            root, source, pack, manifest, primary, secondary = values
            spec = root / "palette-spec.json"
            diagnostic.drafts.write_json(spec, {"schema_version": "catalogue-starter-palette-spec-1.0", "policy": diagnostic.POLICY,
                "pack_manifest_sha256": diagnostic.drafts.digest(pack / "manifest.json"), "case_ids": ["song"],
                "review_sha256": {"song": diagnostic.drafts.digest(pack / "cases/song/review.json")}})
            yield root, source, pack, spec, manifest

    @contextmanager
    def symbolic_run(self, case, callback=None):
        features = feature_packet([0, 4, 8], [vector([0, 4, 7])] * 3)
        def extract(audio, identifier):
            if callback: callback()
            return {"recording": copy.deepcopy(case["recording"]), "fixture": "synthetic extraction stub"}
        with patch.object(diagnostic.nnls, "extract", side_effect=extract), \
             patch.object(diagnostic.nnls, "validate_evidence"), \
             patch.object(diagnostic, "features_from_nnls", return_value=features), \
             patch.object(diagnostic, "features_from_spectral", return_value=features):
            yield

    def test_c_first_and_positive_transposition_raise_pitch_not_relabel_audio(self):
        expected = vector([2, 6, 9])  # C major raised two semitones is D/F#/A.
        np.testing.assert_allclose(diagnostic.palette_templates(["C"], 2)[0], expected)
        np.testing.assert_allclose(diagnostic.palette_templates(["C"], 11)[0], vector([11, 3, 6]))
        result = diagnostic.score_window(feature_packet([0], [expected]), ["C"], 1)
        self.assertEqual(result["best_shifts_semitones"], [2])
        self.assertAlmostEqual(result["shift_ranking"][0]["mean_nearest_palette_cosine"], 1)
        self.assertAlmostEqual(result["proposed_zero_shift_cosine"], 0)

    def test_multiple_chords_distinguish_a_uniform_shift_and_keep_all_candidates(self):
        # Source C/D/G shifted up two becomes D/E/A; independently declared vectors.
        features = feature_packet([0, 2, 4], [vector([2, 6, 9]), vector([4, 8, 11]), vector([1, 4, 9])])
        result = diagnostic.score_window(features, ["C", "D", "G"], 6)
        self.assertEqual(result["best_shifts_semitones"], [2])
        self.assertEqual({row["shift_semitones"] for row in result["shift_ranking"]}, set(range(12)))
        self.assertGreater(result["best_minus_next_distinct_score"], 0)

    def test_uniform_pitch_class_evidence_preserves_all_shift_ties(self):
        result = diagnostic.score_window(feature_packet([0], [vector(range(12))]), ["C", "G"], 1)
        self.assertEqual(result["best_shifts_semitones"], list(range(12)))
        self.assertIsNone(result["best_minus_next_distinct_score"])
        self.assertNotIn("confidence", result)

    def test_silence_and_zero_vectors_return_unscored_ledgers_without_winning_setup(self):
        features = feature_packet([0, 2, 6], [vector([0, 4, 7]), np.zeros(12), np.zeros(12)], [True, False, True])
        result = diagnostic.score_window(features, ["C"], 10)
        self.assertEqual(result["active_evidence_seconds"], 0)
        self.assertEqual(result["silent_seconds"], 7)
        self.assertEqual(result["non_silent_zero_evidence_seconds"], 3)
        self.assertEqual(result["shift_ranking"], [])
        self.assertEqual(result["best_shifts_semitones"], [])
        for key in ("unrestricted_24_triad_cosine", "proposed_zero_shift_cosine", "unrestricted_minus_zero_shift", "best_minus_next_distinct_score"):
            self.assertIsNone(result[key])

    def test_midpoint_cells_partition_exact_duration_and_partial_windows(self):
        starts, ends = diagnostic.frame_cells([0, 2, 6], 10)
        np.testing.assert_array_equal(starts, [0, 1, 4]); np.testing.assert_array_equal(ends, [1, 4, 10])
        features = feature_packet([0, 2, 6], [vector([0, 4, 7]), vector([2, 6, 9]), np.zeros(12)])
        full = diagnostic.score_window(features, ["C"], 10)
        self.assertEqual(full["active_evidence_seconds"], 4)
        self.assertEqual(full["non_silent_zero_evidence_seconds"], 6)
        self.assertAlmostEqual(full["proposed_zero_shift_cosine"], 0.25)
        self.assertAlmostEqual(full["unrestricted_24_triad_cosine"], 1)
        self.assertAlmostEqual(full["unrestricted_minus_zero_shift"], 0.75)
        partial = diagnostic.score_window(features, ["C"], 10, .5, 3)
        self.assertEqual(partial["audio_seconds"], 2.5)
        self.assertEqual(partial["active_evidence_seconds"], 2.5)
        self.assertAlmostEqual(partial["proposed_zero_shift_cosine"], .2)
        self.assertEqual(sum(partial[k] for k in ("active_evidence_seconds", "silent_seconds", "non_silent_zero_evidence_seconds")), 2.5)

    def test_disjoint_windows_recombine_the_full_weighted_score_and_time_ledger(self):
        features = feature_packet([0, 2, 6], [vector([0, 4, 7]), vector([2, 6, 9]), vector([0, 4, 7])], [False, False, True])
        full = diagnostic.score_window(features, ["C"], 10)
        windows = [diagnostic.score_window(features, ["C"], 10, 0, 2.5), diagnostic.score_window(features, ["C"], 10, 2.5, 10)]
        for key in ("audio_seconds", "active_evidence_seconds", "silent_seconds", "non_silent_zero_evidence_seconds"):
            self.assertAlmostEqual(sum(window[key] for window in windows), full[key])
        numerator = sum(window["active_evidence_seconds"] * window["proposed_zero_shift_cosine"] for window in windows)
        self.assertAlmostEqual(numerator / full["active_evidence_seconds"], full["proposed_zero_shift_cosine"])

    def test_bad_frame_order_bounds_norms_and_boolean_masks_reject(self):
        for times in ([], [-1], [10], [0, 0], [1, 0], [float("nan")]):
            with self.subTest(times=times), self.assertRaises(ValueError): diagnostic.frame_cells(times, 10)
        base = feature_packet([0], [vector([0, 4, 7])])
        for field, value in (("chroma", [[1] * 12]), ("chroma", [[float("nan")] * 12]), ("chroma", [[-1] * 12]), ("silent", [0])):
            changed = {**base, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError): diagnostic.score_window(changed, ["C"], 10)
        for first, last in ((-1, 2), (2, 2), (2, 11), (True, 2)):
            with self.subTest(window=(first, last)), self.assertRaises(ValueError): diagnostic.score_window(base, ["C"], 10, first, last)

    def test_nonharmonic_duplicate_and_invalid_palettes_reject(self):
        for shapes in ([], ["C", "C"], ["N"], ["X"], ["C", 2], ["Cunsupported"]):
            with self.subTest(shapes=shapes), self.assertRaises(ValueError): diagnostic.palette_templates(shapes)
        for shift in (-1, 12, True, 1.5):
            with self.subTest(shift=shift), self.assertRaises(ValueError): diagnostic.palette_templates(["C"], shift)

    def test_model_family_ledger_preserves_suspensions_unknowns_gaps_and_reduction_counts(self):
        value = chart([(0, 1, "Cadd9/E"), (1, 2, "Am7/G"), (2, 3, "A7sus4"), (3, 4, "N"), (4, 5, "X"), (5, 6, "Cbizarre")])
        before = copy.deepcopy(value)
        result = diagnostic.model_palette(value, ["C", "Am", "A"])
        ledger = result["ledger"]
        self.assertEqual({key: ledger[key] for key in ("in_palette_seconds", "outside_palette_seconds", "no_chord_seconds", "unknown_seconds", "unsupported_seconds", "uncovered_seconds")},
                         {"in_palette_seconds": 2, "outside_palette_seconds": 1, "no_chord_seconds": 1, "unknown_seconds": 1, "unsupported_seconds": 1, "uncovered_seconds": 4})
        self.assertEqual(ledger["extension_reduced_seconds"], 3)
        self.assertEqual(ledger["explicit_slash_bass_seconds"], 2)
        self.assertAlmostEqual(result["fraction_of_harmonic_families_in_palette"], 2 / 3)
        self.assertEqual(result["outside_examples"][0]["label"], "A7sus4")
        self.assertNotIn("accuracy", result); self.assertEqual(value, before)

    def test_enharmonic_roots_and_explicit_shift_work_without_claiming_capo(self):
        result = diagnostic.model_palette(chart([(0, 10, "Db")]), ["C#"])
        self.assertEqual(result["fraction_of_harmonic_families_in_palette"], 1)
        shifted = diagnostic.model_palette(chart([(0, 10, "D")]), ["C"], shift=2)
        self.assertEqual(shifted["fraction_of_harmonic_families_in_palette"], 1)
        self.assertNotIn("capo", shifted)

    def test_no_harmonic_prediction_time_cannot_earn_family_credit(self):
        result = diagnostic.model_palette(chart([(0, 3, "N"), (3, 6, "X"), (6, 10, "Cunknown")]), ["C"])
        self.assertEqual(result["harmonic_family_seconds"], 0)
        self.assertIsNone(result["fraction_of_harmonic_families_in_palette"])

    def test_cue_audit_keeps_unsupported_rich_template_instead_of_aborting_or_coercing(self):
        value = chart([(0, 10, "C6")])
        membership = diagnostic.model_palette(value, ["C"])
        features = feature_packet([0], [vector([0, 4, 7])])
        result = diagnostic.cue_diagnostics(value, membership, {"fixture": features}, ["C"])
        cue = result["cues"][0]
        self.assertEqual(cue["native_event"]["label"], "C6")
        acoustic = cue["acoustic_comparison"]["fixture"]
        self.assertIsNone(acoustic["raw_label_cosine"])
        self.assertIsNone(acoustic["source_minus_raw_cosine"])
        self.assertAlmostEqual(acoustic["source_palette_zero_shift_cosine"], 1)
        self.assertIn("native quality retained", acoustic["raw_template_status"])

    def test_tiny_out_of_recording_prediction_cannot_create_negative_uncovered_time(self):
        with self.assertRaises(ValueError): diagnostic.model_palette(chart([(0, 10.0005, "C")]), ["C"])

    def test_preflight_pins_exact_pack_source_context_and_existing_private_bytes(self):
        with self.workspace() as (root, source, pack, spec, manifest):
            private = pack / "private-drafts/song.json"; private.parent.mkdir(); private.write_text('{"private":"existing snapshot"}\n')
            before = {path: path.read_bytes() for path in (pack / "manifest.json", pack / "cases/song/review.json", private, spec)}
            _, _, jobs, originals = diagnostic.preflight(pack, spec, root / "output", root)
            self.assertEqual(len(jobs), 1); self.assertEqual(originals[private.resolve()], diagnostic.drafts.digest(private))
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse((root / "output").exists())

    def test_preflight_rejects_changed_source_notes_even_when_recording_identity_still_matches(self):
        with self.workspace() as (root, source, pack, spec, manifest):
            path = pack / "cases/song/review.json"; review = diagnostic.curation.read(path)
            review["source_context"]["setup"]["capo"] = 2; diagnostic.drafts.write_json(path, review)
            with self.assertRaisesRegex(ValueError, "Source context"):
                diagnostic.preflight(pack, spec, root / "output", root)
            self.assertFalse((root / "output").exists())

    def test_changed_native_audio_or_chart_cannot_enter_palette_diagnostic(self):
        for filename in ("audio.wav", "primary.json", "crema.json"):
            with self.subTest(filename=filename), self.workspace() as (root, source, pack, spec, manifest):
                path = pack / "cases/song" / filename
                if filename == "audio.wav":
                    data = bytearray(path.read_bytes()); data[-1] = 1; path.write_bytes(data)
                else:
                    value = diagnostic.curation.read(path); value["chords"][0]["label"] = "D"; diagnostic.drafts.write_json(path, value)
                with self.assertRaises(ValueError): diagnostic.preflight(pack, spec, root / "output", root)
                self.assertFalse((root / "output").exists())

    def test_preflight_rejects_changed_pack_policy_missing_pins_and_unlisted_recordings(self):
        for fault in ("pack", "policy", "missing-pin", "duplicate", "missing-case"):
            with self.subTest(fault=fault), self.workspace() as (root, source, pack, spec, manifest):
                config = diagnostic.curation.read(spec)
                if fault == "pack": config["pack_manifest_sha256"] = "f" * 64
                elif fault == "policy": config["policy"]["acceptance_threshold"] = .8
                elif fault == "missing-pin": config["review_sha256"] = {}
                elif fault == "duplicate": config["case_ids"] = ["song", "song"]
                else: config["case_ids"] = ["absent"]; config["review_sha256"] = {"absent": "f" * 64}
                diagnostic.drafts.write_json(spec, config)
                with self.assertRaises(ValueError): diagnostic.preflight(pack, spec, root / "output", root)

    def test_output_guards_reject_existing_paths_source_ancestry_and_aliases(self):
        with self.workspace() as (root, source, pack, spec, manifest):
            existing = root / "existing"; existing.mkdir()
            for output in (existing, pack / "nested", root):
                with self.subTest(output=output), self.assertRaises(ValueError): diagnostic.preflight(pack, spec, output, root)
            alias = root / "alias"; alias.symlink_to(pack, target_is_directory=True)
            with self.assertRaises(ValueError): diagnostic.preflight(pack, spec, alias / "nested", root)
            private = pack / "private-drafts"; private.symlink_to(source, target_is_directory=True)
            with self.assertRaises(ValueError): diagnostic.preflight(pack, spec, root / "output", root)

    def test_run_retains_raw_and_private_bytes_and_reports_no_accuracy_or_setup_acceptance(self):
        with self.workspace() as (root, source, pack, spec, manifest):
            private = pack / "private-drafts/song.json"; private.parent.mkdir(); private.write_text('{"private":"retained"}\n')
            sources = [pack / "manifest.json", pack / "cases/song/audio.wav", pack / "cases/song/primary.json", pack / "cases/song/crema.json", private, spec]
            before = {path: path.read_bytes() for path in sources}
            with self.symbolic_run(manifest["cases"][0]): report = diagnostic.run(pack, spec, root / "output", root)
            self.assertFalse(report["gold"]); self.assertIsNone(report["human_correction_seconds"])
            self.assertFalse(report["raw_inputs_modified"]); self.assertFalse(report["private_drafts_modified"])
            self.assertIsNone(report["policy"]["acceptance_threshold"])
            case = report["cases"][0]
            self.assertFalse(case["exact_setup_verified"]); self.assertFalse(case["accepted_arrangement"]); self.assertIsNone(case["accuracy_score"])
            self.assertEqual(case["source_setup"]["capo"], None)
            self.assertEqual({path: path.read_bytes() for path in sources}, before)

    def test_concurrent_private_create_edit_or_delete_aborts_without_replacing_inputs(self):
        for action in ("create", "edit", "delete"):
            with self.subTest(action=action), self.workspace() as (root, source, pack, spec, manifest):
                private = pack / "private-drafts/song.json"; private.parent.mkdir()
                if action != "create": private.write_text('{"private":"before"}\n')
                originals = {name: (pack / "cases/song" / name).read_bytes() for name in ("audio.wav", "primary.json", "crema.json")}
                def change():
                    if action == "delete": private.unlink()
                    else: private.write_text('{"private":"concurrent save"}\n')
                output = root / "output"
                with self.symbolic_run(manifest["cases"][0], change), self.assertRaisesRegex(ValueError, "saved private drafts changed"):
                    diagnostic.run(pack, spec, output, root)
                self.assertFalse(output.exists()); self.assertFalse(list(root.glob(".palette-*")))
                self.assertEqual({name: (pack / "cases/song" / name).read_bytes() for name in originals}, originals)
                if action != "delete": self.assertEqual(private.read_text(), '{"private":"concurrent save"}\n')


if __name__ == "__main__": unittest.main()
