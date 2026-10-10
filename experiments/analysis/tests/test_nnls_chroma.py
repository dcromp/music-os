import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "candidates"))
import nnls_chroma_adapter as nnls


def native_metadata(rate=22050, count=6144):
    return {"plugin": "nnls-chroma:nnls-chroma", "output": "chroma", "plugin_version": 5,
            "sample_rate_hz": rate, "frames": count, "hop_size": 2048, "block_size": 16384,
            "timestamp_method": "ShiftData", "timestamp_adjustment_seconds": 0,
            "window": "Hann", "timestamp_semantics": "analysis window center",
            "native_bin_names": nnls.NATIVE_BINS, "parameters": nnls.FROZEN_PARAMETERS}


def native_text(metadata=None, times=None, vectors=None):
    metadata = metadata or native_metadata()
    times = times if times is not None else [index * 2048 / 22050 for index in range(3)]
    vectors = vectors if vectors is not None else [list(range(12)) for _ in times]
    return "# " + json.dumps(metadata) + "\n" + "\n".join(
        "\t".join([f"{timestamp:.9f}", *map(str, vector)]) for timestamp, vector in zip(times, vectors)
    )


def minimal_evidence():
    times = [index * 2048 / 22050 for index in range(3)]
    return {"schema_version": nnls.SCHEMA,
            "recording": {"id": "test", "title": "test", "duration_seconds": 6144 / 22050,
                          "sample_rate_hz": 22050, "sample_count": 6144, "audio_sha256": "0" * 64},
            "analysis": {"id": "nnls-chroma-frozen-v1", "algorithm": "NNLS-Chroma acoustic evidence",
                         "offline": True, "global_tuning": True, "native_host": native_metadata(),
                         "silence": {"threshold": 0.01}, "no_chart_or_reference_consumed": True},
            "pitch_classes": nnls.PITCH_CLASSES, "times_seconds": times,
            "chroma_c_first": [[0.0] * 12, [1.0] + [0.0] * 11, [1.0] + [0.0] * 11],
            "raw_chroma_l2": [0.0, 1.0, 1.0], "rms": [0.0, 0.2, 0.2], "silent": [True, False, False]}


