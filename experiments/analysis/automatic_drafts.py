"""Prepare full-song play-along drafts automatically from saved detector outputs.

CREMA remains the unchanged primary timeline. Other models provide disagreement
evidence, never a vote, reference annotation, or calibrated confidence score.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import wave

import lab
import review_pack

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "experiments" / "review"
DEFAULT_MANIFEST = ROOT / "experiments" / "generated" / "youtube-pilot" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "generated" / "automatic-playalong"
SCHEMA = "automatic-drafts-1.0"
EVIDENCE_SCHEMA = "automatic-draft-evidence-1.0"
VERSION = "0.1.0"
LABEL_RE = re.compile(r"^([A-G](?:#|b)?)(.*)$")
PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR = {"", "maj", "7", "maj7", "6", "maj6", "9", "maj9", "11", "13", "add9"}
MINOR = {"m", "min", "m7", "min7", "m6", "min6", "m9", "min9", "m11", "min11",
         "m13", "min13", "mmaj7", "minmaj7"}
LABEL_FLAG_KINDS = {"root_disagreement", "majmin_disagreement", "no_chord_disagreement", "unresolved_label"}
PRACTICE_GUIDES = {
    "radiohead-creep-youtube-20261010": {"capo": 0, "source_url": "https://guitarlessons365.com/creep-guitar-lesson-radiohead/"},
    "oasis-wonderwall-youtube-20261010": {"capo": 2, "source_url": "https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/"},
    "animals-house-rising-sun-youtube-20261010": {"capo": 0, "source_url": "https://guitarlessons365.com/how-to-play-the-house-of-the-rising-sun-the-animals/"},
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def label_signature(label: str) -> tuple[int | str | None, str | None]:
    """Enharmonic root and supported major/minor family; sus/dim/aug stay unknown.

    This deliberately ignores inversions for comparison only. The original
    labels, native labels, and qualities are retained in every saved chart.
    """
    if label == "N":
        return "N", "N"
    if label in {"X", "?"}:
        return None, None
    match = LABEL_RE.fullmatch(label.split("/", 1)[0])
    if not match:
        return None, None
    name, suffix = match.groups()
    root = (PITCH[name[0]] + (1 if name.endswith("#") else -1 if name.endswith("b") else 0)) % 12
    suffix = suffix.removeprefix(":")
    return root, "maj" if suffix in MAJOR else "min" if suffix in MINOR else None


def paired_recording(primary: dict, secondary: dict) -> dict:
    for chart in (primary, secondary):
        lab.validate_chart(chart)
        recording = chart["recording"]
        if not isinstance(recording.get("audio_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", recording["audio_sha256"]):
            raise ValueError("Prediction must identify its exact prepared audio SHA-256")
        tolerance = 1 / recording["sample_rate_hz"]
        previous = 0.0
        for event in chart["chords"]:
            if abs(event["start_seconds"] - previous) > tolerance:
                raise ValueError("Automatic drafts require full, contiguous prediction coverage")
            previous = event["end_seconds"]
        if abs(previous - recording["duration_seconds"]) > tolerance:
            raise ValueError("Prediction must reach the prepared audio end")
    first, second = primary["recording"], secondary["recording"]
    for field in ("id", "audio_sha256", "sample_rate_hz"):
        if first[field] != second[field]:
            raise ValueError(f"Predictions must match recording {field}")
    if abs(first["duration_seconds"] - second["duration_seconds"]) > 1 / first["sample_rate_hz"]:
        raise ValueError("Prediction durations must match to one sample")
    return dict(first)


def merged_flags(raw: list[dict], merge_gap_seconds: float, min_flag_seconds: float) -> list[dict]:
    merged = []
    for kind in sorted({span["priority_kind"] for span in raw}):
        group = []
        for span in sorted((s for s in raw if s["priority_kind"] == kind), key=lambda s: s["start_seconds"]):
            if group and span["start_seconds"] - group[-1]["end_seconds"] <= merge_gap_seconds:
                group[-1]["end_seconds"] = max(group[-1]["end_seconds"], span["end_seconds"])
                group[-1]["details"].extend(span["details"])
            else:
                group.append({**span, "details": list(span["details"])})
        merged.extend(s for s in group if s["end_seconds"] - s["start_seconds"] >= min_flag_seconds)
    merged.sort(key=lambda s: (s["start_seconds"], s["priority_kind"]))
    for index, span in enumerate(merged):
        span["id"] = f"flag-{index + 1:03d}"
    return merged


def suggested_points(flags: list[dict], duration: float, maximum: int) -> list[dict]:
    """At most a few separated, automatically selected checks; all are optional."""
    kinds = {"root_disagreement": 4, "no_chord_disagreement": 4, "majmin_disagreement": 3,
             "unresolved_label": 2, "boundary_disagreement": 1}
    ranked = sorted(flags, key=lambda s: (-kinds[s["priority_kind"]], -(s["end_seconds"] - s["start_seconds"]), s["start_seconds"]))
    selected, centers = [], []
    for span in ranked:
        center = (span["start_seconds"] + span["end_seconds"]) / 2
        if any(abs(center - previous) < 8 for previous in centers):
            continue
        centers.append(center)
        selected.append({"id": f"check-{len(selected) + 1:02d}", "flag_id": span["id"],
                         "start_seconds": max(0.0, center - 3), "end_seconds": min(duration, center + 3),
                         "reason": span["reason"], "priority_kind": span["priority_kind"]})
        if len(selected) >= maximum:
            break
    return sorted(selected, key=lambda s: s["start_seconds"])


def compare_charts(primary: dict, secondary: dict, boundary_tolerance_seconds: float = 0.5,
                   merge_gap_seconds: float = 0.4, min_flag_seconds: float = 0.4,
                   max_review_points: int = 8) -> dict:
    recording = paired_recording(primary, secondary)
    for value in (boundary_tolerance_seconds, merge_gap_seconds, min_flag_seconds):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("Comparison limits must be finite and nonnegative")
    if not isinstance(max_review_points, int) or isinstance(max_review_points, bool) or not 1 <= max_review_points <= 32:
        raise ValueError("Choose 1–32 optional check spots")
    duration = recording["duration_seconds"]
    raw, root_total, root_same, majmin_total, majmin_same = [], 0.0, 0.0, 0.0, 0.0
    first, second, i, j = primary["chords"], secondary["chords"], 0, 0
    reasons = {"root_disagreement": "Models propose different chord roots",
               "majmin_disagreement": "Models disagree on major versus minor",
               "no_chord_disagreement": "One model proposes no chord while the other proposes harmony",
               "unresolved_label": "A model leaves this interval unresolved",
               "boundary_disagreement": "A chord change lacks a nearby change in the other model"}
    while i < len(first) and j < len(second):
        a, b = first[i], second[j]
        start, end = max(a["start_seconds"], b["start_seconds"]), min(a["end_seconds"], b["end_seconds"])
        if end > start:
            ar, aq = label_signature(a["label"])
            br, bq = label_signature(b["label"])
            # Fractions exclude N/unknown rather than awarding silence credit.
            if isinstance(ar, int) and isinstance(br, int):
                root_total += end - start
                root_same += (end - start) * (ar == br)
            if isinstance(ar, int) and isinstance(br, int) and aq in {"maj", "min"} and bq in {"maj", "min"}:
                majmin_total += end - start
                majmin_same += (end - start) * ((ar, aq) == (br, bq))
            kind = ("unresolved_label" if ar is None or br is None else
                    "no_chord_disagreement" if (ar == "N") != (br == "N") else
                    "root_disagreement" if ar != br else
                    "majmin_disagreement" if aq in {"maj", "min"} and bq in {"maj", "min"} and aq != bq else None)
            if kind:
                raw.append({"start_seconds": start, "end_seconds": end, "reason": reasons[kind], "priority_kind": kind,
                            "details": [{"start_seconds": start, "end_seconds": end,
                                         "primary_label": a["label"], "secondary_label": b["label"]}]})
        a_end, b_end = a["end_seconds"], b["end_seconds"]
        if a_end <= b_end:
            i += 1
        if b_end <= a_end:
            j += 1
    boundaries = [[event["start_seconds"] for event in chart["chords"][1:]] for chart in (primary, secondary)]
    # Greedy one-to-one matching, in time order, avoids crediting one boundary twice.
    ai, bi, matches = 0, 0, 0
    unmatched = []
    while ai < len(boundaries[0]) and bi < len(boundaries[1]):
        a, b = boundaries[0][ai], boundaries[1][bi]
        if abs(a - b) <= boundary_tolerance_seconds:
            matches += 1
            ai += 1
            bi += 1
        elif a < b:
            unmatched.append((a, "primary"))
            ai += 1
        else:
            unmatched.append((b, "secondary"))
            bi += 1
    unmatched.extend((v, "primary") for v in boundaries[0][ai:])
    unmatched.extend((v, "secondary") for v in boundaries[1][bi:])
    raw_label_spans = [{**span, "details": list(span["details"])} for span in raw]
    for timestamp, model in unmatched:
        raw.append({"start_seconds": max(0.0, timestamp - 0.75), "end_seconds": min(duration, timestamp + 0.75),
                    "reason": reasons["boundary_disagreement"], "priority_kind": "boundary_disagreement",
                    "details": [{"boundary_seconds": timestamp, "model": model}]})
    flags = merged_flags(raw, merge_gap_seconds, min_flag_seconds)
    points = suggested_points(flags, duration, max_review_points)
    boundary_total = len(boundaries[0]) + len(boundaries[1])
    return {"schema_version": EVIDENCE_SCHEMA, "recording": recording,
            "status": "automatic unreviewed evidence; no reference annotation", "gold": False,
            "semantics": "Detector agreement is a heuristic. Shared errors survive agreement; these fractions measure agreement, not accuracy or confidence. No manual annotation is required for playback.",
            "comparison": {"primary_algorithm": primary["analysis"]["algorithm"], "secondary_algorithm": secondary["analysis"]["algorithm"]},
            "metrics": {"root_agreement_fraction": root_same / root_total if root_total else None,
                        "root_compared_seconds": root_total, "root_coverage_fraction": root_total / duration,
                        "majmin_agreement_fraction": majmin_same / majmin_total if majmin_total else None,
                        "majmin_compared_seconds": majmin_total, "majmin_coverage_fraction": majmin_total / duration,
                        "boundary_match_fraction": 2 * matches / boundary_total if boundary_total else None,
                        "boundary_matches": matches, "primary_boundaries": len(boundaries[0]), "secondary_boundaries": len(boundaries[1]),
                        "flags_total": len(flags), "review_points_count": len(points)},
            "parameters": {"boundary_tolerance_seconds": boundary_tolerance_seconds, "merge_gap_seconds": merge_gap_seconds,
                           "min_flag_seconds": min_flag_seconds, "max_review_points": max_review_points,
                           "root_policy": "enharmonic root; ignore inversion; exclude N/unknown from denominator",
                           "majmin_policy": "supported major/minor families only; sus/dim/aug/unknown excluded; extensions and inversions preserved in charts",
                           "review_point_policy": "kind priority, then longest merged spans; separated by at least 8 seconds; at most six seconds per spot"},
            "raw_label_disagreements": raw_label_spans, "flags": flags, "review_points": points}


def verified_audio(path: Path, recording: dict) -> None:
    if digest(path) != recording.get("audio_sha256"):
        raise ValueError("Prepared audio SHA-256 does not match source recording")
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("Use prepared mono PCM16 WAV")
        rate, frames = audio.getframerate(), audio.getnframes()
        if rate != recording.get("sample_rate_hz") or abs(frames / rate - recording.get("duration_seconds", -1)) > 1 / rate:
            raise ValueError("Prepared audio sample rate/duration does not match source recording")
        if len(audio.readframes(frames)) != frames * 2:
            raise ValueError("Prepared audio is truncated")


def project_input(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("Automatic draft inputs must be regular project-local files")
    return resolved


def build(manifest_path: Path, output: Path = DEFAULT_OUTPUT, source_root: Path = ROOT,
          additional: dict[str, list[Path]] | None = None) -> dict:
    source_root = source_root.resolve()
    manifest_path = project_input(manifest_path, source_root)
    pilot = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = pilot.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ValueError("Expected 1–64 prepared recording cases")
    output = output.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory; automatic packs are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".automatic-playalong-", dir=output.parent))
    result = {"schema_version": SCHEMA, "pack_id": output.name, "status": "automatic unreviewed play-along drafts",
              "gold": False, "semantics": "CREMA primary charts load immediately. Model disagreement suggests optional check spots; agreement is not accuracy. No manual timing annotation is required.",
              "primary_selection": "CREMA chosen from the small acoustic GuitarSet pilot; full-mix performance is unverified. Raw native outputs are unchanged.",
              "cases": []}
    seen = set()
    additional = additional or {}
    try:
        for case in cases:
            identifier = case.get("id")
            if not review_pack.safe_id(identifier) or identifier in seen:
                raise ValueError("Unique safe recording IDs are required")
            seen.add(identifier)
            relative = case.get("audio")
            if not isinstance(relative, str) or Path(relative).is_absolute():
                raise ValueError("Case audio paths must be manifest-relative")
            audio_path = project_input(manifest_path.parent / relative, source_root)
            if not audio_path.is_relative_to(manifest_path.parent):
                raise ValueError("Case audio must remain inside its prepared pilot")
            source_recording = case.get("source", {}).get("recording", {})
            if source_recording.get("id") != identifier:
                raise ValueError("Source metadata must identify this recording")
            verified_audio(audio_path, source_recording)
            primary_path = project_input(audio_path.parent / "crema.json", source_root)
            secondary_path = project_input(audio_path.parent / "chordino.json", source_root)
            primary = json.loads(primary_path.read_text(encoding="utf-8"))
            secondary = json.loads(secondary_path.read_text(encoding="utf-8"))
            evidence = compare_charts(primary, secondary)
            paired_recording(primary, {**primary, "recording": source_recording})
            folder = staging / "cases" / identifier
            folder.mkdir(parents=True)
            for source, name in ((audio_path, "audio.wav"), (primary_path, "primary.json"), (secondary_path, "chordino.json")):
                shutil.copyfile(source, folder / name)
                if digest(folder / name) != digest(source):
                    raise ValueError("Copied automatic pack artifact hash differs")
            write_json(folder / "evidence.json", evidence)
            extras = []
            for index, candidate_path in enumerate(additional.get(identifier, [])):
                if index >= 4:
                    raise ValueError("At most four additional evidence charts per recording")
                candidate_path = project_input(candidate_path, source_root)
                candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                compared = compare_charts(primary, candidate)
                chart_name, evidence_name = f"additional-{index + 1}.json", f"additional-{index + 1}-evidence.json"
                shutil.copyfile(candidate_path, folder / chart_name)
                write_json(folder / evidence_name, compared)
                extras.append({"name": candidate["analysis"]["algorithm"], "url": f"/cases/{identifier}/{chart_name}",
                               "evidence_url": f"/cases/{identifier}/{evidence_name}",
                               "role": "Additional hypothesis only; not used to select or vote on primary chords", "summary": compared["metrics"]})
            record = {**primary["recording"], "title": case.get("name", primary["recording"]["title"])}
            result["cases"].append({"id": identifier, "name": record["title"], "recording": record,
                                    "audio_url": f"/cases/{identifier}/audio.wav", "primary_url": f"/cases/{identifier}/primary.json",
                                    "evidence_url": f"/cases/{identifier}/evidence.json",
                                    "primary_name": "CREMA automatic draft", "primary_status": "Unreviewed native model output",
                                    "secondary": [{"name": "Chordino", "url": f"/cases/{identifier}/chordino.json"}],
                                    "additional": extras, "summary": evidence["metrics"], "source": case.get("source", {}),
                                    "artifacts": {"primary_sha256": digest(primary_path), "chordino_sha256": digest(secondary_path)},
                                    "origin": {"source_recording_id": identifier, "source_audio_sha256": record["audio_sha256"], "source_offset_seconds": 0}})
            if identifier in PRACTICE_GUIDES:
                result["cases"][-1]["practice"] = {**PRACTICE_GUIDES[identifier], "label_convention": "sounding pitches in raw charts",
                                                   "status": "Teacher-guide capo suggestion; any displayed capo shapes are a separate practice view, not detector labels or reference annotations"}
        if set(additional) - seen:
            raise ValueError("Additional evidence must identify an existing case")
        write_json(staging / "manifest.json", result)
        write_json(staging / "build-spec.json", {"input_manifest": str(manifest_path.relative_to(source_root)),
                                                   "version": VERSION, "primary": "crema.json", "secondary": "chordino.json"})
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging)
        raise
    return result


def public_files(pack: Path) -> dict[str, Path]:
    pack = pack.resolve()
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != SCHEMA or not isinstance(manifest.get("cases"), list)
            or not 1 <= len(manifest["cases"]) <= 64):
        raise ValueError("Invalid automatic play-along manifest")
    files = {"/": STATIC / "index.html", "/index.html": STATIC / "index.html", "/app.js": STATIC / "app.js",
             "/style.css": STATIC / "style.css", "/manifest.json": pack / "manifest.json"}
    # Optional duration/practice metadata has fixed static URLs; never accept
    # caller-supplied paths or expose arbitrary repository files.
    for name in ("rhythm.json", "practice.json", "learning.json"):
        path = STATIC / name
        if path.exists() or path.is_symlink():
            files["/" + name] = path
    seen = set()
    for case in manifest["cases"]:
        identifier = case["id"]
        if not review_pack.safe_id(identifier) or identifier in seen:
            raise ValueError("Invalid or duplicate recording ID")
        seen.add(identifier)
        expected = [(case["audio_url"], "audio.wav"), (case["primary_url"], "primary.json"), (case["evidence_url"], "evidence.json")]
        if not isinstance(case.get("secondary"), list) or len(case["secondary"]) != 1:
            raise ValueError("Automatic packs have exactly one Chordino comparison chart")
        expected.append((case["secondary"][0]["url"], "chordino.json"))
        if not isinstance(case.get("additional", []), list) or len(case.get("additional", [])) > 4:
            raise ValueError("Automatic packs allow at most four additional charts")
        for index, item in enumerate(case.get("additional", [])):
            expected.append((item["url"], f"additional-{index + 1}.json"))
            expected.append((item["evidence_url"], f"additional-{index + 1}-evidence.json"))
        for url, filename in expected:
            if url != f"/cases/{identifier}/{filename}":
                raise ValueError("Unexpected automatic pack asset URL")
            files[url] = pack / "cases" / identifier / filename
    for path in files.values():
        root = STATIC.resolve() if path.is_relative_to(STATIC) else pack
        if not review_pack.safe_public_file(path, root, pack):
            raise ValueError("Public assets must be regular files inside their fixed root")
    return files


def serve(pack: Path, port: int = 8068) -> None:
    # Both interfaces use the same reviewed static directory and guarded handler.
    if STATIC != review_pack.STATIC:
        raise ValueError("Automatic player static root differs from guarded handler root")
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(review_pack.ReviewHandler, files=public_files(pack)))
    print(f"Automatic play-along: http://127.0.0.1:{port}/ — full drafts ready; optional corrections only", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build")
    builder.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    builder.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    builder.add_argument("--additional", action="append", default=[], metavar="RECORDING_ID=PROJECT_PATH")
    server = sub.add_parser("serve")
    server.add_argument("--pack", type=Path, default=DEFAULT_OUTPUT)
    server.add_argument("--port", type=int, default=8068)
    args = parser.parse_args()
    try:
        if args.command == "build":
            extra = {}
            for value in args.additional:
                identifier, separator, relative = value.partition("=")
                if not separator or not review_pack.safe_id(identifier) or Path(relative).is_absolute():
                    raise ValueError("Additional charts use RECORDING_ID=PROJECT_RELATIVE_PATH")
                extra.setdefault(identifier, []).append(ROOT / relative)
            result = build(args.manifest, args.output, additional=extra)
            print(json.dumps({"pack": str(args.output.resolve()), "cases": len(result["cases"]), "status": result["status"]}))
        else:
            serve(args.pack, args.port)
    except (ValueError, KeyError, OSError, json.JSONDecodeError, wave.Error) as error:
        parser.exit(2, f"Automatic drafts failed: {error}\n")


if __name__ == "__main__":
    main()
