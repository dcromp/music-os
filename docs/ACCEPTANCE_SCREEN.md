# Chart acceptance: frozen development and fresh validation

2026-10-11. The new guards reduce wrong supplied chords and stop harmonic progression through silence. They do **not** verify an arrangement. NNLS preserves most correct-chart coverage on fresh examples; the spectral decoder loses substantial correctness on those examples. Keep the existing learner player unchanged.

This is conditional alignment and chart acceptance: labels, order and count are supplied. It is not an independent chord-recognition score. No CREMA/Chordino inference was rerun and no Wonderwall data was used to choose thresholds.

## Completed steps

| Step | Status | Work measured |
|---|---|---|
| Declare bounded thresholds and eligibility rule | Complete before development | Four options, unchanged acoustic/old decoder settings |
| Development only | Complete | 12 screen cases, 440 attempts, zero failures |
| Freeze selected policy and implementation hashes | Complete before validation | Balanced policy, exact parameters and SHA below |
| Previous recipe holdout | Complete without tuning | 12 cases, 176 attempts, zero failures |
| Fresh frozen validation | Complete without tuning | 16 cases, 272 attempts, zero failures |
| Production/recording-specific arrangement acceptance | Not established | Negative controls still retain wrong labels |

The 888 attempts include frozen baselines and multiple supplied-chart variants; they are not 888 independent recordings. The 24 existing and 16 fresh recordings are synthetic. Prior recipe-holdout outcomes were already reported in the previous phase, so it is not a pristine blind holdout. The fresh pack was frozen independently before development selection, but still uses procedural synthesis and shared semantic scoring conventions.

## Predeclared selection and unsuccessful variants

Require all requested development runs to succeed and mean correct-chart semantic chord-quality loss versus frozen old correct charts <=10 percentage points for each acoustic backend separately. Among eligible options minimize corrupt retained wrong-label seconds, then maximize correct coverage, then prefer declared option order. If none qualifies, report no acceptable policy; freeze the all-success option with least maximum per-backend quality loss solely for diagnostic validation, without relaxing the eligibility constraint. No validation tuning or Wonderwall calibration.

| Option | Quality margin | Added-tone ratio / fraction | Spectral / NNLS mean quality loss | Correct harmonic coverage | Correct raw labels discarded | Corrupt wrong seconds | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|
| lenient | 0.12 | 0.08 / 0.35 | 4.620 / 0.020 pp | 95.9% | 2.1% | 92.783 | True |
| balanced | 0.08 | 0.12 / 0.50 | 9.118 / 0.103 pp | 93.8% | 4.3% | 73.197 | True |
| strict | 0.04 | 0.20 / 0.65 | 16.738 / 0.723 pp | 89.9% | 8.2% | 59.701 | False |
| very-strict | 0.02 | 0.28 / 0.75 | 20.425 / 3.530 pp | 86.8% | 11.4% | 54.279 | False |

Balanced won among eligible settings because it retained fewer wrong seconds than lenient. Strict and very-strict removed more wrong labels but failed the predeclared correct-chart loss limit. Rejection of every chord could not win this rule. Thresholds were not changed after validation failures.

## Correct charts: coverage and timing tradeoffs

| Dataset | Backend / policy | Correct harmonic seconds fraction | Accepted harmony | Raw wrong seconds | Retained wrong seconds | Correct raw labels discarded | Boundary F1 | Extra / missed boundaries | X seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| historical-holdout | spectral / old-frozen | 98.8% | 100.0% | 1.633 | 1.633 | 0.000s (0.0%) | 1.000 | 0 / 0 | 0.000 |
| historical-holdout | spectral / balanced | 92.7% | 93.8% | 1.633 | 1.430 | 8.547s (6.2%) | 0.715 | 80 / 2 | 8.996 |
| historical-holdout | nnls-chroma / old-frozen | 96.8% | 100.0% | 4.543 | 4.543 | 0.000s (0.0%) | 0.958 | 3 / 3 | 0.000 |
| historical-holdout | nnls-chroma / balanced | 96.6% | 99.7% | 4.543 | 4.295 | 0.177s (0.1%) | 0.882 | 18 / 3 | 0.425 |
| fresh-validation | spectral / old-frozen | 95.1% | 97.9% | 6.780 | 6.667 | 4.788s (2.1%) | 0.899 | 45 / 1 | 5.223 |
| fresh-validation | spectral / balanced | 72.9% | 77.3% | 57.218 | 10.465 | 7.154s (4.0%) | 0.740 | 96 / 12 | 55.600 |
| fresh-validation | nnls-chroma / old-frozen | 96.9% | 100.0% | 7.481 | 7.481 | 0.000s (0.0%) | 0.971 | 5 / 4 | 0.000 |
| fresh-validation | nnls-chroma / balanced | 96.3% | 99.2% | 7.381 | 6.959 | 1.403s (0.6%) | 0.898 | 30 / 4 | 1.824 |

