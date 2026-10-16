# Rich-quality synthetic screen

24 generated cases; 224 successful attempts and 0 failures.

Raw recognizers infer labels from audio alone. Correct-chart aligners receive the ordered labels and count in advance: those results measure conditional timing, not recognition accuracy. Corrupt-chart runs report wrong labels remaining after unchanged X/N masks.

| Method / scenario | Cases ok / requested | Exact chord quality | Root | Maj/min | Maj/min coverage | Vocabulary coverage | False rich on plain | Boundary F1 | Extra / missed | X | Retained wrong labels |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| chordino | 24 / 24 | 61.5% | 83.9% | 96.2% | 68.4% | 64.0% | 3.9% | 43.2% | 55 / 105 | 0.0% | — |
| crema | 24 / 24 | 61.0% | 83.4% | 90.5% | 68.4% | 76.8% | 4.0% | 67.1% | 13 / 77 | 0.0% | — |
| nnls-chroma/correct | 24 / 24 | 96.8% | 97.1% | 97.6% | 68.4% | — | 2.4% | 96.5% | 5 / 5 | 0.0% | 8.703s |
| nnls-chroma/extra_extensions | 8 / 8 | 0.0% | 91.7% | 91.7% | 89.5% | — | 100.0% | 72.9% | 13 / 13 | 0.0% | 81.800s |
| nnls-chroma/simplified_quality | 16 / 16 | 23.9% | 58.8% | 83.8% | 57.9% | — | 0.0% | 55.0% | 76 / 46 | 16.9% | 109.069s |
| nnls-chroma/wrong_quality | 16 / 16 | 0.0% | 25.3% | 0.0% | 57.9% | — | 56.5% | 44.0% | 86 / 64 | 40.8% | 108.384s |
| nnls-chroma/wrong_section_order | 24 / 24 | 54.1% | 57.3% | 44.4% | 68.4% | — | 34.5% | 73.4% | 44 / 53 | 17.8% | 80.315s |
| spectral/correct | 24 / 24 | 98.9% | 99.2% | 99.1% | 68.4% | — | 0.9% | 100.0% | 0 / 0 | 0.0% | 3.132s |
| spectral/extra_extensions | 8 / 8 | 0.0% | 98.6% | 98.6% | 89.5% | — | 100.0% | 100.0% | 0 / 0 | 0.0% | 81.800s |
| spectral/simplified_quality | 16 / 16 | 23.8% | 88.7% | 99.1% | 57.9% | — | 0.0% | 58.2% | 124 / 30 | 7.5% | 131.166s |
| spectral/wrong_quality | 16 / 16 | 0.0% | 43.4% | 0.0% | 57.9% | — | 77.8% | 41.4% | 272 / 32 | 26.7% | 138.518s |
| spectral/wrong_section_order | 24 / 24 | 50.6% | 53.8% | 45.0% | 68.4% | — | 32.5% | 68.7% | 97 / 41 | 18.2% | 87.223s |

Quality/root rates are unweighted successful case means; their additive duration totals are also preserved. Exact quality ignores slash-bass only and retains suspensions/extensions. Major/minor reports eligible coverage separately. Boundary matching is ordered one-to-one within 150ms, including N/X transitions; errors cover matched boundaries only. Failed attempts stay in every requested subset denominator.

## Corrupt-chart safeguards

Completion is an integration check only. Residual wrong-label seconds and cases without large-mismatch warnings are the substantive tests; guards are not presumed safe because inference succeeds.

- nnls-chroma/extra_extensions: 81.800s retained incorrect labels; 81.800s incorrect rich labels; 8 cases with residual errors; 8 cases without a large-mismatch warning.
- nnls-chroma/simplified_quality: 109.069s retained incorrect labels; 0.000s incorrect rich labels; 16 cases with residual errors; 1 cases without a large-mismatch warning.
- nnls-chroma/wrong_quality: 108.384s retained incorrect labels; 108.384s incorrect rich labels; 16 cases with residual errors; 0 cases without a large-mismatch warning.
- nnls-chroma/wrong_section_order: 80.315s retained incorrect labels; 79.168s incorrect rich labels; 24 cases with residual errors; 7 cases without a large-mismatch warning.
- spectral/extra_extensions: 81.800s retained incorrect labels; 81.800s incorrect rich labels; 8 cases with residual errors; 8 cases without a large-mismatch warning.
- spectral/simplified_quality: 131.166s retained incorrect labels; 0.000s incorrect rich labels; 16 cases with residual errors; 5 cases without a large-mismatch warning.
- spectral/wrong_quality: 138.518s retained incorrect labels; 138.518s incorrect rich labels; 16 cases with residual errors; 1 cases without a large-mismatch warning.
- spectral/wrong_section_order: 87.223s retained incorrect labels; 86.327s incorrect rich labels; 24 cases with residual errors; 7 cases without a large-mismatch warning.

