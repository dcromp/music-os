# music-os

An affordable guitar practice companion, working toward a **band in your pocket** for people who usually play alone.

Development starts with choosing useful chord/rhythm algorithms on Mac and testing them with a guitar. The older Expo app is a reusable UI prototype; iOS development and product integration follow the algorithm experiments.

## Current status

Updated 10 October 2026. Status and deployment information belong in this README as work progresses. The full roadmap is in [plan.md](plan.md); source findings and existing-app checks are in [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md).

| Mac experiment step | Status | Remaining ETA / evidence |
|---|---|---|
| Existing-code audit and reuse decisions | Complete | Expo shell/song cards reusable; chart data and clock need later repair |
| Isolated Mac analysis environment | Complete | Python 3.12.10 and pinned NumPy 2.2.6; separate from npm/Expo |
| Output format and known-chord audio | Complete | Version 1.0 JSON; generated 22-second triad/silence fixture |
| Baseline run and automated checks | Complete | Analysis, pilot, draft-preparation and browser checks pass; native tests require built assets |
| Local play-along bench | Complete | Live Mac browser checks passed: playback, pause, seeking, switching charts, Restart and visible CSV export |
| Run guide, deployment and evidence | Complete | Local startup instructions below; measurements and limits in [Phase 0 results](docs/PHASE0_RESULTS.md) |
| Automated synthetic screening before guitar | Expanded batch complete | 64 cases × 5 algorithms = 320 successful comparisons; [results](docs/SYNTHETIC_RESULTS.md) |
| Chordino Mac setup and comparison | Complete | Project-local native build, common adapter and 64 successful runs; [setup](docs/CHORDINO_SETUP.md) |
| Annotated real-guitar pilot | Complete | Six preselected GuitarSet performances × five models = 30 successful runs; [results](docs/GUITARSET_PILOT.md) |
| Famous-song audio import and detector smoke | Complete | Creep, Wonderwall and House of the Rising Sun imported with yt-dlp; 9 successful detector runs; [evidence](docs/YOUTUBE_IMPORT_SMOKE.md) |
| Chart alignment baseline and synthetic timing | Complete experimental baseline | 64/64 cases; 90.4% mean boundary F1 given correct chord order, with 59 extra / 1 missed changes; [results](docs/ALIGNMENT_SCREEN.md) |
| Explicit section order and repeat counts | Implemented | Finite untimed section schema, partial-prefix handling and five new checks pass; real arrangements remain hypotheses |
| NNLS acoustic evidence comparison | Complete experimental comparison | 64 pairs / 128 successful alignments; conditional F1 98.4% NNLS vs 90.4% spectral, with timing tradeoffs; [results](docs/ACOUSTIC_ALIGNMENT_COMPARISON.md) |
| Automatic full-song play-along | Ready | Creep, Wonderwall and House load complete drafts immediately; optional one-tap issue feedback; [setup](docs/AUTOMATIC_DRAFTS.md) |
| Automated draft/warning evaluation | Complete | Six annotated performances / 12 reference comparisons, exact primary-score parity; disagreement warnings are optional hints; [results](docs/DRAFT_SCREEN.md) |
| Curated real-song alignment validation | Further evaluation planned | Full-mix accuracy and broader holdout comparisons remain unmeasured; manual transcription is not required to try the player; [design](docs/CHART_ALIGNMENT.md) |
| Separation and soft key/context pipeline | Planned supporting experiments | Four controlled variants where alignment/recognition failures justify them; see [plan](plan.md) |
| Further research candidates | Backlog | ChordFormer source/checkpoint review; real-recording evidence takes priority |
| Founder play-along feedback | Optional, ready now | Play normally; tap only if something feels wrong. No timestamp or chord-name entry required |

The synthetic suite compares the template baseline, BTC, CREMA, ChordMini/ChordNet and Chordino across clean triads, voicings/timbres, guitar-like attacks, distractors and timing/vocabulary complexity. ChordMini leads the original core metric including silence (94.7%) and boundary F1 (0.927); the baseline leads the new chord-only core metric (96.1%). Chordino scores 95.4% chord-only, with weaker silence and boundary handling. All audio in that suite is procedural; these are not real-song accuracy estimates and no production algorithm has been selected. The founder's previous analysis code was deleted; the older Expo app only displayed hardcoded sample chords. See [app-readiness criteria](docs/APP_READINESS.md).

