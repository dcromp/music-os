# Automated draft screening

The automatic workflow uses CREMA as an experimental primary draft and Chordino as disagreement evidence. No manual annotations are needed for this screen. These are unchanged cached predictions; warnings do not replace chords.

All six preselected GuitarSet recordings passed pairing/hash checks, all 12 intended/performed comparisons completed, and primary scores exactly reproduced the previous pilot. This passes workflow checks, not a production accuracy gate.

| Reference | Primary major/minor | Eligible coverage | Raw disagreements capture primary errors | Raw disagreement error precision | Errors surviving agreement |
|---|---:|---:|---:|---:|---:|
| Intended | 93.9% | 98.1% | 47.5% | 19.2% | 50.0% |
| Performed | 92.7% | 78.4% | 35.3% | 28.7% | 62.2% |

Scores are duration weighted on `mir_eval.majmin` eligible reference spans. Raw disagreement precision means the fraction of disagreement time containing a primary label error. Other disagreement time has a correct primary label (the secondary is wrong or differs). It is an uncertainty signal, not an instruction to accept the secondary.

Raw disagreement here uses mutually eligible `mir_eval` root/major-minor comparisons, including explicit no-chord differences and excluding unknown predictions. The playback evidence reports its own harmonic-only agreement denominator; these are different measures with separate coverage. Neither is a correctness score without the dataset reference.

| Reference | Warning time / audio | Warnings capture primary quality errors | Label-error fraction within warnings | Correct-primary time inside warnings |
|---|---:|---:|---:|---:|
| Intended | 18.5% | 41.7% | 14.2% | 27.64 s |
| Performed | 18.5% | 33.8% | 22.2% | 12.40 s |

Warning workload is the union of all emitted warning intervals, including timing and unknown/short-event evidence. Intervals overlap only once. This label-error enrichment is deliberately not called timing accuracy or warning precision: a timing warning can be useful even where the chord label is correct. Short disagreement intervals may be omitted by the display thresholds.

Three deterministic known-label checks pass: same-root major/minor disagreement; C7 versus C major sharing the same triad; and two algorithms agreeing on the same wrong chord. The latter two explicitly demonstrate limits of agreement. These are semantic guard tests, not acoustic recognition tests.

GuitarSet totals 182.36 seconds of acoustic guitar. Performed roots and segmentation inherit the instructed lead sheet. Physical onset timing, full-band YouTube accuracy, extension accuracy and calibrated confidence remain unmeasured. Major/minor coverage differs between intended and performed annotations, so their scores have different denominators. The original dataset and model-overlap qualifications remain in [GUITARSET_PILOT.md](GUITARSET_PILOT.md).

The finite automatic gates are exact audio/chart pairing, valid ordered in-range timelines, complete cached comparisons, original-score parity and the semantic edge-case checks. User listening feedback is optional and can focus on a few flagged moments; full manual transcription is not a gate for the experimental play-along.

## Reproduce

From the repository root with the existing verified GuitarSet pilot assets and pinned evaluation environment:

```sh
.venv-crema/bin/python experiments/analysis/draft_screen.py
.venv-crema/bin/python -m unittest discover -s experiments/analysis/tests -p test_draft_screen.py
```

A separate `.venv-pilot` with `requirements-pilot.txt` can replace `.venv-crema`. The script reuses saved JSON; no neural model runtime is needed. Default output is `docs/DRAFT_SCREEN.json` and this Markdown. The JSON preserves input hashes, exact per-case seconds, roots, warning counts and all three known-label cases.
