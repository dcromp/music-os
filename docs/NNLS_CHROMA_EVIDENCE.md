# NNLS-Chroma acoustic evidence for chart alignment

A separate native host now exports **frame-level pitch-class activations** from the existing reviewed NNLS-Chroma plugin. It does not turn Chordino chord intervals into acoustic evidence and consumes no chord chart, labels, reference boundaries or founder ratings. A 44-frame synthetic extraction and twelve focused checks passed on this Apple Silicon Mac. Selecting it as an alignment backend still requires the same synthetic and real-recording comparisons as the spectral baseline.

## Frozen experiment

The host loads `nnls-chroma:nnls-chroma`, output `chroma`, from the same hash-verified `nnls-chroma.dylib` used by Chordino. The reviewed plugin revision is `4c5f214a75cb354f8d8c933e161377c5b4d83713`; Vamp SDK 2.10 revision is `44c2487763eb248a933e9eff9169cfadee375009`. It uses the upstream preferred 16,384-sample block and 2,048-sample hop, Hann window and Vamp `ShiftData` adapter. The plugin defaults are frozen:

| Parameter | Value |
|---|---:|
| `useNNLS` | 1 |
| `tuningmode` | 0: global tuning |
| `whitening` | 1 |
| `s`: spectral shape | 0.7 |
| `chromanormalize` | 0: native raw activations |
| `rollon` | 0 |

This is offline analysis: the plugin computes tuning and NNLS activations during `getRemainingFeatures()`. Parameters were chosen from upstream defaults before real-song review; no Creep-specific parameter tuning occurred. The host emits only the chroma output; it never runs Chordino's chord dictionary/HMM output.

The native bins are `A Bb B C C# D Eb E F F# G Ab`. The Python adapter reorders them to `C C# D Eb E F F# G Ab A Bb B`, then normalizes each nonzero vector to L2 length 1 for cosine emissions. It also retains each pre-normalization norm. Chroma values and cosine scores are not calibrated probabilities.

## Build and run

First create the reviewed native assets using [CHORDINO_SETUP.md](CHORDINO_SETUP.md), including its pinned sources and verified Boost archive. Then compile the separate host:

```sh
.venv-analysis/bin/python experiments/analysis/candidates/build_nnls_chroma_host.py
```

This reuses the existing plugin and SDK static library. It verifies the plugin hash and reviewed SDK checkout, records the linked static-library hash, and writes only `experiments/candidate-assets/nnls-chroma-evidence-native/nnls-chroma-host` plus its `buildinfo.json`. It does not rebuild or change the existing plugin, Chordino host or their provenance manifest. The build recipe targets arm64 macOS 11+ and requires the Apple command-line C++ compiler. No global plugin install or extra Python packages are needed beyond `.venv-analysis`.

Extract a new evidence file from a prepared PCM16 mono WAV:

```sh
.venv-analysis/bin/python experiments/analysis/candidates/nnls_chroma_adapter.py \
  --audio experiments/generated/synthetic-suite/cases/l1-harmonic-004/audio.wav \
  --recording-id l1-harmonic-004 \
  --output experiments/generated/l1-harmonic-004-nnls-evidence.json
```

The adapter refuses an existing output file and any attempt to overwrite source audio. It validates the PCM input, limits recordings to 600 seconds and native processing to 180 seconds, forces project-local `VAMP_PATH`, and checks source/binary provenance, frame count, sample rate, parameters and every feature timestamp. For another format, use the existing `lab.py prepare` command first.

Python integration:

```python
from candidates import nnls_chroma_adapter

evidence = nnls_chroma_adapter.extract(audio_path, recording_id)
nnls_chroma_adapter.validate_evidence(evidence, audio_path)
```

Use the same validation for cached JSON before alignment. Pairing checks the exact prepared-WAV SHA256, sample count and sample rate. Saved evidence can be validated and used without invoking the native model; new extraction requires the compiled assets.

## Exact frame coordinates and JSON schema

Schema identifier: `pitch-class-evidence-1.0`.

- `recording`: ID, title, `audio_sha256`, `sample_rate_hz`, `sample_count`, `duration_seconds`.
- `pitch_classes`: the fixed C-first bin labels.
- `times_seconds`: exact native frame centers, from sample `i * 2048`, converted to seconds by Vamp and printed to nine decimal places.
- `chroma_c_first`: one finite, nonnegative 12-bin L2-normalized vector per center; zero vectors remain zero.
- `raw_chroma_l2`: norm of the native raw activation vector before normalization.
- `rms`: original PCM RMS over the same centered 16,384-sample support, dividing by the full window size with zero padding at the edges.
- `silent`: one independent RMS decision per frame. Its threshold is `max(1e-5, peak_absolute_sample * 0.025)`.
- `analysis`: extraction runtime, exact native settings, source and binary hashes, normalization and RMS details, offline/global-tuning flags, and explicit absence of chart/reference input.

Vamp's pinned `PluginInputDomainAdapter::processShiftingData()` shifts the audio buffer by half a window while leaving the timestamp unchanged; `getTimestampAdjustment()` returns zero for `ShiftData`. NNLS-Chroma copies the corresponding log-spectrum feature timestamp into every chroma feature. The host checks that zero adjustment, and the adapter verifies centers against the entire expected native sample grid. Initial and final FFT regions use zero padding. There is no half-window offset to subtract after extraction.

These coordinates describe where an acoustic window was centered. They are **not measured physical chord-onset times**. At 22,050 Hz the hop is 92.88 ms and the window support is 743.04 ms. A finer interpolation grid can make downstream processing consistent with the baseline, but cannot add temporal information absent from this wider native window. Document any interpolation method and keep independent PCM silence evidence separate from normalized chroma.

Primary implementation sources: [NNLS-Chroma output and bin order](https://github.com/c4dm/nnls-chroma/blob/4c5f214a75cb354f8d8c933e161377c5b4d83713/NNLSChroma.cpp), [NNLS-Chroma defaults](https://github.com/c4dm/nnls-chroma/blob/4c5f214a75cb354f8d8c933e161377c5b4d83713/NNLSBase.cpp), and [Vamp input-domain timestamp handling](https://github.com/vamp-plugins/vamp-plugin-sdk/blob/44c2487763eb248a933e9eff9169cfadee375009/src/vamp-hostsdk/PluginInputDomainAdapter.cpp). These exact sources were inspected in the local pinned checkouts.

## Verification and license provenance

```sh
.venv-analysis/bin/python -W error -m unittest discover \
  -s experiments/analysis/tests -p test_nnls_chroma.py -v
```

All twelve checks passed here, including a native two-second C-triad recording with silence, exact center timestamps, pitch-class order, unchanged audio-hash pairing, independent RMS silence, malformed activations/packets, frozen parameter/configuration rejection, cached evidence integrity and exclusive output publication that protects input aliases. The native integration check skips when the separate host has not been built; eleven adapter checks still run.

NNLS-Chroma declares GPL-2.0-or-later. The SDK has its recorded MIT-style permission notice with name-promotion restriction and embedded KissFFT BSD terms. This experiment records those terms alongside existing [Chordino provenance](CHORDINO_SETUP.md); a product distribution choice remains separate from local evaluation.
