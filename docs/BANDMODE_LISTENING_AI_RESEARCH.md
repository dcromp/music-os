# Band mode: AI that understands and follows a player's recorded guitar

Research for [#66](https://github.com/dcromp/music-os/issues/66) (part of #64).
Written by an AI agent (Claude Code) on 27 October 2026; every web source was
checked on that date. Evidence comes from primary sources: papers, official
repositories, model cards, vendor docs and help pages. Where only a secondary
source was available, or a claim could not be confirmed, the text says so.
**This note makes no product decisions.**

Band mode context: an editable songwriting DAW, first as an iPhone web app.
The player records guitar (and maybe voice) through a USB audio interface, and
an AI band follows the player's song.

## Short answer

- **Offline analysis of a clean, solo guitar take is the mature part.** Open
  models give note transcription (audio to MIDI), beats and tempo, major/minor
  chords and key. Small versions can run in a browser. Solo-guitar accuracy is
  good for notes and strummed chords. It is weak for chords implied by a single
  melody line and for bar and downbeat placement.
- **Sections (verse/chorus) from a recording** exist in research models trained
  on full band mixes. Nobody has measured them on a lone guitar.
- **Live following** splits three ways. Products that follow tempo exist
  (Ableton's Tempo Follower). Score followers exist for written classical
  pieces (Antescofo/Metronaut). Generative, adaptive accompaniment that listens
  to a player is still research (ReaLchords, ReaLJam, Magenta RealTime). No
  product found improvises a band around an unknown guitar part in real time.
- **"AI bandmates generated from my recording"** ships as *offline* features:
  Moises AI Studio and Suno Studio generate parts after you record. Logic Pro's
  Session Players follow a chord track and can follow another track's rhythm.
- **Voice:** humming to notes works through monophonic pitch trackers and
  Basic Pitch, with lower accuracy than on instruments. On full songs, Whisper
  lyric transcription has about 35% word error. Specialised systems do better,
  but none of these are songwriting-grade.
- **This repo:** BTC, CREMA and librosa were chosen and validated on recordings
  much like a player's own clean strummed guitar (GuitarSet). They are offline
  Python/PyTorch/TensorFlow tools that need porting, or a server, to work on a
  phone. Demucs and YAMNet matter less for a single-instrument DI recording.

## 1. Understanding a recording

### 1.1 Note transcription (audio to MIDI)

| Tool | Output | Solo-guitar accuracy (dataset) | Runtime | Licence | Maturity |
|---|---|---|---|---|---|
| **Spotify Basic Pitch** | MIDI notes with pitch bends; note CSV ([repo](https://github.com/spotify/basic-pitch)) | GuitarSet note F (no offset) **0.79**, with offsets 0.56, frame accuracy 0.70 ([paper, Table 2](https://arxiv.org/abs/2203.09893)); 79.0% in the GAPS comparison ([GAPS Table 3](https://arxiv.org/html/2408.08653v2)) | Only **16,782 parameters** (paper §3). Python with TF, CoreML, TFLite or ONNX back ends ([repo](https://github.com/spotify/basic-pitch)). TypeScript port [basic-pitch-ts](https://github.com/spotify/basic-pitch-ts). Web demo at [basicpitch.spotify.com](https://basicpitch.spotify.com/) loads a model in the page. | Apache-2.0 | Shipping open source. "Works best on one instrument at a time" ([repo](https://github.com/spotify/basic-pitch)). |
| **GAPS model** (Riley et al., ISMIR 2024) | Notes with onset, offset and velocity (CRNN after Kong et al.) | GuitarSet F1 87.2–91.2% supervised and **86.1–88.1% zero-shot** ([paper, Tables 3–4](https://arxiv.org/html/2408.08653v2)) | Python/PyTorch, size not stated | Paper says weights were "under consideration" for release; no code licence stated | Research-grade, classical-guitar focus |
| **MT3 / YourMT3+** | Multi-instrument MIDI tokens | MT3 90.0% supervised on GuitarSet, but **32.0% zero-shot** ([GAPS Tables 3–4](https://arxiv.org/html/2408.08653v2)). YourMT3+ reports gains on Slakh and URMP and notes that current models are weaker on pop recordings ([paper](https://arxiv.org/abs/2407.04822)). | Large transformer, GPU demos ([repo](https://github.com/mimbres/YourMT3)) | YourMT3: GPL-3.0 ([repo](https://github.com/mimbres/YourMT3)) | Research-grade; server-class |
| **Klangio Guitar2Tabs** | Tab, MIDI, MusicXML, GP5 from guitar audio; note editor ([App Store](https://apps.apple.com/app/id1589660528), [MuseHub](https://www.musehub.com/app/guitar2tabs)) | No published benchmark found | Cloud or app; listings say "not real-time" | Commercial | Shipping product |

Limits. GuitarSet is clean, solo acoustic guitar, the closest public match to a
DI or mic take. Distorted electric guitar is not covered by these numbers.
Supervised scores on GuitarSet can be inflated by training on GuitarSet, so the
zero-shot column is the fairer guide for a new player
([GAPS](https://arxiv.org/html/2408.08653v2)). String and fret (tab) assignment
is a separate problem; Basic Pitch outputs pitches only.

### 1.2 Tempo, beats, downbeats and bars

| Tool | Output | Evidence | Runtime | Licence | Maturity |
|---|---|---|---|---|---|
| **librosa** tempo-guided tracker (this repo) | Beats, tempo | In-repo GuitarSet: whole-recording beat F1 63–67% at 70 ms and 76–81% at 150 ms; one single-note solo take scored 17% ([FRESH_GUITARSET_RHYTHM_CHECK](FRESH_GUITARSET_RHYTHM_CHECK.md)) | Python, offline | ISC | Mature |
| **Beat This!** (ISMIR 2024) | Beats and downbeats, no DBN needed | Paper tables; the README warns that scores on training sets are optimistic ([repo](https://github.com/CPJKU/beat_this)). In this repo, duration-count error on nominal guitar was 0.545 beats against librosa's 0.084 ([ALGORITHM_SELECTION](ALGORITHM_SELECTION.md)). | PyTorch, offline (non-causal). Checkpoints about 78 MB, small about 8.1 MB ([repo](https://github.com/CPJKU/beat_this)). | MIT (code and weights) | Usable open source |
| **BeatNet** (ISMIR 2021) | Beats, downbeats, tempo, meter. Streaming, real-time, online and offline modes ([repo](https://github.com/mjhydri/BeatNet)) | Claims to beat other online trackers and come close to an offline baseline on GTZAN; the abstract gives no numbers ([paper](https://arxiv.org/abs/2108.03576)) | PyTorch with a particle filter; mic streaming through PyAudio | CC-BY-4.0 | Research-grade, usable |
| **madmom** | Beats and downbeats (offline and `online` mode); chord and key models in its references ([repo](https://github.com/CPJKU/madmom)) | Long-standing MIREX-era methods | Python/C | Code BSD; **models CC BY-NC-SA 4.0**, commercial use by contacting the authors ([repo](https://github.com/CPJKU/madmom)) | Mature, ageing |
| **All-In-One** (WASPAA 2023) | Tempo, beats, downbeats, bar positions, **section segments and labels** (intro, verse, chorus, bridge, solo…) ([repo](https://github.com/mir-aidj/all-in-one)) | Trained on the Harmonix Set (band mixes); the README gives no numbers | PyTorch with NATTEN and Demucs-style demixed input; GPU benchmark 33 min of audio in 73 s on an RTX 4090 | MIT | Research-grade, server-class |
| **Essentia.js** | `BeatTrackerMultiFeature`, key, `ChordsDetection`/`ChordsDetectionBeats` and more ([API](https://mtg.github.io/essentia.js/docs/api/Essentia.html)) | Classic DSP methods; no solo-guitar figure found | **Browser WASM**, plus TF.js add-ons ([site](https://mtg.github.io/essentia.js/)) | **AGPL-3.0**; MTG models CC BY-NC-SA 4.0 or proprietary on request ([models](https://essentia.upf.edu/models.html)) | Usable; "under rapid development", APIs may change |

Limits. Downbeats and bar numbers are the weak point. This repo excluded
inferred downbeats and numbered bars because holdout predictions produced many
extras ([ALGORITHM_SELECTION](ALGORITHM_SELECTION.md)). A songwriter's take may
drift in tempo with no drums to anchor it. A player-supplied click or a count-in
removes most of the problem; that design option is noted here, not decided.

### 1.3 Chords and key

| Tool | Evidence on guitar | Runtime | Licence |
|---|---|---|---|
| **BTC-ISMIR19** (selected here) | Strummed guitar, major/minor: 84.0% (six-take pilot) and 92.0% (four fresh takes). **Single-note solos: 12.5%** contextual harmony ([ALGORITHM_SELECTION](ALGORITHM_SELECTION.md), [FRESH_GUITARSET_CHORD_CHECK](FRESH_GUITARSET_CHORD_CHECK.md)) | PyTorch, ~12 MB checkpoint, CPU ([BTC_SETUP](BTC_SETUP.md)) | MIT (repo) |
| **CREMA** (Strum Along's chart source) | 93.9% and 86.3% on the same sets; solos 7.6% | TensorFlow/Keras 2; ~0.29 s per file after a slow cold start on a Mac ([CREMA_SETUP](CREMA_SETUP.md)) | BSD-2-Clause |
| **Essentia.js** `ChordsDetection`, `KeyExtractor` | No solo-guitar figure found | Browser WASM | AGPL-3.0 |
| **Chordify** (product) | Upload your own audio to get a beat-aligned chord chart; live mic chord detection on Premium Plus ([help](https://support.chordify.net/hc/en-us/articles/360002164538-How-to-use-Premium-features)) | Cloud | Commercial |

Key estimation is offered by Essentia, madmom and others. No solo-guitar key
accuracy was found to cite. Key is easier than chords in principle, but it is
unverified here.

Two alternatives were not verified. From a note transcription (1.1), chords
could be read by symbolic analysis. Or the player could tell the app the chords
and let audio only time them. This repo found that known-chart alignment is not
yet reliable ([ALGORITHM_SELECTION](ALGORITHM_SELECTION.md)).

### 1.4 Sections

All-In-One (1.2) is the only open model found that labels verse and chorus from
audio. It was trained on band mixes, and its solo-guitar behaviour is unknown.
Repetition-based segmentation (for example on chroma) is a classic technique.
No solo-guitar evaluation was found.

## 2. Running it on an iPhone, in a browser

| Building block | Status (27 Oct 2026) |
|---|---|
| **WebGPU in Safari** | Shipping since Safari 26.0 on iOS and iPadOS ([WebKit, Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)). Requires iOS 26 or later ([WebKit bug 299237](https://bugs.webkit.org/show_bug.cgi?id=299237)). |
| **ONNX Runtime Web** | WASM (supports all operators) plus WebGPU, WebGL and WebNN, which each support a subset. Its guidance is to keep browser models small ([docs](https://onnxruntime.ai/docs/tutorials/web/)). |
| **Transformers.js** | Runs ONNX models in the browser, including speech recognition, on WASM by default or on WebGPU ([docs](https://huggingface.co/docs/transformers.js/index)) |
| **Essentia.js** | WASM in browsers ([site](https://mtg.github.io/essentia.js/)) |
| **Demucs in a browser** | Community ONNX/WebGPU ports exist. One reports ~22× real time on a desktop Radeon GPU ([htdemucs-web-onnx](https://huggingface.co/monteslu/htdemucs-web-onnx)); [demucs-rs](https://github.com/nikhilunni/demucs-rs) is a WASM/WebGPU build that its author says is slower than native. No iPhone figures. The v3/v4 weights are reportedly CC BY-NC 4.0 ([demucs-onnx note](https://huggingface.co/HRSadeghi/demucs-onnx)); not verified against Meta's repo. |
| **USB interface input in Safari** | Open WebKit bugs: with echo cancellation off, a mono device can arrive as stereo with only the left channel filled, and `channelCount` is ignored ([bug 281978](https://bugs.webkit.org/show_bug.cgi?id=281978), [Apple forum](https://developer.apple.com/forums/thread/804765)). Echo cancellation is on by default. Round-trip latency on an iPhone with an interface was **not measured or found**. |

Not verified: whether Basic Pitch's web demo runs fully on-device on an iPhone.
Also unverified: how much memory iOS Safari allows a tab for models of this
size, and BTC or CREMA converted to ONNX (no conversion was found). A 16 k
parameter model like Basic Pitch is plausible on a phone. Separation or
transformer transcription on a phone is unmeasured.

## 3. Real-time listening and responding

| System | What it does | Kind |
|---|---|---|
| **Ableton Live Tempo Follower** | Follows the tempo of an audio input; best with a clear rhythm; cannot be used with Link or external sync ([manual](https://www.ableton.com/en/live-manual/11/synchronizing-with-link-tempo-follower-and-midi/)) | Shipping (desktop) |
| **Logic Pro Session Players** | Drummer, Bass and Keyboard players take chords from the Chord track and can "Follow Rhythm Of" another track; not live listening ([Logic for iPad guide](https://support.apple.com/guide/logicpro-ipad/lpip87ac9913/ipados), [Sound On Sound](https://www.soundonsound.com/techniques/logic-pro-session-players)) | Shipping, offline arrangement |
| **Moises AI Studio** | Record a few bars, then generate matching drum and bass stems; adding chords improves results ([feature page](https://moises.ai/features/stem-generation); [9to5Mac, Aug 2025](https://9to5mac.com/2025/08/20/moises-app-can-now-generate-ai-bandmates-based-on-a-single-instrument-recording)). Help page returned 403; output quality was not independently tested. | Shipping, offline generation |
| **Suno Studio** | Browser "generative audio workstation": upload audio, generate stems, export audio and MIDI ([Suno](https://suno.com/blog/suno-studio)). A 2.0 update (Aug 2026) is reported only by a secondary source ([DubSpot](https://blog.dubspot.com/suno-studio-2-0)). | Shipping, offline generation |
| **Antescofo / Metronaut** | Score following plus tempo inference to synchronise electronics or accompaniment to a *written* score ([Wikipedia overview](https://en.wikipedia.org/wiki/Antescofo), [platform](https://platform.antescofo.com/)) | Shipping (classical), needs a score |
| **Music Plus One** (Raphael) | HMM score follower plus predictive orchestral accompaniment for written pieces ([project](https://music.informatics.indiana.edu/~craphael/music_plus_one/index.html)) | Research, long-running |
| **Yousician** | Listens through the mic and checks each string of a chord against the lesson ([support](https://support.yousician.com/hc/en-us/articles/202893201-Chords-are-not-recognized)) | Shipping; verifies a *known* part |
| **ReaLchords** (ICML 2024) | Online chord accompaniment to a live melody (symbolic), RL-tuned to adapt to mistakes and transpositions ([PMLR](https://proceedings.mlr.press/v235/wu24c.html)) | Research |
| **ReaLJam** (CHI EA 2025) | Live human–AI jamming: the user plays melody, a transformer plays chords and shows its plan ahead ([arXiv](https://arxiv.org/abs/2502.21267)) | Research |
| **Magenta RealTime** | Open live music generation steered by text or audio prompts; 2-second chunks, so changes take two or more seconds; no long song structure ([model card](https://huggingface.co/google/magenta-realtime)). Weights CC-BY 4.0, code Apache 2.0. A "Magenta RealTime 2" with about 200 ms control latency is reported only by blogs; **unverified**. | Research/open model, TPU or GPU |

Pattern. Products either follow tempo, follow a known score or chord track, or
generate offline after you record. Adaptive live accompaniment that follows an
unknown guitar part is research, and mostly symbolic (MIDI melody in, chords
out). No product was found that does it from live guitar audio on a phone.

## 4. Voice as a songwriting input

- **Humming or singing to notes.** CREPE is a monophonic pitch tracker that
  outputs frequency and confidence every 10 ms, MIT licensed, ICASSP 2018
  ([repo](https://github.com/marl/crepe)); no official JS build is listed.
  Basic Pitch covers vocals: on the Molina sung-melody set it scores note F (no
  offset) **0.52** and 0.35 with offsets, well below guitar
  ([paper, Table 2](https://arxiv.org/abs/2203.09893)). The weakness is note
  segmentation, not pitch. Klangio sells "Sing2Notes" (named in a
  [Runpod partner post](https://www.runpod.io/blog/klangio-ai-music-transcription-partnership));
  its accuracy was not found.
- **Lyrics.** On the Jam-ALT full-song benchmark, Whisper v2/v3 score about
  35.5–35.7% WER, AudioShake 26.0% and LyricWhiz (Whisper plus an LLM) 24.6%
  ([Jam-ALT paper](https://arxiv.org/html/2311.13987v1)). Separation used as
  voice-activity segmentation improves Whisper further
  ([arXiv 2506.15514](https://arxiv.org/html/2506.15514v1)). Those are full
  mixes; an unaccompanied voice memo is likely easier, but no figure was found.
  Whisper-family models can run in a browser through Transformers.js (§2). A
  phone-sized model's speed and accuracy on singing are unmeasured.

## 5. What this repo already has, and how it transfers

| Asset | What it showed | For a player's own recording | On a phone |
|---|---|---|---|
| **BTC chords** (selected default) | 84–92% major/minor on clean strummed GuitarSet takes; 69% on jazz ensembles; can't emit sus, power, slash or extended chords ([ALGORITHM_SELECTION](ALGORITHM_SELECTION.md)) | **Transfers best.** A player's strummed DI or mic take resembles GuitarSet comping. It fails on riffs and single-note lines (12.5%) and on power chords, which are common in rock songwriting. | PyTorch, 12 MB. Needs an ONNX port (unverified) or a server. |
| **CREMA chords** (Strum Along charts) | 86–94% on the same takes; richer vocabulary, but no add9 or 7sus4 | Same as BTC; models trade places by material | TensorFlow/Keras 2; same porting question |
| **librosa guided beats** | Approximate pulse after a known tempo/meter; no verified downbeats or bars; weak on a solo take (17% F1) | Works if the player gives the tempo (click or count-in); free-time takes are unreliable | Pure DSP; a JS equivalent (Essentia.js) exists, but it is not this tracker |
| **Demucs htdemucs_6s** | Small, uneven chord gain from separation; used to measure how guitar-led a mix is ([STRUMALONG_CATALOGUE_CHECKS](STRUMALONG_CATALOGUE_CHECKS.md)) | **Mostly unneeded.** A single-instrument interface input is already "separated". Could matter only if the player records voice and guitar on one mic. | Browser ports exist; no iPhone figures; weight licence noted as non-commercial |
| **YAMNet** | Corroborates instrument presence; its Strum class was unreliable (ranked a picked song above a strummed one) | Little use on a known DI guitar input. It could tag a take as voice, guitar or silence. | TFLite variants are offered for web and mobile ([TF docs](https://www.tensorflow.org/hub/tutorials/yamnet)); a TF.js build was not confirmed |
| **Evaluation discipline** | Frozen settings, holdouts, "verdict means no check objected" | Directly reusable for testing any Band-mode listener on the founder's own takes | n/a |

All of the repo's pipelines are offline batch tools on a Mac. Strum Along plays
cached results and runs no models on the phone (README status). Nothing here
does real-time analysis today.

## What this means for Band mode

**Possible now (open source or shipping, with evidence on solo guitar):**
- Offline audio to MIDI of a clean guitar take (Basic Pitch: GuitarSet 0.79
  note F, Apache-2.0, tiny model, TypeScript port).
- Offline major/minor chords for strummed parts (BTC/CREMA in this repo,
  84–94% on GuitarSet comping), on a server or Mac.
- Tempo and beats when the player plays to a click or gives the tempo.
- Following tempo live from audio (Ableton Tempo Follower, desktop).
- Generating backing stems after recording (Moises, Suno; offline and cloud).

**Possible with caveats:**
- Running analysis inside iPhone Safari. WebGPU and ONNX Runtime Web exist, but
  model ports, memory limits and USB-input channel bugs are unverified on a
  device.
- Chords from riffs, power chords and single-note lines (weak in every tested
  model), and key estimation (no solo-guitar figure found).
- Hum-to-notes (Basic Pitch on voice 0.52 note F; CREPE gives pitch, not notes).
- Lyrics from a voice memo (around 25–35% WER on full songs; better is likely
  on a cappella, but unmeasured).

**Research-grade:**
- Verse and chorus labels from a lone guitar (All-In-One, trained on band mixes).
- Downbeats and bar numbers on free-time solo takes.
- Higher-accuracy guitar transcription (GAPS 86–88% zero-shot; weights not
  confirmed released) and tab assignment.
- Adaptive live accompaniment (ReaLchords, ReaLJam: symbolic melody in, chords
  out) and live generative models (Magenta RealTime, seconds of latency).

**Doesn't exist (not found):**
- A product or open model that listens to *live guitar audio* and plays a band
  that follows an *unknown* song's chords and sections in real time, on a phone
  or anywhere else.
- Published iPhone-browser latency or accuracy figures for any of the models
  above.

## Not verified

- Basic Pitch running fully on-device in iPhone Safari, and its speed there.
- Demucs v4 weight licence (from a third-party model card, not Meta's repo).
- Magenta RealTime 2 details (blogs only); Suno Studio 2.0 details (secondary).
- Moises AI Studio's help-centre detail (HTTP 403); its output quality.
- Yousician's and Chordify's algorithms (their docs describe behaviour only).
- Key-detection accuracy on solo guitar; Whisper accuracy on unaccompanied singing.
