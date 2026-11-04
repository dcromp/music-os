#!/usr/bin/env python
"""Six-stem separation for the Strum Along instrument stage.

Run with the Demucs environment:

    .venv-demucs/bin/python experiments/analysis/strumalong/stems_6s.py [--only ID[,ID...]] [--force] [--threads 10]

For every recording in strumalong/data/catalogue.json (excluded ones too, they are the labelled negatives) it separates the
pack's prepared mono 22.05 kHz audio with htdemucs_6s and writes, under experiments/generated/strumalong-stems/<id>/
(gitignored):

    guitar16k.wav   the guitar stem only, mono 16 kHz PCM16 (YAMNet's input format)
    stats.json      per-stem energy, energy shares, guitar share of the harmonic accompaniment, guitar low-band ratio

Recordings whose stats.json already exists are skipped unless --force. stats.json is written last, so its existence means the
guitar stem is on disk too. One failing recording does not stop the batch (exit code 1 at the end).

Offline by construction: the weights are the file the founder approved (experiments/candidate-assets/demucs-6s, SHA-256 checked
before loading) and the model is loaded through demucs' local-repo path; nothing is downloaded.

Measures (all on mono stems at 44.1 kHz, the model's own rate):

- energy per stem = mean square of the stem; energy_share = that over the sum of the six; rms_dbfs = 10 log10(mean square).
- guitar_share_of_harmonic = guitar / (guitar + piano + other), by energy.
- guitar_low_band: over the "active" frames of the guitar stem, the energy in 70-250 Hz divided by the energy in 250-4000 Hz.
  Frames are 2048 samples (46 ms), Hann-windowed, not overlapped. A frame is active when the guitar stem's frame energy is at
  least ACTIVE_RATIO (3%, about -15 dB) of the mix's frame energy and the mix is above -60 dBFS RMS. Open-string guitar sits
  at 82 to 330 Hz, ukulele (GCEA) fundamentals start at about 262 Hz, so a ukulele should show a much lower ratio.
"""
import argparse
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strumalong_common import REPO, STEMS_DIR, file_sha256, load_recordings, parse_only, write_json_atomic  # noqa: E402

WEIGHTS = REPO / "experiments" / "candidate-assets" / "demucs-6s" / "5c90dfd2-34c22ccb.th"
WEIGHTS_SHA256 = "34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd"
EXPECTED_SOURCES = ["drums", "bass", "other", "vocals", "guitar", "piano"]
MODEL_RATE = 44100
OUT_RATE = 16000
SCHEMA = "strumalong-stem-stats-1"

FRAME = 2048
ACTIVE_RATIO = 0.03          # guitar frame energy >= 3% of the mix's frame energy (about -15 dB)
SILENCE_POWER = 1e-6         # mix frame mean square below this (-60 dBFS) is silence
LOW_BAND = (70.0, 250.0)
MID_BAND = (250.0, 4000.0)


def r6(x):
    return None if x is None else round(float(x), 6)


# ------------------------------------------------------------------------------------------------ pure statistics (numpy only)
def stem_energy_stats(stems):
    """stems: {name: 1-D array}. -> per-stem rms_dbfs / energy / energy_share and the guitar share of the harmonic bed."""
    energy = {k: float(np.mean(np.square(v, dtype=np.float64))) for k, v in stems.items()}
    total = sum(energy.values())
    share = {k: (e / total if total > 0 else 0.0) for k, e in energy.items()}
    db = {k: (10 * np.log10(e) if e > 0 else None) for k, e in energy.items()}
    harmonic = energy.get("guitar", 0) + energy.get("piano", 0) + energy.get("other", 0)
    return {
        "energy": {k: r6(v) for k, v in energy.items()},
        "energy_share": {k: r6(v) for k, v in share.items()},
        "rms_dbfs": {k: (None if v is None else round(float(v), 2)) for k, v in db.items()},
        "guitar_share_of_harmonic": r6(energy.get("guitar", 0) / harmonic) if harmonic > 0 else None,
    }


