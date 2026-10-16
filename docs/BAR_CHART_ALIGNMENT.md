# Full written-bar chart alignment with audio-only origin search

Completed 12 October 2026 on three newly fixed publisher-paired JazzSAMBA
first-minute mixes. Full written musical coordinates give promising main-chord
coverage, but the current prototype does not meet the strict written-grid timing
check and cannot verify an arrangement. All eighteen planned runs succeed;
every output remains `accepted_for_playback=false`.
[Source, frozen-protocol and output hashes plus results](BAR_CHART_ALIGNMENT.json)
preserve the evidence without publishing complete charts, annotations or music.

| Candidate, correct full source chart | Main-chord agreement | Known reference coverage | Unknown prediction | Written-grid boundary F1 at 150 ms |
|---|---:|---:|---:|---:|
| Source-tempo grid; tempo and origin chosen from audio | 86.8% | 90.7% | 16.5 s / 180 s | 0.0% |
| Audio-derived pulse grid; metrical mapping chosen from audio | 86.0% | 90.7% | 17.4 s / 180 s | 32.1% |

Agreement is duration-weighted against 163.173 seconds of eligible publisher
major/minor triad targets. Source unknowns and unannotated gaps are excluded from
eligible agreement and reported separately; unknown predictions earn no credit.
These are conditional scores with known written chords, bar lengths and source
BPM/meter. They are not independent recognition accuracy or verification that
the richer recorded chords have playable beginner substitutions.

All three are asynchronous fixed-tempo mixes. Their publisher written-grid
targets are constructed from the **same supplied musical coordinates and declared
BPM**. A scoring-only provenance check finds at most 0.474 ms difference between
that nominal construction and exported source times, attributable to rounding.
Consequently an unsearched zero-origin metadata grid would reconstruct the
publisher's nominal timeline almost exactly. This dependence means the 86.8%
score cannot establish an acoustic timing improvement, independent tempo
recognition, or accuracy on variable-tempo live music. The zero-origin observation
is an annotation-construction audit, not an added scored candidate or a new
winner selected after these outcomes.

The source-tempo candidate selects exactly the declared tempo on every input,
but selects a half-quarter-note *early* origin from NNLS acoustic fit. That moves
written boundaries 158–188 ms early, just beyond the predeclared 150 ms window.
No source-time correction, gold offset fitting or widened tolerance was applied.
The zero timing score must be read alongside this consistent small displacement;
it is not evidence that every main-chord label is incorrect. Conversely, high
duration agreement does not establish reliable change cues. Physical harmonic
attacks and recorded anticipations were not separately annotated or scored.

## Fresh inputs and explicit musical units

| Input | Experiment role | Written meter | Declared quarter-note BPM | Source-tempo agreement | Pulse agreement / grid F1 |
|---|---|---|---:|---:|---:|
| All of Me | Development | 4/4 | 170 | 90.2% | 90.2% / 51.9% |
| Alice in Wonderland | Holdout | 3/4 | 160 | 81.7% | 84.7% / 40.4% |
| Autumn Leaves | Holdout | 4/4 | 190 | 88.9% | 82.8% / 0.0% |

The exact fixed IDs are publisher song IDs 3, 2 and 6, each preferred mixture,
first 60.000 seconds from zero. Selection and search settings were frozen before
acquisition/inference. The two holdouts have not been used to retune this
prototype. This experiment's fresh recordings do not prove exclusion from
pretrained model training or generalization to rock repertoire.

The whole publisher-expanded written chart is used: 182 interval positions for
All of Me, 477 for Alice and 204 for Autumn Leaves. Only 37, 59 and 44 positions,
respectively, intersect the selected source-tempo first-minute prefix. The model
does not receive a chart prefix selected using annotated source seconds and does
not compress the full arrangement into the minute. Unvisited positions beyond
the audio excerpt are expected, with counts and meaning retained in diagnostics.

Written coordinates are `(bar + fraction) × quarter notes per bar`. Bar zero is
retained. A 3/4 bar has three quarter notes; a 4/4 bar has four. This explicitly
tests the waltz convention that the older player pulse metadata did not support.
It introduces no player/UI change or automatic meter claim.

## Candidate contracts frozen before output

The model input whitelist contains the complete musical bar/fraction-derived
coordinates, projected labels, declared source BPM/meter and source identity.
It contains no `start_time`, `end_time`, annotated wallclock seconds, timed
reference, key, gold-selected excerpt endpoint or physical onset labels. A test
replaces source wallclock values with invalid objects and obtains exactly the
same complete musical model input. Publisher source fields and richer symbols
remain pinned in the local research packet.

The major/minor projection uses the publisher's explicit root and triad fields.
Unsupported triads and written gaps remain X. Rich extensions and slash voicings
are preserved as original symbols alongside the declared easier projection;
they are not silently promoted to equivalent playable arrangements.

Both candidates use exact-paired, unchanged native NNLS-Chroma evidence. Their
objective is mean assigned-template cosine over *all active* native frames.
Unknown/unwritten positions score zero, so a hypothesis cannot improve its fit
merely by excluding difficult frames. Silence is excluded from the fit. No
cosine value is called calibrated confidence or used to accept playback.

1. The source-tempo candidate tests factors 0.65–1.55 of declared BPM in 0.01
   increments. Musical origins span ±2 written bars in quarter-note steps of
   0.25. It chooses the best acoustic fit, then prefers factors nearest one and
   origins nearest zero on a tie. This is an explicitly named **audio-only chart
   origin and tempo search**, not an offset fitted against annotated times.
