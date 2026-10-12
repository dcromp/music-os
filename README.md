# music-os

An affordable guitar practice companion, working toward a **band in your pocket** for people who usually play alone.

Development starts with choosing useful chord/rhythm algorithms on Mac and testing them with a guitar. The older Expo app is a reusable UI prototype; iOS development and product integration follow the algorithm experiments.

## Current status

Updated 12 October 2026. Status and deployment information belong in this README as work progresses. The full roadmap is in [plan.md](plan.md); source findings and existing-app checks are in [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md).

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
| Curated real-song alignment validation | Ensemble diagnostic complete; broader validation continues | Written-chart agreement is measured on three jazz mixes; exact popular-song arrangements remain unverified; [design](docs/CHART_ALIGNMENT.md) |
| Separation and soft key/context pipeline | Planned supporting experiments | Four controlled variants where alignment/recognition failures justify them; see [plan](plan.md) |
| Further research candidates | Backlog | ChordFormer source/checkpoint review; real-recording evidence takes priority |
| Founder play-along feedback | Initial qualitative feedback received | Mostly correct; Wonderwall's richer shapes need attention. No measured accuracy score; [audit and next step](docs/WONDERWALL_QUALITY_AUDIT.md) |
| Rich-quality synthetic controls | Complete | 24 richer/plain/contrast guitar-voicing cases, four conditions and two transposed recipe variants; [results](docs/RICH_QUALITY_SCREEN.md) |
| Rich-quality and corrupted-chart evaluation | Complete; rejection check fails | 224/224 comparisons; known-chart timing works on these examples, but both aligners retain every forced rich upgrade on eight plain controls |
| Wonderwall guided full-song hypothesis | Complete, unaccepted | Six frozen runs; reversed section order also completes with low mismatch and compressed positions; [diagnostics](docs/WONDERWALL_GUIDED_DRAFT.md) |
| Guarded quality / section acceptance | Implemented and evaluated | Active-evidence dwell and same-root/added-tone checks; original aligner remains frozen; [evaluation](docs/ACCEPTANCE_SCREEN.md) |
| Fresh acceptance validation | Complete | 888 development/validation attempts, zero failures; NNLS reduces wrong-label seconds by 77.8% on fresh corrupt charts and retains 96.3% correct harmony on correct charts; spectral guard fails retention check |
| Guarded Wonderwall diagnostic | Complete, unaccepted | All six runs eliminate silent progress; reversed NNLS is partial, but wrong arrangements still retain labels; [diagnostics](docs/WONDERWALL_GUARDED_CHECK.md) |
| Beginner core-chord display | Deployed and browser verified | Optional Core chords view removes selected extensions, retains suspensions and raw feedback; 29 browser helper checks pass |
| Core-chord cached screen | Complete | 48 unchanged outputs rescored: CREMA 61.0% exact / 73.8% core, Chordino 61.5% / 72.8%; [retrospective results](docs/CORE_CHORD_SCREEN.md) |
| Whole-sequence diagnostic | Complete, insufficient for acceptance | 25 cached comparisons; stable edit distance ranks the correct chart first in 3/4 procedural recordings, with a wrong extra repeat first in the fourth; [results](docs/ARRANGEMENT_SCREEN.md) |
| Beginner repertoire seed | Complete | 100 source-linked title candidates from Hal Leonard lists; [catalogue and first ten](docs/CATALOGUE_SEED.md) |
| First ten recording identities / teaching variants | Source review complete | Exact uploads and two proposed skill tracks saved; recording-compatible shapes/rhythm need checks; [review](docs/FIRST_TEN_REVIEW.md) |
| First ten automatic preparation / raw drafts | Complete | Ten recordings and 20 charts; eight new inputs, two exact cache reuses, bounded failure recovery; [evidence](docs/FIRST_TEN_PREPARATION.json) |
| Expanded ten-song playback | Deployed and browser verified | All ten load cues, playback/seek and Core chords work; 47 served assets match Mac bytes; original 8068 retained |
| Chord hold lengths / estimated beats and bars | Deployed and browser verified | Current hold/progress, upcoming lengths and a proportional strip; approximate pulse units with seconds fallback; [evidence](docs/PLAYALONG_RHYTHM.md) |
| Suggested strumming practice | Deployed and browser verified | Two original practice drills per song, including 6/8 and syncopation; matching recorded patterns remains later work |
| Independent first-ten reference discovery | Source candidates found | Five songs have independent annotations; corpus master/time-origin matching remains open; [metadata](docs/FIRST_TEN_REFERENCE_CANDIDATES.json) |
| Cached acoustic pulse/count check | Complete diagnostic | Six exact audio/JAMS pairs; tempo guidance fixes one pulse-level error, supported-window mean count error 0.309→0.048 beats; phase remains uneven; [results](docs/RHYTHM_REFERENCE_CHECK.md) |
| Fresh acoustic pulse/count reference check | Complete | Ten frozen exact pairs, four development/six holdout; guided holdout count error 1.245→0.097 beats, with 23/344 windows unsupported; phase remains uneven; [results](docs/FRESH_GUITARSET_RHYTHM_CHECK.md) |
| Fresh five-model chord comparison | Complete | 50 successful runs / 100 intended/performed comparisons; comping and single-note solos reported separately; [results](docs/FRESH_GUITARSET_CHORD_CHECK.md) |
| External mixed-instrument beat challenges | Complete | Three author-paired ARTBeaT clips; 76.3% whole-recording F1 at 70ms, variable-tempo piano weaker; [results](docs/MIXED_RHYTHM_REFERENCE_CHECK.md) |
| Paired ensemble chord comparison | Complete diagnostic | Three 60-second JazzSAMBA mixes; unchanged five-model extension, BTC 69.2% / CREMA 64.9% supported-chart maj/min agreement, 83.8% coverage; [results](docs/JAZZSAMBA_REFERENCE_CHECK.md) |
| First-ten setup / rhythm / section-source review | Complete source review | All ten paired identities; specific swing/mute/build-up/retuning/section work items, exact-upload timings still unverified; [review](docs/FIRST_TEN_ARRANGEMENT_CHECK.md) |
| Neural beat candidate comparison | Complete diagnostic | Two published checkpoints, 36 successful runs across 18 paired inputs; small model helps fluctuating piano, tempo-level ambiguity remains; [results](docs/BEAT_THIS_COMPARISON.md) |
| Nominal barline check | Complete retrospective diagnostic | Six experiment holdouts: 65.4% / 63.6% F1 at 70ms, with many extra bar starts; keep approximate counts and seconds fallback; [results](docs/NOMINAL_DOWNBEAT_CHECK.md) |
| Supplied-order ensemble alignment | Complete; current guard loses too much coverage | Twelve frozen runs; source-order agreement 61.9% baseline / 33.7% guarded, with wrong cues retained on corrupted charts; [results](docs/JAZZSAMBA_ALIGNMENT_CHECK.md) |
| Written-bar chart alignment | Complete; timing/acceptance still fail | Eighteen runs; 86.8% / 86.0% conditional chart agreement, but nominal targets share input BPM/coordinates and boundaries remain unreliable; [results](docs/BAR_CHART_ALIGNMENT.md) |
| Source-separation comparison | Preparing isolated runtime and frozen protocol | Three existing ensemble excerpts, original/drums removed/drums+vocals removed, unchanged BTC; estimated 30–50 minutes for processing and paired report |
| Commercial song-access route | Initial comparison complete | Official embeds plus separately permitted analysis is the preferred route; private licence prices remain unresolved; [comparison](docs/SONG_ACCESS_FEASIBILITY.md) |
| Representative real references / learner validation | In progress | Estimated 1.5–2.5 focused days for broader annotated/version-matched checks; founder transcription is not required |

