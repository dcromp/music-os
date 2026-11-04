# BTC-ISMIR19 candidate setup

This candidate runs the pretrained **major/minor BTC model on CPU**, independently of the baseline environment and Expo. It emits the project's version `1.0` JSON format. It performs no training, audio downloads, source separation, beat detection or strumming inference.

## Source, checkpoint and terms

- Official source: [jayg996/BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19), pinned to revision `2682317be668032e6e4b269ded36adaa2ad57df0`.
- Checkpoint: the official repository's [test/btc_model.pt](https://github.com/jayg996/BTC-ISMIR19/blob/2682317be668032e6e4b269ded36adaa2ad57df0/test/btc_model.pt), approximately 12 MB. It is bundled in the repository; no third-party checkpoint host is used.
- SHA-256: `71c2c5db17e8c43b8a9a9da5db36ef2d667158c07a214eba16344c154c00bf54`.
- The repository carries an [MIT licence](https://github.com/jayg996/BTC-ISMIR19/blob/2682317be668032e6e4b269ded36adaa2ad57df0/LICENSE). No separate checkpoint-specific licence or model card was found in the inspected source. Record the checkpoint's inclusion under this repository licence as provenance; resolve deployment terms separately before distributing a production model. The code licence does not grant rights to songs or the original training audio.
- The [upstream README](https://github.com/jayg996/BTC-ISMIR19/blob/2682317be668032e6e4b269ded36adaa2ad57df0/README.md) describes training/evaluation datasets and warns that their annotations do not include the copyrighted audio. Synthetic tests do not establish real-song performance or training-data independence for later benchmarks.

The adapter checks the source revision and checkpoint hash before inference. It loads the checkpoint with PyTorch's restricted `weights_only=True` loader, allowing the NumPy scalar/dtype types needed by its stored normalization value. It does not switch to unrestricted pickle loading.

## Isolated installation on Mac

Test environment: macOS arm64, Python 3.12.10. The fully pinned inference dependencies are in [requirements-btc.lock](../experiments/analysis/candidates/requirements-btc.lock). The baseline's NumPy environment remains separate.

From the repository root:

```sh
python3.12 -m venv .venv-btc
.venv-btc/bin/python -m pip install --only-binary=:all: -r experiments/analysis/candidates/requirements-btc.lock
mkdir -p experiments/candidate-assets
git clone https://github.com/jayg996/BTC-ISMIR19.git experiments/candidate-assets/btc-ismir19
git -C experiments/candidate-assets/btc-ismir19 checkout --detach 2682317be668032e6e4b269ded36adaa2ad57df0
```

On the audited Mac, `/Users/davidcrompton/miniforge3/bin/python` can replace `python3.12` for environment creation. `.venv-btc`, upstream assets/checkpoints and the NumPy/Numba compilation cache are local generated assets. They must remain gitignored. Installation downloads Python wheels and the official repository; inference makes no network requests.

Run one recording:

```sh
.venv-btc/bin/python experiments/analysis/candidates/btc_adapter.py --audio experiments/generated/audio.wav --output experiments/results/btc-smoke.json --recording-id synthetic-triads-v1
.venv-analysis/bin/python experiments/analysis/lab.py evaluate experiments/generated/reference.json experiments/results/btc-smoke.json
```

Use `--btc-repo /absolute/path/to/the/pinned/checkout` for an alternate asset location. `--threads` defaults to four CPU threads; record any changes in comparison results. Input and output paths must differ. Analyse and play the same recording. The recording ID must match its reference annotations.

Process a generated suite in one interpreter, reusing the loaded model:

```sh
.venv-btc/bin/python experiments/analysis/candidates/btc_adapter.py --batch-manifest experiments/generated/synthetic-suite/manifest.json --output-root experiments/results/synthetic-btc
```

Case audio paths resolve relative to the manifest. Each successful chart is written to `output-root/cases/{id}/btc.json`, and `btc-batch-summary.json` records successes/failures and total time. Invalid/missing audio is logged per case; remaining cases continue. The process exits nonzero if any case fails. Failed cases receive no invented chart, and prior output is removed before an inference rerun. IDs must be unique safe path components.

## Compatibility and timing choices

The original inference script uses obsolete NumPy/YAML calls, fails to initialize its feature accumulator for files of ten seconds or less, and uses an approximate `10/108` seconds-per-frame clock. This adapter imports the reviewed upstream model rather than running its training/inference script. It supplies a process-local `np.float` compatibility alias and reads configuration with `yaml.safe_load`.

Feature extraction retains the supplied checkpoint's 22,050 Hz input, 144 CQT bins, 24 bins/octave, 2,048-sample hop and ten-second chunks. Features use the checkpoint's mean/std. The adapter follows the upstream 108-frame transformer blocks, excludes padding from output, timestamps each CQT frame from its actual sample hop and chunk origin, and ends the final event at the original audio duration. Major/minor labels use `C`/`Cm` notation, with `N` for no chord. These changes fix input/output plumbing; the learned weights and network are unchanged.

`analysis.runtime_seconds` includes feature extraction and CPU inference; the first call in a process also includes imports/checkpoint loading and may compile/cache NumPy/Numba kernels. Batch charts identify whether the model was reused. Report first and subsequent runs separately; include the full batch/process wall time for costs. CPU is intentional: this adapter has not been validated on CUDA or Apple MPS.

## Evidence boundary

The checkpoint must first run successfully and produce a valid, full-duration timeline. Automated synthetic agreement is a diagnostic for setup, vocabulary and timing. It is not a production selection criterion by itself: the model was trained for recorded music, and generated timbres can differ substantially. Record synthetic failures alongside scores and verify promising candidates on real, permitted, held-out recordings before guitar sessions decide usefulness.

Initial verified run on 10 October 2026: the 22-second setup fixture produced nine predicted events, a valid full-duration chart and **89.9915% exact-label duration agreement** against eight reference events. The first call took **49.28 seconds**, including cold setup/feature-kernel compilation. The template baseline's higher score on this simple fixture does not establish superior real-recording performance.

The suite's first four-second case also ran successfully: three predicted events, **92.3379% exact-label duration agreement**, and **2.214 seconds** in a fresh process after the feature cache was populated. A separate batch check ran a three-second excerpt, deliberately missing audio, then a four-second case: both real inputs yielded valid timelines covering exactly their input durations; the missing input logged a failure and produced no chart, and the next case continued with the cached model. The three-/four-second batch calls took approximately **2.285/0.060 seconds**; these are setup diagnostics on this Mac, not real-song performance estimates.
