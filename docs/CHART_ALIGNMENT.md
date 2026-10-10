# Curated catalogue: chart-assisted alignment

## Product direction

For a curated few hundred rock/pop songs, obtain and review the likely harmony once, align it to a specific recording, and reuse the approved arrangement for every practice session. The next experiment prioritises this route. Existing chord detectors become evidence for chart verification, alignment and disagreement review; their raw recognition results remain useful controls.

Start with ten permitted excerpts for the technical comparison, then the existing 30–50-arrangement learning-path pilot. Expand toward a few hundred titles when measured preparation/review effort and demand justify it. Popularity guides repertoire; arrangement difficulty and the learner's next skill determine progression.

## Inputs and consensus

| Input | What it contributes | What it does not establish |
|---|---|---|
| Key | A likely tonal centre and transposition check | Chord order, borrowed chords or precise changes |
| Chords used in a song | A candidate vocabulary | Sequence, repetitions or durations |
| Ordered verse/chorus charts | A much stronger alignment reference | Whether every source matches this recording |
| Reviewed sequence and section order | Expected harmony through the performance | Accurate boundaries, rearticulation or rhythm |

Collect candidate references with URL/author, retrieval date, version, capo/tuning, simplification notes, section order and source-use status. Normalise enharmonic names and convert played shapes to **sounding pitches** before comparison; preserve playable shapes separately. For example, capo 2 with G–Em–C–D shapes sounds A–F#m–D–E. A raw vote between those two charts would create a false disagreement.

Group sources by recording/arrangement and likely shared origin. Several copies of the same chart are correlated evidence, not several independent votes. Compare ordered sections and retain disagreements rather than collapsing every source into one global chord list. Check the proposed consensus against audio; key is supporting evidence, not a rule that removes out-of-key chords. Preserve both the recorded harmony and any intentionally simpler teaching arrangement.

Reference discovery and permission to reuse or publish source material remain distinct fields in the existing content workstream. This experiment does not assume bulk scraping or redistribution is available from a public chart page. Authored, authorised or appropriately licensed material can supply the initial pipeline inputs.

## Technical pipeline

1. Identify the exact recording: album/radio/live/acoustic version, duration and source identity. Preserve its audio time origin.
2. Create a reviewed candidate chord sequence with sections/repeats, sounding key and separate capo/shape information. Do not provide alignment test timestamps.
3. Extract acoustic evidence from the original mix: chroma or candidate chord scores, harmonic changes and beats/onsets. Add separation only if a controlled comparison improves the alignment.
4. Align the expected sequence to the evidence. Begin with a small constrained dynamic-programming decoder allowing variable chord durations; add explicit section/repeat transitions when the simple expanded sequence is insufficient. Use rhythm as a timing hint, while preserving offbeat and fast changes.
5. Flag disagreement and drift for review. An incorrect reference must not receive a confident-looking forced path merely because an aligner can return one. Keep unknown/unmatched spans, alternative labels and a free-recognition fallback.
6. Review and cache the timed harmony, section markers and teaching arrangement. Version manual corrections separately from raw model output.

Repeated identical chords do not necessarily create a harmonic boundary in the audio. Bar boundaries and rearticulation need rhythm evidence or a reviewed beat grid. Repeated progressions can also match several verses; section order and optional manually supplied anchors help distinguish them. Edited recordings and covers need their own validated alignment.

## Research leads

