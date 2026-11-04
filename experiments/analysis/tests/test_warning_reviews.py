"""Review dispositions cannot silently replace source warnings or native cues."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import warning_reviews as reviews


class WarningReviews(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "catalogue").mkdir()
        self.evidence = self.root / "catalogue/evidence.json"
        self.evidence.write_text('{"gold":false}\n')
        self.recording = {"id": "house", "audio_sha256": "a" * 64, "sample_rate_hz": 22050, "duration_seconds": 120}
        self.finding = {"id": "online-003", "kind": "quality-conflict", "start_seconds": 90, "end_seconds": 93,
                        "native_label": "Em", "source_ids": ["one", "two"], "reason": "Replay the native cue."}
        self.case = {"recording": self.recording, "primary_sha256": "b" * 64, "analysis_id": "native-crema",
                     "findings": [self.finding], "summary": {"flagged_spans": 1}, "extra": "preserved"}
        self.report = {"schema_version": "online-chord-checks-1.0", "pack_id": "first-ten", "cases": [self.case]}
        self.review = {"schema_version": "online-finding-review-1.0", "status": "local-evidence-proposal", "gold": False,
                       "candidate_exposure": "model-exposed", "actor": "agent", "reviewed_at_utc": "2026-10-18T12:00:00Z",
                       "note": "E is a local candidate; physical cue bounds remain unverified.", "guide_correction_ids": [],
                       "proposal": {"label": "E", "timing_status": "native-boundaries-unverified"},
                       "evidence_refs": [{"path": "catalogue/evidence.json", "sha256": reviews.digest(self.evidence)}]}
        self.entry = {"finding_binding": {key: copy.deepcopy(self.finding[key]) for key in reviews.BINDING_FIELDS}, "review": self.review}
        self.case_review = {key: copy.deepcopy(self.case[key]) for key in ("recording", "primary_sha256", "analysis_id")}
        self.case_review["findings"] = [self.entry]
        self.input = {"schema_version": "online-warning-reviews-1.0", "pack_id": "first-ten", "cases": [self.case_review]}

    def apply(self, value=None):
        return reviews.apply_reviews(self.report, self.input if value is None else value, root=self.root)

    def test_annotations_preserve_every_raw_field_and_do_not_mutate_inputs(self):
        before = copy.deepcopy((self.report, self.input))
        result = self.apply()
        self.assertEqual((self.report, self.input), before)
        finding = result["cases"][0]["findings"][0]
        self.assertEqual(finding["review"]["proposal"]["label"], "E")
        self.assertEqual({key: value for key, value in finding.items() if key not in {"review", "review_binding"}}, self.finding)
        self.assertEqual(result["cases"][0]["summary"], {"flagged_spans": 1})
        self.assertEqual(result["cases"][0]["extra"], "preserved")

    def test_recording_pack_and_native_chart_identity_are_exact(self):
        for field, value in (("primary_sha256", "c" * 64), ("analysis_id", "other")):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.input); candidate["cases"][0][field] = value
                with self.assertRaises(ValueError): self.apply(candidate)
        for field, value in (("id", "other"), ("audio_sha256", "c" * 64), ("sample_rate_hz", 44100), ("duration_seconds", 121)):
            candidate = copy.deepcopy(self.input); candidate["cases"][0]["recording"][field] = value
            with self.assertRaises(ValueError): self.apply(candidate)
        with self.assertRaises(ValueError): self.apply({**self.input, "pack_id": "other"})

    def test_exact_warning_binding_cannot_move_a_review_to_a_similar_cue(self):
        for field, value in (("id", "other"), ("kind", "source-order-conflict"), ("start_seconds", 90.1),
                             ("end_seconds", 94), ("native_label", "E"), ("source_ids", ["one"]),
                             ("source_ids", ["one", "one"]), ("start_seconds", float("nan"))):
            candidate = copy.deepcopy(self.input); candidate["cases"][0]["findings"][0]["finding_binding"][field] = value
            with self.assertRaises(ValueError): self.apply(candidate)
        self.entry["finding_binding"]["source_ids"].reverse()
        self.assertEqual(self.apply()["cases"][0]["findings"][0]["native_label"], "Em")

    def test_duplicate_cases_or_warning_reviews_are_rejected(self):
        candidate = copy.deepcopy(self.input); candidate["cases"].append(copy.deepcopy(candidate["cases"][0]))
        with self.assertRaises(ValueError): self.apply(candidate)
        candidate = copy.deepcopy(self.input); candidate["cases"][0]["findings"] *= 2
        with self.assertRaises(ValueError): self.apply(candidate)

    def test_agent_proposal_cannot_become_founder_or_independent_acceptance(self):
        for change in ({"status": "independently-accepted"}, {"gold": True}, {"actor": "human"},
                       {"candidate_exposure": "audio-only"}, {"reviewed_at_utc": "2026-10-18T12:00:00"},
                       {"note": "x" * 1501}, {"proposal": {"label": "E", "timing_status": "verified"}},
                       {"accepted": True}, {"guide_correction_ids": ["invented"]}):
            candidate = copy.deepcopy(self.input); candidate["cases"][0]["findings"][0]["review"].update(change)
            with self.assertRaises(ValueError): self.apply(candidate)

    def test_covered_or_inconclusive_notes_do_not_suggest_new_player_chords(self):
        self.review.update(status="covered-by-provisional-guide", guide_correction_ids=["founder-intro"], proposal=None)
        self.assertEqual(self.apply()["cases"][0]["findings"][0]["review"]["status"], "covered-by-provisional-guide")
        self.review.update(status="inconclusive", guide_correction_ids=[])
        self.assertIsNone(self.apply()["cases"][0]["findings"][0]["review"]["proposal"])
        self.review["proposal"] = {"label": "E", "timing_status": "native-boundaries-unverified"}
        with self.assertRaises(ValueError): self.apply()

    def test_evidence_reference_must_be_public_metadata_with_matching_hash(self):
        for change in ({"path": "../secret.json"}, {"path": "catalogue/.private.json"},
                       {"path": "experiments/review/sessions/private.json"}, {"path": "catalogue/song.wav"},
                       {"path": str(self.evidence)}, {"sha256": "c" * 64}):
            candidate = copy.deepcopy(self.input); candidate["cases"][0]["findings"][0]["review"]["evidence_refs"][0].update(change)
            with self.assertRaises(ValueError): self.apply(candidate)
        self.evidence.write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash changed"): self.apply()

    def test_symlink_evidence_or_input_cannot_alias_private_files(self):
        alias = self.root / "catalogue/alias.json"; alias.symlink_to(self.evidence)
        self.review["evidence_refs"][0]["path"] = "catalogue/alias.json"
        with self.assertRaisesRegex(ValueError, "symlinks"): self.apply()

    def test_new_report_hashes_both_inputs_and_never_overwrites(self):
        report = self.root / "report.json"; report.write_text(json.dumps(self.report))
        inputs = self.root / "reviews.json"; inputs.write_text(json.dumps(self.input))
        output = self.root / "annotated.json"
        result = reviews.prepare(report, inputs, output, root=self.root)
        self.assertEqual(result["review_inputs"]["report_sha256"], reviews.digest(report))
        self.assertEqual(result["review_inputs"]["reviews_sha256"], reviews.digest(inputs))
        self.assertEqual(json.loads(output.read_text()), result)
        before = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "never overwritten"): reviews.prepare(report, inputs, output, root=self.root)
        self.assertEqual(output.read_bytes(), before)

    def test_existing_annotations_are_not_silently_replaced(self):
        self.report["cases"][0]["findings"][0]["review"] = {}
        with self.assertRaisesRegex(ValueError, "previous review"): self.apply()

    def test_inputs_changed_after_snapshot_cannot_publish_mismatched_provenance(self):
        for changed_name in ("report", "reviews"):
            with self.subTest(changed_name=changed_name):
                report = self.root / "report.json"; report.write_text(json.dumps(self.report))
                inputs = self.root / "reviews.json"; inputs.write_text(json.dumps(self.input))
                output = self.root / "annotated.json"
                changed_path = report if changed_name == "report" else inputs
                original_read = Path.read_bytes
                changed = False
                def read_then_change(path):
                    nonlocal changed
                    body = original_read(path)
                    if path == changed_path and not changed:
                        changed = True
                        path.write_text('{"concurrent_edit":true}')
                    return body
                with patch.object(Path, "read_bytes", read_then_change), self.assertRaisesRegex(ValueError, "Inputs or evidence changed"):
                    reviews.prepare(report, inputs, output, root=self.root)
                self.assertFalse(output.exists())

    def test_evidence_changed_after_validation_is_rechecked_before_publication(self):
        report = self.root / "report.json"; report.write_text(json.dumps(self.report))
        inputs = self.root / "reviews.json"; inputs.write_text(json.dumps(self.input))
        output = self.root / "annotated.json"
        original_apply = reviews.apply_reviews
        def apply_then_change(*args, **kwargs):
            result = original_apply(*args, **kwargs)
            self.evidence.write_text('{"concurrent_edit":true}')
            return result
        with patch.object(reviews, "apply_reviews", apply_then_change), self.assertRaisesRegex(ValueError, "Inputs or evidence changed"):
            reviews.prepare(report, inputs, output, root=self.root)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
