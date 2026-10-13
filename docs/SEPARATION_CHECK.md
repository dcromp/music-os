# Retrospective ensemble source-separation check

Started 12 October; completed 13 October 2026. Local research only; all outputs remain unaccepted for playback. The experiment tests whether removing estimated interference improves the existing BTC chord detector on three already exposed JazzSAMBA excerpts. It does not test guitar isolation, rock repertoire, perceptual stem quality or a new holdout.

The three 60-second mono 22,050 Hz WAVs are the exact inputs from the [paired ensemble comparison](JAZZSAMBA_REFERENCE_CHECK.md): Blue Bossa, Amazing Grace and When the Saints Go Marching In. The catalogue names piano, bass, drums and horn leads, with no guitar or vocals. Written chart grids are the scoring targets; they are not individually marked performed chord notes or physical attacks. Original development/holdout labels remain provenance, with no fresh holdout claim here.

Before separation or derivative detector inference, the protocol fixed the three conditions, one model and one detector:

| Condition | Signal supplied to unchanged BTC |
|---|---|
| Original | Three byte-identical cached original-mix predictions |
| Minus drums | Resampled original stereo minus estimated drums |
| Minus drums and vocals | Resampled original stereo minus estimated drums minus estimated vocals |

BTC was selected retrospectively because it led the already observed ensemble benchmark. Six residual and three resampling-only BTC runs retain its native major/minor vocabulary, decoder, CQT timing, ten-second chunks, no smoothing and four CPU threads, matching the three historical controls. The separator runs on one CPU thread, float32, shifts zero, split enabled, 25% overlap, zero worker jobs and the checkpoint's native 7.8-second segment. No chart, key, tempo, label or annotated timestamp enters separation or detector inference. There is no gain/threshold/model/condition selection after outputs.

