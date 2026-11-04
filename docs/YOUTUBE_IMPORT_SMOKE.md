# Three-song import and detector smoke test — 10 October 2026

**Three imports and nine detector runs succeeded.** These are the versions already listed in the old Music OS prototype. All models used the same prepared mono 22,050 Hz PCM16 WAV for each song, without separation, key assistance, beat guidance or manual corrections. Audio/hash pairing and the output schema were checked for all nine predictions.

| Recording | Prepared duration | Baseline events | CREMA events | Chordino events |
|---|---:|---:|---:|---:|
| [Radiohead — Creep](https://www.youtube.com/watch?v=XFkzRNyygfk) | 236.635 s | 2,181 | 52 | 54 |
| [Oasis — Wonderwall](https://www.youtube.com/watch?v=bx1Bh8ZvH84) | 277.780 s | 2,168 | 144 | 92 |
| [The Animals — House of the Rising Sun](https://www.youtube.com/watch?v=4-43lLKaqBQ) | 248.546 s | 1,627 | 138 | 152 |

The first two uploads identify Radiohead and Oasis as uploaders. House is from **The Animals Tribute Channel (unofficial)**. Version identity, edits and harmony still need listening review.

Event counts describe segmentation, not correctness. The unsmoothed spectral baseline produces thousands of segments on these mixes. The more stable pretrained/native outputs make better inspection candidates, but fewer events can also mean missed changes. There is no independently checked chord or timing reference for these recordings yet, so **no real-song accuracy score or production selection is claimed**.

| Recording | Baseline analysis | CREMA analysis | Chordino analysis |
|---|---:|---:|---:|
| Creep | 0.326 s | 13.885 s | 1.425 s |
| Wonderwall | 0.306 s | 8.559 s | 1.211 s |
| House of the Rising Sun | 0.287 s | 7.276 s | 0.974 s |

Creep's CREMA time includes imports and model load. The other two CREMA times are per-file feature/inference/decoding time, with **one shared 4.129-second model load** measured separately. The table is therefore not a like-for-like cold-start benchmark. Download/conversion time is excluded throughout; native Chordino loads its plugin per recording. Full versions, runtime semantics, hashes and label-duration summaries are in [the JSON evidence](YOUTUBE_IMPORT_SMOKE.json).

The initial two-song CREMA batch stopped before inference because its adapter required an annotation reference merely for a file-overwrite guard. The adapter now permits unannotated inference, retaining guards when a reference is supplied. Five focused tests passed and the unchanged model batch succeeded on retry. No reference labels were invented to make inference work.

## First chart-assisted real-song draft

Separate authored lesson pages agree on the simplified Creep loop **G → B → C → Cm**: [Andy Guitar](https://www.andyguitar.co.uk/videos/radiohead-creep), [Tom Fontana](https://www.theguitarlesson.com/guitar-lessons/creep-guitar-lesson-radiohead/) and [Carl Brown](https://guitarlessons365.com/creep-guitar-lesson-radiohead/). Source independence is plausible but unproven. These are source-informed candidate labels, not a verified sequence of sections/repeats or timestamped gold. Sus4 embellishments and changing guitar layers make the four-chord chart an intentional simplification.

With its original frozen defaults, the new aligner processed the full Creep recording in **0.427 seconds**, proposing **124 path transitions / 31 cycle wraps**. About **19.8% of active frames** triggered its acoustic mismatch rule. The final masked timeline contained **827 events**, including short `X` gaps. Those template scores are uncalibrated diagnostics, not confidence or accuracy percentages.

**This draft is unaccepted.** A four-label loop without expected repeat count or section structure permits excessive cycling on a dense mix. It demonstrates why the curated input should specify reviewed section order and repetitions, and why raw path events and unknown gaps must stay visible. No parameters were tuned on this recording, and no real timing score was calculated.

The separate [64-case synthetic alignment screen](ALIGNMENT_SCREEN.md) measures timing given the correct labels and order. Its 90.4% mean boundary F1 does not transfer to this unrestricted real-song cyclic task.

## Source-informed inputs and next steps

Three short candidate charts are committed in `experiments/fixtures/untimed-charts/`. They preserve sources and arrangement assumptions:

- **Creep:** simplified cyclic hypothesis, bound to the imported WAV hash; section order/repeat counts remain unchecked.
- **Wonderwall:** intro-only shapes Em7, G, Dsus4, A7sus4 with capo 2, supplied as sounding F#m7, A, Esus4, B7sus4. Rich suspended qualities are preserved. [Carl Brown](https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/) documents capo/key; [Greg Shute's chart](https://www.gregshuteguitar.co.uk/_files/ugd/4079b4_0a1b39a89c1a4776a5c8f553f259cb08.pdf) distinguishes sections.
- **House:** intro-only Am, C, D, F, Am, E, Am, E. Vocal cadences and the ending differ, as described by [Jonathan Richter](https://richterguitar.com/house-of-the-rising-sun-the-animals/) and [Carl Brown](https://guitarlessons365.com/how-to-play-the-house-of-the-rising-sun-the-animals/).

The intro candidates have not been forced over complete songs. Next select exact excerpts, check their audible chords/sections independently, and keep evaluation timestamps outside the aligner. Freeze a development/holdout split before adding section constraints or changing settings. Then compare reviewed-sequence alignment with the saved audio-only outputs and measure correction effort.

Imports and predictions remain local and gitignored. Successful acquisition proves technical feasibility for these experiments; it does not establish commercial clearance or any payment arrangement with YouTube. [Setup and saved-file details](YOUTUBE_IMPORT.md) describe the reproducible route.
