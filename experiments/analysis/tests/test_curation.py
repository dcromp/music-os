"""Curation keeps exact native inputs, separate corrections and honest effort."""
from contextlib import contextmanager
import copy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave
from functools import partial
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import automatic_drafts as drafts
import curation


class CurationTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "source"
        folder = source / "cases/song"
        folder.mkdir(parents=True)
        audio = folder / "audio.wav"
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(100)
            stream.writeframes(b"\x00\x00" * 1000)
        recording = {"id": "song", "title": "Fixture", "audio_sha256": drafts.digest(audio), "duration_seconds": 10.0, "sample_rate_hz": 100}
        primary = {"schema_version": "1.0", "recording": recording, "analysis": {"id": "btc", "algorithm": "BTC-ISMIR19", "version": "test", "runtime_seconds": 1, "parameters": {}},
                   "chords": [{"start_seconds": 0, "end_seconds": 4, "label": "C"}, {"start_seconds": 4, "end_seconds": 4.2, "label": "Am"}, {"start_seconds": 4.2, "end_seconds": 10, "label": "G"}]}
        secondary = copy.deepcopy(primary); secondary["analysis"]["algorithm"] = "crema-pretrained"
        secondary["chords"] = [{"start_seconds": 0, "end_seconds": 5, "label": "C7/E"}, {"start_seconds": 5, "end_seconds": 10, "label": "G"}]
        drafts.write_json(folder / "btc.json", primary); drafts.write_json(folder / "crema.json", secondary)
        drafts.write_json(source / "manifest.json", {"cases": [{"id": "song", "name": "Fixture", "audio": "cases/song/audio.wav", "source": {"recording": recording}}]})
        selected = root / "selected"
        drafts.build(source / "manifest.json", selected, root, primary_model="btc", secondary_model="crema")
        context = {"schema_version": "first-ten-arrangement-check-1.0", "sources": [{"id": "teacher", "title": "Teacher", "url": "https://example.com/lesson"}],
                   "cases": [{"recording": recording, "source_ids": ["teacher"], "entry_shapes": ["C", "G"],
                              "setup": {"tuning": "EADGBE", "capo": None, "tuning_status": "Hypothesis", "capo_status": "Unverified"},
                              "rhythm_hypothesis": "Practice drill", "correction_needs": ["Check exact recording"], "sections_to_check": ["Intro"]}]}
        context_path = root / "context.json"; drafts.write_json(context_path, context)
        return selected, context_path, primary, secondary

    @contextmanager
    def pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, context, primary, secondary = self.fixture(root)
            output = root / "curation"
            manifest = curation.build(source, context, output, root)
            static = root / "static"; static.mkdir()
            for name in ("index.html", "app.js", "style.css"): (static / name).write_text("Fixture")
            with patch.object(curation, "STATIC", static):
                yield root, source, output, manifest, primary, secondary

    def test_preparation_preserves_native_bytes_and_joins_exact_source_context(self):
        with self.pack() as (root, source, output, manifest, primary, secondary):
            for name in ("audio.wav", "primary.json", "crema.json"):
                self.assertEqual((source / "cases/song" / name).read_bytes(), (output / "cases/song" / name).read_bytes())
            self.assertFalse(manifest["gold"])
            review = curation.read(output / "cases/song/review.json")
            self.assertIsNone(review["correction_effort"]["human_seconds"])
            self.assertEqual(review["statistics"]["short_primary_events"], 1)
            self.assertEqual([p["kind"] for p in review["points"]].count("coverage-sample"), 4)
            self.assertTrue(all(0 <= p["start_seconds"] < p["end_seconds"] <= 10 for p in review["points"]))
            self.assertEqual(review["source_context"]["sources"][0]["id"], "teacher")

    def test_preparation_rejects_other_master_or_context_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, context, _, _ = self.fixture(root)
            curation.build(source, context, root / "output", root)
            with self.assertRaises(ValueError): curation.build(source, context, root / "output", root)
            wrong = curation.read(context); wrong["cases"][0]["recording"]["audio_sha256"] = "f" * 64
            drafts.write_json(context, wrong)
            with self.assertRaises(ValueError): curation.build(source, context, root / "bad", root)
            self.assertFalse((root / "bad").exists())
            self.assertFalse(list(root.glob(".curation-*")))

    def test_preparation_rejects_changed_native_chart_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, context, _, _ = self.fixture(root)
            path = source / "cases/song/primary.json"; value = curation.read(path)
            value["chords"][0]["label"] = "D"; drafts.write_json(path, value)
            before = path.read_bytes()
            with self.assertRaises(ValueError): curation.build(source, context, root / "bad", root)
            self.assertEqual(path.read_bytes(), before)

    def test_source_update_is_paired_and_does_not_rewrite_frozen_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, context, primary, _ = self.fixture(root)
            original = context.read_bytes()
            update = {"schema_version": "curation-source-updates-1.0", "context_sha256": drafts.digest(context), "checked_date": "2026-10-14", "sources": [],
                      "cases": [{"recording": primary["recording"], "correction_needs": ["Keep meter unverified"], "review_role": "Setup", "note": "Text does not confirm a meter change"}]}
            path = root / "updates.json"; drafts.write_json(path, update)
            output = root / "updated"; curation.build(source, context, output, root, path)
            self.assertEqual(context.read_bytes(), original)
            review = curation.read(output / "cases/song/review.json")
            self.assertEqual(review["source_context"]["correction_needs"], ["Keep meter unverified"])
            update["cases"][0]["recording"]["audio_sha256"] = "f" * 64; drafts.write_json(path, update)
            with self.assertRaises(ValueError): curation.build(source, context, root / "bad", root, path)

    def test_union_of_flag_spans_does_not_double_count_workload(self):
        self.assertEqual(curation.merged_duration([(1, 4), (2, 3), (3, 7), (8, 9)]), 7)
        self.assertEqual(curation.merged_duration([]), 0)

    def test_draft_metadata_cannot_claim_gold_or_other_audio_or_approval(self):
        with self.pack() as (_, _, output, manifest, _, _):
            case = manifest["cases"][0]; review = curation.read(output / "cases/song/review.json")
            original = curation.blank_draft(manifest, case)
            for field in ("gold", "recording", "base_artifacts", "pack_id", "revision", "accepted"):
                value = copy.deepcopy(original)
                if field == "gold": value[field] = True
                elif field == "recording": value[field]["audio_sha256"] = "f" * 64
                elif field == "base_artifacts": value[field]["primary_sha256"] = "f" * 64
                elif field == "pack_id": value[field] = "other"
                elif field == "revision": value[field] = True
                else: value[field] = True
                with self.subTest(field=field), self.assertRaises(ValueError): curation.validate_draft(value, manifest, case, review)

    def test_startup_rejects_changed_copied_audio_charts_and_recording_context(self):
        for filename in ("audio.wav", "primary.json", "crema.json", "review.json"):
            with self.subTest(filename=filename), self.pack() as (_, _, output, _, _, _):
                path = output / "cases/song" / filename
                if filename == "audio.wav":
                    data = bytearray(path.read_bytes()); data[-1] = 1; path.write_bytes(data)
                else:
                    value = curation.read(path)
                    if filename == "review.json": value["recording"]["audio_sha256"] = "f" * 64
                    else: value["chords"][0]["label"] = "D"
                    drafts.write_json(path, value)
                with self.assertRaises(ValueError): curation.public_files(output)

    def test_malformed_recording_metadata_returns_400_without_writes(self):
        with self.server() as (values, port):
            for recording in (None, "song", [], 42):
                draft = curation.blank_draft(values[3], values[3]["cases"][0]); draft["recording"] = recording
                with self.subTest(recording=recording):
                    self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft)[0], 400)
            self.assertFalse((values[2] / "private-drafts").exists())

    def test_corrections_and_sections_reject_overlap_out_of_bounds_and_code_labels(self):
        with self.pack() as (_, _, output, manifest, _, _):
            case = manifest["cases"][0]; review = curation.read(output / "cases/song/review.json")
            for intervals in ([{"start_seconds": 0, "end_seconds": 11, "label": "C"}],
                              [{"start_seconds": 0, "end_seconds": 5, "label": "C"}, {"start_seconds": 4, "end_seconds": 6, "label": "D"}],
                              [{"start_seconds": 0, "end_seconds": 5, "label": "<script>"}],
                              [{"start_seconds": float("nan"), "end_seconds": 5, "label": "C"}]):
                value = curation.blank_draft(manifest, case); value["chord_edits"] = intervals
                with self.assertRaises(ValueError): curation.validate_draft(value, manifest, case, review)
            value = curation.blank_draft(manifest, case); value["sections"] = [{"start_seconds": 8, "end_seconds": 7, "name": "Verse"}]
            with self.assertRaises(ValueError): curation.validate_draft(value, manifest, case, review)

    def test_checked_windows_are_bounded_and_never_arrangement_acceptance(self):
        with self.pack() as (_, _, output, manifest, _, _):
            case = manifest["cases"][0]; review = curation.read(output / "cases/song/review.json")
            value = curation.blank_draft(manifest, case); value["checked_points"] = [p["id"] for p in review["points"]]
            curation.validate_draft(value, manifest, case, review)
            self.assertFalse(value["gold"]); self.assertNotIn("accepted", value)
            value["checked_points"].append("invented")
            with self.assertRaises(ValueError): curation.validate_draft(value, manifest, case, review)

    def test_review_time_keeps_human_agent_and_qa_separate(self):
        with self.pack() as (_, _, output, manifest, _, _):
            case = manifest["cases"][0]; review = curation.read(output / "cases/song/review.json")
            value = curation.blank_draft(manifest, case)
            value["sessions"] = [{"id": actor, "actor": actor, "task": "chords", "active_seconds": seconds,
                                  "started_at": "2026-10-14T10:00:00Z", "ended_at": "2026-10-14T10:01:00Z"}
                                 for actor, seconds in (("human", 25), ("agent", 30), ("qa", 40))]
            curation.validate_draft(value, manifest, case, review)
            self.assertEqual(curation.effort(value), {"human_seconds": 25, "agent_seconds": 30, "qa_seconds": 40})
            self.assertEqual(curation.effort(curation.blank_draft(manifest, case)), {"human_seconds": None, "agent_seconds": None, "qa_seconds": None})
            for change in ({"active_seconds": float("inf")}, {"active_seconds": -1}, {"active_seconds": 1801}, {"active_seconds": 100}, {"actor": "unknown"}, {"ended_at": "2026-10-13T10:00:00Z"}):
                bad = copy.deepcopy(value); bad["sessions"][0].update(change)
                with self.assertRaises(ValueError): curation.validate_draft(bad, manifest, case, review)

    @contextmanager
    def server(self):
        with self.pack() as values:
            root, source, output, manifest, _, _ = values
            files, _ = curation.public_files(output)
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(curation.CurationHandler, files=files, manifest=manifest, pack=output))
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try: yield values, server.server_port
            finally: server.shutdown(); server.server_close(); thread.join()

    def request(self, port, method, path, value=None, origin=True, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        body = json.dumps(value) if value is not None else None
        request_headers = {"Content-Type": "application/json"}
        if origin: request_headers["Origin"] = f"http://127.0.0.1:{port}"
        request_headers.update(headers or {})
        connection.request(method, path, body, request_headers); response = connection.getresponse()
        payload = response.read(); status = response.status; connection.close()
        return status, payload

    def test_saved_draft_roundtrip_revision_and_raw_bytes_preserved(self):
        with self.server() as (values, port):
            _, source, output, manifest, _, _ = values
            original = {name: (output / "cases/song" / name).read_bytes() for name in ("audio.wav", "primary.json", "crema.json")}
            status, body = self.request(port, "GET", "/api/drafts/song"); self.assertEqual(status, 200)
            draft = json.loads(body)["draft"]; draft["chord_edits"] = [{"start_seconds": 4, "end_seconds": 4.2, "label": "G", "note": "QA fixture"}]
            status, body = self.request(port, "POST", "/api/drafts/song", draft); self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["draft"]["revision"], 1)
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft)[0], 409)
            saved = json.loads(self.request(port, "GET", "/api/drafts/song")[1])["draft"]
            self.assertEqual(saved["chord_edits"], draft["chord_edits"])
            self.assertFalse(saved["gold"])
            for name, before in original.items(): self.assertEqual((output / "cases/song" / name).read_bytes(), before)
            self.assertEqual(self.request(port, "GET", "/private-drafts/song.json")[0], 404)
            self.assertEqual(self.request(port, "GET", "/build-spec.json")[0], 404)

    def test_write_api_rejects_cross_origin_invalid_body_and_unsafe_routes(self):
        with self.server() as (values, port):
            draft = curation.blank_draft(values[3], values[3]["cases"][0])
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft, origin=False)[0], 403)
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft, headers={"Origin": "https://example.com"})[0], 403)
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft, headers={"Content-Type": "text/plain"})[0], 400)
            self.assertEqual(self.request(port, "POST", "/api/drafts/../song", draft)[0], 400)
            self.assertEqual(self.request(port, "POST", "/api/drafts/song?file=secret", draft)[0], 400)
            bad = copy.deepcopy(draft); bad["gold"] = True
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", bad)[0], 400)
            self.assertFalse((values[2] / "private-drafts").exists())

    def test_public_assets_reject_private_symlink_or_hardlink_alias(self):
        with self.server() as (values, port):
            _, _, output, manifest, _, _ = values
            draft = curation.blank_draft(manifest, manifest["cases"][0])
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft)[0], 200)
            public = output / "cases/song/review.json"
            public.unlink(); public.hardlink_to(output / "private-drafts/song.json")
            self.assertEqual(self.request(port, "GET", "/cases/song/review.json")[0], 404)

    def test_private_symlink_cannot_redirect_correction_writes(self):
        with self.server() as (values, port):
            root, _, output, manifest, _, _ = values
            outside = root / "outside"; outside.mkdir()
            (output / "private-drafts").symlink_to(outside, target_is_directory=True)
            draft = curation.blank_draft(manifest, manifest["cases"][0])
            self.assertEqual(self.request(port, "POST", "/api/drafts/song", draft)[0], 400)
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__": unittest.main()