def guitar_band_stats(guitar, mix, sr=MODEL_RATE, frame=FRAME, active_ratio=ACTIVE_RATIO):
    """Low-band ratio of the guitar stem over its active frames (definition in the module docstring)."""
    n = min(len(guitar), len(mix)) // frame
    if n == 0:
        return {"frames": 0, "active_frames": 0, "active_fraction": 0.0, "low_band_ratio": None, "low_band_db": None, "centroid_hz": None}
    g = np.asarray(guitar[: n * frame], dtype=np.float64).reshape(n, frame)
    m = np.asarray(mix[: n * frame], dtype=np.float64).reshape(n, frame)
    eg, em = (g ** 2).mean(1), (m ** 2).mean(1)
    active = (em > SILENCE_POWER) & (eg >= active_ratio * em)
    out = {"frames": int(n), "active_frames": int(active.sum()), "active_fraction": r6(active.mean()),
           "active_ratio": active_ratio, "band_low_hz": list(LOW_BAND), "band_mid_hz": list(MID_BAND)}
    if not active.any():
        out.update(low_band_ratio=None, low_band_db=None, centroid_hz=None)
        return out
    win = np.hanning(frame)
    spec = np.abs(np.fft.rfft(g[active] * win, axis=1)) ** 2
    freqs = np.fft.rfftfreq(frame, 1.0 / sr)
    low = spec[:, (freqs >= LOW_BAND[0]) & (freqs < LOW_BAND[1])].sum()
    mid = spec[:, (freqs >= MID_BAND[0]) & (freqs < MID_BAND[1])].sum()
    ratio = float(low / mid) if mid > 0 else None
    centroid = float((spec * freqs).sum() / spec.sum()) if spec.sum() > 0 else None
    out.update(low_band_ratio=r6(ratio), low_band_db=(None if not ratio else round(10 * float(np.log10(ratio)), 2)),
               centroid_hz=(None if centroid is None else round(centroid, 1)))
    return out


# ------------------------------------------------------------------------------------------------ model
def load_model(threads):
    import torch
    import demucs
    from demucs.pretrained import get_model

    if not WEIGHTS.is_file():
        raise FileNotFoundError(f"weights not found: {WEIGHTS}")
    sha = file_sha256(WEIGHTS)
    if sha != WEIGHTS_SHA256:
        raise RuntimeError(f"demucs weights SHA-256 mismatch: {sha}")
    # A local repo: the approved .th (symlink, so no 50 MB copy) plus the package's own htdemucs_6s.yaml. With `repo` set,
    # demucs.pretrained.get_model never touches the network.
    repo = STEMS_DIR / "_demucs_repo"
    repo.mkdir(parents=True, exist_ok=True)
    link = repo / WEIGHTS.name
    if not link.exists():
        link.symlink_to(WEIGHTS)
    yaml_src = Path(demucs.__file__).parent / "remote" / "htdemucs_6s.yaml"
    yaml_dst = repo / "htdemucs_6s.yaml"
    if not yaml_dst.exists():
        yaml_dst.write_text(yaml_src.read_text())
    torch.set_num_threads(threads)
    model = get_model("htdemucs_6s", repo=repo)
    if list(model.sources) != EXPECTED_SOURCES:
        raise RuntimeError(f"unexpected sources {model.sources}")
    model.eval()
    return model, {"name": "htdemucs_6s", "demucs_version": getattr(demucs, "__version__", None),
                   "weights_file": WEIGHTS.name, "weights_sha256": sha, "sources": list(model.sources),
                   "samplerate": int(model.samplerate), "segment_seconds": float(model.models[0].segment) if hasattr(model, "models") else float(model.segment)}


def separate(model, wav, sr, device="cpu"):
    """wav: mono float32 at `sr`. -> (stems {name: mono float32 at 44.1 kHz}, mix mono float32 at 44.1 kHz)."""
    import julius
    import torch
    from demucs.apply import apply_model

    x = torch.from_numpy(np.ascontiguousarray(wav, dtype=np.float32))
    if sr != MODEL_RATE:
        x = julius.resample_frac(x, sr, MODEL_RATE)
    mix = x[None].repeat(2, 1)                         # dual mono, [2, T]
    ref = mix.mean(0)
    mean, std = ref.mean(), ref.std()
    norm = (mix - mean) / (std + 1e-8)                 # same normalisation as the demucs CLI
    with torch.no_grad():
        out = apply_model(model, norm[None], shifts=0, split=True, overlap=0.25, progress=False, device=device, num_workers=0)[0]
    out = out * (std + 1e-8) + mean                    # back to the file's own level
    mono = out.mean(1).numpy()                         # [S, T]
    stems = {name: mono[i].astype(np.float32) for i, name in enumerate(model.sources)}
    return stems, x.numpy().astype(np.float32)


def write_guitar16k(guitar44, path):
    import julius
    import soundfile as sf
    import torch

    g = julius.resample_frac(torch.from_numpy(np.ascontiguousarray(guitar44)), MODEL_RATE, OUT_RATE).numpy()
    clipped = int((np.abs(g) > 1.0).sum())
    g = np.clip(g, -1.0, 1.0)
    sf.write(str(path), g, OUT_RATE, subtype="PCM_16")
    return clipped, len(g)


