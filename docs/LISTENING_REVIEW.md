# Automatic play-along and optional review

The default page now gives you a prepared song to play. It does not ask you to transcribe chord names or timings. Open [the player](http://127.0.0.1:8068/), choose a song and press play. Current and upcoming chords follow the audio clock automatically.

If a moment feels wrong, tap **Something feels wrong**. The page records the playback time and displayed chord and saves the issue in this browser. A reason or note is optional. This reaction timestamp is a problem location, not a verified chord-change boundary. There is no required session length or checklist.

## Current automatic pack

`experiments/generated/automatic-playalong/` contains full prepared recordings for Creep, Wonderwall and House of the Rising Sun. CREMA supplies the unchanged primary draft; Chordino supplies optional disagreements. Creep also has an advanced NNLS cyclic hypothesis. [Preparation and provenance](AUTOMATIC_DRAFTS.md) describe exact audio pairing and the experimental model choice.

Wonderwall defaults to **Capo 2 · played shapes**, using its teacher-guide capo suggestion. The practice display transposes detected roots and named bass notes while preserving quality; raw sounding-pitch charts stay unchanged. You can select **Sounding pitches** instead. Feedback preserves both labels and the selected capo/view. Creep and House use no capo suggestion beyond zero.

**Chord detail → Core chords** offers a simpler view: Em7 → Em, Cadd9 → C, A7sus4 → Asus4. Dsus4 stays Dsus4; replacing it with D would introduce a third. The current full shape appears underneath when it differs. Full chords is the default, and reload restores that default. The choice is retained per song within the current tab. This convention leaves out notes and may change the sound; actual fingering/transition difficulty is a separate question. [The retrospective screen](CORE_CHORD_SCREEN.md) measures extension differences ignored, not detector improvement.

Contiguous events showing the same core chord appear as one interval, so the next cue reflects the next different displayed harmony. Silence, uncertainty and missing intervals are preserved. Raw events still determine the detector label and timestamp recorded when you tap an issue.

Disagreement points are under optional details. They are places where algorithms differ, not a list of known mistakes. Many flags have a correct primary chord, and some shared errors produce no flag. [Automated warning evaluation](DRAFT_SCREEN.md) measures that limitation without founder annotations. These hints never block playback or rewrite the primary timeline.

## Start on the Mac

From `/Users/davidcrompton/Documents/music-os`:

```sh
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-playalong --port 8068
```

The existing synthetic bench remains on port 8067. Stop either command with Ctrl+C; restart after reboot. The automatic pack is already cached on the deployed Mac. For another build, use the instructions in [AUTOMATIC_DRAFTS.md](AUTOMATIC_DRAFTS.md) and choose a new output directory.

## Feedback storage

Issues, optional reasons and notes save to browser-local storage, keyed by pack, recording ID and exact audio hash. Reloading restores them. This storage stays in the browser profile/origin where you used the player; another browser or clearing storage does not retain it. If storage is unavailable, the page reports that limitation and keeps feedback in the tab with optional export.

**Download feedback** and **Copy feedback JSON** are backups, not required steps. Exports use a feedback schema separate from manual chord annotations. They record source coordinates, the raw sounding chord, displayed chord/shape, practice view, `quality_mode` and whether the user heard a problem. Earlier reports without `quality_mode` mean Full chords and still load. They are not reference truth or algorithm-accuracy labels.

## Optional research tools

Other charts, source details and manual annotations remain under **Advanced**. You can inspect or correct a troublesome moment if useful, but the founder does not need to label a song before playing. Manual annotation exports remain model-exposed drafts with `gold: false`; use sounding pitches for reference-style labels and verify them separately before scoring.

The earlier three 20-second packs remain cached in `experiments/generated/listening-review/` and `experiments/generated/listening-review-alignment/`. Their sample ranges, identities and anonymous alternatives remain auditable. The current interface automatically displays a draft even for these older packs; it no longer provides the former blind-annotation-first workflow. Its old blank-mark task is superseded by the automatic player.

Independent accuracy evaluation uses existing annotated datasets and separately verified references. Ordinary play-along reactions guide usefulness and investigations; they do not require detailed manual transcription or certify a chart as correct.

## Verification

Tests cover exact audio/chart matching, full-duration preparation, feedback capture from the playback clock, source offsets, persistence and case isolation, optional manual provenance, practice transposition, and private HTTP routes. Browser smoke checked immediate chords, seeking, issue capture, reload persistence and song switching. The deployed player additionally verified Creep's immediate G/B/C/Cm cues and Wonderwall switching between Em7/G practice shapes and F#m7/A sounding pitches. QA feedback stayed on a separate test origin; the deployed Creep page was left with no invented user issues.

The core-view continuation adds nine helper checks (29 total), including pitch-class subsets, suspensions, slash bass, display-only merging and backward compatible feedback. A temporary port-8069 QA browser verified Em / Full chord: Em7 at 16s with capo 2, F#m / Full chord: F#m7 in sounding view, automatic issue capture, note persistence across reload and replay. Test feedback remains isolated on that QA origin; the normal player receives no invented issue reports.

The installed port-8068 player then verified Wonderwall's Core chords selector and Em / Full chord: Em7 at the same 16s timestamp, with no added issue. Its HTML, JavaScript and CSS match the Mac checkout byte-for-byte. The temporary QA server and both test tabs were closed; the original user tab remains available. Reload it to load the updated selector.
