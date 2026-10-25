"""Light tests for the instrument stage helpers (plain unittest; no audio, no models, no network).

    .venv-crema/bin/python -m unittest experiments/analysis/strumalong/test_instrument_stage.py
    (or: cd experiments/analysis/strumalong && ../../../.venv-crema/bin/python -m unittest test_instrument_stage)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_homogeneity as hh  # noqa: E402
import stems_6s  # noqa: E402
import strum_features as sf  # noqa: E402
import strumalong_common as sc  # noqa: E402
import yamnet_tags as yt  # noqa: E402


class ChordLabels(unittest.TestCase):
    def test_pitch_classes(self):
        self.assertEqual(sc.chord_pitch_classes("Em7"), [2, 4, 7, 11])
        self.assertEqual(sc.chord_pitch_classes("D6add9"), [2, 4, 6, 9, 11])       # D E F# A B
        self.assertEqual(sc.chord_pitch_classes("Asus4"), [2, 4, 9])                  # A D E
        self.assertIn(6, sc.chord_pitch_classes("D/F#"))                           # slash bass is part of the template
        self.assertEqual(sc.chord_pitch_classes("Cmaj7"), [0, 4, 7, 11])
        self.assertIsNone(sc.chord_pitch_classes("N"))
        self.assertIsNone(sc.chord_pitch_classes("X"))

    def test_family_key_matches_the_js_checker(self):
        for label, key in [("Em7", "Em"), ("Cmaj7", "C"), ("Bsus4", "Bsus"), ("D/F#", "D"), ("F#m7", "F#m"), ("G7", "G"),
                           ("A#", "A#"), ("Fdim", "Fdim"), ("Dmaj7/F#", "D"), ("D6add9", "D")]:
            self.assertEqual(sc.family_key(label), key, label)
        self.assertIsNone(sc.family_key("N"))

    def test_variants(self):
        self.assertIn("D6add9", hh.family_variants("D"))
        self.assertIn("F#m7", hh.family_variants("F#m"))
        self.assertTrue(all(sc.family_key(v) == "A#m" for v in hh.family_variants("A#m")))
        self.assertTrue(all(sc.family_key(v) == "Bsus" for v in hh.family_variants("Bsus")))


class Templates(unittest.TestCase):
    def chroma(self, label, noise=0.0, seed=0):
        v = hh.template_vector(label) + noise * np.random.default_rng(seed).random(12)
        return v

    def test_pearson_prefers_the_played_chord(self):
        g = self.chroma("G", noise=0.1)
        self.assertGreater(hh.pearson(g, hh.template_vector("G")), hh.pearson(g, hh.template_vector("Em")))
        self.assertGreater(hh.pearson(g, hh.template_vector("G")), 0.9)
        self.assertEqual(hh.pearson(np.ones(12), hh.template_vector("G")), 0.0)    # flat chroma carries no information

    def test_score_bar_claim_mode(self):
        d = self.chroma("D6add9")
        held, best, delta = hh.score_bar(d, ("Em", "Em7"), {"D": "Dmaj7/F#"}, "claim")
        self.assertEqual(best[1], "D6add9")                                          # rivals get their colour variants
        self.assertGreater(delta, 0.1)
        em = self.chroma("Em7")
        _, _, delta2 = hh.score_bar(em, ("Em", "Em7"), {"D": "D"}, "claim")
        self.assertLess(delta2, 0)

    def test_no_rivals_gives_no_margin(self):
        _, best, delta = hh.score_bar(self.chroma("C"), ("C", "C"), {}, "claim")
        self.assertIsNone(best)
        self.assertIsNone(delta)


class Holds(unittest.TestCase):
    BEAT = 0.5

    def grid(self, n):
        return [i * self.BEAT for i in range(n)]

    def test_beat_position_round_trip_and_extrapolation(self):
        beats = self.grid(40)
        for x in (-2.0, 0.0, 3.25, 39.0, 41.5):
            self.assertAlmostEqual(hh.beat_position(beats, hh.beat_time(beats, x)), x, places=6)

    def test_blip_is_absorbed_and_threshold_applies(self):
        beats = self.grid(80)
        chords = [{"s": 0, "e": 10, "l": "Em"}, {"s": 10, "e": 10.2, "l": "G"}, {"s": 10.2, "e": 19, "l": "Em"},
                  {"s": 19, "e": 21, "l": "D"}]
        runs = hh.family_runs(chords, beats)
        self.assertEqual([r["key"] for r in runs], ["Em", "D"])                      # the 0.4-beat G is a blip
        holds = hh.long_holds(runs, 16)
        self.assertEqual(len(holds), 1)
        self.assertGreater(holds[0]["beats"], 37)
        self.assertEqual(hh.long_holds(runs, 40), [])

    def test_n_breaks_a_hold(self):
        beats = self.grid(80)
        runs = hh.family_runs([{"s": 0, "e": 10, "l": "C"}, {"s": 10, "e": 12, "l": "N"}, {"s": 12, "e": 22, "l": "C"}], beats)
        self.assertEqual(len(runs), 3)

    def synthetic(self, alternate):
        """Chart: Em for 40 s (80 beats of 0.5 s) then D for 10 s. Chroma matrix with chroma_cqt's frame rate (hop 512 at 22050 Hz):
        Em throughout the first 40 s, except that with `alternate` every odd bar (2 s) is D, as in a chart that merged two chords."""
        sr, hop = 22050, 512
        beats = self.grid(120)
        chords = [{"s": 0, "e": 40, "l": "Em"}, {"s": 40, "e": 50, "l": "D"}]
        n = int(60 * sr / hop)
        chroma = np.zeros((12, n))
        em, d = hh.template_vector("Em"), hh.template_vector("D")
        rng = np.random.default_rng(1)
        for i in range(n):
            t = i * hop / sr
            odd_bar = int(t // 2.0) % 2 == 1
            chroma[:, i] = (d if (t >= 40 or (alternate and odd_bar)) else em) + 0.05 * rng.random(12)
        return chords, beats, chroma, sr, hop

    def test_alternating_bars_inside_a_hold_are_found(self):
        chords, beats, chroma, sr, hop = self.synthetic(alternate=True)
        res = hh.analyse_holds(chords, beats, 4, chroma, sr, hop)
        self.assertEqual(res["long_holds"], 2)                                        # Em 80 beats and D 20 beats
        self.assertEqual(res["bars"], 25)
        self.assertAlmostEqual(res["missed_change_fraction"], 10 / 25, places=3)
        self.assertEqual(res["examples"][0]["winner"][0], "D")
        self.assertEqual(res["holds"][0]["held"], "Em")

    def test_a_true_hold_scores_zero(self):
        chords, beats, chroma, sr, hop = self.synthetic(alternate=False)
        res = hh.analyse_holds(chords, beats, 4, chroma, sr, hop)
        self.assertEqual(res["missed_change_fraction"], 0.0)
        self.assertEqual(res["examples"], [])

    def test_no_long_holds_gives_null_fraction(self):
        beats = self.grid(40)
        res = hh.analyse_holds([{"s": 0, "e": 2, "l": "C"}, {"s": 2, "e": 4, "l": "G"}], beats, 4, np.zeros((12, 5)), 22050, 512)
        self.assertEqual(res["long_holds"], 0)
        self.assertIsNone(res["missed_change_fraction"])


class StemStats(unittest.TestCase):
    def test_energy_shares_sum_to_one_and_harmonic_share(self):
        t = np.arange(44100) / 44100
        stems = {"drums": 0.1 * np.sin(t), "bass": 0.2 * np.sin(t), "other": 0.1 * np.sin(t), "vocals": 0.3 * np.sin(t),
                 "guitar": 0.3 * np.sin(t), "piano": 0.0 * t}
        s = stems_6s.stem_energy_stats(stems)
        self.assertAlmostEqual(sum(s["energy_share"].values()), 1.0, places=4)
        self.assertAlmostEqual(s["guitar_share_of_harmonic"], 0.09 / (0.09 + 0.01), places=3)

    def test_low_band_ratio_separates_low_and_high_guitar(self):
        sr = 44100
        t = np.arange(sr * 2) / sr
        mix = 0.5 * np.sin(2 * np.pi * 440 * t)
        low = stems_6s.guitar_band_stats(0.3 * np.sin(2 * np.pi * 110 * t), mix, sr)
        high = stems_6s.guitar_band_stats(0.3 * np.sin(2 * np.pi * 880 * t), mix, sr)
        self.assertGreater(low["low_band_ratio"], 50 * high["low_band_ratio"])
        self.assertGreater(low["active_fraction"], 0.99)

    def test_a_silent_guitar_stem_has_no_active_frames(self):
        sr = 44100
        t = np.arange(sr * 2) / sr
        mix = 0.5 * np.sin(2 * np.pi * 440 * t)
        out = stems_6s.guitar_band_stats(1e-4 * np.sin(2 * np.pi * 110 * t), mix, sr)
        self.assertEqual(out["active_frames"], 0)
        self.assertIsNone(out["low_band_ratio"])


class Tags(unittest.TestCase):
    names = ["x%d" % i for i in range(521)]
    idx = {k: i for i, k in enumerate(yt.CLASS_KEYS)}

    def test_top_k_mask(self):
        scores = np.array([[0.1, 0.9, 0.5, 0.3, 0.2, 0.05, 0.0], [0.9, 0.1, 0.0, 0.0, 0.2, 0.3, 0.4]])
        m = yt.top_k_mask(scores, 3)
        self.assertEqual(m.sum(1).tolist(), [3, 3])
        self.assertTrue(m[0, 1] and m[0, 2] and m[0, 3] and not m[0, 0])

    def summary(self, guitar=0.8, strum=0.1):
        scores = np.full((10, 521), 0.001, dtype=np.float32)
        scores[:, self.idx["guitar"]] = guitar
        scores[:, self.idx["strum"]] = strum
        return yt.summarize(scores, self.idx, self.names)

    def test_summarize_reports_mean_p90_top5_and_strum_given_guitar(self):
        s = self.summary()
        g = s["classes"]["guitar"]
        self.assertAlmostEqual(g["mean"], 0.8, places=3)
        self.assertAlmostEqual(g["top5_frac"], 1.0)
        self.assertEqual(s["strum_given_guitar"]["frames"], 10)
        self.assertAlmostEqual(s["strum_given_guitar"]["value"], 0.1, places=3)

    def test_strum_given_guitar_is_null_without_guitar_frames(self):
        s = self.summary(guitar=0.0)
        self.assertEqual(s["strum_given_guitar"]["frames"], 0)
        self.assertIsNone(s["strum_given_guitar"]["value"])

    def test_flat_scores_are_probabilities_and_strum_is_optional(self):
        mix, stem = self.summary(0.2), self.summary(0.9)
        flat = yt.flat_scores(mix, stem)
        self.assertNotIn("strum", flat)
        self.assertIn("strum", yt.flat_scores(mix, stem, include_strum=True))
        self.assertTrue(all(isinstance(v, float) and 0 <= v <= 1 for v in flat.values()))
        self.assertEqual(yt.flat_scores(mix, stem, "mix", "mean")["guitar"], 0.2)
        self.assertEqual(yt.flat_scores(mix, None, "stem", "mean")["guitar"], 0.2)     # no stem: falls back to the mix

    def test_merge_keeps_other_recordings_and_replaces_updated_ones(self):
        old = {"schema": yt.SCHEMA, "model": {"name": "old"}, "recordings": {"a": {"scores": {"guitar": 0.1}}, "b": {"scores": {"guitar": 0.2}}}}
        doc = yt.merge_tags(old, {"name": "yamnet"}, {"b": {"scores": {"guitar": 0.9}}, "c": {"scores": {"guitar": 0.5}}})
        self.assertEqual(list(doc["recordings"]), ["a", "b", "c"])
        self.assertEqual(doc["recordings"]["b"]["scores"]["guitar"], 0.9)
        self.assertEqual(doc["model"]["name"], "yamnet")
        other = yt.merge_tags({"schema": "something-else", "recordings": {"z": {}}}, {"name": "yamnet"}, {"c": {}})
        self.assertEqual(list(other["recordings"]), ["c"])

    def test_merge_keeps_the_strum_blocks_strum_features_wrote(self):
        old = {"schema": yt.SCHEMA, "model": {"name": "old"}, "strum_features": {"version": "v"},
               "recordings": {"a": {"scores": {"guitar": 0.1}, "strum": {"restrike_onbeat": 0.7}}}}
        doc = yt.merge_tags(old, {"name": "yamnet"}, {"a": {"scores": {"guitar": 0.9}}})
        self.assertEqual(doc["recordings"]["a"]["strum"], {"restrike_onbeat": 0.7})
        self.assertEqual(doc["recordings"]["a"]["scores"]["guitar"], 0.9)
        self.assertEqual(doc["strum_features"], {"version": "v"})

    def test_atomic_json_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nested" / "tags.json"
            sc.write_json_atomic(p, {"schema": yt.SCHEMA, "recordings": {"a": {"scores": {"guitar": 0.5}}}})
            self.assertEqual(json.loads(p.read_text())["recordings"]["a"]["scores"]["guitar"], 0.5)
            self.assertFalse(p.with_name("tags.json.tmp").exists())

    def test_class_names_resolve_in_the_real_class_map_when_present(self):
        path = yt.MODEL_DIR / "assets" / "yamnet_class_map.csv"
        if not path.is_file():
            self.skipTest("YAMNet class map not on this machine")
        names = yt.read_class_map(path)
        self.assertEqual(len(names), 521)
        idx = yt.class_indices(names)
        self.assertEqual(names[idx["ukulele"]], "Ukulele")
        self.assertEqual(names[idx["guitar"]], "Guitar")


class StrumFeatures(unittest.TestCase):
    def test_restrike_share_counts_peaks_that_got_louder(self):
        post = np.full(100, -80.0)
        pre = np.full(100, -80.0)
        for k in (20, 40, 60, 80):
            post[k] = -20.0
        pre[[20, 40]] = -10.0                                  # two partials were already louder before the attack
        self.assertAlmostEqual(sf.restrike_share(pre, post, 0, 100), 0.5)
        pre[:] = -90.0
        self.assertAlmostEqual(sf.restrike_share(pre, post, 0, 100), 1.0)
        few = np.full(100, -80.0)
        few[50] = -20.0
        self.assertIsNone(sf.restrike_share(pre, few, 0, 100))      # fewer than 3 peaks: no reading

    def test_chord_tone_coverage(self):
        new = np.zeros(12)
        new[[4, 7, 11]] = [1.0, 0.5, 0.2]                        # E minor: E G B all renewed
        self.assertEqual(sf.chord_tone_coverage(new, [4, 7, 11]), 3)
        new[[7, 11]] = 0.05                                      # only E renewed: a single picked note
        self.assertEqual(sf.chord_tone_coverage(new, [4, 7, 11]), 1)
        self.assertIsNone(sf.chord_tone_coverage(new, [4, 11]))     # power chords and dyads are not judged
        self.assertIsNone(sf.chord_tone_coverage(np.zeros(12), [4, 7, 11]))

    def test_summary_uses_on_beat_attacks_only(self):
        rows = [[1.0, 1, 0.01, 0.9, 3], [1.5, 1, 0.25, 0.1, 1], [2.0, 1, 0.02, 0.7, 1], [2.5, 1, 0.03, float("nan"), -1]]
        out = sf.summarise_attacks(rows)
        self.assertAlmostEqual(out["restrike_onbeat"], 0.8)
        self.assertEqual(out["onbeat_attacks"], 2)
        self.assertAlmostEqual(out["single_onbeat"], 0.5)
        self.assertEqual(out["attacks"], 4)
        self.assertIsNone(sf.summarise_attacks([])["restrike_onbeat"])

    def synth(self, strum):
        """Six decaying 'strings' (E minor, 82-330 Hz with harmonics), re-struck every beat at 100 BPM. Strummed: every string
        is re-excited on the beat. Picked: one string per beat in turn, the others keep ringing."""
        rate, beat, n = sf.SR, 0.6, 24
        t = np.arange(int(rate * beat * (n + 1))) / rate
        f0 = [82.41, 123.47, 164.81, 196.0, 246.94, 329.63]
        y = np.zeros_like(t)
        beats = [0.3 + i * beat for i in range(n)]
        for i, b in enumerate(beats):
            strings = range(6) if strum else [i % 6]
            for s in strings:
                tt = t - b - 0.002 * s
                env = np.where(tt >= 0, np.exp(-np.clip(tt, 0, None) / 0.8), 0.0)
                for h in (1, 2, 3, 4):
                    y += env * np.sin(2 * np.pi * f0[s] * h * tt) / h
        return (0.1 * y / np.abs(y).max()).astype(np.float32), beats

    def test_a_strum_restrikes_more_partials_than_picking(self):
        try:
            import librosa  # noqa: F401
        except ImportError:
            self.skipTest("librosa not in this environment")
        chords = [{"start_seconds": 0, "end_seconds": 100, "label": "Em"}]
        y, beats = self.synth(True)
        strum = sf.analyse_signal(y, beats, chords)
        y, beats = self.synth(False)
        pick = sf.analyse_signal(y, beats, chords)
        self.assertGreater(strum["onbeat_attacks"], 15)
        self.assertGreater(pick["onbeat_attacks"], 15)
        self.assertGreater(strum["restrike_onbeat"], pick["restrike_onbeat"] + 0.2)

    def test_merge_keeps_yamnet_fields_and_adds_stems_only_when_missing(self):
        old = {"schema": sf.SCHEMA, "model": {"name": "yamnet"}, "recordings": {"a": {"scores": {"guitar": 0.5}, "stems": {"guitar_share_of_harmonic": 0.9}}}}
        doc = sf.merge_strum(old, {"a": {"restrike_onbeat": 0.7}, "b": {"restrike_onbeat": 0.6}},
                             stems={"a": {"guitar_share_of_harmonic": 0.1}, "b": {"guitar_share_of_harmonic": 0.8}}, meta={"b": {"pack": "p"}})
        self.assertEqual(doc["model"], {"name": "yamnet"})
        self.assertEqual(doc["recordings"]["a"]["scores"], {"guitar": 0.5})
        self.assertEqual(doc["recordings"]["a"]["stems"]["guitar_share_of_harmonic"], 0.9)      # yamnet_tags.py's copy wins
        self.assertEqual(doc["recordings"]["b"]["stems"]["guitar_share_of_harmonic"], 0.8)
        self.assertEqual(doc["recordings"]["b"]["pack"], "p")
        self.assertEqual(doc["strum_features"]["version"], sf.VERSION)
        fresh = sf.merge_strum({"schema": "other", "recordings": {"z": {}}}, {"a": {"restrike_onbeat": 0.7}})
        self.assertEqual(list(fresh["recordings"]), ["a"])


class Discovery(unittest.TestCase):
    def test_catalogue_recordings_when_present(self):
        if not sc.CATALOGUE.is_file():
            self.skipTest("no catalogue")
        recs = sc.load_recordings()
        ids = [r["id"] for r in recs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(r["excluded"] for r in recs))                              # the labelled negatives are included
        with self.assertRaises(KeyError):
            sc.load_recordings(only=["not-a-recording"])
        self.assertEqual(sc.parse_only(["a,b", "c"]), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
