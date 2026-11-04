"""Shared helpers for the Strum Along instrument stage (standard library only, so every venv can import it).

- recording discovery from strumalong/data/catalogue.json (the same packs catalogue_checks.js reads);
- chord label parsing that mirrors catalogue_checks.js (`parseChord` / `familyKey`) plus the pitch-class sets of the chord
  qualities the CREMA charts use (maj, min, 7, m7, maj7, sus, add9, 6, dim, aug, 5, 9 ...);
- small file helpers.

Nothing here reads audio, downloads anything or writes outside paths the caller names.
"""
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CATALOGUE = REPO / "strumalong" / "data" / "catalogue.json"
SONGS_DIR = REPO / "strumalong" / "songs"
STEMS_DIR = REPO / "experiments" / "generated" / "strumalong-stems"
TAGS_PATH = REPO / "experiments" / "generated" / "strumalong-instrument-tags.json"
HOLDS_PATH = REPO / "experiments" / "generated" / "strumalong-hold-checks.json"

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
      "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}


def file_sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(block)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json_atomic(path, data):
    """Write sorted-key JSON through a temp file so a killed batch never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def load_recordings(repo=REPO, only=None):
    """Every recording in every available pack of strumalong/data/catalogue.json, in catalogue order.

    Each item: id, pack, title, duration, audio_path (the pack's prepared mono 22.05 kHz WAV), audio_exists,
    pack_audio_sha256, primary_path, rhythm (the pack's rhythm case or None), excluded, excluded_reason.
    Excluded recordings are included on purpose: they are the labelled negatives.
    `only`: optional iterable of recording ids; unknown ids raise KeyError so a typo is not silently a no-op.
    """
    repo = Path(repo)
    cat = read_json(repo / "strumalong" / "data" / "catalogue.json")
    if not cat:
        raise FileNotFoundError("strumalong/data/catalogue.json not found")
    excluded = {x["recording_id"]: x.get("reason", "") for x in cat.get("exclude", []) if x.get("recording_id")}
    out = []
    for pack in cat.get("packs", []):
        pdir = repo / pack["dir"]
        manifest = read_json(pdir / "manifest.json")
        if not manifest:
            continue
        rhythm = read_json(repo / pack["rhythm"]) if pack.get("rhythm") else None
        rhythm_by_id = {(c.get("recording") or {}).get("id"): c for c in (rhythm or {}).get("cases", [])}
        for c in manifest.get("cases", []):
            rid = c["id"]
            audio = pdir / "cases" / rid / "audio.wav"
            out.append({
                "id": rid, "pack": pack["id"], "title": c.get("name") or rid,
                "duration": (c.get("recording") or {}).get("duration_seconds"),
                "audio_path": audio, "audio_exists": audio.is_file(),
                "pack_audio_sha256": (c.get("recording") or {}).get("audio_sha256"),
                "primary_path": pdir / "cases" / rid / "primary.json",
                "rhythm": rhythm_by_id.get(rid),
                "excluded": rid in excluded, "excluded_reason": excluded.get(rid),
            })
    if only:
        wanted = list(dict.fromkeys(only))
        known = {r["id"] for r in out}
        missing = [w for w in wanted if w not in known]
        if missing:
            raise KeyError("unknown recording id(s): " + ", ".join(missing))
        out = [r for r in out if r["id"] in set(wanted)]
    return out


def parse_only(values):
    """--only accepts repeated flags and comma-separated lists."""
    ids = []
    for v in values or []:
        ids.extend(x.strip() for x in v.split(",") if x.strip())
    return ids


# ------------------------------------------------------------------------------------------------ chord labels
_LABEL = re.compile(r"^([A-G](?:#|b)?)([^/]*)(?:/([A-G](?:#|b)?))?$")

# Interval sets (semitones above the root). Anything not listed falls back to the family triad.
QUALITY_INTERVALS = {
    "": (0, 4, 7), "maj": (0, 4, 7), "M": (0, 4, 7),
    "m": (0, 3, 7), "min": (0, 3, 7),
    "7": (0, 4, 7, 10), "dom7": (0, 4, 7, 10),
    "m7": (0, 3, 7, 10), "min7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11), "M7": (0, 4, 7, 11),
    "mmaj7": (0, 3, 7, 11),
    "sus": (0, 5, 7), "sus4": (0, 5, 7), "sus2": (0, 2, 7), "7sus4": (0, 5, 7, 10),
    "add9": (0, 2, 4, 7), "madd9": (0, 2, 3, 7),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "6add9": (0, 2, 4, 7, 9), "69": (0, 2, 4, 7, 9), "6/9": (0, 2, 4, 7, 9),
    "9": (0, 2, 4, 7, 10), "m9": (0, 2, 3, 7, 10), "maj9": (0, 2, 4, 7, 11),
    "5": (0, 7),
    "dim": (0, 3, 6), "dim7": (0, 3, 6, 9), "m7b5": (0, 3, 6, 10), "hdim7": (0, 3, 6, 10),
    "aug": (0, 4, 8), "+": (0, 4, 8),
}


def parse_chord(label):
    """-> {root, kind, quality, bass} or None for N, X and junk. kind is the triad family: "" (major-ish), "m", "sus", "5",
    "dim", "aug", mirroring catalogue_checks.js parseChord. quality is the label's own quality string."""
    if not isinstance(label, str) or label in ("N", "X"):
        return None
    m = _LABEL.match(label.strip())
    if not m or m.group(1) not in PC:
        return None
    q = m.group(2).lstrip(":")
    if q == "":
        kind = ""
    elif "sus" in q:
        kind = "sus"
    elif re.match(r"^(dim|o|°|m7b5|hdim)", q):
        kind = "dim"
    elif re.match(r"^(aug|\+)", q):
        kind = "aug"
    elif q == "5":
        kind = "5"
    elif re.match(r"^(maj|M)", q):
        kind = ""
    elif re.match(r"^(m|min|minor)", q):
        kind = "m"
    else:
        kind = ""
    bass = PC.get(m.group(3)) if m.group(3) else None
    return {"root": PC[m.group(1)], "kind": kind, "quality": q, "bass": bass}


def family_key(label):
    """"Em", "G", "Asus", "D5": root + triad kind, or None for N, X and junk (same as catalogue_checks.js familyKey)."""
    p = parse_chord(label)
    return None if p is None else NAMES[p["root"]] + p["kind"]


_KIND_TRIAD = {"": (0, 4, 7), "m": (0, 3, 7), "sus": (0, 5, 7), "5": (0, 7), "dim": (0, 3, 6), "aug": (0, 4, 8)}


def chord_pitch_classes(label):
    """Sorted pitch classes of a chord label (root + quality tones, plus a slash bass), or None for N, X and junk.
    Qualities not in QUALITY_INTERVALS fall back to the family triad."""
    p = parse_chord(label)
    if p is None:
        return None
    iv = QUALITY_INTERVALS.get(p["quality"]) or _KIND_TRIAD[p["kind"]]
    pcs = {(p["root"] + i) % 12 for i in iv}
    if p["bass"] is not None:
        pcs.add(p["bass"])
    return sorted(pcs)
