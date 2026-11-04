"""Offline first-ten workflow tests; generated audio only and no network calls."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import repertoire_batch as batch


class RepertoireBatchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.output = self.root / "experiments" / "generated" / "prepared"
        self.cache = self.root / "experiments" / "generated" / "youtube-pilot" / "manifest.json"
        self.cache.parent.mkdir(parents=True)
        self.review_path = self.root / "catalogue" / "first-ten-review.json"
        self.review_path.parent.mkdir()
        self.rows = []
        self.original = {}
        cached_cases = []
        cached = [("radiohead-creep-youtube-20261010", "Creep", "Radiohead", "XFkzRNyygfk"),
                  ("oasis-wonderwall-youtube-20261010", "Wonderwall", "Oasis", "bx1Bh8ZvH84")]
        for index in range(10):
            if index < 2:
                recording_id, title, artist, video_id = cached[index]
            else:
                recording_id, title, artist, video_id = f"new-{index}", f"Song {index}", "Generated Artist", f"video{index:06d}"
            row = {"id": f"song-{index}", "title": title, "artist": artist,
                   "selected_recording": {"recording_id": recording_id, "url": f"https://www.youtube.com/watch?v={video_id}",
                                          "video_id": video_id, "expected_uploader": artist},
                   "cached_example": None,
                   "teaching": {"chord_set": ["TEACHING_SECRET"], "key": "DO_NOT_INFER", "timings": [123]}}
            if index < 2:
                folder = self.cache.parent / "cases" / recording_id
                source = self.make_case(folder, row)
                (folder / "source.json").write_text(json.dumps(source))
                for name in ("crema.json", "chordino.json"):
                    chart = {"schema_version": "1.0", "recording": deepcopy(source["recording"]),
                             "analysis": {"id": recording_id + "-" + name},
                             "chords": [{"start_seconds": 0, "end_seconds": 1, "label": "C"}]}
                    (folder / name).write_text(json.dumps(chart) + "\n")
                row["cached_example"] = {key: source["recording"][key] for key in ("audio_sha256", "duration_seconds")}
                row["cached_example"]["recording_id"] = recording_id
                cached_cases.append({"id": recording_id, "audio": f"cases/{recording_id}/audio.wav", "source": source})
                for path in folder.iterdir():
                    self.original[path] = path.read_bytes()
            self.rows.append(row)
        self.review = {"schema_version": batch.SCHEMA, "songs": self.rows}
        self.cache.write_text(json.dumps({"cases": cached_cases}))
        self.original[self.cache] = self.cache.read_bytes()
        self.write_review()
        self.import_calls = []

    def write_review(self):
        self.review_path.write_text(json.dumps(self.review))

    def make_case(self, folder, row, mutation=None):
        folder.mkdir(parents=True, exist_ok=False)
        audio = folder / "audio.wav"
        with wave.open(str(audio), "wb") as handle:
            handle.setnchannels(1); handle.setframerate(22050); handle.setsampwidth(2)
            handle.writeframes(b"\0\0" * 22050)
        selected = row["selected_recording"]
        source = {"schema_version": "1.0", "status": "prepared",
                  "recording": {"id": selected["recording_id"], "title": row["title"], "audio": "audio.wav",
                                "duration_seconds": 1.0, "sample_rate_hz": 22050, "audio_sha256": batch.sha256(audio)},
                  "source": {"video_id": selected["video_id"], "url": selected["url"], "title": row["title"],
                             "uploader": row["artist"], "file": "source.m4a", "sha256": "unused-cache-source-pin"}}
        if mutation:
            mutation(source, folder)
        return source

    def fake_import(self, url, recording_id, source_use, output_root, python, node, ffmpeg):
        self.import_calls.append({"url": url, "recording_id": recording_id, "source_use": source_use,
                                  "python": python, "node": node, "ffmpeg": ffmpeg})
        row = next(row for row in self.rows if row["selected_recording"]["recording_id"] == recording_id)
        folder = output_root / recording_id
        source = self.make_case(folder, row)
        encoded = folder / "source.m4a"
        encoded.write_bytes(b"generated encoded placeholder")
        source["source"]["sha256"] = batch.sha256(encoded)
        (folder / "manifest.json").write_text(json.dumps(source))
        return {"manifest": str(folder / "manifest.json"), "audio": str(folder / "audio.wav")}

    def run_prepare(self, importer=None, output=None, progress=None, reuse_prepared=None):
        return batch.prepare(self.review_path, output or self.output, Path("/isolated-python"),
                             Path("/node-runtime"), Path("/ffmpeg-runtime"), self.cache, self.root,
                             importer=importer or self.fake_import, progress=progress, reuse_prepared=reuse_prepared)

    def status(self):
        return json.loads((self.output / "batch-status.json").read_text())

    def assert_originals_unchanged(self):
        for path, content in self.original.items():
            self.assertEqual(path.read_bytes(), content)

    def test_prepares_all_ten_reuses_two_outputs_and_only_imports_eight_selected_urls(self):
        report = self.run_prepare()
        self.assertEqual((report["status"], report["completed"], report["failed"]), ("prepared", 10, 0))
        self.assertEqual(len(self.import_calls), 8)
        self.assertEqual([call["url"] for call in self.import_calls], [row["selected_recording"]["url"] for row in self.rows[2:]])
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(len(manifest["cases"]), 10)
        self.assertEqual(report["manifest_sha256"], batch.sha256(self.output / "manifest.json"))
        for row in self.rows[:2]:
            identifier = row["selected_recording"]["recording_id"]
            for name in ("audio.wav", "source.json", "crema.json", "chordino.json"):
                self.assertEqual((self.output / "cases" / identifier / name).read_bytes(),
                                 (self.cache.parent / "cases" / identifier / name).read_bytes())
        self.assert_originals_unchanged()

    def test_inference_manifest_excludes_cached_jobs_and_all_teaching_fields(self):
        self.run_prepare()
        payload = (self.output / "audio-only-inference-manifest.json").read_text()
        data = json.loads(payload)
        self.assertEqual(len(data["cases"]), 8)
        self.assertTrue(all(case["id"] not in batch.CACHED_IDS for case in data["cases"]))
        for forbidden in ("TEACHING_SECRET", "DO_NOT_INFER", '"teaching":', '"timings":', '"chord_set":'):
            self.assertNotIn(forbidden, payload)
        self.assertTrue(all(set(case) == {"id", "name", "audio", "source"} for case in data["cases"]))

    def test_importer_receives_only_explicit_input_and_isolated_runtime_arguments(self):
        self.run_prepare()
        for call in self.import_calls:
            self.assertEqual((call["python"], call["node"], call["ffmpeg"]),
                             (Path("/isolated-python"), Path("/node-runtime"), Path("/ffmpeg-runtime")))
            self.assertEqual(call["source_use"], batch.SOURCE_USE)
            self.assertNotIn("TEACHING_SECRET", json.dumps({key: str(value) for key, value in call.items()}))

    def test_existing_output_never_overwritten(self):
        self.output.mkdir(parents=True)
        marker = self.output / "sentinel"
        marker.write_bytes(b"preserve")
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare()
        self.assertEqual(marker.read_bytes(), b"preserve")
        self.assertEqual(self.import_calls, [])

    def test_output_and_input_symlinks_or_external_paths_rejected(self):
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare(output=self.root / "outside-generated")
        link = self.root / "review-link.json"
        link.symlink_to(self.review_path)
        with self.assertRaises(batch.BatchFailure):
            batch.prepare(link, self.output, Path("p"), Path("n"), Path("f"), self.cache, self.root, importer=self.fake_import)
        allowed = self.root / "experiments" / "generated"
        alias = allowed / "alias"
        alias.symlink_to(self.cache.parent, target_is_directory=True)
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare(output=alias / "new")
        self.assertEqual(self.import_calls, [])

    def test_review_requires_ten_unique_safe_ids_selected_url_match_and_two_pinned_cache_rows(self):
        mutations = [lambda value: value["songs"].pop(),
                     lambda value: value["songs"][2].update(id="../bad"),
                     lambda value: value["songs"][2]["selected_recording"].update(recording_id="x" * 65),
                     lambda value: value["songs"][2]["selected_recording"].update(video_id="wrong"),
                     lambda value: value["songs"][2]["selected_recording"].update(url={"bad": "url"}),
                     lambda value: value["songs"][2].update(id=value["songs"][0]["id"]),
                     lambda value: value["songs"][0]["cached_example"].update(duration_seconds=True),
                     lambda value: value["songs"][0].update(cached_example=None),
                     lambda value: value["songs"][0]["cached_example"].update(recording_id="animals-house-rising-sun-youtube-20261010")]
        for mutation in mutations:
            review = deepcopy(self.review)
            mutation(review)
            with self.subTest(review=review), self.assertRaises((batch.BatchFailure, batch.youtube_import.ImportFailure)):
                batch.reviewed_songs(review)

    def test_wrong_cached_audio_pin_is_a_persisted_case_failure_without_network_reuse(self):
        self.rows[0]["cached_example"]["audio_sha256"] = "0" * 64
        self.write_review()
        report = self.run_prepare()
        self.assertEqual((report["status"], report["completed"], report["failed"]), ("incomplete", 9, 1))
        self.assertEqual(len(self.import_calls), 8)
        self.assertIn("reviewed pin", report["cases"][0]["error"])
        self.assertFalse((self.output / "manifest.json").exists())
        self.assertFalse((self.output / "audio-only-inference-manifest.json").exists())
        self.assert_originals_unchanged()

    def test_wrong_cached_chart_pairing_rejected_without_mutating_pilot(self):
        identifier = self.rows[0]["selected_recording"]["recording_id"]
        chart_path = self.cache.parent / "cases" / identifier / "crema.json"
        value = json.loads(chart_path.read_text())
        value["recording"]["audio_sha256"] = "0" * 64
        chart_path.write_text(json.dumps(value))
        report = self.run_prepare()
        self.assertEqual(report["cases"][0]["status"], "failed")
        self.assertIn("cached detector output", report["cases"][0]["error"])
        self.assertFalse((self.output / "cases" / identifier).exists())

    def test_wrong_imported_video_channel_title_audio_hash_or_source_hash_rejected_in_staging(self):
        mutations = [lambda source: source["source"].update(video_id="wrong"),
                     lambda source: source["source"].update(uploader="Unrelated Artist"),
                     lambda source: source["source"].update(title="Different Song"),
                     lambda source: source["recording"].update(audio_sha256="0" * 64),
                     lambda source: source["source"].update(sha256="0" * 64)]
        for index, mutation in enumerate(mutations):
            def changed_import(*args):
                result = self.fake_import(*args)
                source_path = Path(result["manifest"])
                source = json.loads(source_path.read_text())
                mutation(source)
                source_path.write_text(json.dumps(source))
                return result
            output = self.root / "experiments" / "generated" / f"bad-input-{index}"
            report = self.run_prepare(importer=changed_import, output=output)
            self.assertEqual((report["completed"], report["failed"]), (2, 8))
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(len(list((output / "cases").iterdir())), 2)
            self.assertFalse((output / "manifest.json").exists())

    def test_a_failed_import_persists_safe_results_and_does_not_stop_other_recordings(self):
        def fails_one(*args):
            if args[1] == "new-2":
                raise RuntimeError("https://signed.example/stream?token=SECRET COOKIE")
            return self.fake_import(*args)
        report = self.run_prepare(importer=fails_one)
        self.assertEqual((report["completed"], report["failed"]), (9, 1))
        self.assertEqual(len(self.import_calls), 7)
        self.assertEqual(self.status()["status"], "incomplete")
        serialized = (self.output / "batch-status.json").read_text()
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("signed.example", serialized)
        self.assertFalse(any(path.name.startswith(".batch-staging-") for path in self.output.iterdir()))

    def test_full_manifests_are_published_only_after_all_inputs_pass(self):
        progress = []
        def observe(item):
            progress.append(item)
            self.assertFalse((self.output / "manifest.json").exists())
            self.assertFalse((self.output / "audio-only-inference-manifest.json").exists())
            self.assertEqual(self.status()["completed"], item["completed"])
        self.run_prepare(progress=observe)
        self.assertEqual(len(progress), 10)
        self.assertTrue((self.output / "manifest.json").exists())

    def test_source_title_article_and_official_topic_channel_variants_are_reasonable_matches(self):
        row = deepcopy(self.rows[2]); row["title"] = "The Song 2"
        folder = self.root / "article-fixture"
        source = self.make_case(folder, row)
        source["source"].update(title="Song 2 (Remastered)", uploader="Generated Artist - Topic")
        row["selected_recording"]["expected_uploader"] = ["Generated Artist (Official Artist Channel)"]
        batch.verify_source(source, row, folder / "audio.wav")

    def test_metadata_without_reviewed_expected_channel_falls_back_to_artist_match(self):
        row = deepcopy(self.rows[2]); row["selected_recording"].pop("expected_uploader")
        folder = self.root / "artist-fixture"
        source = self.make_case(folder, row)
        source["source"]["uploader"] = "Generated ArtistVEVO"
        batch.verify_source(source, row, folder / "audio.wav")
        source["source"]["uploader"] = "OtherArtist"
        with self.assertRaises(batch.BatchFailure):
            batch.verify_source(source, row, folder / "audio.wav")

    def test_safe_import_error_categories_do_not_copy_untrusted_diagnostics(self):
        message = batch.safe_failure(batch.youtube_import.ImportFailure("HTTP 403 https://signed.example?token=SECRET"))
        self.assertIn("403", message)
        self.assertNotIn("SECRET", message)
        self.assertNotIn("signed.example", message)

    def partial_pack(self):
        def fails_one(*args):
            if args[1] == "new-4":
                raise batch.youtube_import.ImportFailure("upstream access refusal HTTP 403")
            return self.fake_import(*args)
        report = self.run_prepare(importer=fails_one)
        self.assertEqual((report["completed"], report["failed"]), (9, 1))
        self.import_calls.clear()
        return self.output

    def snapshot(self, folder):
        return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob("*") if path.is_file()}

    def test_partial_recovery_copies_nine_byte_exact_and_retries_only_the_failed_explicit_url(self):
        previous = self.partial_pack()
        originals = self.snapshot(previous)
        next_pack = self.root / "experiments" / "generated" / "recovered"
        report = self.run_prepare(output=next_pack, reuse_prepared=previous)
        self.assertEqual((report["status"], report["completed"], report["failed"]), ("prepared", 10, 0))
        self.assertEqual([call["recording_id"] for call in self.import_calls], ["new-4"])
        self.assertEqual(report["reuse_prepared"]["batch_status_sha256"], batch.sha256(previous / "batch-status.json"))
        self.assertEqual(sum(item["workflow"] == "reuse-prepared" for item in report["cases"]), 9)
        for relative, content in originals.items():
            if relative.startswith("cases/"):
                self.assertEqual((next_pack / relative).read_bytes(), content)
        self.assertEqual(self.snapshot(previous), originals)
        self.assert_originals_unchanged()
        inference = json.loads((next_pack / "audio-only-inference-manifest.json").read_text())
        self.assertEqual(len(inference["cases"]), 8)
        self.assertEqual({case["id"] for case in inference["cases"]}, {f"new-{index}" for index in range(2, 10)})

    def test_complete_reuse_needs_no_imports_and_still_has_eight_new_inference_inputs(self):
        self.run_prepare()
        previous = self.output
        originals = self.snapshot(previous)
        self.import_calls.clear()
        next_pack = self.root / "experiments" / "generated" / "reused-all-ten"
        report = self.run_prepare(output=next_pack, reuse_prepared=previous)
        self.assertEqual(report["status"], "prepared")
        self.assertEqual(self.import_calls, [])
        self.assertEqual(sum(item["workflow"] == "reuse-prepared" for item in report["cases"]), 10)
        self.assertEqual(len(json.loads((next_pack / "audio-only-inference-manifest.json").read_text())["cases"]), 8)
        self.assertEqual(self.snapshot(previous), originals)

    def test_reuse_changed_catalogue_hash_rejected_before_any_import_or_new_output(self):
        previous = self.partial_pack()
        self.review["notes"] = "Changed review bytes"
        self.write_review()
        next_pack = self.root / "experiments" / "generated" / "changed-review"
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare(output=next_pack, reuse_prepared=previous)
        self.assertEqual(self.import_calls, [])
        self.assertFalse(next_pack.exists())

    def test_reuse_wrong_source_audio_encoded_hash_and_original_cached_chart_bytes_fail_preflight(self):
        self.run_prepare()
        previous = self.output
        originals = self.snapshot(previous)
        new_case = previous / "cases" / "new-2"
        cached_case = previous / "cases" / self.rows[0]["selected_recording"]["recording_id"]
        mutations = [lambda: (new_case / "audio.wav").write_bytes(b"corrupt"),
                     lambda: (new_case / "source.m4a").write_bytes(b"wrong encoded source"),
                     lambda: (new_case / "source.json").write_text("{}"),
                     lambda: (cached_case / "crema.json").write_bytes((cached_case / "crema.json").read_bytes() + b" ")]
        self.import_calls.clear()
        for index, mutation in enumerate(mutations):
            mutation()
            next_pack = self.root / "experiments" / "generated" / f"reuse-corrupt-{index}"
            with self.subTest(index=index), self.assertRaises(batch.BatchFailure):
                self.run_prepare(output=next_pack, reuse_prepared=previous)
            self.assertFalse(next_pack.exists())
            self.assertEqual(self.import_calls, [])
            for relative, content in originals.items():
                (previous / relative).write_bytes(content)

    def test_reuse_symlink_case_or_file_rejected_before_import(self):
        previous = self.partial_pack()
        case = previous / "cases" / "new-2"
        audio = case / "audio.wav"
        contents = audio.read_bytes()
        other = self.root / "external-wave.wav"
        other.write_bytes(contents)
        audio.unlink(); audio.symlink_to(other)
        next_pack = self.root / "experiments" / "generated" / "reuse-symlink"
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare(output=next_pack, reuse_prepared=previous)
        self.assertFalse(next_pack.exists())
        self.assertEqual(self.import_calls, [])

    def test_reuse_wrong_status_identity_totals_and_unexpected_files_are_rejected(self):
        previous = self.partial_pack()
        status_path = previous / "batch-status.json"
        original = status_path.read_bytes()
        mutations = [lambda value: value["cases"][2].update(video_id="wrong"),
                     lambda value: value.update(completed=10),
                     lambda value: value["cases"][2].update(audio_sha256="0" * 64),
                     lambda value: value["cases"][0]["cached_detector_sha256"].update(**{"crema.json": "0" * 64})]
        for index, mutation in enumerate(mutations):
            status = json.loads(original)
            mutation(status)
            status_path.write_text(json.dumps(status))
            next_pack = self.root / "experiments" / "generated" / f"reuse-status-{index}"
            with self.subTest(index=index), self.assertRaises(batch.BatchFailure):
                self.run_prepare(output=next_pack, reuse_prepared=previous)
            self.assertFalse(next_pack.exists())
        status_path.write_bytes(original)
        (previous / "cases" / "new-2" / "sidecar.txt").write_text("unexpected")
        with self.assertRaises(batch.BatchFailure):
            self.run_prepare(output=self.root / "experiments" / "generated" / "reuse-extra", reuse_prepared=previous)
        self.assertEqual(self.import_calls, [])

    def test_reuse_retains_optional_paired_detector_files_on_new_inputs(self):
        previous = self.partial_pack()
        folder = previous / "cases" / "new-2"
        source = json.loads((folder / "source.json").read_text())
        chart = {"schema_version": "1.0", "recording": source["recording"],
                 "chords": [{"start_seconds": 0, "end_seconds": 1, "label": "C"}]}
        for name in ("crema.json", "chordino.json"):
            (folder / name).write_text(json.dumps(chart) + "\n")
        next_pack = self.root / "experiments" / "generated" / "reuse-models"
        self.run_prepare(output=next_pack, reuse_prepared=previous)
        for name in ("crema.json", "chordino.json"):
            self.assertEqual((next_pack / "cases" / "new-2" / name).read_bytes(), (folder / name).read_bytes())

    def test_reuse_retry_failure_keeps_nine_successes_in_fresh_pack_and_preserves_original_status(self):
        previous = self.partial_pack()
        originals = self.snapshot(previous)
        def still_fails(*args):
            self.import_calls.append({"recording_id": args[1]})
            raise batch.youtube_import.ImportFailure("HTTP 403 https://signed.example?token=SECRET")
        next_pack = self.root / "experiments" / "generated" / "retry-failed"
        report = self.run_prepare(importer=still_fails, output=next_pack, reuse_prepared=previous)
        self.assertEqual((report["status"], report["completed"], report["failed"]), ("incomplete", 9, 1))
        self.assertEqual(self.import_calls, [{"recording_id": "new-4"}])
        self.assertFalse((next_pack / "manifest.json").exists())
        self.assertEqual(len(list((next_pack / "cases").iterdir())), 9)
        self.assertNotIn("SECRET", (next_pack / "batch-status.json").read_text())
        self.assertEqual(self.snapshot(previous), originals)

    def test_fresh_output_cannot_be_nested_inside_preserved_cache_or_reused_pack(self):
        previous = self.partial_pack()
        for output in (previous / "nested", self.cache.parent / "nested"):
            with self.assertRaises(batch.BatchFailure):
                self.run_prepare(output=output, reuse_prepared=previous)
            self.assertFalse(output.exists())
        self.assertEqual(self.import_calls, [])


if __name__ == "__main__":
    unittest.main()
