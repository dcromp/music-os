# ChordMini / ChordNet 2E1D candidate

Runs on the Mac in an isolated Python 3.12 environment. This is an additional pretrained chord model, distinct from original BTC and CREMA. No training, guitar session or production selection has occurred.

## Provenance

- Official source: [ptnghia-j/ChordMini](https://github.com/ptnghia-j/ChordMini), revision `aa6e3a8d7b017f082fd2aaff9329d5c26af49c03`.
- Bundled checkpoint: `checkpoints/2e1d_model_best.pth`, SHA-256 `ecc3de5e7b5b4affdd8e903106e11c24440631e5f43cf22d2a5975b3f160229a`.
- Source carries MIT terms; the README distinguishes source licensing from dataset rights. No separate checkpoint model card/terms were resolved in this experiment. Record this before any production redistribution.
- The adapter uses the checkpoint's actual 170-class mapping, including X (unknown) and N (no chord), and its stored normalization. It uses the official architecture-inference helper and strict weight loading; the checkpoint does not store explicit head-count configuration, so that helper's inference is a documented limitation.

Unlike the upstream loader, the adapter uses restricted `torch.load(weights_only=True)` and verifies the checkpoint hash. It retains the official feature extraction and model code. Frame times use the CQT hop in seconds; padding is excluded and the final interval ends at recording duration. Kernel size 1 avoids the upstream helper's implicit ChordNet temporal smoothing. Overlap is disabled for this first raw-output comparison.

## Setup

```sh
python3.12 -m venv .venv-chordmini
.venv-chordmini/bin/python -m pip install -r experiments/analysis/candidates/requirements-chordmini.lock
git clone https://github.com/ptnghia-j/ChordMini.git experiments/candidate-assets/chordmini
git -C experiments/candidate-assets/chordmini checkout --detach aa6e3a8d7b017f082fd2aaff9329d5c26af49c03
```

The tested environment uses PyTorch 2.6, NumPy 1.26.4 and librosa 0.10.2.post1. This differs from the current upstream requirements; the committed lock records the environment actually used. Matplotlib/seaborn are required by upstream package imports even though this adapter does not plot. Model/cache assets and the environment are ignored.

```sh
.venv-chordmini/bin/python experiments/analysis/candidates/chordmini_adapter.py --batch-manifest experiments/generated/synthetic-suite/manifest.json --output-root experiments/generated/synthetic-suite
```

Single-file mode accepts `--audio`, `--output` and `--recording-id`. Batch mode reuses the model, logs failures, and returns nonzero if any fail. Do not count a missing prediction as success. CPU inference uses four threads; the batch summary reports model setup separately from processing time.

The initial 64 cases produced 64 valid charts. Synthetic screening places this model ahead on major/minor core and boundary metrics in the current suite, but all timbres are procedural and short. Real recordings remain essential evidence before choosing a production pipeline.