Fresh spectral mean semantic-quality loss is **22.924 percentage points**, exceeding the development limit of 10 points. Its raw proposed path accumulates 57.218 wrong seconds versus 6.780 for the old path: the large coverage loss is not explained solely by masking correct labels. The active-dwell decoder itself changes position timing/order realization on these examples. Fresh NNLS mean loss is **0.516 points**; it discards 1.403 raw-correct seconds (0.608%) and preserves 96.3% duration-weighted correct harmonic coverage.

N/X gaps introduce additional output boundaries. For fresh correct NNLS charts, mean boundary F1 falls from 0.971 to 0.898 and extra boundaries rise from 5 to 30 while missed boundaries remain 4. A useful quality guard therefore still needs a way to avoid fragmented teaching output. Matched-boundary timing error excludes misses/extras and cannot compensate for them.

## Corrupt charts: residual wrong labels and silent traversal

| Dataset | Backend / policy | Corrupt cases | Raw wrong seconds | Retained wrong seconds | Cases retaining wrong labels | Silent position advances | Proposed harmonic events with no active evidence |
|---|---|---:|---:|---:|---:|---:|---:|
| historical-holdout | spectral / old-frozen | 32 | 289.092 | 219.858 | 32 | 47 | 47 |
| historical-holdout | spectral / balanced | 32 | 281.557 | 46.863 | 24 | 0 | 0 |
| historical-holdout | nnls-chroma / old-frozen | 32 | 281.388 | 189.990 | 32 | 52 | 52 |
| historical-holdout | nnls-chroma / balanced | 32 | 287.424 | 33.392 | 24 | 0 | 0 |
| fresh-validation | spectral / old-frozen | 52 | 512.739 | 326.013 | 52 | 119 | 78 |
| fresh-validation | spectral / balanced | 52 | 540.849 | 62.606 | 45 | 0 | 0 |
| fresh-validation | nnls-chroma / old-frozen | 52 | 510.058 | 272.492 | 52 | 149 | 112 |
| fresh-validation | nnls-chroma / balanced | 52 | 511.912 | 60.392 | 41 | 0 | 0 |

All evaluated sequences contain only harmonic positions, with silence markers withheld. Thus every counted silent target transition here is a harmonic promotion. New guards produce zero such transitions across all validation rows. The old decoder produces 301 on fresh cases (including correct charts) and 99 on corrupt historical cases. This fixes a specific forced-traversal failure; it does not establish correct repeats or section order.

| Fresh corrupt control | Backend | Retained wrong seconds: old → balanced | Wrong cases surviving: balanced / requested |
|---|---|---:|---:|
| extra_extensions | spectral | 43.934 → 0.775 | 4 / 4 |
| extra_extensions | nnls-chroma | 44.649 → 6.745 | 4 / 4 |
| wrong_quality | spectral | 93.701 → 6.167 | 5 / 12 |
| wrong_quality | nnls-chroma | 59.885 → 0.050 | 1 / 12 |
| simplified_quality | spectral | 115.656 → 32.444 | 12 / 12 |
| simplified_quality | nnls-chroma | 109.473 → 36.336 | 12 / 12 |
| wrong_section_order | spectral | 60.367 → 12.192 | 16 / 16 |
| wrong_section_order | nnls-chroma | 45.871 → 5.289 | 16 / 16 |
| missing_repeat | spectral | 11.024 → 8.553 | 4 / 4 |
| missing_repeat | nnls-chroma | 9.593 → 9.172 | 4 / 4 |
| extra_repeat | spectral | 1.331 → 2.474 | 4 / 4 |
| extra_repeat | nnls-chroma | 3.022 → 2.800 | 4 / 4 |

