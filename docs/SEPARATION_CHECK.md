# Retrospective ensemble source-separation check

Started 12 October; status updated 13 October 2026. Local research only; all outputs remain unaccepted for playback. The experiment tests whether removing estimated interference improves the existing BTC chord detector on three already exposed JazzSAMBA excerpts. It does not test guitar isolation, rock repertoire, perceptual stem quality or a new holdout.

The three 60-second mono 22,050 Hz WAVs are the exact inputs from the [paired ensemble comparison](JAZZSAMBA_REFERENCE_CHECK.md): Blue Bossa, Amazing Grace and When the Saints Go Marching In. The catalogue names piano, bass, drums and horn leads, with no guitar or vocals. Written chart grids are the scoring targets; they are not individually marked performed chord notes or physical attacks. Original development/holdout labels remain provenance, with no fresh holdout claim here.

Before separation or derivative detector inference, the protocol fixed the three conditions, one model and one detector:

| Condition | Signal supplied to unchanged BTC |
|---|---|
| Original | Three byte-identical cached original-mix predictions |
| Minus drums | Resampled original stereo minus estimated drums |
| Minus drums and vocals | Resampled original stereo minus estimated drums minus estimated vocals |

BTC was selected retrospectively because it led the already observed ensemble benchmark. Six new BTC runs retain its native major/minor vocabulary, decoder, CQT timing, ten-second chunks, no smoothing and four CPU threads, matching the three historical controls. The separator runs on one CPU thread, float32, shifts zero, split enabled, 25% overlap, zero worker jobs and the checkpoint's native 7.8-second segment. No chart, key, tempo, label or annotated timestamp enters separation or detector inference. There is no gain/threshold/model/condition selection after outputs.

**Source and model pins.** The isolated environment uses Demucs 4.1.0 from PyPI; eight inference modules were verified byte-identical to the [author's release commit](https://github.com/adefossez/demucs/tree/6a604bb002d12c4fbabb303ba64db40b5c5743f0). The package's [newer inference dependencies](https://github.com/adefossez/demucs/blob/v4.1.0/pyproject.toml) avoid the archived version's Torchaudio/Dora/OpenUnmix requirements. [requirements-demucs.txt](../experiments/analysis/requirements-demucs.txt) records every installed version, including Torch 2.6.0, NumPy 1.26.4 and Julius 0.2.8. Package inventories, installed separator modules, candidate code/checkpoint, original audio/reference/control bytes and this runner's source are frozen before inference.

The official `adefossez/HTDemucs` model revision is `cbc8a9b1a87023b7fd74e7b3412e6321c0eab003`; [955717e8.safetensors](https://huggingface.co/adefossez/HTDemucs/blob/cbc8a9b1a87023b7fd74e7b3412e6321c0eab003/955717e8.safetensors) is exactly 84,025,440 bytes, SHA256 `d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd`. The runner loads that verified local safetensors directly, avoiding a mutable model lookup or legacy fallback. Standard HTDemucs emits drums/bass/other/vocals. Guitar is available only in the distinct experimental six-source model, which is not used here.

Code is MIT. The official weight model card [removed its MIT declaration](https://huggingface.co/adefossez/HTDemucs/commit/cbc8a9b1a87023b7fd74e7b3412e6321c0eab003), so commercial weight terms remain unresolved. Dataset reuse terms also remain unresolved. Neither model weights nor source music/charts are included in the Git change; no public product use is established by this research run.

**Preparation and pairing.** The existing mono source is duplicated into two channels and resampled to 44,100 Hz with Julius. Normalization and each stem's inverse transform match the official API: subtract the channel-mean signal's scalar mean, divide by its unbiased standard deviation plus `1e-8`, then restore each output using the same standard deviation and mean. Residuals use the resampled original, rather than a sum of estimated accompaniment stems. These formulas differ when the model is not mixture-consistent.

Native stereo stems and residuals are preserved as IEEE float32 WAVs without clipping, limiting, independent stem gain changes or lossy encoding. Residuals are averaged across stereo channels and resampled to 22,050 Hz. Every detector input must retain exactly 1,323,000 frames and 60 seconds; the runner rejects changes rather than trimming, padding, moving timestamps or scaling endpoints. The unchanged cached control does not make that resampling round trip, so the comparison includes the fixed preparation change alongside separation. Its numerical effect is reported separately and is not silently attributed to the separator.

Reference bytes and source fields remain immutable. A derivative prediction keeps its own audio hash; scoring checks the original reference's exact identity and the derivative's declared source hash, frames, duration, sample rate, condition and protocol/input-declaration hashes before using the unchanged pilot scorer. The gold recording hash is never rebound to a processed input. Supported richer Harte targets and the declared source-triad projection are scored separately, with the same eligibility conventions as the original ensemble report.

The objective signal diagnostics report RMS, peak, DC, fraction of samples outside ±1, first-difference RMS and all-stem reconstruction error. These measure signal changes; there are no isolated-stem references establishing SDR, perceptual quality or how much useful harmony was removed. Cached control times and current inference times are not normalized hosting estimates. The two residual conditions share one separation per recording, so their separation costs must not be added together.

## Results

All three separation runs completed successfully in 127.329 seconds total, with a reported process peak RSS of 2.038 GB. The nine new BTC runs (six residuals and three resampling-only controls) have not started, so there is no chord-agreement or separator-benefit result. The separate resampling-only source and checks are saved; its declaration must be frozen before derivative BTC inference. [SEPARATION_CHECK.json](SEPARATION_CHECK.json) records this partial status and the exact completed attempt hash. Work resumes from the durable Documents checkout after the workspace move. No player charts, rhythm grids or frozen detector/aligner policies change.

## Reproduction

The ignored local pack is `experiments/generated/separation-check-v1`; assets are `experiments/candidate-assets/demucs-4.1.0`. Create an isolated Python 3.12 environment and install the exact requirements. Acquire the pinned official model/source assets above and verify hashes; the runner performs no downloads. Fresh inference requires the existing BTC runtime/assets, and cached scoring requires pinned `mir_eval 0.8.2` in `.venv-pilot`.

```bash
.venv-demucs/bin/python experiments/analysis/separation_check.py prepare
.venv-demucs/bin/python experiments/analysis/separation_check.py separate --protocol-sha256 PROTOCOL_SHA
.venv-btc/bin/python experiments/analysis/separation_check.py infer --protocol-sha256 PROTOCOL_SHA
.venv-pilot/bin/python experiments/analysis/separation_check.py score --protocol-sha256 PROTOCOL_SHA --output experiments/generated/separation-check-v1/new-report.json
```

Use the exact hash printed by `prepare`; choose a fresh `--pack` for another inference run. Existing attempts and native files are never replaced. Per-input failures stay in saved attempt packets and requested score rows. Eleven focused tests cover original-minus-stem arithmetic, dimensions/finite samples, unsupported stems, unclipped amplitude, source/derivative lineage, immutable gold, rejected protocol/condition changes, path confinement and failure coverage.
