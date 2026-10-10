# Chordino / NNLS-Chroma on Mac

**Built and screened: 64/64 synthetic cases completed successfully on Apple Silicon.** No system packages or global Vamp folders were installed. This adds a practical classical NNLS/HMM approach to the template baseline and neural candidates; it does not select a production engine.

## Provenance

| Component | Reviewed version | Role |
|---|---|---|
| [c4dm/nnls-chroma](https://github.com/c4dm/nnls-chroma) | `4c5f214a75cb354f8d8c933e161377c5b4d83713`; Vamp plugin version 5 | Chordino NNLS features, built-in dictionary and HMM/Viterbi decoding |
| [Vamp SDK](https://github.com/vamp-plugins/vamp-plugin-sdk) | `44c2487763eb248a933e9eff9169cfadee375009`; SDK 2.10 | Plugin interface, loading and time-to-frequency input adapter |
| [Boost source](https://archives.boost.io/release/1.87.0/source/boost_1_87_0.tar.gz) | 1.87.0; SHA256 `f55c340aa49763b1925ccf02b2e83f35fdcf634c9d5164a2acb87540173c741d` | Header-only plugin dependency |
| Project native host | `experiments/analysis/candidates/chordino-host.cpp` | Bounded WAV-only host; no libsndfile, Python binding or Sonic Annotator dependency |

Chordino source declares GPL-2.0-or-later. The SDK's actual `COPYING` contains an MIT-style permission notice plus a name-promotion restriction; embedded KissFFT has BSD-3-Clause terms. Boost uses BSL-1.0. Record these separately from a future product distribution decision. Chordino's README describes optional heuristic decoding, but this pinned source exposes no `useHMM` parameter and always uses HMM/Viterbi.

## Build from a fresh checkout

Requirements: Apple Silicon macOS, Apple command-line compiler tools, CMake, make, git and the Phase 0 Python environment. Fetch the official sources into the ignored project-local assets directory:

```sh
mkdir -p experiments/candidate-assets
git clone https://github.com/c4dm/nnls-chroma.git experiments/candidate-assets/nnls-chroma
git -C experiments/candidate-assets/nnls-chroma checkout --detach 4c5f214a75cb354f8d8c933e161377c5b4d83713
git clone https://github.com/vamp-plugins/vamp-plugin-sdk.git experiments/candidate-assets/vamp-plugin-sdk
git -C experiments/candidate-assets/vamp-plugin-sdk checkout --detach 44c2487763eb248a933e9eff9169cfadee375009
curl --fail --location https://archives.boost.io/release/1.87.0/source/boost_1_87_0.tar.gz --output experiments/candidate-assets/boost_1_87_0.tar.gz
shasum -a 256 experiments/candidate-assets/boost_1_87_0.tar.gz
```

Confirm the Boost checksum above, then build:

```sh
.venv-analysis/bin/python experiments/analysis/candidates/build_chordino.py
```

The build script also verifies the archive checksum, pinned revisions and unmodified tracked upstream sources. It extracts required Boost headers into a fresh temporary project-local directory for every build, so an existing modified header tree cannot receive verified provenance. It compiles arm64 for macOS 11+, changes upstream's old x86_64 build flags, uses `-O3` without `-ffast-math`, and records compiler, source and binary hashes in `experiments/candidate-assets/chordino-native/buildinfo.json`. It was run successfully on this Mac. No `cmake --install`, Homebrew installation or global plugin registration occurs.

## Run

```sh
.venv-analysis/bin/python experiments/analysis/candidates/chordino_adapter.py --audio experiments/generated/audio.wav --recording-id synthetic-triads-v1 --output experiments/generated/chordino.json
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini,chordino
```

The first command assumes the smoke fixture already exists; use the recording ID from its reference when evaluating it. The suite loads the adapter automatically and records per-case failures/runtime. Other candidates need their own isolated environments. Saved charts can be viewed without installing native assets, but rerunning Chordino requires this build.

## Output and timing decisions

The host accepts RIFF PCM16 **mono** WAV, 8–192 kHz, with a 512 MiB file limit. Use `lab.py prepare` for other input formats. It sets no guessed chord timings: plugin defaults use Hann windows, 16,384-sample blocks and 2,048-sample hops. Vamp `ShiftData` centers the spectrum on the supplied sample timestamp; the host uses overlapping preferred-size blocks and pads the start/tail. At 22,050 Hz, the window is about 743 ms and the hop about 93 ms, which helps explain broad boundary uncertainty on short cases.

Stdout contains a `# {JSON}` metadata header followed by timestamp/label TSV. The plugin emits a final `N` feature at its last processed timestamp as a **termination marker**, even if audio still sounds. The adapter removes exactly this last marker, preserves earlier genuine `N`, merges duplicate events, clips to recording bounds and extends the final active event to source duration. Any uncovered initial range becomes unknown `X`, not an invented chord. Native quality and bass labels are preserved; e.g. `Bbm` and `Ab` are enharmonic equivalents of `A#m` and `G#` in the suite.

The adapter forces `VAMP_PATH` to the project-native directory, refuses an external `chord.dict`, verifies binary hashes against build provenance, validates frame count/sample rate and common-schema output, and refuses to overwrite source audio. Runtime includes a native process/plugin load per recording. Four focused tests cover sentinel handling, genuine silence, duplicate events, uncovered input and malformed timestamps.

The strumming smoke case recognised the progression but placed the first chord early and missed ending silence. Clean C major can be labelled Cmaj7. These are measured quality/timing issues, not setup failures. Use separate chord-only, root, richer-quality and silence/timing metrics; see [synthetic results](SYNTHETIC_RESULTS.md).
