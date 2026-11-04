# Wonderwall: frozen teacher-section alignment hypothesis

**Status: unaccepted research output; the default player and its raw CREMA draft remain unchanged.** On 11 October 2026, the existing spectral and native NNLS aligners processed one source-informed full-song hypothesis plus two deliberate controls. Richer labels fit these acoustic features better than the simplified control, but the reversed section order also returned high coverage and complete progress. This does not establish correct chord qualities, section locations or timestamps.

## Exact recording and untimed hypothesis

The experiment uses the saved prepared audio for [Oasis' official video](https://www.youtube.com/watch?v=bx1Bh8ZvH84), not newly downloaded or embedded playback:

- Recording ID: `oasis-wonderwall-youtube-20261010`.
- Prepared WAV: `experiments/generated/youtube-pilot/cases/oasis-wonderwall-youtube-20261010/audio.wav`.
- SHA256: `88e1649a3efa33647b8a07a7fc5feab2540c588ce35e2f27a3a682f2c4553462`.
- Exact duration: 277.78031746031746 seconds; mono 22050 Hz PCM16.
- Fixture: `experiments/fixtures/section-charts/wonderwall-full-guided.json`, version 0.1.0, `untimed-chart-1.1`, 167 expanded harmonic positions.

[Greg Shute's teacher chart](https://www.gregshuteguitar.co.uk/_files/ugd/4079b4_0a1b39a89c1a4776a5c8f553f259cb08.pdf), checked on 11 October 2026, supplies capo-2 shapes, a first-verse variation, a passing G/F# bass, and section/repeat notation. [Carl Brown's lesson description](https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/) independently confirms standard tuning, capo 2 and F# minor, and discusses variation and combined overdubs; its page text does not confirm the full repeat counts.

The supplied sounding vocabulary is F#m7, A, Esus4, B7sus4, Dadd9 and A/G#. Played shapes are preserved separately. The existing aligner supports these labels but deliberately ignores slash-bass voicing; A and A/G# have identical templates. Neither key nor capo metadata changes the acoustic path.

The fixture declares finite intro, verse, bridge and chorus order. Unnumbered repeat signs mean two total performances in this hypothesis; final `x8` means eight total performances of the written chorus line. These interpretations are frozen assumptions, **not verified counts for the exact video edit**. Consecutive held A7sus4 bars and the final continuing Em7 are not manufactured harmonic changes. Drum fill and guitar embellishment boundaries are not separately supplied. No lyrics, source PDF, beat durations, chord timestamps or gold section anchors are included.

## Frozen run and controls

All six outputs use the existing aligner 0.2.0 defaults: 25 ms requested hop, 180 ms requested spectral window, 150 ms minimum chord interval, transition penalty 0.12, unknown cosine threshold 0.45, mismatch margin 0.30, 600-second bound. Finite start-first/end-last constraints force ordered progress. PCM rounding gives a 24.9887 ms grid and about 174.921 ms minimum interior dwell. No parameters, repeats or labels were tuned against model timestamps or the resulting path.

NNLS evidence was extracted once by the existing frozen native adapter, with no chart/reference consumed. It uses approximately 93 ms native hop and 743 ms support at this sample rate; interpolation to the decoder grid does not add native timing precision. The saved evidence includes build revisions, binary hashes and extraction runtime (1.066 seconds in this run).

- **Guided:** the declared richer teacher-section hypothesis.
- **Reversed order:** the same section definitions and total position count, with the entire order list reversed. Deliberately implausible structure; never a playback candidate.
- **Simplified quality:** identical order/count, with F#m7→F#m, Esus4→E, B7sus4→B, Dadd9→D and A/G#→A. This removes characteristic qualities/bass; it is a control, not an alternative accepted arrangement.

| Input / features | Labeled coverage | Active mismatch | Positions under 300 ms | Positions at dwell floor | Median proposed dwell | Visited / supplied |
|---|---:|---:|---:|---:|---:|---:|
| Guided / spectral | 85.4% | 5.12% | 32 | 19 | 1.249 s | 167 / 167 |
| Guided / NNLS | 88.6% | 1.57% | 33 | 24 | 1.324 s | 167 / 167 |
| Reversed order / spectral | 84.3% | 6.38% | 95 | 91 | 0.175 s | 167 / 167 |
| Reversed order / NNLS | 87.3% | 3.05% | 101 | 99 | 0.175 s | 167 / 167 |
| Simplified quality / spectral | 76.0% | 15.56% | 42 | 33 | 1.224 s | 167 / 167 |
| Simplified quality / NNLS | 82.9% | 7.88% | 43 | 38 | 1.249 s | 167 / 167 |

Coverage is the fraction of exact WAV duration assigned a supplied chord rather than N/X. Active mismatch excludes PCM-silent frames. These are decoder diagnostics, **not chord or boundary accuracy**. All outputs are `needs_review`, with zero unvisited positions and 166 forced transitions. Completion is expected from the endpoint constraints; it is not a passing gate. Dwell bins are descriptive inspection thresholds, not calibrated error labels.

## Why the result remains unaccepted

The reversed NNLS input consumes **80 proposed positions entirely without active acoustic frames**. It still completes and has only 3.05% active mismatch, while 101 positions last under 300 ms. This is a direct warning against accepting a chart through completion, objective value or low mismatch alone: neutral silence emissions allow forced progress before useful harmonic evidence.

The guided NNLS path has 33 positions under 300 ms and two positions entirely without active frames. Its first two declared intro occurrences span 0–26.663 and 26.663–41.631 seconds; one later eight-position verse occurrence is compressed to 63.621–71.093 seconds. These are proposed bounds, not verified sections. The first proposed F#m7 interval lasts 17.242 seconds and includes source silence; the final interval lasts 16.873 seconds. Long spans can contain held chords, silence or chart drift, so length alone cannot declare them wrong.

Adjacent A→A/G# and chorus-ending F#m7→verse-starting F#m7 pairs are acoustically indistinguishable in the current templates. Section names and counts come from the input. The decoder cannot discover their correctness or time identical-chord rearticulation.

Gap masking also flickers independently of the minimum proposed dwell. Guided spectral produces 462 output events including 134 X gaps, 117 shorter than 150 ms. Guided NNLS reduces that to 247 events with 22 X gaps, 13 shorter than 150 ms. The mask's short gaps would need a separate, validated presentation/abstention policy before serving as learner-facing changes; smoothing them without evaluation would not make the underlying timing correct.

The richer-quality input has less mismatch and greater labeled coverage than its simplification. That supports retaining the vocabulary for further controlled research. It does **not** prove every extension exists at each predicted position, nor validate this teacher arrangement against the recording. There is no independent full-song chord/timing reference consumed or scored here. No founder transcription task is added; normal play-along and optional one-tap feedback remain the user workflow.

## Artifacts and reproduction

The tracked wrapper `experiments/analysis/wonderwall_guided.py` builds both control inputs deterministically, runs all six alignments through the existing decoder, and writes the diagnostic report. It requires the exact prepared WAV and frozen native assets from [the YouTube import](YOUTUBE_IMPORT.md) and [NNLS setup](NNLS_CHROMA_EVIDENCE.md); it does not download new audio. Code and fixture are tracked, while audio and generated results remain local research assets.

Original outputs are retained under `experiments/generated/wonderwall-guided-20261011/`. `summary.json` is the original run report. The tracked wrapper separately validated these unchanged cached outputs and produced `verified-summary.json`: exact source/audio/module hashes, deterministic control bytes, decoder arguments and NNLS evidence pairing all matched. The original six outputs and their recorded runtimes remain the evidence for the table above; this verification did not rerun or tune the aligner.

Reports retain each output/input hash, aligner/adapter/wrapper hashes, frozen arguments, section intervals, dwell compression, no-active-frame progress, gap counts and acceptance status. `nnls-evidence.json` retains native extraction/build provenance. `guided-{spectral,nnls}.json`, `reversed-order-{spectral,nnls}.json` and `simplified-quality-{spectral,nnls}.json` retain complete acoustic/path evidence. The two control input JSONs are saved alongside their results.

From the repository root, reproduce the experiment in a **new output directory**:

```sh
.venv-analysis/bin/python experiments/analysis/wonderwall_guided.py run \
  --audio experiments/generated/youtube-pilot/cases/oasis-wonderwall-youtube-20261010/audio.wav \
  --chart experiments/fixtures/section-charts/wonderwall-full-guided.json \
  --output experiments/generated/wonderwall-guided-reproduction-001
```

This builds both controls, extracts frozen native evidence, runs spectral and NNLS for each input, and writes `summary.json`. An optional `--evidence-json` accepts already cached native evidence only after exact audio/recording validation, and preserves those input bytes in the new output directory. The wrapper pins source, audio and decoder/adapter identities; a changed fixture, different recording or changed implementation requires a separately versioned experiment rather than silently entering this frozen reproduction.

To inspect the original saved run without rerunning inference, write a **new report file**:

```sh
.venv-analysis/bin/python experiments/analysis/wonderwall_guided.py summarize \
  --directory experiments/generated/wonderwall-guided-20261011 \
  --output experiments/generated/wonderwall-guided-20261011/verified-summary-new.json
```

The summary command verifies source and output pairing, both deterministic control inputs, frozen arguments and acoustic evidence before computing diagnostics. Both commands refuse existing outputs; protected inputs cannot be replaced. The run command removes only its newly created incomplete output on failure. The optional cached-evidence path and summarize mode never alter original outputs.

Four focused checks cover source mutation/timestamp rejection, deterministic control identities and counts, refusal to simplify unknown/no-chord labels, and protection of an existing output directory or symlink:

```sh
.venv-analysis/bin/python -m unittest discover \
  -s experiments/analysis/tests -p test_wonderwall_guided.py -v
```

All four checks passed. Existing cached six-case validation passed without new dependencies. Public access to teacher material and successful local acquisition do not establish commercial redistribution rights.
