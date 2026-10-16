"""Offline guard and pairing tests; no network access or copyrighted fixtures."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import youtube_import as importer


class YouTubeImportTests(unittest.TestCase):
    def metadata(self):
        return {"id": "XFkzRNyygfk", "title": "Test title", "duration": 2,
                "availability": "public", "live_status": "not_live", "age_limit": 0,
                "vcodec": "none", "acodec": "mp4a.40.2", "format_id": "140", "ext": "m4a",
                "url": "https://signed.example/stream?token=secret", "cookies": "secret",
                "formats": [{"url": "https://signed.example/other?token=secret"}]}

    def test_canonical_single_video_and_tracking(self):
        expected = ("https://www.youtube.com/watch?v=XFkzRNyygfk", "XFkzRNyygfk")
        for value in ("https://www.youtube.com/watch?v=XFkzRNyygfk&t=12",
                      "https://youtu.be/XFkzRNyygfk?si=tracking",
                      "https://m.youtube.com/shorts/XFkzRNyygfk",
                      "https://youtube.com/embed/XFkzRNyygfk"):
            self.assertEqual(importer.canonical_url(value), expected)

    def test_unsafe_or_collection_urls_rejected(self):
        for value in ("http://youtu.be/XFkzRNyygfk", "https://youtube.com.evil/watch?v=XFkzRNyygfk",
                      "https://user:secret@youtube.com/watch?v=XFkzRNyygfk",
                      "https://youtube.com:443/watch?v=XFkzRNyygfk",
                      "https://youtube.com/watch?v=XFkzRNyygfk&list=PL1",
                      "https://youtube.com/watch?v=XFkzRNyygfk&v=XFkzRNyygfk",
                      "https://youtube.com/results?search_query=music",
                      "https://youtu.be/XFkzRNyygfk/other", "https://youtu.be/short"):
            with self.subTest(value=value), self.assertRaises(importer.ImportFailure):
                importer.canonical_url(value)

    def test_metadata_pairing_and_access_guards(self):
        mutations = ({"id": "wrong-ID"}, {"duration": 601}, {"duration": float("nan")},
                     {"duration": True}, {"is_live": True}, {"live_status": "is_upcoming"},
                     {"availability": "private"}, {"availability": "needs_auth"},
                     {"age_limit": 18}, {"entries": []}, {"vcodec": "avc"},
                     {"ext": "../x"}, {"format_id": "https://evil"}, {"filesize": importer.MAX_BYTES + 1})
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(importer.ImportFailure):
                importer.minimal_metadata({**self.metadata(), **mutation}, "XFkzRNyygfk")

    def test_metadata_drops_signed_urls_and_credentials(self):
        data = self.metadata()
        data["title"] = "Title https://signed.example?token=secret\n"
        output = json.dumps(importer.minimal_metadata(data, "XFkzRNyygfk"))
        self.assertNotIn("secret", output)
        self.assertNotIn("cookies", output)
        self.assertNotIn("formats", output)
        self.assertIn("[link omitted]", output)

    def test_output_restrictions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "allowed"
            with patch.object(importer, "ALLOWED_OUTPUTS", (allowed,)):
                for identifier in ("../source", "", ".", "has spaces", "x" * 65):
                    with self.assertRaises(importer.ImportFailure):
                        importer.validate_output(allowed, identifier)
                with self.assertRaises(importer.ImportFailure):
                    importer.validate_output(root / "outside", "test")
                target = importer.validate_output(allowed, "test")
                target.mkdir(parents=True)
                sentinel = target / "source.m4a"
                sentinel.write_bytes(b"do not overwrite")
                with self.assertRaises(importer.ImportFailure):
                    importer.validate_output(allowed, "test")
                self.assertEqual(sentinel.read_bytes(), b"do not overwrite")

    def test_isolated_command_has_no_ambient_auth_or_proxy(self):
        command = importer.common_command(Path(sys.executable), Path(sys.executable))
        for flag in ("--ignore-config", "--no-plugin-dirs", "--no-remote-components", "--no-js-runtimes",
                     "--no-playlist", "--no-cookies", "--no-cookies-from-browser", "--no-geo-bypass"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--proxy") + 1], "")

    def test_manifest_pairs_exact_prepared_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = importer.minimal_metadata(self.metadata(), "XFkzRNyygfk")

            def fake_run(command, timeout, step, directory=None, disk_limit=None):
                if step == "Audio download":
                    (directory / "source.m4a").write_bytes(b"source fixture")
                elif step == "Audio preparation":
                    with wave.open(str(directory / "audio.wav"), "wb") as audio:
                        audio.setnchannels(1)
                        audio.setsampwidth(2)
                        audio.setframerate(22050)
                        audio.writeframes(b"\0\0" * 44100)
                return "", 0

            with patch.object(importer, "ALLOWED_OUTPUTS", (root,)), \
                 patch.object(importer, "inspect", return_value=(metadata, "test-version")), \
                 patch.object(importer, "run_bounded", side_effect=fake_run):
                result = importer.import_recording("https://youtu.be/XFkzRNyygfk", "fixture-test",
                                                  "Generated offline test", root, Path(sys.executable),
                                                  Path(sys.executable), Path(sys.executable))
            manifest = json.loads(Path(result["manifest"]).read_text())
            audio = Path(result["audio"])
            self.assertEqual(manifest["recording"]["id"], "fixture-test")
            self.assertEqual(manifest["recording"]["audio_sha256"], importer.sha256(audio))
            self.assertEqual(manifest["source"]["sha256"], importer.sha256(audio.parent / "source.m4a"))
            self.assertEqual(manifest["recording"]["duration_seconds"], 2)
            self.assertNotIn("secret", json.dumps(manifest))
            self.assertEqual(sorted(path.name for path in audio.parent.iterdir()), ["audio.wav", "manifest.json", "source.m4a"])

    def test_failed_download_leaves_no_recording_or_partial_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = importer.minimal_metadata(self.metadata(), "XFkzRNyygfk")
            with patch.object(importer, "ALLOWED_OUTPUTS", (root,)), \
                 patch.object(importer, "inspect", return_value=(metadata, "test-version")), \
                 patch.object(importer, "run_bounded", side_effect=importer.ImportFailure("Network failure")):
                with self.assertRaises(importer.ImportFailure):
                    importer.import_recording("https://youtu.be/XFkzRNyygfk", "fixture-test", "test", root,
                                              Path(sys.executable), Path(sys.executable), Path(sys.executable))
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
