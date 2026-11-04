# Frozen spectral versus NNLS acoustic alignment

64/64 cases completed as pairs; 0 excluded and 0 failed/partial cases. Both paths use chart_aligner 0.2.0 and the same frozen defaults.

Correct ordered chord labels and their event count are supplied. All reference timestamps and N events are withheld from inference. This measures conditional timing on procedural audio, not recognition or real-song accuracy.

| Backend | Mean boundary F1 | Precision | Recall | Extra / missed | Matched error | Mean X | Silence-duration coverage | Feature / align time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| spectral | 0.9038 | 0.8476 | 0.9969 | 59 / 1 | 50.8 ms | 0.46% | 82.78% | 0.645s / 1.094s |
| nnls-chroma | 0.9844 | 0.9844 | 0.9844 | 5 / 5 | 77.0 ms | 0.00% | 82.78% | 3.729s / 1.175s |

Metrics are unweighted case means on paired successful cases. Errors cover matched boundaries only. The 150ms matching tolerance and decoder settings were frozen before this comparison; failures remain visible in JSON/CSV.

NNLS reduces spurious changes on this generator, while its matched boundaries have a larger average timing error. Its five unmatched reference boundaries and five unmatched predictions occur in the sine screen/holdout cases, low-register holdout, distortion holdout and power-chord screen. The total predicted boundary count is still 264: these are timing mismatches outside the tolerance, rather than five omitted sequence positions. Both paths visit every supplied sequence position. All 128 reference silence boundaries match, but the unchanged short-window silence mask covers only 82.78% of the reference silence duration.

On the existing procedural screen split, mean F1 is 0.9116 spectral / 0.9909 NNLS; on its holdout split it is 0.8867 / 0.9700. These splits share a generator and are not an independent real-song test. Neither backend flags a large acoustic mismatch on these correctly labelled cases; that heuristic does not establish precise timing or acceptance. Every output still requires human review.

Exact unmodified feature calls timed by serial wrappers. Spectral extraction is already included in align_call; native NNLS extraction is separate. NNLS align_call also computes original PCM features for the unchanged short-window silence mask. Decoder/other time excludes measured PCM features and evidence loading/resampling but includes chart/audio I/O, scoring templates, path decoding and output construction. End-to-end inference excludes evidence serialization, subsequent output publication and evaluation; no double-counting of spectral extraction.

## Interpretation limits

- Correct labels, event count and order are supplied: conditional timing, not independent chord recognition accuracy.
- No settings tuned on this run; both paths use the same decoder, silence mask and mismatch thresholds.
- NNLS uses an approximately 743ms native window and 93ms hop at 22050Hz; interpolation to a 25ms decoder grid does not create finer acoustic resolution.
- Features are offline with global tuning; cosine scores and mismatch heuristics are not calibrated confidence.
- Finite start/end constraints can force a wrong chart to complete; X gaps, boundary errors and sequence diagnostics must be inspected.
- All 64 recipes share a procedural generator; named screen/holdout splits do not establish real-song generalisation.
- A smaller matched-boundary error can coexist with missed changes; no real-song or application readiness claim follows.

## Reproduce

```sh
.venv-analysis/bin/python experiments/analysis/alignment_comparison.py
```

The native acoustic host must first be built as described in [NNLS_CHROMA_EVIDENCE.md](NNLS_CHROMA_EVIDENCE.md). The generated 64-case suite must already exist. Default outputs are ignored local artifacts under `experiments/generated/acoustic-alignment-comparison/`; choose a new `--output` directory or explicitly use `--overwrite`. The complete suite is protected against output aliases. The original alignment screen is untouched.

Publish a review snapshot after inference:

```sh
.venv-analysis/bin/python experiments/analysis/alignment_comparison.py --publish-docs --overwrite
```

The machine report records audio, untimed-chart, hidden-reference, feature/evidence, output and implementation hashes. Native build/source provenance is preserved in each evidence packet. Fixed NNLS metadata and audio pairing are validated before alignment. Settings were not adjusted using Creep or other real recordings.
