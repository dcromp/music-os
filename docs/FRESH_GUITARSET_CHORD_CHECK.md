# Fresh five-model guitar chord diagnostic

Completed 12 October 2026: ten exact paired recordings, five unchanged candidates,
50 successful inference runs and 100 intended/performed reference comparisons.
The [frozen protocol](../experiments/fixtures/guitarset-validation-protocol.json)
pins the prior ten-input selection, adapters, settings and model/native assets.
[Results](FRESH_GUITARSET_CHORD_RESULTS.json) preserve per-case failures, eligible
coverage and development/holdout plus comping/solo summaries. No key, tempo,
separation, smoothing or chart guidance enters inference.

| Candidate | Four comping inputs: intended major/minor | Six solos: intended contextual harmony |
|---|---:|---:|
| Baseline | 58.3% | 8.1% |
| BTC | 92.0% | 12.5% |
| CREMA | 86.3% | 7.6% |
| ChordMini | 87.1% | 6.8% |
| Chordino | 88.3% | 10.7% |

Eligible intended quality coverage is 95.9% for comping and 96.0% for solos.
Only two comping recordings belong to the experiment holdout: their scores are
60.9/96.2/96.5/96.2/97.3% in the table's order, at 92.4% coverage. Do not infer a
population ranking from two performances. Four holdout solos remain weak for all
models. Reporting one pooled ten-recording percentage would obscure this change
in task.

Both reference types inherit sheet-derived roots and interval boundaries.
Intended harmony is contextual; a melody need not sound all notes of its
underlying chord. Performed labels are sheet-informed note-derived symbolic
descriptions, including qualities excluded by major/minor scoring. Their solo
eligible coverage is only 39.8%. These are not physical-onset or full-mix scores.
Development/holdout is this experiment's split, not proven training exclusion.

BTC deserves continued comparison; CREMA remains a useful draft candidate rather
than a universal winner. Keep the cheap baseline as a control and Chordino as a
practical alternative. Existing player charts are unchanged. Low solo scores
also argue for supplying known harmony when building future accompaniment rather
than expecting a chord detector to recover an entire band from a lead line.

Preparation/scoring code is in
`experiments/analysis/guitarset_validation.py`. Saved Mac rescoring needs only
the pinned evaluation environment, not checkpoints:

```sh
.venv-pilot/bin/python experiments/analysis/guitarset_validation.py score
```

New inference requires all frozen model assets and their separate runtimes.
Use `prepare` for a fresh destination and `run` once; existing predictions are
preserved and only explicit `--reuse-existing` rescoring reuses them. Attempt logs
retain setup/runtime failures independently of musical scores.
