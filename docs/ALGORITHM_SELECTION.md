# Initial Mac algorithm decision

Completed 13 October 2026. **Roadmap stage 1 (initial algorithm evaluation and selection) is complete.** This selects the offline workflow for a curated beginner catalogue. It does not certify automatic lessons or unrestricted song transcription. Catalogue correction effort and ordinary guitar followability remain the stage 2/3 acceptance gates; the broader Phase A product-readiness exit has not passed.

## Selected workflow

| Step | Decision | Reason / limit |
|---|---|---|
| Input | Analyse the original mix once, then cache the output | Separation gave a small, uneven downstream gain. Keep exact recording IDs, audio hashes and source timing. |
| Basic chord draft | **BTC-ISMIR19**, official 25-label checkpoint, CPU, four threads | Stronger recent core-harmony diagnostics; inexpensive local batch inference. Only major/minor plus no-chord, with no added smoothing or beat snapping. |
| Richer review alternative | **CREMA 0.2.0 / a4c7d57.0**, native decoding | Earlier acoustic pilot winner; retains more qualities and inversions. Compare separately; no majority vote, automatic model switching or confidence claim. |
| Pulse / chord duration | Existing **tempo-guided librosa** tracker | Approximate local pulse counts after an explicit song tempo/meter convention. Seconds outside supported pulse coverage. |
| Strumming | **Authored practice drills** | No tested algorithm transcribes down/up strokes. Match actual recorded parts during catalogue review. |
| Teaching arrangement | Recording-specific reviewed shapes, capo/tuning, sections and rhythm | Neither BTC nor CREMA output is a verified playable simplification. Preserve the raw charts separately. |

BTC cannot emit suspensions, power chords, slash bass or richer shapes. It can therefore miss a musically important distinction even when a major/minor score is high. CREMA cannot emit add9 or 7sus4 either. Wonderwall and other distinctive arrangements need reviewed teaching shapes; the beginner scope does not justify replacing every chord with a triad.

This is a fixed engineering choice for new basic-harmony drafts. We have not fitted a classifier to switch between models from a guessed recording category, nor calibrated model confidence. CREMA remains an available review alternative when BTC loses a needed distinction or fails an audible section.

## Evidence behind the choice

| Diagnostic | BTC intended/supported major/minor | CREMA | Interpretation |
|---|---:|---:|---|
| Six original acoustic comping performances | 84.0% | 93.9% | CREMA wins this small pilot; BTC misses substantial harmony in the Funk example. |
| Four fresh acoustic comping performances | 92.0% | 86.3% | BTC wins the full comping subset. Only two are experiment holdouts: BTC 96.2%, CREMA 96.5%. |
| Three publisher-paired jazz ensemble clips | 69.2% | 64.9% | BTC leads against supported written-chart targets, with 83.8% eligible coverage. These are jazz performances and musician-authored grids. |

Sources: [original guitar pilot](GUITARSET_PILOT.md), [fresh guitar comparison](FRESH_GUITARSET_CHORD_CHECK.md), [ensemble comparison](JAZZSAMBA_REFERENCE_CHECK.md). All five candidate integrations completed their synthetic and real-reference runs. Synthetic rankings did not transfer reliably, so they are diagnostics rather than the selection criterion. Dataset training exclusion is unproven; experiment holdouts are not certified unseen model-training material. Single-note solo contextual harmony remains weak for every model.

The models trade places across material. BTC is selected for the narrower basic-harmony task, with CREMA retained for review; these figures do not establish rock-catalogue accuracy. The five popular-song annotation candidates have no proven master/time-origin match, so the new ten-song run receives **no accuracy score**.

## Closed and deferred alternatives