The real-guitar pilot changes the ranking: CREMA leads at **93.9% intended major/minor agreement** and 94.4% root agreement. BTC scores 84.0%, Chordino 82.7%, ChordMini 79.5% and the baseline 54.3% on intended major/minor. Eligible reference coverage is 98.1%; performed-quality comparisons have lower coverage and separate scores. Six acoustic performances are a diagnostic sample, not an accuracy estimate for arbitrary songs. No source separation, key assistance or founder play-tests have been used yet.

The default player now starts with complete automatic CREMA drafts for the three imported songs. CREMA is the experimental primary because it led the annotated acoustic pilot; full-mix accuracy remains unmeasured. Chordino differences provide optional hints, without replacing primary chords or claiming that agreement proves correctness. The known-chart/NNLS experiments remain available separately: their cyclic drafts and bounded prefixes have not been accepted as verified arrangements. See [automatic preparation](docs/AUTOMATIC_DRAFTS.md) and [real diagnostics](docs/REAL_ALIGNMENT_DIAGNOSTICS.md).

## Run on Mac

The experiment bench is a local browser tool, independent of the Expo app. Requirements: Python 3.12 and a browser; FFmpeg is needed only to convert other local recordings.

The current Mac checkout is `/Users/davidcrompton/Documents/music-os`, on branch `codex/mac-analysis-phase0`. From the repository root:

```sh
cd /Users/davidcrompton/Documents/music-os
python3.12 -m venv .venv-analysis
.venv-analysis/bin/python -m pip install -r experiments/analysis/requirements.txt
.venv-analysis/bin/python experiments/analysis/lab.py smoke
.venv-analysis/bin/python -m unittest discover -s experiments/analysis/tests -v
.venv-analysis/bin/python experiments/analysis/lab.py serve
```

Browser-logic checks additionally run with `node experiments/bench/test.js` (no npm install needed).

The [YouTube import guide](docs/YOUTUBE_IMPORT.md) covers isolated yt-dlp setup and cached recordings. The existing iframe wrapper supplies playback, while the separate Python importer supplies prepared local audio. Automatic drafts are ready to use below.

## Play with the automatic draft

