"""Estimate pulse grids for exact local play-along WAVs, without bar/downbeat claims.

Meter and initial tempo hints are explicit curated inputs. The tracker returns
uncalibrated pulse positions; half/double tempo and compound-meter ambiguities
remain possible. Chord predictions and their boundaries are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import wave

SCHEMA = "playalong-rhythm-1.0"
CONFIG_SCHEMA = "playalong-rhythm-config-1.0"
VERSION = "0.1.0"
SAMPLE_RATE = 22050
HOP_SAMPLES = 512
MAX_DURATION_SECONDS = 600
MAX_BEATS = 5000
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,127}")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _load_json(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError(f"Nonfinite JSON number: {value}")
    packet = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    if not isinstance(packet, dict):
        raise ValueError("Expected a JSON object")
    return packet, hashlib.sha256(raw).hexdigest()


def validate_config(config: dict, recording_ids: set[str]) -> dict:
    if not isinstance(config, dict) or config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError(f"Expected rhythm config schema_version {CONFIG_SCHEMA}")
    settings = config.get("recordings")
    if not isinstance(settings, dict) or set(settings) != recording_ids:
        raise ValueError("Rhythm config recording IDs must exactly match the play-along manifest")
    for identifier, setting in settings.items():
        if not isinstance(setting, dict):
            raise ValueError(f"Config for {identifier} must be an object")
        start_bpm = setting.get("start_bpm")
        if not _number(start_bpm) or not 20 <= start_bpm <= 300:
            raise ValueError(f"Config start_bpm for {identifier} must be between 20 and 300")
        lower, upper = setting.get("tempo_min_bpm"), setting.get("tempo_max_bpm")
        if lower is not None or upper is not None:
            if (not _number(lower) or not _number(upper) or not 20 <= lower < upper <= 300
                    or not lower <= start_bpm <= upper):
                raise ValueError("Tempo range must have finite 20 <= min < max <= 300 and contain start_bpm")
        beats = setting.get("beats_per_bar")
        if beats is not None and (isinstance(beats, bool) or not isinstance(beats, int) or beats not in (2, 4)):
            raise ValueError("beats_per_bar must be null, 2 or 4; tracker pulses do not infer meter")
        for name in ("meter_label", "meter_status"):
            if not _text(setting.get(name)):
                raise ValueError(f"Config {name} for {identifier} is required")
        try:
            json.dumps(setting, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise ValueError("Rhythm config must contain finite JSON data") from error
    return settings


def verify_audio(path: Path, recording: dict) -> None:
    if digest(path) != recording["audio_sha256"]:
        raise ValueError("Audio SHA-256 differs from its declared recording")
    try:
        with wave.open(str(path), "rb") as stream:
            if (stream.getnchannels() != 1 or stream.getsampwidth() != 2
                    or stream.getcomptype() != "NONE" or stream.getframerate() != SAMPLE_RATE):
                raise ValueError("Rhythm input must be PCM16 mono WAV at 22050 Hz")
            frames = stream.getnframes()
            if frames < 1 or abs(frames / SAMPLE_RATE - recording["duration_seconds"]) > 1 / SAMPLE_RATE:
                raise ValueError("Audio duration differs from its declared recording")
            # Reject truncated WAVs before inference instead of loading fewer samples.
            remaining = frames * 2
            while remaining:
                chunk = stream.readframes(min(65536, remaining // 2))
                if not chunk:
                    raise ValueError("Audio WAV is truncated")
                remaining -= len(chunk)
    except wave.Error as error:
        raise ValueError("Rhythm input is not a readable PCM WAV") from error


def check_output(output: Path, protected: list[Path], *, overwrite: bool) -> None:
    for source in protected:
        if output.resolve() == source.resolve() or (
                output.exists() and source.exists() and output.samefile(source)):
            raise ValueError("Output cannot overwrite or alias an input")
    if output.is_symlink():
        raise ValueError("Output cannot be a symlink")
    if output.exists() and not overwrite:
        raise ValueError("Output exists; use --overwrite explicitly")
    if output.exists() and not output.is_file():
        raise ValueError("Output must be a regular file")


def preflight(manifest_path: Path, config_path: Path, output: Path, *, overwrite: bool = False) -> dict:
    manifest, manifest_hash = _load_json(manifest_path)
    config, config_hash = _load_json(config_path)
    if manifest.get("schema_version") != "automatic-drafts-1.0":
        raise ValueError("Expected an automatic-drafts-1.0 play-along manifest")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ValueError("Manifest must contain 1–64 recording cases")
    pack = manifest_path.parent.resolve(strict=True)
    rows, identifiers = [], set()
    for case in cases:
        identifier = case.get("id") if isinstance(case, dict) else None
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier) or identifier in identifiers:
            raise ValueError("Unique safe case IDs are required")
        identifiers.add(identifier)
        recording = case.get("recording")
        if not isinstance(recording, dict) or recording.get("id") != identifier or not _text(recording.get("title")):
            raise ValueError("Case and recording identity must match; recording title is required")
        if recording.get("sample_rate_hz") != SAMPLE_RATE or isinstance(recording.get("sample_rate_hz"), bool):
            raise ValueError("Recording sample_rate_hz must be 22050")
        duration = recording.get("duration_seconds")
        if not _number(duration) or not 0 < duration <= MAX_DURATION_SECONDS:
            raise ValueError("Recording duration must be positive and at most 600 seconds")
        if not isinstance(recording.get("audio_sha256"), str) or not SHA_PATTERN.fullmatch(recording["audio_sha256"]):
            raise ValueError("Recording needs its exact audio SHA-256")
        if case.get("audio_url") != f"/cases/{identifier}/audio.wav":
            raise ValueError("Manifest audio_url must identify its fixed case WAV")
        audio = (pack / "cases" / identifier / "audio.wav").resolve(strict=True)
        if not audio.is_relative_to(pack) or not audio.is_file():
            raise ValueError("Case audio must be a file inside the play-along pack")
        rows.append({"id": identifier, "recording": recording, "audio": audio})
    settings = validate_config(config, identifiers)
    protected = [manifest_path, config_path, *(row["audio"] for row in rows)]
    check_output(output, protected, overwrite=overwrite)
    # Complete validation of every waveform before loading librosa or tracking one.
    for row in rows:
        verify_audio(row["audio"], row["recording"])
    return {"manifest": manifest, "manifest_sha256": manifest_hash, "config": config,
            "config_sha256": config_hash, "rows": rows, "settings": settings, "protected": protected}


class TempoRangePrior:
    """A declared tempo-level constraint, not evidence or probability confidence."""
    def __init__(self, start_bpm: float, lower: float, upper: float):
        self.start_bpm, self.lower, self.upper = start_bpm, lower, upper

    def logpdf(self, value):
        import numpy as np
        value = np.asarray(value, dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            weight = -.5 * (np.log2(value) - np.log2(self.start_bpm)) ** 2
        return np.where((value >= self.lower) & (value <= self.upper), weight, -np.inf)


def track_audio(audio: Path, setting: dict) -> dict:
    """Lazy optional dependency: tests and input validation need no librosa."""
    import librosa
    import numpy as np
    y, sample_rate = librosa.load(audio, sr=SAMPLE_RATE, mono=True)
    onsets = librosa.onset.onset_strength(y=y, sr=sample_rate, hop_length=HOP_SAMPLES, aggregate=np.mean)
    kwargs = {}
    if setting.get("tempo_min_bpm") is not None:
        prior = TempoRangePrior(setting["start_bpm"], setting["tempo_min_bpm"], setting["tempo_max_bpm"])
        selected = librosa.beat.tempo(onset_envelope=onsets, sr=sample_rate,
            hop_length=HOP_SAMPLES, prior=prior)
        selected_bpm = float(selected[0])
        if not setting["tempo_min_bpm"] <= selected_bpm <= setting["tempo_max_bpm"]:
            raise ValueError("No native tempo candidate satisfies the declared tempo range")
        kwargs["bpm"] = selected_bpm
    tempo, beats = librosa.beat.beat_track(onset_envelope=onsets, sr=sample_rate,
        hop_length=HOP_SAMPLES, start_bpm=setting["start_bpm"], tightness=100,
        trim=True, units="time", **kwargs)
    return {"pulse_bpm": float(tempo), "beat_times_seconds": [float(value) for value in beats],
            "library_version": librosa.__version__}


def validate_pulses(prediction: dict, duration: float) -> None:
    if not isinstance(prediction, dict):
        raise ValueError("Tracker must return a prediction object")
    bpm = prediction.get("pulse_bpm")
    if not _number(bpm) or not 20 <= bpm <= 300:
        raise ValueError("Estimated pulse BPM must be finite and between 20 and 300")
    beats = prediction.get("beat_times_seconds")
    if (not isinstance(beats, list) or not 2 <= len(beats) <= MAX_BEATS
            or any(not _number(value) or not 0 <= value < duration for value in beats)
            or any(first >= second for first, second in zip(beats, beats[1:]))):
        raise ValueError("Need 2–5000 strictly increasing pulse times inside the exact recording")
    if not _text(prediction.get("library_version")):
        raise ValueError("Tracker must identify its library version")


def _publish(output: Path, result: dict, protected: list[Path], *, overwrite: bool) -> None:
    check_output(output, protected, overwrite=overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{output.name}.",
                                         dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        check_output(output, protected, overwrite=overwrite)
        if overwrite:
            os.replace(temporary, output)
        else:
            try:
                os.link(temporary, output)
            except FileExistsError as error:
                raise ValueError("Output appeared during inference; refusing to overwrite it") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build(manifest_path: Path, config_path: Path, output: Path, *, overwrite: bool = False) -> dict:
    started = time.perf_counter()
    packet = preflight(manifest_path, config_path, output, overwrite=overwrite)
    result = {"schema_version": SCHEMA, "version": VERSION,
              "pack_id": packet["manifest"].get("pack_id"), "status": "estimated",
              "gold": False, "manifest_sha256": packet["manifest_sha256"],
              "config_sha256": packet["config_sha256"],
              "semantics": "Audio-derived pulse estimates, with declared meter hypotheses; no verified downbeats, bar starts or chord boundary snapping.",
              "cases": []}
    for row in packet["rows"]:
        case_started = time.perf_counter()
        setting = packet["settings"][row["id"]]
        try:
            prediction = track_audio(row["audio"], setting)
            validate_pulses(prediction, row["recording"]["duration_seconds"])
        except (ValueError, ImportError) as error:
            raise ValueError(f"Recording {row['id']}: {error}") from error
        if digest(row["audio"]) != row["recording"]["audio_sha256"]:
            raise ValueError("Audio changed during rhythm inference")
        result["cases"].append({"recording": dict(row["recording"]),
            "beat_times_seconds": prediction["beat_times_seconds"], "pulse_bpm": prediction["pulse_bpm"],
            "beats_per_bar": setting.get("beats_per_bar"), "meter_label": setting["meter_label"],
            "status": "estimated", "analysis": {"id": f"librosa-pulse-grid-{VERSION}",
                "library": "librosa", "library_version": prediction["library_version"],
                "runtime_seconds": time.perf_counter() - case_started,
                "parameters": {"sample_rate_hz": SAMPLE_RATE, "hop_samples": HOP_SAMPLES,
                    "start_bpm": setting["start_bpm"], "onset_aggregate": "mean",
                    "tightness": 100, "trim": True, "units": "time", "source_separation": "none",
                    "tempo_min_bpm": setting.get("tempo_min_bpm"), "tempo_max_bpm": setting.get("tempo_max_bpm"),
                    "tempo_selection": "native autocorrelation candidates with declared range prior" if setting.get("tempo_min_bpm") is not None else "native default pseudo-log-normal prior centered on start_bpm"},
                "config_status": setting["meter_status"], "config": dict(setting),
                "score_is_calibrated_confidence": False, "downbeats_inferred": False,
                "chord_boundaries_snapped": False,
                "limitations": ["Declared priors/ranges select a metrical hypothesis; they do not verify pulse units or force chord timing.",
                    "Half/double tempo, subdivisions and compound-meter ambiguities remain possible.",
                    "Returned pulse phase does not establish a downbeat or absolute bar number.",
                    "Leading/trailing weak pulses are trimmed; unsupported spans should retain a seconds fallback."]}})
    if digest(manifest_path) != packet["manifest_sha256"] or digest(config_path) != packet["config_sha256"]:
        raise ValueError("Manifest or config changed during rhythm inference")
    for row in packet["rows"]:
        if digest(row["audio"]) != row["recording"]["audio_sha256"]:
            raise ValueError("Audio changed after its rhythm inference")
    result["runtime_seconds"] = time.perf_counter() - started
    _publish(output, result, packet["protected"], overwrite=overwrite)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        result = build(args.manifest, args.config, args.output, overwrite=args.overwrite)
    except (ValueError, OSError, json.JSONDecodeError, ImportError) as error:
        parser.exit(2, f"Rhythm estimation failed: {error}\n")
    print(json.dumps({"output": str(args.output), "status": result["status"], "cases": len(result["cases"]),
                      "runtime_seconds": result["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