- **Chordino:** retain the runnable practical alternative and historical comparison packs. Do not require it in the new default workflow; it trails BTC on the newer comping/ensemble diagnostics.
- **ChordMini/ChordNet:** retain saved results; its synthetic lead did not establish an advantage on recorded material. No new integration work in the default pipeline.
- **Template baseline:** keep for fixtures and low-cost controls. Its real-harmony errors and excess changes make it unsuitable as the default learner chart.
- **BeatThis small0:** available for targeted fluctuating-tempo investigations, outside the default pipeline. Better phase results on some inputs do not resolve pulse-level ambiguity. Nominal-guitar duration-count error is 0.545 beats versus 0.084 for the guided librosa comparison.
- **Numbered bars, inferred downbeats and chord snapping:** excluded. Nominal holdout bar-start predictions produce many extras; current timing evidence supports approximate duration units and seconds fallback.
- **Demucs separation:** targeted experiment only. Controlled supported agreement improves 69.1761% to 69.6693% (0.493 percentage points); two of three excerpts worsen. This instrumental-jazz experiment is not guitar-isolation evidence.
- **Known-chart / NNLS alignment:** research candidate only. Correct ordered charts do not guarantee accepted timings or section counts. Existing guards discard too much correct ensemble coverage, and corrupt arrangements still produce cues.
- **Key-conditioned relabelling and automatic strumming inference:** deferred because no evaluated implementation demonstrates a benefit.
- **More model architectures:** reopen only when a recurring catalogue failure cannot be handled affordably with the selected workflow and review.

Detailed negative results remain in [beat comparisons](BEAT_THIS_COMPARISON.md), [nominal downbeats](NOMINAL_DOWNBEAT_CHECK.md), [separation controls](SEPARATION_CHECK.md), [ensemble alignment](JAZZSAMBA_ALIGNMENT_CHECK.md) and [written-bar alignment](BAR_CHART_ALIGNMENT.md).

## Implementation and reproducibility

The versioned [selection record](../experiments/fixtures/selected-workflow-v1.json) pins the models, existing settings, dependency files, adapters and evidence. The existing adapters retain their frozen inference behaviour. The automatic pack builder now supports an explicit BTC primary and CREMA secondary, including separate batch-output roots, and preserves native chart/audio bytes. Default commands without model flags retain the legacy CREMA/Chordino mode.

From `/Users/davidcrompton/Documents/music-os`, after the model setup in [BTC_SETUP.md](BTC_SETUP.md) and [CREMA_SETUP.md](CREMA_SETUP.md), use fresh output directories:

```sh
.venv-btc/bin/python experiments/analysis/candidates/btc_adapter.py \
  --batch-manifest experiments/generated/repertoire-first-ten-v2/manifest.json \
  --output-root experiments/generated/selected-first-ten-btc-replay

.venv-analysis/bin/python experiments/analysis/automatic_drafts.py build \
  --manifest experiments/generated/repertoire-first-ten-v2/manifest.json \
  --output experiments/generated/automatic-first-ten-selected-replay \
  --primary-model btc --secondary-model crema \
  --primary-root experiments/generated/selected-first-ten-btc-replay
```

Verify the saved selected pack without inference or any accuracy claim:

```sh
.venv-analysis/bin/python -B experiments/analysis/workflow_check.py
```

For the replay directories above, add `--pack experiments/generated/automatic-first-ten-selected-replay --btc-root experiments/generated/selected-first-ten-btc-replay`. An optional `--output` must name an unused report file; existing inputs/reports are never overwritten.

The source pack already contains the exact cached CREMA charts. For new recordings, run CREMA's batch adapter too and pass its output directory with `--secondary-root`. Neither inference adapter downloads audio or trains a model. Analysis is offline; playback uses cached outputs without model environments.

[Completion evidence](ALGORITHM_SELECTION_RESULTS.json) records the new ten-song BTC run, 39 frozen-file checks, selected-pack byte/identity checks and the retained original player identity. All 319 available Python checks and 110 JavaScript checks pass; 20 optional-dependency Python checks are skipped in the analysis environment. Live QA verifies playback, seeking and the CREMA alternative, with all 48 served assets byte-identical and four private routes returning 404. The new pack is a local research artifact, not a public deployment. Ports 8070/8068 retain the existing CREMA charts and saved practice/feedback context. Promote reviewed arrangements in the next milestone rather than silently replacing them from a benchmark ranking.

## Next acceptance gates

Stage 2 checks the exact recording, sounding harmony versus played shapes, physical change timing, sections and suggested rhythms. Record actual reviewer correction minutes per audio minute and the changes needed. Detector disagreement is a workload hint, not measured correction time or accuracy.

Stage 3 measures normal guitar followability and usefulness, followed by the two-week practice trial. The founder does not need to annotate chords or timestamps. No founder input blocks the completed algorithm selection.

Commercial model/content distribution and hosting economics remain later gates. Existing source/weight/dependency provenance is recorded in the setup documents; local Mac runtime is not a cloud cost quote. Cache reviewed catalogue arrangements and measure one-time preparation separately from recurring playback costs.
