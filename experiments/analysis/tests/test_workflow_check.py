"""Selected-workflow reports bind native predictions to an unchanged source pack."""

import copy
from contextlib import contextmanager, ExitStack
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import automatic_drafts as drafts
import workflow_check as workflow


class WorkflowCheckTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            source = root / "source"
            source_case = source / "cases/test-song"
            source_case.mkdir(parents=True)
            audio_path = source_case / "audio.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\x00\x00" * 16000)
            record = {"id": "test-song", "title": "Test song", "duration_seconds": 2.0,
                      "sample_rate_hz": 8000, "audio_sha256": drafts.digest(audio_path)}
            btc = {"schema_version": "1.0", "recording": record,
                   "analysis": {"id": "btc-test", "algorithm": "BTC-ISMIR19", "version": "test",
                                "runtime_seconds": .25,
                                "parameters": {"checkpoint_sha256": "1" * 64,
                                               "upstream_revision": "2" * 40,
                                               "device": "cpu", "threads": 4, "smoothing": "none"}},
                   "chords": [{"start_seconds": 0, "end_seconds": 1, "label": "C"},
                              {"start_seconds": 1, "end_seconds": 2, "label": "G"}]}
            crema = copy.deepcopy(btc)
            crema["analysis"] = {"id": "crema-test", "algorithm": "crema-pretrained", "version": "test",
                                 "runtime_seconds": .5,
                                 "parameters": {"model_version": "a4c7d57.0", "device": "cpu",
                                                "intraop_threads": "1", "inter_op_threads": "1"}}
            crema["chords"] = [{"start_seconds": 0, "end_seconds": .9, "label": "C7/E", "native_label": "C:7/3"},
                               {"start_seconds": .9, "end_seconds": 2, "label": "G", "native_label": "G:maj"}]
            chordino = copy.deepcopy(btc)
            chordino["analysis"] = {"id": "chordino-test", "algorithm": "Chordino-NNLS-Chroma", "version": "test",
                                    "runtime_seconds": .1, "parameters": {}}
            drafts.write_json(source_case / "crema.json", crema)
            drafts.write_json(source_case / "chordino.json", chordino)
            source_manifest = source / "manifest.json"
            drafts.write_json(source_manifest, {"cases": [{"id": "test-song", "name": "Test song",
                                                           "audio": "cases/test-song/audio.wav",
                                                           "source": {"recording": record, "note": "Known local fixture"}}]})
            btc_root = root / "btc-results"
            btc_case = btc_root / "cases/test-song"
            btc_case.mkdir(parents=True)
            native_btc = btc_case / "btc.json"
            drafts.write_json(native_btc, btc)
            batch_path = btc_root / "btc-batch-summary.json"
            drafts.write_json(batch_path, {"algorithm": "BTC-ISMIR19", "manifest": str(source_manifest),
                                          "runtime_seconds": .28, "failed_cases": 0,
                                          "cases": [{"id": "test-song", "status": "ok", "output": str(native_btc),
                                                     "runtime_seconds": .25}]})
            legacy = root / "legacy-player"
            drafts.build(source_manifest, legacy, root)
            selected = root / "selected-player"
            drafts.build(source_manifest, selected, root, primary_model="btc", secondary_model="crema",
                         primary_root=btc_root)
            pin = root / "pinned-input.txt"
            pin.write_text("Frozen source dependency\n", encoding="utf-8")
            policy = root / "policy.json"
            drafts.write_json(policy, {"schema_version": "selected-workflow-1.0", "primary": "btc", "secondary": "crema",
                                       "frozen_files": {pin.name: drafts.digest(pin)},
                                       "btc_checkpoint_sha256": "1" * 64, "btc_upstream_revision": "2" * 40,
                                       "retained_player_manifest_sha256": drafts.digest(legacy / "manifest.json")})
            static = root / "static"
            static.mkdir()
            for name in ("index.html", "app.js", "style.css"):
                (static / name).write_text("Local static fixture", encoding="utf-8")
            stack.enter_context(patch.object(workflow, "ROOT", root))
            stack.enter_context(patch.object(workflow, "LEGACY", legacy))
            stack.enter_context(patch.object(drafts, "STATIC", static))
            stack.enter_context(patch.object(drafts.review_pack, "STATIC", static))
            yield {"root": root, "source": source_manifest, "btc_root": btc_root, "btc": native_btc,
                   "batch": batch_path, "pack": selected, "legacy": legacy, "policy": policy, "pin": pin}

    def audit(self, fixture):
        return workflow.audit(fixture["pack"], fixture["btc_root"], fixture["source"], fixture["policy"])

    def snapshot(self, root):
        return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def invoke_main(self, fixture, output):
        args = ["workflow_check.py", "--pack", str(fixture["pack"]), "--btc-root", str(fixture["btc_root"]),
                "--source-manifest", str(fixture["source"]), "--policy", str(fixture["policy"]), "--output", str(output)]
        with patch.object(sys, "argv", args), patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            workflow.main()

    def test_valid_audit_and_new_report_leave_all_inputs_byte_identical(self):
        with self.fixture() as fixture:
            before = self.snapshot(fixture["root"])
            result = self.audit(fixture)
            self.assertEqual(self.snapshot(fixture["root"]), before)
            self.assertEqual((result["successful_cases"], result["failed_cases"], result["audio_seconds"]), (1, 0, 2.0))
            self.assertIsNone(result["cases"][0]["accuracy_score"])
            self.assertEqual(result["cases"][0]["hashes"]["primary.json"], drafts.digest(fixture["btc"]))
            self.assertEqual(result["policy_sha256"], drafts.digest(fixture["policy"]))
            self.assertEqual(result["retained_player_manifest_sha256"], drafts.digest(fixture["legacy"] / "manifest.json"))
            self.assertIsNotNone(datetime.fromisoformat(result["checked_at_utc"]).tzinfo)
            output = fixture["root"] / "new-report.json"
            self.invoke_main(fixture, output)
            report = json.loads(output.read_text())
            self.assertEqual(report["successful_cases"], 1)
            self.assertIsNone(report["cases"][0]["accuracy_score"])
            after = self.snapshot(fixture["root"])
            self.assertEqual(after.pop("new-report.json"), output.read_bytes())
            self.assertEqual(after, before)

    def test_audit_rejects_a_valid_model_name_that_falsely_declares_the_primary(self):
        with self.fixture() as fixture:
            path = fixture["pack"] / "manifest.json"
            manifest = json.loads(path.read_text())
            # Chordino/CREMA is a valid route declaration but not the selected workflow.
            manifest["model_selection"] = {"primary": "chordino", "secondary": "crema"}
            drafts.write_json(path, manifest)
            with self.assertRaises(ValueError):
                self.audit(fixture)

    def test_audit_binds_selected_manifest_declarations_to_source_and_native_bytes(self):
        for field in ("recording", "origin", "artifacts", "summary", "source"):
            with self.subTest(field=field), self.fixture() as fixture:
                path = fixture["pack"] / "manifest.json"
                manifest = json.loads(path.read_text())
                case = manifest["cases"][0]
                if field == "recording":
                    case[field]["audio_sha256"] = "f" * 64
                elif field == "origin":
                    case[field]["source_offset_seconds"] = 1
                elif field == "artifacts":
                    case[field]["primary_sha256"] = "f" * 64
                elif field == "summary":
                    case[field]["root_agreement_fraction"] = .125
                else:
                    case[field]["note"] = "A different recording source"
                drafts.write_json(path, manifest)
                with self.assertRaises(ValueError):
                    self.audit(fixture)

    def test_audit_links_batch_identity_paths_and_timing_to_the_saved_predictions(self):
        for field in ("output", "runtime_seconds", "algorithm", "nonfinite_total", "negative_total"):
            with self.subTest(field=field), self.fixture() as fixture:
                batch = json.loads(fixture["batch"].read_text())
                if field == "output":
                    batch["cases"][0][field] = str(fixture["source"])
                elif field == "runtime_seconds":
                    batch["cases"][0][field] = 10
                elif field == "algorithm":
                    batch[field] = "Another engine"
                elif field == "nonfinite_total":
                    batch["runtime_seconds"] = float("nan")
                else:
                    batch["runtime_seconds"] = -1
                # NaN is deliberate hostile input; production writer disallows it.
                fixture["batch"].write_text(json.dumps(batch), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.audit(fixture)

    def test_audit_rejects_changes_to_either_native_or_copied_chart(self):
        for which in ("native", "copied"):
            with self.subTest(chart=which), self.fixture() as fixture:
                path = fixture["btc"] if which == "native" else fixture["pack"] / "cases/test-song/primary.json"
                chart = json.loads(path.read_text())
                chart["chords"][0]["label"] = "D"
                drafts.write_json(path, chart)
                with self.assertRaises(ValueError):
                    self.audit(fixture)

    def test_audit_rejects_changed_pinned_source_input(self):
        with self.fixture() as fixture:
            fixture["pin"].write_text("Modified dependency\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "input changed"):
                self.audit(fixture)

    def test_audit_rejects_legacy_chart_mutation_without_rewriting_legacy_manifest(self):
        with self.fixture() as fixture:
            path = fixture["legacy"] / "cases/test-song/chordino.json"
            chart = json.loads(path.read_text())
            chart["chords"][0]["label"] = "D"
            drafts.write_json(path, chart)
            with self.assertRaisesRegex(ValueError, "Existing player chart"):
                self.audit(fixture)

    def test_main_refuses_existing_report_or_source_output_without_mutating_inputs(self):
        for destination in ("report", "source"):
            with self.subTest(destination=destination), self.fixture() as fixture:
                output = fixture["source"]
                if destination == "report":
                    output = fixture["root"] / "existing-report.json"
                    output.write_text("Previous report\n", encoding="utf-8")
                before = self.snapshot(fixture["root"])
                with self.assertRaises(SystemExit) as error:
                    self.invoke_main(fixture, output)
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(self.snapshot(fixture["root"]), before)


if __name__ == "__main__":
    unittest.main()