class NativeParserTests(unittest.TestCase):
    def test_native_order_rotates_a_first_to_c_first(self):
        times, vectors, metadata = nnls.parse_native(native_text(), 22050, 6144)
        np.testing.assert_allclose(times, np.arange(3) * 2048 / 22050, atol=1e-9)
        np.testing.assert_array_equal(vectors[0], [3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1, 2])
        self.assertEqual(metadata["timestamp_adjustment_seconds"], 0)

    def test_centers_reject_half_window_offset_missing_and_duplicate_frames(self):
        times = np.arange(3) * 2048 / 22050
        for wrong in (times + 8192 / 22050, times[:2], [times[0], times[0], times[2]]):
            with self.subTest(times=wrong), self.assertRaises(ValueError):
                nnls.parse_native(native_text(times=wrong), 22050, 6144)

    def test_frozen_plugin_metadata_cannot_silently_change(self):
        for key, value in (("hop_size", 1024), ("block_size", 4096), ("timestamp_method", "NoShift"),
                           ("native_bin_names", nnls.PITCH_CLASSES), ("output", "simplechord")):
            metadata = copy.deepcopy(native_metadata())
            metadata[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                nnls.parse_native(native_text(metadata=metadata), 22050, 6144)

    def test_parameter_changes_rejected(self):
        for name, value in (("useNNLS", 0), ("s", float("nan")), ("extra", 1)):
            metadata = copy.deepcopy(native_metadata())
            metadata["parameters"][name] = value
            with self.subTest(name=name), self.assertRaises(ValueError):
                nnls.parse_native(native_text(metadata=metadata), 22050, 6144)

    def test_invalid_native_activations_rejected(self):
        for vector in ([0] * 11, [float("nan")] + [0] * 11, [-1] + [0] * 11):
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                nnls.parse_native(native_text(vectors=[vector] * 3), 22050, 6144)
        with self.assertRaises(ValueError):
            nnls.parse_native(native_text() + "\n# {}", 22050, 6144)

    def test_pcm_rms_centers_and_full_zero_padded_denominator(self):
        signal = np.ones(16)
        times = np.array([0, 0.5, 0.9375])
        actual = nnls.centered_rms(signal, times, 16, 8)
        np.testing.assert_allclose(actual, [np.sqrt(4 / 8), 1, np.sqrt(5 / 8)])


class EvidenceTests(unittest.TestCase):
    def test_valid_evidence_and_silence_are_separate(self):
        evidence = minimal_evidence()
        nnls.validate_evidence(evidence)
        self.assertTrue(evidence["silent"][0])
        self.assertEqual(sum(evidence["chroma_c_first"][0]), 0)

    def test_corrupt_evidence_rejected(self):
        modifications = [lambda e: e["times_seconds"].__setitem__(0, 0.01),
                         lambda e: e["chroma_c_first"][1].__setitem__(0, 2),
                         lambda e: e["silent"].__setitem__(0, False),
                         lambda e: e["raw_chroma_l2"].__setitem__(1, float("inf")),
                         lambda e: e["analysis"]["native_host"].__setitem__("hop_size", 1024),
                         lambda e: e["recording"].__setitem__("audio_sha256", "bad"),
                         lambda e: e["analysis"].__setitem__("global_tuning", False),
                         lambda e: e["analysis"].__setitem__("offline", False),
                         lambda e: e["analysis"].__setitem__("algorithm", "label expansion"),
                         lambda e: e["raw_chroma_l2"].__setitem__(0, 1),
                         lambda e: e["recording"].__setitem__("sample_count", 22050 * 601)]
        for mutate in modifications:
            evidence = copy.deepcopy(minimal_evidence())
            mutate(evidence)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                nnls.validate_evidence(evidence)

    def test_audio_hash_pairing_rejects_another_file(self):
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "silence.wav"
            with wave.open(str(audio), "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(22050)
                target.writeframes(np.zeros(6144, dtype="<i2").tobytes())
            evidence = minimal_evidence()
            with self.assertRaisesRegex(ValueError, "does not match"):
                nnls.validate_evidence(evidence, audio)
            evidence["recording"]["audio_sha256"] = nnls.sha(audio)
            nnls.validate_evidence(evidence, audio)

    def test_missing_and_malformed_packet_fields_are_value_errors(self):
        for bad in ({"schema_version": nnls.SCHEMA},
                    {**minimal_evidence(), "analysis": None},
                    {**minimal_evidence(), "recording": {"sample_rate_hz": "wrong"}}):
            with self.subTest(packet=bad), self.assertRaises(ValueError):
                nnls.validate_evidence(bad)

    def test_publication_rejects_input_aliases_and_creates_complete_json(self):
        with tempfile.TemporaryDirectory() as folder:
            audio, output = Path(folder) / "audio.wav", Path(folder) / "evidence.json"
            audio.write_bytes(b"protected input")
            with patch.object(nnls, "extract", return_value=minimal_evidence()) as inference:
                with self.assertRaises(ValueError):
                    nnls.extract_to_file(audio, "test", audio)
                inference.assert_not_called()
                nnls.extract_to_file(audio, "test", output)
                self.assertEqual(json.loads(output.read_text()), minimal_evidence())
                with self.assertRaises(ValueError):
                    nnls.extract_to_file(audio, "test", output)
                output.unlink()
                output.hardlink_to(audio)
                with self.assertRaises(ValueError):
                    nnls.extract_to_file(audio, "test", output)
            self.assertEqual(audio.read_bytes(), b"protected input")

    @unittest.skipUnless((nnls.ROOT / "experiments/candidate-assets/nnls-chroma-evidence-native/nnls-chroma-host").exists(),
                         "separate native NNLS acoustic host not built")
    def test_real_native_extraction_preserves_clock_hash_and_zero_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            rate, count = 22050, 44100
            audio = Path(folder) / "C-triad.wav"
            time = np.arange(count) / rate
            signal = sum(np.sin(2 * np.pi * frequency * time) for frequency in (261.625565, 329.627557, 391.995436)) / 5
            signal[:rate // 2] = 0
            signal[-rate // 2:] = 0
            with wave.open(str(audio), "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(rate)
                target.writeframes((signal * 32767).astype("<i2").tobytes())
            evidence = nnls.extract(audio, "native-C-triad-test")
            nnls.validate_evidence(evidence, audio)
            self.assertEqual(evidence["recording"]["audio_sha256"], nnls.sha(audio))
            self.assertEqual(evidence["times_seconds"][0], 0)
            np.testing.assert_allclose(evidence["times_seconds"], np.arange(0, count, 2048) / rate, atol=1e-9)
            self.assertTrue(evidence["silent"][0])
            self.assertTrue(evidence["silent"][-1])
            self.assertEqual(evidence["raw_chroma_l2"][0], 0)
            stable = np.array(evidence["chroma_c_first"])[np.argmin(np.abs(np.array(evidence["times_seconds"]) - 1))]
            self.assertGreater(sum(stable[[0, 4, 7]]), sum(stable[[1, 6, 10]]))


if __name__ == "__main__":
    unittest.main()
