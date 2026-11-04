#!/usr/bin/env python
"""Strummed-or-picked features of the Demucs guitar stem, for the Strum Along instrument stage.

Run with the CREMA environment (librosa 0.9.2, numpy, scipy, soundfile), after stems_6s.py:

    .venv-crema/bin/python experiments/analysis/strumalong/strum_features.py [--only ID[,ID...]] [--jobs 7]

For every recording in strumalong/data/catalogue.json (excluded ones too: they are the labelled negatives) it reads

    experiments/generated/strumalong-stems/<id>/guitar16k.wav   Demucs htdemucs_6s guitar stem, mono 16 kHz (stems_6s.py)
    experiments/generated/strumalong-stems/<id>/stats.json      stem energy shares (stems_6s.py)
    the pack's rhythm case (beat_times_seconds) and primary.json (the raw CREMA chart)

and merges a `strum` block per recording into experiments/generated/strumalong-instrument-tags.json, keeping everything
yamnet_tags.py wrote (and adding a `stems` block copied from stats.json when the file has none yet). Nothing else is
written. Offline, no models, no lyrics. About 15 to 20 s for all 44 recordings with 7 processes.

The question is "does the guitar re-strike the whole chord on the beat?". A down-strum re-excites every string, so nearly every
sounding partial gets louder at once; a picked note or a riff excites one string while the others keep decaying.

- Attacks: librosa onset detection on the stem (onset_strength hop 128, n_fft 1024, lag 2, max_size 3, normalised by its 99th
  percentile; onset_detect delta 0.08, wait 6 frames = 48 ms). An attack is kept when its onset strength is >= 0.15 and the
  stem frame is within 25 dB of the stem's 95th-percentile RMS (the guitar is playing).
- On-beat attacks: within 60 ms of a beat of the pack's beat grid. Up-strums and off-beat attacks look like picking in every
  song (they hit a few strings), so only on-beat attacks carry the information.
- restrike (per attack): 2048-point STFT frames (8 ms hop) about 72 ms before and after the attack. The partial peaks of the
  "after" spectrum in 120-2000 Hz (local maxima over +-2 bins within 30 dB of the loudest) are counted, and restrike is the
  share of them that are louder after than before (before = max over +-1 bin). None with fewer than 3 peaks.
- restrike_onbeat = mean restrike over on-beat attacks; restrike_onbeat_se = its standard error (sd / sqrt n).
  HIGH = strummed. Calibration (25 October 2026, 44 recordings): the six founder-labelled picked or riff songs 0.583 to 0.630,
  the 36 strummed positives 0.592 to 0.918 (median 0.71). Dense 16th-note or distorted strumming and arrangement bleed lower it.
- single_onbeat (evidence only, not gated): on each on-beat attack the NEW energy (sqrt of the positive power change,
  100-1200 Hz) is folded into 12 pitch classes; the attack is "single" when only one tone of the chart's chord at that moment
  (chords with 3+ tones) gets at least 15% of the strongest chord tone's new energy. Share of single attacks. HIGH = picked.
  It depends on the CREMA chart being right.

These definitions and constants are the ones the gate in catalogue_checks.js was calibrated on (scratch study, 25 October
2026; see docs/STRUMALONG_CATALOGUE_CHECKS.md). Changing any of them needs a new calibration, so `version` names them.
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strumalong_common import (STEMS_DIR, TAGS_PATH, chord_pitch_classes, file_sha256, load_recordings,  # noqa: E402
                               parse_only, read_json, write_json_atomic)

SCHEMA = "strumalong-instrument-tags-1"
VERSION = "strum-features-1"
TOOL = "experiments/analysis/strumalong/strum_features.py"

SR = 16000
HOP = 128                # 8 ms
NFFT = 2048              # 128 ms analysis window
OFF = 9                  # before/after frames centred about 72-80 ms either side of the attack
ONSET_NFFT = 1024
ONSET_LAG, ONSET_MAX_SIZE, ONSET_DELTA, ONSET_WAIT = 2, 3, 0.08, 6
ACTIVE_DB = 25.0         # stem frame RMS within 25 dB of its 95th percentile
MIN_ONSET = 0.15         # normalised onset strength floor
BEAT_TOL = 0.06          # on-beat: within 60 ms of a beat
PEAK_LO, PEAK_HI, PEAK_RANGE_DB, MIN_PEAKS = 120.0, 2000.0, 30.0, 3
PC_LO, PC_HI = 100.0, 1200.0
SINGLE_REL = 0.15

PARAMS = {
    "sample_rate_hz": SR, "hop": HOP, "n_fft": NFFT, "pre_post_offset_frames": OFF, "onset_n_fft": ONSET_NFFT,
    "onset_lag": ONSET_LAG, "onset_max_size": ONSET_MAX_SIZE, "onset_delta": ONSET_DELTA, "onset_wait_frames": ONSET_WAIT,
    "active_db_below_p95": ACTIVE_DB, "min_onset_strength": MIN_ONSET, "beat_tolerance_seconds": BEAT_TOL,
    "peak_band_hz": [PEAK_LO, PEAK_HI], "peak_range_db": PEAK_RANGE_DB, "min_peaks": MIN_PEAKS,
    "pitch_class_band_hz": [PC_LO, PC_HI], "single_relative_energy": SINGLE_REL,
}
DEFINITION = ("restrike_onbeat: mean over guitar-stem attacks within 60 ms of a pack beat of the share of 120-2000 Hz partial "
              "peaks (within 30 dB of the loudest) that are louder ~72 ms after the attack than ~72 ms before; high = strummed. "
              "single_onbeat: share of those attacks whose new energy reaches only one tone of the chart's chord; high = picked.")


# ------------------------------------------------------------------------------------------------ pure helpers (numpy only)
def r4(x):
    return None if x is None else round(float(x), 4)


def pitch_class_matrix(freqs):
    """[12, bins]: linear split of each 100-1200 Hz bin between its two nearest pitch classes."""
    m = np.zeros((12, len(freqs)))
    midi = 69 + 12 * np.log2(np.maximum(freqs, 1e-3) / 440.0)
    for k in np.nonzero((freqs >= PC_LO) & (freqs <= PC_HI))[0]:
        pc = midi[k] % 12
        lo = int(np.floor(pc))
        w = pc - lo
        m[lo % 12, k] += 1 - w
        m[(lo + 1) % 12, k] += w
    return m


def restrike_share(pre_db, post_db, lo, hi):
    """Share of the post-attack partial peaks in bins [lo, hi) that got louder. A peak is a local maximum over +-2 bins
    within PEAK_RANGE_DB of the loudest bin; 'before' is the max over +-1 bin. None with fewer than MIN_PEAKS peaks."""
    seg = post_db[lo:hi]
    if len(seg) < 5:
        return None
    top = seg.max()
    ups = n = 0
    for i in range(2, len(seg) - 2):
        v = seg[i]
        if v < top - PEAK_RANGE_DB:
            continue
        if v >= seg[i - 1] and v >= seg[i + 1] and v >= seg[i - 2] and v >= seg[i + 2]:
            k = lo + i
            n += 1
            ups += v > pre_db[k - 1:k + 2].max()
    return ups / n if n >= MIN_PEAKS else None


def chord_tone_coverage(new_pc, pcs):
    """Number of chord tones (pitch classes `pcs`) that receive at least SINGLE_REL of the strongest chord tone's new energy.
    None for chords with fewer than 3 tones or no new energy on any chord tone."""
    if not pcs or len(pcs) < 3:
        return None
    ct = np.asarray(new_pc)[list(pcs)]
    if ct.max() <= 0:
        return None
    return int(np.sum(ct >= SINGLE_REL * ct.max()))


def chord_at(chords, t):
    for c in chords:
        if c["start_seconds"] <= t < c["end_seconds"]:
            return c["label"]
    return None


def summarise_attacks(rows):
    """rows: per attack (t, onset, beat_dist, restrike or nan, coverage or -1). -> the song-level numbers."""
    r = np.asarray(rows, dtype=float).reshape(-1, 5)
    on = r[:, 2] < BEAT_TOL
    rs = r[on & ~np.isnan(r[:, 3]), 3]
    cov = r[on & (r[:, 4] >= 0), 4]
    allrs = r[~np.isnan(r[:, 3]), 3]
    return {
        "restrike_onbeat": r4(rs.mean()) if len(rs) else None,
        "restrike_onbeat_se": r4(rs.std(ddof=1) / np.sqrt(len(rs))) if len(rs) >= 2 else None,
        "onbeat_attacks": int(len(rs)),
        "single_onbeat": r4(np.mean(cov <= 1)) if len(cov) else None,
        "single_onbeat_attacks": int(len(cov)),
        "restrike_all": r4(allrs.mean()) if len(allrs) else None,
        "attacks": int(len(r)),
    }


# ------------------------------------------------------------------------------------------------ signal analysis
def analyse_signal(y, beats, chords):
    """y: mono guitar stem at SR. beats: beat times (s). chords: [{start_seconds, end_seconds, label}] (the pack chart).
    -> summarise_attacks(...) plus the stem's active fraction."""
    import librosa

    beats = np.asarray(beats, dtype=float)
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=HOP)[0]
    rdb = 20 * np.log10(rms + 1e-9)
    active = rdb > np.percentile(rdb, 95) - ACTIVE_DB
    oenv = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, n_fft=ONSET_NFFT, fmax=8000, lag=ONSET_LAG,
                                        max_size=ONSET_MAX_SIZE)
    oenv = oenv / (np.percentile(oenv, 99) + 1e-9)
    onsets = librosa.onset.onset_detect(onset_envelope=oenv, sr=SR, hop_length=HOP, units="frames", wait=ONSET_WAIT,
                                        normalize=False, delta=ONSET_DELTA)
    power = np.abs(librosa.stft(y, n_fft=NFFT, hop_length=HOP)) ** 2
    db = 10 * np.log10(power + 1e-14)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=NFFT)
    lo, hi = int(np.searchsorted(freqs, PEAK_LO)), int(np.searchsorted(freqs, PEAK_HI))
    pcm = pitch_class_matrix(freqs)
    rows = []
    for f in onsets:
        if f - OFF - 1 < 0 or f + OFF + 2 >= power.shape[1] or not active[min(f, len(active) - 1)] or oenv[f] < MIN_ONSET:
            continue
        t = f * HOP / SR
        beat_dist = float(np.min(np.abs(beats - t))) if len(beats) else np.inf
        rs = restrike_share(db[:, f - OFF - 1:f - OFF + 1].mean(1), db[:, f + OFF:f + OFF + 2].mean(1), lo, hi)
        new = np.sqrt(np.clip(power[:, f + OFF:f + OFF + 2].mean(1) - power[:, f - OFF - 1:f - OFF + 1].mean(1), 0, None))
        cov = chord_tone_coverage(pcm @ new, chord_pitch_classes(chord_at(chords, t)))
        rows.append([t, float(oenv[f]), beat_dist, np.nan if rs is None else rs, -1 if cov is None else cov])
    out = summarise_attacks(rows)
    out["stem_active_fraction"] = r4(active.mean())
    return out


