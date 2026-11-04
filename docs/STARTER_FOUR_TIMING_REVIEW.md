# Starter-four native timing and contrast review

Updated 16 October 2026. **Stage 2 now has a bounded operator-review queue and harmonic contrast candidates for the four starter recordings. No physical timing, complete section map or arrangement is accepted.** The pass reuses exact cached BTC/CREMA charts and NNLS evidence. It performs no extraction, neural inference, timestamp refinement or automatic correction. Original audio remains the default; the 39 Stage 1 frozen pins remain unchanged.

**Ticket 3 follow-up:** the [bounded recording assessment](STARTER_FOUR_RECORDING_ASSESSMENT.md) now accounts for every selected/fixed sample and names the unresolved per-song claims. It verifies input/replay integrity but performs no audition; ticket 3 remains open and the reviewed-pack gate remains blocked pending a capable review or matched reference.

## What the queue measures

Contiguous equivalent core labels are merged; silence, unknowns, unsupported labels and gaps remain distinct. Ordered one-to-one matching pairs the same directed core transition within 0.5 seconds, maximizing pair count before minimizing total time difference. Unpaired transitions and paired differences above 0.15 seconds create replay windows with 1.5-second padding. The unchanged priority order selects at most 12 windows per recording; BTC boundaries near its 10-second chunk seams are annotated for inspection.

| Recording | BTC / CREMA core boundaries | Compatible pairs | Median / maximum paired difference | All / selected replay windows |
|---|---:|---:|---:|---:|
| Wild Thing | 103 / 79 | 71 | 61.7 / 279.5 ms | 57 / 12 |
| Love Me Do | 73 / 55 | 51 | 61.3 / 434.1 ms | 39 / 12 |
| Knockin' on Heaven's Door — Dylan | 73 / 64 | 59 | 61.3 / 248.0 ms | 21 / 12 |
| Twist and Shout — Beatles | 112 / 101 | 93 | 31.4 / 465.1 ms | 35 / 12 |

These are between-model differences and review workload, **not boundary accuracy, confidence or verified errors**. Both models can share errors. The 48 selected windows supplement the existing fixed coverage samples; they do not replace inspection of agreement regions or establish full-song coverage. The source-guided hold rules are retrospective review targets, not independently validated section detectors.

## Reviewable contrast candidates

- **Twist:** both models expose two long A passages, with full active NNLS support on the native spans and A cosine approximately 0.854–0.892. The private developer draft is now revision 2 and holds two provisional common intersections: **[82.87927437641723, 96.5944671201814)** and **[136.90485260770976, 145.85142857142858)** seconds. They are named “A hold / build-up search window 1/2 (provisional)”. The second BTC hold ends at 145.85142857142858 seconds while CREMA continues to 146.7501133786848: an unresolved 0.899-second difference. The intersections are harmonic search windows, not verified formal build-up extents or tighter timing estimates.
- **Love:** recurring D material around 56–66 and 90–100 seconds contrasts with the G/C material. Longer C holds around 21.5–28.2, 42.8–49.5 and 117.7–124.3 seconds provide hold/stop/mute review targets. CREMA extends the second C hold to 53.499 seconds, while BTC proposes intervening G/C material; the discrepancy remains visible. No complete bridge map or physical mute timing follows.
- **Dylan:** the selected Am/C inventory contains 23 BTC runs and 21 CREMA runs, with intervening harmony explicitly represented in the full native charts. These are filtered response runs, not consecutive chords, a formal section count or a verified repeat count. BTC's additional Am fragment at 82.508–83.065 seconds remains unresolved. Shared C/E tones make nearest-template relabelling unsafe: on the first BTC Am span, C cosine is 0.820 versus Am 0.767. Acoustic scores remain context only.
- **Wild:** CREMA's long A passages at 26.099–45.976 and 91.672–111.177 seconds identify contrast search regions. BTC fragments them with other proposals, and the reported NNLS active support is 16.347/19.876 and 15.604/19.505 seconds respectively. This does not establish the source-described G/A figure or authorize replacing outside-palette cues.

Teacher sources and their separate practice adaptations remain in the [first-four source/pitch review](STARTER_FOUR_CATALOGUE_CHECK.md). Harmonic holds and changes cannot determine repeated attacks, stroke direction, swing, muting, bar counts or physical guitar voicing. NNLS uses approximately 743 ms windows and 93 ms hops; its template scores cannot verify precise physical change times. Pulses are not consumed by this pass, and no chord is snapped to a pulse or numbered bar.

## Cached procedural controls

The unchanged queue was evaluated retrospectively on all 64 cached synthetic recordings, totaling 450 seconds. No models were rerun or policy retuned. Reference matching uses a fixed 150 ms tolerance. Typed metrics require matching core labels and transition direction; time-only metrics can credit a nearby wrong transition. All-transition F1 is **0.770 BTC / 0.583 CREMA** for typed matching, versus **0.821 / 0.699** for time-only matching. These targets include N/X edges; harmonic-only results and coverage ledgers remain in the JSON. This is not a fresh selected-pipeline or popular-recording accuracy estimate.