**Source and model pins.** The isolated environment uses Demucs 4.1.0 from PyPI; eight inference modules were verified byte-identical to the [author's release commit](https://github.com/adefossez/demucs/tree/6a604bb002d12c4fbabb303ba64db40b5c5743f0). The package's [newer inference dependencies](https://github.com/adefossez/demucs/blob/v4.1.0/pyproject.toml) avoid the archived version's Torchaudio/Dora/OpenUnmix requirements. [requirements-demucs.txt](../experiments/analysis/requirements-demucs.txt) records every installed version, including Torch 2.6.0, NumPy 1.26.4 and Julius 0.2.8. Package inventories, installed separator modules, candidate code/checkpoint, original audio/reference/control bytes and this runner's source are frozen before inference.

The official `adefossez/HTDemucs` model revision is `cbc8a9b1a87023b7fd74e7b3412e6321c0eab003`; [955717e8.safetensors](https://huggingface.co/adefossez/HTDemucs/blob/cbc8a9b1a87023b7fd74e7b3412e6321c0eab003/955717e8.safetensors) is exactly 84,025,440 bytes, SHA256 `d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd`. The runner loads that verified local safetensors directly, avoiding a mutable model lookup or legacy fallback. Standard HTDemucs emits drums/bass/other/vocals. Guitar is available only in the distinct experimental six-source model, which is not used here.

Code is MIT. The official weight model card [removed its MIT declaration](https://huggingface.co/adefossez/HTDemucs/commit/cbc8a9b1a87023b7fd74e7b3412e6321c0eab003), so commercial weight terms remain unresolved. Dataset reuse terms also remain unresolved. Neither model weights nor source music/charts are included in the Git change; no public product use is established by this research run.

**Preparation and pairing.** The existing mono source is duplicated into two channels and resampled to 44,100 Hz with Julius. Normalization and each stem's inverse transform match the official API: subtract the channel-mean signal's scalar mean, divide by its unbiased standard deviation plus `1e-8`, then restore each output using the same standard deviation and mean. Residuals use the resampled original, rather than a sum of estimated accompaniment stems. These formulas differ when the model is not mixture-consistent.

Native stereo stems and residuals are preserved as IEEE float32 WAVs without clipping, limiting, independent stem gain changes or lossy encoding. Residuals are averaged across stereo channels and resampled to 22,050 Hz. Every detector input must retain exactly 1,323,000 frames and 60 seconds; the runner rejects changes rather than trimming, padding, moving timestamps or scaling endpoints. The unchanged cached control does not make that resampling round trip. A separately frozen round-trip-only condition applies the identical preparation without separation to all three originals. It was declared at 2026-10-13 07:52:44 UTC before any new BTC output; its hash is `a6ea0b658cadd0bfa8e8d49e4a6b4ea838089e0a57da89be292329c697bd1bc5`. Its relative waveform RMS differences are 0.861%, 0.504% and 0.546%; all three resulting chord-event arrays exactly match the untouched original controls.

Reference bytes and source fields remain immutable. A derivative prediction keeps its own audio hash; scoring checks the original reference's exact identity and the derivative's declared source hash, frames, duration, sample rate, condition and protocol/input-declaration hashes before using the unchanged pilot scorer. The gold recording hash is never rebound to a processed input. Supported richer Harte targets and the declared source-triad projection are scored separately, with the same eligibility conventions as the original ensemble report.

The objective signal diagnostics report RMS, peak, DC, fraction of samples outside ±1, first-difference RMS and all-stem reconstruction error. These measure signal changes; there are no isolated-stem references establishing SDR, perceptual quality or how much useful harmony was removed. Cached control times and current inference times are not normalized hosting estimates. The two residual conditions share one separation per recording, so their separation costs must not be added together.

## Results

All three separation runs and all nine new BTC runs succeed. Twenty-four scoring comparisons cover four conditions against two unchanged reference conventions. [Exact metrics, input/output/model hashes and signal diagnostics](SEPARATION_CHECK.json) preserve the complete result. An independent audit reproduces every eligible-duration score within `1e-14` and reconstructs each residual/control WAV sample-for-sample.

| Input condition | Supported major/minor agreement | Declared source-triad agreement |
|---|---:|---:|
| Untouched original, cached BTC | 69.2% | 65.9% |
| Resampling only | 69.2% | 65.9% |
| Original minus drums | 69.7% | 66.3% |
| Original minus drums and vocals | 69.7% | 66.3% |

Supported reference eligibility is 150.881/180 seconds (83.8%); the separately declared triad target covers 167.397 seconds (93.0%). Unknown predictions earn no agreement credit. Changing the target changes the denominator; it is not a detector improvement. Neither reference describes every performed note or physical harmonic attack.

The aggregate supported gain is only **0.493 percentage points**. Blue Bossa improves 45.10→49.92%, while Amazing Grace worsens 79.92→78.06% and Saints worsens 76.34→75.92%. The drums-plus-vocals condition produces exactly the same chord events as drums-only on each instrumental input, so it adds no chord-recognition benefit here. There are no guitar or vocal parts establishing general instrument-isolation quality.

Separation totals 127.329 seconds for 180 seconds of audio, including model load and publication; its reported process peak RSS is 2.038 GB. Native per-input extraction totals 126.755 seconds and the two residual conditions share that work. The six residual BTC calls total 32.531 seconds, dominated by the first 30.745-second cold startup/JIT call. Three resampling controls total 5.732 seconds. These different cache/startup states are not a controlled speed comparison or cloud-cost estimate. No clipping occurs; native residual peaks remain below one and all-stem reconstruction RMS differences are 1.865–2.641% of original signal RMS.

**Decision:** keep original-mix analysis as the default. The small, uneven gain does not justify adding separation to every song. Retain it for a separately selected interference problem or future permitted guitar-part experiment. Current model settings, reference bytes, player charts and acceptance flags remain unchanged. No new outputs are accepted for playback.

## Reproduction

The ignored local pack is `experiments/generated/separation-check-v1`; assets are `experiments/candidate-assets/demucs-4.1.0`. Create an isolated Python 3.12 environment and install the exact requirements. Acquire the pinned official model/source assets above and verify hashes; the runner performs no downloads. Fresh inference requires the existing BTC runtime/assets, and cached scoring requires pinned `mir_eval 0.8.2` in `.venv-pilot`.

```bash
.venv-demucs/bin/python experiments/analysis/separation_check.py prepare
.venv-demucs/bin/python experiments/analysis/separation_check.py separate --protocol-sha256 PROTOCOL_SHA
.venv-btc/bin/python experiments/analysis/separation_check.py infer --protocol-sha256 PROTOCOL_SHA
.venv-pilot/bin/python experiments/analysis/separation_check.py score --protocol-sha256 PROTOCOL_SHA --output experiments/generated/separation-check-v1/new-report.json
```

Use the exact hash printed by `prepare`; choose a fresh `--pack` for another inference run. Existing attempts and native files are never replaced. Per-input failures stay in saved attempt packets and requested score rows. Eleven separation checks and four resampling-control checks pass. The separation checks cover original-minus-stem arithmetic, dimensions/finite samples, unsupported stems, unclipped amplitude, source/derivative lineage, immutable gold, rejected protocol/condition changes, path confinement and failure coverage.


The separate control runner is `experiments/analysis/resampling_control.py`. Its `prepare` command must run before any derivative BTC output; it refuses a retroactive declaration. Use its printed `--extension-sha256` for `infer`, then `score` with the original three-condition `--base-report` and a new `--output`. Both source files and declarations are hashed. A timestamp metadata correction was made before the first control declaration; original separation code/policy stayed frozen.
