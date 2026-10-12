# Supplied-chart alignment on three paired ensemble excerpts

Completed 12 October 2026: twelve conditional NNLS alignment runs on the same
three publisher-paired JazzSAMBA first-60-second mixes used in the
[raw recognizer comparison](JAZZSAMBA_REFERENCE_CHECK.md). Giving the algorithm
the intended main-chord order does not yet produce dependable lesson timings.
The baseline retains substantially more usable labels than the existing guards,
while both configurations retain wrong cues on a deliberately incorrect chart.
[Exact input, protocol, prediction and result pins](JAZZSAMBA_ALIGNMENT_CHECK.json)
make the bounded experiment auditable. No arrangement was promoted.

| Supplied chart | Aligner | Main-chord agreement | Unknown audio | Retained incorrect cues | Unvisited positions |
|---|---|---:|---:|---:|---:|
| Source triad runs | Frozen NNLS | 61.9% | 34.3 s | 29.5 s | 0 |
| Source triad runs | Frozen balanced guards + NNLS | 33.7% | 99.2 s | 16.1 s | 26 |
| Every known root shifted +1 semitone | Frozen NNLS | 0.8% | 140.6 s | 27.9 s | 0 |
| Every known root shifted +1 semitone | Frozen balanced guards + NNLS | 0.0% | 168.5 s | 3.9 s | 108 |

Each row covers the same 180 seconds. Major/minor agreement has 167.397 seconds
of eligible written-reference harmony, or 93.0% coverage. Unknown source positions
and unannotated gaps are excluded from eligible agreement; guesses in those
regions are reported separately in the JSON. Unknown *predictions* receive no
agreement credit. Retained incorrect cue duration counts only emitted harmonic
labels that disagree with eligible reference harmony; it is not the duration of
all abstentions or missing cues.

The guards reduce emitted wrong labels on the corrupted chart from 27.9 to
3.9 seconds, but also lose 28.2 percentage points of agreement on the source-order
chart. They leave part of Blue Bossa and Amazing Grace unvisited. Their current
ensemble coverage is insufficient for a default play-along lesson pipeline.
These outcomes leave both candidate implementations and the acceptance policy
unchanged; further development needs a separate predeclared experiment.

## What was given to the aligner

The existing publisher-source major/minor triad projection supplies ordered
*runs*, including repeated song passages. Adjacent identical projected labels
are merged because these chroma templates cannot identify a rearticulation of
the same chord. Unsupported projected positions remain X, as do leading/trailing
unannotated gaps. Blue Bossa has 35 supplied positions including eight X
positions; Amazing Grace has 46 positions including one X; When the Saints Go
Marching In has 34 positions including one X.

This is the previously declared easier triad target, not an assertion that rich
jazz chords are ordinary playable beginner substitutions. Original rich symbols,
alterations, slash information and source fields stay in the hash-pinned local
references. The runner accepts only explicit `maj`/`min` projections plus N/X,
and refuses an unsupported rich label rather than guessing a conversion.

Every source timestamp, grid location, duration, tempo and key is absent from
the input consumed by the decoder. The source triad chart and the deterministic
wrong-root chart are written and hash-pinned before acoustic extraction or
alignment. Both use a finite supplied sequence, start at its first position and
request its last position as the endpoint. A guarded infeasible endpoint remains
a partial path with unvisited positions; it is not filled with invented cues.

NNLS-Chroma extraction receives only exact audio and recording ID. Both aligners
use the same cached native features, the existing 25 ms decoder step, 180 ms
analysis-window request, 150 ms minimum dwell, 0.12 transition penalty, 0.45
unknown threshold and 0.30 mismatch margin. The guarded configuration uses the
already frozen balanced policy with 0.08 quality margin, 0.12 added-tone ratio
and 0.50 support fraction. There is no source separation, key assistance,
tempo/grid snapping, offset fitting or endpoint scaling. Native chroma has about
743 ms acoustic support and a 93 ms hop at 22050 Hz; decoder interpolation does
not add acoustic resolution.

## Timing diagnostic and recognition context

There are 95 changes between different, contiguous supported projected
harmonies. N/X boundaries, gaps and repeated identical chords are excluded.
An emitted N/X edge cannot earn timing credit. Ordered one-to-one matching uses
a fixed 150 ms tolerance against the publisher's **written chart grid**:

| Correct supplied order | Matched grid changes | Emitted supported changes | Grid-change F1 |
|---|---:|---:|---:|
| Frozen NNLS | 26 / 95 | 53 | 35.1% |
| Frozen balanced guards + NNLS | 5 / 95 | 15 | 9.1% |

These are conditional chart-grid diagnostics. They do not measure physical chord
attacks, pianist voicings or every performed note. Source timestamps are aligned
to musician-authored bar grids, and ensemble performers can anticipate or delay
the written harmony. No prediction-derived temporal correction was applied.

For context, the unchanged audio-only recognizers score 28.9% baseline, 65.9%
BTC, 61.6% CREMA, 58.0% ChordMini and 55.5% Chordino on the same separately
declared triad target. Those models are given no chord order, so this comparison
does not establish equivalent task difficulty or a recognition improvement.
The supplied-order NNLS result gives no convincing advantage over the stronger
raw recognizer on these clips.

## Scope and reproduction

Protocol `9ee7df9d413bf45126c73901469d7f670d0279347484368f91aa692b6012754e`
was frozen before these twelve alignment outputs. This is a retrospective
extension on three clips already exposed to raw recognizer evaluation. The
inherited one-development/two-holdout labels are retained for reporting, but do
not make this a fresh evaluation or prove exclusion from pretrained training.
There was no tuning after observing these results.

Source: [publisher demo](https://github.com/pnlong/jazzsamba-demo), commit
`3715097238b33593d865d05b772e094642843612`, dataset
[10.5281/zenodo.22943963](https://doi.org/10.5281/zenodo.22943963). Exact MP3,
annotation and prepared-WAV identities are pinned in the JSON. These jazz web
exports are a bounded ensemble test, not evidence of general rock-song accuracy,
beginner followability or affordable correction effort. Dataset media licensing
remains unresolved; music and full annotations remain local and untracked.

Seven focused checks pass with pinned `mir_eval`: timestamp withholding,
unknown/gap preservation, unsupported-label rejection, the fixed wrong-root
control, exclusion of identical/unknown edges, refusal to credit abstention
edges, and separation of retained wrong labels from unknown reference regions.
All twelve inference/scoring runs succeed. Native feature extraction totals
0.76 seconds and alignment/output writing totals 1.74 seconds on this Mac;
those timings exclude acquisition, preparation, interpreter startup and review.

To create a new audit output without replacing the frozen packet, run from the
repository with the existing native NNLS runtime and paired reference cache:

```sh
.venv-pilot/bin/python experiments/analysis/jazzsamba_alignment_check.py prepare \
  --output experiments/generated/jazzsamba-alignment-new-audit
.venv-pilot/bin/python experiments/analysis/jazzsamba_alignment_check.py run \
  --output experiments/generated/jazzsamba-alignment-new-audit
```

The runner refuses existing inference outputs and verifies all frozen input,
chart, candidate, policy, scorer and native-runtime hashes before starting.
