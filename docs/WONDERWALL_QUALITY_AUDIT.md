# Wonderwall: first feedback and chord-quality limitation

## Feedback received

On 10 October 2026 the founder described the automatic player as **mostly
correct**, with Wonderwall potentially the trickiest song because of its Em7,
Dsus4, A7sus4 and Cadd9 shapes. This is qualitative feedback. No issue timestamps,
completed guitar-session protocol or accuracy labels were supplied; do not infer
which recordings or passages were checked or assign a percentage.

## What the current model can express

The capo-2 view changes roots, preserving chord quality. A teacher's
[Wonderwall chart](https://www.gregshuteguitar.co.uk/_files/ugd/4079b4_0a1b39a89c1a4776a5c8f553f259cb08.pdf)
uses those shapes and G, and [Carl Brown's lesson](https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/)
confirms capo 2 and sounding F# minor. These are arrangement inputs, not timing
truth for the imported video.

| Played shape, capo 2 | Sounding label | Installed CREMA vocabulary | Default Chordino dictionary | Saved CREMA segments |
| --- | --- | --- | --- | ---: |
| Em7 | F#m7 | Supported | Supported | 40 |
| G | A | Supported | Supported | 37 |
| Dsus4 | Esus4 | Supported | Absent | 0 |
| A7sus4 | B7sus4 | Absent | Absent | 0 |
| Cadd9 | Dadd9 | Absent | Absent | 0 |

The saved CREMA draft also contains 27 D-major segments, one Bsus4 segment and
six B-major segments. In the capo view these display as C, Asus4 and A. Counts
describe output, not measured errors or expected event counts. Neither model's
current vocabulary can emit the full A7sus4/Cadd9 shapes. CREMA can represent
Dsus4 but did not emit its sounding equivalent in this recording. These are
different limitations: missing vocabulary versus failed recognition.

Read-only inspection with `pickletools` of the installed CREMA 0.2.0 model's
`pump.pkl` found a `3567s` vocabulary: N/X plus twelve roots times fourteen
qualities (major, minor, diminished, augmented, major/minor sixths,
minor/major/dominant/diminished/half-diminished/minor-major sevenths, sus2 and
sus4). It has no add9 or 7sus4. The adapter's display suffix table is broader
than the trained vocabulary; label conversion cannot add model classes.

Chordino's built-in names are defined in
`experiments/candidate-assets/nnls-chroma/chromamethods.cpp:272`. The current
adapter requires that dictionary and rejects external `chord.dict`. It has
minor sevenths but neither suspensions nor add9.

Saved input identity: `oasis-wonderwall-youtube-20261010`, audio SHA-256
`88e1649a3efa33647b8a07a7fc5feab2540c588ce35e2f27a3a682f2c4553462`.
Audited `primary.json` SHA-256:
`1d696977fe56f91126f3e838903939a6670a335d7079fc297b45e6573a3c3e83`.
The saved primary remains unchanged.

## Next bounded experiment

Root or collapsed major/minor scores cannot establish preservation of these
extensions. Prioritise the following before broader model search or iOS work:

1. Generate guitar-like voiced m7, sus4, 7sus4 and add9 progressions with shared
   upper notes, staggered strums, bass changes and capo transposition. Include
   plain triad controls to catch indiscriminate addition of extensions.
2. Report exact quality and unsupported-vocabulary coverage beside root,
   major/minor and boundary scores. Keep raw audio-only models as controls.
3. Compare a separately labelled chart-assisted draft with the richer expected
   vocabulary and reviewed section order. The existing aligner supports 7sus4
   and add9. Test wrong-quality/wrong-section inputs and permit unknown spans.

The audit, controls and bounded guided comparison are complete as of
11 October 2026. [The richer screen](RICH_QUALITY_SCREEN.md) has 24 cases and
224 successful comparisons. Correct-chart timing is promising on procedural
audio, but added extensions survive rejection in all eight plain controls.
[The full-song hypothesis](WONDERWALL_GUIDED_DRAFT.md) also completes wrong
section order with substantial compression. It remains unaccepted. The original
0.5–1 focused-day estimate described this first pass; quality/section acceptance
and broader real-reference validation remain further work. Founder
transcription is not required.

Do not replace every D with Dadd9 or B with B7sus4. Preserve raw predictions,
then cache any accepted teaching arrangement separately. Simplification should
be an explicit practice option, not an unmarked substitute for original shapes.