The synthetic suite compares the template baseline, BTC, CREMA, ChordMini/ChordNet and Chordino across clean triads, voicings/timbres, guitar-like attacks, distractors and timing/vocabulary complexity. ChordMini leads the original core metric including silence (94.7%) and boundary F1 (0.927); the baseline leads the new chord-only core metric (96.1%). Chordino scores 95.4% chord-only, with weaker silence and boundary handling. All audio in that suite is procedural; these are not real-song accuracy estimates and no production algorithm has been selected. The founder's previous analysis code was deleted; the older Expo app only displayed hardcoded sample chords. See [app-readiness criteria](docs/APP_READINESS.md).

The real-guitar pilot changes the ranking: CREMA leads at **93.9% intended major/minor agreement** and 94.4% root agreement. BTC scores 84.0%, Chordino 82.7%, ChordMini 79.5% and the baseline 54.3% on intended major/minor. Eligible reference coverage is 98.1%; performed-quality comparisons have lower coverage and separate scores. Six acoustic performances are a diagnostic sample, not an accuracy estimate for arbitrary songs. No source separation or key assistance has been applied in this comparison; founder feedback does not contribute to these scores.

The [paired rhythm diagnostic](docs/RHYTHM_REFERENCE_CHECK.md) checks six cached recordings against nominal beat grids. The [fresh ten-input check](docs/FRESH_GUITARSET_RHYTHM_CHECK.md) is now complete: a public open-licensed archive mirror has an index identical to the official archive, and selected entries pass CRC/size and JAMS hash checks. Tempo guidance improves duration counts, while phase errors remain. No downbeats or physical chord boundaries are verified. Exact popular-song reference matching remains open.

