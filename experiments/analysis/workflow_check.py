"""Audit the saved selected workflow without inference or reference-score claims.

Run after the selected BTC/CREMA pack is built. Inputs and historical outputs
are read only; a report is written only to an unused output path.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import automatic_drafts as drafts

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "experiments/fixtures/selected-workflow-v1.json"
SOURCE = ROOT / "experiments/generated/repertoire-first-ten-v2/manifest.json"
BTC_ROOT = ROOT / "experiments/generated/selected-first-ten-btc-v1"
PACK = ROOT / "experiments/generated/automatic-first-ten-selected-v1"
LEGACY = ROOT / "experiments/generated/automatic-first-ten-v1"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(pack: Path = PACK, btc_root: Path = BTC_ROOT, source: Path = SOURCE,
          policy_path: Path = POLICY) -> dict:
    policy = read(policy_path)
    if policy.get("schema_version") != "selected-workflow-1.0":
        raise ValueError("Expected the versioned selected-workflow-1.0 decision")
    if policy.get("primary") != "btc" or policy.get("secondary") != "crema":
        raise ValueError("This audit is for the fixed BTC/CREMA selection")
    for relative, expected in policy["frozen_files"].items():
        path = drafts.project_input(ROOT / relative, ROOT)
        if drafts.digest(path) != expected:
            raise ValueError(f"Selected workflow input changed: {relative}")
    manifest = read(pack / "manifest.json")
    if manifest.get("model_selection") != {"primary": "btc", "secondary": "crema"}:
        raise ValueError("Selected manifest declares a different model pair")
    source_manifest = read(source)
    jobs = {case["id"]: case for case in source_manifest["cases"]}
    cases = manifest["cases"]
    identifiers = [case["id"] for case in cases]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(jobs):
        raise ValueError("Selected pack must contain exactly the declared source cases")
    if manifest.get("gold") is not False:
        raise ValueError("Selected automatic pack must not claim reference status")
    public = drafts.public_files(pack)
    rows = []
    for case in cases:
        identifier = case["id"]
        original_audio = drafts.project_input(source.parent / jobs[identifier]["audio"], ROOT)
        native_btc = drafts.project_input(btc_root / "cases" / identifier / "btc.json", ROOT)
        native_crema = original_audio.parent / "crema.json"
        folder = pack / "cases" / identifier
        charts = [read(native_btc), read(native_crema)]
        record = jobs[identifier]["source"]["recording"]
        drafts.verified_audio(original_audio, record)
        for chart in charts:
            drafts.paired_recording(chart, {**chart, "recording": record})
        btc_parameters = charts[0]["analysis"]["parameters"]
        if (charts[0]["analysis"]["algorithm"] != "BTC-ISMIR19"
                or btc_parameters["checkpoint_sha256"] != policy["btc_checkpoint_sha256"]
                or btc_parameters["upstream_revision"] != policy["btc_upstream_revision"]
                or btc_parameters["device"] != "cpu" or btc_parameters["threads"] != 4
                or btc_parameters["smoothing"] != "none"):
            raise ValueError("BTC source, checkpoint or settings differ from the selection")
        crema_parameters = charts[1]["analysis"]["parameters"]
        if (charts[1]["analysis"]["algorithm"] != "crema-pretrained"
                or crema_parameters["model_version"] != "a4c7d57.0"
                or crema_parameters["device"] != "cpu"
                or str(crema_parameters["intraop_threads"]) != "1"
                or str(crema_parameters["inter_op_threads"]) != "1"):
            raise ValueError("CREMA model or settings differ from the selection")
        hashes = {}
        for original, copied in [(original_audio, folder / "audio.wav"),
                                 (native_btc, folder / "primary.json"),
                                 (native_crema, folder / "crema.json")]:
            original_hash = drafts.digest(original)
            if original_hash != drafts.digest(copied):
                raise ValueError("Selected pack changed a native chart or source WAV")
            hashes[copied.name] = original_hash
        declared = case.get("recording", {})
        for field in ("id", "audio_sha256", "sample_rate_hz", "duration_seconds"):
            if declared.get(field) != record[field]:
                raise ValueError("Selected manifest declares a different recording identity")
        if (case.get("artifacts") != {"primary_sha256": hashes["primary.json"],
                                     "crema_sha256": hashes["crema.json"]}
                or case.get("source") != jobs[identifier].get("source", {})
                or case.get("origin") != {"source_recording_id": identifier,
                                          "source_audio_sha256": record["audio_sha256"],
                                          "source_offset_seconds": 0}):
            raise ValueError("Selected manifest declares different chart hashes, source or timing origin")
        saved_evidence = read(folder / "evidence.json")
        if (saved_evidence != drafts.compare_charts(*charts)
                or case.get("summary") != saved_evidence["metrics"]):
            raise ValueError("Selected disagreement evidence differs from paired predictions")
        rows.append({"id": identifier, "audio_seconds": record["duration_seconds"],
                     "hashes": hashes, "btc_runtime_seconds": charts[0]["analysis"]["runtime_seconds"],
                     "btc_intervals": len(charts[0]["chords"]),
                     "crema_intervals": len(charts[1]["chords"]),
                     "accuracy_score": None, "status": "unreviewed integration check"})
    batch = read(btc_root / "btc-batch-summary.json")
    if (batch["failed_cases"] != 0 or len(batch["cases"]) != len(rows)
            or {case["id"] for case in batch["cases"]} != set(jobs)
            or any(case["status"] != "ok" for case in batch["cases"])):
        raise ValueError("Selected inference batch must succeed on every exact source case")
    if (batch.get("algorithm") != "BTC-ISMIR19"
            or not isinstance(batch.get("runtime_seconds"), (int, float))
            or isinstance(batch["runtime_seconds"], bool)
            or not math.isfinite(batch["runtime_seconds"]) or batch["runtime_seconds"] < 0
            or Path(batch.get("manifest", "")).resolve() != source.resolve()):
        raise ValueError("BTC batch summary has different source/algorithm or invalid runtime")
    measured = {row["id"]: row for row in rows}
    for batch_case in batch["cases"]:
        native_path = btc_root / "cases" / batch_case["id"] / "btc.json"
        if (Path(batch_case.get("output", "")).resolve() != native_path.resolve()
                or batch_case.get("runtime_seconds") != measured[batch_case["id"]]["btc_runtime_seconds"]):
            raise ValueError("BTC batch output path/runtime does not match the audited native chart")
    legacy_hash = drafts.digest(LEGACY / "manifest.json")
    if legacy_hash != policy["retained_player_manifest_sha256"]:
        raise ValueError("Existing player manifest changed during selected preparation")
    legacy_cases = {case["id"]: case for case in read(LEGACY / "manifest.json")["cases"]}
    for identifier, case in legacy_cases.items():
        folder = LEGACY / "cases" / identifier
        drafts.verified_audio(folder / "audio.wav", case["recording"])
        for filename, field in [("primary.json", "primary_sha256"), ("chordino.json", "chordino_sha256")]:
            if drafts.digest(folder / filename) != case["artifacts"][field]:
                raise ValueError("Existing player chart bytes changed")
    return {"schema_version": "algorithm-selection-results-1.0",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "selection_status": "initial offline workflow selected; catalogue acceptance pending",
            "policy_sha256": drafts.digest(policy_path),
            "frozen_files_verified": len(policy["frozen_files"]),
            "source_manifest_sha256": drafts.digest(source),
            "selected_manifest_sha256": drafts.digest(pack / "manifest.json"),
            "btc_batch_summary_sha256": drafts.digest(btc_root / "btc-batch-summary.json"),
            "retained_player_manifest_sha256": legacy_hash,
            "successful_cases": len(rows), "failed_cases": 0,
            "audio_seconds": sum(row["audio_seconds"] for row in rows),
            "btc_batch_runtime_seconds": batch["runtime_seconds"],
            "public_assets_verified": len(public), "cases": rows,
            "limitations": ["No verified reference pairs for this popular-song batch; no accuracy score",
                            "Existing local caches warmed; runtime is BTC batch only, not acquisition, review or hosting cost",
                            "CREMA charts are exact cached native results, not fresh inference",
                            "Correction effort and ordinary guitar followability remain unmeasured acceptance gates",
                            "Legacy player bytes and identity retained; selected pack is a separate local research artifact"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=PACK)
    parser.add_argument("--btc-root", type=Path, default=BTC_ROOT)
    parser.add_argument("--source-manifest", type=Path, default=SOURCE)
    parser.add_argument("--policy", type=Path, default=POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.output.exists():
            raise ValueError("Reports are not overwritten; choose an unused output path")
        result = audit(args.pack, args.btc_root, args.source_manifest, args.policy)
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"successful_cases": result["successful_cases"],
                          "frozen_files_verified": result["frozen_files_verified"],
                          "audio_seconds": result["audio_seconds"],
                          "btc_batch_runtime_seconds": result["btc_batch_runtime_seconds"],
                          "report": str(args.output) if args.output else None}))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"Selected workflow audit failed: {error}\n")


if __name__ == "__main__":
    main()
