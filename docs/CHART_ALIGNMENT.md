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

Estimated effort: **2–3 focused days once suitable inputs/references are available**; this is a planning estimate, excluding external content-access lead time. No alignment implementation or benchmark result is claimed yet.

| Part | Deliverable | Estimated effort |
|---|---|---|
| Freeze ten representative excerpts and references | Exact versions, source records, untimed candidate sequences and independently checked timing gold | 0.5–1 day |
| Implement a small alignment baseline | Shared-format output; variable durations; mismatch/fallback evidence | 1 day |
| Compare and inspect failures | Held-out results, timing plots and review-cost measurements | 0.5–1 day |

Compare **audio-only recognition**, **key/chord-vocabulary guidance**, and **known-sequence alignment** on the same recordings. Freeze a development/holdout split before tuning. Use permitted rock/pop or suitable original recordings, including repeats, sparse/dense arrangements, intros and quick/offbeat changes. Add corrupted chart inputs: wrong key/capo, wrong chord, missing repeat/section and a different edit. Generated cases with known boundaries can diagnose these failures before manual guitar sessions.

Measure harmony agreement, median and 90th-percentile change-time error, boundary precision/recall, missed changes, section drift, catastrophic wrong alignment, review/correction minutes per recording, and end-to-end runtime. Report development and holdout results separately. A few small errors and one whole-verse drift are different product failures.

Giving a model the expected chord sequence defines an **alignment** task. Report it separately from audio-only chord recognition. Keep evaluation timestamps hidden from the aligner; do not use GuitarSet's lead-sheet boundaries as physical played-onset gold without independent verification. Measure results against the actual recording, rather than treating online consensus as ground truth.

The catalogue decision should depend on useful timings and affordable one-time curation per recording/arrangement. No new per-song cost or accuracy figure is assumed. Reuse can keep inference out of ordinary playback, while chart preparation, rights, hosting and customer support remain distinct costs in the existing plan.