The expanded player starts with complete automatic CREMA drafts for ten selected recordings; the original three-song player remains available. CREMA is the experimental primary because it led the annotated acoustic pilot; full-mix accuracy remains unmeasured. Chordino differences provide optional hints, without replacing primary chords or claiming that agreement proves correctness. The known-chart/NNLS experiments remain available separately: their cyclic drafts and bounded prefixes have not been accepted as verified arrangements. See [automatic preparation](docs/AUTOMATIC_DRAFTS.md) and [real diagnostics](docs/REAL_ALIGNMENT_DIAGNOSTICS.md).

The first qualitative feedback is promising: the player seems mostly correct, with Wonderwall's Em7/Dsus4/A7sus4/Cadd9 shapes a concern. CREMA cannot emit add9 or 7sus4; default Chordino lacks those and suspensions. The [richer synthetic comparison](docs/RICH_QUALITY_SCREEN.md) is complete: raw exact quality on rich progressions is 42.8% CREMA / 36.0% Chordino, versus 92.5% / 95.4% on plain controls. Given correct labels/order/count, spectral timing F1 is 100.0% and NNLS 96.5%; these are conditional procedural results. Deliberately upgrading plain chords to rich labels survives both rejection masks in all eight controls. The [full Wonderwall hypothesis](docs/WONDERWALL_GUIDED_DRAFT.md) also exposes wrong-order compression. Improve quality/section acceptance before promoting guided arrangements. Raw predictions and the deployed player remain unchanged.

The [new guarded comparison](docs/ACCEPTANCE_SCREEN.md) freezes settings on development cases before 16 fresh synthetic recordings. Harmonic progress through silence is eliminated. The NNLS path reduces incorrect-label time on corrupt charts from 272.492 to 60.392 seconds while correct-chart harmonic quality remains 96.3%; neither result is real-song accuracy. The spectral guard loses too much correct harmony and is excluded from further guarded-arrangement consideration. Wrong chords and missing/extra repeats still survive, and short unknown gaps add display changes. Keep CREMA for current automatic drafts and NNLS as the guarded-alignment research candidate; whole-arrangement validation remains necessary.

The founder's beginner focus now has an optional **Core chords** display. Em7 becomes Em and Cadd9 becomes C; Dsus4 stays Dsus4, and A7sus4 becomes Asus4. Full chords remain the default. Adjacent identical core labels display as one interval, while gaps, silence and uncertainty stay visible. Saved charts, raw labels and feedback timestamps are preserved. The [48-output cached screen](docs/CORE_CHORD_SCREEN.md) shows which extension distinctions this easier task ignores; it does not improve the detector or establish substitute suitability. The [25-comparison structure diagnostic](docs/ARRANGEMENT_SCREEN.md) uses a chart-independent acoustic sequence, but still sometimes favours wrong repeats. No guided arrangement is promoted.

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

