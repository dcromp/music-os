# Guitar learning app → Band in your pocket

Project plan · 10 October 2026 · Working title

**Project repository:** [dcromp/music-os](https://github.com/dcromp/music-os). The 10 October 2026 [reuse audit](docs/REUSE_AUDIT.md) found an Expo/React Native YouTube play-along prototype. Keep its app shell, song cards and player composition; repair the chart data flow and synchronization. Audio separation, chord detection, learning paths and accompaniment are new work. The founder's previous analysis workflow is not in the inspected repository.

## 1. Vision and first product

**Long-term vision:** make playing guitar alone feel like playing with a band. Serve people who lack nearby musicians, compatible schedules, or the confidence to join a group. Success means they pick up their instrument more often, enjoy playing, and improve through making music.

**First product:** an affordable song-based guitar practice app that shows useful chords and rhythm guidance, then recommends what to play next. Start with rock and with players who know some chords but need help progressing.

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

## 4. Phase 0 — Reuse findings and playback baseline

**Initial inspection completed on 10 October 2026.** [docs/REUSE_AUDIT.md](docs/REUSE_AUDIT.md) records evidence and component decisions at commit `0083861`. Device/browser playback and the first guitar session remain to be verified. Allow an initial 2–4 focused days for the playback repairs below, then revise the estimate from observed results.

What exists:

- Expo SDK 51 / React Native 0.74.5 with Expo Router, theme utilities, seven hardcoded song cards, an embedded YouTube wrapper and a chord/beat/bar display.
- The active flow is Songs → `app/screens/SongPlayer.js`. The separate Player tab, Profile and Tutorial are placeholders; login/signup simulate navigation.
- A preliminary Song type includes timed chord intervals, but the display always loads sampleSongData instead of the selected song. It ignores the sample's timestamps and runs on its own fixed-tempo timer. At 120 BPM it advances a chord every two seconds despite sample intervals of 15 seconds.
- Two unused hooks sketch player-state and clock synchronization. They need consolidation and correction before use; one expects numeric states while the installed wrapper supplies string states.
- No implemented audio import, analysis pipeline, persistence, strumming, recommendation or band engine. Earlier player code inspected in history does not supply those missing capabilities.

Verification: locked dependencies install, TypeScript passes and the sole starter snapshot test passes. Android bundle export succeeds. Web export fails because the iframe wrapper imports missing `react-native-web-webview`. These checks do not validate live playback or chart accuracy; the JavaScript core also lacks checkJs coverage.

Next implementation:

1. Keep Expo initially. Establish one practice player, move non-route modules outside `app/`, and provide direct access for founder testing. Validate the chosen native or browser playback path; resolve web support before promising browser availability. Record a supported runtime and run commands.
2. Extend the shared, versioned recording/analysis/arrangement format with explicit timestamp units. Use stable IDs instead of duplicated route metadata. Replace the current sample with a clearly synthetic timing fixture and one manually verified recording/chart pair.
3. Feed the selected chart into the display and derive highlighting from numeric playback time. Consolidate the clock hooks, handling seek, pause/resume, buffering, replay, source change and supported speeds. Retain the visual bar concept where useful, while allowing real timestamps and changes inside bars. Add focused tests when implementing these behaviours.
4. Run the first guitar session on the founder's actual screen/audio setup. Add `PLAYTEST_LOG.csv` for observations and record a reproducible baseline.

**Exit decision:** one verified recording/chart pair remains aligned through start, pause/resume, forward/backward seeking and replay, and the founder can complete a short session without manually resetting the chart. This gate is still outstanding. Establish it before interpreting recognition-model play-test results.

### Phase A — Build the guitar testing bench

**Indicative effort: 1–2 focused weeks.** These are planning estimates for a solo builder, not delivery commitments.

Use the repaired Expo player from Phase 0 as the comparison interface. Recover the founder's previous separation/chord-analysis workflow separately if available; none was found in music-os. Put offline analysis tooling in this repository behind adapters that emit the shared JSON format, and import those results into the player. Record inputs, dependencies, outputs and known failures; start with a simple detector if the prior workflow cannot be recovered.

Select 12–20 test tracks or excerpts across clean acoustic guitar, distorted rhythm guitar, sparse and dense mixes, slow and fast changes, open chords, power chords, and rhythmically awkward passages. Use recordings with a suitable permission basis for the experiment; include original recordings with known chords and timing. Keep a source and permission record for each item.

Extend the existing player to switch imported analysis versions, adjust timing offset and record a session rating. Add local-audio playback for permitted benchmark material; it is not already implemented, despite the react-native-sound dependency. Keep the playback source matched to the analysed recording. No accounts, payment system or polished mobile app yet.

Compare these approaches with identical inputs and hardware:

| Experiment | Question |
|---|---|
| Simple chroma/template baseline | How far does a cheap, explainable chord detector get us? |
| Pretrained chord-recognition model | Does it materially improve useful chord labels and timing? |
| Full mix versus separated harmonic/instrument stems | Does separation improve recognition enough to justify processing cost and artefacts? |
| Raw versus beat-aware smoothing | Can we remove distracting label flicker without erasing real changes? |
| Full chord vocabulary versus simplified vocabulary | Which output is more playable for the target learner? |
| Beat/onset analysis versus human-authored practice rhythms | What rhythm information is reliable and useful? |

Specific libraries and models are selected during the spike after checking maintenance, commercial-use licences, model-weight terms, hardware needs and reproducibility. An LLM may explain structured results, but it is not the source of truth for timestamps or harmony.

### Candidate tools and controlled comparisons

The supplied report, “Algorithmic Architectures and Empirical Evaluation Framework for Automated Guitar Learning Systems”, provides research leads, not a validated implementation specification. Keep Phase 0 first. Do not adopt its runtime, cost, accuracy or confidence figures as measured results for this project.

| Area | Initial candidates | Experiment and decision |
|---|---|---|
| Chord recognition | Recovered founder workflow if available, a simple chroma/template baseline, BTC-ISMIR19 and CREMA | No detector exists in the inspected app. Run candidates on identical excerpts; compare chord accuracy, followability, setup effort and processing cost. Choose after measurement rather than preselecting BTC. |
| Source separation | Standard HT-Demucs; optional 6-stem model | Compare original mix, 4-stem bass plus “other”, and isolated guitar. Retain separation only where its benefit warrants its cost; it may remove useful harmony or introduce artefacts. |
| Beat and section analysis | Simple baseline; All-In-One | No beat tracker exists in the inspected app. Compare beat/downbeat alignment and useful practice boundaries. Test All-In-One for combined tempo, beats and sections; verify dependency and model requirements. |
| Chord smoothing | Raw output, simple duration smoothing, beat-aware probability pooling/decoding where probabilities are available | Measure distracting flicker and lost/shifted genuine changes. Include anticipations, fast changes, tempo variation and an incorrect beat grid. |
| Rhythm guidance | Human-authored pattern library; optional onset detection and pattern matching | Establish a useful practice-pattern baseline before trying automated transcription or stroke-direction classification. |
| Evaluation | mir_eval plus founder play-tests | Use duration-weighted chord scores, boundary timing and beat metrics alongside usability and correction effort. |

Run experiments in stages: compare chord detectors on the original mix first, test separation with the strongest practical candidates second, then assess timing and simplification. Avoid an exhaustive combination of every model and setting before any guitar feedback.

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

Annotate a small reference set of chord boundaries, chord labels and beats. Reserve several tracks as a holdout set so repeated tuning does not merely fit the founder's favourites.

Use mir_eval's root and major/minor chord comparisons first; add richer chord-quality metrics only where the reference labels support them. Score simplified teaching arrangements separately from exact transcription so deliberate simplification is not confused with recognition failure. Investigate GuitarSet and annotated popular-music datasets as supplementary benchmarks after checking audio availability, permissions and overlap with candidate models' training data. Published annotation access does not necessarily include the audio. Evaluate separation SDR only where reference stems exist; downstream chord usefulness is the main project criterion.

Measure both musical accuracy and experience:

- Duration-weighted chord agreement, with separate exact and simplified-label scores.
- Chord-boundary timing error and unnecessary changes per minute.
- Beat tracking errors, including half/double-tempo mistakes.
- Processing time, memory, compute cost per analysed minute, and manual correction time.
- “Could I follow it?”, “Did it sound right?”, “Where did I stop?”, and “Would I play it again?”

Where practical, hide the algorithm identity and alternate comparison order. Otherwise expectations and familiarity may dominate preference.

For the founder's main comparison, present the same excerpt in three anonymous versions: a measured detector baseline (recovered workflow or simple new detector), an alternative detector, and the strongest detector with timing/arrangement improvements. The old app's arbitrary sample chart is not a detector baseline. Keep a manually checked reference chart as a control. Track recognition, display timing and playability separately; if the combined improved version wins, test timing and simplification separately before attributing the benefit to either one.

**Exit decision:** select the cheapest workflow that produces enjoyable, usable results on most target material. If none does, narrow the supported material or introduce manual review; do not expand the catalogue to hide quality problems.

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

Use music-os as the implementation repository and retain its Expo/React Native shell for the first iteration. The Android bundle builds, while web currently has a dependency blocker; verify playback on the chosen target before settling the first test platform. Add a platform-specific playback adapter if needed rather than replacing the whole app. Check the older Expo stack against the intended device/build workflow and plan upgrades from a captured baseline. Run analysis offline or in background jobs and reuse results where permitted instead of analysing audio on every play.

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
| 1 | Establish one player flow and select/verify target playback support | Reproducible run guide; clean routes; native or browser smoke test |
| 2 | Define shared versioned JSON; connect one verified recording/chart pair to the playback clock | Timing fixture and selected-song data flow; pause/seek/replay checks |
| 3 | Run a short guitar session with the verified chart | Phase 0 acceptance evidence, play-test log and timing corrections |
| 4 | Recover external founder analysis workflow or implement a baseline; add offline adapters and local audio | Reproducible analysis outputs imported into the existing player |
| 5 | Choose benchmark material, add candidate switching and run staged comparisons | Test-set manifest, anonymous guitar ratings and held-out quality/cost report |
| 6 | Investigate content and playback commercial routes in parallel | Source/permission/cost comparison |
| 7 | Choose the first reliable detector/arrangement workflow | Phase B implementation brief |

The next meaningful milestone is a play-along experience the founder wants to use again. Build the curriculum around that evidence, then test whether other players want to pay for it.

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
