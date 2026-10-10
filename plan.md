# Guitar learning app → Band in your pocket

Project plan · 10 October 2026 · Working title

**Project repository:** [dcromp/music-os](https://github.com/dcromp/music-os). The 10 October 2026 [reuse audit](docs/REUSE_AUDIT.md) found an Expo/React Native YouTube play-along prototype. Preserve its useful UI for later product integration. **First choose and validate the algorithms on the founder's Mac**, using offline analysis and a small local play-along bench. Repairing the Expo app or developing iOS is not a prerequisite. Audio separation, chord detection, learning paths and accompaniment are new work; the founder's previous analysis workflow is not in the inspected repository.

## 1. Vision and first product

**Long-term vision:** make playing guitar alone feel like playing with a band. Serve people who lack nearby musicians, compatible schedules, or the confidence to join a group. Success means they pick up their instrument more often, enjoy playing, and improve through making music.

**First product:** an affordable song-based guitar practice app that shows useful chords and rhythm guidance, then recommends what to play next. Start with rock and with players who know some chords but need help progressing.

**Catalogue strategy:** work toward a curated few hundred rock/pop titles, beginning with a smaller reviewed learning path. For known songs, use comparable chord/key references plus audio verification, then align the reviewed sequence to a specific recording. Prioritise reliable timings and affordable one-time curation; keep free chord recognition as a control, verification signal and fallback.

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

### Phase A — Choose algorithms on Mac and build the guitar testing bench

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

The bounded spike is described in [docs/CHART_ALIGNMENT.md](docs/CHART_ALIGNMENT.md). Import, section/repeat inputs and paired evidence screening are complete. Further reference/holdout work remains an estimated **1.5–2.5 focused days**, independent of founder transcription. The automatic three-song player is available now; its optional problem timestamps can focus later research. The longer Animals corpus recording still requires matching, and cyclic Creep alignment remains unaccepted. Intro-only hypotheses are not whole-song references.

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

**Exit decision:** recommend an initial chord/beat/rhythm workflow with measured Mac runtime, quality, correction effort and founder play-test evidence, including held-out excerpts. Keep the scripts, shared output format and bench reproducible. Select the cheapest practical workflow that produces enjoyable, usable results on most target material; if none does, narrow the supported material or introduce review. The algorithm choice may evolve after broader testing, but substantial product/iOS work starts after this decision.

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

Run this alongside Phase A. The existence of Chordify is a reason to investigate feasible arrangements, not evidence that a public per-video YouTube tariff exists.

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

| Order | Action | Output |
|---|---|---|
| 0 | Completed: inspect existing code and run baseline checks | [Reuse audit](docs/REUSE_AUDIT.md); Android bundling passes, web blocker recorded, playback unverified |
| 1 | Establish a fresh detector baseline in an isolated Mac environment (prior workflow deleted) | Reproducible analysis command, explicit output format and first chart |
| 2 | Screen candidates with progressive synthetic cases, then select real benchmark excerpts | Per-condition diagnostics, held-out recipes, reference annotations and Mac runtime/quality measurements |
| 3 | Build the small local-audio browser bench and check its playback clock | Known chart fixture, pause/seek/replay validation and a short guitar session |
| 4 | Compare promising detectors, separation inputs and timing/arrangement variants | Anonymous guitar ratings, held-out results and correction effort |
| 5 | Choose the initial algorithms and record the decision | Repeatable scripts, quality/cost report and accepted limitations |
| 6 | Investigate content and playback commercial routes in parallel | Source/permission/cost comparison |
| 7 | Choose the product platform and integrate the selected pipeline | Phase B brief, scoped Expo/browser repairs and later iOS work |

The next meaningful milestone is a measured algorithm choice supported by enjoyable guitar sessions on Mac. Develop the product and curriculum around that evidence, then test whether other players want to pay for it.

Phase A's comparison report should record candidate versions, permitted inputs, exact run commands, measurements, anonymous play-test ratings and a keep/adapt/reject decision for each tested approach. Preserve negative results so future work does not repeat failed experiments.

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
