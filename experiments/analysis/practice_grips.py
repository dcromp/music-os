"""Project-authored grip examples; symbolic checks are not recording verification."""
from __future__ import annotations

OPEN_MIDI = (40, 45, 50, 55, 59, 64)
ROOTS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
QUALITIES = {"": {0, 4, 7}, "m": {0, 3, 7}, "m7": {0, 3, 7, 10},
             "sus4": {0, 5, 7}, "7sus4": {0, 5, 7, 10}, "add9": {0, 2, 4, 7}}
GRIPS = {
    "A": (None, 0, 2, 2, 2, 0), "D": (None, None, 0, 2, 3, 2), "E": (0, 2, 2, 1, 0, 0),
    "G": (3, 2, 0, 0, 3, 3), "C": (None, 3, 2, 0, 1, 0), "Am": (None, 0, 2, 2, 1, 0),
    "Em": (0, 2, 2, 0, 0, 0), "B": (None, 2, 4, 4, 4, 2), "Cm": (None, 3, 5, 5, 4, 3),
    "F": (None, None, 3, 2, 1, 1), "Dm": (None, None, 0, 2, 3, 1), "Em7": (0, 2, 2, 0, 3, 3),
    "Dsus4": (None, None, 0, 2, 3, 3), "A7sus4": (None, 0, 2, 0, 3, 3), "Cadd9": (None, 3, 2, 0, 3, 3),
    "G/F#": (2, 2, 0, 0, 3, 3),
}


def note_pc(name):
    if not name or name[0] not in ROOTS or name[1:] not in ("", "#", "b"):
        raise ValueError("Expected a named note")
    return (ROOTS[name[0]] + (1 if name.endswith("#") else -1 if name.endswith("b") else 0)) % 12


def expected_pitches(label):
    import re
    match = re.fullmatch(r"([A-G][#b]?)(m7|m|7sus4|sus4|add9)?(?:/([A-G][#b]?))?", label)
    if not match:
        raise ValueError("Unsupported declared grip quality")
    root, quality, bass = match.groups()
    pc = note_pc(root)
    expected = {(pc + interval) % 12 for interval in QUALITIES[quality or ""]}
    bass_pc = note_pc(bass) if bass else pc
    if bass:
        expected.add(bass_pc)
    return expected, bass_pc


def verify_grip(label, frets):
    if len(frets) != 6 or any(value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 12) for value in frets):
        raise ValueError("Use six bounded frets or muted strings")
    pitches = [open_note + fret for open_note, fret in zip(OPEN_MIDI, frets) if fret is not None]
    expected, bass = expected_pitches(label)
    if not pitches or {pitch % 12 for pitch in pitches} != expected or min(pitches) % 12 != bass:
        raise ValueError("Grip notes or bass do not match the declared chord")
    return {"shape": label, "frets_low_to_high": list(frets), "played_pitch_classes": sorted(expected),
            "lowest_pitch_class": bass, "symbolic_notes_checked": True,
            "verification_scope": "Pitch-class and bass check in conventional standard tuning; playability and exact recorded voicing are not verified"}


def source_palette(context):
    shapes = context.get("entry_shapes")
    if shapes is None:
        return {"status": "riff-or-section-guide-required", "grips": [], "exact_audio_pitch_verified": False}
    if not isinstance(shapes, list) or not shapes or any(shape not in GRIPS for shape in shapes):
        raise ValueError("Source shape vocabulary needs an explicit project grip")
    setup = context["setup"]
    shift = 0 if setup["tuning"] == "EADGBE" else -2 if setup["tuning"] == "DGCFAD" else None
    capo = setup["capo"]
    if capo is not None and (isinstance(capo, bool) or not isinstance(capo, int) or not 0 <= capo <= 12):
        raise ValueError("Capo must be explicitly unknown or a fret from 0 to 12")
    result = []
    for shape in shapes:
        item = verify_grip(shape, GRIPS[shape])
        item["sounding_pitch_classes_if_setup_applies"] = (sorted({(pc + shift + capo) % 12 for pc in item["played_pitch_classes"]})
                                                          if shift is not None and isinstance(capo, int) and not isinstance(capo, bool) else None)
        result.append(item)
    return {"status": "source-guided-practice-proposal", "grips": result,
            "declared_uniform_tuning_shift_semitones": shift, "teacher_capo": capo,
            "exact_audio_pitch_verified": False,
            "semantics": "Project grip examples for the teacher-supported palette. X means a muted string; 0 is open. Frets are relative to a declared capo. Unconfirmed capo leaves sounding pitch unspecified."}
