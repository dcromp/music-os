import copy
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alignment_comparison as comparison
import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import lab


def fixture_suite(folder):
    suite = folder / "suite"
    audio, reference_path = lab.create_fixture(suite)
    case = {"id": "fixture", "level": 5, "condition": "offbeat", "split": "holdout",
            "audio": audio.name, "reference": reference_path.name}
    lab.write_json(suite / "manifest.json", {"suite_version": "test", "cases": [case]})
    return suite, audio, reference_path


class AlignmentComparisonTests(unittest.TestCase):
    def test_both_backends_receive_only_same_untimed_labels_and_score_after_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            suite, audio, reference_path = fixture_suite(folder)
            reference = lab.load_chart(reference_path)
            actual_align, actual_score = chart_aligner.align, alignment_screen.boundary_metrics
            stages, charts = [], []

            def extraction(audio_path, identifier):
                self.assertEqual(audio_path, audio)
                self.assertEqual(identifier, reference["recording"]["id"])
                stages.append("extract")
                return {"schema_version": "interface-test-evidence"}

            def alignment(audio_path, chart_path, **parameters):
                chart = json.loads(chart_path.read_text())
                charts.append(chart)
                self.assertEqual(chart["sequence"], [event["label"] for event in reference["chords"] if event["label"] != "N"])
                serialized = chart_path.read_text()
                for key in ("start_seconds", "end_seconds", "duration_seconds", "beats_seconds", "downbeats_seconds"):
                    self.assertNotIn(key, serialized)
                self.assertEqual({key: value for key, value in parameters.items() if key != "evidence_json"}, comparison.DEFAULTS)
                backend = "nnls" if "evidence_json" in parameters else "spectral"
                stages.append(f"align-{backend}")
                # This test supplies mocked native evidence. Exercise the real
                # aligner without it while auditing the actual adapter interface.
                parameters.pop("evidence_json", None)
                with patch.object(lab, "load_chart", side_effect=AssertionError("Aligner read timing gold")):
                    return actual_align(audio_path, chart_path, **parameters)

            def scoring(expected, predicted):
                self.assertIn(stages[-1], ("align-spectral", "align-nnls"))
                stages.append("score")
                return actual_score(expected, predicted)

            output = folder / "comparison"
            with patch.object(nnls_chroma_adapter, "extract", side_effect=extraction), \
                 patch.object(nnls_chroma_adapter, "validate_evidence") as validate, \
                 patch.object(chart_aligner, "align", side_effect=alignment), \
                 patch.object(alignment_screen, "boundary_metrics", side_effect=scoring):
                report = comparison.run(suite, output)
            self.assertEqual(stages, ["align-spectral", "score", "extract", "align-nnls", "score"])
            self.assertEqual(charts[0], charts[1])
            validate.assert_called_once_with({"schema_version": "interface-test-evidence"}, audio)
            self.assertEqual(report["paired_successful_cases"], 1)
            self.assertEqual(report["backend_failed_attempts"], {"spectral": 0, "nnls-chroma": 0})
            row = report["cases"][0]
            self.assertEqual(row["audio_sha256"], comparison.sha(audio))
            self.assertEqual(row["hidden_reference_sha256"], comparison.sha(reference_path))
            self.assertEqual(row["backends"]["nnls-chroma"]["evidence_sha256"], comparison.sha(output / "cases/fixture/nnls-evidence.json"))
            timing = row["backends"]["spectral"]["timing"]
            self.assertGreater(timing["feature_extraction_wall_seconds"], 0)
            self.assertEqual(timing["feature_extraction_wall_seconds"], timing["original_pcm_features_wall_seconds"])
            self.assertEqual(timing["end_to_end_inference_wall_seconds"], timing["align_call_wall_seconds"])

    def test_native_timeout_preserves_successful_control_and_failure_row(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            suite, _, _ = fixture_suite(folder)
            with patch.object(nnls_chroma_adapter, "extract", side_effect=subprocess.TimeoutExpired("host", 180)):
                report = comparison.run(suite, folder / "comparison")
            self.assertEqual(report["paired_successful_cases"], 0)
            self.assertEqual(report["failed_or_partial_cases"], 1)
            self.assertEqual(report["backend_successful_cases"], {"spectral": 1, "nnls-chroma": 0})
            self.assertEqual(report["backend_failed_attempts"], {"spectral": 0, "nnls-chroma": 1})
            self.assertEqual(report["summary"], {})
            self.assertIn("timed out", report["cases"][0]["backends"]["nnls-chroma"]["reason"])
            rows = list(csv.DictReader(io.StringIO(comparison.csv_report(report))))
            self.assertEqual([row["status"] for row in rows], ["ok", "error"])
            self.assertEqual(rows[1]["boundary_f1_150ms"], "")
            self.assertIn("timed out", rows[1]["reason"])

    def test_unsupported_labels_are_visible_exclusions_with_no_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            suite, _, reference_path = fixture_suite(folder)
            reference = lab.load_chart(reference_path)
            reference["chords"][0]["label"] = "Cmystery"
            lab.write_json(reference_path, reference)
            with patch.object(nnls_chroma_adapter, "extract") as extract, patch.object(chart_aligner, "align") as align:
                report = comparison.run(suite, folder / "comparison")
            extract.assert_not_called()
            align.assert_not_called()
            self.assertEqual(report["excluded_cases"], 1)
            self.assertEqual(report["paired_successful_cases"], 0)
            self.assertEqual(report["cases"][0]["status"], "excluded")
            self.assertIn("Unsupported", report["cases"][0]["reason"])

    def test_complete_suite_is_protected_from_cross_case_output_aliases_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            suite, _, reference_path = fixture_suite(folder)
            # This unused auxiliary file must be protected too, not only the
            # first case's audio/reference pair.
            other_input = suite / "auxiliary-source.json"
            other_input.write_text("preserve whole-suite input")
            before = other_input.read_bytes()
            output = folder / "comparison"
            directory = output / "cases/fixture"
            directory.mkdir(parents=True)
            alias = directory / "nnls-evidence.json"
            os.link(other_input, alias)
            with self.assertRaisesRegex(ValueError, "alias"):
                comparison.run(suite, output, overwrite=True)
            self.assertFalse((directory / "untimed-input.json").exists())
            self.assertEqual(other_input.read_bytes(), before)
            alias.unlink()
            alias.symlink_to(reference_path)
            with self.assertRaisesRegex(ValueError, "alias"):
                comparison.run(suite, output, overwrite=True)
            self.assertFalse((directory / "untimed-input.json").exists())

    def test_duplicate_ids_escaped_paths_and_existing_results_require_explicit_action(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            suite, _, _ = fixture_suite(folder)
            manifest_path = suite / "manifest.json"
            original = json.loads(manifest_path.read_text())
            changed = copy.deepcopy(original)
            changed["cases"] *= 2
            lab.write_json(manifest_path, changed)
            output = folder / "comparison"
            with self.assertRaisesRegex(ValueError, "IDs collide"):
                comparison.run(suite, output)
            self.assertFalse(output.exists())
            changed = copy.deepcopy(original)
            changed["cases"][0]["reference"] = "../outside.json"
            (folder / "outside.json").write_text("unrelated")
            lab.write_json(manifest_path, changed)
            with self.assertRaisesRegex(ValueError, "inside the suite"):
                comparison.run(suite, output)
            self.assertFalse(output.exists())
            lab.write_json(manifest_path, original)
            output.mkdir()
            (output / "report.json").write_text("prior owner's result")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                comparison.run(suite, output)
            self.assertEqual((output / "report.json").read_text(), "prior owner's result")
            comparison.preflight(suite, output, overwrite=True)

    def test_measurement_wrapper_restores_original_functions_after_error(self):
        original_features, original_evidence = chart_aligner.features, chart_aligner.acoustic_evidence
        with self.assertRaisesRegex(RuntimeError, "inference failed"):
            with comparison.measured_acoustic_calls():
                raise RuntimeError("inference failed")
        self.assertIs(chart_aligner.features, original_features)
        self.assertIs(chart_aligner.acoustic_evidence, original_evidence)

    def test_text_publication_refuses_alias_and_preserves_concurrent_result(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "source.json"
            source.write_text("input")
            target = folder / "output.md"
            os.link(source, target)
            with self.assertRaisesRegex(ValueError, "alias"):
                comparison.write_text_safely(target, "replace", [source], overwrite=True)
            self.assertEqual(source.read_text(), "input")
            target.unlink()
            original_link = os.link

            def concurrent(source_path, target_path):
                Path(target_path).write_text("concurrent owner's result")
                original_link(source_path, target_path)

            with patch.object(comparison.os, "link", side_effect=concurrent):
                with self.assertRaisesRegex(ValueError, "concurrently"):
                    comparison.write_text_safely(target, "replace", [source], overwrite=False)
            self.assertEqual(target.read_text(), "concurrent owner's result")
            self.assertEqual(list(folder.glob(".output.md.*")), [])


if __name__ == "__main__":
    unittest.main()
