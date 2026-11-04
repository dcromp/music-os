import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rhythm_grid as rhythm


def write_json(path, value):
    path.write_text(json.dumps(value))


def fixture(folder, ids=("first-song",)):
    pack = folder / "pack"
    pack.mkdir()
    rows = []
    settings = {}
    for identifier in ids:
        directory = pack / "cases" / identifier
        directory.mkdir(parents=True)
        audio = directory / "audio.wav"
        write_wave(audio)
        rows.append({"id": identifier, "audio_url": f"/cases/{identifier}/audio.wav",
                     "recording": {"id": identifier, "title": "Fixture song", "sample_rate_hz": 22050,
                                   "duration_seconds": 4., "audio_sha256": rhythm.digest(audio)}})
        settings[identifier] = {"start_bpm": 93, "beats_per_bar": 4, "meter_label": "4/4",
                                "meter_status": "unverified source-informed proposal"}
    manifest = pack / "manifest.json"
    config = folder / "config.json"
    write_json(manifest, {"schema_version": "automatic-drafts-1.0", "pack_id": "test-pack", "cases": rows})
    write_json(config, {"schema_version": rhythm.CONFIG_SCHEMA, "recordings": settings})
    return manifest, config, folder / "rhythm.json"


def write_wave(path, *, rate=22050, channels=1, sample_width=2):
    with wave.open(str(path), "wb") as stream:
        stream.setframerate(rate)
        stream.setnchannels(channels)
        stream.setsampwidth(sample_width)
        stream.writeframes(b"\0" * rate * 4 * channels * sample_width)


def good_prediction():
    return {"pulse_bpm": 92.28515625, "beat_times_seconds": [.18575963718820862, .8359183673469388, 1.486077097505668, 2.136235827664397],
            "library_version": "test-library"}