def analyse_recording(job):
    """job: {id, stem, stats, primary, beats}. -> (id, strum block or None, error text or None)."""
    import soundfile as sf

    try:
        y, sr = sf.read(job["stem"], dtype="float32")
        if sr != SR:
            raise ValueError(f"guitar stem is {sr} Hz, expected {SR}")
        if y.ndim > 1:
            y = y.mean(1)
        chart = read_json(job["primary"]) or {}
        block = analyse_signal(y, job["beats"], chart.get("chords") or [])
        stats = read_json(job["stats"]) or {}
        block.update({
            "attacks_per_beat": r4(block["attacks"] / len(job["beats"])) if job["beats"] else None,
            "beats": len(job["beats"]),
            "audio_sha256": stats.get("audio_sha256"),
            "stem_sha256": file_sha256(job["stem"]),
            "chart_sha256": file_sha256(job["primary"]) if Path(job["primary"]).is_file() else None,
            "version": VERSION,
        })
        return job["id"], block, None
    except Exception as exc:  # one bad recording does not stop the batch
        return job["id"], None, repr(exc)


def stems_from_stats(stats, rid):
    """The `stems` block yamnet_tags.py writes, for recordings it has not tagged yet (same fields, same source)."""
    s = stats.get("stems", {})
    band = stats.get("guitar_band") or {}
    return {
        "energy_share": s.get("energy_share"), "rms_dbfs": s.get("rms_dbfs"),
        "guitar_share_of_harmonic": s.get("guitar_share_of_harmonic"),
        "guitar_low_band_ratio": band.get("low_band_ratio"), "guitar_low_band_db": band.get("low_band_db"),
        "guitar_active_fraction": band.get("active_fraction"), "guitar_centroid_hz": band.get("centroid_hz"),
        "model": (stats.get("model") or {}).get("name"), "weights_sha256": (stats.get("model") or {}).get("weights_sha256"),
        "stats_file": f"experiments/generated/strumalong-stems/{rid}/stats.json",
    }


