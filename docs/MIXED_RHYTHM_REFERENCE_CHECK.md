# External beat challenges

Completed 12 October 2026 on three preselected
[ARTBeaT author-paired clips](https://audiolabs-erlangen.de/resources/MIR/2024-ARTBeaT),
64.717 seconds total. Rico Rosenbusch's 2024 dataset is CC BY 4.0. Original WAV
and ground-truth CSV files are paired by selected ZIP-entry CRC/size and SHA-256;
the [result snapshot](MIXED_RHYTHM_REFERENCE_CHECK.json) preserves all pins and
metrics. Ground-truth events are separate from collected listener taps. The
distributed README does not establish how individual physical attacks were
marked, and supplies no bar-position labels.

The unchanged librosa tracker uses default 120 BPM, without source tempo or
reference-time guidance. Whole-recording one-to-one matching retains misses:

| Clip | Split | F1 at 70ms |
|---|---|---:|
| Layered synth arpeggio/instruments | Development | 96.3% |
| Distorted guitar/drums, source-described 7/8 | Holdout | 84.5% |
| Performed piano with fluctuating tempo | Holdout | 51.7% |

Aggregate F1 is 76.3% at 70ms, with 92 matched/29 missed/28 extra pulses; at 150ms
it is 81.3%. The two holdouts together score 66.3% at 70ms. These controlled
external challenges are neither whole rock songs nor a population accuracy
estimate. No duration-count, downbeat, chord or strumming score is invented.

The piano failure motivates a separate tempo-adaptive candidate comparison.
Preserve these results and label reuse retrospective after exposure. Five new
challenge recordings and unchanged neural candidate settings are frozen before
their inference in
[the next selection](../experiments/fixtures/beat-candidate-selection.json).

Saved local inputs/results are in
`experiments/generated/mixed-rhythm-reference-v1`; pinned `.venv-pilot` can
rescore them with `rhythm_reference_eval.py`. New extraction needs the separate
librosa environment. The source preparation helper is saved with the ignored
candidate assets; no media is redistributed in Git.
