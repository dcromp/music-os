"""Automatic drafts preserve predictions, pair exact audio, and flag heuristics."""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import automatic_drafts as drafts


class AutomaticDraftTests(unittest.TestCase):
    def fixture(self, root):
        case = root / "pilot" / "cases" / "test-song"
        case.mkdir(parents=True)
        audio_path = case / "audio.wav"
        with wave.open(str(audio_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(100)
            audio.writeframes(b"\x00\x00" * 1000)
        record = {"id": "test-song", "title": "Test song", "duration_seconds": 10.0,
                  "sample_rate_hz": 100, "audio_sha256": drafts.digest(audio_path)}
        primary = {"schema_version": "1.0", "recording": record,
                   "analysis": {"id": "crema", "algorithm": "CREMA", "version": "test", "runtime_seconds": 1,
                                "parameters": {"confidence_semantics": "uncalibrated native score"}},
                   "chords": [{"start_seconds": 0, "end_seconds": 4, "label": "C7/E", "native_label": "C:7/3", "confidence": .87},
                              {"start_seconds": 4, "end_seconds": 7, "label": "Am"},
                              {"start_seconds": 7, "end_seconds": 10, "label": "G"}]}
        secondary = copy.deepcopy(primary)
        secondary["analysis"]["id"] = "chordino"
        secondary["analysis"]["algorithm"] = "Chordino"
        secondary["chords"] = [{"start_seconds": 0, "end_seconds": 4.2, "label": "Cmaj7"},
                               {"start_seconds": 4.2, "end_seconds": 7, "label": "A"},
                               {"start_seconds": 7, "end_seconds": 10, "label": "D"}]
        drafts.write_json(case / "crema.json", primary)
        drafts.write_json(case / "chordino.json", secondary)
        manifest = {"cases": [{"id": "test-song", "name": "Test song", "audio": "cases/test-song/audio.wav",
                               "source": {"recording": record}}]}
        drafts.write_json(root / "pilot/manifest.json", manifest)
        return primary, secondary, root / "pilot/manifest.json"

    def selected_fixture(self, root):
        primary, _, manifest = self.fixture(root)
        source = root / "pilot/cases/test-song"
        primary["analysis"]["algorithm"] = "crema-pretrained"
        drafts.write_json(source / "crema.json", primary)
        btc = copy.deepcopy(primary)
        btc["analysis"].update({"id": "btc", "algorithm": "BTC-ISMIR19"})
        btc["chords"][0].update({"label": "C", "native_label": "C"})
        btc_root = root / "btc-results"
        folder = btc_root / "cases/test-song"
        folder.mkdir(parents=True)
        drafts.write_json(folder / "btc.json", btc)
        return manifest, btc_root

    def static_fixture(self, root):
        static = root / "static"
        static.mkdir()
        for name in ("index.html", "app.js", "style.css"):
            (static / name).write_text("fixture")
        return static

    def test_selected_btc_crema_pack_preserves_bytes_identity_and_fixed_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            source = root / "pilot/cases/test-song"
            output = root / "selected-output"
            result = drafts.build(manifest, output, root, primary_model="btc",
                                  secondary_model="crema", primary_root=btc_root)
            target = output / "cases/test-song"
            self.assertEqual((target / "primary.json").read_bytes(), (btc_root / "cases/test-song/btc.json").read_bytes())
            for name in ("audio.wav", "crema.json"):
                self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
            self.assertFalse((target / "chordino.json").exists())
            self.assertEqual(result["model_selection"], {"primary": "btc", "secondary": "crema"})
            case = result["cases"][0]
            self.assertEqual(case["primary_name"], "BTC automatic draft")
            self.assertEqual(case["secondary"], [{"name": "CREMA", "url": "/cases/test-song/crema.json"}])
            self.assertEqual(case["origin"]["source_audio_sha256"], drafts.digest(source / "audio.wav"))
            self.assertEqual(case["artifacts"]["crema_sha256"], drafts.digest(source / "crema.json"))
            self.assertFalse(result["gold"])
            evidence = json.loads((target / "evidence.json").read_text())
            self.assertEqual(evidence["comparison"], {"primary_algorithm": "BTC-ISMIR19", "secondary_algorithm": "crema-pretrained"})
            spec = json.loads((output / "build-spec.json").read_text())
            self.assertEqual((spec["primary"], spec["secondary"], spec["primary_root"]), ("btc.json", "crema.json", "btc-results"))
            static = self.static_fixture(root)
            with patch.object(drafts, "STATIC", static), patch.object(drafts.review_pack, "STATIC", static):
                files = drafts.public_files(output)
                self.assertEqual(files["/cases/test-song/crema.json"], (target / "crema.json").resolve())
                self.assertNotIn("/cases/test-song/chordino.json", files)
                self.assertNotIn("/build-spec.json", files)
            with self.assertRaises(ValueError):
                drafts.build(manifest, output, root, primary_model="btc", secondary_model="crema", primary_root=btc_root)

    def test_selected_models_accept_independent_batch_roots_without_moving_native_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            source = root / "pilot/cases/test-song"
            crema_root = root / "crema-results"
            comparison = crema_root / "cases/test-song/crema.json"
            comparison.parent.mkdir(parents=True)
            comparison.write_bytes((source / "crema.json").read_bytes())
            (source / "crema.json").unlink()
            before = {path: path.read_bytes() for path in (source / "audio.wav", comparison, btc_root / "cases/test-song/btc.json")}
            output = root / "independent-output"
            built = drafts.build(manifest, output, root, primary_model="btc", secondary_model="crema",
                                 primary_root=btc_root, secondary_root=crema_root)
            target = output / "cases/test-song"
            self.assertEqual((target / "crema.json").read_bytes(), before[comparison])
            self.assertEqual((target / "primary.json").read_bytes(), before[btc_root / "cases/test-song/btc.json"])
            self.assertEqual(built["cases"][0]["artifacts"]["crema_sha256"], drafts.digest(comparison))
            spec = json.loads((output / "build-spec.json").read_text())
            self.assertEqual((spec["primary_root"], spec["secondary_root"]), ("btc-results", "crema-results"))
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse((source / "crema.json").exists())

    def test_secondary_batch_root_and_native_chart_cannot_leave_project(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            alias = root / "comparison-alias"
            alias.symlink_to(Path(outside), target_is_directory=True)
            for comparison_root in (Path(outside), alias):
                with self.subTest(root=comparison_root), self.assertRaises(ValueError):
                    drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema",
                                 primary_root=btc_root, secondary_root=comparison_root)
            comparison_root = root / "crema-results"
            comparison = comparison_root / "cases/test-song/crema.json"
            comparison.parent.mkdir(parents=True)
            external = Path(outside) / "crema.json"
            external.write_bytes((root / "pilot/cases/test-song/crema.json").read_bytes())
            comparison.symlink_to(external)
            with self.assertRaises(ValueError):
                drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema",
                             primary_root=btc_root, secondary_root=comparison_root)
            self.assertFalse((root / "bad-output").exists())
            self.assertFalse(list(root.glob(".automatic-playalong-*")))

    def test_explicit_model_selection_rejects_mislabeled_primary_or_comparison(self):
        for model in ("btc", "crema"):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, btc_root = self.selected_fixture(root)
                path = btc_root / "cases/test-song/btc.json" if model == "btc" else root / "pilot/cases/test-song/crema.json"
                chart = json.loads(path.read_text())
                chart["analysis"]["algorithm"] = "different-model"
                drafts.write_json(path, chart)
                with self.assertRaisesRegex(ValueError, "declared model"):
                    drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema", primary_root=btc_root)
                self.assertFalse((root / "bad-output").exists())
                self.assertFalse(list(root.glob(".automatic-playalong-*")))

    def test_selected_model_chart_must_match_exact_source_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            path = btc_root / "cases/test-song/btc.json"
            chart = json.loads(path.read_text())
            chart["recording"]["audio_sha256"] = "f" * 64
            drafts.write_json(path, chart)
            with self.assertRaisesRegex(ValueError, "audio_sha256"):
                drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema", primary_root=btc_root)
            self.assertFalse((root / "bad-output").exists())

    def test_selected_models_and_primary_root_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            for primary, secondary in (("btc", "btc"), ("arbitrary", "crema"), ("btc", "../private"), ("", "crema")):
                with self.subTest(primary=primary, secondary=secondary), self.assertRaises(ValueError):
                    drafts.build(manifest, root / "bad-output", root, primary_model=primary, secondary_model=secondary, primary_root=btc_root)
            for selected_root in (Path(outside), root / "outside-alias"):
                if selected_root.parent == root:
                    selected_root.symlink_to(Path(outside), target_is_directory=True)
                with self.subTest(root=selected_root), self.assertRaises(ValueError):
                    drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema", primary_root=selected_root)
            # A regular in-project batch root cannot hide an external chart either.
            chart = btc_root / "cases/test-song/btc.json"
            external = Path(outside) / "btc.json"
            external.write_bytes(chart.read_bytes())
            chart.unlink()
            chart.symlink_to(external)
            with self.assertRaises(ValueError):
                drafts.build(manifest, root / "bad-output", root, primary_model="btc", secondary_model="crema", primary_root=btc_root)
            self.assertFalse((root / "bad-output").exists())

    def test_selected_comparison_route_cannot_expose_an_arbitrary_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, btc_root = self.selected_fixture(root)
            output = root / "selected-output"
            built = drafts.build(manifest, output, root, primary_model="btc", secondary_model="crema", primary_root=btc_root)
            static = self.static_fixture(root)
            with patch.object(drafts, "STATIC", static), patch.object(drafts.review_pack, "STATIC", static):
                for name, url in (("CREMA", "/cases/test-song/private.json"), ("Chordino", "/cases/test-song/crema.json"), ("CREMA", "/cases/test-song/crema.json?path=private")):
                    modified = copy.deepcopy(built)
                    modified["cases"][0]["secondary"] = [{"name": name, "url": url}]
                    drafts.write_json(output / "manifest.json", modified)
                    with self.subTest(url=url, name=name), self.assertRaises(ValueError):
                        drafts.public_files(output)
                for selection in ({"primary": "btc", "secondary": "arbitrary"}, {"primary": "btc", "secondary": "btc"}, {"primary": [], "secondary": "crema"}, {"primary": "btc", "secondary": "crema", "filename": "private.json"}):
                    modified = copy.deepcopy(built)
                    modified["model_selection"] = selection
                    drafts.write_json(output / "manifest.json", modified)
                    with self.subTest(selection=selection), self.assertRaises(ValueError):
                        drafts.public_files(output)

    def test_roots_enharmonics_inversions_and_unknown_qualities(self):
        for label, expected in (("C7/E", (0, "maj")), ("Db:min7/3", (1, "min")), ("C#m7", (1, "min")),
                                ("Csus4", (0, None)), ("Cdim", (0, None)), ("Caug", (0, None)),
                                ("Cm7b5", (0, None)), ("C5", (0, None)), ("N", ("N", "N")), ("X", (None, None))):
            with self.subTest(label=label):
                self.assertEqual(drafts.label_signature(label), expected)

    def test_duration_agreement_is_not_full_quality_or_correctness(self):
        with tempfile.TemporaryDirectory() as directory:
            p, s, _ = self.fixture(Path(directory))
            result = drafts.compare_charts(p, s)
            self.assertAlmostEqual(result["metrics"]["root_agreement_fraction"], .68)
            self.assertAlmostEqual(result["metrics"]["majmin_agreement_fraction"], .4)
            self.assertEqual(result["metrics"]["boundary_match_fraction"], 1)
            self.assertFalse(result["gold"])
            kinds = {flag["priority_kind"] for flag in result["flags"]}
            self.assertEqual(kinds, {"majmin_disagreement", "root_disagreement"})
            # Both models can share the same wrong label. The utility reports agreement only.
            same = drafts.compare_charts(p, p)
            self.assertEqual(same["metrics"]["majmin_agreement_fraction"], 1)
            self.assertEqual(same["flags"], [])
            self.assertIn("Shared errors", same["semantics"])

    def test_suspended_unknown_and_no_chord_coverage_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            p, s, _ = self.fixture(Path(directory))
            p["chords"] = [{"start_seconds": 0, "end_seconds": 5, "label": "Csus4"},
                           {"start_seconds": 5, "end_seconds": 10, "label": "N"}]
            s["chords"] = [{"start_seconds": 0, "end_seconds": 10, "label": "C"}]
            result = drafts.compare_charts(p, s)
            self.assertEqual(result["metrics"]["root_coverage_fraction"], .5)
            self.assertEqual(result["metrics"]["majmin_coverage_fraction"], 0)
            self.assertIsNone(result["metrics"]["majmin_agreement_fraction"])
            self.assertIn("no_chord_disagreement", {flag["priority_kind"] for flag in result["flags"]})
            p["chords"][0]["label"] = "X"
            self.assertIn("unresolved_label", {flag["priority_kind"] for flag in drafts.compare_charts(p, s)["flags"]})

    def test_short_raw_disagreements_remain_auditable_but_not_review_work(self):
        with tempfile.TemporaryDirectory() as directory:
            p, s, _ = self.fixture(Path(directory))
            s["chords"] = [{"start_seconds": 0, "end_seconds": 3.8, "label": "C"},
                           {"start_seconds": 3.8, "end_seconds": 4, "label": "D"},
                           *copy.deepcopy(p["chords"][1:])]
            result = drafts.compare_charts(p, s)
            self.assertEqual(len(result["raw_label_disagreements"]), 1)
            self.assertFalse(any(flag["priority_kind"] == "root_disagreement" for flag in result["flags"]))
            self.assertIn("boundary_disagreement", {flag["priority_kind"] for flag in result["flags"]})

    def test_boundary_matching_is_one_to_one_and_review_count_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            p, s, _ = self.fixture(Path(directory))
            p["chords"] = [{"start_seconds": i / 10, "end_seconds": (i + 1) / 10, "label": "C" if i % 2 else "G"} for i in range(100)]
            s["chords"] = [{"start_seconds": 0, "end_seconds": 5, "label": "C"}, {"start_seconds": 5, "end_seconds": 10, "label": "G"}]
            result = drafts.compare_charts(p, s)
            self.assertEqual(result["metrics"]["boundary_matches"], 1)
            self.assertLessEqual(len(result["review_points"]), 8)
            self.assertTrue(all(point["end_seconds"] - point["start_seconds"] <= 6 for point in result["review_points"]))

    def test_prediction_pairing_and_full_coverage_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            p, s, _ = self.fixture(Path(directory))
            for field, value in (("id", "different"), ("audio_sha256", "1" * 64), ("duration_seconds", 11), ("sample_rate_hz", 200)):
                bad = copy.deepcopy(s)
                bad["recording"][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    drafts.compare_charts(p, bad)
            bad = copy.deepcopy(s)
            bad["chords"][0]["start_seconds"] = .1
            with self.assertRaises(ValueError):
                drafts.compare_charts(p, bad)

    def test_build_preserves_every_primary_byte_and_exact_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p, _, manifest = self.fixture(root)
            result = drafts.build(manifest, root / "output", root)
            case = result["cases"][0]
            source = root / "pilot/cases/test-song"
            target = root / "output/cases/test-song"
            self.assertEqual((target / "primary.json").read_bytes(), (source / "crema.json").read_bytes())
            self.assertEqual((target / "audio.wav").read_bytes(), (source / "audio.wav").read_bytes())
            self.assertEqual(json.loads((target / "primary.json").read_text())["chords"][0], p["chords"][0])
            self.assertEqual(case["recording"]["audio_sha256"], drafts.digest(target / "audio.wav"))
            self.assertFalse(result["gold"])
            self.assertIn("No manual", result["semantics"])

    def test_audio_pairing_build_cleanup_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, manifest = self.fixture(root)
            drafts.build(manifest, root / "output", root)
            with self.assertRaises(ValueError):
                drafts.build(manifest, root / "output", root)
            value = json.loads(manifest.read_text())
            value["cases"][0]["source"]["recording"]["audio_sha256"] = "0" * 64
            drafts.write_json(manifest, value)
            with self.assertRaises(ValueError):
                drafts.build(manifest, root / "bad-output", root)
            self.assertFalse((root / "bad-output").exists())
            self.assertFalse(list(root.glob(".automatic-playalong-*")))

    def test_additional_hypotheses_require_exact_full_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p, _, manifest = self.fixture(root)
            candidate = root / "extra.json"
            drafts.write_json(candidate, p)
            built = drafts.build(manifest, root / "output", root, {"test-song": [candidate]})
            self.assertEqual(len(built["cases"][0]["additional"]), 1)
            p["recording"]["id"] = "excerpt"
            drafts.write_json(candidate, p)
            with self.assertRaises(ValueError):
                drafts.build(manifest, root / "bad-output", root, {"test-song": [candidate]})
            self.assertFalse((root / "bad-output").exists())

    def test_server_fixed_allowlist_and_private_alias_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, manifest = self.fixture(root)
            output = root / "output"
            drafts.build(manifest, output, root)
            static = root / "static"
            static.mkdir()
            for name in ("index.html", "app.js", "style.css"):
                (static / name).write_text("fixture")
            with patch.object(drafts, "STATIC", static), patch.object(drafts.review_pack, "STATIC", static):
                files = drafts.public_files(output)
                self.assertNotIn("/build-spec.json", files)
                self.assertIn("/cases/test-song/evidence.json", files)
                handler = drafts.review_pack.ReviewHandler.__new__(drafts.review_pack.ReviewHandler)
                handler.public_files = files
                for url in ("/build-spec.json", "/../pilot/manifest.json", "/manifest.json?path=secret"):
                    self.assertEqual(handler.translate_path(url), str(static / "__not_found__"))
                public = output / "cases/test-song/evidence.json"
                public.unlink()
                os.link(output / "build-spec.json", public)
                self.assertEqual(handler.translate_path("/cases/test-song/evidence.json"), str(static / "__not_found__"))
                with self.assertRaises(ValueError):
                    drafts.public_files(output)


    def test_optional_practice_metadata_uses_only_fixed_static_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, manifest = self.fixture(root)
            output = root / "output"
            drafts.build(manifest, output, root)
            static = root / "static"
            static.mkdir()
            for name in ("index.html", "app.js", "style.css"):
                (static / name).write_text("fixture")
            with patch.object(drafts, "STATIC", static), patch.object(drafts.review_pack, "STATIC", static):
                self.assertNotIn("/rhythm.json", drafts.public_files(output))
                for name in ("rhythm.json", "practice.json", "learning.json"):
                    (static / name).write_text('{"fixture": true}')
                files = drafts.public_files(output)
                self.assertEqual(files["/rhythm.json"], static / "rhythm.json")
                self.assertEqual(files["/practice.json"], static / "practice.json")
                self.assertEqual(files["/learning.json"], static / "learning.json")
                handler = drafts.review_pack.ReviewHandler.__new__(drafts.review_pack.ReviewHandler)
                handler.public_files = files
                self.assertEqual(handler.translate_path("/practice.json"), str(static / "practice.json"))
                for url in ("/practice.json?path=secret", "/learning.json?path=secret", "/rhythm-config.json", "/../practice.json", "/../learning.json"):
                    self.assertEqual(handler.translate_path(url), str(static / "__not_found__"))
                for name in ("practice.json", "learning.json"):
                    path = static / name
                    path.unlink()
                    path.symlink_to(output / "build-spec.json")
                    self.assertEqual(handler.translate_path("/" + name), str(static / "__not_found__"))
                    with self.assertRaises(ValueError):
                        drafts.public_files(output)
                    path.unlink()
                    path.write_text('{"fixture": true}')


if __name__ == "__main__":
    unittest.main()