def merge_strum(existing, blocks, stems=None, meta=None):
    """Merge per-recording `strum` blocks into a tags document, keeping every other field (YAMNet scores, stems, ...).
    stems: optional {id: stems block} used only where an entry has none. meta: optional {id: {pack, excluded, ...}} for new
    entries. A document with another schema is replaced."""
    doc = dict(existing) if (existing or {}).get("schema") == SCHEMA else {"schema": SCHEMA}
    recs = {k: dict(v) for k, v in (doc.get("recordings") or {}).items()}
    for rid, block in blocks.items():
        entry = recs.get(rid) or dict((meta or {}).get(rid) or {})
        entry["strum"] = block
        if "stems" not in entry and stems and stems.get(rid):
            entry["stems"] = stems[rid]
        recs[rid] = entry
    doc["recordings"] = {k: recs[k] for k in sorted(recs)}
    doc["strum_features"] = {"tool": TOOL, "version": VERSION, "definition": DEFINITION, "params": PARAMS}
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="recording id(s), comma separated or repeated")
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--out", default=str(TAGS_PATH), help="tags JSON to merge into (default experiments/generated/strumalong-instrument-tags.json)")
    args = ap.parse_args(argv)

    recs = load_recordings(only=parse_only(args.only))
    jobs, stems, meta, failures = [], {}, {}, []
    for rec in recs:
        rid = rec["id"]
        stem, stats_path = STEMS_DIR / rid / "guitar16k.wav", STEMS_DIR / rid / "stats.json"
        if not stem.is_file() or not stats_path.is_file():
            print(f"{rid}: no guitar stem yet (run stems_6s.py), skipped", flush=True)
            failures.append(rid)
            continue
        stats = read_json(stats_path) or {}
        stems[rid] = stems_from_stats(stats, rid)
        meta[rid] = {"pack": rec["pack"], "excluded": rec["excluded"], **({"excluded_reason": rec["excluded_reason"]} if rec["excluded_reason"] else {})}
        jobs.append({"id": rid, "stem": str(stem), "stats": str(stats_path), "primary": str(rec["primary_path"]),
                     "beats": list((rec["rhythm"] or {}).get("beat_times_seconds") or [])})

    blocks = {}
    with ProcessPoolExecutor(max(1, args.jobs)) as pool:
        for rid, block, err in pool.map(analyse_recording, jobs):
            if err:
                print(f"{rid}: FAILED {err}", flush=True)
                failures.append(rid)
                continue
            blocks[rid] = block
            print(f"{rid:62s} on-beat {block['onbeat_attacks']:4d}  restrike {block['restrike_onbeat']}"
                  f" +- {block['restrike_onbeat_se']}  single {block['single_onbeat']}", flush=True)

    out = Path(args.out)
    doc = merge_strum(read_json(out), blocks, stems, meta)
    write_json_atomic(out, doc)
    print(f"wrote {out} ({len(blocks)} strum blocks updated, {len(failures)} skipped or failed)", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
