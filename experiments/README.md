# Mac analysis experiments

Phase 0 establishes a reproducible analysis environment and a local guitar test bench. Phase A compares recognition models, chart alignment and real recordings. These tools run independently of the older Expo app.

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

Open [the local bench](http://127.0.0.1:8067/) and load the synthetic demo. The server binds to localhost, exposes bench assets and allowlisted demo/synthetic files, and stops with Ctrl+C. It serves no repository secrets or general file listings. Generated audio/results and the environment are gitignored. This is a local development deployment; there is no public hosted service or iOS build.

Node is needed for the dependency-free browser checks and the separate YouTube importer, but not for serving the bench. Use Download CSV or the visible Show CSV copy fallback to retain ratings; closing/reloading the tab clears unsaved rows.

## Commands

The beginner view and whole-sequence continuation use saved outputs, with no
model inference or founder transcription:

```sh
.venv-analysis/bin/python experiments/analysis/core_chord_screen.py --output experiments/generated/core-chord-screen-new
.venv-analysis/bin/python experiments/analysis/arrangement_screen.py --output experiments/generated/arrangement-screen-new
node experiments/review/test.js
```

[Core scoring](../docs/CORE_CHORD_SCREEN.md) distinguishes exact from reduced
quality. [Structure diagnostics](../docs/ARRANGEMENT_SCREEN.md) retain raw/stable
unrestricted sequences and expose wrong-chart rankings; they do not approve
arrangements. Both commands need cached inputs named in their help/guides and
a fresh output directory. The player exposes Core chords as an optional display
after capo conversion, retaining raw outputs and issue timestamps.

The [rich-quality screen](../docs/RICH_QUALITY_SCREEN.md) generates and runs
24 richer/plain/contrast cases automatically. The saved v2 pack/report is the
current frozen comparison; no founder annotation is required. A new run needs
the isolated CREMA environment and built Chordino/NNLS assets from the candidate
setup guides, and fresh output directories:

```sh
.venv-analysis/bin/python experiments/analysis/rich_quality_suite.py generate --output-dir experiments/generated/rich-quality-suite-new
.venv-analysis/bin/python experiments/analysis/rich_quality_screen.py --suite experiments/generated/rich-quality-suite-new --output experiments/generated/rich-quality-screen-new
```

The [Wonderwall wrapper](../docs/WONDERWALL_GUIDED_DRAFT.md) separately builds
frozen section/quality controls and runs six alignments, or verifies cached
outputs without model inference. These results remain research artifacts;
the automatic player continues to use its existing raw drafts.

[Acceptance experiments](../docs/ACCEPTANCE_SCREEN.md) use `acceptance_fixtures.py`
for fresh voiced/silent/repeat cases, `guarded_aligner.py` for active-evidence
dwell and quality abstention, and `acceptance_screen.py` for declare/develop/
freeze/validate stages. The saved policy requires its SHA and matching code
before validation. No neural inference is needed with the existing native
feature caches; the original aligner and reports remain unchanged.

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

Prepare creates a new mono 22,050 Hz, 16-bit PCM WAV and refuses to overwrite existing audio. Analysis accepts 16-bit PCM WAV (mono or stereo). Use the prepared WAV for both analysis and browser playback so decoder offsets or different edits do not confound timing. Select the local WAV and its chart in the bench. The separate [YouTube importer](../docs/YOUTUBE_IMPORT.md) accepts an explicitly chosen recording; the browser does not run extraction or analysis.

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
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini,chordino
```

Install model environments/assets using the candidate setup documents before requesting their runs; [Chordino](../docs/CHORDINO_SETUP.md) uses a project-local native build. `--reuse-existing` requires matching saved-prediction audio hashes and does not rerun any detector, including the baseline. Failed/unavailable candidates remain visible and make the runner exit nonzero; logs, JSON and CSV stay in the generated suite directory. The five-candidate screen completed 320 comparisons with zero failures. See [recorded results](../docs/SYNTHETIC_RESULTS.md), including the chord-only metric that excludes silence and ambiguous power chords.

The server's `/api/suite` inventory exposes only safe case IDs and allowlisted audio/chart files. Use Load synthetic suite → choose case → Load case in the bench. No model inference happens in the browser. Generated cases can be played without guitar first; founder guitar sessions follow the automated screening.

Use synthetic failures to diagnose integration/timing/vocabulary problems early. Confirm adapters and input conventions before dropping a candidate: artificial tones can be outside the training domain of a real-recording model. Power chords require ambiguous-quality or root-only evaluation. Real recordings and guitar play-tests remain the selection evidence.

## Known-chart timing

The new NumPy aligner accepts strictly untimed ordered labels, with explicit finite/cyclic assumptions. It preserves source hashes, raw path evidence and `N`/`X` gaps; it does not infer capo conversion or song structure. See [setup](../docs/CHART_ALIGNER_SETUP.md).

```sh
.venv-analysis/bin/python experiments/analysis/alignment_screen.py
```

The [64-case conditional screen](../docs/ALIGNMENT_SCREEN.md) withholds all reference timing/silence events from inference. Its timing score assumes the correct harmonic order and count. The [three-song import smoke](../docs/YOUTUBE_IMPORT_SMOKE.md) proves acquisition and detector execution; its Creep cyclic alignment remains an unaccepted draft. Exact excerpt/section review and independent timing references precede real-song scoring and founder guitar sessions.

Version 0.2 adds finite section/repeat charts and cached NNLS acoustic packets. Build the separate [native host](../docs/NNLS_CHROMA_EVIDENCE.md), then run `alignment_comparison.py` for the frozen 64-case paired comparison. Native evidence consumes audio only; source hashes and fixed frame-center coordinates remain explicit. [Paired results](../docs/ACOUSTIC_ALIGNMENT_COMPARISON.md) and [real diagnostics](../docs/REAL_ALIGNMENT_DIAGNOSTICS.md) remain separate.

The default [automatic player](../docs/AUTOMATIC_DRAFTS.md) serves full-song drafts on port 8068, independently of the synthetic bench. Chords appear immediately; one tap captures a problem time and saves feedback locally. Manual chord/timestamp entry is optional advanced work. Earlier 20-second packs remain available as research artifacts; no model output or reaction timestamp becomes reference truth automatically. [Instructions](../docs/LISTENING_REVIEW.md) explain storage and practice views.