## Recipe subsets

| Raw recognizer / subset | Cases ok / requested | Exact chord quality | Root | Maj/min | Maj/min coverage | Vocabulary coverage | False rich on plain |
|---|---:|---:|---:|---:|---:|---:|---:|
| crema/family/rich_progression | 8 / 8 | 42.8% | 66.7% | 89.3% | 52.1% | 60.7% | 4.0% |
| crema/family/plain_control | 8 / 8 | 92.5% | 92.5% | 92.5% | 89.5% | 100.0% | 0.0% |
| crema/family/same_root_contrasts | 8 / 8 | 47.7% | 91.1% | 89.7% | 63.6% | 69.6% | 8.0% |
| crema/split/screen | 12 / 12 | 66.7% | 86.0% | 90.1% | 68.8% | 77.2% | 7.9% |
| crema/split/holdout | 12 / 12 | 55.3% | 80.8% | 90.9% | 68.0% | 76.3% | 0.1% |
| chordino/family/rich_progression | 8 / 8 | 36.0% | 68.3% | 95.0% | 52.1% | 37.4% | 8.1% |
| chordino/family/plain_control | 8 / 8 | 95.4% | 95.4% | 95.4% | 89.5% | 100.0% | 0.0% |
| chordino/family/same_root_contrasts | 8 / 8 | 53.0% | 88.1% | 98.3% | 63.6% | 54.6% | 3.6% |
| chordino/split/screen | 12 / 12 | 61.8% | 84.0% | 96.3% | 68.8% | 64.4% | 4.1% |
| chordino/split/holdout | 12 / 12 | 61.2% | 83.9% | 96.2% | 68.0% | 63.6% | 3.7% |

Vocabulary coverage is the fraction of reference harmonic seconds representable by the audited native output vocabulary; it is not model accuracy. Every family/condition and screen/holdout subset is recorded separately in JSON. These splits are recipe variants of one generator, not an independent real-song holdout.

## Failures

No integration/scoring failures.

## Limits

- Raw CREMA/Chordino are independent recognition; correct-chart labels/order/count are supplied, so their alignment scores are conditional timing, not recognition accuracy.
- Both aligners use existing frozen defaults; native feature extraction is cached once per audio and reused unchanged across controls.
- Wrong-chart residual errors measure false labels surviving X/N masking. A successful run or no-large-mismatch diagnostic does not validate the chart.
- Template cosine scores and mismatch diagnostics are not calibrated probabilities; finite endpoint constraints can force wrong charts.
- Synthetic screen and holdout share one procedural generator. They do not demonstrate real guitar, full-song, production or catalogue accuracy.
- NNLS native frames have approximately 93ms spacing and 743ms support at 22050Hz; resampling cannot create physical onset precision.
- Native recognizer output is preserved; no chart relabeling, key/capo fix, extension upgrade or consensus is applied.

## Reproduce

```sh
.venv-analysis/bin/python experiments/analysis/rich_quality_suite.py generate --output-dir experiments/generated/rich-quality-suite-v2
.venv-analysis/bin/python experiments/analysis/rich_quality_screen.py --suite experiments/generated/rich-quality-suite-v2 --output experiments/generated/rich-quality-screen-v2
```

Choose fresh output directories. The screen never overwrites a previous suite/screen. Existing CREMA and Chordino environments/native assets are required; no model download or training occurs. Audio bytes, independently untimed charts, hidden reference, raw predictions, evidence, implementations and native/model provenance remain in the machine report/artifacts. All reference timestamp scoring happens after all inference.
