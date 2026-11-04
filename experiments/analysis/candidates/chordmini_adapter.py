"""CPU adapter for the official ChordMini ChordNet 2E1D checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
REVISION = "aa6e3a8d7b017f082fd2aaff9329d5c26af49c03"
CHECKPOINT_HASH = "ecc3de5e7b5b4affdd8e903106e11c24440631e5f43cf22d2a5975b3f160229a"


class Model:
    def __init__(self, repository: Path):
        started = time.perf_counter()
        os.environ.setdefault("NUMBA_CACHE_DIR", str(ROOT / "experiments/candidate-assets/chordmini-numba"))
        os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "experiments/candidate-assets/chordmini-matplotlib"))
        import numpy as np
        import torch
        import yaml
        self.np, self.torch = np, torch
        torch.set_num_threads(4)
        checkpoint = repository / "checkpoints/2e1d_model_best.pth"
        revision = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
        if revision != REVISION:
            raise ValueError(f"Expected ChordMini source {REVISION}, found {revision}")
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != CHECKPOINT_HASH:
            raise ValueError("Unexpected checkpoint hash")
        sys.path.insert(0, str(repository))
        from src.models.chord_net import ChordNet
        from src.models.common.checkpoint_loading import _infer_chordnet
        from src.utils import HParams
        from src.evaluation.utils.common import extract_song_features
        from src.evaluation.utils.inference import predict_sliding_windows
        self.features, self.predict = extract_song_features, predict_sliding_windows
        with torch.serialization.safe_globals([np.core.multiarray.scalar, np.dtype, type(np.dtype("float64"))]):
            data = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.config = HParams.load(str(repository / "config/ChordMini.yaml"))
        self.architecture = _infer_chordnet(data["model_state_dict"], self.config)
        self.model = ChordNet(**self.architecture).to("cpu")
        self.model.load_state_dict(data["model_state_dict"], strict=True)
        self.model.eval()
        self.mean, self.std = float(data["normalization"]["mean"]), float(data["normalization"]["std"])
        self.mapping = {int(key): value for key, value in data["idx_to_chord"].items()}
        self.setup_seconds = time.perf_counter() - started

    def analyze(self, audio: Path, recording_id: str) -> dict:
        import soundfile as sf
        started = time.perf_counter()
        info = sf.info(str(audio))
        duration = info.frames / info.samplerate
        features, hop_seconds = self.features(str(audio), self.config)
        labels = self.predict(model=self.model, feature_matrix=features, mean=self.mean, std=self.std,
                              seq_len=108, batch_size=16, model_type="ChordNet", n_classes=len(self.mapping),
                              vote_aggregation="logit", use_overlap=False, overlap_ratio=0,
                              smooth_logits=False, smooth_predictions=False, kernel_size=1, use_gaussian=False)
        events = []
        for index, value in enumerate(labels):
            start = index * hop_seconds
            if start >= duration:
                break
            native = self.mapping[int(value)]
            label = native.replace(":min", "m").replace(":maj", "maj").replace(":", "")
            if events and events[-1]["label"] == label:
                continue
            if events:
                events[-1]["end_seconds"] = start
            events.append({"start_seconds": start, "end_seconds": duration,
                           "label": label, "native_label": native})
        if not events:
            raise ValueError("No ChordMini predictions")
        return {"schema_version": "1.0",
                "recording": {"id": recording_id, "title": audio.stem, "duration_seconds": duration,
                              "sample_rate_hz": info.samplerate,
                              "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest()},
                "analysis": {"id": f"chordnet-{CHECKPOINT_HASH[:12]}", "algorithm": "ChordMini-ChordNet2E1D",
                             "version": f"adapter-0.1/upstream-{REVISION[:12]}",
                             "runtime_seconds": time.perf_counter() - started,
                             "parameters": {"upstream_revision": REVISION, "checkpoint_sha256": CHECKPOINT_HASH,
                                            "device": "cpu", "threads": 4, "architecture": self.architecture,
                                            "torch_version": self.torch.__version__, "seq_len": 108,
                                            "numpy_version": self.np.__version__,
                                            "smoothing": "none", "overlap": False,
                                            "mapping": "checkpoint idx_to_chord, not a guessed vocabulary",
                                            "model_setup_seconds": self.setup_seconds}}, "chords": events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recording-id")
    parser.add_argument("--batch-manifest", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--repository", type=Path, default=ROOT / "experiments/candidate-assets/chordmini")
    args = parser.parse_args()
    model = Model(args.repository)
    jobs = []
    if args.batch_manifest:
        manifest = json.loads(args.batch_manifest.read_text())
        output_root = args.output_root or args.batch_manifest.parent
        for case in manifest["cases"]:
            if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in case["id"]):
                raise ValueError("Unsafe case ID")
            audio = (args.batch_manifest.parent / case["audio"]).resolve()
            if not audio.is_relative_to(args.batch_manifest.parent.resolve()):
                raise ValueError("Case audio leaves manifest directory")
            jobs.append((audio, output_root / "cases" / case["id"] / "chordmini.json", case["id"]))
    else:
        if not args.audio or not args.output or not args.recording_id:
            parser.error("Provide --audio, --output and --recording-id")
        jobs = [(args.audio, args.output, args.recording_id)]
    failures = []
    started = time.perf_counter()
    for audio, output, recording_id in jobs:
        try:
            if audio.resolve() == output.resolve():
                raise ValueError("Output must not overwrite audio")
            if output.exists():
                output.unlink()
            result = model.analyze(audio, recording_id)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
            print(f"ChordMini {recording_id}: {result['analysis']['runtime_seconds']:.3f}s", flush=True)
        except Exception as error:
            failures.append({"id": recording_id, "error": str(error)})
            print(f"ChordMini failed {recording_id}: {error}", file=sys.stderr, flush=True)
    if args.batch_manifest:
        (output_root / "chordmini-batch-summary.json").write_text(json.dumps({
            "cases": len(jobs), "failures": failures, "model_setup_seconds": model.setup_seconds,
            "batch_wall_seconds": time.perf_counter() - started}, indent=2) + "\n")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
