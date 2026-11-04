# Starter-four catalogue check

Results from 14 October 2026; files, regression checks and local services reverified on 16 October 2026. **The four starter songs have completed a bounded pitch-class/palette check and source follow-up.** Four developer drafts now hold setup/rhythm notes; Dylan has two **provisional** G-label replacements. Stage 2 remains in progress: no recording arrangement, physical change timing, section map, capo/tuning, accuracy score or human correction cost is accepted. [Evidence and pinned artifacts](STARTER_FOUR_CATALOGUE_CHECK.json).

## What the pitch check found

All 12 uniform pitch-class shifts were compared using original-audio spectral features and frozen NNLS-Chroma. Each method scores the nearest chord in the source palette, with exact duration weights on nonsilent, nonzero evidence. The full recordings and every 20-second window are retained, alongside four fixed coverage samples per song. The four-song run took **4.1 seconds** on the existing Mac setup; this is analysis runtime, not curation time or a hosting estimate.

| Recording | Proposed shape palette | Best whole-recording shift, both methods | Zero-shift cosine: spectral / NNLS | Local investigation still needed |
|---|---|---:|---:|---|
| Wild Thing | A / D / E | 0 | 0.659 / 0.777 | Spectral 60–80 s prefers +5; NNLS stays at zero. Outside-palette C/Em/G cues remain unresolved. |
| Love Me Do | G / C / D | 0 | 0.632 / 0.739 | Several windows prefer +5 or +7; the last short window is unscored. A/Em/Cm cues remain unresolved. |
| Knockin' on Heaven's Door — Dylan | G / D / Am / C | 0 | 0.737 / 0.875 | All 20-second windows prefer zero, but two native Gm cues prompted the targeted check below. |
| Twist and Shout — Beatles | D / G / A | 0 | 0.657 / 0.810 | Some later windows prefer +7. Short F#m/Dm/Bm cues remain unresolved. |

These are **uncalibrated acoustic compatibility scores**, not confidence or percentages correct. Local shifts can reflect shared chords, missing palette material, vocals, bass or harmonics; they do not establish a key change. A preferred relative shift of zero cannot identify physical standard tuning, absence of a capo, octave or guitar voicing. All four capo observations remain unknown, with zero only proposed. NNLS compensates global tuning and supplies no cents/concert-pitch finding.

Raw BTC/source-palette family membership is 97.1–98.9%; CREMA is 100% on eligible harmonic-family time. Those figures exclude N/X, unsupported labels and gaps, and ignore selected extensions/inversions. They describe model/palette membership, not accuracy. Suspensions remain distinct from major/minor thirds; an optional richer grip is not an error merely because the entry palette is simpler.

**Controls:** four independently declared MIDI-note recordings × two feature methods produced **eight passing expected-behaviour checks**: zero shift, +2 transposition direction, silence with no score, and a single C chord retaining ambiguous shifts 0/+5/+7. Missing-minor and wrong-third diagnostic comparisons are also saved. These procedural controls validate mechanics; they are not real-guitar or song-accuracy evidence.

## Targeted Dylan investigation

The exposed native BTC cues are **[29.473741496598638, 30.27863945578231)** and **[50.185759637188205, 51.02167800453515)** seconds, both labelled Gm. Their bounds were fixed before the targeted run. Existing pinned four-stem Demucs processed the exact full recording on CPU with one thread, shifts 0 and overlap 0.25: **135.9 seconds model inference / 144.0 seconds total**.

The table shows direct **G cosine minus Gm cosine** on matched active support. Positive favours the G template; negative favours Gm. Neither sign is a performed-harmony reference.

| Native cue | Backend | Original | Resampling/PCM control | Minus estimated vocals | Estimated other |
|---|---|---:|---:|---:|---:|
| 29.474–30.279 s | Spectral | −0.204530 | −0.204529 | +0.016232 | +0.035116 |
| 29.474–30.279 s | NNLS | −0.313040 | −0.313038 | +0.175143 | +0.178530 |
| 50.186–51.022 s | Spectral | −0.151760 | −0.151759 | +0.012292 | +0.022815 |
| 50.186–51.022 s | NNLS | −0.358125 | −0.358124 | +0.234835 | +0.250001 |

Both derivatives change the preference in both methods at both cues, while preprocessing alone changes the margin by at most **0.00000204** and preserves its sign. Own and matched support cover each entire cue—0.804898 and 0.835918 seconds—with **zero support lost**. The shared PCM scale is 1.0, with no clipping; native stereo and mono FLOAT derivatives are preserved, and all analysis copies retain exact frames and time coordinates. `other` contains mixed instruments and artifacts, not an isolated guitar.