Both missing- and extra-repeat variants retain incorrect labels in all four fresh examples per backend. Quiet traversal is prevented, but extra repeats can still compress through active music. The all-corrupt-chart rejection gate is **false**; passing a local cosine/quality test must never mark the full arrangement approved.

## Frozen provenance

- Declaration SHA: `b144cb4445e8fefb1f6b0c7ca3eea1e0cdf96665958307b9f57777207a592cbe`.
- Selected policy SHA: `7a75786e45528622a86b5a6998452ef252c908f43a796c80d447c81b259c9ff3`; frozen at `2026-10-11T08:12:46.011066+00:00` before validation starts.
- Existing suite manifest: `a758123c992804e19a35bc1ba9910dd705534ab61fce707c150d5ffcbe55d57f`.
- Fresh suite manifest: `8056143b524e92d2a1795204c1033ccb2c168dc41e6dc3903a1057e56858215c`; independently frozen before development selection.
- Fresh NNLS evidence index: `ec34663b9b6dcdb58589a63eb9f6876e1b194376122ea121582e9af49587911b`.
- Guard source: `f25536fdf9c56e5fdb0d03e8441c91a60ee91961272afa47011b5b815e24e6b0`.
- Acceptance runner: `4e91855013bb6546ed4325c77c932fced72ebefc3e8ece32fdecdd5e80da9b35`.
- Frozen old aligner: `e21dc021cc8c508fea583ca4e11d293e6cfaf443535c4c370532cd9ff6a8a3e9`.

The JSON includes exact case IDs, input/untimed/reference/acoustic hashes, all requested case outcomes, failures, correct and corrupt groups, and raw/accepted scores. Each case result occupies one physical JSON line to keep the tracked report readable; this remains normal JSON. Full predictions and frames remain in ignored experiment artifacts. Existing old outputs are copied byte for byte and their decoder settings, chart/evidence/audio pairing are checked. Both paths share one immutable spectral feature cache per case and unchanged native NNLS evidence. No raw model inference or native extraction is performed by this runner.

The CLI forbids replacing even an empty existing output directory, verifies a required declaration hash before development and a required frozen-policy/module hash before validation. Reference timestamps are loaded only after all inference for that dataset. No outcome is used to retune. Explicit-N untimed charts and direct empty-row report-helper calls are outside this bounded run and need separately scoped completion/harmonic-progress guards.

## Reproduce

```sh
.venv-analysis/bin/python experiments/analysis/acceptance_screen.py declare \
  --output experiments/generated/acceptance-declaration-new.json \
  --fresh-manifest-sha256 8056143b524e92d2a1795204c1033ccb2c168dc41e6dc3903a1057e56858215c
# Record the declaration SHA printed above before running development.
.venv-analysis/bin/python experiments/analysis/acceptance_screen.py develop \
  --suite experiments/generated/rich-quality-suite-v2 \
  --cached-screen experiments/generated/rich-quality-screen-v2 \
  --declaration experiments/generated/acceptance-declaration-new.json \
  --declaration-sha256 <printed-declaration-sha> \
  --output experiments/generated/acceptance-development-new
# Record the frozen-policy SHA printed above before validation.
.venv-analysis/bin/python experiments/analysis/acceptance_screen.py validate \
  --frozen-policy experiments/generated/acceptance-development-new/frozen-policy.json \
  --frozen-sha256 <printed-frozen-policy-sha> \
  --historical-suite experiments/generated/rich-quality-suite-v2 \
  --historical-cache experiments/generated/rich-quality-screen-v2 \
  --fresh-suite experiments/generated/acceptance-validation-v1 \
  --fresh-cache experiments/generated/acceptance-validation-v1 \
  --output experiments/generated/acceptance-validation-screen-new
```

Choose fresh paths. The saved byte-paired NNLS caches and old baseline artifacts are required. Tests: `python -m unittest discover -s experiments/analysis/tests -p test_acceptance_screen.py` (13 checks).

Next development should isolate why active-dwell progression loses correct spectral paths, and evaluate a separate whole-arrangement compatibility check for missing/extra repeats. It needs another independently frozen validation pack before any threshold adjustment is judged successful. No additional manual transcription task is required from the founder.
