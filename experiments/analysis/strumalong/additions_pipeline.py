"""Driver for the Strum Along additions pack.

Imports the existing, unchanged music-os tools; adds no analysis code.
Run with the repo's analysis interpreter so the existing modules import:

  .venv-analysis/bin/python -B experiments/analysis/strumalong/additions_pipeline.py <step> ...

The 24 October 2026 run used a scratch stage directory; the default stage directory is now a
gitignored folder beside the pack. The stage step refuses to reuse an existing stage directory.

Steps (each is a separate subcommand so a failed song never blocks the rest):
  import   - yt-dlp importer, one recording at a time (needs download permission)
  stage    - verify importer outputs, copy audio into a scratch batch dir, write batch manifest
  infer    - CREMA batch (.venv-crema) + Chordino batch (.venv-analysis), frozen adapters, default env
  build    - automatic_drafts.build() into the new pack (legacy CREMA primary / Chordino secondary mode)
  rhythm   - rhythm_grid.py CLI (.venv-crema, librosa 0.9.2) -> <pack>/rhythm.json
  all      - stage, infer, build, rhythm

Nothing under an existing pack, review/*.json or frozen tool is written.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / "experiments" / "analysis"
DEFAULT_IMPORT_ROOT = ROOT / "experiments" / "local-audio" / "youtube"
DEFAULT_STAGE = ROOT / "experiments" / "generated" / "strumalong-additions-v1-stage"
DEFAULT_PACK = ROOT / "experiments" / "generated" / "strumalong-additions-v1"
DEFAULT_CONFIG = ROOT / "experiments" / "fixtures" / "rhythm-strumalong-additions-v1.json"
DEFAULT_ADDITIONS = ROOT / "strumalong" / "data" / "additions.json"
CREMA_PY = ROOT / ".venv-crema" / "bin" / "python"
ANALYSIS_PY = ROOT / ".venv-analysis" / "bin" / "python"
YOUTUBE_PY = ROOT / ".venv-youtube" / "bin" / "python"
NODE = Path("/opt/homebrew/bin/node")
SOURCE_USE = "Requested local founder strum-along app, 24 Oct 2026; personal testing; commercial clearance not established"


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as s:
        for chunk in iter(lambda: s.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def selected(args) -> list[dict]:
    cands = load(Path(args.candidates))
    rows = cands["first_picks"] if args.set == "first" else cands[args.set]
    if args.only:
        wanted = set(args.only.split(","))
        rows = [r for r in rows if r["recording_id"] in wanted]
    return rows


def run(cmd: list, **kw) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def step_import(args) -> None:
    # Paced: one recording at a time, a random pause between downloads, and the batch
    # stops at the first upstream rate limit instead of retrying. Rerun to resume.
    import random
    import time
    downloaded = 0
    for row in selected(args):
        target = Path(args.import_root) / row["recording_id"]
        if target.exists():
            print("skip (exists):", row["recording_id"])
            continue
        if downloaded:
            pause = random.uniform(args.pause_min, args.pause_max)
            print(f"pause {pause:.0f} s", flush=True)
            time.sleep(pause)
        downloaded += 1
        url = f"https://www.youtube.com/watch?v={row['video_id']}"
        result = subprocess.run([str(c) for c in [YOUTUBE_PY, ANALYSIS / "youtube_import.py", "--node", NODE,
                                 "import", url, "--recording-id", row["recording_id"], "--source-use", SOURCE_USE,
                                 "--output-root", args.import_root]], capture_output=True, text=True, timeout=600)
        print(result.stdout, end="", flush=True)
        if result.returncode != 0:
            print("IMPORT FAILED", row["recording_id"], result.stderr.strip()[-300:], file=sys.stderr, flush=True)
            if "429" in result.stdout + result.stderr or "rate limit" in (result.stdout + result.stderr).lower():
                raise SystemExit("upstream rate limit: stopping the batch; rerun later to resume")


def step_stage(args) -> None:
    stage = Path(args.stage_dir)
    if stage.exists():
        raise SystemExit(f"stage dir exists, choose a new one: {stage}")
    cases = []
    for row in selected(args):
        rid = row["recording_id"]
        folder = Path(args.import_root) / rid
        if not folder.is_dir():
            print("MISSING import (skipped):", rid, file=sys.stderr)
            continue
        man = load(folder / "manifest.json")
        rec, src = man["recording"], man["source"]
        assert man["status"] == "prepared" and rec["id"] == rid, rid
        assert src["video_id"] == row["video_id"], f"video id mismatch {rid}"
        audio = folder / "audio.wav"
        assert sha256(audio) == rec["audio_sha256"], f"audio hash mismatch {rid}"
        assert sha256(folder / src["file"]) == src["sha256"], f"source hash mismatch {rid}"
        with wave.open(str(audio), "rb") as w:
            assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 22050, 2), rid
            assert abs(w.getnframes() / 22050 - rec["duration_seconds"]) < 1e-6, rid
        assert rec["duration_seconds"] < 600, rid
        target = stage / "cases" / rid
        target.mkdir(parents=True)
        shutil.copyfile(audio, target / "audio.wav")
        assert sha256(target / "audio.wav") == rec["audio_sha256"]
        cases.append({"id": rid, "name": f"{row['artist']} - {row['title']}",
                      "audio": f"cases/{rid}/audio.wav", "source": man})
    if not cases:
        raise SystemExit("nothing staged")
    (stage / "manifest.json").write_text(json.dumps({
        "pilot_version": "1.0", "status": "prepared", "cases": cases,
        "limitations": "Strum Along additions staging batch; cached outputs only; no verified timing gold or accuracy claim."},
        indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"staged {len(cases)} recordings in {stage}")


def step_infer(args) -> None:
    stage = Path(args.stage_dir)
    manifest = stage / "manifest.json"
    # Frozen adapters, default environment (no threading overrides), same entry points as the first ten.
    run([CREMA_PY, ANALYSIS / "candidates" / "crema_adapter.py", "--batch-manifest", manifest,
         "--output-root", stage], timeout=3600)
    run([ANALYSIS_PY, ANALYSIS / "candidates" / "chordino_adapter.py", "--batch-manifest", manifest,
         "--output-root", stage], timeout=3600)


def step_build(args) -> None:
    sys.path.insert(0, str(ANALYSIS))
    import automatic_drafts  # existing module, unchanged
    stage, pack = Path(args.stage_dir), Path(args.pack)
    # source_root is the scratch staging root: build() only requires inputs to live inside it.
    result = automatic_drafts.build(stage / "manifest.json", pack, source_root=stage)
    # The first-ten builder hard-codes capo metadata for its own IDs; mirror that structure for the
    # additions from the authored additions.json (suggestions, not detector labels).
    additions = Path(args.additions)
    if additions.is_file():
        meta = {s["recording_id"]: s for s in load(additions)["songs"]}
        manifest_path = pack / "manifest.json"
        manifest = load(manifest_path)
        for case in manifest["cases"]:
            song = meta.get(case["id"])
            if song is not None:
                case["practice"] = {
                    "capo": song["capo"], "source_url": (song.get("sources") or [{}])[0].get("url"),
                    "label_convention": "sounding pitches in raw charts",
                    "status": "Authored capo suggestion; any displayed capo shapes are a separate practice view, not detector labels or reference annotations"}
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"built {pack} with {len(result['cases'])} cases")


def step_rhythm(args) -> None:
    pack = Path(args.pack)
    run([CREMA_PY, ANALYSIS / "rhythm_grid.py", "--manifest", pack / "manifest.json",
         "--config", args.config, "--output", pack / "rhythm.json"], timeout=3600)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("step", choices=["import", "stage", "infer", "build", "rhythm", "all"])
    p.add_argument("--candidates", default=str(ROOT / "experiments" / "fixtures" / "strumalong-additions-candidates-v1.json"))
    p.add_argument("--set", default="first", choices=["first", "fallbacks_in_order"])
    p.add_argument("--only", help="comma-separated recording ids")
    p.add_argument("--pause-min", type=float, default=60.0, help="import: minimum seconds between downloads")
    p.add_argument("--pause-max", type=float, default=150.0, help="import: maximum seconds between downloads")
    p.add_argument("--import-root", default=str(DEFAULT_IMPORT_ROOT))
    p.add_argument("--stage-dir", default=str(DEFAULT_STAGE))
    p.add_argument("--pack", default=str(DEFAULT_PACK))
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--additions", default=str(DEFAULT_ADDITIONS))
    args = p.parse_args()
    steps = {"import": [step_import], "stage": [step_stage], "infer": [step_infer], "build": [step_build],
             "rhythm": [step_rhythm], "all": [step_stage, step_infer, step_build, step_rhythm]}[args.step]
    for fn in steps:
        fn(args)


if __name__ == "__main__":
    main()