def process(rec, model, model_info, args):
    import soundfile as sf

    out_dir = STEMS_DIR / rec["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    wav, sr = sf.read(str(rec["audio_path"]), dtype="float32", always_2d=False)
    if wav.ndim > 1:
        wav = wav.mean(1)
    dur = len(wav) / sr
    audio_sha = file_sha256(rec["audio_path"])
    t1 = time.time()
    stems, mix44 = separate(model, wav, sr, device=args.device)
    t2 = time.time()
    clipped, n16 = write_guitar16k(stems["guitar"], out_dir / "guitar16k.wav")
    stats = {
        "schema": SCHEMA,
        "recording_id": rec["id"], "pack": rec["pack"], "excluded": rec["excluded"],
        "audio_sha256": audio_sha, "pack_audio_sha256": rec["pack_audio_sha256"],
        "audio_sha256_matches_pack": (None if not rec["pack_audio_sha256"] else rec["pack_audio_sha256"] == audio_sha),
        "duration_seconds": round(dur, 3), "input_sample_rate_hz": int(sr),
        "model": model_info,
        "params": {"shifts": 0, "split": True, "overlap": 0.25, "device": args.device, "threads": args.threads,
                   "input": "mono duplicated to stereo, resampled to 44.1 kHz, demucs-CLI normalisation undone on output",
                   "guitar_stem_file": "guitar16k.wav", "guitar_stem_format": f"mono {OUT_RATE} Hz PCM16",
                   "guitar_stem_clipped_samples": clipped},
        "stems": stem_energy_stats(stems),
        "mix_rms_dbfs": round(float(10 * np.log10(max(float(np.mean(np.square(mix44, dtype=np.float64))), 1e-12))), 2),
        "guitar_band": guitar_band_stats(stems["guitar"], mix44),
        "timing": {"separation_seconds": round(t2 - t1, 2), "total_seconds": round(time.time() - t0, 2),
                   "realtime_factor": round((t2 - t1) / dur, 3)},
    }
    write_json_atomic(out_dir / "stats.json", stats)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="recording id(s), comma separated or repeated")
    ap.add_argument("--force", action="store_true", help="redo recordings whose stats.json exists")
    ap.add_argument("--threads", type=int, default=10, help="torch CPU threads (default 10 of 14 cores)")
    ap.add_argument("--device", default="cpu", help="torch device (default cpu)")
    ap.add_argument("--list", action="store_true", help="list recordings and what is already done, then exit")
    args = ap.parse_args(argv)

    recs = load_recordings(only=parse_only(args.only))
    todo = [r for r in recs if args.force or not (STEMS_DIR / r["id"] / "stats.json").exists()]
    if args.list:
        for r in recs:
            done = (STEMS_DIR / r["id"] / "stats.json").exists()
            print(f"{'done' if done else 'todo'}  {r['duration'] or 0:7.1f}s  {'EXCL ' if r['excluded'] else 'ship '} {r['id']}")
        print(f"{len(todo)} to do of {len(recs)}; audio total {sum((r['duration'] or 0) for r in todo) / 60:.1f} min to do")
        return 0
    print(f"{len(recs)} recordings, {len(recs) - len(todo)} already done, {len(todo)} to do", flush=True)
    if not todo:
        return 0
    t_load = time.time()
    model, info = load_model(args.threads)
    print(f"model loaded in {time.time() - t_load:.1f}s: sources {info['sources']}, weights sha256 {info['weights_sha256'][:12]}...", flush=True)

    failures, done_audio, done_sep = [], 0.0, 0.0
    t_batch = time.time()
    for i, rec in enumerate(todo, 1):
        if not rec["audio_exists"]:
            print(f"[{i}/{len(todo)}] {rec['id']}: audio missing at {rec['audio_path']}", flush=True)
            failures.append(rec["id"])
            continue
        try:
            st = process(rec, model, info, args)
        except Exception:
            traceback.print_exc()
            failures.append(rec["id"])
            continue
        t = st["timing"]
        done_audio += st["duration_seconds"]
        done_sep += t["separation_seconds"]
        gb = st["guitar_band"]
        print(f"[{i}/{len(todo)}] {rec['id']}  {st['duration_seconds']:.0f}s audio  separate {t['separation_seconds']:.1f}s "
              f"({t['realtime_factor']:.2f}x realtime)  total {t['total_seconds']:.1f}s  "
              f"guitar share {st['stems']['energy_share']['guitar']:.3f}  guitar/harmonic {st['stems']['guitar_share_of_harmonic']}  "
              f"low-band ratio {gb['low_band_ratio']}", flush=True)
    print(f"done in {(time.time() - t_batch) / 60:.1f} min; {len(todo) - len(failures)} ok, {len(failures)} failed", flush=True)
    if failures:
        print("failed: " + ", ".join(failures), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
