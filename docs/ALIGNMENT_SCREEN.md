# Conditional synthetic alignment screen — 10 October 2026

The experimental known-chart aligner completed **64/64** existing procedural cases, with **zero failures and zero excluded labels**. The input for each case contained only its ordered non-`N` intended chord labels. Every reference timestamp and every reference `N` event was withheld from the aligner. Charts used `finite`, `start_policy: first` and `end_policy: last`, with the initial default scoring and transition settings.

This tests **timing conditional on being given the right labels, count and order**. It does not measure chord recognition, online-chart correctness, song-structure discovery or real-song accuracy. The reference timestamps are read separately by the runner only for scoring the completed result.

| Material | Cases | Boundary F1 within 150 ms | Precision | Recall | Matched mean error | Extra boundaries | Missed boundaries | Mean X coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Clean triads | 24 | 87.8% | 81.3% | 100.0% | 77.9 ms | 17 | 0 | 0.443% |
| Voicings and timbres | 12 | 93.5% | 90.3% | 98.3% | 43.7 ms | 9 | 1 | 0.231% |
| Guitar-like attacks | 6 | 90.3% | 83.4% | 100.0% | 30.3 ms | 7 | 0 | 0.416% |
| Controlled distractors | 12 | 88.7% | 81.8% | 100.0% | 31.1 ms | 19 | 0 | 0.879% |
| Temporal/vocabulary complexity | 10 | 94.9% | 90.8% | 100.0% | 30.2 ms | 7 | 0 | 0.280% |
| **All cases** | **64** | **90.4%** | **84.8%** | **99.7%** | **50.8 ms** | **59** | **1** | **0.457%** |

Percentages and errors are **unweighted case means**. Counts are summed. The all-case row therefore is not a pooled precision/recall ratio. There were 264 reference boundaries and 322 predicted boundaries; 263 reference boundaries matched. No supplied finite-sequence positions were missed. The aggregate inference runtime was approximately 0.87 seconds on this local run; this lightweight NumPy baseline is not a cost measurement for pretrained models or a deployed service.

All **128** reference silence boundaries matched a predicted boundary touching an `N` event within 150 ms, measured separately from generic/X transitions. Their mean matched error was **86.1 ms**. Yet only **82.8%** of the reference `N` duration was covered on average. The centred analysis window sees a neighbouring chord before or after the actual silence boundary, so a good tolerance-based boundary score does not establish precise silence coverage. No `N` duration fell inside annotated harmony in this particular suite.

Unknown `X` spans totalled **2.074 seconds**. Short gaps, especially near attacks and silence edges, produced extra boundaries even though X coverage was small. Consequently the high recall and low matched error must be read beside the **59 extra boundaries**, precision, and coverage. They do not establish that the display is stable enough for learners.

The recipe-design holdout subset scored 88.7% boundary F1 versus 91.2% for the screen subset, with matched errors of 35.0 ms and 58.0 ms respectively. Both use the same procedural generator; they are not evidence of real-recording generalisation. No settings were selected using real-song timing annotations.

## Metric and reference limits

All event starts after the first event count as boundaries, including `N` and `X` transitions. Ordered one-to-one matching maximises the number of pairs within 150 ms, then minimises their summed absolute timing error. This avoids undercounting closely spaced events when a nearest-first greedy assignment consumes the only match for a later boundary. Mean error includes **matched boundaries only**; missed and extra boundaries are always reported with it. Separate no-chord metrics match only boundaries with an `N` event on either side.

Every case has contiguous reference coverage over its complete generated audio. The scorer **rejects a partial reference** rather than interpreting an unannotated region as correct or incorrect. For a real recording, cut and fully annotate the chosen excerpt, then report the excerpt's coverage of the source separately. Neither a plausible cyclic path nor a manually checked short intro establishes whole-song timing accuracy.

The finite endpoint requirement supplies event count and order; it can force transitions when an input chart is wrong. Counterfactual wrong-chart tests flag acoustic conflicts and preserve `X` gaps. Even `no_large_mismatch_detected` is only a screening diagnostic: each result still requires review. The aligner emits no calibrated confidence score.

## Reproduce and inspect

```sh
.venv-analysis/bin/python experiments/analysis/alignment_screen.py
```

Add `--overwrite` to explicitly replace a prior run. Per-case untimed inputs, timelines and raw frame evidence are written under `experiments/generated/alignment-screen/cases/`; the machine report is `experiments/generated/alignment-screen/report.json`. Audio remains in the existing synthetic suite.

- [Setup and exact input assumptions](CHART_ALIGNER_SETUP.md)
- [Saved report JSON](ALIGNMENT_SCREEN.json)
- [Per-case CSV](ALIGNMENT_SCREEN.csv)

Next: compare a fully reviewed chord/section sequence against independently annotated timing in exact real recordings. Add duration or section constraints only after establishing a separate tuning/evaluation split, and compare with unconstrained recognition and optional source separation.
