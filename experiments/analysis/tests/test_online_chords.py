"""Online reference facts remain review hints tied to native chart identity."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import online_chords as online


class OnlineChordChecks(unittest.TestCase):
    def source(self, name, chords, *, capo=0, tuning=0, intro=None):
        return online.normalize_source({"id": name, "title": name, "url": f"https://{name}.example/lesson",
            "origin_group": name, "status": "extracted", "content_sha256": name,
            "chord_shapes": chords, "capo": capo, "tuning_shift_semitones": tuning,
            "label_basis": "played-shapes", "ordered_sections": [{"name": "intro", "chords": intro}] if intro else []})

    def chart(self, labels):
        recording = {"id": "generated", "title": "Fixture", "duration_seconds": len(labels) * 2,
                     "sample_rate_hz": 22050, "audio_sha256": "a" * 64}
        chart = {"schema_version": "1.0", "recording": recording,
                 "analysis": {"id": "fixture", "algorithm": "fixture", "version": "1", "runtime_seconds": 0},
                 "chords": [{"start_seconds": i * 2, "end_seconds": (i + 1) * 2, "label": label} for i, label in enumerate(labels)]}
        return {"recording": recording}, chart

    def test_capo_transposes_bass_and_preserves_suspensions(self):
        source = self.source("teacher", ["Em7", "Dsus4", "A7sus4", "Cadd9", "G/F#"], capo=2)
        self.assertEqual(source["sounding_chords"], ["F#m7", "Esus4", "B7sus4", "Dadd9", "A/G#"])
        self.assertEqual(source["normalization"]["capo_basis"], "source")
        lowered = self.source("teacher", ["F#m", "A/C#"], tuning=-2)
        self.assertEqual(lowered["sounding_chords"], ["Em", "G/B"])

    def test_unknown_nonuniform_or_variant_setup_abstains(self):
        for capo, tuning in [(None, 0), (0, None), (True, 0), (0, "open-A")]:
            source = self.source("teacher", ["A", "D", "E"], capo=capo, tuning=tuning)
            self.assertEqual(source["sounding_chords"], [])
            self.assertEqual(source["comparison_status"], "unknown-setup")
        source = {"status": "extracted", "arrangement_variant": True, "chord_shapes": ["G"], "capo": 0, "tuning_shift_semitones": 0}
        self.assertEqual(online.normalize_source(source)["comparison_status"], "excluded-source")

    def test_seed_setup_is_explicit_hypothesis_and_never_overrides_source(self):
        source = {"status": "extracted", "chord_shapes": ["Em7"], "capo": None,
                  "tuning_shift_semitones": None, "label_basis": "played-shapes"}
        seed = {"comparison_setup": {"capo": 2, "tuning_shift_semitones": 0}}
        result = online.normalize_source(source, seed)
        self.assertEqual(result["sounding_chords"], ["F#m7"])
        self.assertEqual(result["comparison_status"], "teaching-hypothesis")
        self.assertEqual(online.normalize_source({**source, "capo": 0}, seed)["sounding_chords"], ["Em7"])

    def test_same_publisher_or_copied_page_is_not_two_sources(self):
        first = self.source("a", ["A", "D", "E"])
        second = {**self.source("b", ["A", "D", "E"]), "origin_group": "a"}
        third = {**self.source("c", ["A", "D", "E"]), "content_sha256": "a"}
        case, chart = self.chart(["Am"])
        result = online.check_case(case, chart, "b" * 64, [first, second, third])
        self.assertEqual(result["summary"]["independent_source_groups"], 1)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["status"], "insufficient-sources")

    def test_house_minor_quality_is_flagged_without_changing_chart(self):
        case, chart = self.chart(["Am", "C", "D", "F", "Am", "Em"])
        before = copy.deepcopy(chart)
        sources = [self.source(name, ["Am", "C", "D", "F", "E", "Dm", "E7"]) for name in ("one", "two")]
        result = online.check_case(case, chart, "b" * 64, sources)
        self.assertEqual([(f["native_label"], f["kind"], f["start_seconds"]) for f in result["findings"]], [("Em", "quality-conflict", 10)])
        self.assertIn("may be another section", result["findings"][0]["reason"])
        self.assertEqual(chart, before)

    def test_extensions_enharmonics_and_optional_variants_do_not_create_false_quality_conflicts(self):
        case, chart = self.chart(["Am7", "Db", "Dsus4", "A7sus4"])
        first = self.source("one", ["Am", "C#", "Dsus4", "A7sus4"])
        second = self.source("two", ["Am7", "Db", "D", "A"])
        result = online.check_case(case, chart, "b" * 64, [first, second])
        self.assertEqual(result["findings"], [])
        case, chart = self.chart(["D"])
        result = online.check_case(case, chart, "b" * 64, [self.source(name, ["Dsus4"]) for name in ("one", "two")])
        self.assertEqual(result["findings"][0]["kind"], "quality-conflict")

    def test_intro_order_produces_broad_native_window_not_missing_chord_timestamp(self):
        intro = ["Am", "C", "D", "F", "Am", "E", "Am", "E"]
        case, chart = self.chart(["Am", "C", "D", "F", "Am", "Em", "Am", "C"])
        sources = [self.source(name, intro, intro=intro) for name in ("one", "two")]
        result = online.check_case(case, chart, "b" * 64, sources)
        findings = [f for f in result["findings"] if f["kind"] == "source-order-conflict"]
        self.assertEqual(len(findings), 1)
        self.assertEqual((findings[0]["start_seconds"], findings[0]["end_seconds"]), (8, 16))
        self.assertNotIn("replacement_label", findings[0])
        self.assertIn("times are unknown", findings[0]["reason"])

    def test_unanchored_or_competing_intro_orders_abstain(self):
        case, chart = self.chart(["Am", "C", "E", "F", "Am", "Em"])
        intro = ["Am", "C", "D", "F", "Am", "E"]
        sources = [self.source(name, intro, intro=intro) for name in ("one", "two")]
        self.assertFalse(any(f["kind"] == "source-order-conflict" for f in online.check_case(case, chart, "b" * 64, sources)["findings"]))
        case, chart = self.chart(["Am", "C", "D", "F", "Am", "Em"])
        for name in ("three", "four"):
            sources.append(self.source(name, intro, intro=["Am", "C", "D", "F", "Am", "G"]))
        self.assertFalse(any(f["kind"] == "source-order-conflict" for f in online.check_case(case, chart, "b" * 64, sources)["findings"]))

    def test_palette_cannot_find_wild_thing_wrong_member_or_timing(self):
        case, chart = self.chart(["A", "D", "E", "E"])
        result = online.check_case(case, chart, "b" * 64, [self.source(name, ["A", "D", "E"]) for name in ("one", "two")])
        self.assertEqual(result["findings"], [])

    def test_intro_does_not_anchor_across_unknown_or_silent_gaps(self):
        intro = ["Am", "C", "D", "F", "Am", "E"]
        sources = [self.source(name, intro, intro=intro) for name in ("one", "two")]
        for gap in ("X", "N"):
            case, chart = self.chart(["Am", "C", gap, "D", "F", "Am", "Em"])
            findings = online.check_case(case, chart, "b" * 64, sources)["findings"]
            self.assertFalse(any(f["kind"] == "source-order-conflict" for f in findings))

    def test_riff_and_identity_mismatch_never_become_chord_findings(self):
        case, chart = self.chart(["Am"])
        sources = [self.source(name, ["A", "D", "E"]) for name in ("one", "two")]
        result = online.check_case(case, chart, "b" * 64, sources, harmony_task=False)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["status"], "not-harmony-task")
        case["recording"] = {**case["recording"], "audio_sha256": "c" * 64}
        with self.assertRaisesRegex(ValueError, "exact native recording"):
            online.check_case(case, chart, "b" * 64, sources)


if __name__ == "__main__":
    unittest.main()
