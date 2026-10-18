"""Public evidence windows and project-local report building remain diagnostic."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import accompaniment_quality_review as review


def vector(indices):
    result = np.zeros(12)
    result[indices] = 1 / math.sqrt(len(indices))
    return result


def features(times, vectors, silent=None, frame_size=2):
    return {"times": np.array(times, dtype=float), "chroma": np.array(vectors, dtype=float),
            "silent": np.array(silent if silent is not None else [False] * len(times), dtype=bool),
            "parameters": {"frame_size": frame_size, "hop_samples": 1}}


class WindowEvidenceTests(unittest.TestCase):
    def score(self, packet, start=0, end=4, interior_only=False):
        return review.window_evidence(packet, ["E", "Em", "Am"], 4, start, end,
                                      sample_rate_hz=10, interior_only=interior_only)

    def test_duration_weights_and_candidate_scores_preserve_E_Em_Am(self):
        packet = features([0, 1, 3], [vector([4, 8, 11]), vector([4, 7, 11]), vector([9, 0, 4])])
        result = self.score(packet)
        # Midpoint cells have durations .5, 1.5, 2 seconds. E vs Em shares two tones;
        # E/Em vs Am shares one. These hand-derived values are independent fixtures.
        scores = {row["label"]: row["mean_cosine"] for row in result["candidate_scores"]}
        self.assertAlmostEqual(scores["E"], 13 / 24)
        self.assertAlmostEqual(scores["Em"], 5 / 8)
        self.assertAlmostEqual(scores["Am"], 2 / 3)
        self.assertEqual(result["active_evidence_seconds"], 4)
        self.assertEqual(result["triad_ranking"][0]["label"], "Am")
        self.assertEqual(len(result["triad_ranking"]), 24)

    def test_shared_tones_preserve_an_exact_candidate_tie(self):
        result = self.score(features([0], [vector([4, 11])]))
        scores = {row["label"]: row["mean_cosine"] for row in result["candidate_scores"]}
        self.assertAlmostEqual(scores["E"], math.sqrt(2 / 3))
        self.assertEqual(scores["E"], scores["Em"])

    def test_interior_windows_exclude_boundary_smear_instead_of_snapping(self):
        packet = features([0, 1, 2, 3], [vector([4, 8, 11]), vector([4, 7, 11]),
                                       vector([9, 0, 4]), vector([4, 8, 11])], frame_size=10)
        whole = self.score(packet, .75, 2.75)
        interior = self.score(packet, .75, 2.75, True)
        self.assertEqual(whole["active_evidence_seconds"], 2)
        self.assertEqual(interior["active_evidence_seconds"], 1)
        self.assertEqual(interior["boundary_excluded_cell_seconds"], 1)
        self.assertAlmostEqual(interior["candidate_scores"][2]["mean_cosine"], 1)
        self.assertLess(whole["candidate_scores"][2]["mean_cosine"], 1)

    def test_silent_zero_and_too_short_interiors_abstain(self):
        result = self.score(features([0, 2], [vector([4, 8, 11]), np.zeros(12)], [True, False]))
        self.assertEqual(result["active_evidence_seconds"], 0)
        self.assertEqual(result["silent_seconds"], 1)
        self.assertEqual(result["non_silent_zero_evidence_seconds"], 3)
        self.assertIsNone(result["mean_l2_chroma_c_first"])
        self.assertTrue(all(row["mean_cosine"] is None for row in result["candidate_scores"]))
        self.assertEqual(result["triad_ranking"], [])
        short = self.score(features([0], [vector([4, 8, 11])]), 0, .05, True)
        self.assertEqual(short["boundary_excluded_cell_seconds"], .05)
        self.assertEqual(short["active_evidence_seconds"], 0)

    def test_invalid_features_candidates_and_regions_are_rejected(self):
        valid = features([0, 1], [vector([4, 8, 11])] * 2)
        mutations = [("times", [0, float("nan")]), ("times", [1, 0]),
                     ("chroma", [[float("nan")] * 12] * 2), ("chroma", [[1] * 12] * 2),
                     ("chroma", [[-1] + [0] * 11] * 2), ("silent", [1, 0])]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                packet = copy.deepcopy(valid); packet[key] = value
                with self.assertRaises(ValueError): self.score(packet)
        for labels in (["N"], ["X"], ["E", "E"], [], ["nonsense"]):
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                review.window_evidence(valid, labels, 4, 0, 4, sample_rate_hz=10)
        for start, end in ((-1, 2), (1, 1), (0, float("nan")), (0, 5)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.score(valid, start, end)


class ReportBuildTests(unittest.TestCase):
    def workspace(self, directory):
        root = Path(directory).resolve()
        rate, count = 22050, 44100
        audio = root / "audio.wav"
        signal = .2 * np.sin(2 * np.pi * 330 * np.arange(count) / rate)
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
            stream.writeframes((signal * 32767).astype("<i2").tobytes())
        sha = hashlib.sha256(audio.read_bytes()).hexdigest()
        recording = {"id": "synthetic-E", "title": "Synthetic fixture", "sample_rate_hz": rate,
                     "duration_seconds": 2.0, "audio_sha256": sha}
        chart = {"schema_version": "1.0", "recording": recording,
                 "analysis": {"id": "fixture", "algorithm": "synthetic fixture", "version": "1", "runtime_seconds": 0},
                 "chords": [{"start_seconds": 0, "end_seconds": 2, "label": "E"}]}
        for name in ("primary", "btc", "chordino"):
            (root / f"{name}.json").write_text(json.dumps(chart))
        times = (np.arange(0, count, 2048) / rate).tolist()
        # A known symbolic packet exercises packet identity/validation without a
        # native host. It is explicitly a fixture, not extracted audio evidence.
        metadata = {"plugin": "nnls-chroma:nnls-chroma", "output": "chroma", "plugin_version": 5,
                    "sample_rate_hz": rate, "frames": count, "hop_size": 2048, "block_size": 16384,
                    "timestamp_method": "ShiftData", "timestamp_adjustment_seconds": 0,
                    "window": "Hann", "timestamp_semantics": "analysis window center",
                    "native_bin_names": review.pitch.nnls.NATIVE_BINS,
                    "parameters": review.pitch.nnls.FROZEN_PARAMETERS}
        evidence = {"schema_version": review.pitch.nnls.SCHEMA,
                    "recording": dict(recording, sample_count=count),
                    "analysis": {"id": "nnls-chroma-frozen-v1", "algorithm": "NNLS-Chroma acoustic evidence",
                                 "offline": True, "global_tuning": True, "no_chart_or_reference_consumed": True,
                                 "native_host": metadata, "silence": {"threshold": .01}},
                    "pitch_classes": review.pitch.nnls.PITCH_CLASSES, "times_seconds": times,
                    "chroma_c_first": [vector([4, 8, 11]).tolist()] * len(times),
                    "raw_chroma_l2": [1] * len(times), "rms": [.1] * len(times), "silent": [False] * len(times)}
        (root / "nnls.json").write_text(json.dumps(evidence))
        case = {"recording_id": recording["id"], "audio": "audio.wav", "primary": "primary.json",
                "btc": "btc.json", "chordino": "chordino.json", "nnls": "nnls.json",
                "regions": [{"id": "quality", "start_seconds": .1, "end_seconds": 1.9,
                             "candidates": ["E", "Em", "Am"]}]}
        spec = root / "spec.json"
        spec.write_text(json.dumps({"schema_version": review.SPEC_SCHEMA, "cases": [case],
                                    "inputs": {"audio.wav": sha}}))
        return root, spec, root / "new" / "report.json"

    def test_complete_build_preserves_inputs_and_retains_diagnostic_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec, output = self.workspace(directory)
            original = {path: path.read_bytes() for path in root.iterdir()}
            report = review.run(spec, output, root)
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertEqual({path: path.read_bytes() for path in original}, original)
            self.assertFalse(report["gold"])
            self.assertIsNone(report["human_correction_seconds"])
            self.assertGreaterEqual(report["agent_processing_seconds"], 0)
            case = report["cases"][0]
            self.assertFalse(case["accepted_arrangement"])
            self.assertFalse(case["physical_timing_verified"])
            self.assertIsNone(case["accuracy_score"])
            region = case["regions"][0]
            self.assertEqual(region["model_overlaps"]["primary"][0]["label"], "E")
            self.assertAlmostEqual(region["model_overlaps"]["primary"][0]["overlap_seconds"], 1.8)
            scores = region["features"]["nnls"]["interior_only"]["candidate_scores"]
            self.assertAlmostEqual(scores[0]["mean_cosine"], 1)

    def test_existing_outputs_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec, output = self.workspace(directory)
            output.parent.mkdir(); output.write_text("keep")
            with self.assertRaises(ValueError): review.run(spec, output, root)
            self.assertEqual(output.read_text(), "keep")

    def test_recording_identity_hash_rate_duration_and_id_must_match(self):
        for field, value in (("audio_sha256", "0" * 64), ("sample_rate_hz", 44100),
                             ("duration_seconds", 2.0001), ("id", "other")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root, spec, output = self.workspace(directory)
                path = root / "btc.json"; chart = json.loads(path.read_text())
                chart["recording"][field] = value; path.write_text(json.dumps(chart))
                with self.assertRaises(ValueError): review.run(spec, output, root)
                self.assertFalse(output.exists())

    def test_unsafe_or_mismatched_inputs_and_paths_are_rejected(self):
        for mutation in ("source-alias", "parent-alias", "outside-output", "bad-pin", "invalid-evidence", "bad-region"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root, spec, output = self.workspace(directory)
                config = json.loads(spec.read_text())
                if mutation == "source-alias":
                    (root / "alias.json").symlink_to(root / "btc.json")
                    config["cases"][0]["btc"] = "alias.json"
                elif mutation == "parent-alias":
                    (root / "alias").symlink_to(root, target_is_directory=True)
                    config["cases"][0]["btc"] = "alias/btc.json"
                elif mutation == "outside-output":
                    output = root.parent / "forbidden-review-output.json"
                elif mutation == "bad-pin":
                    config["inputs"]["audio.wav"] = "0" * 64
                elif mutation == "invalid-evidence":
                    path = root / "nnls.json"; packet = json.loads(path.read_text())
                    packet["chroma_c_first"][0][0] = float("nan"); path.write_text(json.dumps(packet))
                else:
                    config["cases"][0]["regions"][0]["end_seconds"] = 3
                spec.write_text(json.dumps(config))
                with self.assertRaises(ValueError): review.run(spec, output, root)
                self.assertFalse(output.exists())

    def test_input_change_before_publication_aborts_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec, output = self.workspace(directory)
            original_read = Path.read_bytes
            spec_reads = 0
            def filesystem_read(path):
                nonlocal spec_reads
                if path == spec:
                    spec_reads += 1
                    if spec_reads == 2:
                        spec.write_text('{"concurrent": "edit"}')
                return original_read(path)
            with patch.object(Path, "read_bytes", filesystem_read), self.assertRaisesRegex(ValueError, "Inputs changed"):
                review.run(spec, output, root)
            self.assertFalse(output.exists())
            self.assertEqual(spec.read_text(), '{"concurrent": "edit"}')

    def test_two_recording_cases_are_kept_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec, output = self.workspace(directory)
            config = json.loads(spec.read_text())
            second = copy.deepcopy(config["cases"][0])
            second["recording_id"] = "synthetic-E-second"
            for name in ("primary", "btc", "chordino", "nnls"):
                packet = json.loads((root / second[name]).read_text())
                packet["recording"]["id"] = second["recording_id"]
                second[name] = f"{name}-second.json"
                (root / second[name]).write_text(json.dumps(packet))
            config["cases"].append(second)
            spec.write_text(json.dumps(config))
            report = review.run(spec, output, root)
            self.assertEqual([case["recording"]["id"] for case in report["cases"]],
                             ["synthetic-E", "synthetic-E-second"])


if __name__ == "__main__":
    unittest.main()
