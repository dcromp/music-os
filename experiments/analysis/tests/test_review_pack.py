"""Offline excerpt pairing, blinding and server scope checks."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_pack as review


class ReviewPackTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "source.wav"
        samples = b"".join(index.to_bytes(2, "little", signed=True) for index in range(400))
        with wave.open(str(source), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(100)
            audio.writeframes(samples)
        recording = {"id": "source-recording", "title": "Generated", "sample_rate_hz": 100,
                     "duration_seconds": 4.0, "audio_sha256": review.digest(source)}
        chart = {"schema_version": "1.0", "recording": recording,
                 "analysis": {"id": "secret-model", "algorithm": "secret-model", "version": "secret-version",
                              "runtime_seconds": 0.5, "parameters": {"secret_parameter": True}},
                 "chords": [{"start_seconds": 0, "end_seconds": 1.5, "label": "C", "native_label": "secret-native"},
                            {"start_seconds": 1.5, "end_seconds": 3, "label": "G"},
                            {"start_seconds": 3, "end_seconds": 4, "label": "Am"}]}
        review.write_json(root / "prediction.json", chart)
        spec = {"schema_version": review.SCHEMA, "bounds_status": "frozen-listening-windows", "cases": [{
            "id": "review-case", "title": "Generated listening window", "audio": "source.wav",
            "source_recording_id": "source-recording", "source_audio_sha256": recording["audio_sha256"],
            "start_seconds": 1.001, "end_seconds": 3.001, "candidates": ["prediction.json"]}]}
        return samples, chart, spec

    def test_exact_pcm_origin_and_blinded_clipped_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            samples, chart, spec = self.fixture(root)
            output = root / "pack"
            manifest = review.build(spec, output, root)
            case = manifest["cases"][0]
            self.assertEqual(case["origin"]["source_start_frame"], 100)
            self.assertEqual(case["origin"]["source_offset_seconds"], 1)
            self.assertEqual(case["origin"]["duration_seconds"], 2)
            with wave.open(str(output / "cases/review-case/audio.wav"), "rb") as clip:
                self.assertEqual(clip.readframes(clip.getnframes()), samples[200:600])
            candidate = json.loads((output / "cases/review-case/candidate-a.json").read_text())
            self.assertEqual(candidate["chords"], [{"start_seconds": 0, "end_seconds": 0.5, "label": "C"},
                                                  {"start_seconds": 0.5, "end_seconds": 2, "label": "G"}])
            public = json.dumps(manifest) + json.dumps(candidate)
            self.assertNotIn("secret", public)
            key = (output / "private-candidate-key.json").read_text()
            self.assertIn("secret-model", key)
            self.assertEqual(candidate["recording"]["audio_sha256"], review.digest(output / "cases/review-case/audio.wav"))

    def test_source_and_prediction_pairing_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, chart, spec = self.fixture(root)
            for field, value in (("id", "other"), ("audio_sha256", "bad"),
                                 ("duration_seconds", 4.2), ("sample_rate_hz", 200)):
                altered = json.loads(json.dumps(chart))
                altered["recording"][field] = value
                review.write_json(root / "prediction.json", altered)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    review.build(spec, root / "pack", root)
                self.assertFalse((root / "pack").exists())
            spec["cases"][0]["source_audio_sha256"] = "bad"
            with self.assertRaises(ValueError):
                review.build(spec, root / "pack", root)

    def test_explicit_excerpt_predictions_keep_local_time_and_require_clip_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, chart, spec = self.fixture(root)
            origin = review.clip_pcm(root / "source.wav", root / "clip.wav", 1.001, 3.001)
            chart["recording"] = {"id": "review-case", "title": "Generated excerpt", "sample_rate_hz": 100,
                                  "duration_seconds": 2, "audio_sha256": origin["audio_sha256"]}
            chart["chords"] = [{"start_seconds": 0, "end_seconds": 0.7, "label": "C"},
                               {"start_seconds": 0.7, "end_seconds": 2, "label": "G"}]
            review.write_json(root / "excerpt-prediction.json", chart)
            spec["cases"][0]["candidates"] = [{"path": "excerpt-prediction.json", "time_origin": "excerpt"}]
            review.build(spec, root / "pack", root)
            blinded = json.loads((root / "pack/cases/review-case/candidate-a.json").read_text())
            self.assertEqual(blinded["chords"], chart["chords"])
            spec["cases"][0]["candidates"][0]["time_origin"] = "source"
            with self.assertRaises(ValueError):
                review.build(spec, root / "wrong-origin", root)

    def test_frozen_bounds_no_overwrite_and_transaction_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, spec = self.fixture(root)
            with self.assertRaises(ValueError):
                review.build({**spec, "bounds_status": "unfrozen"}, root / "pack", root)
            review.build(spec, root / "pack", root)
            sentinel = (root / "pack/manifest.json").read_bytes()
            with self.assertRaises(ValueError):
                review.build(spec, root / "pack", root)
            self.assertEqual((root / "pack/manifest.json").read_bytes(), sentinel)
            spec["cases"][0]["end_seconds"] = 5
            with self.assertRaises(ValueError):
                review.build(spec, root / "bad-pack", root)
            self.assertFalse((root / "bad-pack").exists())
            self.assertFalse(list(root.glob(".listening-review-*")))

    def test_untimed_chart_is_private_and_remains_strictly_untimed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, spec = self.fixture(root)
            untimed = {"schema_version": "untimed-chart-1.0", "recording": {"id": "candidate", "title": "Candidate"},
                       "sequence": ["C", "G"], "mode": "finite", "metadata": {"status": "unreviewed"}}
            review.write_json(root / "untimed.json", untimed)
            spec["cases"][0]["untimed_chart"] = "untimed.json"
            review.build(spec, root / "pack", root)
            copied = json.loads((root / "pack/cases/review-case/untimed-chart.json").read_text())
            review.chart_aligner.validate_untimed_chart(copied)
            self.assertEqual(copied["sequence"], ["C", "G"])
            self.assertEqual(copied["recording"]["id"], "review-case")
            with patch.object(review, "STATIC", root / "static"):
                self.make_static(root / "static")
                files = review.public_files(root / "pack")
            self.assertNotIn("/cases/review-case/untimed-chart.json", files)
            untimed["metadata"]["start_seconds"] = 0
            review.write_json(root / "untimed.json", untimed)
            with self.assertRaises(ValueError):
                review.build(spec, root / "bad-pack", root)

    def make_static(self, folder):
        folder.mkdir()
        for name in ("index.html", "app.js", "style.css"):
            (folder / name).write_text("static fixture")

    def test_server_allowlist_hides_key_inputs_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, spec = self.fixture(root)
            review.build(spec, root / "pack", root)
            static = root / "static"
            self.make_static(static)
            with patch.object(review, "STATIC", static):
                files = review.public_files(root / "pack")
                handler = review.ReviewHandler.__new__(review.ReviewHandler)
                handler.public_files = files
                self.assertEqual(Path(handler.translate_path("/cases/review-case/audio.wav")), root / "pack/cases/review-case/audio.wav")
                for url in ("/private-candidate-key.json", "/build-spec.json", "/cases/review-case/origin.json",
                            "/cases/review-case/../private-candidate-key.json", "/manifest.json?path=secret",
                            "/%2e%2e/source.wav", "/cases/review-case/untimed-chart.json"):
                    with self.subTest(url=url):
                        self.assertEqual(handler.translate_path(url), str(static / "__not_found__"))
                audio = root / "pack/cases/review-case/audio.wav"
                audio.unlink()
                audio.symlink_to(root / "source.wav")
                self.assertEqual(handler.translate_path("/cases/review-case/audio.wav"), str(static / "__not_found__"))

    def test_input_path_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            for value in ("../anything", str(root / "source.wav")):
                with self.subTest(value=value), self.assertRaises((ValueError, FileNotFoundError)):
                    review.input_path(value, root)
            with self.assertRaises(ValueError):
                review.clip_pcm(root / "source.wav", root / "clip.wav", float("nan"), 2)

    def test_server_rejects_inside_private_symlinks_and_hard_link_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, spec = self.fixture(root)
            pack = root / "pack"
            review.build(spec, pack, root)
            static = root / "static"
            self.make_static(static)
            with patch.object(review, "STATIC", static):
                files = review.public_files(pack)
                handler = review.ReviewHandler.__new__(review.ReviewHandler)
                handler.public_files = files
                public = pack / "cases/review-case/candidate-a.json"
                public.unlink()
                public.symlink_to(pack / "private-candidate-key.json")
                self.assertEqual(handler.translate_path("/cases/review-case/candidate-a.json"), str(static / "__not_found__"))
                with self.assertRaises(ValueError):
                    review.public_files(pack)
                public.unlink()
                os.link(pack / "private-candidate-key.json", public)
                self.assertEqual(handler.translate_path("/cases/review-case/candidate-a.json"), str(static / "__not_found__"))
                with self.assertRaises(ValueError):
                    review.public_files(pack)


if __name__ == "__main__":
    unittest.main()
