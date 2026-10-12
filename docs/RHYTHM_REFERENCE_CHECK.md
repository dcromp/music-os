# Paired pulse and chord-length diagnostic

Completed 12 October 2026 on the six cached GuitarSet performances. This checks
the duration-count method used by the Mac player against exact paired source
annotations. It does not verify the ten-song catalogue's chords or arrangements.
The [compact results](RHYTHM_REFERENCE_RESULTS.json) preserve every audio/source
identity, configuration and report hash, per-recording metrics and missing
coverage. Full predictions and per-window reports remain in the ignored local
`experiments/generated/guitarset-rhythm-cached-v1/` packet.

Subsequent work resolved the acquisition dependency through a verified public
archive mirror. The [fresh ten-input check](FRESH_GUITARSET_RHYTHM_CHECK.md) is
complete. The blocked-attempt notes below describe the earlier checkpoint.

## Method and scope

The same six performances used by the chord pilot total 182.362 seconds. All are
retrospective development material. GuitarSet's `beat_position` annotations are
nominal metronome/lead-sheet positions, not manually marked physical guitar
attacks; a performer can anticipate, lag or swing around this grid. Prepared WAV
and original JAMS hashes are verified. No recording offset is fitted, and no
reference timestamp is used to move or snap predictions.

The frozen librosa tracker runs twice on each exact recording. **Default 120**
uses the native starting prior without a tempo range. **Nominal-tempo guided**
receives only the filename's nominal tempo and a declared ±15% range, with beat
times and positions withheld. This guided condition tests the value of selecting
the musical pulse level; it is not uninformed recognition. Source separation,
chord recognition and acceptance policies are unchanged.

The scorer uses chronological maximum-cardinality one-to-one pulse matching at
70ms and 150ms. Whole-recording metrics retain leading/trailing misses. Pinned
`mir_eval` 0.8.2 metrics separately disclose their standard first-five-seconds
trim. Reference-defined half-, one- and two-bar windows test duration counts by
interpolating detected pulse ordinals without extrapolating past observed
coverage. The 312 overlapping windows are not 312 independent recordings.

## Results

| Measure | Default 120 | Nominal-tempo guided |
|---|---:|---:|
| Whole-recording micro F1, 70ms | 45.6% | 57.7% |
| Whole-recording micro F1, 150ms | 63.5% | 73.4% |
| Matched / missed / extra pulses, 150ms | 202 / 134 / 98 | 242 / 94 / 81 |
| Supported count windows | 290 / 312 | 291 / 312 |
| Mean absolute count error, supported windows | 0.309 beats | 0.048 beats |
| 90th percentile absolute count error | 0.828 beats | 0.085 beats |
| Mean equivalent bar-length error, 4/4 convention | 0.077 bars | 0.012 bars |
| Extraction runtime, six recordings | 3.59 seconds | 1.91 seconds |

The runtime comparison is a single sequential run with different warm-up/cache
conditions, not a speed benchmark. All five other beat outputs are unchanged:
the aggregate improvement comes from the 142-BPM Rock2 case avoiding the wrong
pulse level. Its 70ms F1 rises from 34.6% to 99.2%, and count error falls from
1.380 to 0.031 beats. This supports using a checked tempo-level prior for curated
recordings, but does not establish reliability across songs.

Duration counts and pulse phase measure different properties. The BN1 recording
still has 0% F1 at 70ms and 6.5% at 150ms, although its count error is 0.048 beats.
A regular grid can have nearly correct interval lengths while falling between
the nominal beats. Its high any-metrical-level score must not be mistaken for
correct quarter-note phase. Downbeats and bar starts are explicitly unmeasured.
The player continues to label counts approximate and use seconds outside
coverage; these results do not authorize snapping chord boundaries to beats.

## Fresh selection and repertoire references

[Ten new performances](../experiments/fixtures/rhythm-reference-selection.json)
were selected before new audio acquisition or inference, with four development
and six holdout cases. Distinct progression/tempo/key groups exclude those used
by the prior pilot. The initial official Zenodo range request returned HTTP 504;
a bounded check of its ordinary archive link timed out. No fresh audio or
predictions were acquired, and no holdout score is available. This is an external
source-availability dependency; no founder recording or transcription is needed.
Preserve the selection and run the two declared conditions when acquisition is
available, without retuning on the exposed cached scores.

Independent annotation candidates exist for five of the first ten songs:
Love Me Do, Twist And Shout, Brown Eyed Girl, Come As You Are and House Of The
Rising Sun. [Source metadata](FIRST_TEN_REFERENCE_CANDIDATES.json) records the
canonical albums, annotation hashes and quality/training caveats. Matching title
or duration does not verify a master or time origin. The selected remasters and
uploads remain unmatched, so no corpus timestamp is copied into the player and
no full-mix accuracy is claimed. Isophonics annotation-use terms need clarification
before product reuse; possible CREMA training overlap also limits generalisation
claims. These are reference-discovery findings, not accepted arrangements.

## Reproduce and next steps

The deployed Mac checkout includes the cached packet and its six exact audio
pairs. Rescoring needs the existing pinned evaluation environment, not model
inference. Choose a fresh output file; the scorer refuses to replace inputs or
an existing report:

```sh
.venv-pilot/bin/python experiments/analysis/rhythm_reference_eval.py \
  --references experiments/generated/guitarset-rhythm-cached-v1/references.json \
  --predictions experiments/generated/guitarset-rhythm-cached-v1/nominal-tempo-guided-predictions.json \
  --output experiments/generated/guitarset-rhythm-cached-v1/guided-rescore.json \
  --condition nominal-tempo-guided
```

The new evaluator adds 20 focused checks for exact pairing, input validation,
one-to-one matching, coverage, count windows, explicit standard-metric semantics
and safe output paths. The full standard run passes 243 checks with 16 expected
`mir_eval` skips; those 16 pass in the pinned environment: 259 distinct checks.
No player code or metadata changed in this diagnostic; the previous 47 browser
helper checks and deployment evidence remain applicable.

Next acquire the frozen new sample, finish canonical-recording matching or use
another exactly paired mixed-audio benchmark, then check section-specific
arrangements and strumming. Broader reference work remains an estimated 1.5–2.5
focused days, excluding unavailable-host waiting. Normal guitar feedback later
answers whether this feels useful and enjoyable; it is separate from accuracy
scoring and does not block this technical work.