2. The pulse candidate uses unchanged librosa 0.9.2 onset/beat tracking,
   `tightness=100`, `trim=True`, with declared BPM as its initial tempo hint.
   It tests 0.5, 1 and 2 quarter notes per detected pulse and the same written
   origin range against NNLS fit. All three select one quarter note per pulse.
   It interpolates only between actual detected pulse timestamps, preserving
   uncovered leading/trailing intervals as X. It never extrapolates endpoint
   pulses, scales the recording length or consumes reference beats.

The current native features have about 743 ms support and a 93 ms hop at
22050 Hz. Musical interpolation does not create additional acoustic resolution.
The two candidates are separate declared hypotheses; neither is selected after
looking at gold scores to manufacture a combined winner.

## Negative controls expose the acceptance problem

| Corrupted full chart | Candidate | Main-chord agreement | Retained incorrect cues | Grid-boundary F1 at 150 ms |
|---|---|---:|---:|---:|
| Every known root shifted +1 semitone | Source-tempo grid | 1.4% | 148.9 s | 23.8% |
| Every known root shifted +1 semitone | Pulse grid | 0.9% | 146.7 s | 16.3% |
| Written bar eight deleted; subsequent coordinates shifted one bar | Source-tempo grid | 77.5% | 28.3 s | 68.5% |
| Written bar eight deleted; subsequent coordinates shifted one bar | Pulse grid | 74.7% | 32.0 s | 31.0% |

The wrong-root control retains source unknowns and musical lengths; it changes
only each known root by a deterministic semitone. The missing-bar control deletes
the fixed musical interval for written bar eight and closes that interval in
the chart. It is not chosen using source seconds or observed problem passages.

The deleted-bar source-grid control receives a better *unlabelled timing* score
than the correct full chart. Its audio-only origin search partly compensates for
the missing bar, while early labels/order remain wrong. This demonstrates why
boundary proximity alone cannot verify a recording-specific arrangement.
Correct charts have higher acoustic objectives than these controls on each input,
but the small missing-bar differences are not an acceptance calibration.

The prototype deliberately emits the supplied labels rather than weakening the
old guards or pretending a new acceptance threshold is justified. Its controls
therefore retain many wrong cues. Reviewed arrangements and a separate,
independently evaluated acceptance path remain necessary. No old aligner,
policy, detector settings or existing ten-song player artifact changed.

## Preparation failures, provenance and checks

Two preparation attempts stopped before any NNLS, pulse or alignment inference.
The All of Me source ends with a symbol whose musical start and end coordinates
are identical. The strict interval parser initially rejected it. It now preserves
that item as an unresolved zero-extent written point without guessing a hold;
regions beyond the last defined interval remain unknown. The separate scoring
producer also initially rejected the corresponding terminal wallclock point
beyond the first-minute excerpt. It now excludes out-of-excerpt scoring rows
before requiring positive interval duration. The musical chart still uses every
written source row, including the unresolved point. Both failed selections and
failure records remain saved; search settings were unchanged and freshly frozen
before the successful packet's acquisition/inference.

Source: [publisher demo](https://github.com/pnlong/jazzsamba-demo), exact commit
`3715097238b33593d865d05b772e094642843612`, dataset
[10.5281/zenodo.22943963](https://doi.org/10.5281/zenodo.22943963). Git-tree blob
identities, byte lengths and SHA-256 checks prove the three exact preferred MP3
and annotation pairings. Total downloaded full MP3 bytes are 22,763,175; no large
dataset archive was used. FFmpeg honors codec delay/padding and creates exactly
1,323,000 mono PCM16 frames at 22050 Hz per case without arbitrary trimming,
gain, temporal shifts or endpoint scaling.

Successful selection hash:
`41890aa30994ca097f59ee2ecb7c3e3fa464a61815d3e4aa608bb2e0e194f4db`.
Protocol hash:
`8d00ca5472465289cdad10ff770e56807346ab17d21653cbdd72a49ee014025a`.
Implementation hash:
`db437945628d3b7946b52c051a672b883615380e9efe5f64f9177fb4b68dca86`.
Full local report hash:
`5ae43eb74cc278e3cbc1154c3f0bf7ef5f1745c5ee86ab3e4b7159fcba6af7c1`.

Eleven focused checks pass: full-chart independence from poisoned wallclock
fields, explicit 3/4 units, schema rejection of gold fields, unsupported-symbol
handling, both corruptions, unresolved terminal positions, scoring-only excerpt
validation, partial full-chart prefixes, exact identity checks, no unknown-frame
fit credit and refusal to extrapolate pulse endpoints. All eighteen runs succeed.
There was no retuning after output. These are publisher written-grid targets,
not individually marked physical attacks, beginner usefulness or review-cost
measurements. Dataset media licensing remains unresolved; complete source charts,
annotations, MP3s and WAVs stay local and untracked.

The full cached packet lives in `experiments/generated/bar-chart-alignment-v1`.
To reproduce in a fresh directory with the existing native and pulse runtimes:

```sh
.venv-analysis/bin/python experiments/analysis/bar_chart_alignment.py prepare \
  --output experiments/generated/bar-chart-alignment-new-audit
.venv-pilot/bin/python experiments/analysis/bar_chart_alignment.py run \
  --output experiments/generated/bar-chart-alignment-new-audit
```

Preparation uses bounded official-source acquisition; inference verifies the
frozen charts, audio, references, selection, settings and implementation/runtime
pins. Existing inference artifacts and reports are refused rather than replaced.