class RhythmGridTests(unittest.TestCase):
    def test_output_preserves_native_clock_exact_identity_and_proposal_status(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            original = manifest.read_bytes()
            with patch.object(rhythm, "track_audio", return_value=good_prediction()) as tracker:
                result = rhythm.build(manifest, config, output)
            self.assertEqual(result["schema_version"], "playalong-rhythm-1.0")
            self.assertEqual(result, json.loads(output.read_text()))
            self.assertEqual(manifest.read_bytes(), original)
            self.assertEqual(result["manifest_sha256"], hashlib.sha256(original).hexdigest())
            self.assertFalse(result["gold"])
            row = result["cases"][0]
            self.assertEqual(row["beat_times_seconds"], good_prediction()["beat_times_seconds"])
            self.assertEqual(row["status"], "estimated")
            self.assertEqual(row["beats_per_bar"], 4)
            self.assertEqual(row["analysis"]["parameters"]["hop_samples"], 512)
            self.assertEqual(row["analysis"]["config_status"], "unverified source-informed proposal")
            self.assertFalse(row["analysis"]["downbeats_inferred"])
            self.assertFalse(row["analysis"]["chord_boundaries_snapped"])
            self.assertNotIn("downbeats_seconds", row)
            tracker.assert_called_once()

    def test_compound_two_pulses_and_unresolved_meter_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory), ids=("compound", "unresolved"))
            packet = json.loads(config.read_text())
            packet["recordings"]["compound"].update(beats_per_bar=2, meter_label="6/8", pulse_unit="dotted quarter")
            packet["recordings"]["unresolved"].update(beats_per_bar=None, meter_label="4/4 + 2/4")
            write_json(config, packet)
            with patch.object(rhythm, "track_audio", return_value=good_prediction()):
                result = rhythm.build(manifest, config, output)
            self.assertEqual(result["cases"][0]["beats_per_bar"], 2)
            self.assertEqual(result["cases"][0]["analysis"]["config"]["pulse_unit"], "dotted quarter")
            self.assertIsNone(result["cases"][1]["beats_per_bar"])

    def test_invalid_waveform_hash_fails_before_any_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory), ids=("valid", "invalid"))
            packet = json.loads(manifest.read_text())
            packet["cases"][1]["recording"]["audio_sha256"] = "f" * 64
            write_json(manifest, packet)
            with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "SHA-256"):
                rhythm.build(manifest, config, output)
            tracker.assert_not_called()
            self.assertFalse(output.exists())

    def test_bad_audio_format_fails_before_tracking(self):
        for fields in ({"channels": 2}, {"sample_width": 1}, {"rate": 44100}):
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as directory:
                manifest, config, output = fixture(Path(directory))
                audio = manifest.parent / "cases/first-song/audio.wav"
                write_wave(audio, **fields)
                packet = json.loads(manifest.read_text())
                packet["cases"][0]["recording"]["audio_sha256"] = rhythm.digest(audio)
                write_json(manifest, packet)
                with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "PCM16"):
                    rhythm.build(manifest, config, output)
                tracker.assert_not_called()

    def test_declared_duration_must_match_to_one_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            packet = json.loads(manifest.read_text())
            packet["cases"][0]["recording"]["duration_seconds"] = 3.9
            write_json(manifest, packet)
            with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "duration"):
                rhythm.build(manifest, config, output)
            tracker.assert_not_called()

    def test_missing_extra_and_duplicate_case_configuration_are_rejected(self):
        for kind in ("missing", "extra", "duplicate_case", "recording_id", "unsafe_id", "escaped_audio_url"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                manifest, config, output = fixture(Path(directory))
                packet, settings = json.loads(manifest.read_text()), json.loads(config.read_text())
                if kind == "missing": settings["recordings"] = {}
                elif kind == "extra": settings["recordings"]["extra"] = settings["recordings"]["first-song"]
                elif kind == "duplicate_case": packet["cases"].append(packet["cases"][0])
                elif kind == "recording_id": packet["cases"][0]["recording"]["id"] = "different"
                elif kind == "unsafe_id": packet["cases"][0]["id"] = "../escape"
                else: packet["cases"][0]["audio_url"] = "/cases/first-song/../../audio.wav"
                write_json(manifest, packet)
                write_json(config, settings)
                with patch.object(rhythm, "track_audio") as tracker, self.assertRaises(ValueError):
                    rhythm.build(manifest, config, output)
                tracker.assert_not_called()

    def test_invalid_config_values_and_schema_rejected_before_inference(self):
        variants = [{"start_bpm": True}, {"start_bpm": 0}, {"start_bpm": 301}, {"beats_per_bar": True},
                    {"beats_per_bar": 3}, {"beats_per_bar": 4.0}, {"meter_label": ""}, {"meter_status": ""},
                    {"tempo_min_bpm": 80}, {"tempo_min_bpm": 100, "tempo_max_bpm": 80},
                    {"tempo_min_bpm": 100, "tempo_max_bpm": 110},
                    {"tempo_min_bpm": 19, "tempo_max_bpm": 100}]
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                manifest, config, output = fixture(Path(directory))
                settings = json.loads(config.read_text())
                settings["recordings"]["first-song"].update(variant)
                write_json(config, settings)
                with patch.object(rhythm, "track_audio") as tracker, self.assertRaises(ValueError):
                    rhythm.build(manifest, config, output)
                tracker.assert_not_called()

    def test_duplicate_json_fields_and_nonfinite_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            config.write_text('{"schema_version":"playalong-rhythm-config-1.0","recordings":{},"recordings":{}}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                rhythm.build(manifest, config, output)
            config.write_text('{"value":NaN}')
            with self.assertRaisesRegex(ValueError, "Nonfinite JSON"):
                rhythm.build(manifest, config, output)

    def test_invalid_pulses_bpm_and_missing_version_rejected(self):
        variants = [{"beat_times_seconds": []}, {"beat_times_seconds": [.2]},
                    {"beat_times_seconds": [.2, .2]}, {"beat_times_seconds": [.3, .2]},
                    {"beat_times_seconds": [-.1, .2]}, {"beat_times_seconds": [.2, 4.]},
                    {"beat_times_seconds": [True, 1.5]}, {"beat_times_seconds": [.2, float("nan")]},
                    {"beat_times_seconds": list(range(5001))}, {"pulse_bpm": 0}, {"pulse_bpm": 301},
                    {"pulse_bpm": True}, {"pulse_bpm": float("inf")}, {"library_version": ""}]
        for variant in variants:
            with self.subTest(variant=variant):
                with self.assertRaises(ValueError):
                    rhythm.validate_pulses({**good_prediction(), **variant}, 4.)

    def test_existing_output_refused_without_inference_and_explicit_overwrite_works(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            output.write_text("keep old output")
            with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "overwrite"):
                rhythm.build(manifest, config, output)
            tracker.assert_not_called()
            self.assertEqual(output.read_text(), "keep old output")
            with patch.object(rhythm, "track_audio", return_value=good_prediction()):
                rhythm.build(manifest, config, output, overwrite=True)
            self.assertEqual(json.loads(output.read_text())["schema_version"], rhythm.SCHEMA)

    def test_partial_batch_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory), ids=("first", "second"))
            output.write_text("existing output")
            with patch.object(rhythm, "track_audio", side_effect=[good_prediction(), ValueError("no pulses")]), \
                    self.assertRaisesRegex(ValueError, "no pulses"):
                rhythm.build(manifest, config, output, overwrite=True)
            self.assertEqual(output.read_text(), "existing output")
            self.assertEqual(list(output.parent.glob(".rhythm.json.*")), [])

    def test_symlink_and_input_hardlink_output_aliases_are_rejected(self):
        for mode in ("symlink", "hardlink", "samefile"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                manifest, config, output = fixture(Path(directory))
                original = manifest.read_bytes()
                if mode == "symlink": output.symlink_to(manifest)
                elif mode == "hardlink": os.link(manifest, output)
                else: output = manifest
                with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "alias"):
                    rhythm.build(manifest, config, output, overwrite=True)
                tracker.assert_not_called()
                self.assertEqual(manifest.read_bytes(), original)

    def test_source_change_during_inference_prevents_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            def tracking(audio, setting):
                with audio.open("r+b") as stream:
                    stream.seek(-2, 2)
                    stream.write(b"\1\0")
                return good_prediction()
            with patch.object(rhythm, "track_audio", side_effect=tracking), self.assertRaisesRegex(ValueError, "Audio changed"):
                rhythm.build(manifest, config, output)
            self.assertFalse(output.exists())

    def test_waveform_symlink_escaping_pack_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            manifest, config, output = fixture(folder)
            audio = manifest.parent / "cases/first-song/audio.wav"
            outside = folder / "outside.wav"
            audio.rename(outside)
            audio.symlink_to(outside)
            with patch.object(rhythm, "track_audio") as tracker, self.assertRaisesRegex(ValueError, "inside"):
                rhythm.build(manifest, config, output)
            tracker.assert_not_called()

    def test_declared_range_prior_excludes_wrong_meter_levels(self):
        prior = rhythm.TempoRangePrior(87, 78, 96)
        scores = prior.logpdf([0, 70, 86.13, 117.45, 172.26, float("inf")])
        self.assertTrue(np.isfinite(scores[2]))
        self.assertTrue(np.isneginf(scores[[0, 1, 3, 4, 5]]).all())

    def test_later_input_change_invalidates_previously_tracked_case(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory), ids=("first", "second"))
            first_audio = manifest.parent / "cases/first/audio.wav"
            def tracking(audio, setting):
                if audio.parent.name == "second":
                    with first_audio.open("r+b") as stream:
                        stream.seek(-2, 2)
                        stream.write(b"\1\0")
                return good_prediction()
            with patch.object(rhythm, "track_audio", side_effect=tracking), self.assertRaisesRegex(ValueError, "after"):
                rhythm.build(manifest, config, output)
            self.assertFalse(output.exists())

    def test_config_change_during_inference_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, config, output = fixture(Path(directory))
            output.write_text("previous complete packet")
            def tracking(audio, setting):
                config.write_text("changed config")
                return good_prediction()
            with patch.object(rhythm, "track_audio", side_effect=tracking), self.assertRaisesRegex(ValueError, "config changed"):
                rhythm.build(manifest, config, output, overwrite=True)
            self.assertEqual(output.read_text(), "previous complete packet")

    def test_lazy_tracker_uses_selected_native_tempo_and_preserves_pulse_times(self):
        fake = types.SimpleNamespace(__version__="mock-0.9.2", load=Mock(return_value=(np.zeros(32), 22050)),
            onset=types.SimpleNamespace(onset_strength=Mock(return_value=np.ones(10))),
            beat=types.SimpleNamespace(tempo=Mock(return_value=np.array([86.1328125])),
                                      beat_track=Mock(return_value=(86.1328125, np.array([.185759637, .882358277])))))
        settings = {"start_bpm": 87, "tempo_min_bpm": 78, "tempo_max_bpm": 96}
        with patch.dict(sys.modules, {"librosa": fake}):
            result = rhythm.track_audio(Path("mock.wav"), settings)
        self.assertEqual(result["beat_times_seconds"], [.185759637, .882358277])
        self.assertEqual(fake.beat.beat_track.call_args.kwargs["bpm"], 86.1328125)
        self.assertEqual(fake.beat.beat_track.call_args.kwargs["units"], "time")
        self.assertTrue(fake.beat.beat_track.call_args.kwargs["trim"])
        self.assertEqual(result["library_version"], "mock-0.9.2")


if __name__ == "__main__":
    unittest.main()
