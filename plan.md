# Guitar learning app → Band in your pocket

Project plan · Updated 17 October 2026 · Working title

**Execution:** [GitHub Issues](https://github.com/dcromp/music-os/issues) is now the ticket board. The [initial eight-ticket index](docs/agents/tickets.md) links the completed checkpoint and remaining work with native dependencies. `AGENTS.md` and `docs/agents/` configure the approved Matt Pocock skills workflow; this plan remains the high-level roadmap, and README remains the status/deployment overview.

**House/source integration follow-up on 17 October:** the founder-confirmed E-major intro and two teaching sources now inform a provisional player correction: insert E near eight seconds inside a long native Am hold, then show E over the later Em cue, retaining raw predictions. Timing proposals are not verified boundaries. [Source/proposals](catalogue/house-intro-feedback-20261017.json), [verification](docs/HOUSE_INTRO_FEEDBACK_UPDATE.json). Online source research was implemented as agent work and saved metadata; automatic source discovery/consensus was never connected to the player. Make that connection a catalogue-preparation priority rather than relying on the founder to discover each wrong cue. Current workflow verification uses player-v3; preceding policies remain historical.

**Player feedback update on 17 October:** [visible chord lengths](docs/PLAYALONG_RHYTHM.md) now distinguish approximate half/full/multiple-bar holds on the scrolling strip, with divisions anchored to each original chord onset and variable local pulse intervals. They do not establish song bar lines or physical change timing. The founder's Wild Thing A near 25 seconds is a separate provisional display correction over the native 23.777–26.099-second E span; raw E and its boundaries remain unchanged. Dylan retains raw Am7, with Am in Core. The [guitar-first path](docs/PLAYALONG_LEARNING_PATH.md) now recommends seven E-standard teaching setups; Love Me Do remains in the ten-song selector, retained steps keep their progress, and recording tuning is not independently verified. The explicit player-v2 workflow policy versions only the two guide pins, with 37 frozen inputs unchanged. This practical feedback does not complete ticket 3 or accept an arrangement. Validation passes: 136 JavaScript checks, 420 Python checks and 20 optional skips, plus default/narrow browser QA. [Current evidence](docs/PLAYALONG_FEEDBACK_UPDATE.json) and README hold deployment details.

**Content-route specification on 16 October:** [the original-exercise pilot design](docs/ORIGINAL_EXERCISE_ROUTE.md) and [provenance/budget record](docs/ORIGINAL_EXERCISE_ROUTE.json) resolve [the route-design ticket](https://github.com/dcromp/music-os/issues/9). The first candidate paid route is three short project-authored drills, illustrated by a byte-reproduced nine-second procedural control with no imported media. The three lessons are not yet produced or accepted. Keep authoring/review costs separate from monthly hosting, content, payment and support costs; all unquoted grants/fees remain unknown. Proceed with local preparation, hold paid release until the specified permission, musical, player and operating gates pass. This does not replace the existing popular-song catalogue review or authorize vendor contact/public deployment.

**Ticket 3 assessment on 16 October:** [the first-four evidence handoff](docs/STARTER_FOUR_RECORDING_ASSESSMENT.md) preserves all 48 selected windows, 16 fixed samples and eleven unresolved claims with exact audio/draft identities. It verifies inputs and replay slices, not auditory correctness. Ticket 3 stays open and the reviewed-pack gate stays blocked: this session has no capable audio reviewer or matched independent timing reference. No new arrangement or boundary is accepted, human correction effort remains unmeasured, and no founder transcription is assigned. Resume with capable exact-file review or a validated canonical-audio reference mapping; musical completion has no reliable ETA until that route exists.

**Project repository:** [dcromp/music-os](https://github.com/dcromp/music-os). The 10 October 2026 [reuse audit](docs/REUSE_AUDIT.md) found an Expo/React Native YouTube play-along prototype. Preserve its useful UI for later product integration. **The initial Mac algorithm evaluation is complete:** BTC for new basic-harmony drafts, CREMA for richer review, original-mix processing and tempo-guided librosa. Use offline analysis and the local play-along bench. Stage 2 review preparation and correction tooling are implemented; exact catalogue acceptance, measured human correction effort and normal guitar usefulness checks remain outstanding. Repairing the Expo app or developing iOS is not a prerequisite. Audio separation, chord detection, learning paths and accompaniment are new work; the founder's previous analysis workflow is not in the inspected repository.

## 1. Vision and first product

**Long-term vision:** make playing guitar alone feel like playing with a band. Serve people who lack nearby musicians, compatible schedules, or the confidence to join a group. Success means they pick up their instrument more often, enjoy playing, and improve through making music.

**First product:** an affordable song-based guitar practice app that shows useful chords and rhythm guidance, then recommends what to play next. Start with rock and with players who know some chords but need help progressing.

**Catalogue strategy:** work toward a curated few hundred rock/pop titles, beginning with a smaller reviewed learning path. For known songs, use comparable chord/key references plus audio verification, then align the reviewed sequence to a specific recording. Prioritise reliable timings and affordable one-time curation; keep free chord recognition as a control, verification signal and fallback.

**Beginner arrangement strategy:** prioritise reliable core harmony, usable timings and playable transitions before exhaustive extensions. Offer Full chords and an explicitly labelled Core chords view: m7 → minor, 7/maj7/add9 → major, 7sus4 → sus4. Preserve major/minor, suspensions, diminished/augmented/power distinctions, and slash bass. Removing an extension can simplify the chart but does not necessarily simplify the fingering; Wonderwall's shared-finger richer shapes may make transitions easier. Choose a small first learning path with reviewed guitar shapes and difficulty based on actual transitions, rhythm and tempo. Keep raw recognition and richer arrangements for later progression toward accompaniment. As of 12 October, the Mac player has visible chord hold lengths, progress and a proportional timeline so one short change is distinguishable from a chord held for several beats. Automated beat tracking can provide approximate duration units after pulse-level and meter checks; never infer verified downbeats or snap raw chord changes to a grid. Two suggested count/arrow strumming drills per song are deployed as separate practice arrangements, with simple starts and optional next patterns. [Implementation, sources and checks](docs/PLAYALONG_RHYTHM.md) record approximate pulse/meter assumptions and the synthetic sanity test. Match the original guitar part and section-specific rhythm later; use 6/8 exercises for House and preserve uncertainty around Wonderwall's local meter.

**Repertoire progress on 12 October:** [100 candidate titles](catalogue/rock-candidates.json) use public Hal Leonard lists: 50 electric-rock titles, the 49 actually displayed titles from the three-chord rock collection, and Wonderwall from the strumming collection. [Source notes](docs/CATALOGUE_SEED.md) preserve the count discrepancy and distinguish publisher membership from original-recording chords. The [first-ten review](docs/FIRST_TEN_REVIEW.md) selects exact uploads and teaching proposals; ten recordings are prepared and 20 raw charts are available. Eight inputs are new, including a label-distributed Animals version; Creep and Wonderwall reuse exact cached audio/charts. The old House tribute remains separate. Proposed rhythm and riff tracks account for Creep's barres, Wonderwall's shared fingers/rhythm and original versus adapted tunings. These are provisional placements, with no verified timed arrangements or publisher difficulty ranking. Expanded local playback is deployed and verified on port 8070; the latest algorithm-selection run passes 319 analysis checks, with 20 optional-dependency skips (339 discovered). [Independent annotation candidates](docs/FIRST_TEN_REFERENCE_CANDIDATES.json) exist for five songs but canonical-master/time-origin matching remains open. Next check recording-compatible shapes/rhythm/sections and independent real references; estimated 1.5–2.5 focused days excludes source-host waiting and includes about half a day for first-ten arrangement review. The founder does not need to transcribe songs.

The Mac bench implements the [provisional seven-step guitar-first rhythm path](docs/PLAYALONG_LEARNING_PATH.md): skill focus, existing starting drill, next unpractised song and optional reversible browser-local practice progress. Its E-standard teaching setups do not verify exact recording tuning. It resumes only during untouched initial loading, keeps all ten songs directly selectable, and separates riff guides and issue feedback. The 17 October selection-only update preserves path/revision and retained step identities; Love Me Do's saved data is not deleted. This supplies a structured workflow for normal practice without claiming validated difficulty, mastery or verified recording arrangements. The original eight-step implementation's 62 helper checks and browser evidence remain historical; current verification belongs in the README.

**Stage 2 progress on 14 October:** the [developer review workspace](docs/CATALOGUE_CURATION.md) prepares ten exact-audio worklists, source checks and symbolic grips, and saves corrections separately from raw charts. The [first-four pass](docs/STARTER_FOUR_CATALOGUE_CHECK.md) corroborates teaching palettes/variants and compares all twelve uniform pitch shifts using spectral and NNLS evidence. All four favour the proposed main palette on whole recordings; local ambiguity prevents setup or accuracy claims. A controlled Dylan separation test changes two G/Gm comparisons after vocals removal, with preprocessing and matched-support controls independently reproduced. Four source/rhythm note drafts and two provisional G-label replacements are [versioned editorial proposals](catalogue/starter-four-curation-proposals-v1.json); their bounds remain native predictions and nothing is promoted to ordinary playback. Explicit actor sessions measure UI draft entry only, excluding research and analysis; no human correction-cost estimate exists. **Recording acceptance, physical timing/sections and actual human effort remain unmeasured; Stage 2 is not complete.** The current run passes 368 of 388 Python tests (20 optional skips) and all 124 JavaScript checks. Ports 8070/8073 remain independent. Next verify the first four's changes/contrast/rhythm cues and continue the remaining recordings; estimate 1.5–2.5 focused days excluding source waiting, with no founder transcription task.

**Stage 2 continuation on 16 October:** the [native timing/contrast review](docs/STARTER_FOUR_TIMING_REVIEW.md) pairs directed changes without moving either model's timestamps. The first four yield 152 candidate replay windows, 48 selected windows and 16 retained fixed samples. Two common A-hold intersections are saved in Twist and Shout's separate draft as provisional search windows, with an unresolved 0.899-second ending difference. [Version 2 editorial proposals](catalogue/starter-four-curation-proposals-v2.json) preserve these and the earlier Dylan edits. All 64 cached synthetic cases and eight symbolic controls ran before any guitar assignment; replay windows cover 49/52 primary error/extra points but only 16/40 operational misses, and 87/134 directly flagged points are reference-correct. Shared +300 ms clock errors remain invisible to agreement. Use this as review guidance; no arrangement is accepted or human correction effort measured. The latest regression run passes 386/406 Python tests (20 optional skips), all 39 frozen pins, and unchanged served assets; 124 JavaScript checks passed earlier the same day. Next inspect actual contrast/rhythm/uncertain-change windows and continue remaining recordings, without retuning models on these exposed outcomes or reopening the completed algorithm tournament. Estimated remaining catalogue work stays 1.5–2.5 focused days, excluding source waiting, not a promised unattended deadline. No founder transcription is required.

**All-ten checkpoint on 16 October:** the [timing/rhythm and remaining-six pass](docs/CATALOGUE_TIMING_RHYTHM_CHECK.md) is complete as automated diagnostics. The native inventory retains 120 selected windows and 40 fixed samples; ten separate drafts now contain 19 provisional search/coverage windows. Brown/Creep/House favour expected shift zero in both acoustic methods, while Wonderwall favours the expected capo-2 shift +2. Riff material stays outside triad scoring. Synthetic attack/energy controls distinguish damp from ringing, but expose substantial false transients and missed soft attacks; the detector is excluded from automatic strumming transcription or chord-time refinement. Thirty new regressions pass, with 416/436 Python tests passing and 20 optional skips. Musical timing/sections, recorded guitar contacts and human correction effort still require a capable recording review or matched independent references. Preserve this work in a committed checkpoint and track the remaining bounded work through the requested GitHub Issues setup.

The founder is the first test player. His own guitar sessions will guide early algorithm and interface decisions. Broader testing will follow: a tool that works for one player is promising evidence, not proof of a market.

The first product should stand on its own. Customers should get a worthwhile practice companion even if the full band experience takes years to develop.

**Initial promise:** “Play songs you like, with chords and strumming you can follow, and a clear next step.”

## 2. Starting assumptions

| Assumption | Status | How to resolve it |
|---|---|---|
| Audio can be separated and analysed for chords | The founder has already done this; useful starting evidence | Reproduce the workflow and benchmark how reliably it supports actual playing |
| A Chordify-like service can operate commercially | Existing product demonstrates a market implementation | Investigate available sourcing, permissions, commercial terms and costs for our implementation |
| Chordify pays YouTube a small amount per video | Speculation; not a verified commercial arrangement | Do not put this into the financial model as a fact; obtain actual terms or choose another supported route |
| Structured progression and rhythm guidance improve practice | Core product hypothesis | Compare guided sessions with the founder's current workflow, then run an external pilot |
| Users will pay around $4–6/month | Proposed price test, informed by the user's quoted competitor prices | Test payment and renewal after users experience the product |
| Chord analysis can become the foundation for a virtual band | Plausible technical direction | Reuse song timing, harmony, sections and rhythm data; validate accompaniment separately |
| Reviewed chord/key references make curated songs primarily an alignment task | Research-supported direction; local benefit and source availability unmeasured | Test chart-assisted alignment against audio-only recognition, including wrong/capo/edited references; measure timing and review cost |

Technical experimentation and commercial sourcing are separate workstreams. Continue useful experiments while investigating the latter. Do not treat an unverified rights arrangement as an engineering blocker for every experiment, or technical feasibility as confirmation of permission to launch.

## 3. Target user and scope

Start with adult beginners and returning guitarists who enjoy rock, know several chords or basic power chords, and usually practise alone. They can follow simple instruction but struggle with selecting suitable songs, keeping rhythm, or knowing whether they are progressing.

The first release supports one coherent learning path and a small, reliable catalogue. Choose acoustic rhythm or electric rhythm as the first emphasis during the founder's initial sessions; avoid trying to cover both comprehensively at launch.

Include:

- Chords aligned to playback, with the next change visible early enough to prepare.
- Simple strumming guidance, with audible original demonstrations.
- Clearly labelled simplified arrangements and more demanding variants.
- Short practice sessions and recommendations based on skills and musical taste.
- Section practice and count-ins where the playback source supports them.
- Fast correction and feedback tools for the test player and content reviewer.

Defer full courses for absolute beginners, exhaustive song coverage, solos and note-perfect tabs, live multiplayer, automatic performance grading, and accompaniment that follows the player in real time.

## 4. Phase 0 — Audit and Mac experiment setup

**Initial inspection completed on 10 October 2026.** [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md) records evidence and component decisions at commit `0083861`. The existing app has no configured native macOS target. Its browser build, the potential Mac access route, currently fails. Live app playback and guitar testing remain unverified. These findings inform later product integration; they do not block Phase A's independent algorithm bench on Mac.

What exists:

- Expo SDK 51 / React Native 0.74.5 with Expo Router, theme utilities, seven hardcoded song cards, an embedded YouTube wrapper and a chord/beat/bar display.
- The active flow is Songs → `app/screens/SongPlayer.js`. The separate Player tab, Profile and Tutorial are placeholders; login/signup simulate navigation.
- A preliminary Song type includes timed chord intervals, but the display always loads sampleSongData instead of the selected song. It ignores the sample's timestamps and runs on its own fixed-tempo timer. At 120 BPM it advances a chord every two seconds despite sample intervals of 15 seconds.
- Two unused hooks sketch player-state and clock synchronization. They need consolidation and correction before use; one expects numeric states while the installed wrapper supplies string states.
- No implemented audio import, analysis pipeline, persistence, strumming, recommendation or band engine. Earlier player code inspected in history does not supply those missing capabilities.

Verification: locked dependencies install, TypeScript passes and the sole starter snapshot test passes. Android bundle export succeeds. Web export fails because the iframe wrapper imports missing `react-native-web-webview`. These checks do not validate live playback or chart accuracy; the JavaScript core also lacks checkJs coverage.

**Reuse decision:** keep the app shell, song cards and player composition as candidates for Phase B. Defer route cleanup, Expo upgrades, YouTube web repairs and iOS/device work until the algorithm experiment supplies useful results. Build new offline analysis tooling and a versioned output format in music-os now. The old app's free-running sample animation must not be used to judge model accuracy. The founder confirmed that his prior analysis code was deleted; establish a fresh baseline.

Phase 0 now includes the experiment foundation as well as the completed code audit. Keep its step/status/ETA table, startup instructions and deployment state in the root [README.md](README.md). Its deliverables are an isolated Mac environment, versioned JSON format, known-chord fixture, a cheap baseline with measured output, a minimal local browser play-along bench and a reproducible run guide. Validate the bench clock before trusting guitar ratings. Synthetic results establish plumbing only; Phase A chooses algorithms using real material and held-out tests.

**Current evidence:** Phase 0's technical foundation is implemented. The expanded automated Phase A screen has completed 64 synthetic cases for each of five algorithms (320 successful comparisons), including the project-local Chordino Mac build. Results and limitations are in [docs/SYNTHETIC_RESULTS.md](docs/SYNTHETIC_RESULTS.md). The [six-recording annotated real-guitar pilot](docs/GUITARSET_PILOT.md) completed all 30 model runs and reverses the synthetic ranking: CREMA leads intended major/minor agreement at 93.9%, followed by BTC 84.0%, Chordino 82.7%, ChordMini 79.5% and baseline 54.3%. This small acoustic dataset has lead-sheet-derived roots/boundaries and different eligible quality coverage; it is not a general app accuracy claim. Per the founder's sequencing preference, automated screening and reference checks precede guitar sessions.

**Curated-song progress:** a separate Python yt-dlp importer successfully acquired Creep, Wonderwall and House of the Rising Sun from the old song list, with prepared-audio hashes and source records. Baseline, CREMA and Chordino completed nine smoke runs. The new known-chart aligner completed 64 conditional synthetic timing cases at 90.4% mean boundary F1 within 150 ms, with 59 extra and one missed boundary. This score assumes correct ordered harmony and does not measure recognition. Its first full-recording Creep cyclic draft over-repeats and remains unaccepted. Next review exact excerpts, sections and repeats, then annotate timing independently. [Import evidence](docs/YOUTUBE_IMPORT_SMOKE.md), [alignment results](docs/ALIGNMENT_SCREEN.md) and [setup](docs/CHART_ALIGNER_SETUP.md) preserve the distinction.

**Current implementation:** explicit finite sections/repeats, NNLS acoustic evidence and the paired synthetic comparison are implemented. NNLS scores 98.4% conditional boundary F1 versus 90.4% spectral, with timing tradeoffs; the full Creep cyclic drafts remain unaccepted. The default experience now uses complete automatic CREMA drafts, with Chordino differences as optional hints. Charts appear immediately, and a one-tap issue button captures/saves playback time. The founder's role is to play and report moments that feel wrong, without manually naming or timing chords. The older short windows and manual editor remain optional research tools. [Automatic workflow](docs/AUTOMATIC_DRAFTS.md), [automated evaluation](docs/DRAFT_SCREEN.md), [paired results](docs/ACOUSTIC_ALIGNMENT_COMPARISON.md) and [reference research](docs/REAL_REFERENCE_SOURCES.md) separate usefulness feedback from scientific validation.

**First founder feedback:** the player seems mostly correct; Wonderwall's Em7/Dsus4/A7sus4/Cadd9 shapes may be the trickiest part. This is qualitative feedback without independently checked timing or quality labels. The [vocabulary audit](docs/WONDERWALL_QUALITY_AUDIT.md) confirms CREMA cannot emit add9/7sus4 and default Chordino cannot emit suspensions or add9. The bounded rich-quality screen and chart-assisted comparison are now complete: voiced m7/sus4/7sus4/add9, shared upper notes, strummed attacks, capo conversion and plain-triad negative controls. Exact quality and unsupported-vocabulary coverage sit beside root/major-minor/timing metrics. Preserve raw outputs and keep founder transcription optional; findings and the next dependency are below.

### Phase A — Choose algorithms on Mac and build the guitar testing bench

**Roadmap stage 1 completed on 13 October.** [Decision](docs/ALGORITHM_SELECTION.md) and [completion evidence](docs/ALGORITHM_SELECTION_RESULTS.json) select BTC for new basic-harmony drafts, CREMA for richer review, original mixes, the existing guided librosa pulse tracker and authored practice drills. The new ten-song BTC batch succeeds without claiming accuracy on unmatched popular-song references. Model selection is explicit and fixed; no automatic voting, confidence-based switching, numbered bars or unaccepted chart alignment enters the default workflow. Existing CREMA playback packs remain intact.

Split the broader Phase A exit into three explicit milestones: **A1 / roadmap stage 1: offline algorithm selection (complete); A2 / stage 2: recording-specific catalogue acceptance and actual correction effort (in progress; review tooling complete); A3 / stage 3: ordinary guitar followability and usefulness (pending).** Correction time and play-test evidence have not been measured by benchmark scores, so the full product-readiness gate is not passed. This closes the initial model tournament; reopen a method only for a concrete recurring catalogue failure.

**12 October automated real-reference work expanded:** the [six cached pulse/count diagnostic](docs/RHYTHM_REFERENCE_CHECK.md) is followed by [ten fresh exact guitar pairs](docs/FRESH_GUITARSET_RHYTHM_CHECK.md), acquired through an index/CRC/hash-verified public archive mirror after official host failures. Guided holdout duration-count error falls 1.245→0.097 beats, while phase remains uneven. [Fifty fresh chord-model runs](docs/FRESH_GUITARSET_CHORD_CHECK.md) separate four comping performances from six solos; intended comping agreement is BTC 92.0%, Chordino 88.3%, ChordMini 87.1%, CREMA 86.3%, baseline 58.3%. Contextual harmony recovery from solos remains weak. [Three publisher-paired jazz ensembles](docs/JAZZSAMBA_REFERENCE_CHECK.md) add a five-model retrospective comparison: BTC 69.2%/CREMA 64.9% supported-chart major/minor agreement at 83.8% coverage. Written chart targets are not note-level performed harmony. No universal winner or full-rock accuracy claim follows.

**Rhythm candidates and arrangement work:** [three external beat challenges](docs/MIXED_RHYTHM_REFERENCE_CHECK.md) expose variable-tempo weakness; [two neural checkpoints](docs/BEAT_THIS_COMPARISON.md) complete 36 runs over 18 inputs, including five newly frozen challenges. Small0 helps piano phase but duration counts still need tempo-level conventions. Native endpoint extras remain charged, and downbeats are not promoted. [All-ten teaching-source follow-up](docs/FIRST_TEN_ARRANGEMENT_CHECK.md) supplies concrete swing/mute/build-up/retuning/section tasks; exact-upload timings and correction cost remain unmeasured. The separate [nominal barline diagnostic](docs/NOMINAL_DOWNBEAT_CHECK.md) is complete: six experiment holdouts score 65.4% / 63.6% F1 at 70ms, with too many extra starts for numbered bars. [Twelve supplied-order ensemble alignment runs](docs/JAZZSAMBA_ALIGNMENT_CHECK.md) also complete; agreement falls from 61.9% to 33.7% under the existing guard, so that guard is unsuitable as the default ensemble lesson pipeline. The [written-bar prototype](docs/BAR_CHART_ALIGNMENT.md) completes eighteen runs on three newly selected ensembles, withholding annotated recording seconds. Its 86.8% / 86.0% main-chord agreement is conditional: the nominal scoring grid is constructed from the same supplied BPM and coordinates. Audio-selected source-grid changes are consistently 158–188 ms early and miss all 109 changes at 150 ms tolerance; corrupted charts also retain cues. These outputs remain unaccepted. The [source-separation comparison](docs/SEPARATION_CHECK.md) completes three separation runs and nine fresh BTC runs, including a separately frozen resampling-only control. Supported agreement rises only 69.2→69.7%, with one excerpt improving and two worsening; keep original-mix processing as default. This retrospective instrumental-jazz check does not test guitar isolation or general rock accuracy. The [popular-song matching check](docs/FIRST_TEN_REFERENCE_MATCHING.md) pins sixteen official objects/nine annotations but proves no corpus master/time-origin correspondence, so those five songs remain unscored. [Status](docs/SEPARATION_CHECK.md) is preserved after all source, assets and runtimes were transferred into the durable `Documents/music-os` checkout. [Workspace details](docs/WORKSPACE_MOVE.md) record the canonical repository, remote branch and verification. Frozen earlier policies stay unchanged. Later normal guitar sessions and the two-week practice trial supply usefulness/enjoyment evidence separately from accuracy scoring.

**11 October bounded rich-quality comparison complete:** [24 richer/plain/contrast fixtures and 224 successful comparisons](docs/RICH_QUALITY_SCREEN.md) show strong conditional timing when correct harmony is supplied, but both rejection masks retain all forced rich upgrades on eight plain controls. Raw rich-progression exact quality is 42.8% CREMA / 36.0% Chordino; procedural results are not full-mix accuracy. [Six frozen Wonderwall runs](docs/WONDERWALL_GUIDED_DRAFT.md) also complete reversed section order with low mismatch, consuming many positions in silence. Keep that full-song hypothesis unaccepted. The guarded comparison below addresses local quality evidence and silent progression; whole-arrangement compatibility and independently checked real excerpts remain outstanding. Cache accepted teaching arrangements separately from raw predictions; founder transcription remains optional. Broader reference/holdout work remains planned at 1.5–2.5 focused days, with whole-arrangement acceptance still an explicit dependency.

**Guarded acceptance implemented and screened:** [888 completed attempts](docs/ACCEPTANCE_SCREEN.md) compare the frozen baseline with four declared development settings and a policy frozen before previous-holdout/fresh validation. The new decoder counts supporting active evidence for dwell and cannot traverse harmonic positions in silence; quality conflicts become unknown rather than invented corrections. Fresh NNLS corrupt-chart wrong seconds fall 272.492→60.392, with 96.3% correct-chart harmonic quality. The spectral guard fails the predeclared retention constraint on fresh cases and is excluded from this guarded candidate path. All-corrupt-chart rejection remains false; missing/extra repeats and short N/X fragmentation remain open. Keep the NNLS guard as a research candidate, test recording-specific structure and presentation/abstention independently, and use existing annotated recordings/version-matched references before learner-facing promotion. CREMA raw drafts remain the default; no new founder transcription assignment.

**Full-song guarded check complete:** [six Wonderwall runs](docs/WONDERWALL_GUARDED_CHECK.md) reuse the exact prior charts/audio/features and frozen policy, with no retuning. All have zero silent harmonic progress; reversed-order NNLS leaves 15 positions unvisited, while the guided NNLS retains 71.9% of total duration as labels. This is coverage, not accuracy. Wrong charts still retain substantial labels and compressed active progression; retain these as unaccepted research artifacts. Next prioritise whole-arrangement compatibility for counts/sections and usable unknown-span presentation, then representative annotated/version-matched real excerpts. Broader real-reference work remains estimated at 1.5–2.5 focused days; do not spend that stage retuning on already exposed validation outcomes.

**Beginner/core and structure continuation complete:** the optional core display is implemented and QA browser checks pass. The [48-output retrospective comparison](docs/CORE_CHORD_SCREEN.md) gives CREMA 61.0% exact / 73.8% core quality and Chordino 61.5% / 72.8%, with the original detector bytes/timings unchanged. Suspension/third and root errors remain; a reduced vocabulary is an easier task, not an accuracy upgrade. Display-only merging removes redundant adjacent core labels without filling N/X or temporal gaps. Feedback preserves the raw label, played shape and selected quality mode.

The [whole-sequence diagnostic](docs/ARRANGEMENT_SCREEN.md) completes 25 cached comparisons, verifies global acoustic argmax is independent of supplied order, and preserves raw and predeclared 150ms stable-run views. Correct section charts have the lowest stable edit distance in 3/4 procedural recordings; extra repeats win the fourth. Raw sequences fare worse. CREMA and Chordino favour a deliberately simplified Wonderwall chart, reflecting vocabulary limits rather than verifying an arrangement. Do not use edit-distance rank or endpoint completion as an acceptance gate. Next use representative annotated/version-matched recordings and bounded rhythm/beat-aware structure work on separate development material. No threshold fitting on these exposed cases; all guided charts remain unaccepted. Broader real-reference work remains 1.5–2.5 focused days, without compulsory founder transcription.

**Indicative effort: 1–2 focused weeks.** These are planning estimates for a solo builder, not delivery commitments.

Extend Phase 0's fresh baseline; the prior workflow was deleted. Put additional offline analysis tooling behind command-line adapters that emit the shared versioned JSON format with recording identity, explicit timestamp units, chord intervals and available beat/section data. Run it on the founder's Mac in the isolated environment. Record macOS version, CPU/architecture, memory, runtime and model versions, inputs and failures. Default to CPU for comparability and check optional Mac acceleration per candidate. Do not assume CUDA or that every model already supports Apple acceleration.

Select 12–20 test tracks or excerpts across clean acoustic guitar, distorted rhythm guitar, sparse and dense mixes, slow and fast changes, open chords, power chords, and rhythmically awkward passages. Use recordings with a suitable permission basis for the experiment; include original recordings with known chords and timing. Keep a source and permission record for each item.

Start by producing machine-readable chord results, timeline plots and metric summaries. Add only the interface needed for the founder to judge them with a guitar: a small locally served browser page on Mac that plays the same local audio, displays imported timestamped chords, switches analysis versions and records ratings. Keep this bench separate from Expo, with a documented local startup command and no dependency on the existing YouTube wrapper. It is experiment tooling, not the production app or a native macOS app.

Validate the clock with synthetic timelines and already annotated material. Highlight from the audio element's current playback time; handle pause/resume, seek and replay, and preview future chords separately. Keep the source file matched to its chart. Give the founder automatic drafts to play with, capturing the current moment when he reports a problem. Detailed annotation is an optional specialist/reference task, not a prerequisite for trying the app. Defer account flows, mobile builds and broader app repairs.

Compare these approaches with identical inputs and hardware:

| Experiment | Question |
|---|---|
| Simple chroma/template baseline | How far does a cheap, explainable chord detector get us? |
| Pretrained chord-recognition model | Does it materially improve useful chord labels and timing? |
| Full mix versus separated harmonic/instrument stems | Does separation improve recognition enough to justify processing cost and artefacts? |
| Raw chord output versus soft key/context assistance | Can likely key and neighbouring chords resolve uncertain labels without erasing borrowed chords or modulations? |
| Audio-only versus known chart/sequence alignment | Does reviewed harmony reduce errors and correction effort when aligning curated songs to exact recordings? |
| Raw versus beat-aware smoothing | Can we remove distracting label flicker without erasing real changes? |
| Full chord vocabulary versus simplified vocabulary | Which output is more playable for the target learner? |
| Beat/onset analysis versus human-authored practice rhythms | What rhythm information is reliable and useful? |

Specific libraries and models are selected during the spike after checking maintenance, commercial-use licences, model-weight terms, hardware needs and reproducibility. An LLM may explain structured results, but it is not the source of truth for timestamps or harmony.

### Candidate tools and controlled comparisons

The supplied report, “Algorithmic Architectures and Empirical Evaluation Framework for Automated Guitar Learning Systems”, provides research leads, not a validated implementation specification. Keep Phase 0 first. Do not adopt its runtime, cost, accuracy or confidence figures as measured results for this project.

| Area | Initial candidates | Experiment and decision |
|---|---|---|
| Chord recognition | Spectral-template baseline, BTC-ISMIR19, CREMA, ChordMini/ChordNet2E1D, Chordino/NNLS-Chroma; ChordFormer after source/checkpoint review | Five have completed the same 64-case synthetic screen. Chordino Mac setup is complete; the shortlist is open. Compare real-recording harmony, timing, setup and compute before narrowing it. |
| Source separation | Standard HT-Demucs; optional 6-stem model; Spleeter as an alternative comparison | Compare original mix, 4-stem bass plus “other”, and isolated guitar. Retain separation only where its benefit warrants its cost; it may remove useful harmony or introduce artefacts. |
| Key and harmonic context | Cheap chroma/key-profile baseline; optional verified pretrained key estimator | Estimate from audio, retain alternative keys and uncertainty, then test a soft prior for ambiguous chord candidates. Allow local key changes; never force all chords into one scale. |
| Curated chart alignment | NumPy finite section/repeat decoder; spectral or NNLS evidence; DECIBEL/ChordSync research leads | Paired screen complete; automatic detector drafts are the default while reviewed-sequence/holdout research continues. No founder transcription gate. |
| Beat and section analysis | Simple baseline; All-In-One | No beat tracker exists in the inspected app. Compare beat/downbeat alignment and useful practice boundaries. Test All-In-One for combined tempo, beats and sections; verify dependency and model requirements. |
| Chord smoothing | Raw output, simple duration smoothing, beat-aware probability pooling/decoding where probabilities are available | Measure distracting flicker and lost/shifted genuine changes. Include anticipations, fast changes, tempo variation and an incorrect beat grid. |
| Rhythm guidance | Human-authored pattern library; optional onset detection and pattern matching | Establish a useful practice-pattern baseline before trying automated transcription or stroke-direction classification. |
| Evaluation | mir_eval plus founder play-tests | Use duration-weighted chord scores, boundary timing and beat metrics alongside usability and correction effort. |

The initial detector screen and annotated acoustic pilot are complete. Next prioritise [curated chart-assisted alignment](docs/CHART_ALIGNMENT.md): compare audio-only detection, key/chord-vocabulary guidance and alignment from an ordered reviewed sequence on ten permitted excerpts. Test separation and soft context as controlled improvements where failures justify them. Avoid an exhaustive model/setting combination before guitar feedback. [App-readiness criteria](docs/APP_READINESS.md) records the validation gate; measure timing, drift and correction effort as well as raw recognition. A curated learning-path release can use reviewed, cached arrangements.

[Spleeter](https://github.com/deezer/spleeter) and [Demucs](https://github.com/facebookresearch/demucs) are source-separation tools, not chord recognisers. Their output is audio stems, which must go through a separate chord detector. Spleeter provides 2/4/5-stem variants; Demucs provides the usual vocals/drums/bass/other split and an experimental six-source variant with guitar/piano. Benchmark the original mix against selected stems or recombined accompaniment rather than assuming a cleaner-sounding stem improves recognition. Separation adds compute and can introduce artefacts or remove useful harmony. For the longer band-in-your-pocket goal, stems can support muting a part for practice; generated accompaniment remains a separate engine. Meta's linked Demucs repository is archived and points to the author's fork, so check the actual maintained source and pinned dependencies at integration time.

Run the automated synthetic suite and annotated-data checks before assigning guitar comparisons. A setup failure is distinct from a poor musical score; do not omit it. These automated screens are complete for the initial candidates. Now use automatic drafts for ordinary play-along feedback, while broader reference evaluation continues separately. User reactions guide usefulness and investigations; they do not become accuracy labels automatically.

### Curated references and chart-assisted timing

Search for comparable chord/key references for a specific recording, preserve provenance and source-use status, normalise capo shapes into sounding pitches, and compare ordered verses/choruses plus repetitions. An unordered list of chords only narrows the vocabulary; an ordered sequence and section structure provide a much stronger alignment constraint. Copied charts are correlated evidence, and a simplified learner chart is a separate arrangement rather than proof of exact recorded harmony.

Use the chart to guide variable-duration alignment against acoustic evidence, then flag contradictions and unknown spans for review. Exact recording identity matters: radio edits, covers, intros and section repeats can invalidate an otherwise correct chart. Preserve raw recognition, alternative readings, reviewed harmony and playable shapes. Once checked, cache the alignment per recording/arrangement so ordinary playback needs no new inference.

The bounded spike is described in [docs/CHART_ALIGNMENT.md](docs/CHART_ALIGNMENT.md). Import, section/repeat inputs and paired evidence screening are complete. Further reference/holdout work remains an estimated **1.5–2.5 focused days**, independent of founder transcription. The automatic ten-song player is available on port 8070, with the earlier three-song pack retained on 8068; its optional problem timestamps can focus later research. The longer Animals corpus recording still requires matching, and cyclic Creep alignment remains unaccepted. Intro-only hypotheses are not whole-song references.

Research leads include [DECIBEL](https://arxiv.org/abs/2002.09748) and [ChordSync](https://arxiv.org/abs/2408.00674). ChordSync's execution/checkpoint availability is unresolved; do not mark it integrated or assign a benchmark score. Test wrong-key/capo charts, wrong chords and missing repeats deliberately, and evaluate actual timing against independently checked audible boundaries. Chart-assisted scores are separate from audio-only recognition, and timing gold stays hidden from the aligner.

### Pipeline experiment: separation and musical context

Treat song analysis as a modular pipeline with shared source timing. Key, chords and rhythm can inform one another; a first key estimate should remain revisable rather than becoming an irreversible first-step decision. Joint use of key, chord, bass and metric context has a research basis in [Dixon's computational harmony work](https://webspace.eecs.qmul.ac.uk/s.e.dixon/pub/2010/Dixon-CMMR-2010.pdf); its historical results are not measured accuracy for this app.

| Step | Output / purpose | Experiment state |
|---|---|---|
| Decode once | Prepared audio, identity/hash and shared time origin | Implemented |
| Choose analysis signal | Original mix; optional guitar, accompaniment or harmonic stem combination | Separation comparison planned |
| Extract evidence | Chroma/chord candidate scores; key candidates; beats/onsets; optional bass evidence | Chord labels implemented; other evidence and score export require adapters |
| Resolve uncertain harmony | Combine audio evidence with neighbouring chords and a soft key prior | Planned; measure benefit before retaining |
| Stabilise timing | Reduce flicker while preserving audible, offbeat and fast changes | Planned controlled treatment; preserve raw timestamps |
| Make a practice arrangement | Playable shapes/capo, labelled simplification and suitable practice rhythm | Later product stage, evaluated separately from exact recognition |

After the curated alignment baseline, compare four variants where further improvement is needed, using one practical detector and fixed settings: **original mix**, **separation only**, **key/context assistance only**, and **separation plus key/context assistance**. Keep timing smoothing fixed during this comparison. Tune on development recordings, freeze settings, then evaluate held-out recordings. Record accuracy, missed changes, added wrong chords, correction effort and total processing time, including separation and key analysis. Externally sourced keys/charts are legitimate declared inputs for a chart-assisted task; do not give evaluation-only gold labels to the audio-only control and claim it discovered them. An oracle-key diagnostic must be explicitly labelled and excluded from deployment claims.

Use key to rank uncertain alternatives, not to discard strong audio evidence. A song in C major can contain F minor or D major; preserve those if supported. Include minor/relative-major ambiguity, borrowed chords, secondary dominants, key changes, modal rock and deliberately wrong key estimates in the next synthetic context tests. Disable or weaken the prior when the key is uncertain. Prefer audio-derived key evidence and avoid a feedback loop in which wrong chord labels imply a key that then reinforces those same labels.

Current adapters mostly emit final labels rather than comparable candidate probabilities. Export model scores before implementing probabilistic assistance, and validate their calibration; a softmax or chroma similarity is not automatically a trustworthy confidence percentage. Store raw candidates, key alternatives, context adjustments and reasons separately from the displayed arrangement, so improvements and regressions remain inspectable.

### Progressive synthetic screening before real-recording comparisons

Use original generated audio with known labels to identify broken integrations, vocabulary gaps and basic timing errors early. Build up controlled difficulty rather than jumping immediately to dense music:

| Level | Generated conditions | What to inspect |
|---|---|---|
| 1. Clean harmony | Major/minor triads, silence, all roots, slow changes | Basic recognition, input/output correctness and no-chord behaviour |
| 2. Voicing variation | Inversions, octave/register changes, missing/doubled notes and changed instrument timbres | Sensitivity to voicing and harmonic content |
| 3. Guitar-like events | Plucked decays, staggered strum attacks, accents and repeated strokes | Chord stability during attacks/decays and rhythm detection |
| 4. Controlled mix | Add bass movement, drum-like transients, a melodic line, noise and simple effects independently | Whether separation helps and which distractors cause false labels |
| 5. Temporal/music complexity | Faster/offbeat changes, tempo variation, section repetition, power chords and extensions | Boundary accuracy, smoothing damage and vocabulary/ambiguity handling |

Keep generator seeds and recipes reproducible. Vary one factor at a time before combining factors; report results per condition, not just an aggregate score. Reserve unseen seeds, roots and timbres for synthetic holdouts. Sound synthesis and any sample assets must have an appropriate permission basis.

Use these as screening diagnostics. Confirm sample rate, label mapping and adapter correctness before rejecting a candidate for basic failures. Synthetic timbre can differ substantially from a pretrained model's training domain, so a poor synthetic score alone is insufficient to reject a model intended for real music. Power chords do not establish major/minor quality; mark ambiguity or evaluate root/acceptable labels instead of inventing an exact quality. Generated strum timing is known, but any direction classifier still needs physical guitar examples.

Phase 0 supplies the initial fixture and baseline. Phase A's levelled suite is implemented and has run across five candidates. ChordMini leads the original core metric including silence and boundary F1; the baseline leads the new chord-only metric but flickers more. Chordino recognises clean voiced triads well but has weaker silence/timing behaviour and misses fast changes. Proceed to annotated real recordings and then founder guitar sessions; newer architectures remain optional backlog work. A synthetic winner is not a production winner.

Pin tool/model versions and record hardware, audio duration, settings, cold versus warm runtime, peak memory and failure rate. Include decoding, separation and feature extraction in end-to-end processing time. Cloud cost estimates must include actual provider pricing, idle/startup time and storage where relevant; the report's per-song compute estimate is not a budget.

Check code, model weights, dependencies and datasets separately. BTC's repository identifies an MIT licence and CREMA identifies BSD-2-Clause, but that alone is not a complete deployment review. All-In-One depends on madmom, which distinguishes BSD source code from noncommercial model/data files; inspect whether the selected pipeline uses those files before drawing a commercial-use conclusion.

Use one consistently decoded audio source and preserve its timing reference across analyses and playback. Do not assume different decoders or recordings have identical offsets. Retain raw timestamps alongside any adjusted display or practice boundaries.

### Musical safeguards for the experiments

- Do not impose a universal maximum number of chord changes per bar or force every change onto a rigid grid. These can hide genuine musical events. Compare optional snapping with unsnapped output and keep manual correction available.
- Treat a detected bass note as evidence for harmony, not ground truth for the chord root; inversions and passing notes are expected.
- Treat pattern similarity as a ranking score, not a calibrated probability. Determine display thresholds from labelled examples and play-tests rather than adopting the report's 0.75 value.
- Distinguish detected attack timing from inferred down/up strokes. When uncertain, show a labelled practice pattern instead of claiming an exact transcription.
- Review suggested section loops by listening and playing. Downbeat snapping alone does not resolve pickup notes, wrong beat grids or discontinuities at loop boundaries. Allow pickup/count-in choices and editable boundaries where supported.
- Keep the current chord aligned with playback and preview upcoming changes separately. Test a configurable look-ahead rather than shifting the whole chart early by a fixed 1–1.5 seconds.

Use existing annotated datasets and independently prepared references for accuracy evaluation. Reserve fresh tracks as holdouts. Detailed new annotation is a separate curation/research activity; the founder should not have to transcribe every song to use or test the player.

Use mir_eval's root and major/minor chord comparisons first; add richer chord-quality metrics only where the reference labels support them. Score simplified teaching arrangements separately from exact transcription so deliberate simplification is not confused with recognition failure. Investigate GuitarSet and annotated popular-music datasets as supplementary benchmarks after checking audio availability, permissions and overlap with candidate models' training data. Published annotation access does not necessarily include the audio. Evaluate separation SDR only where reference stems exist; downstream chord usefulness is the main project criterion.

Measure both musical accuracy and experience:

- Duration-weighted chord agreement, with separate exact and simplified-label scores.
- Chord-boundary timing error and unnecessary changes per minute.
- Beat tracking errors, including half/double-tempo mistakes.
- Processing time, memory, compute cost per analysed minute, and manual correction time.
- “Could I follow it?”, “Did it sound right?”, “Where did I stop?”, and “Would I play it again?”

Where practical, hide the algorithm identity and alternate comparison order. Otherwise expectations and familiarity may dominate preference.

For optional structured founder comparisons, prepare the excerpt and all charts automatically, then ask him to play and rate followability or tap a problem. Baseline/alternative/improved versions and existing reference controls can support a bounded comparison without manual timestamp entry. Track recognition, display timing and playability separately. Keep detailed reference labelling out of the ordinary practice flow.

**A1 selection exit: complete.** The selected initial workflow has reproducible adapters/model pins, reference diagnostics including experiment holdouts, a fresh successful ten-song integration/runtime run and preserved native outputs. BTC's limited vocabulary is accepted for raw basic-harmony drafts, with CREMA review and recording-specific teaching arrangements required. Current evidence does not select unrestricted transcription or automatic chart acceptance.

**A2/A3 product-readiness exit: still required.** The developer review workspace is implemented, but its worklists, symbolic grip checks, saved drafts and QA do not accept recording arrangements or measure human correction cost. Measure actual correction effort, independently check representative recording-specific arrangements/timing, and collect founder followability/usefulness evidence during ordinary play. Select the cheapest reviewed workflow that produces enjoyable, usable results; narrow material if necessary. Benchmark agreement and disagreement flags do not substitute for correction time or guitar ratings. Substantial product/iOS work follows these catalogue/practice gates.

## 5. Founder play-test protocol

Run three or four 15–20 minute guitar sessions each week. Keep logging under a minute so research does not replace playing.

1. Pick one familiar and one less familiar excerpt at an appropriate difficulty.
2. Play with the current baseline and a candidate version.
3. Mark the time of confusing chords, late cues, awkward voicings, or unsuitable rhythms.
4. Rate chord usefulness, timing, rhythm guidance and enjoyment from 1–5.
5. Record whether the session ended with a successful play-through and what to change next.

Distinguish recognition errors from teaching and playback errors. A correctly identified chord can still be an unsuitable fingering; a good chart can feel wrong because of output latency; an accurate rhythm can be too difficult for the learner.

Create and use `PLAYTEST_LOG.csv` for session-level records. Keep timestamped findings in the notes field initially; introduce a dedicated annotation tool only if needed.

**Proposed internal gate:** at least 8 of 10 representative reviewed excerpts score 4/5 or better for followability across two sessions. Treat this as a project decision rule, not a scientific or industry benchmark.

## 6. Phase B — Make a useful practice companion

**Indicative effort: 2–3 focused weeks after the testing bench.**

Integrate the selected analysis outputs into a practice product. Choose the first product platform after Phase A: a Mac-accessible browser version or an Expo mobile version. The existing Expo shell is reusable, but its web path needs repair and native macOS is not configured. Begin iOS work when the algorithms and practice interaction justify it.

If continuing with Expo, establish one practice player, move non-route modules outside `app/`, replace duplicated route metadata with stable IDs, and feed the selected recording/arrangement into the display. Replace its free-running timer with playback-clock synchronization and consolidate the unused hooks. Verify pause/resume, forward/backward seeking, replay, buffering, source changes and supported speeds. Check dependency/runtime compatibility and add focused tests while implementing these behaviours. Reuse Phase A's known chart and timing fixtures rather than diagnosing a new model and a new player simultaneously.

Build the smallest complete practice flow:

1. Select a song and an appropriate arrangement.
2. Preview the chords and the one skill to focus on.
3. Practise a suitable rhythm with an original demonstration or click.
4. Play a section, then the complete arrangement.
5. Record “too easy”, “about right” or “too hard”, plus the specific difficulty.
6. Get a suggested next session.

Support two rhythm modes: **practice pattern**, a suitable accompaniment selected for the learner; and **transcribed rhythm**, only where its accuracy has been validated. Never present a suggested pattern as the exact recorded guitar part.

Make chord text readable at guitar-playing distance. Allow a simple keyboard or optional foot-control interaction. Test the actual speaker/headphone setup; wireless audio delay can affect how the player experiences visual alignment.

Provide editing for chord labels, boundaries, section markers, capo/tuning notes and arrangement difficulty. Preserve the raw analysis alongside reviewed and simplified versions.

**Exit decision:** the founder chooses this app for ordinary practice for two weeks and can finish sessions without developer intervention. Keep a short record of why he returns to another tool.

## 7. Phase C — Add structured progression

**Indicative effort: 1–2 focused weeks, with ongoing content work.**

Create a reviewed catalogue of approximately 30–50 arrangements, subject to the chosen content route. Attach difficulty to the arrangement, not just the song title.

Build this as the first batch of a potential few hundred rock/pop songs. Each entry needs a specific recording/version, reviewed sounding harmony, capo/played shapes, aligned timing and section structure, with source provenance and correction history. Expand only after measuring curation effort and player demand; several easy/hard arrangements of one song can support progression without increasing the title count.

Tag the actual demands: chord shapes, chord transitions, change rate, tempo, rhythmic subdivision, syncopation, muting, barre chords, power chords, stamina, tuning and capo requirements. Record which skill each arrangement introduces and which it reinforces.

Add a small capo and voicing experiment. Search a practical range of capo positions and familiar chord shapes, preserving the recording's sounding key. Show the capo position and played shapes explicitly. Compare familiar open shapes, barre requirements, hand movement and transition speed against the founder's actual ratings; the easiest arrangement depends on the player's learned shapes, not a universal score. Use the report's cited playability research as a lead to inspect before implementing its formulas or weights.

Do not automatically replace every suspended, extended or slash chord with a triad. Review whether the simplification preserves the recognisable harmony and fits the backing track. Keep the detected harmony and the teaching arrangement separate, with optional power-chord versions where musically suitable. Start with a reviewed shape library rather than a full biomechanical fingering optimiser.

Start with transparent rules: prefer liked music using established skills plus one manageable new challenge. Avoid recommending a song that introduces a new chord, faster changes and a new rhythm simultaneously. Revisit weak skills through different songs.

Example progression: steady downstrokes → comfortable open-chord changes → eighth-note strumming → rests and accents → power-chord movement → palm muting. Adapt the sequence to the selected acoustic or electric focus.

Let players skip, repeat, choose alternatives and revisit favourites. Advancement initially relies on self-report and successful play-throughs; do not invent precision with unvalidated microphone scoring.

**Exit decision:** the app gives a useful, understandable answer to “What should I practise next?” and changes its recommendation when the player reports a specific problem.

## 8. Phase D — Test with other players and test payment

**Indicative duration: a four-week pilot after the founder version is stable.** Recruit 10–20 target players beyond the founder, with a mix of beginner and returning-player ability.

Give each player a short baseline session using their usual tools, then access to the guided product. Collect completed practice sessions, songs or sections completed, difficulty feedback, support requests and reasons for stopping. Minimise collection of raw microphone audio; it is unnecessary for this pilot.

Test a real paid continuation around $4–6/month, clearly presented as a price experiment. Measure payment separately from statements of interest.

Proposed decision signals:

- At least half of participants still practise with it in week four.
- Retained players typically complete at least two meaningful sessions per week.
- Several participants pay to continue and can explain what they would miss.
- Manual correction and support costs appear affordable at the tested price.

These are directional gates for a small pilot, not proof of product-market fit. If users enjoy play-along but ignore recommendations, reconsider whether progression is the main paid benefit. If they follow recommendations but distrust charts, prioritise content quality.

## 9. Technical foundation and cost control

Use music-os as the implementation repository. The first development target is the founder's Mac: offline analysis scripts plus a minimal local browser bench, independent of Expo. Preserve the old Expo shell for later integration. Its Android bundle builds, its web build fails on a dependency, and no native macOS target is configured; settle the product platform after the algorithm decision. Run analysis offline or in background jobs and reuse results where permitted instead of analysing audio on every play. Port the selected results format into whichever product UI is chosen.

Keep five concepts separate:

- **Recording/source:** exact version, duration, provenance and permitted uses.
- **Analysis:** model version, chord events, beats, confidence and processing cost.
- **Arrangement:** playable chords, voicings, simplification, rhythm guidance and required skills.
- **Song structure:** sections, boundaries and repetitions.
- **Practice history:** what the player attempted, difficulty feedback and next recommendation.

Align each chart to a specific recording. Live versions, remasters, edits and different intros can break timing. Store manual corrections independently so model upgrades cannot silently erase them. Flag uncertain output for review rather than filling gaps with confident guesses.

The first cost model should include payment/platform fees, applicable taxes, content/rights costs, compute, storage, support and human review. Separate initial catalogue creation from recurring cost. At $5/month, 1,000 paying users yield $5,000/month gross before those costs; that is an illustration, not a forecast.

Record cost per newly processed song, cost per reviewed arrangement, recurring cost per active payer, acquisition cost and retention. Set spending limits after the first benchmark. Avoid unlimited on-demand processing until its costs and sourcing are understood.

## 10. Content and YouTube commercial workstream

The initial [song-access comparison](docs/SONG_ACCESS_FEASIBILITY.md) is complete, with primary-source terms and unresolved costs. Continue this work alongside Phase A. Official embedded playback plus separately permitted analysis is the preferred route; API quota is not a music-licence fee. The existence of Chordify is a reason to investigate feasible arrangements, not evidence that a public per-video YouTube tariff exists.

Compare three possible routes:

1. Official embedded playback with separately sourced, permitted analysis and teaching content.
2. An authorised catalogue or commercial partner supplying the needed audio/data rights.
3. Artist partnerships and original recordings that explicitly permit analysis and the intended app features.

For each route, establish playback permissions, analysis access, storage/reuse permissions, chart/arrangement permissions, commercial terms, territory limits, and handling of removed recordings. Determine whether the planned looping, speed controls and future instrument muting are supported. Keep unavailable capabilities out of the advertised product.

YouTube's published API policies restrict downloading and separating audiovisual content without approval. The founder's successful experiments demonstrate capability; they do not establish the commercial terms for this app. Get a targeted review of the selected implementation before public monetisation rather than designing around guessed fees.

**Deliverable:** a one-page comparison with actual terms or explicitly unresolved items, costs and a preferred launch route. If the preferred catalogue is unavailable, continue with a narrower authorised catalogue and test whether users still value the experience.

## 11. Roadmap toward a band in your pocket

| Stage | Player experience | What carries forward | New question to validate |
|---|---|---|---|
| 1. Guided song practice | Follow chords and rhythm; choose the next song | Harmony, timing, sections, arrangements, practice habits | Does this make solo practice easier and more enjoyable? |
| 2. Backing band | Play with drums and bass at a selected tempo | Beat grid, chord map, section structure | Does the accompaniment sound musical enough to return to? |
| 3. Rehearsal partner | Repeat sections, change intensity, remove the player's part where permitted | Arrangement and playback controls | Which controls create the feeling of rehearsing with others? |
| 4. Responsive band | Accompaniment reacts to playing, tempo or section cues | Song model plus new live audio/timing systems | Can response remain stable, low-latency and enjoyable? |

Begin stage 2 with original or appropriately licensed grooves and arrangements. Stem separation may support an authorised “remove the guitar” mode, but generated accompaniment and extracted stems are distinct product and rights choices.

Keep the first experiment simple: a steady drummer and bass part following a known progression. Real-time listening, tempo following, expressive accompaniment and recovery after mistakes are substantial later research problems.

For this first band experiment, use authored MIDI drum grooves and simple root/root-fifth bass patterns driven by the reviewed chord map, tempo and section markers. Compare a fixed groove with basic verse/chorus variation and fills. Use appropriately licensed soundfonts or samples and measure whether the result feels musical, stays in time and encourages another play-through. Generated MIDI does not by itself establish rights to every sound asset or song arrangement. Keep generation local where practical and measure its actual device performance.

Defer live tempo-following, microphone-based intensity response and automatic recovery/vamping until the fixed-tempo band is enjoyable. Later tests must distinguish the player's sound from the app's own accompaniment and account for microphone processing and playback latency.

The bridge between the products is a reusable model of harmony, rhythm and song structure. Validate the emotional promise at every stage: “Did this feel more like making music with others?”

## 12. Immediate backlog

| Order | Action | Status / output |
|---|---|---|
| 0 | Audit old code and establish the Mac analysis/player foundation | Complete; [reuse audit](docs/REUSE_AUDIT.md), automated fixtures, playback clock and durable Documents checkout |
| 1 | Evaluate and select the initial offline algorithms | **Complete**; [BTC/CREMA + guided pulse decision](docs/ALGORITHM_SELECTION.md), pinned methods, new ten-song batch and separate selected research pack |
| 2 | Make the starter catalogue dependable | **In progress**; all-ten diagnostics and ten provisional drafts complete. Founder feedback now adds a provisional Wild Thing display correction and clearer hold-length UI; it does not close physical timing, recorded rhythm, full-arrangement or human-cost gates. Next secure a capable recording-review/reference route and publish a small reviewed pack; [assessment](docs/STARTER_FOUR_RECORDING_ASSESSMENT.md). Earlier 1.5–2.5-day effort estimate depends on that route. |
| 3 | Assess ordinary guitar practice | Pending; optional issue taps and bounded followability checks, then a two-week usefulness trial. No founder transcription |
| 4 | Resolve commercial content/playback route | Parallel; [initial comparison](docs/SONG_ACCESS_FEASIBILITY.md), then actual terms/costs for the chosen route |
| 5 | Choose product platform and integrate reviewed catalogue | After catalogue/practice gates; browser or Expo, scoped repairs and later iOS/device work |
| 6 | Expand progression and run an external paid pilot | After founder workflow is useful; measure curation/support cost and retained practice |
| 7 | Add the first backing-band experiment | Later; fixed-tempo authored drums and bass from reviewed harmony/sections |

The next milestone is a dependable reviewed starter catalogue, followed by enjoyable ordinary practice. Model selection is complete for this scope; production readiness depends on correction effort, accepted arrangements and usefulness rather than another broad model comparison.

Preserve the comparison reports, frozen candidate settings and negative results. Each new method must address a named failure with a bounded comparison. The founder remains the first practice user, not the source of compulsory accuracy annotations.

## Evidence and references

These sources support context, not claims about private licensing agreements or guaranteed economics. Competitor prices mentioned in discussion are user-provided and should be checked for market, tier and billing period before a formal pricing comparison.

- [Musopia: differences between JustinGuitar's website and app](https://musopia.zendesk.com/hc/en-us/articles/360021893219-What-s-the-difference-between-the-courses-on-the-justinguitar-com-website-and-this-app) — identifies song copyright fees as an app subscription cost, without disclosing the cost breakdown.
- [Chordify: strumming-pattern support](https://support.chordify.net/hc/en-us/articles/360019489618-Does-Chordify-show-the-strumming-patterns) — published support statement says patterns are not detected; its algorithm assessment dates to 2021.
- [Chordify terms](https://chordify.net/pages/terms-and-conditions/) — describes embedded YouTube API playback, without establishing the proposed per-video payment arrangement.
- [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies) — relevant restrictions and commercial-use conditions for an API-based implementation.
- [JustinGuitar song library](https://www.justinguitar.com/songs/) — existing difficulty/chord/genre discovery means simple filtering alone is insufficient differentiation.
- [BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19) — candidate chord-recognition implementation; supports major/minor and larger-vocabulary inference.
- [CREMA](https://github.com/bmcfee/crema) — alternative chord-analysis candidate with a BSD-2-Clause repository licence.
- [Demucs](https://github.com/facebookresearch/demucs) — separation candidates, model-specific limitations and resource guidance; benchmark the exact selected configuration.
- [All-In-One](https://github.com/mir-aidj/all-in-one) — tempo, beat, downbeat and functional-section analysis, with installation dependencies and audio-offset guidance.
- [madmom licence distinctions](https://github.com/CPJKU/madmom#license) — separate source-code and model/data terms; inspect actual dependency usage.
- [mir_eval chord evaluation](https://mir-eval.readthedocs.io/latest/api/chord.html) — standard chord comparisons for the benchmark.
