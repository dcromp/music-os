"""Catalogue-wide inspection respects teaching setup and cannot accept music."""
from contextlib import contextmanager, ExitStack
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_change_check as check


def chart(events, duration=10.0):
    return {"schema_version": "1.0", "recording": {"id": "declared-fixture", "title": "Declared fixture",
            "duration_seconds": duration, "sample_rate_hz": 22050, "audio_sha256": "a" * 64},
            "analysis": {"id": "declared", "algorithm": "symbolic-fixture", "version": "1",
                         "runtime_seconds": 0, "parameters": {}},
            "chords": [{"start_seconds": a, "end_seconds": b, "label": c} for a, b, c in events]}


def context(song, shapes):
    points = [{"id": str(i), "kind": "coverage-sample", "start_seconds": i * 2,
               "end_seconds": i * 2 + 1} for i in range(4)]
    return {"source_context": {"song_id": song, "entry_shapes": shapes},
            "points": points + [{"id": "contrast", "kind": "disagreement", "start_seconds": 5, "end_seconds": 6}]}


class CatalogueChangeCheckTests(unittest.TestCase):
    def test_riff_first_tracks_cannot_acquire_triad_hold_targets(self):
        native = chart([(0, 10, "Em")])
        for song in ("seven-nation-army", "come-as-you-are"):
            with self.subTest(song=song):
                result = check.case_review(native, copy.deepcopy(native), context(song, None))
                self.assertTrue(result["riff_first"])
                self.assertEqual(result["source_guided_hold_candidates"], [])
                self.assertFalse(result["accepted_arrangement"])
                with patch.dict(check.TARGETS, {song: [("Em", 1)]}), self.assertRaises(ValueError):
                    check.case_review(native, copy.deepcopy(native), context(song, None))

    def test_capo_two_review_targets_sounding_f_sharp_minor_not_em_shape(self):
        native = chart([(0, 3, "F#m7"), (3, 6, "Em"), (6, 10, "D")])
        result = check.case_review(native, copy.deepcopy(native), context("wonderwall", ["Em7", "G"]))
        candidates = result["source_guided_hold_candidates"]
        self.assertEqual([(r["model"], r["target"]) for r in candidates],
                         [("btc", "F#m"), ("btc", "D"), ("crema", "F#m"), ("crema", "D")])
        self.assertTrue(all(r["native_span"]["source_labels"] != ["Em"] for r in candidates))
        self.assertTrue(all(r["accepted_section"] is False for r in candidates))

    def test_catalogue_inventory_preserves_gaps_native_labels_and_fixed_samples(self):
        # Neither B fragment reaches the 2s threshold. A missing second must not
        # turn them into one sustained B; the contiguous Cm does qualify.
        native = chart([(0, 1, "B"), (2, 3, "B"), (3, 5, "Cm"), (5, 10, "C")])
        secondary = copy.deepcopy(native); source = context("creep", ["G", "B", "C", "Cm"])
        before = copy.deepcopy((native, secondary, source))
        result = check.case_review(native, secondary, source)
        self.assertEqual([(r["model"], r["target"]) for r in result["source_guided_hold_candidates"]],
                         [("btc", "Cm"), ("crema", "Cm")])
        self.assertEqual(len(result["fixed_coverage_samples"]), 4)
        self.assertTrue(any(r["kind"].endswith("coverage-gap") for r in result["boundary_review"]["all_review_windows"]))
        self.assertEqual((native, secondary, source), before)
        self.assertIsNone(result["physical_timing_accuracy"])

    @contextmanager
    def small_run(self):
        """Mock public preflight only; real read/write and mutation guard remain."""
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory).resolve(); pack = root / "experiments/generated/input"
            folder = pack / "cases/declared-fixture"; folder.mkdir(parents=True)
            native = chart([(0, 4, "B"), (4, 10, "Cm")]); write = check.drafts.write_json
            case = {"id": "declared-fixture", "name": "Declared fixture", "artifacts": {}}
            manifest = {"cases": [case]}; write(pack / "manifest.json", manifest)
            write(folder / "primary.json", native); write(folder / "crema.json", native)
            write(folder / "review.json", context("creep", ["G", "B", "C", "Cm"]))
            (folder / "audio.wav").write_bytes(b"Mocked preflight fixture; not audio evidence")
            private = pack / "private-drafts"; private.mkdir(); write(private / "declared-fixture.json", {"note": "retain"})
            public = {str(p.relative_to(pack)): p for p in pack.rglob("*") if p.is_file() and private not in p.parents}
            stack.enter_context(patch.object(check.curation, "public_files", return_value=(public, manifest)))
            # The method dependency pins must also be inside this disposable
            # root, rather than accidentally pinning the actual source tree.
            modules = [check, check.timing, check.curation, check.curation.review_pack, check.drafts,
                       check.timing.lab, check.timing.core_chord_screen, check.timing.pitch.rich_quality_suite]
            for index, module in enumerate(dict.fromkeys(modules)):
                dependency = root / f"method-{index}.py"; dependency.write_text(f"# declared method {index}\n")
                stack.enter_context(patch.object(module, "__file__", str(dependency)))
            yield {"root": root, "pack": pack, "folder": folder, "private": private,
                   "output": root / "experiments/generated/output"}

    def test_published_report_retains_inputs_and_explicitly_has_no_acceptance(self):
        with self.small_run() as p:
            before = {f: f.read_bytes() for f in p["pack"].rglob("*") if f.is_file()}
            result = check.run(p["pack"], p["output"], root=p["root"])
            self.assertEqual({f: f.read_bytes() for f in before}, before)
            self.assertEqual(result["accepted_arrangements"], 0)
            self.assertFalse(result["gold"]); self.assertFalse(result["raw_inputs_modified"])
            self.assertFalse(result["private_drafts_modified"])
            self.assertIsNone(result["human_correction_seconds"])
            self.assertEqual(len(result["cases"][0]["fixed_coverage_samples"]), 4)
            self.assertTrue((p["output"] / "report.json").is_file())

    def test_concurrent_chart_or_private_draft_change_aborts_without_publication(self):
        for target in ("chart", "private", "new-private", "deleted-private"):
            with self.subTest(target=target), self.small_run() as p:
                original = check.case_review
                mutated = p["folder"] / "primary.json" if target == "chart" else p["private"] / "declared-fixture.json"
                def mutate(*args):
                    result = original(*args)
                    if target == "new-private":
                        (p["private"] / "new.json").write_text('{"new":true}\n')
                    elif target == "deleted-private": mutated.unlink()
                    else: mutated.write_text('{"concurrent":"retained"}\n')
                    return result
                with patch.object(check, "case_review", side_effect=mutate), self.assertRaisesRegex(ValueError, "changed"):
                    check.run(p["pack"], p["output"], root=p["root"])
                self.assertFalse(p["output"].exists())
                self.assertEqual(list(p["output"].parent.glob(".change-check-*")), [])
                if target in ("chart", "private"):
                    self.assertEqual(mutated.read_text(), '{"concurrent":"retained"}\n')


if __name__ == "__main__":
    unittest.main()
