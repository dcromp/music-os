# Synthetic screening results

10 October 2026 · 64 deterministic cases × 5 algorithms = **320 successful comparisons**, with no failed runs.

## Overall results

Values are unweighted means across cases. Agreement within each case is duration-weighted. These custom screening metrics are not mir_eval and are not estimates of real-song accuracy.

| Candidate | Core incl. silence | Chord-only core | Root | Exact labels | Boundary F1 (150 ms) |
|---|---:|---:|---:|---:|---:|
| Baseline | 93.3% | 96.1% | 93.8% | 90.4% | 0.630 |
| BTC | 89.1% | 91.6% | 90.1% | 84.7% | 0.761 |
| CREMA | 74.9% | 84.4% | 77.5% | 61.4% | 0.607 |
| ChordMini | 94.7% | 94.2% | 94.4% | 90.0% | 0.927 |
| Chordino | 78.7% | 95.4% | 81.1% | 72.3% | 0.388 |

## Per level: chord-only major/minor agreement

| Level | Baseline | BTC | CREMA | ChordMini | Chordino |
|---|---:|---:|---:|---:|---:|
| Clean triads | 99.9% | 86.4% | 82.5% | 94.0% | 100.0% |
| Voicings/timbres | 97.0% | 92.5% | 74.9% | 89.0% | 95.8% |
| Guitar-like attacks | 98.0% | 97.7% | 93.6% | 96.6% | 98.2% |
| Controlled distractors | 97.8% | 95.5% | 95.5% | 98.1% | 95.8% |
| Timing/vocabulary complexity | 79.1% | 95.4% | 81.1% | 95.3% | 78.6% |

## Interpretation

- ChordMini leads boundary F1 and the earlier core metric that includes silence. The cheap baseline has the highest chord-only core mean on these artificial tones. Those rankings differ because metric scope matters; neither selects a production engine.
- The template baseline fits these procedural tones well but adds about five extra segments per case on average. Its high chord score can conceal a distracting display.
- BTC has lower core agreement overall but better temporal boundaries than the baseline, especially on plucked and complex conditions.
- CREMA struggles more with these short synthetic inputs, including silence, extensions and timing. Investigate input/domain/decoding behaviour before rejecting it for real recordings.
- Chordino recognises all clean voiced major/minor triads in this suite, but often anticipates the first chord, misses ending silence and merges fast changes. It scores 95.4% on chord-only core versus 78.7% when silence is included, with boundary F1 0.388. ChordFormer remains a research candidate pending source/checkpoint review; move to real recordings before expanding the search further.

## Suite and metrics

The 64 cases cover all twelve roots in major/minor triads; paired voicing/register/timbre changes; plucked, staggered and accented envelopes; bass, drums, melodic distractors, 10 dB noise, distortion and combined mixes; fast/offbeat changes, changing chord durations, power chords and sevenths. The tempo-ramp case approximates acceleration through changing event/attack periods; it is not a human rubato performance. All audio is procedural oscillators and envelopes, not physical guitar recordings.

Both major/minor metrics collapse supported extensions to their triad family and ignore bass notation. The earlier core metric includes reference silence; the new chord-only metric excludes silence and ambiguous power chords, and averages only cases with eligible chord duration. Thus power-chord cases cannot score well on chord recognition just by correctly predicting their silent intro/outro. Coverage is explicit in JSON/CSV. Ambiguous power-chord spans are excluded from that metric and have a separate acceptable-label score. Exact labels remain strict and therefore penalise missing extensions and additional inversion notation; generated inversion cases do not have bass-note reference labels, so exact inversion conclusions are inappropriate. Root and boundary scores help expose these differences.

Boundary matching uses a 150 ms tolerance, one-to-one greedy matching, and all supplied event boundaries including silence transitions. Extra/unmatched changes reduce precision. It tests timing rather than whether each boundary carries the right chord. Screen/holdout are paired generator recipe variants, not proof of independence from a model training corpus.

Every reused prediction must match the audio SHA-256 and recording ID/duration. Missing predictions, adapter errors or timeouts are recorded as failures and make the runner exit nonzero. Pretrained models load once per batch. Per-file analysis runtime and scoring runtime are separate; first-use compilation/model startup must not be multiplied by every clip.

The raw [JSON](SYNTHETIC_RESULTS.json) and [CSV](SYNTHETIC_RESULTS.csv) include every case, score and failure status. Input assets and predictions remain local/generated. Model setup and hashes are documented in [BTC_SETUP.md](BTC_SETUP.md), [CREMA_SETUP.md](CREMA_SETUP.md), [CHORDMINI_SETUP.md](CHORDMINI_SETUP.md) and [CHORDINO_SETUP.md](CHORDINO_SETUP.md).

## Repeat

Install the isolated candidate environments from their setup documents, then run:

```sh
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py generate
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini,chordino
```

The first four models reuse their matching saved predictions; Chordino was newly inferred on the same 64 inputs. The committed combined report was then rescored to add the chord-only metric; this rescoring is not a second model inference run.

Use `--reuse-existing` only to rescore already generated predictions; it checks input hashes and does not perform new model inference. Use the browser’s Load synthetic suite and Load case controls to inspect the same audio with reference and candidate charts.

## Browser verification

The 64-case inventory and all four model choices were verified on the deployed Mac browser. A cold-loaded strumming case could seek to 1.0 seconds before playback and display the correct current source-time chord. The server now supplies WAV byte-range responses; Native sentinel/timing conversion and silence-excluding scoring checks were added. See the README for the current test count.

## Next

Chordino screening is complete. Inspect the weakest cases and validate models on the preselected GuitarSet pilot, then on permitted recordings representative of the planned practice repertoire. Separation and soft key/context assistance are subsequent controlled pipeline comparisons in plan.md. Founder guitar sessions follow the automated screening and reference checks. No guitar ratings have been used in this report.
