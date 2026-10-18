# music-os

An affordable guitar practice companion, working toward a **band in your pocket** for people who usually play alone.

The initial Mac algorithm selection is complete: BTC for new basic-harmony drafts, CREMA for richer review, and tempo-guided librosa for approximate duration counts. Stage 2 is in progress: a developer review workspace prepares recording-specific checks and saves separate corrections. Recording acceptance and measured human correction effort remain outstanding; normal guitar practice follows. The older Expo app is a reusable UI prototype; iOS development and product integration follow the algorithm experiments.

## Current status

Updated 18 October 2026. Status and deployment information belong in this README as work progresses. The full roadmap is in [plan.md](plan.md); source findings and existing-app checks are in [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md).

**Live chord display timing, 17 October:** the founder reported a late D in Wild Thing. An isolated live check reproduced A remaining visible after the first saved D boundary: the last stale sample was about 159 ms after that boundary. Playback now refreshes from the actual audio clock on animation frames; the repeated pass had one stale sample about 2 ms after the boundary, followed by D at the next observed frame. This is a sampled display-lag comparison, not a latency guarantee or musical boundary validation. The founder subsequently identified the opening D around 4 seconds, the same cue used in that test; this is clarification of the earlier report, not a new post-fix audition. The saved D boundary remains 4.087 seconds: the earlier secondary estimate is not an independently verified musical onset. Native timings and every teaching guide remain unchanged. The normal player was refreshed with its paused position restored. [Verification and limits](docs/PLAYER_FRAME_CLOCK_CHECK.json).

**Latest player update, 17 October:** scrolling chords show compact estimated hold lengths, including half, full and multiple bars, with divisions measured from each chord's own start. The guitar-first path now recommends seven E-standard teaching setups; all ten recordings remain selectable and existing practice/feedback identities are preserved. Wild Thing displays the founder's reported A near 25 seconds as a provisional correction over the native 23.777–26.099-second E cue; raw E and unverified boundaries remain intact. Dylan's raw Am7 remains available, with Am in Core chords. [Duration/correction details](docs/PLAYALONG_RHYTHM.md), [path details](docs/PLAYALONG_LEARNING_PATH.md).

**House intro update, 17 October:** the founder confirmed E major and supplied Am–C–D–F / Am–E–Am–E. Two teaching sources agree. The player now inserts a provisional E at 7.988–9.474 seconds inside the long native Am hold, retaining Am on both sides, and displays E over the later native Em cue at 11.146–12.539 seconds. The first boundaries come from the paired secondary detector; neither interval is independently timed. Raw charts, the Wild Thing A correction and all storage identities remain intact. [Source/proposal record](catalogue/house-intro-feedback-20261017.json), [verification](docs/HOUSE_INTRO_FEEDBACK_UPDATE.json).

