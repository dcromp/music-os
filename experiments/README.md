# Mac analysis experiments

Phase 0 establishes a reproducible analysis environment and a local guitar test bench. Phase A will compare recognition models and real recordings. These tools run independently of the older Expo app.

## Setup

Python 3.12 was used on the founder's Mac. With an existing Python 3.12 installation:

```sh
python3.12 -m venv .venv-analysis
.venv-analysis/bin/python -m pip install -r experiments/analysis/requirements.txt
.venv-analysis/bin/python experiments/analysis/lab.py smoke
.venv-analysis/bin/python -m unittest discover -s experiments/analysis/tests -v
node experiments/bench/test.js
.venv-analysis/bin/python experiments/analysis/lab.py serve
```

On the audited Mac, Python is also available at `/Users/davidcrompton/miniforge3/bin/python` (3.12.10). Substitute that executable for `python3.12` when creating the environment. The system/Homebrew `python3` was 3.14.3 and was not used for this experiment. NumPy is pinned; no system packages are changed. FFmpeg is optional for the fixture, required for normalising other local audio formats.

Open [the local bench](http://127.0.0.1:8067/) and load the synthetic demo. The server binds to localhost, exposes the bench assets and three demo files, and stops with Ctrl+C. It serves no repository secrets or general file listings. Generated audio/results and the environment are gitignored. This is a local development deployment; there is no public hosted service or iOS build.

Node is required only for the dependency-free browser-logic checks, not for serving the bench. Use Download CSV or the visible Show CSV copy fallback to retain ratings; closing/reloading the tab clears unsaved rows.

## Commands

Generate a known 22-second triad fixture and reference chart:

```sh
.venv-analysis/bin/python experiments/analysis/lab.py fixture
```

Create the fixture, run the template detector and save comparison metrics:

```sh
.venv-analysis/bin/python experiments/analysis/lab.py smoke
```

Prepare a local recording and analyse it:

```sh
.venv-analysis/bin/python experiments/analysis/lab.py prepare /absolute/path/input.mp3 experiments/local-audio/song.wav
.venv-analysis/bin/python experiments/analysis/lab.py analyze experiments/local-audio/song.wav --recording-id my-recording-v1 --output experiments/results/song-baseline.json
```

Prepare creates a new mono 22,050 Hz, 16-bit PCM WAV and refuses to overwrite existing audio. Analysis accepts 16-bit PCM WAV (mono or stereo). Use the prepared WAV for both analysis and browser playback so decoder offsets or different edits do not confound timing. Select the local WAV and its chart in the bench. There is no upload to a remote service and no automatic YouTube extraction.

Compare against a manually labelled chart identifying the same recording:

```sh
.venv-analysis/bin/python experiments/analysis/lab.py evaluate reference.json experiments/results/song-baseline.json --output experiments/results/song-metrics.json
```

## Interchange format v1.0

```json
{
  "schema_version": "1.0",
  "recording": {
    "id": "my-recording-v1",
    "title": "My recording",
    "duration_seconds": 8.0,
    "sample_rate_hz": 22050
  },
  "analysis": {
    "id": "baseline-v1",
    "algorithm": "spectral-template",
    "version": "0.1.0",
    "runtime_seconds": 0.1,
    "parameters": {}
  },
  "chords": [
    {"start_seconds": 0.0, "end_seconds": 4.0, "label": "C"},
    {"start_seconds": 4.0, "end_seconds": 8.0, "label": "Am"}
  ],
  "beats_seconds": [0.0, 0.5, 1.0],
  "downbeats_seconds": [0.0]
}
```

All timestamps are seconds, not milliseconds. Chord intervals are ordered and nonoverlapping; starts are inclusive and ends exclusive. Gaps are allowed and show no supplied chord. `N` means no chord; the baseline supports 12 major and 12 minor labels. Beats/downbeats are optional: the baseline does not detect them. The fixture's beat grid is generated reference data, not algorithm output. Keep labels, recording identity and version explicit when adding detector adapters.

The baseline uses spectral chroma and major/minor templates, with no source separation or smoothing. It is deliberately a cheap reference point. It does not infer guitar fingering, strum direction, capo, chord extensions or song structure. Its relative silence threshold and harmonic interference need evaluation on real recordings.

## What the smoke result means

The generated fixture has seven pitched chord events (including an inversion) and one silent interval. Metrics report exact matching duration over annotated duration, reference coverage, event counts and runtime. This custom plumbing metric is not a replacement for mir_eval's task-specific comparisons.

A high result on this fixture confirms the basic input/output/timing path. It does not establish performance on actual guitar, dense mixes or unseen songs, and does not select a production algorithm. Founder guitar ratings and held-out real excerpts are still required.

## Automated progressive synthetic screening

The suite generator creates 64 deterministic cases across roots/voicings/registers, guitar-like plucks and staggered attacks, controlled bass/percussion/noise, and faster/offbeat changes. It uses procedural tones/envelopes, not recordings of actual guitars. Recipes, hashes and paired screen/holdout variants are saved in its manifest. Results are reported per condition and candidate.

```sh
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py generate
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini
```

Install model environments/assets using the candidate setup documents before requesting their runs. `--reuse-existing` rescoring requires matching audio hashes and produces no new inference. Failed/unavailable candidates remain visible and make the runner exit nonzero; logs, JSON and CSV stay in the generated suite directory. The initial four-candidate batch completed 256 comparisons with zero failures. See [recorded results](../docs/SYNTHETIC_RESULTS.md).

The server's `/api/suite` inventory exposes only safe case IDs and allowlisted audio/chart files. Use Load synthetic suite → choose case → Load case in the bench. No model inference happens in the browser. Generated cases can be played without guitar first; founder guitar sessions follow the automated screening.

Use synthetic failures to diagnose integration/timing/vocabulary problems early. Confirm adapters and input conventions before dropping a candidate: artificial tones can be outside the training domain of a real-recording model. Power chords require ambiguous-quality or root-only evaluation. Real recordings and guitar play-tests remain the selection evidence.