An independent audit rebuilt spectral features from actual PCM, rescored saved C-first NNLS evidence and verified source/protocol/checkpoint/module pins plus **17 output hashes**. All **256 cue-score scalars** reproduce within **3.33 × 10⁻¹⁶**. FLOAT/PCM encoding, quantization diagnostics and native original-minus-vocals construction also match. This numerical reproduction did not rerun Demucs.

The result supports investigating vocal influence and a source-guided G interpretation. It does not prove which performed guitar chord is present or verify the native boundaries. The two G replacements are therefore **provisional editorial proposals in the developer working copy only**, at the unchanged native bounds. Raw charts, the learner's audio/chart pack and ordinary playback remain unchanged. Original audio remains the default workflow. The first targeted attempt was stopped before results publication to correct inherited protocol metadata; its protocol remains preserved separately.

## Teaching proposals and saved drafts

The additive [source review](../catalogue/starter-four-teaching-review.json) keeps teacher arrangements separate from exact-recording evidence. No complete charts, lyrics, tabs, teacher timestamps or bar/repeat counts were imported.

| Song | Source-supported variation and untimed practice tasks |
|---|---|
| Wild Thing | Keep paired attacks/holds separate from contrasting G/A material; A5/D5/E5 is an optional adaptation. Explicit standard-tuning lesson support comes from [Carl Brown](https://guitarlessons365.com/wild-thing-guitar-lesson-the-troggs/); [Lauren Bateman](https://www.laurenbateman.com/wild-thing-chord-chart/) describes additional material beyond the main palette. |
| Love Me Do | Distinguish a deliberate mute from a skipped attack; add qualitative swing and locate the longer hold and D-led middle before creating timed cues. [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-01-love-me-do) and [Brad Litton](https://www.simpleguitar.com/blog/howtoplaylovemedo) support these teaching tasks. Optional Cadd9 and transposed adaptations remain separate proposals. |
| Dylan | Preserve optional Am7 and gradually added attacks; treat fingerstyle as a separate adaptation and locate alternating Am/C response material. [Song Notes](https://songnotes.net/lessons/88/) supports the richer option; [Jon MacLennan](https://www.jonmaclennan.com/blog/knockin-on-heaven%27s-door-chords) supplies standard-tuning/subdivision guidance. His displayed Am/ii7 theory mismatch is excluded. |
| Twist and Shout | Separate the main response groove, sustained A build-up, solo and ending; repeated downstroke eighths differ from the current alternating drill. [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-02-twist-and-shout) and [Jon MacLennan](https://www.jonmaclennan.com/blog/twist-and-shout-chords) support these tasks and optional D5/A7 variants. Other performers' arrangements remain separate. |

All four private developer drafts are saved with exact audio/native-chart identity and revision protection. They contain source notes; only Dylan has chord replacements. There are **no timed section edits** or accepted arrangements. The [versioned editorial proposals](../catalogue/starter-four-curation-proposals-v1.json) preserve the provisional content separately from local private draft files. Recorded agent sessions measure UI draft entry only; research, inference and musical validation are excluded. Human correction effort and total curation cost remain unmeasured.

## Reproduce and continue

From `/Users/davidcrompton/Documents/music-os`, these commands reuse the frozen specification and cached song inputs. Each output directory must be unused; existing outputs are never overwritten:

```sh
.venv-analysis/bin/python experiments/analysis/catalogue_palette_controls.py \
  --output experiments/generated/catalogue-palette-controls-replay

.venv-analysis/bin/python experiments/analysis/catalogue_pitch_check.py \
  --pack experiments/generated/catalogue-curation-20261014 \
  --spec experiments/fixtures/catalogue-starter-four-v1.json \
  --output experiments/generated/catalogue-starter-four-pitch-replay
```

They need the existing pinned native NNLS host, but no fresh audio acquisition or neural chord-model inference. Saved reports can be inspected without rerunning extraction. The completed separation pack is `experiments/generated/catalogue-dylan-separation-v2-20261014`; a new separator run uses `catalogue_targeted_separation.py prepare` followed by `run --expected` with the exact hash printed by preparation and a fresh pack. The existing completed pack cannot be overwritten.

The [developer reviewer](http://127.0.0.1:8073/) shows these drafts. [Ordinary practice](http://127.0.0.1:8070/) remains available. Regression verification passes **368 of 388 Python checks**, with 20 optional-dependency skips, and **124 JavaScript checks**. All 39 Stage 1 frozen pins, 45 reviewer assets and 48 retained learner assets are verified.

Remaining Stage 2 work is independent recording/arrangement review: physical change timing, section coverage, audible suitability of played shapes and rhythm, plus genuine correction effort. Keep unresolved cues visible and check the other six songs before accepting a catalogue. The next actual arrangement pass remains an indicative **1.5–2.5 focused days**, excluding source delays; the ordinary-practice usefulness trial is Stage 3. No founder transcription task or current founder input is required to continue technical work.