**Online chord checks, 18 October:** automatic catalogue preparation now searches primary teaching pages, extracts chord facts, normalizes capo/tuning and flags source-coverage, quality and short intro-order conflicts. The player has a separate **Online chord checks** panel with source status, assumed setups and replay buttons; native charts remain unchanged. Keyless search is best effort: blocked requests and insufficient source coverage remain visible, and saved source URLs supply a fallback. The final run has four comparable songs, four with insufficient sources and two riff exclusions; five replay hints concern House, with no confirmed-error count. The provider initially returned results but challenge-blocked all eight harmony searches in the final batch; cached search outcomes and seed sources are explicit. [Commands and limits](docs/ONLINE_CHORD_CHECKS.md), [verification](docs/ONLINE_CHORD_CHECK_RESULTS.json), [ticket #16](https://github.com/dcromp/music-os/issues/16).

**Wild Thing cache follow-up, 17 October:** an existing page still showed E at 25 seconds although a fresh live player showed A. Allowlisted HTML/scripts/styles/JSON now return current bytes with `Cache-Control: no-store`, including old conditional requests; audio range requests retain their existing behavior. The player has a visible **17 Oct update** marker. Existing open pages need one reload or a fresh tab. A fresh port-8070 tab was opened at 25 seconds and shows A. [Follow-up evidence](docs/PLAYER_CACHE_FOLLOWUP.json).

**Diagnostic checkpoint:** the all-ten automated timing/rhythm pass and remaining-six setup/pitch follow-up are complete. Ten developer drafts preserve notes and 19 provisional replay/search windows; physical musical acceptance remains open. [Per-song findings and reproduction commands](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md). The approved GitHub Issues workflow is configured with Matt Pocock's 27 repository-local skills. The [original-exercise content route](docs/ORIGINAL_EXERCISE_ROUTE.md) now specifies a three-exercise pilot, exact procedural input provenance, playback behaviour and separate setup/monthly budgets; paid launch remains on hold for the stated permissions, lesson and product gates. The [eight-ticket index](docs/agents/tickets.md) links the work.

**Ticket 3 status:** the [first-four recording assessment](docs/STARTER_FOUR_RECORDING_ASSESSMENT.md) now binds all 48 selected disagreement windows, 16 fixed samples and eleven specific claims to the saved audio. Input integrity and replay checks pass; **audible musical review remains blocked** by the absence of a capable reviewer or a matched independent reference. No excerpt is accepted, and the reviewed-pack ticket remains blocked. This pass did not perform a listening review; no founder transcription is required.

**Ticket board:** [All tickets](https://github.com/dcromp/music-os/issues?q=is%3Aissue) · [Ready for an agent](https://github.com/dcromp/music-os/issues?q=is%3Aissue+is%3Aopen+label%3Aready-for-agent+no%3Aassignee+-is%3Ablocked) · [Needs triage](https://github.com/dcromp/music-os/issues?q=is%3Aissue+is%3Aopen+label%3Aneeds-triage) · [Blocked](https://github.com/dcromp/music-os/issues?q=is%3Aissue+is%3Aopen+is%3Ablocked) · [Done](https://github.com/dcromp/music-os/issues?q=is%3Aissue+is%3Aclosed). GitHub is the source of truth for ticket state; this README keeps the status and deployment overview. [Workflow conventions](docs/agents/issue-tracker.md).

| Mac experiment step | Status | Remaining ETA / evidence |
|---|---|---|
| Initial algorithm evaluation / workflow selection | **Complete** | BTC + CREMA review alternative; original mix, guided librosa, authored drills; [decision](docs/ALGORITHM_SELECTION.md) |
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
| Separation and soft key/context pipeline | Default decision complete | Original mix retained; separation targeted only, key-conditioned relabelling deferred |
| Further research candidates | Deferred | Reopen only for a recurring catalogue failure that the selected workflow/review cannot handle |
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
| Expanded ten-song playback | Deployed and browser verified | All ten load cues, playback/seek and Core chords work; 48 served assets match canonical bytes; original 8068 retained |
| Chord hold lengths / estimated beats and bars | Player update, 17 October | Visible compact lengths and hold-relative divisions on the proportional strip; approximate pulse units with seconds fallback; [details](docs/PLAYALONG_RHYTHM.md) |
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
| Source-separation comparison | Complete; keep original mix as default | Nine fresh BTC runs plus three originals, 24 comparisons; 69.2→69.7% supported agreement, one input improves/two worsen; [results](docs/SEPARATION_CHECK.md) |
| Popular-song canonical reference matching | Bounded check complete; no verified pairs | Sixteen official objects, nine annotation hashes verified; all five master/time-origin correspondences remain unproven; [findings](docs/FIRST_TEN_REFERENCE_MATCHING.md) |
| Suggested practice path | Seven-step guitar-first selection, 17 October | E-standard teaching setups, next-song/drill suggestions, separate reversible progress and two riff guides. Love Me Do stays in the ten-song selector; exact recording tunings remain unchecked. [Details](docs/PLAYALONG_LEARNING_PATH.md) |
| Commercial song-access route | Concrete original-exercise design complete; paid launch on hold | Three planned drills; byte-reproduced procedural example; separate creation/recurring budgets and explicit unknowns. No lessons or public service deployed; [route and gates](docs/ORIGINAL_EXERCISE_ROUTE.md), [popular-song comparison](docs/SONG_ACCESS_FEASIBILITY.md) |
| Developer catalogue review workspace | Ready; ten source-backed drafts saved | Ten exact-audio worklists, separate corrections and actor-specific review timer; [guide](docs/CATALOGUE_CURATION.md) |
| First four pitch/source and targeted conflict checks | Complete diagnostic; two provisional label edits | Whole-recording main palettes compatible at proposed pitch; local ambiguity retained. Removing vocals changes two Dylan G/Gm comparisons; [results](docs/STARTER_FOUR_CATALOGUE_CHECK.md) |
| First four native timing / contrast queue | Complete review aid; physical timing still pending | 48 selected windows plus 16 fixed samples; two provisional Twist A-hold windows. Synthetic controls expose missed changes and noisy flags; [results](docs/STARTER_FOUR_TIMING_REVIEW.md) |
| All-ten timing/rhythm and remaining-six setup pass | Complete diagnostic; musical acceptance pending | 120 selected windows, 40 fixed samples, six new acoustic cases; full-mix attack detector rejected for automatic strumming. [Findings](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md) |
| Recording-specific catalogue acceptance / human correction effort | **Open; first-four audible review needs a capable reviewer or matched reference** | Four exact-input assessments and 64 queued replay spans recorded; zero accepted excerpts. Review ETA is unresolved until that route is available; human correction effort remains unmeasured. [Handoff and gaps](docs/STARTER_FOUR_RECORDING_ASSESSMENT.md) |
| Ordinary guitar usefulness trial | Pending | Normal practice and optional issue taps; two-week elapsed trial after representative arrangements are checked |

The synthetic suite compares the template baseline, BTC, CREMA, ChordMini/ChordNet and Chordino across clean triads, voicings/timbres, guitar-like attacks, distractors and timing/vocabulary complexity. ChordMini leads the original core metric including silence (94.7%) and boundary F1 (0.927); the baseline leads the new chord-only core metric (96.1%). Chordino scores 95.4% chord-only, with weaker silence and boundary handling. All audio in that suite is procedural; these are not real-song accuracy estimates. The [initial offline workflow](docs/ALGORITHM_SELECTION.md) is now selected; production catalogue acceptance remains outstanding. The founder's previous analysis code was deleted; the older Expo app only displayed hardcoded sample chords. See [app-readiness criteria](docs/APP_READINESS.md).

The real-guitar pilot changes the ranking: CREMA leads at **93.9% intended major/minor agreement** and 94.4% root agreement. BTC scores 84.0%, Chordino 82.7%, ChordMini 79.5% and the baseline 54.3% on intended major/minor. Eligible reference coverage is 98.1%; performed-quality comparisons have lower coverage and separate scores. Six acoustic performances are a diagnostic sample, not an accuracy estimate for arbitrary songs. No source separation or key assistance has been applied in this comparison; founder feedback does not contribute to these scores.

The [paired rhythm diagnostic](docs/RHYTHM_REFERENCE_CHECK.md) checks six cached recordings against nominal beat grids. The [fresh ten-input check](docs/FRESH_GUITARSET_RHYTHM_CHECK.md) is now complete: a public open-licensed archive mirror has an index identical to the official archive, and selected entries pass CRC/size and JAMS hash checks. Tempo guidance improves duration counts, while phase errors remain. No downbeats or physical chord boundaries are verified. Exact popular-song reference matching remains open.

The expanded player starts with complete automatic CREMA drafts for ten selected recordings; the original three-song player remains available. This existing pack retains its earlier CREMA primary and practice/feedback identity. New basic-harmony preparation now selects BTC with CREMA for review; both popular-song draft batches remain unscored. Chordino differences provide optional hints, without replacing primary chords or claiming that agreement proves correctness. The known-chart/NNLS experiments remain available separately: their cyclic drafts and bounded prefixes have not been accepted as verified arrangements. See [automatic preparation](docs/AUTOMATIC_DRAFTS.md) and [real diagnostics](docs/REAL_ALIGNMENT_DIAGNOSTICS.md).

The first qualitative feedback is promising: the player seems mostly correct, with Wonderwall's Em7/Dsus4/A7sus4/Cadd9 shapes a concern. CREMA cannot emit add9 or 7sus4; default Chordino lacks those and suspensions. The [richer synthetic comparison](docs/RICH_QUALITY_SCREEN.md) is complete: raw exact quality on rich progressions is 42.8% CREMA / 36.0% Chordino, versus 92.5% / 95.4% on plain controls. Given correct labels/order/count, spectral timing F1 is 100.0% and NNLS 96.5%; these are conditional procedural results. Deliberately upgrading plain chords to rich labels survives both rejection masks in all eight controls. The [full Wonderwall hypothesis](docs/WONDERWALL_GUIDED_DRAFT.md) also exposes wrong-order compression. Improve quality/section acceptance before promoting guided arrangements. Those research runs preserved raw predictions and did not promote a guided arrangement.

The [new guarded comparison](docs/ACCEPTANCE_SCREEN.md) freezes settings on development cases before 16 fresh synthetic recordings. Harmonic progress through silence is eliminated. The NNLS path reduces incorrect-label time on corrupt charts from 272.492 to 60.392 seconds while correct-chart harmonic quality remains 96.3%; neither result is real-song accuracy. The spectral guard loses too much correct harmony and is excluded from further guarded-arrangement consideration. Wrong chords and missing/extra repeats still survive, and short unknown gaps add display changes. Keep CREMA for current automatic drafts and NNLS as the guarded-alignment research candidate; whole-arrangement validation remains necessary.

The founder's beginner focus now has an optional **Core chords** display. Em7 becomes Em, Am7 becomes Am and Cadd9 becomes C; Dsus4 stays Dsus4, and A7sus4 becomes Asus4. Full chords remain the default. Adjacent identical core labels display as one interval, while gaps, silence and uncertainty stay visible. Saved charts, raw labels and feedback timestamps are preserved. The [48-output cached screen](docs/CORE_CHORD_SCREEN.md) shows which extension distinctions this easier task ignores; it does not improve the detector or establish substitute suitability. The [25-comparison structure diagnostic](docs/ARRANGEMENT_SCREEN.md) uses a chart-independent acoustic sequence, but still sometimes favours wrong repeats. No guided arrangement is promoted.

## Run on Mac

The experiment bench is a local browser tool, independent of the Expo app. Requirements: Python 3.12 and a browser; FFmpeg is needed only to convert other local recordings.

The canonical working checkout is `/Users/davidcrompton/Documents/music-os`, on branch `codex/online-chord-checks`, tracking `origin/codex/online-chord-checks` at `https://github.com/dcromp/music-os.git`. All further work runs from this folder. The [workspace move](docs/WORKSPACE_MOVE.md) records transferred assets, runtime repairs and verification. From the repository root:

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

Choose **Chord detail → Core chords** for the simpler view. The full chord name appears underneath when the Core display differs. This may change the sound; it is not a verified beginner arrangement. Choice stays with the song during the tab session and returns to Full chords after reload. Issue reports record the quality view used at the tap.

**Chord lengths** shows approximate beats/bars or seconds. Current and upcoming chords show lengths such as **~½ bar**, **~1 bar** or **~2 bars**. Scrolling blocks show compact numbers under an estimated-bars/beats legend; seconds keep their `s` suffix. Longer scrolling holds have internal divisions measured from the chord's own onset; these are duration units, not song bar lines. The strip scrolls horizontally on narrow screens. Clipped holds retain their full duration and show continuation arrows. The progress bar and timeline follow the audio clock and variable local pulse intervals. House uses a proposed 6/8 convention, while Wonderwall shows beats until the exact recording's local meter is verified. Counts outside the detected beat range fall back to seconds; no downbeats or numbered measures are inferred.

Wild Thing's **reported A near 0:25** is identified on screen and applied only to the exact paired native E span at 23.777–26.099 seconds. It is a provisional display correction, not a verified interval transcription. Feedback retains raw E, displayed A and the correction's provenance. A metadata/hash mismatch keeps the original chord. The local server supplies a SHA-256 header bound to the exact chart response bytes for browsers without WebCrypto; when available, browser WebCrypto computes the digest directly.

**Suggested strumming** gives count-and-arrow practice exercises. Start with the simple pattern and optionally choose the next one. D ↓ means down, U ↑ means up, and — means skip that stroke while keeping your hand moving. These are practice suggestions; the recorded parts may differ. [Details and evidence](docs/PLAYALONG_RHYTHM.md).

The [100-song pool](catalogue/rock-candidates.json) now has a [reviewed first-ten batch](docs/FIRST_TEN_REVIEW.md). All ten have automatic drafts; their proposed learning order and teaching shapes need recording/arrangement checks. The page shows chord cues, not riff instruction or a verified strumming lesson. Come As You Are uses studio D standard; Seven Nation Army distinguishes original Open A from a standard-tuning teaching adaptation. See the review before practising those riffs.

**Suggested practice path** gives a seven-song guitar-first order, a skill focus and a first drill. Its E-standard setups are teaching choices, not independently measured recording tunings. Love Me Do remains available in the ten-song selector; its saved progress is not deleted. **Use starting drill** brings its counts/arrows into view; **Try next** suggests an unpractised song. **Practised this step** is optional and reversible, saved separately from issue feedback in this browser. Reloading resumes the first unpractised available step; you can choose any song. The order is provisional and progress is a record of practice, not a skill assessment. Seven Nation Army and Come As You Are have separate riff-guide links. [Behavior and evidence](docs/PLAYALONG_LEARNING_PATH.md).

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

## Prepare catalogue arrangements

The [developer catalogue reviewer](http://127.0.0.1:8073/) uses the selected BTC/CREMA research pack to prepare arrangements; ordinary practice remains on port 8070. Its ten recording-specific worklists combine model disagreements, fixed samples that may contain shared errors, source-guided setup/rhythm checks and symbolically checked grip examples. These are investigation hints, not error counts or verified recorded voicings. [Workflow and evidence](docs/CATALOGUE_CURATION.md).

From the canonical checkout, start the prepared workspace with:

```sh
.venv-analysis/bin/python experiments/analysis/curation.py serve \
  --pack experiments/generated/catalogue-curation-20261014 --port 8073
```

Chord replacements, section markers and setup/rhythm notes save to separate model-exposed drafts. Explicit Start/Pause review sessions distinguish human review, agent work and QA; automated preparation and QA do not count as measured human correction cost. Checked replay windows do not accept an entire arrangement. Actual recording acceptance and human correction effort remain unmeasured, and no founder transcription task is required.

Drafts persist on this Mac under `experiments/generated/catalogue-curation-20261014/private-drafts/`. Revision checks prevent one tab silently overwriting another; **Export draft backup** provides an optional JSON copy. They remain separate from raw audio/charts and the normal player's practice progress and issue feedback. The workspace, audio and local drafts are Git-ignored. Restart its server after a reboot; pushing code does not deploy the server or transfer these local assets.

The [16 October timing pass](docs/STARTER_FOUR_TIMING_REVIEW.md) generates a separate native-change queue and contrast inventory from cached charts/evidence. It does not alter the reviewer's existing replay list. Twist and Shout's developer draft now has two provisional common A-hold search windows, with source-supported all-down eighths retained as a practice proposal. The second hold's native endings differ by 0.899 seconds. [Version 2 editorial proposals](catalogue/starter-four-curation-proposals-v2.json) preserve these windows and the earlier two Dylan label proposals; none is an approved lesson. All 64 cached synthetic controls and eight symbolic checks ran automatically: agreement misses shared clock errors, and 87/134 directly flagged primary points were already reference-correct. Keep this queue as review guidance, not an accuracy or acceptance gate.

The [all-ten follow-up](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md) now adds full-mix attack/energy measurements, source rechecks and setup-aware pitch diagnostics for the remaining six. Brown/Creep/House favour expected shift zero; Wonderwall favours +2 from capo-relative shapes. Both riff tracks stay outside triad scoring. Ten separate drafts now have notes and 19 provisional harmonic-search or coverage-replay windows, versioned in the [first-ten editorial backup](catalogue/first-ten-curation-proposals-v1.json). Batch entry adds no review timer sessions. The transient detector produces many extras and misses soft attacks in synthetic controls, so it is not used to transcribe guitar strumming, snap chords or approve lessons.

## Deployment

| Target | State | Start / stop |
|---|---|---|
| Mac experiment bench | Stopped; earlier live browser checks passed | Run `lab.py serve`; opens on localhost port 8067. Stop with Ctrl+C. Use `--port 8069` if needed; listening review uses 8068. |
| Original Mac automatic player | Stopped; earlier core/full and capo/sounding checks passed | Run `automatic_drafts.py serve --pack experiments/generated/automatic-playalong --port 8068`; stop with Ctrl+C. Reload an older tab to load the Core chords selector. |
| Expanded ten-song Mac player | Running on port 8070 with online source checks; normal paused Wild Thing position restored | Run `automatic_drafts.py serve --pack experiments/generated/automatic-first-ten-v1 --port 8070 --online-checks experiments/generated/online-chord-checks-20261017-final/report.json`; stop with Ctrl+C. [Preparation/restart details](docs/ONLINE_CHORD_CHECKS.md). Pack/feedback identities are retained; temporary 8071 is stopped. |
| Rich-chord / Wonderwall research | Tools and cached v2 results saved in the Mac checkout; hashes and 26 new checks verified | See [rich screen](docs/RICH_QUALITY_SCREEN.md) and [frozen Wonderwall CLI](docs/WONDERWALL_GUIDED_DRAFT.md). Recognition reruns need isolated model environments; cached diagnostics do not. |
| Guarded acceptance research | Frozen settings, 888 comparison outputs and six verified Wonderwall diagnostics saved on Mac | [Acceptance guide](docs/ACCEPTANCE_SCREEN.md) and [full-song check](docs/WONDERWALL_GUARDED_CHECK.md); existing native caches suffice, with no neural inference or player change |
| Core / structure diagnostics | 48 core and 25 structure comparisons complete; all cache input/outcome hashes verified on Mac | [Core screen](docs/CORE_CHORD_SCREEN.md), [structure screen](docs/ARRANGEMENT_SCREEN.md); `core-chord-screen-v1` and `arrangement-screen-v2` saved locally, with no model environments needed |
| Paired rhythm/chord reference diagnostics | Six cached pairs, fresh ten, external beats and ensemble comparisons complete; all research packs, model assets and runtimes transferred to the durable checkout | [Fresh guitar rhythm](docs/FRESH_GUITARSET_RHYTHM_CHECK.md), [chord models](docs/FRESH_GUITARSET_CHORD_CHECK.md), [ensemble chords](docs/JAZZSAMBA_REFERENCE_CHECK.md), [neural beats](docs/BEAT_THIS_COMPARISON.md); cached rescoring needs `.venv-pilot`, fresh inference needs separate runtimes |
| Selected BTC/CREMA research pack | Prepared and separately verified; used as immutable curation input | `experiments/generated/automatic-first-ten-selected-v1/`; temporary port8072 QA server stopped; [decision/replay](docs/ALGORITHM_SELECTION.md) |
| Developer catalogue reviewer | Stopped; earlier live QA verified, separate from the learner player | Run `curation.py serve --pack experiments/generated/catalogue-curation-20261014 --port 8073`; stop with Ctrl+C; [guide and QA evidence](docs/CATALOGUE_CURATION.md). Temporary reviewer QA servers are stopped. |
| Native timing / contrast review | Four-song and 64-case cached reports saved; two provisional A-hold windows in Twist's private draft | [Commands/results](docs/STARTER_FOUR_TIMING_REVIEW.md); cached analysis needs no neural inference. Full reports and screenshot proofs remain local; compact results and editorial proposals are versioned. |
| All-ten timing/rhythm follow-up | Final reports and ten provisional drafts saved; learner 8070 running, reviewer can be restarted | [Findings/replay](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md); diagnostic reports stay separate from immutable learner charts. |
| Original-exercise pilot | Design and provenance checks complete; no exercise pack deployed | [Specification](docs/ORIGINAL_EXERCISE_ROUTE.md); local original-input preparation can proceed, while paid launch waits for the listed permission, lesson and product checks |
| Public web service | Not deployed | Hosting, authentication, storage and public launch are later work |
| Native macOS app | Not configured | The current Mac tool is a browser page plus local analysis scripts |
| Expo web product | Existing build fails | Missing `react-native-web-webview` in the YouTube wrapper; defer repair until product integration |
| Expo Android product | Bundle export passed | Device installation and live playback remain unverified |
| Expo iOS product | Existing project target; not verified/deployed | Defer device/build work until algorithm and practice results justify integration |

To restart the existing Mac setup, run `cd /Users/davidcrompton/Documents/music-os` followed by `.venv-analysis/bin/python experiments/analysis/lab.py serve`; the environment and demo are already created.

The 18 October online-source integration passes 480 of 500 Python tests, with 20 optional skips, and all 153 JavaScript checks (91 player, 48 bench, 14 curation). All 41 native artifacts remain byte-identical. Player-v4 verifies 39 pins and ten selected cases; it inherits 38 v3 pins and versions only the optional server code pin. Existing build/comparison functions and all inference settings are unchanged. Historical v1/v2/v3 policies remain intact. The cached final report reproduces the five House hints without network access; all ten player states, replay, preserved corrections and source failure labels are browser-checked. [Evidence and coverage](docs/ONLINE_CHORD_CHECK_RESULTS.json).

The display-clock follow-up passes all 147 JavaScript checks (85 player, 48 bench, 14 curation), including six new frame/lifecycle regressions. All 39 current workflow pins, 41 cached assets and 48 learner routes still verify. It changes no Python source and does not rerun the preceding Python checkpoint. The temporary timing QA server is stopped; port 8070 remains running.

The cache follow-up passes 421 of 441 discovered Python tests, with 20 optional skips, and rechecks all 74 player JavaScript helpers. All 38 mutable learner routes return current bytes despite a future `If-Modified-Since`; 41 cached recording/chart/evidence artifacts and all 39 current policy pins remain unchanged. WAV byte ranges and private-route guards pass. The earlier 17 October result below remains the preceding UI checkpoint.

The experiment server binds to `127.0.0.1` only. It serves the bench and allowlisted experiment files, not the repository generally. It has no public hosting, uploads, accounts or background daemon. Generated audio, local recordings, results and analysis environments are gitignored. Restart the command after restarting the machine; a source push does not deploy a hosted service.

The historical 16 October checkpoint passed 416 of 436 discovered Python tests, with 20 optional-dependency skips. The all-ten follow-up added 30 regressions for setup/riff distinctions, attack/energy controls, exact chart targets and concurrent-input guards. All 124 JavaScript checks passed that day: 62 play-along, 48 bench and 14 curation. Its 45 reviewer assets, 48 learner assets and 39 frozen workflow pins passed. [Checkpoint evidence](docs/CATALOGUE_TIMING_RHYTHM_CHECK.json) preserves that result. Earlier optional evaluation/separation passes remain historical. Media, models, generated analysis and private session storage remain ignored; raw charts, practice progress and feedback identity are preserved.

**Earlier 17 October player verification:** 136 JavaScript checks (74 player, 48 bench, 14 curation) pass; 440 Python tests are discovered, with 420 passed and 20 optional-dependency skips. The explicit player-v2 audit verifies 39 pins and ten selected cases. Browser QA verifies the A cue at 25 s, Dylan Core Am/full Am7 at 47 s, seconds fallback, all ten song choices, Love Me Do outside the path, and feedback persistence/removal on an isolated origin. Default and narrow-screen geometry checks confirm proportional horizontal blocks, readable ordinary short-hold numbers and local horizontal scrolling without page overflow. Tiny clipped edge blocks retain complete tooltip/accessibility descriptions. All 41 cached learner manifest/audio/chart/evidence files remain byte-identical; all 48 public learner routes match disk. [Current verification record](docs/PLAYALONG_FEEDBACK_UPDATE.json) records the checks and local screenshot proofs. The 17 October v3 guidance policy kept 37 frozen inputs unchanged and versions only the learning/practice guide pins; v1 and the preceding player-v2 policy remain immutable historical evidence. The House follow-up passes 141 JavaScript checks and 421 of 441 Python tests, with 20 optional skips. Verify the current checkout with:

```sh
.venv-analysis/bin/python -B experiments/analysis/workflow_check.py \
  --policy experiments/fixtures/selected-workflow-player-v4.json
```

This guidance update changes no inference settings, native chart/audio bytes or beat grid, and does not accept a full arrangement. [Policy scope](docs/ALGORITHM_SELECTION.md).

The 16 October ticket-3 desk assessment verified the four exact audio/native-chart identities, draft snapshots and all 64 queued PCM slices, preserving their original selection. At that checkpoint, all 39 frozen pins passed and the 45 reviewer/48 learner public routes retained unchanged assets. These were integrity checks; no auditory observation, musical acceptance, fresh inference or full regression rerun was claimed. Existing packs/storage identities were preserved. [Versioned assessment](catalogue/starter-four-recording-assessment-v1.json).

The 16 October content-route design independently verifies source/asset hashes, byte-exact regeneration of `l3-pluck-036`, three chart schemas and matched cached prediction/audio identities. Its illustrative budget arithmetic is checked separately; no new inference, player change or full regression run was needed for these documentation/evidence changes. At that checkpoint, ports 8070/8073 listened locally; no new service or paid catalogue was deployed. [Route evidence](docs/ORIGINAL_EXERCISE_ROUTE.json).

The Mac checkout contains the original three-song caches, conditional screens, NNLS evidence and legacy review windows. Expanded inputs/drafts use `experiments/generated/repertoire-first-ten-v2/` and playback uses `experiments/generated/automatic-first-ten-v1/`; the failed v1 preparation status is preserved separately. The player serves only its allowlisted audio/chart/evidence assets. Feedback persists in browser-local storage; download/copy is an optional backup, not a required step. `.venv-youtube` supports fresh imports, and native assets support NNLS extraction. Neural inference environments remain separate research setup; saved playback requires none of them. Restart each server after reboot.

## Existing Expo prototype

The prototype has hardcoded song cards, embedded YouTube playback and a sample chord animation. The animation uses unrelated data and an independent timer, so it is not the algorithm-testing interface.

```sh
npm ci
npm start
```

This is the old app startup path, not the Mac experiment setup above. Expo SDK 51 / React Native 0.74.5 need a compatibility check before current device deployment. Do not run `npm run reset-project`: it moves the existing app out of its routes.

## Next

Work now follows the [GitHub ticket board](https://github.com/dcromp/music-os/issues). [#2](https://github.com/dcromp/music-os/issues/2) records the completed diagnostic checkpoint. Recording reviews are [#3–#6](docs/agents/tickets.md), the reviewed practice pack is [#7](https://github.com/dcromp/music-os/issues/7), optional guitar feedback is [#8](https://github.com/dcromp/music-os/issues/8), and the completed content-route specification is [#9](https://github.com/dcromp/music-os/issues/9). Its [original-exercise proposal](docs/ORIGINAL_EXERCISE_ROUTE.md) records the paid-launch hold and next evidence; the three teaching drills remain planned. Check native blockers before claiming a ticket. The new work-request and bug forms activate on GitHub after [PR #1](https://github.com/dcromp/music-os/pull/1) reaches the default branch; the live tickets, labels and dependencies are already available.

**Roadmap stage 1 is complete.** [Algorithm selection](docs/ALGORITHM_SELECTION.md) records the fixed offline workflow, alternatives and limits. Ten fresh BTC runs succeeded on the exact cached first-ten inputs: 2,024.1 seconds of audio in 36.1 seconds of batch processing with existing caches. A separate BTC/CREMA pack is prepared for research; the current ports 8070/8068 retain their existing charts and browser-local practice/feedback identities. The repeatable verifier checks model/settings/evidence pins and native byte preservation. [Completion evidence](docs/ALGORITHM_SELECTION_RESULTS.json).

**Stage 2 is in progress:** all ten have recording-bound diagnostic findings, notes and focused search windows. The [checkpoint](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md) records why full-mix transients cannot establish guitar contacts. [Ticket 3's bounded assessment](docs/STARTER_FOUR_RECORDING_ASSESSMENT.md) now records the first four's exact spans and unresolved musical claims; it remains open because this session has neither a capable audio-listening reviewer nor a verified reference mapping. A capable review or proven reference must supply actual evidence before ticket 7 can publish reviewed excerpts. Physical acceptance and human correction cost remain unmeasured; no founder transcription is required. There is no defensible musical-review completion ETA until that route is available. Ordinary practice and optional feedback follow; product/iOS integration remains later work.