Open [the player](http://127.0.0.1:8068/), choose a song and press play. The current chord and upcoming changes appear automatically. Listen or pick up your guitar; there is no annotation task to complete first.

If something feels wrong, tap **Something feels wrong**. The page captures the playback time and chord and saves the issue automatically in this browser. A reason or note is optional. Model disagreements, other charts and manual corrections are under optional details; none is a checklist you must finish. [Instructions](docs/LISTENING_REVIEW.md) explain storage and practice views. The synthetic bench on port 8067 remains optional.

## Automated synthetic tests

The deployed Mac browser has saved predictions for all five candidates; playback does not require the model environments. Install the isolated candidate environments/assets below before rerunning model inference in a fresh checkout.

Candidate setup: [BTC](docs/BTC_SETUP.md), [CREMA](docs/CREMA_SETUP.md), [ChordMini](docs/CHORDMINI_SETUP.md), [Chordino](docs/CHORDINO_SETUP.md). The baseline environment is separate from the model environments; Chordino uses a local native plugin/host.

```sh
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py generate
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini,chordino
```

The runner loads each model once per batch, scores every case, writes JSON/CSV under `experiments/generated/synthetic-suite`, and exits nonzero for requested unavailable candidates or failed cases. Use `--reuse-existing` to rescore outputs only; it verifies audio hashes. Committed [results](docs/SYNTHETIC_RESULTS.md) include per-case evidence.

The known-chart timing screen runs separately, using the generated audio and ordered labels with every reference timestamp and silence event withheld from the aligner:

```sh
.venv-analysis/bin/python experiments/analysis/alignment_screen.py
```

Add `--overwrite` only to replace an existing screen deliberately. [Results](docs/ALIGNMENT_SCREEN.md) report boundary precision/recall, missed/extra changes, silence coverage and unknown spans. [Setup](docs/CHART_ALIGNER_SETUP.md) explains finite versus cyclic inputs and sounding chord labels.

For the newer frozen spectral/NNLS comparison, build the separate [native acoustic host](docs/NNLS_CHROMA_EVIDENCE.md) and run `.venv-analysis/bin/python experiments/analysis/alignment_comparison.py`. Saved [paired results](docs/ACOUSTIC_ALIGNMENT_COMPARISON.md) report all 64 cases and extraction/alignment runtimes separately; use a new output directory or explicit `--overwrite` for another run.

Automated runs and reference evaluation are handled by the agent. To inspect synthetic results, press **Load synthetic suite** in the port-8067 bench, choose a case, and **Load case**. The default port-8068 player is for ordinary play-along and optional issue feedback, with no transcription assignment. See [app-readiness criteria](docs/APP_READINESS.md).

Real-guitar scoring uses pinned `mir_eval` in a separate evaluation environment. The Mac deployment includes saved pilot inputs/references/predictions and `.venv-pilot`, so the existing results can be rescored without loading the models:

```sh
.venv-pilot/bin/python experiments/analysis/guitarset_pilot.py run --reuse-existing
.venv-pilot/bin/python -m unittest discover -s experiments/analysis/tests -p test_guitarset_pilot.py -v
```

For a fresh checkout, create `.venv-pilot` with Python 3.12 and install `experiments/analysis/requirements-pilot.txt`. Model inference and retrieval of the original dataset assets are separate setup steps in [the pilot report](docs/GUITARSET_PILOT.md).

On the founder's audited Mac, `/Users/davidcrompton/miniforge3/bin/python` is Python 3.12.10 and can replace `python3.12` in the first command. The Homebrew `python3` is 3.14.3 and was not used for the baseline.

Open [http://127.0.0.1:8067](http://127.0.0.1:8067/) and press **Load demo**. Choose the reference chart or baseline output, play/seek/replay, and compare the current and upcoming chords. Ratings stay in the tab until exported. Use **Download CSV**, or **Show CSV** to copy the text if the browser does not save the download; the visible fallback was verified in the in-app browser. Local audio and JSON can also be selected; prepare and analyse the same recording as described in [experiments/README.md](experiments/README.md).

## Deployment

| Target | State | Start / stop |
|---|---|---|
| Mac experiment bench | Running locally in this session; live browser checks passed | Run `lab.py serve`; opens on localhost port 8067. Stop with Ctrl+C. Use `--port 8069` if needed; listening review uses 8068. |
| Mac automatic player | Running on port 8068; immediate chords and capo-view switching verified | Run `automatic_drafts.py serve --pack experiments/generated/automatic-playalong --port 8068`; stop with Ctrl+C. |
| Public web service | Not deployed | Hosting, authentication, storage and public launch are later work |
| Native macOS app | Not configured | The current Mac tool is a browser page plus local analysis scripts |
| Expo web product | Existing build fails | Missing `react-native-web-webview` in the YouTube wrapper; defer repair until product integration |
| Expo Android product | Bundle export passed | Device installation and live playback remain unverified |
| Expo iOS product | Existing project target; not verified/deployed | Defer device/build work until algorithm and practice results justify integration |

To restart the existing Mac setup, run `cd /Users/davidcrompton/Documents/music-os` followed by `.venv-analysis/bin/python experiments/analysis/lab.py serve`; the environment and demo are already created.

The experiment server binds to `127.0.0.1` only. It serves the bench and allowlisted experiment files, not the repository generally. It has no public hosting, uploads, accounts or background daemon. Generated audio, local recordings, results and analysis environments are gitignored. Restart the command after restarting the machine; a source push does not deploy a hosted service.

The Mac checkout contains cached three-song audio, detector charts, conditional screens, NNLS evidence, legacy review windows and `experiments/generated/automatic-playalong/`. The player serves only its allowlisted audio/chart/evidence assets. Feedback persists in browser-local storage; download/copy is an optional backup, not a required step. `.venv-youtube` supports fresh imports, and native assets support NNLS extraction. Neural inference environments remain separate research setup; saved playback requires none of them. Restart each server after reboot.

## Existing Expo prototype

The prototype has hardcoded song cards, embedded YouTube playback and a sample chord animation. The animation uses unrelated data and an independent timer, so it is not the algorithm-testing interface.

```sh
npm ci
npm start
```

This is the old app startup path, not the Mac experiment setup above. Expo SDK 51 / React Native 0.74.5 need a compatibility check before current device deployment. Do not run `npm run reset-project`: it moves the existing app out of its routes.

## Next

Continue automated comparisons with annotated data and fresh holdout material while the founder plays normally. Optional timestamped feedback helps target problems; it is not reference truth. The Animals corpus recording still requires version matching before scoring. Compare recognition, vocabulary guidance and known-sequence alignment, then measure correction effort and followability. The founder does not need to manually transcribe the repertoire.
