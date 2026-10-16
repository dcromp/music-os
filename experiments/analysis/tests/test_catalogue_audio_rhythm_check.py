"""PCM clocks, energy distinctions and isolation of descriptive rhythm outputs."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_audio_rhythm_check as check


def chart(recording):
    return {"schema_version": "1.0", "recording": recording,
            "analysis": {"id": "declared", "algorithm": "symbolic-fixture", "version": "1", "runtime_seconds": 0, "parameters": {}},
            "chords": [{"start_seconds": 0.0, "end_seconds": 1.5, "label": "C"},
                       {"start_seconds": 1.5, "end_seconds": 3.0, "label": "G"}]}


class AudioRhythmCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = check.synthetic_controls()

    def test_silence_has_no_transients_or_energy_and_preserves_sample_clock(self):
        features = check.signal_features(np.zeros(22050))
        self.assertEqual(features["attack_times_seconds"], [])
        np.testing.assert_array_equal(features["rms"], 0)
        np.testing.assert_allclose(features["times"], np.arange(len(features["times"])) * 128 / 22050)
        self.assertLess(features["times"][-1], 1)

    def test_sharp_same_chord_attacks_have_known_clock_but_extras_are_visible(self):
        row = self.controls["cases"][0]
        self.assertEqual(row["score"]["matched"], 8)
        self.assertLess(row["score"]["maximum_absolute_error_seconds"], .004)
        self.assertGreater(row["score"]["extras"], 0)
        self.assertLess(row["score"]["f1"], 1)
        self.assertIn("not suitable", self.controls["detector_status"])

    def test_eighth_swing_and_soft_attack_controls_retain_failures(self):
        rows = {row["id"]: row for row in self.controls["cases"]}
        self.assertEqual(rows["eighth-attacks-same-harmony"]["score"]["matched"], 16)
        self.assertGreater(rows["swung-pair-attacks"]["score"]["extras"], 0)
        self.assertLess(rows["slow-attack-limitation"]["score"]["matched"], 8)
        self.assertTrue(all(row["score"]["detected_attacks"] == len(row["detected_attack_times_seconds"]) for row in rows.values()))

    def test_explicit_damp_and_skipped_attack_have_different_energy(self):
        ringing, damped = self.controls["energy_controls"]
        self.assertEqual(ringing["reference_attack_times_seconds"], damped["reference_attack_times_seconds"])
        self.assertIsNone(ringing["reference_damp_seconds"])
        self.assertEqual(damped["reference_damp_seconds"], 1.5)
        self.assertGreater(ringing["energy"]["after_over_before_rms"], .9)
        self.assertEqual(damped["energy"]["after_over_before_rms"], 0)
        self.assertIn("not an identified guitar mute", damped["energy"]["semantics"])

    def test_shifted_clock_fails_even_when_attack_count_and_spacing_match(self):
        score = self.controls["shifted_clock_negative_control"]["score"]
        self.assertEqual(score["reference_attacks"], score["detected_attacks"])
        self.assertEqual(score["matched"], 0)
        self.assertEqual(score["f1"], 0)

    def test_attack_matching_is_one_to_one_and_keeps_signed_native_error(self):
        score = check.match_attacks([1, 1.4], [.7, 1.05, 1.4], .5)
        self.assertEqual(score["matched"], 2)
        self.assertEqual([row["detected_seconds"] for row in score["pairs"]], [1.05, 1.4])
        self.assertAlmostEqual(score["pairs"][0]["signed_error_seconds"], .05)
        self.assertEqual(check.nearest_attack(1, [.7, 1.3])["nearest_attack_seconds"], .7)
        self.assertAlmostEqual(check.nearest_attack(1, [1.3])["attack_minus_native_seconds"], .3)

    def test_phase_histogram_does_not_fit_offset_or_force_a_meter(self):
        straight = check.phase_inventory([.5, .75, 1, 1.25], [.5, 1, 1.5])
        shifted = check.phase_inventory([.6, .85, 1.1, 1.35], [.5, 1, 1.5])
        self.assertEqual(sum(straight["phase_counts"]), 4)
        self.assertEqual(straight["phase_counts"][0], 2)
        self.assertEqual(straight["phase_counts"][6], 2)
        self.assertNotEqual(straight["phase_counts"], shifted["phase_counts"])
        self.assertIn("no swing", straight["semantics"])

    def test_energy_edge_geometry_remains_bounded_and_empty_side_unscored(self):
        features = check.signal_features(np.ones(22050) * .1)
        first = check.energy_change(features, 0)
        last = check.energy_change(features, 1)
        self.assertIsNone(first["before_rms"]); self.assertIsNone(first["after_over_before_rms"])
        self.assertIsNone(last["after_rms"]); self.assertIsNone(last["after_over_before_rms"])
        self.assertEqual(first["before_window_seconds"], [0.0, 0.0])
        self.assertEqual(last["after_window_seconds"], [1.0, 1.0])

    def test_invalid_clock_signal_and_window_inputs_reject(self):
        for signal, rate in (([], 22050), ([[0]], 22050), ([np.nan], 22050), ([0], 44100)):
            with self.subTest(signal=signal, rate=rate), self.assertRaises(ValueError): check.signal_features(signal, rate)
        for first, second in (([1, 1], []), ([np.inf], []), ([-1], []), ([2, 1], [])):
            with self.assertRaises(ValueError): check.match_attacks(first, second)
        for pulses in ([], [1], [1, 1], [2, 1], [False, 1]):
            with self.assertRaises(ValueError): check.phase_inventory([], pulses)
        features = check.signal_features(np.zeros(22050))
        for start, end in ((-1, .2), (.5, .5), (.5, 2), (False, .5)):
            with self.assertRaises(ValueError): check.window_diagnostics(features, start, end)

    def test_pcm_synthesis_is_seeded_and_not_silently_rescaled(self):
        first = check.plucked_pcm([.5, 1], duration=2, noise=.0005)
        second = check.plucked_pcm([.5, 1], duration=2, noise=.0005)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.dtype, np.dtype("<i2"))
        self.assertEqual(len(first), 44100)

    def test_repeated_attacks_do_not_manufacture_chord_changes_or_accept_rhythm(self):
        pcm = check.plucked_pcm([.5, 1, 2, 2.5], duration=3)
        features = check.signal_features(pcm.astype(float) / 32768)
        recording = {"id": "declared", "title": "Declared PCM", "duration_seconds": 3.0, "sample_rate_hz": 22050, "audio_sha256": "a"*64}
        primary = chart(recording); before = copy.deepcopy(primary)
        pulse = {"pulse_bpm": 120, "beat_times_seconds": [.5, 1, 1.5, 2, 2.5], "analysis": {"config_status": "fixture"}}
        result = check.summarize_recording({"id": "declared", "name": "Declared PCM", "recording": recording}, primary, copy.deepcopy(primary), {"points": []}, pulse, features)
        self.assertGreater(result["full_mix_attacks"], 4)
        self.assertEqual(len(result["native_boundaries"]["btc"]["native_events"]), 1)
        self.assertEqual(result["native_boundaries"]["btc"]["native_events"][0]["time_seconds"], 1.5)
        self.assertEqual(primary, before); self.assertFalse(result["accepted_rhythm"])
        self.assertIsNone(result["physical_timing_accuracy"]); self.assertIsNone(result["guitar_attack_accuracy"])

    @contextmanager
    def small_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve(); pack = base/"pack"; folder = pack/"cases/declared"; folder.mkdir(parents=True)
            pcm = check.plucked_pcm([.5, 1, 2], duration=3)
            with wave.open(str(folder/"audio.wav"), "wb") as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(22050); stream.writeframes(pcm.tobytes())
            recording = {"id": "declared", "title": "Declared PCM", "duration_seconds": 3.0, "sample_rate_hz": 22050, "audio_sha256": check.digest(folder/"audio.wav")}
            case = {"id": "declared", "name": "Declared PCM", "recording": recording}
            def write(path, value): path.write_text(json.dumps(value)+"\n")
            write(pack/"manifest.json", {"cases": [case]})
            write(folder/"primary.json", chart(recording)); write(folder/"crema.json", chart(recording)); write(folder/"review.json", {"points": []})
            private = pack/"private-drafts/declared.json"; private.parent.mkdir(); write(private, {"retained": "draft"})
            learner = base/"learner.json"; config = base/"config.json"; practice = base/"practice.json"
            for path in (learner, config, practice): write(path, {})
            pulses = base/"pulses.json"
            write(pulses, {"schema_version": check.rhythm_grid.SCHEMA, "manifest_sha256": check.digest(learner), "config_sha256": check.digest(config),
                          "cases": [{"recording": recording, "pulse_bpm": 120, "beat_times_seconds": [.5, 1, 1.5, 2, 2.5], "analysis": {"library_version": "declared", "config_status": "declared"}}]})
            targets = base/"timing.json"; write(targets, {"schema_version": "catalogue-change-check-1.0", "cases": [{"id": "declared", "recording": recording, "source_guided_hold_candidates": [], "boundary_review": {"selected_review_windows": []}}]})
            spec = base/"spec.json"; write(spec, check.make_spec(pack, pulses, learner, config, practice, targets))
            files = {str(p): p for p in [pack/"manifest.json", *folder.iterdir()]}
            with patch.object(check.curation, "public_files", return_value=(files, {"cases": [case]})):
                yield {"base": base, "pack": pack, "folder": folder, "pulses": pulses, "learner": learner, "config": config,
                       "practice": practice, "spec": spec, "targets": targets, "output": base/"output", "private": private}

    def run_small(self, values):
        # The filesystem root permits real method files plus an isolated /tmp
        # fixture; production defaults require every input under repository root.
        return check.run(values["pack"], values["pulses"], values["learner"], values["config"], values["practice"], values["spec"], values["output"], root=Path("/"), timing_review=values["targets"])

    def test_runner_preserves_native_private_bytes_and_refuses_output_reuse(self):
        with self.small_workspace() as values:
            before = {p: p.read_bytes() for p in values["base"].rglob("*") if p.is_file()}
            result = self.run_small(values)
            self.assertEqual({p: p.read_bytes() for p in before}, before)
            self.assertFalse(result["raw_charts_modified"]); self.assertFalse(result["private_drafts_modified"])
            self.assertFalse(result["gold"]); self.assertIsNone(result["human_correction_seconds"])
            self.assertIn("not suitable", result["detector_status"])
            with self.assertRaisesRegex(ValueError, "unused output"): self.run_small(values)

    def test_concurrent_input_or_private_mutation_is_retained_and_aborts_publish(self):
        for target in ("spec", "pulses", "private", "new-private", "delete-private"):
            with self.subTest(target=target), self.small_workspace() as values:
                original = check.summarize_recording
                def mutate(*args):
                    result = original(*args)
                    if target == "delete-private": values["private"].unlink()
                    else:
                        path = values["private"].with_name("concurrent.json") if target == "new-private" else values[target]
                        path.write_text('{"concurrent":"retained"}\n')
                    return result
                with patch.object(check, "summarize_recording", side_effect=mutate), self.assertRaisesRegex(ValueError, "Inputs or saved drafts changed"):
                    self.run_small(values)
                self.assertFalse(values["output"].exists())
                self.assertFalse(list(values["base"].glob(".audio-rhythm-*")))

    def test_stale_native_chart_target_and_private_symlink_reject_before_analysis(self):
        with self.small_workspace() as values:
            packet = json.loads(values["targets"].read_text())
            packet["cases"][0]["native_artifacts"] = {"primary_sha256": "f"*64, "crema_sha256": "e"*64}
            values["targets"].write_text(json.dumps(packet))
            spec = check.make_spec(values["pack"], values["pulses"], values["learner"], values["config"], values["practice"], values["targets"])
            values["spec"].write_text(json.dumps(spec))
            with patch.object(check, "signal_features", side_effect=AssertionError("Preflight must reject first")), self.assertRaisesRegex(ValueError, "chart artifacts"):
                self.run_small(values)
            self.assertFalse(values["output"].exists())
        with self.small_workspace() as values:
            values["private"].unlink(); values["private"].symlink_to(values["practice"])
            with patch.object(check, "signal_features", side_effect=AssertionError("Preflight must reject first")), self.assertRaisesRegex(ValueError, "non-symlink"):
                self.run_small(values)
            self.assertFalse(values["output"].exists())


if __name__ == "__main__": unittest.main()
