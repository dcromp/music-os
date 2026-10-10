# What would make the chord engine useful in an app?

## Current judgement

Existing models are promising enough for a practice prototype. The synthetic screen does **not** establish real-song accuracy or select the production model. The [six-performance real-guitar pilot](GUITARSET_PILOT.md) now shows why: CREMA leads intended major/minor agreement at 93.9% (98.1% reference coverage), ahead of BTC 84.0%, Chordino 82.7%, ChordMini 79.5% and baseline 54.3%. CREMA's weaker synthetic result did not predict its real-guitar performance. Retain several practical candidates for representative mixes and inspected boundaries; use the baseline as a cost reference. Six performances from one acoustic dataset do not establish general song reliability.

Music OS's earlier Expo prototype did not contain a chord detector. `app/components/ChordProgressionDisplay.js` imports `sampleSongData.json`, uses its C–Am–F–G sequence for every song and advances with a separate 120 BPM timer. That code is a display prototype. It cannot identify which algorithm the founder used in his subsequently deleted analysis experiment.

Chordify is evidence that automatic charts can support a useful product, but it is not evidence that any checkpoint performs equally well. Its [own technical explanation](https://chordify.net/pages/technology-algorithm-explained/) describes trained deep neural networks for chord recognition and beat tracking and an internal research team. Its [company history](https://chordify.net/pages/about/) describes building its initial algorithm from chord-recognition research. These descriptions do not disclose its current model, weights or an independently comparable accuracy figure.

## Failures hidden by an average

The initial four-model synthetic results include the following concrete diagnostics:

| Candidate | Case / observation | Product implication |
|---|---|---|
| ChordMini | `l1-harmonic-015`: generated G minor is labelled `N` for the entire recording | A strong average still includes completely missed chords |
| ChordMini | `l2-sine-024`: C and F recognised, Am/G substantially missed; inverted F minor in `l2-inversion-029` can become D-flat major seventh | Check timbre/voicing robustness on real instruments |
| BTC | `l1-harmonic-021`: generated B-flat minor becomes `N`; spread voicings and distortion are weaker conditions | Inspect individual failures rather than trusting a single mean |
| Baseline | Seventh-chord cases average about 27.7% root agreement; roughly five extra segments per case across the original suite | Correct triads alone do not make a stable, useful display |
| CREMA | High-register and half-second changes are weak; short events can be merged or skipped | Check real-recording inputs and decoding before deciding whether it is useful |
| Chordino | All clean voiced triads recognised, but first changes can be early, ending silence is missed and half-second changes are merged | Preserve separate harmony and timing/silence checks |

These are procedural tones, not physical guitar performances. They are diagnostic failures, not estimates of failure frequency in songs. A chord-only major/minor metric now excludes reference silence and ambiguous power chords, so a model labelling everything `N` cannot receive credit for chord recognition from the silent intro/outro. The earlier core metric is retained for comparison and includes silence. Power-chord spans use root/acceptable-label comparisons because no third establishes major/minor quality.

## Bounded real-recording gate

1. **Completed:** select a small annotated acoustic-guitar pilot before looking at model outputs. Check recording permission, timing issues, annotation meaning and possible training overlap. The preselected GuitarSet pilot is a diagnostic set, not proof of generalisation to commercial mixes.
2. Compare the same prepared microphone audio across candidates. Evaluate performed and intended harmony separately where supplied; do not quietly replace a difficult reference with one that improves the score. Preserve the original annotations, source hashes and normalization decisions.
3. Extend to the planned 12–20 excerpts: actual guitar, distorted rhythm, power chords, sparse and dense mixes, fast/slow changes, silence and awkward rhythm. Reserve recordings/performers for final validation. Check a subset of chord labels and audible changes manually. Use mir_eval where its vocabulary matches the reference; preserve chord-only coverage and per-recording failures.
4. Compare raw detection with one bounded stability/arrangement treatment on separate development material. Measure missed changes as well as removed flicker. Beat alignment is a candidate treatment, not permission to force every change onto a beat.
5. Assign the founder a concrete 15–20 minute session: one suitable excerpt, anonymous candidate charts and a manually checked control, with questions about wrong chords, late changes and ease of following. No guitar work is assigned during the automated screen.

For a **curated learning path**, the practical first release can use automatic drafts with checked, cached arrangements. Track correction effort per minute of audio and recurring failure conditions. A chart with a few cheap corrections can be viable even if raw transcription is imperfect. For unrestricted “analyse any song”, reliability needs broader evidence and an easy correction workflow. Raw labels are also insufficient to generate accompaniment: bass motion, beat/section timing and playable voicings require separate validation.

The next priority is [chart-assisted alignment](CHART_ALIGNMENT.md) for known catalogue entries. Use reviewed, version-matched ordered chord sequences and key references as declared inputs; keep audio-only recognition as a control and verification signal. Measure actual boundaries and section drift, including corrupted charts, rather than treating online consensus as timing ground truth. Record one-time preparation/correction cost per recording and arrangement. No alignment benchmark has been run yet.

Do not spend months trying every published model before testing real music. Chordino screening and the first real-recording pilot are complete; use larger representative recordings to narrow the shortlist, and revisit newer architectures only if a concrete quality, vocabulary or runtime gap remains. “Ready” means useful charts for the target practice repertoire at an acceptable correction cost, followed by successful play-tests; it is not a universal synthetic percentage threshold.

## Website's role

The local website is an optional diagnostic viewer. The agent handles automated runs and reports; the founder can listen or inspect charts but has no current test assignment. A later guitar session must identify the exact recording, charts, task and feedback questions first.