[DECIBEL](https://arxiv.org/abs/2002.09748) combines audio estimates with aligned symbolic representations. Its [Jump Alignment documentation](https://daphneo.github.io/DECIBEL/html/codedescription/audiotabaligner.html) describes an HMM for untimed chart sequences, with jumps between chart lines and transposition selection. Inspect its features/decoder as a practical implementation reference; its trained parameters, old dependencies and source terms still need review before adoption. We need not inherit its assumption that every useful event sits on a beat.

[ChordSync](https://arxiv.org/abs/2408.00674) directly studies aligning ordered chord annotations to audio using acoustic probabilities and forced alignment. It is a research lead, not a verified ready-to-run candidate here: the current official [prediction source](https://raw.githubusercontent.com/andreamust/ChordSync/main/ChordSync/prediction.py) has placeholder label preprocessing, and [issue 1](https://github.com/andreamust/ChordSync/issues/1) reports missing execution/checkpoint assets. Resolve those before allocating integration work or assigning a score.

## Next bounded experiment

An [initial NumPy alignment baseline](CHART_ALIGNER_SETUP.md) is implemented. Its [64-case conditional synthetic screen](ALIGNMENT_SCREEN.md) completed with mean boundary F1 90.4% within 150 ms, 59 extra and one missed boundary. Correct labels/order/count were inputs; all timestamps and reference silence events were withheld. This is a timing diagnostic, not recognition or real-song accuracy.

The Python [YouTube importer](YOUTUBE_IMPORT.md) acquired three recordings from the existing song list. Nine detector runs succeeded. A simplified Creep cyclic draft over-repeats the four-chord loop and is unaccepted; exact sections/repeat counts and independently checked timing gold remain outstanding. Wonderwall and House have source-informed intro candidates only, pending exact excerpt selection. See [the smoke evidence](YOUTUBE_IMPORT_SMOKE.md).

Version 0.2 now accepts finite section order/repeats and optional native NNLS evidence. A [64-case paired comparison](ACOUSTIC_ALIGNMENT_COMPARISON.md) scores NNLS at 98.4% conditional boundary F1, versus 90.4% spectral, with larger matched timing error. [Ten real drafts](REAL_ALIGNMENT_DIAGNOSTICS.md) remain unaccepted: richer features reduce Creep cycling but do not establish correct repeat counts. Three exact first-20-second development windows and five anonymous drafts each are ready in [the listening review](LISTENING_REVIEW.md). Their bounds are arbitrary windows, not verified sections.

[Independent-source research](REAL_REFERENCE_SOURCES.md) found human Animals annotations, but their CD recording is about 14.4 seconds longer than our import. No timing gold has been transferred or scored. First save blind human marks, then repeat/refine them and verify recording identity before evaluation.

**Remaining estimate: 1.5–2.5 focused days** for reference preparation and the broader comparison, excluding external content-access lead time. This is a planning estimate, not a delivery commitment. The full ten-excerpt experiment remains incomplete.

| Part | Status / deliverable | Remaining effort |
|---|---|---|
| Audio acquisition and smoke inference | Complete for three existing catalogue entries; source/hash evidence and nine detector outputs | Complete |
| Small alignment baseline | Implemented; finite section/repeat schema, optional NNLS, mismatch/X evidence | Complete experimental baseline |
| Conditional synthetic timing screen | Complete original 64 cases plus 64 paired spectral/NNLS cases; timing gold withheld | Complete |
| First three listening windows | Ready: exact 20-second clips, anonymous drafts and blank human annotations | First familiarisation 5–10 min; checked references across three may take 20–40 min or longer |
| Freeze ten representative excerpts and references | Pending: verified versions, sections/repeats, timing gold and fresh real holdout material | 0.5–1 day |
| Compare and inspect failures | Pending: audio-only/vocabulary/sequence comparison, corrupted-chart controls, drift and review-cost measurements | 1–1.5 days |

Compare **audio-only recognition**, **key/chord-vocabulary guidance**, and **known-sequence alignment** on the same recordings. Freeze a development/holdout split before tuning. Use permitted rock/pop or suitable original recordings, including repeats, sparse/dense arrangements, intros and quick/offbeat changes. Add corrupted chart inputs: wrong key/capo, wrong chord, missing repeat/section and a different edit. Generated cases with known boundaries can diagnose these failures before manual guitar sessions.

Measure harmony agreement, median and 90th-percentile change-time error, boundary precision/recall, missed changes, section drift, catastrophic wrong alignment, review/correction minutes per recording, and end-to-end runtime. Report development and holdout results separately. A few small errors and one whole-verse drift are different product failures.

Giving a model the expected chord sequence defines an **alignment** task. Report it separately from audio-only chord recognition. Keep evaluation timestamps hidden from the aligner; do not use GuitarSet's lead-sheet boundaries as physical played-onset gold without independent verification. Measure results against the actual recording, rather than treating online consensus as ground truth.

The catalogue decision should depend on useful timings and affordable one-time curation per recording/arrangement. No new per-song cost or accuracy figure is assumed. Reuse can keep inference out of ordinary playback, while chart preparation, rights, hosting and customer support remain distinct costs in the existing plan.
