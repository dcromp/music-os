# Synthetic screening results

10 October 2026 · 64 deterministic cases × 4 algorithms = **256 successful comparisons**, with no failed runs.

## Overall results

Values are unweighted means across cases. Agreement within each case is duration-weighted. These custom screening metrics are not mir_eval and are not estimates of real-song accuracy.

| Candidate | Major/minor core | Root | Exact labels | Boundary F1 (150 ms) |
|---|---:|---:|---:|---:|
| baseline | 93.3% | 93.8% | 90.4% | 0.630 |
| btc | 89.1% | 90.1% | 84.7% | 0.761 |
| crema | 74.9% | 77.5% | 61.4% | 0.607 |
| chordmini | 94.7% | 94.4% | 90.0% | 0.927 |

## Per level: major/minor core agreement

| Level | Baseline | BTC | CREMA | ChordMini |
|---|---:|---:|---:|---:|
| Clean triads | 95.6% | 86.8% | 74.0% | 94.8% |
| Voicings/timbres | 95.4% | 89.0% | 70.6% | 89.8% |
| Guitar-like attacks | 96.3% | 94.3% | 87.2% | 96.5% |
| Controlled distractors | 96.1% | 93.2% | 87.7% | 97.8% |
| Timing/vocabulary complexity | 80.1% | 86.8% | 59.3% | 95.3% |

## Interpretation

- ChordMini is the strongest initial candidate on core harmony and boundaries in this suite. Keep it for the next screening stage alongside BTC and the cheap baseline; this is not production selection.
- The template baseline fits these procedural tones well but adds about five extra segments per case on average. Its high chord score can conceal a distracting display.
- BTC has lower core agreement overall but better temporal boundaries than the baseline, especially on plucked and complex conditions.
- CREMA struggles more with these short synthetic inputs, including silence, extensions and timing. Investigate input/domain/decoding behaviour before rejecting it for real recordings.
- Chordino/NNLS-Chroma remains untested because project-local Mac host/plugin setup is outstanding. ChordFormer is another research candidate pending source/checkpoint review. Do not treat four tested approaches as the entire model universe.

## Suite and metrics

The 64 cases cover all twelve roots in major/minor triads; paired voicing/register/timbre changes; plucked, staggered and accented envelopes; bass, drums, melodic distractors, 10 dB noise, distortion and combined mixes; fast/offbeat changes, changing chord durations, power chords and sevenths. The tempo-ramp case approximates acceleration through changing event/attack periods; it is not a human rubato performance. All audio is procedural oscillators and envelopes, not physical guitar recordings.

Major/minor core collapses supported extensions to their triad family and ignores bass notation. Ambiguous power-chord spans are excluded from that metric and have a separate acceptable-label score. Exact labels remain strict and therefore penalise missing extensions and additional inversion notation; generated inversion cases do not have bass-note reference labels, so exact inversion conclusions are inappropriate. Root and boundary scores help expose these differences.

Boundary matching uses a 150 ms tolerance, one-to-one greedy matching, and all supplied event boundaries including silence transitions. Extra/unmatched changes reduce precision. It tests timing rather than whether each boundary carries the right chord. Screen/holdout are paired generator recipe variants, not proof of independence from a model training corpus.

Every reused prediction must match the audio SHA-256 and recording ID/duration. Missing predictions, adapter errors or timeouts are recorded as failures and make the runner exit nonzero. Pretrained models load once per batch. Per-file analysis runtime and scoring runtime are separate; first-use compilation/model startup must not be multiplied by every clip.

The raw [JSON](SYNTHETIC_RESULTS.json) and [CSV](SYNTHETIC_RESULTS.csv) include every case, score and failure status. Input assets and predictions remain local/generated. Model setup and hashes are documented in [BTC_SETUP.md](BTC_SETUP.md), [CREMA_SETUP.md](CREMA_SETUP.md) and [CHORDMINI_SETUP.md](CHORDMINI_SETUP.md).

## Repeat

Install the isolated candidate environments from their setup documents, then run:

```sh
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py generate
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini
```

Use `--reuse-existing` only to rescore already generated predictions; it checks input hashes and does not perform new model inference. Use the browser’s Load synthetic suite and Load case controls to inspect the same audio with reference and candidate charts.

## Next

Extend screening with Chordino and source/checkpoint-verified newer candidates, inspect the weakest cases, then validate promising models on permitted real-recording holdouts. Founder guitar sessions follow the automated screening and reference checks. No guitar ratings have been used in this report.
