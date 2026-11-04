import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chart_aligner as frozen
import guarded_aligner as guard
import lab


def ideal_packet(labels, *, frames_per_label=12, hop=25):
    vectors = []
    silent = []
    for label in labels:
        template = frozen.chord_template(label)
        vectors.extend([np.zeros(12) if template is None else template] * frames_per_label)
        silent.extend([label == "N"] * frames_per_label)
    return {"chroma": np.array(vectors), "silent": np.array(silent),
            "rms": np.where(silent, 0, .3), "hop_samples": hop,
            "frame_size": 128, "silence_rms_threshold": .01}


def inputs(folder, sequence, packet, *, extra_samples=0, **fields):
    rate = 1000
    audio = folder / "audio.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(np.zeros(len(packet["chroma"]) * packet["hop_samples"] + extra_samples, dtype="<i2").tobytes())
    chart = {"schema_version": frozen.SCHEMA,
             "recording": {"id": "test", "title": "Independent ideal evidence test",
                           "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest()},
             "sequence": sequence, **fields}
    source = folder / "untimed.json"
    source.write_text(json.dumps(chart))
    return audio, source


def ideal_align(folder, heard, supplied, *, frames_per_label=12, **parameters):
    packet = ideal_packet(heard, frames_per_label=frames_per_label)
    audio, source = inputs(folder, supplied, packet)
    with patch.object(frozen, "features", return_value=packet):
        return guard.align(audio, source, **parameters)


class GuardedAlignerTests(unittest.TestCase):
    def test_silent_intro_cannot_consume_harmonic_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            result = ideal_align(folder, ["N", "C", "G", "Am"], ["C", "G", "Am"], frames_per_label=20)
            columns = result["alignment_evidence"]["frame_columns"]
            frames = result["alignment_evidence"]["frames"]
            self.assertEqual({row[columns.index("sequence_index")] for row in frames[:20]}, {0})
            self.assertEqual(result["alignment_evidence"]["diagnostics"]["silent_position_advance_count"], 0)
            self.assertTrue(result["alignment_evidence"]["diagnostics"]["endpoint_reached"])
            self.assertEqual(result["chords"][0]["label"], "N")
            self.assertEqual([event["label"] for event in result["chords"]], ["N", "C", "G", "Am"])

    def test_all_silence_has_partial_path_not_forced_completed_chart(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["N"], frames_per_label=80)
            audio, source = inputs(folder, ["C", "G", "Am", "F"], packet)
            with patch.object(frozen, "features", return_value=packet):
                control = frozen.align(audio, source)
                result = guard.align(audio, source)
            old = control["alignment_evidence"]["diagnostics"]
            new = result["alignment_evidence"]["diagnostics"]
            self.assertEqual(old["unvisited_sequence_indices"], [])
            self.assertFalse(new["endpoint_reached"])
            self.assertTrue(new["partial"])
            self.assertEqual(new["unvisited_sequence_indices"], [1, 2, 3])
            self.assertEqual(new["silent_position_advance_count"], 0)
            self.assertEqual(new["supplied_positions_without_minimum_evidence_count"], 4)
            self.assertEqual(new["acoustic_fit_status"], "no_active_harmonic_evidence")
            self.assertEqual([event["label"] for event in result["chords"]], ["N"])
            self.assertFalse(new["accepted_for_playback"])

    def test_active_dwell_ignores_silence_and_requires_matched_target(self):
        emissions = np.array([[1., .2]] * 2 + [[0., 0.]] * 10 + [[1., .2]] + [[.2, 1.]] * 4)
        support = emissions > .8
        pause = np.zeros_like(support)
        pause[2:12] = True
        path, _, status = guard.evidence_path(emissions, support, pause,
            minimum_frames=3, terminal_minimum_frames=3, transition_penalty=.12,
            mode="finite", start_policy="first", end_policy="last")
        self.assertEqual(path[:13].tolist(), [0] * 13)
        self.assertEqual(path[13:].tolist(), [1] * 4)
        self.assertTrue(status["endpoint_reached"])

    def test_active_mismatch_resets_supporting_dwell(self):
        emissions = np.array([[1., .2]] * 2 + [[.1, .1]] + [[1., .2]] * 2 + [[.2, 1.]] * 5)
        support = emissions > .8
        path, _, status = guard.evidence_path(emissions, support, np.zeros_like(support),
            minimum_frames=3, terminal_minimum_frames=3, transition_penalty=.12,
            mode="finite", start_policy="first", end_policy="last")
        self.assertFalse(status["endpoint_reached"])
        self.assertEqual(set(path), {0})

    def test_short_final_active_chord_is_partial_and_emits_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["C"], frames_per_label=12)
            final = ideal_packet(["G"], frames_per_label=2)
            for name in ("chroma", "silent", "rms"):
                packet[name] = np.concatenate((packet[name], final[name]))
            audio, source = inputs(folder, ["C", "G"], packet)
            with patch.object(frozen, "features", return_value=packet):
                result = guard.align(audio, source)
            diagnostic = result["alignment_evidence"]["diagnostics"]
            self.assertTrue(diagnostic["partial"])
            self.assertFalse(diagnostic["endpoint_reached"])
            self.assertIn(1, diagnostic["insufficient_active_evidence_sequence_indices"])
            self.assertEqual(result["chords"][-1]["label"], "X")
            self.assertIn("insufficient_active_evidence_dwell", result["chords"][-1]["evidence"]["reasons"])

    def test_correct_rich_qualities_are_retained_on_ideal_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            sequence = ["Em7", "G", "Dsus4", "A7sus4", "Cadd9"]
            result = ideal_align(folder, sequence, sequence)
            self.assertEqual([event["label"] for event in result["chords"]], sequence)
            diagnostic = result["alignment_evidence"]["diagnostics"]
            self.assertEqual(diagnostic["rejected_quality_frames"], 0)
            self.assertEqual(diagnostic["quality_abstention_fraction_of_active_audio"], 0)
            self.assertFalse(diagnostic["arrangement_verified"])
            self.assertFalse(diagnostic["accepted_for_playback"])

    def test_clipped_terminal_interval_does_not_overstate_active_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["C"], frames_per_label=6)
            audio, source = inputs(folder, ["C"], packet, extra_samples=-1)
            with patch.object(frozen, "features", return_value=packet):
                result = guard.align(audio, source)
            diagnostic = result["alignment_evidence"]["diagnostics"]
            self.assertTrue(diagnostic["partial"])
            self.assertFalse(diagnostic["endpoint_reached"])
            self.assertAlmostEqual(diagnostic["position_matched_evidence_seconds"][0], .149)
            self.assertEqual([event["label"] for event in result["chords"]], ["X"])

    def test_plain_audio_with_supplied_extensions_abstains_not_relabels(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ideal_align(Path(directory), ["Em", "C", "A"], ["Em7", "Cadd9", "A7"])
            self.assertTrue(all(event["label"] == "X" for event in result["chords"]))
            proposed = result["alignment_evidence"]["proposed_path_events_before_gap_mask"]
            self.assertEqual([event["label"] for event in proposed], ["Em7", "Cadd9", "A7"])
            self.assertTrue(any("unsupported_added_tones" in event["evidence"]["reasons"] for event in result["chords"]))

    def test_same_root_competing_suspension_rejects_wrong_supplied_plain(self):
        chroma = np.tile(frozen.chord_template("Dsus4"), (12, 1))
        result = guard.quality_evidence(chroma, np.zeros(12, dtype=bool), ["D"],
            quality_margin=.04, added_tone_ratio=.12, added_tone_fraction=.5, support_window_frames=6)
        self.assertTrue(result["same_root_quality_reject"].all())
        self.assertTrue(all(label == "Dsus4" for label in result["same_root_best_label"][:, 0]))
        self.assertFalse(result["added_tone_reject"].any())

    def test_extra_tone_support_fraction_excludes_silence_votes(self):
        chroma = np.tile(frozen.chord_template("Cadd9"), (20, 1))
        silent = np.zeros(20, dtype=bool)
        silent[7:13] = True
        chroma[silent] = 0
        result = guard.quality_evidence(chroma, silent, ["Cadd9"], quality_margin=.04,
            added_tone_ratio=.12, added_tone_fraction=.95, support_window_frames=6)
        self.assertFalse(result["added_tone_reject"].any())
        self.assertTrue(np.allclose(result["added_tone_support_fraction"][~silent], 1))

    def test_explicit_no_chord_and_unknown_keep_distinct_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ideal_align(Path(directory), ["N", "C", "G"], ["N", "X", "G"])
            labels = [event["label"] for event in result["chords"]]
            self.assertEqual(labels, ["N", "X", "G"])
            unknown = next(event for event in result["chords"] if event["label"] == "X")
            self.assertIn("explicit_unknown", unknown["evidence"]["reasons"])

    def test_explicit_no_chord_conflict_outputs_x_and_cannot_mature(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ideal_align(Path(directory), ["C", "G"], ["N", "G"])
            self.assertTrue(result["alignment_evidence"]["diagnostics"]["partial"])
            self.assertTrue(all(event["label"] == "X" for event in result["chords"]))
            self.assertIn("explicit_no_chord_conflicts_with_active_audio", result["chords"][0]["evidence"]["reasons"])

    def test_template_indistinguishable_slash_bass_is_not_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ideal_align(Path(directory), ["A", "A", "Em7"], ["A", "A/G#", "Em7"])
            diagnostic = result["alignment_evidence"]["diagnostics"]
            self.assertIn([0, 1], diagnostic["acoustically_indistinguishable_sequence_position_pairs"])
            self.assertFalse(diagnostic["arrangement_verified"])
            self.assertFalse(diagnostic["accepted_for_playback"])

    def test_section_intervals_do_not_advance_through_silent_intro(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["N", "C", "G", "Am"])
            audio, source = inputs(folder, ["C", "G", "Am"], packet)
            chart = json.loads(source.read_text())
            chart.pop("sequence")
            chart.update(schema_version=frozen.SECTION_SCHEMA,
                sections=[{"id": "verse", "sequence": ["C", "G"]}, {"id": "outro", "sequence": ["Am"]}],
                order=[{"section_id": "verse"}, {"section_id": "outro"}])
            source.write_text(json.dumps(chart))
            with patch.object(frozen, "features", return_value=packet):
                result = guard.align(audio, source)
            sections = result["alignment_evidence"]["section_intervals_from_proposed_path"]
            self.assertEqual([section["section_id"] for section in sections], ["verse", "outro"])
            self.assertGreaterEqual(sections[1]["start_seconds"], .9)
            self.assertEqual(result["alignment_evidence"]["diagnostics"]["zero_active_section_interval_count"], 0)

    def test_recording_hash_untimed_fields_and_output_alias_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["C"])
            audio, source = inputs(folder, ["C"], packet)
            with self.assertRaisesRegex(ValueError, "alias"):
                guard.align_to_file(audio, source, source, overwrite=True)
            chart = json.loads(source.read_text())
            chart["recording"]["audio_sha256"] = "wrong"
            source.write_text(json.dumps(chart))
            with self.assertRaisesRegex(ValueError, "audio_sha256"):
                guard.align(audio, source)
            chart["recording"].pop("audio_sha256")
            chart["metadata"] = {"start_seconds": 0}
            source.write_text(json.dumps(chart))
            with self.assertRaisesRegex(ValueError, "timing field"):
                guard.align(audio, source)

    def test_acoustic_input_cache_provenance_and_no_gold_read(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["C"])
            audio, source = inputs(folder, ["C"], packet)
            evidence_path = folder / "evidence.json"
            evidence_path.write_text("cached acoustic features, not chords")
            provenance = {"backend": "nnls-chroma", "evidence_sha256": "declared-test-digest"}
            with patch.object(frozen, "features", return_value=packet) as feature_call, \
                 patch.object(frozen, "acoustic_evidence", return_value=(packet["chroma"], provenance)) as cached_call, \
                 patch.object(lab, "load_chart", side_effect=AssertionError("Timed gold read")):
                result = guard.align(audio, source, evidence_json=evidence_path)
            feature_call.assert_called_once()
            cached_call.assert_called_once_with(audio, evidence_path, "test", packet, 1000)
            self.assertEqual(result["alignment_evidence"]["acoustic_input"], provenance)
            self.assertEqual(result["alignment_input"]["chart_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertTrue(all("confidence" not in event for event in result["chords"]))

    def test_ambiguous_harte_major_seventh_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "scale-degree 7"):
                ideal_align(Path(directory), ["Dsus4"], ["D:sus4(7)"])

    def test_invalid_parameters_and_bounded_path_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            packet = ideal_packet(["C"])
            audio, source = inputs(folder, ["C"], packet)
            for parameter in ("quality_margin", "added_tone_ratio", "added_tone_fraction"):
                for value in (float("nan"), -1, 1.01, True):
                    with self.subTest(parameter=parameter, value=value), self.assertRaises(ValueError):
                        guard.align(audio, source, **{parameter: value})
        with self.assertRaisesRegex(ValueError, "bounded"):
            guard.evidence_path(np.ones((12, 2)), np.ones((12, 2), dtype=bool), np.zeros((12, 2), dtype=bool),
                minimum_frames=3, terminal_minimum_frames=3, transition_penalty=.12,
                mode="finite", start_policy="first", end_policy="last", max_decoder_cells=10)


if __name__ == "__main__":
    unittest.main()
