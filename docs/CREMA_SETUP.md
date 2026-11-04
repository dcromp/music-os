# CREMA candidate: setup and evidence

Status as of 10 October 2026: **runs on this Apple Silicon Mac**. The published
pretrained model completed all 64 generated synthetic cases with no inference
failures. The adapter is for offline candidate screening; this is not a mobile
integration or an algorithm selection decision.

## Reproduce locally

Use Python 3.11 and a separate environment. CREMA expects Keras 2 APIs and should
not share the baseline's NumPy 2 environment. From the repository root:

```sh
python3.11 -m venv .venv-crema
.venv-crema/bin/python -m pip install -r experiments/analysis/candidates/requirements-crema.txt
```

The first TensorFlow import on this Mac took tens of seconds while its native
libraries loaded. Later batch model setup was substantially faster. Do not
multiply this cold start by the number of test clips: use batch mode.

Single file:

```sh
.venv-crema/bin/python experiments/analysis/candidates/crema_adapter.py \
  --audio experiments/generated/audio.wav \
  --output experiments/results/crema-fixture.json \
  --recording-id synthetic-triads-v1
```

Generated suite, loading the model once:

```sh
.venv-crema/bin/python experiments/analysis/candidates/crema_adapter.py \
  --batch-manifest experiments/generated/synthetic-suite/manifest.json \
  --output-root experiments/results/crema-synthetic
```

Outputs use the common chart schema under
`cases/{recording-id}/crema.json`. A batch summary records successes, failures,
model setup and overall wall time. Individual failures are logged and other
cases continue. No audio download, training or mobile deployment is performed.

## What was actually run

- Published package: CREMA 0.2.0; published chord model: `a4c7d57.0`.
- Machine: macOS, Apple Silicon (`arm64`); Python 3.11.13; CPU inference with
  one intra-op and one inter-op TensorFlow thread.
- Synthetic suite: 64 cases, all output charts validated against the lab schema.
- Batch model setup: **3.06 seconds**; batch wall time: **20.13 seconds**;
  median per-file feature extraction, inference and decoding: **0.291 seconds**.
- Earlier 22-second setup fixture: 7 predicted chord intervals, **44.04 seconds**
  including cold imports/model setup; **41.67% duration-weighted exact label
  agreement** with its reference. This simple score penalises extensions and
  inversions; it is not a `mir_eval` result or a claim about real-song accuracy.

The fixture exposed concrete errors: several plain minor triads became minor
sevenths, the one-second silent interval was not recognised as `N`, and a chord
change was late. The final inversion was represented as `C/E`. The broader suite
should distinguish chord-root/major-minor correctness from extensions, bass,
silence and timing. Synthetic scores screen controlled failure modes; real
guitar and song recordings are still needed before choosing a production model.

The unpinned dependency installation first failed because current scikit-learn
expects estimator tags that pumpp's old label encoder does not implement.
Pinning scikit-learn 1.3.2 and SciPy 1.11.4 resolved inference. The dependency file
also retains Keras/TensorFlow 2.15, librosa 0.9.2 and NumPy 1.26.4. Upgrading
these independently needs a rerun of the suite.

## Output semantics

The adapter retains CREMA's native feature extraction, pretrained weights,
Viterbi decoding and inversion logic. It does not modify the model or retrain.
`C:maj` becomes `C`, `C:min` becomes `Cm`, seventh and suspended qualities are
retained, and inversions become conventional bass-note labels. Each event also
contains `native_label` for evaluation without lossy display conversion.

`N` means no chord; CREMA's `X` means unknown/out-of-gamut and remains `X`.
Never count `X` as silence. Model confidence is an uncalibrated native score, not
the probability that the chart is correct. Per-file batch runtime excludes the
shared model load, which is reported separately.

## Source, pretrained assets and terms

Reviewed primary sources:

- [Official repository](https://github.com/bmcfee/crema), checked out at
  `051c91697fd16856a0a1019cc06ee1f11fb52c5f`. The current Git tree lacks the
  pretrained asset files; do not assume cloning it provides a runnable model.
- [Official PyPI release](https://pypi.org/project/crema/0.2.0/). Its wheel
  includes `pump.pkl`, `model_spec.pkl`, `model.h5` and the model version file.
  Wheel SHA-256 verified against official PyPI metadata:
  `b2787afd0367463438ca2b9b2944c490308eee1f307e5796078ec540a6281484`.
- [Model documentation](https://github.com/bmcfee/crema/blob/main/docs/models.rst)
  describes the vocabulary and `N`/`X` semantics.
- [Repository licence](https://github.com/bmcfee/crema/blob/main/LICENSE.md)
  and the licence bundled in the PyPI wheel both contain BSD-2-Clause terms.
  The package's metadata reports ISC; that discrepancy is recorded rather than
  silently treated as resolved.

The model assets are bundled with the BSD-licensed distribution and no separate
weights licence was found there. Preserve its copyright notice and licence if
redistributing. This observation does not establish rights in training
recordings, third-party input songs or YouTube audio; those are separate from
the algorithm code and pretrained-package terms.

Only the official wheel was loaded. The package uses Python pickle for its pump
and model specification; these are executable deserialisation formats, so an
arbitrary replacement asset is not interchangeable with the verified release.

The environment and generated predictions remain local/ignored. The adapter,
dependency pins and this document are the reproducible repository artifacts.