Open [the ten-song player](http://127.0.0.1:8070/), choose a song and press play. The [original three-song player](http://127.0.0.1:8068/) retains its earlier recordings and feedback. The current chord and upcoming changes appear automatically. Listen or pick up your guitar; there is no annotation task to complete first.

If something feels wrong, tap **Something feels wrong**. The page captures the playback time and chord and saves the issue automatically in this browser. A reason or note is optional. Model disagreements, other charts and manual corrections are under optional details; none is a checklist you must finish. [Instructions](docs/LISTENING_REVIEW.md) explain storage and practice views. The synthetic bench on port 8067 remains optional.

Choose **Chord detail → Core chords** for the simpler view. The current full detected shape appears underneath when it differs. This may change the sound; it is not a verified beginner arrangement. Choice stays with the song during the tab session and returns to Full chords after reload. Issue reports record the quality view used at the tap.

**Chord lengths** shows approximate beats/bars or seconds. Each current and upcoming chord shows how long to hold it; the progress bar and timeline follow the audio clock. House uses a proposed 6/8 convention, while Wonderwall shows beats until its meter changes are mapped. Counts outside the detected beat range fall back to seconds.

**Suggested strumming** gives count-and-arrow practice exercises. Start with the simple pattern and optionally choose the next one. D ↓ means down, U ↑ means up, and — means skip that stroke while keeping your hand moving. These are practice suggestions; the recorded parts may differ. [Details and evidence](docs/PLAYALONG_RHYTHM.md).

The [100-song pool](catalogue/rock-candidates.json) now has a [reviewed first-ten batch](docs/FIRST_TEN_REVIEW.md). All ten have automatic drafts; their proposed learning order and teaching shapes need recording/arrangement checks. The page shows chord cues, not riff instruction or a verified strumming lesson. Come As You Are uses studio D standard; Seven Nation Army distinguishes original Open A from a standard-tuning teaching adaptation. See the review before practising those riffs.

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

Automated runs and reference evaluation are handled by the agent. To inspect synthetic results, press **Load synthetic suite** in the port-8067 bench, choose a case, and **Load case**. The port-8070 ten-song player is for ordinary play-along and optional issue feedback, with no transcription assignment. See [app-readiness criteria](docs/APP_READINESS.md).

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
| Original Mac automatic player | Running on port 8068; core/full and capo/sounding views verified, served file bytes checked | Run `automatic_drafts.py serve --pack experiments/generated/automatic-playalong --port 8068`; stop with Ctrl+C. Reload an older tab to load the Core chords selector. |
| Expanded ten-song Mac player | Running on port 8070; all ten guides, hold lengths/progress, proportional strip and strumming verified | Run `automatic_drafts.py serve --pack experiments/generated/automatic-first-ten-v1 --port 8070`; stop with Ctrl+C. Uses a separate feedback pack identity. |
| Rich-chord / Wonderwall research | Tools and cached v2 results saved in the Mac checkout; hashes and 26 new checks verified | See [rich screen](docs/RICH_QUALITY_SCREEN.md) and [frozen Wonderwall CLI](docs/WONDERWALL_GUIDED_DRAFT.md). Recognition reruns need isolated model environments; cached diagnostics do not. |
| Guarded acceptance research | Frozen settings, 888 comparison outputs and six verified Wonderwall diagnostics saved on Mac | [Acceptance guide](docs/ACCEPTANCE_SCREEN.md) and [full-song check](docs/WONDERWALL_GUARDED_CHECK.md); existing native caches suffice, with no neural inference or player change |
| Core / structure diagnostics | 48 core and 25 structure comparisons complete; all cache input/outcome hashes verified on Mac | [Core screen](docs/CORE_CHORD_SCREEN.md), [structure screen](docs/ARRANGEMENT_SCREEN.md); `core-chord-screen-v1` and `arrangement-screen-v2` saved locally, with no model environments needed |
| Paired rhythm/chord reference diagnostics | Six cached pairs, fresh ten, external beats and ensemble comparisons complete; 395 cache files hash-verified on Mac; tools and reports synchronized | [Fresh guitar rhythm](docs/FRESH_GUITARSET_RHYTHM_CHECK.md), [chord models](docs/FRESH_GUITARSET_CHORD_CHECK.md), [ensemble chords](docs/JAZZSAMBA_REFERENCE_CHECK.md), [neural beats](docs/BEAT_THIS_COMPARISON.md); cached rescoring needs `.venv-pilot`, fresh inference needs separate runtimes |
| Public web service | Not deployed | Hosting, authentication, storage and public launch are later work |
| Native macOS app | Not configured | The current Mac tool is a browser page plus local analysis scripts |
| Expo web product | Existing build fails | Missing `react-native-web-webview` in the YouTube wrapper; defer repair until product integration |
| Expo Android product | Bundle export passed | Device installation and live playback remain unverified |
| Expo iOS product | Existing project target; not verified/deployed | Defer device/build work until algorithm and practice results justify integration |

To restart the existing Mac setup, run `cd /Users/davidcrompton/Documents/music-os` followed by `.venv-analysis/bin/python experiments/analysis/lab.py serve`; the environment and demo are already created.

The experiment server binds to `127.0.0.1` only. It serves the bench and allowlisted experiment files, not the repository generally. It has no public hosting, uploads, accounts or background daemon. Generated audio, local recordings, results and analysis environments are gitignored. Restart the command after restarting the machine; a source push does not deploy a hosted service.

The completed continuation passes 309 distinct Python checks: 290 in the analysis environment and 19 separately with pinned evaluation dependencies. The written-bar report passed an independent code, source and metric audit. The previous 47 JavaScript helper checks remain applicable; these reference diagnostics change no player code. Rhythm metadata and the 20 suggested practice patterns are paired to exact recordings; raw detector charts and feedback identities remain unchanged. [Preparation evidence](docs/FIRST_TEN_PREPARATION.json) pins every new audio/chart hash. The completed reference caches (395 files, 275 MB) and research tools are synchronized to the Mac checkout. Saved scoring needs no model inference. The new separator runtime and outputs are still being prepared.

The Mac checkout contains the original three-song caches, conditional screens, NNLS evidence and legacy review windows. Expanded inputs/drafts use `experiments/generated/repertoire-first-ten-v2/` and playback uses `experiments/generated/automatic-first-ten-v1/`; the failed v1 preparation status is preserved separately. The player serves only its allowlisted audio/chart/evidence assets. Feedback persists in browser-local storage; download/copy is an optional backup, not a required step. `.venv-youtube` supports fresh imports, and native assets support NNLS extraction. Neural inference environments remain separate research setup; saved playback requires none of them. Restart each server after reboot.

## Existing Expo prototype

The prototype has hardcoded song cards, embedded YouTube playback and a sample chord animation. The animation uses unrelated data and an independent timer, so it is not the algorithm-testing interface.

```sh
npm ci
npm start
```

This is the old app startup path, not the Mac experiment setup above. Expo SDK 51 / React Native 0.74.5 need a compatibility check before current device deployment. Do not run `npm run reset-project`: it moves the existing app out of its routes.

## Next

No founder input currently blocks technical work. The fresh chord tests, neural beat comparison, nominal barline check, supplied-order ensemble diagnostic and first-ten source review are complete. The written-bar prototype completes eighteen runs on three new ensembles; its dependent nominal targets and early changes prevent a timing claim. The controlled separation comparison is now running; next then check exact-recording sections/shapes and measure correction effort. Popular-song canonical references remain a separate source-availability dependency. The broader real-reference/arrangement milestone remains an estimated 1.5–2.5 focused days, excluding unavailable-source waiting. Optional issue taps during normal practice can guide investigations; they are not accuracy labels. Later, the founder's ordinary playing and a two-week practice trial assess usefulness and enjoyment. Manual transcription is not required.