| Queue | Windows across 64 cases | Replay union / audio seconds | Primary error/extra points inside windows | Operational misses inside windows | Direct primary flags reference-correct at 150 ms |
|---|---:|---:|---:|---:|---:|
| All | 161 | 238.604 / 450 | 49 / 52 | 16 / 40 | 87 / 134 |
| Selected 12 per case | 155 | 237.934 / 450 | 49 / 52 | 16 / 40 | 82 / 129 |

The 52 primary error/extra points comprise 26 residual timing errors and 26 extras: windows cover 26/26 and 23/26 respectively. “Operational misses” are reference transitions left unmatched after first matching at 150 ms and then associating remaining compatible transitions within 500 ms; the association does not relax the passing tolerance. Wrong labels can contribute an extra and a miss, so this partition does not identify a physical cause. All strict reference misses, including residual timing errors, are also retained: windows cover 41/66.

The **64.9% (87/134)** and **63.6% (82/129)** figures are the proportion of directly flagged BTC points that the procedural reference considers correct. They are **not false-positive rates**: their denominator is flagged points, rather than all reference-correct native points. Correct points incidentally covered by replay padding are counted separately. The queue covers many existing erroneous points while missing many absent transitions and spending about half the audio duration; it does not certify a recording or establish correction effort.

All eight symbolic expected-behaviour checks pass. In the shared-error negative control, shifting **both** model charts by +0.30 seconds preserves five perfect between-model pairs and produces zero priority windows, while every typed and time-only 150 ms reference match fails. Wrong-direction transitions remain unmatched even at identical times; silence, unknowns and gaps remain distinct. These symbolic controls test mechanics, not audio recognition.

## Artifacts and replay

The final [real report](../experiments/generated/catalogue-starter-timing-v2-20261016/report.json) retains native spans, complete score context, replay queues, recording identities and method/specification hashes. Its SHA-256 is `9cbf0d2e388b340fee5835c7a0e0084780a9ee01c43d9c4c60ff33cd3c89c6a6`. The final [controls report](../experiments/generated/catalogue-timing-controls-v3-20261016/report.json), [source snapshot](../experiments/generated/catalogue-timing-controls-v3-20261016/source-snapshot.json), per-case files and symbolic controls retain the evaluation inputs and denominators. The controls report SHA-256 is `26e17d8c4f6af9b225f42b80d9745fff96886fac84163544ec70987ffdbf6d0d`.

These full reports and media are ignored local artifacts. The committed [compact summary](STARTER_FOUR_TIMING_REVIEW.json) pins them and retains the key denominators, policies and provenance. [Editorial backup v2](../catalogue/starter-four-curation-proposals-v2.json) versions the four project-authored drafts, including the two earlier Dylan label proposals and the new Twist windows; v1 remains historical. The earlier unversioned timing run is retained locally, but v2 is final because it additionally pins the executing chord-template and review-path dependencies. Its numerical results are unchanged. Controls v3 records the portable runner and final dependency hashes.

Generation took **0.278 seconds** for the real review and **0.105 seconds** for cached controls on the current Mac. These are analysis runtimes, not curation time or hosting estimates. The saved Twist agent session measures draft entry only; research, analysis and musical validation are excluded. Human correction effort remains unmeasured. No new chord labels or native times were edited in this pass.

Verification on 16 October: 406 Python tests discovered, 386 passed and 20 optional-dependency checks skipped; all 18 new timing tests pass. All 124 JavaScript checks passed earlier the same day; this continuation changes no JavaScript. All 39 frozen workflow pins, 45 reviewer public assets and 48 learner public assets verify, with five private routes returning 404. An independent audit reproduced all 64 synthetic cases' counts/coverage and 255 real-hold NNLS cosine values, then verified the final reports' source pins. Browser verification confirms Twist draft revision 2 saved separately; the two bounds exactly equal the native-hold intersections. No musical acceptance follows from these software checks.

From `/Users/davidcrompton/Documents/music-os`, with the existing ignored cached inputs present, use fresh output directories:

```sh
.venv-analysis/bin/python experiments/analysis/catalogue_timing_review.py \
  --pack experiments/generated/catalogue-curation-20261014 \
  --pitch-spec experiments/fixtures/catalogue-starter-four-v1.json \
  --evidence experiments/generated/catalogue-starter-four-pitch-v3-20261014 \
  --spec experiments/fixtures/catalogue-starter-timing-v1.json \
  --output experiments/generated/catalogue-starter-timing-replay

.venv-analysis/bin/python experiments/analysis/catalogue_timing_controls.py \
  --suite experiments/generated/synthetic-suite \
  --spec experiments/fixtures/catalogue-starter-timing-v1.json \
  --output experiments/generated/catalogue-timing-controls-replay
```

Existing outputs are refused. The [developer reviewer](http://127.0.0.1:8073/) retains separate, unaccepted draft content; ordinary playback remains available at [port 8070](http://127.0.0.1:8070/). Continue with bounded operator replay of contrasts and timing disagreements, preserving unresolved spans. No founder transcription task is required.
