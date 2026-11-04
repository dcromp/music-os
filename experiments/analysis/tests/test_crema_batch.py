"""Batch plumbing tests without importing the heavyweight CREMA model."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "candidates"))
import crema_adapter as adapter


class CremaBatchTests(unittest.TestCase):
    def manifest(self, root, reference=None):
        root.mkdir(parents=True, exist_ok=True)
        (root / "audio.wav").write_bytes(b"audio input fixture")
        case = {"id": "song-test", "audio": "audio.wav"}
        if reference is not None:
            case["reference"] = reference
        path = root / "manifest.json"
        path.write_text(json.dumps({"cases": [case]}))
        return path

    def result(self):
        return {"analysis": {"parameters": {}, "runtime_seconds": 1},
                "chords": [{"label": "C", "start_seconds": 0, "end_seconds": 1}]}

    def test_inference_accepts_unannotated_audio_without_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root / "inputs")
            model = object()
            with patch.object(adapter, "load_model", return_value=model), \
                 patch.object(adapter, "analyze", return_value=self.result()) as analyze, \
                 redirect_stdout(io.StringIO()):
                status = adapter.run_batch(manifest, root / "outputs")
            self.assertEqual(status, 0)
            analyze.assert_called_once_with((manifest.parent / "audio.wav").resolve(), "song-test", model=model)
            self.assertTrue((root / "outputs/cases/song-test/crema.json").is_file())
            self.assertFalse((manifest.parent / "reference.json").exists())
            self.assertNotIn("reference", json.loads(manifest.read_text())["cases"][0])

    def test_provided_reference_is_preserved_without_reading_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root / "inputs", "reference.json")
            reference = manifest.parent / "reference.json"
            # An opaque sentinel demonstrates that this adapter never consumes
            # labels to run recognition; it only protects the supplied file.
            reference.write_bytes(b"reference sentinel")
            with patch.object(adapter, "load_model", return_value=object()), \
                 patch.object(adapter, "analyze", return_value=self.result()), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(adapter.run_batch(manifest, root / "outputs"), 0)
            self.assertEqual(reference.read_bytes(), b"reference sentinel")

    def test_provided_reference_outside_inputs_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root / "inputs", "../outside.json")
            (root / "outside.json").write_bytes(b"outside reference")
            with patch.object(adapter, "load_model") as load, self.assertRaisesRegex(ValueError, "Reference is outside"):
                adapter.run_batch(manifest, root / "outputs")
            load.assert_not_called()
            self.assertFalse((root / "outputs").exists())

    def test_prediction_cannot_overwrite_provided_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root, "cases/song-test/crema.json")
            reference = root / "cases/song-test/crema.json"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"keep this reference")
            with patch.object(adapter, "load_model") as load, self.assertRaisesRegex(ValueError, "overwrite a source"):
                adapter.run_batch(manifest, root)
            load.assert_not_called()
            self.assertEqual(reference.read_bytes(), b"keep this reference")

    def test_summary_cannot_overwrite_provided_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.manifest(root, "crema-batch-summary.json")
            reference = root / "crema-batch-summary.json"
            reference.write_bytes(b"keep this summary reference")
            with patch.object(adapter, "load_model") as load, self.assertRaisesRegex(ValueError, "without overwriting sources"):
                adapter.run_batch(manifest, root)
            load.assert_not_called()
            self.assertEqual(reference.read_bytes(), b"keep this summary reference")


if __name__ == "__main__":
    unittest.main()
