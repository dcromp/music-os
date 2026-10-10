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
| Baseline run and automated checks | Complete | Initial fixture works; expanded 16 Python and 48 JavaScript checks pass |
| Local play-along bench | Complete | Live Mac browser checks passed: playback, pause, seeking, switching charts, Restart and visible CSV export |
| Run guide, deployment and evidence | Complete | Local startup instructions below; measurements and limits in [Phase 0 results](docs/PHASE0_RESULTS.md) |
| Automated synthetic screening before guitar | Initial batch complete | 64 cases × 4 algorithms = 256 successful comparisons; [results](docs/SYNTHETIC_RESULTS.md) |
| Additional candidates | Pending | Chordino needs Mac Vamp setup; ChordFormer needs source/checkpoint review |
| Founder guitar test on real material | Deferred | After automated screening and reference checks; 15–20 minutes when ready |

The initial fixture checks experiment plumbing. The expanded synthetic suite now compares the template baseline, BTC, CREMA and ChordMini/ChordNet across clean triads, voicings/timbres, guitar-like attacks, distractors and timing/vocabulary complexity. ChordMini leads major/minor core agreement (94.7%) and boundary F1 (0.927) in this suite. All audio is procedural; no production algorithm has been selected and no guitar ratings have been used. The founder confirmed the previous analysis code was deleted, so the baseline is newly implemented.

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

## Automated synthetic tests

The deployed Mac browser has saved predictions for all four candidates; playback does not require the model environments. Install the isolated candidate environments/assets below before rerunning model inference in a fresh checkout.

Candidate setup: [BTC](docs/BTC_SETUP.md), [CREMA](docs/CREMA_SETUP.md), [ChordMini](docs/CHORDMINI_SETUP.md). The baseline environment is separate from the model environments.

```sh
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py generate
.venv-analysis/bin/python experiments/analysis/synthetic_suite.py run --candidates baseline,btc,crema,chordmini
```

The runner loads each model once per batch, scores every case, writes JSON/CSV under `experiments/generated/synthetic-suite`, and exits nonzero for requested unavailable candidates or failed cases. Use `--reuse-existing` to rescore outputs only; it verifies audio hashes. Committed [results](docs/SYNTHETIC_RESULTS.md) include per-case evidence.

In the browser, press **Load synthetic suite**, choose a case, and **Load case** to compare its reference and available candidate charts. This is the next step before guitar sessions. Chordino and newer candidates remain explicit backlog items, not untested algorithms with assigned scores.

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

Review the automated screening's weakest cases, add Chordino and other verified candidates, then test promising models and separation variants on permitted real excerpts and annotated holdouts. Record quality, timing errors, correction effort and runtime before founder guitar sessions and product integration.
