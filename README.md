# music-os

An affordable guitar practice companion, working toward a **band in your pocket** for people who usually play alone.

Development starts with choosing useful chord/rhythm algorithms on Mac and testing them with a guitar. The older Expo app is a reusable UI prototype; iOS development and product integration follow the algorithm experiments.

## Current status

Updated 10 October 2026. Status and deployment information belong in this README as work progresses. The full roadmap is in [plan.md](plan.md); source findings and existing-app checks are in [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md).

| Phase 0 part | Status | Remaining ETA / evidence |
|---|---|---|
| Existing-code audit and reuse decisions | Complete | Expo shell/song cards reusable; chart data and clock need later repair |
| Isolated Mac analysis environment | Complete | Python 3.12.10 and pinned NumPy 2.2.6; separate from npm/Expo |
| Output format and known-chord audio | Complete | Version 1.0 JSON; generated 22-second triad/silence fixture |
| Baseline run and automated checks | Complete | 98.9% exact-label duration agreement on synthetic fixture; 7 Python and 41 JavaScript checks pass |
| Local play-along bench | Complete | Live Mac browser checks passed: playback, pause, seeking, switching charts, Restart and visible CSV export |
| Run guide, deployment and evidence | Complete | Local startup instructions below; measurements and limits in [Phase 0 results](docs/PHASE0_RESULTS.md) |
| Founder guitar test on real material | Pending founder session | 15–20 minutes once suitable local audio is chosen |

The synthetic result checks experiment plumbing. It is not a real-guitar benchmark or a selected production algorithm. The baseline produced 11 segments against 8 reference segments, including brief extra transitions. BTC, CREMA, source separation and real-song comparisons remain Phase A work. The founder confirmed the previous analysis code was deleted, so the baseline is newly implemented.

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

On the founder's audited Mac, `/Users/davidcrompton/miniforge3/bin/python` is Python 3.12.10 and can replace `python3.12` in the first command. The Homebrew `python3` is 3.14.3 and was not used for the baseline.

Open [http://127.0.0.1:8067](http://127.0.0.1:8067/) and press **Load demo**. Choose the reference chart or baseline output, play/seek/replay, and compare the current and upcoming chords. Ratings stay in the tab until exported. Use **Download CSV**, or **Show CSV** to copy the text if the browser does not save the download; the visible fallback was verified in the in-app browser. Local audio and JSON can also be selected; prepare and analyse the same recording as described in [experiments/README.md](experiments/README.md).

## Deployment

| Target | State | Start / stop |
|---|---|---|
| Mac experiment bench | Running locally in this session; live browser checks passed | Run `lab.py serve`; opens on localhost port 8067. Stop with Ctrl+C. Use `--port 8068` if needed. |
| Public web service | Not deployed | Hosting, authentication, storage and public launch are later work |
| Native macOS app | Not configured | The current Mac tool is a browser page plus local analysis scripts |
| Expo web product | Existing build fails | Missing `react-native-web-webview` in the YouTube wrapper; defer repair until product integration |
| Expo Android product | Bundle export passed | Device installation and live playback remain unverified |
| Expo iOS product | Existing project target; not verified/deployed | Defer device/build work until algorithm and practice results justify integration |

To restart the existing Mac setup, run `cd /Users/davidcrompton/Documents/music-os` followed by `.venv-analysis/bin/python experiments/analysis/lab.py serve`; the environment and demo are already created.

The experiment server binds to `127.0.0.1` only. It serves the bench and generated demo files, not the repository generally. It has no public hosting, uploads, accounts or background daemon. Generated audio, local recordings, results and `.venv-analysis` are gitignored. Restart the command after restarting the machine; a source push does not deploy a hosted service.

## Existing Expo prototype

The prototype has hardcoded song cards, embedded YouTube playback and a sample chord animation. The animation uses unrelated data and an independent timer, so it is not the algorithm-testing interface.

```sh
npm ci
npm start
```

This is the old app startup path, not the Mac experiment setup above. Expo SDK 51 / React Native 0.74.5 need a compatibility check before current device deployment. Do not run `npm run reset-project`: it moves the existing app out of its routes.

## Next

Extend the synthetic screening from clean triads to varied voicings/timbres, guitar-like attacks and controlled mix/rhythm complexity. Use it to diagnose basic failures, then compare baseline/BTC/CREMA and separation variants on permitted real excerpts and annotated holdouts. Record quality, timing errors, correction effort, runtime and founder guitar ratings before selecting a pipeline and integrating it into a product UI.
