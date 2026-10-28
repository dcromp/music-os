# Band mode research: open-source amps, effects and starter tones for a learner

Research for [#72](https://github.com/dcromp/music-os/issues/72) (part of #64).
Done by an AI agent (Claude Code). All sources were checked on
**28 October 2026**. This note gathers facts and does not make product
decisions. It builds on the iPhone web DAW note for #67
(`docs/BANDMODE_IPHONE_WEB_DAW_RESEARCH.md` on branch
`research/bandmode-iphone-web-daw`), called "the #67 note" below.

**How the sources were read.** I took licences, activity dates and star counts
from the GitHub API on 28 October 2026. I read licence files, READMEs and
library source headers directly. I also read these pages directly:

- TONE3000's terms, API terms, sharing policy and blog posts
- Voxengo's IR page
- the Faust library sources
- the UK Trade Marks Act on legislation.gov.uk
- Marshall's beginner pages
- BOSS's pedal-order article
- the Line 6 Helix models list (PDF)
- the arXiv Slimmable NAM paper
- the Zenodo WAM guitar-rack record
- the Sound On Sound news item on Origin Effects

Some sources I saw only as search-result extracts, because the page refused the
fetch (403 or a bot wall) or was not opened. Those items are marked
*(search extract)* and are less firmly checked.

**Status key.** ✅ possible now in a web app · ⚠️ possible with caveats ·
📱 native-only · ❌ missing or not found.

---

## Summary table

| Option | What it is | Code licence | Assets licence | Runtime | Status for a web app |
| --- | --- | --- | --- | --- | --- |
| [NeuralAmpModelerCore](https://github.com/sdatkinson/NeuralAmpModelerCore) | NAM inference engine (C++) | MIT | n/a | Native C++; compiles to Wasm | ✅ via Wasm port |
| [neural-amp-modeler-wasm](https://github.com/tone-3000/neural-amp-modeler-wasm) (TONE3000) | NAM in an AudioWorklet, React player, live input | MIT | Bundled demo `.nam` and IR files: **no licence stated** | Browser (Wasm + AudioWorklet) | ⚠️ works; iOS memory fixes in Aug 2026; no phone CPU figures |
| [neural-amp-modeler](https://github.com/sdatkinson/neural-amp-modeler) | NAM trainer (Python) | MIT | n/a | Desktop/GPU | n/a (offline training) |
| TONE3000 catalogue/API | 275k+ community NAM captures and IRs | n/a | Owned by each creator; ToS bars commercial redistribution; API forbids bundling/preloading | Download per user via API | ⚠️ needs commercial agreement; can't ship as built-in presets |
| [AIDA-X](https://github.com/AidaDSP/AIDA-X) | RTNeural amp-model player plus IR cab | GPL-3.0-or-later | Model pack on Google Drive, licence not stated | CLAP/LV2/VST2/VST3/standalone | ❌ no web build found |
| [Guitarix](https://github.com/brummer10/guitarix) | Linux amp and effects suite | GPL-3.0-or-later (whole) | Bundled IRs: GPL-2.0-or-later | JACK/LV2 (Linux) | ⚠️ only its DSP, via Faust `tonestacks`/`tubes` (LGPL) |
| [Faust](https://github.com/grame-cncm/faust) + [faustlibraries](https://github.com/grame-cncm/faustlibraries) + [faustwasm](https://github.com/grame-cncm/faustwasm) | DSP language → Wasm/AudioWorklet | Compiler LGPL-2.1; faustwasm LGPL-2.1; libraries licensed per function (STK-4.3/MIT/LGPL/GPL-3.0-only) | n/a | Browser | ✅ (check each function's licence) |
| [Web Audio Modules](https://github.com/webaudiomodules/api) / [wam-examples](https://github.com/webaudiomodules/wam-examples) | Plugin standard for the web, plus example guitar pedals and amp | MIT | n/a | Browser | ✅ examples exist; maturity varies |
| [Tone.js](https://github.com/Tonejs/Tone.js) effects | Chorus, delays, reverbs, distortion, auto-wah, etc. | MIT | n/a | Browser | ✅ basic quality |
| Built-in Web Audio nodes | WaveShaper, Convolver, DynamicsCompressor, Biquad, Delay | Platform | n/a | Browser | ✅ (see #67 note) |
| [openDAW](https://github.com/andremichelle/openDAW) | Browser DAW with TONE3000/NAM device | AGPL-3.0 or paid commercial licence | n/a | Browser | ⚠️ reference only; AGPL |
| [RTNeural](https://github.com/jatinchowdhury18/RTNeural) | Real-time NN inference (C++) | BSD-3-Clause | n/a | Native; Wasm port not verified | ⚠️ unverified in browser |
| [NeuralAudio](https://github.com/mikeoliphant/NeuralAudio) | Fast NAM/RTNeural inference library | MIT | n/a | Native | ⚠️ browser use not verified |
| [BYOD](https://github.com/Chowdhury-DSP/BYOD), [KlonCentaur](https://github.com/jatinchowdhury18/KlonCentaur), [Proteus](https://github.com/GuitarML/Proteus) | Native guitar plugins | GPL-3.0 / BSD-3 / GPL-3.0 | Proteus [ToneLibrary](https://github.com/GuitarML/ToneLibrary): GPL-3.0 | Native plugins | 📱/desktop only |
| ToneLib GFX | Commercial amp/effects suite | Proprietary, $89.95 list ([tonelib.net](https://tonelib.net/tl-gfx.html)) | n/a | Desktop | ❌ not open source |
| iOS NAM apps (NAM Loader Pedal, NAM Live, Ampz) | AUv3/standalone NAM players | Proprietary | n/a | Native iOS | 📱 *(search extract)* |
| Tuner: [pitchy](https://github.com/ianprime0509/pitchy), [PitchDetect](https://github.com/cwilso/PitchDetect) | JS pitch detection | 0BSD / MIT | n/a | Browser | ✅ |
| Cab IRs: Guitarix BestPlugins | Amp/cab IRs named after real amps | GPL-2.0-or-later | — | WAV for ConvolverNode | ⚠️ GPL'd assets |
| Voxengo free IRs | Mostly reverb spaces, plus 4 "Direct Cabinet" | Free incl. commercial use; no selling or profiting from distribution | — | WAV | ⚠️ redistribution conditions |
| OpenAIR (Univ. of York) | Room/space IRs | Per-item Creative Commons | — | WAV | ⚠️ check each item *(search extract)* |

---

## 1. Amp and cab simulation

### Neural Amp Modeler (NAM)

- **What it does.** NAM is a neural-network emulator for guitar amps
  ([repo](https://github.com/sdatkinson/neural-amp-modeler)). It has three
  parts: a Python trainer
  ([neural-amp-modeler](https://github.com/sdatkinson/neural-amp-modeler)), a
  C++ core DSP library
  ([NeuralAmpModelerCore](https://github.com/sdatkinson/NeuralAmpModelerCore))
  and a plugin
  ([NeuralAmpModelerPlugin](https://github.com/sdatkinson/NeuralAmpModelerPlugin)).
- **Code licence.** All three repos are **MIT** (GitHub licence metadata, 28
  Oct 2026). The wasm port's README says the core pulls in its own Eigen,
  nlohmann and AudioDSPTools dependencies
  ([README](https://github.com/tone-3000/neural-amp-modeler-wasm)). I did not
  audit those licences separately.
- **Maturity.** The repos are active: the trainer was pushed 27 Oct 2026 and
  has about 3.1k stars, and Core v0.6.0 was released 1 Oct 2026 (GitHub API).
- **The format.** TONE3000's API terms say "The Neural Amp Modeler (NAM)
  format, including A2 and A1, is open source and free to implement in any
  product" ([TONE3000 API terms](https://www.tone3000.com/api/terms), effective
  7 July 2026).
- **Architecture 2 (A2).**
  - A2 was announced on 2 June 2026 by TONE3000 with NAM's creator
    ([TONE3000 blog](https://www.tone3000.com/blog/introducing-neural-amp-modeler-nam-architecture-2-a2)).
  - The post claims A2-Full uses "30-40% less CPU" than A1 and that A2-Lite
    runs at 50% CPU on a 600 MHz ARM Cortex-M7. It also claims A2 beat Neural
    DSP, ToneX and Line 6 Proxy in objective tests (39 tones) and in a blind
    MUSHRA test with over 1,000 participants. These are the vendor's own
    results. The post says the test code and ratings are on GitHub, which I
    did not inspect.
- **"Slimmable" models.** Atkinson's paper describes one model file whose
  width, and therefore CPU cost, can be cut at runtime without retraining
  ([arXiv 2511.07470](https://arxiv.org/html/2511.07470v1), Nov 2025). The
  PiPedal release notes report that A2 uses less CPU than A1 on Raspberry Pi 4
  ([PiPedal v2.0.102](https://newreleases.io/project/github/rerdavies/pipedal/release/v2.0.102),
  *(search extract)*). This matters for phones: one file could be run smaller
  on a weak device.

### NAM in the browser (TONE3000 `neural-amp-modeler-wasm`)

- **What it does.** TONE3000's README calls it a WebAssembly port of
  NeuralAmpModelerCore, "enabling real-time audio amp modeling directly in the
  browser". The npm package includes the engine, a React player that supports
  "live input through an audio interface", and an iframe embed
  ([repo](https://github.com/tone-3000/neural-amp-modeler-wasm)). The licence
  is **MIT**. The repo was last pushed 27 Oct 2026.
- **Architecture, from the README.**
  - It is a single-threaded Wasm module that runs inside a hand-written
    AudioWorklet. It "deliberately avoids" Emscripten's
    `-sAUDIO_WORKLET`/pthreads/SharedArrayBuffer setup. The README says
    instantiating a threaded module a second time "caused a wasm recompile
    storm in WebKit that crossed the iOS Jetsam memory limit".
  - As a result, **no COOP/COEP headers are needed**, and the initial heap is
    64 MB, growing up to 512 MB.
  - It loads **A2 files only**. Legacy A1 files are rejected.
  - The core submodule is pinned to v0.5.4, behind the core's v0.6.0.
- **Cross-reference to #67.** The #67 note found that GitHub Pages cannot set
  COOP/COEP headers. This port's design removes that obstacle for NAM. Note
  that the October 2025 launch post said the player needed COOP/COEP and warned
  that "Playback may not perform correctly on older or low-power devices"
  ([TONE3000 web player post](https://www.tone3000.com/blog/introducing-the-nam-web-player)).
  The current README supersedes the header requirement.
- **iOS evidence.** The commit history includes "attempt to quick-fix ios oom
  kill" and three `ios-memory` PRs merged 9–13 Aug 2026
  ([commits](https://github.com/tone-3000/neural-amp-modeler-wasm/commits/main)).
  So iOS Safari is a target, and memory has been a real problem there. The repo
  has **no issues mentioning iOS** (GitHub search). I found **no published CPU,
  voice-count or latency figures on an iPhone** (**unverified**; this needs a
  device test).
- **Bundled demo models.** The demo models are labelled with real amps:
  Fender Deluxe Reverb, Marshall JCM800, Vox AC10, Dumble ODS, Ampeg V-2,
  EVH 5153 and Roland JC-120
  ([models README](https://github.com/tone-3000/neural-amp-modeler-wasm/blob/main/ui/public/models/README.md)).
  The README states **no licence for these `.nam` files**, nor for the IR
  folder ([IR README](https://github.com/tone-3000/neural-amp-modeler-wasm/blob/main/ui/public/irs/README.md)).
  The repo's MIT licence may or may not be intended to cover them
  (**unverified**). The npm tarball does not include them; the player fetches
  them from GitHub.
- **Other browser users.** [openDAW](https://github.com/andremichelle/openDAW)
  is a browser DAW that hosts TONE3000 captures with live input "With Effects".
  It uses the same Wasm runtime
  ([TONE3000 post, 23 Mar 2026](https://www.tone3000.com/blog/opendaw-now-supports-tone3000)).
  openDAW itself is **AGPL-3.0**, or a paid commercial licence (openDAW
  README), so it is a reference rather than something to embed casually.

### TONE3000 (capture library)

- **Size.** TONE3000 describes 275,000+ NAM captures
  ([openDAW post](https://www.tone3000.com/blog/opendaw-now-supports-tone3000)).
- **Who owns the tones.** Creators keep ownership of what they upload. The
  Terms of Service (dated 12 Mar 2025) say: "You may not sell, license, or
  commercially distribute content accessed through our platform" without
  written permission from both the owner and TONE3000
  ([ToS](https://www.tone3000.com/terms)).
- **API terms** (effective 7 July 2026,
  [API terms](https://www.tone3000.com/api/terms)):
  - The licence is limited and revocable.
  - Commercial products need a commercial agreement and approval before launch.
  - "Do not preload catalog content onto devices or bundle it with your
    product without written permission."
  - Downloads must happen only on a user's request.
  - Creator names and licence info must be kept, and some tones require
    attribution.
- **What may be shared** ([Tone Sharing Policy](https://www.tone3000.com/policy)):
  - Captures of analog gear are allowed.
  - Captures of current plugins and modelers, and commercial IRs, are banned.
  - Pack titles use the format "[Brand] [Make and Model] [Year]" and must not
    include artist names.
  - The page carries the footer "All trademarks… are the property of their
    respective owners".
  - "All tones are free for now", with paid tones described as coming.
- **What this means.** A curated set of TONE3000 captures cannot simply be
  shipped as Band mode's built-in "foundation tones" without written
  permission. A user-initiated browse/download through the API is the
  sanctioned route, and commercial use needs an agreement.

### AIDA-X (AidaDSP)

- **What it does.** An amp-model player using RTNeural (LSTM/GRU JSON models)
  with an IR cab after the model. It supports CLAP, LV2, VST2, VST3 and
  standalone, and has an LV2 build for MOD Dwarf and Raspberry Pi
  ([README](https://github.com/AidaDSP/AIDA-X)).
- **Licences.** The code is **GPL-3.0-or-later**. Models come from a Google
  Drive pack and the MOD forum, with no licence stated in the README.
- **Maturity.** The last release was 1.1.0 on 1 Feb 2024, and the last push
  was Dec 2024 (GitHub API). That makes it quieter than NAM.
- **Browser.** No web or Wasm build was found. RTNeural itself is
  **BSD-3-Clause** ([repo](https://github.com/jatinchowdhury18/RTNeural)), but
  I did not verify a browser port (**unverified**).

### Guitarix

- **What it does.** A Linux (JACK/LV2) amp and effects suite
  ([repo](https://github.com/brummer10/guitarix)). Latest release V0.47.0 was
  on 25 Aug 2025; the repo was last pushed Oct 2026.
- **Licence.** The COPYING file says the project as a whole is
  **GPL-3.0-or-later**. That is because it includes GPLv3+ zita-resampler and
  zita-convolver, plus an LGPLv3+ file, even though most of its own code is
  GPLv2+ ([COPYING](https://github.com/brummer10/guitarix/blob/master/trunk/COPYING)).
- **Browser route.** Guitarix's tone stacks and tube stages are already in the
  Faust standard libraries:
  - `tonestacks.lib` is "from the Guitarix project", licensed
    **LGPL-2.1-or-later**.
  - `tubes.lib` has "Vacuum tube amplifier stage emulations from the Guitarix
    project", with 12AX7, 12AT7 and 12AU7 stages
    ([faustlibraries](https://github.com/grame-cncm/faustlibraries)).
  - This is the most practical way to use Guitarix-derived DSP in a browser.
    I found no direct Guitarix web port.
- **Bundled cab IRs.** These are the "BestPlugins" packs, released under
  **GPL-2.0-or-later** by David Fau Casquel (2013)
  ([LICENSE](https://github.com/brummer10/guitarix/blob/master/trunk/IR/BestPlugins_Amps/LICENSE)).
  The file names name real amps (for example "EVH 5150 III.wav" and
  "Mesa Boogie Mark V.wav").

### ToneLib

- ToneLib GFX is a **paid, proprietary** product at $89.95 list, with a free
  trial ([tonelib.net](https://tonelib.net/tl-gfx.html)). It is not usable as
  open source. I did not check whether it has an iOS version.

### Impulse-response (cab) libraries

- **Built-in support.** Web Audio's `ConvolverNode` runs cab IRs natively in
  the browser (see the #67 note, §3). The NAM wasm player also loads IRs
  ([README](https://github.com/tone-3000/neural-amp-modeler-wasm)).
- **Openly licensed guitar-cab IRs.** I found **no verified CC0 or CC-BY
  guitar-cab IR pack** (❌). What I did find:
  - Guitarix's BestPlugins IRs are GPL-2.0+ (above).
  - Voxengo's free IRs are mostly reverb spaces plus four "Direct Cabinet"
    files. They may be used "royalty-free for any purpose, including
    commercial usage". However, "You may not sell these impulse files or earn
    any direct or indirect profit from their distribution", and redistribution
    must keep the files unaltered with their notice
    ([Voxengo](https://www.voxengo.com/impulses/)).
  - OpenAIR (University of York) has room IRs under per-item Creative Commons
    licences that the uploader picks
    ([OpenAIR](https://www.openair.hosted.york.ac.uk/?page_id=2),
    *(search extract)*).
  - Free vendor cab packs exist: Origin Effects (6 cabs, Oct 2024,
    [Sound On Sound](https://www.soundonsound.com/news/origin-effects-launch-free-ir-cab-library)),
    God's Cab, Metal Cabs and Devil's Lab (*(search extract)*,
    [KVR](https://www.kvraudio.com/news/48200),
    [BPB](https://bedroomproducersblog.com/2013/09/11/metal-cabs-free/)).
    Their redistribution terms were **not verified**. "Free to download" is
    not the same as "free to bundle in an app".
  - TONE3000 permits sharing "openly licensed IRs" and bans commercial IRs
    ([policy](https://www.tone3000.com/policy)).
- **Self-made IRs.** Recording IRs of a cab the project owns, or generating a
  synthetic cab filter (for example Faust `speakerbp` in `misceffects.lib`,
  STK-4.3), avoids third-party IR licences. This is an observation, not a
  sourced recommendation.

---

## 2. Effect pedals (open DSP)

| Effect | Browser options found | Licence | Notes |
| --- | --- | --- | --- |
| Drive/distortion | Web Audio `WaveShaperNode`; Tone.js `Distortion`, `Chebyshev`; Faust `ef.cubicnl` (STK-4.3); Faust `tubes.lib` (Guitarix, licence line not found in header grep); WAM `TS9_OverdriveFaustGenerated`, `disto_machine` | Platform / MIT / STK-4.3 / MIT | WaveShaper `oversample` is 'none'/'2x'/'4x' and helps avoid aliasing ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/WaveShaperNode/oversample)). Tone.js `Distortion` defaults to `oversample: "none"` ([source](https://github.com/Tonejs/Tone.js/blob/dev/Tone/effect/Distortion.ts)). Chris Rogers argued for oversampling to avoid "extremely harsh aliasing" in amp sims ([W3C list, 2013](https://lists.w3.org/Archives/Public/public-audio/2013AprJun/0373.html)) |
| Fuzz | WAM `BigMuff`, `quadrafuzz` ([wam-examples](https://github.com/webaudiomodules/wam-examples)) | MIT (repo) | Example quality; named after a commercial pedal |
| Chorus/flanger/phaser | Tone.js `Chorus`, `Phaser`, `Vibrato`, `Tremolo`; Faust `phaflangers.lib`; WAM `StonePhaserStereo` | MIT / per-function / MIT | — |
| Delay | Web Audio `DelayNode`; Tone.js `FeedbackDelay`, `PingPongDelay`; Faust `ef.echo`; WAM `pingpongdelay` | Platform / MIT / per-function | Simple to build well |
| Reverb | `ConvolverNode` + IR; Tone.js `Reverb` (convolution of decaying noise), `Freeverb`, `JCReverb`; Faust `jpverb`, `greyhole` (MIT), `dattorro_rev_default` (STK-4.3), `zita_rev1` (via demos), `springreverb`, `vital_rev` (**GPL-3.0-only**) | Platform / MIT / mixed | Faust spring reverb exists, which is relevant to "amp spring reverb" |
| Compressor | `DynamicsCompressorNode`; Faust `compressor_mono`/`stereo` (STK-4.3) but `peak_compression_gain_*` (**GPL-3.0-only**) | Platform / mixed | — |
| Wah / auto-wah | Tone.js `AutoWah`; Faust `ve.wah4`, `ve.crybaby`, `ve.autowah`; Biquad bandpass sweep | MIT / Faust (file header STK-4.3; per-function lines not found for crybaby) | "Crybaby" is a commercial pedal name |
| Noise gate | Faust `ef.gate_mono` (STK-4.3) | STK-4.3 | Useful before high gain |
| Tuner | [pitchy](https://github.com/ianprime0509/pitchy) (0BSD), [PitchDetect](https://github.com/cwilso/PitchDetect) (MIT, last push 2022), `AnalyserNode` | Permissive | Not a pedal; needs only analysis |
| Amp tone stack / tube stages | Faust `tonestacks.lib` (LGPL-2.1+), `tubes.lib`; WAM `GuitarAmpSim60s` | LGPL / MIT | Classic EQ shapes taken from Guitarix |

**Faust licensing detail.** The `misceffects.lib` header is LGPL with an
"EXCEPTION TO THE LGPL LICENSE". That exception lets you "freely choose the
license for the resulting" compiled code ([misceffects.lib](https://github.com/grame-cncm/faustlibraries/blob/master/misceffects.lib)).
On top of that, individual functions declare their own licences: STK-4.3
(MIT-style, [licence text](https://github.com/grame-cncm/faustlibraries/blob/master/licenses/stk-4.3.0.md)),
MIT, LGPL-2.1+, or GPL-3.0-only. **Check each function's `declare … license`
line before using it.** The compiler is LGPL-2.1 (COPYING.txt), and
[faustwasm](https://github.com/grame-cncm/faustwasm) is LGPL-2.1
(`package.json`).

**Web Audio Modules (WAM).**
- **What it is.** WAM is a plugin standard for the browser (API `package.json`
  licence MIT; [api](https://github.com/webaudiomodules/api), last pushed
  Mar 2023). The [wam-examples](https://github.com/webaudiomodules/wam-examples)
  repo (MIT, pushed Nov 2025) includes `pedalboard`, `PedalBoard-WAC2022`,
  `GuitarAmpSim60s`, `TS9_OverdriveFaustGenerated`, `BigMuff`, `quadrafuzz`,
  `disto_machine` and `StonePhaserStereo`.
- **Research history.** The Université Côte d'Azur group published "Making a
  guitar rack plugin – WebAudio Modules 2.0" at WAC 2022 (CC BY 4.0,
  [Zenodo](https://zenodo.org/record/6769098)). An earlier group paper reported
  about 14 ms latency for a WebAudio pedalboard on a MacBook Pro in Chrome
  (*(search extract)*,
  [HAL](https://hal.archives-ouvertes.fr/hal-01893781); bot wall on fetch).
- **What I couldn't check.** I found no iPhone measurements for WAM pedals.
  Quality is "research example", not a commercial product. Faust can compile
  to WAM via faust2wam ([Faust deploying docs](https://faustdoc.grame.fr/manual/deploying),
  *(search extract)*).

**Tone.js.** MIT. Latest release 15.1.22 (12 July 2026, GitHub API). Its effect
folder includes AutoFilter, AutoPanner, AutoWah, BitCrusher, Chebyshev,
Chorus, Distortion, FeedbackDelay, Freeverb, FrequencyShifter, JCReverb,
Phaser, PingPongDelay, PitchShift, Reverb, ReverseDelay, StereoWidener,
Tremolo and Vibrato ([source](https://github.com/Tonejs/Tone.js/tree/dev/Tone/effect)).
These effects suit learning and work fine as a "pedal" layer. I found no
published quality evaluation.

**Native-only effect sources.** BYOD (GPL-3.0, "Build-your-own guitar
distortion"), KlonCentaur (BSD-3-Clause, RNN plus wave-digital-filter
emulation; last push 2021) and Proteus (GPL-3.0, last push 2023) are native
plugins (GitHub API). In principle they could be ported to Wasm, but I found no
browser build.

---

## 3. Running in an iPhone web app

- **Built-in effects.** Gain, biquad, waveshaper, delay, convolver and
  compressor nodes all run natively in Safari (see the #67 note, §3). They are
  the cheapest option on CPU.
- **AudioWorklet + Wasm DSP** (Faust, NAM) works in Safari since 14.1. The
  #67 note records AudioWorklet glitch bugs, including the iOS 27 crackle while
  echo-cancelled capture is running
  ([WebKit 326286](https://bugs.webkit.org/show_bug.cgi?id=326286)). That bug
  directly affects **live monitoring through an amp sim**.
- **CPU budget.** Web Audio renders on one real-time thread with 128-frame
  quanta, which is about 2.7 ms at 48 kHz (see the #67 note). NAM A2 plus
  slimmable sizing is the most CPU-flexible neural option found. However, I
  found **no iPhone CPU benchmark for NAM in Safari** (**unverified**). The
  TONE3000 iOS OOM fixes show that **memory** is a real limit as well as CPU.
- **Latency.** The #67 note found no published iPhone Safari round-trip
  figure, and no input-latency API. Playing live "through" a browser amp sim
  adds the full web round trip.
- **Two safer patterns for a learner** (my inference, not sourced practice):
  1. Monitor dry through the interface's direct monitor, record DI, and apply
     the amp/effects at playback or render time (`OfflineAudioContext`).
  2. Offer live amp monitoring as optional, and say plainly that it adds
     delay.
  Re-amping DI is also how NAM-style tones can be changed after recording.
- **Native-only items.**
  - AUv3 hosting and native low-latency session modes
    (`AVAudioSession .measurement`, preferred buffer duration; see the #67
    note §2 and §8).
  - Native iOS NAM apps exist: NAM Loader Pedal (AUv3, iOS 17+), NAM Live
    (A2, AUv3) and Ampz (AUv3, TONE3000 integration)
    ([App Store](https://apps.apple.com/app/id6775461616),
    [App Store](https://apps.apple.com/app/id6778012976),
    [App Store](https://apps.apple.com/app/id6761513571); *(search extract)*,
    prices and details not verified). This shows NAM runs on iPhones
    natively.

---

## 4. Teaching tone: how established sources teach beginners

**Signal-chain order.**

BOSS's guide (Henry Yates, undated,
[BOSS Articles](https://articles.boss.info/?p=34677)) gives this order:

1. **Tuner first**, because it needs a clean signal.
2. **Dynamics and pitch pedals early** (compressor, octave), with wah usually
   just before drive.
3. **Drive/distortion next.** Noisy pedals go early, with a noise gate in this
   area. Stack drives "from lightest to heaviest".
4. **Modulation after drive.**
5. **Delay after drive.**
6. **Reverb last**, or in the amp's effects loop.
7. **Amp/cab sims usually at the end.**

BOSS says EQ and volume placement is debated, and frames the whole order as a
starting point for experimentation. Roland Indonesia gives a similar order and
explains that drive amplifies noise from pedals placed before it
([Roland Indonesia](https://rolandindonesia.com/order-effects-chain-simple-guide),
*(search extract)*).

**EQ starting point.** Marshall teaches setting "all EQ knobs to 12 o'clock",
then changing one knob at a time to hear what it does
([Marshall EQ guide](https://www.marshall.com/backstage/beginners/understanding-basic-eq-how-to-shape-your-guitar-tone)).
Marshall's setup guide adds: start with the volume low and the EQ neutral,
then raise the volume gradually; gain sets how hard the amp is driven
([Marshall setup guide](https://www.marshall.com/backstage/beginners/a-beginners-guide-to-setting-up-your-guitar-amp)).

**Genre directions** (Marshall, directional only; no numbers given):

| Style | Direction |
| --- | --- |
| Blues | Bass and mids up, treble down |
| Rock | Bass and mids up |
| Metal/thrash | Mids down |
| Jazz | Bass up, treble down |
| Funk/clean | Treble up |
| Lead | Treble and mids up, to stand out |

([Marshall EQ guide](https://www.marshall.com/backstage/beginners/understanding-basic-eq-how-to-shape-your-guitar-tone))

**Gain vs volume.** Fender's explainer presents gain as a tone (distortion)
control and master volume as loudness
([Fender](https://www.fender.com/articles/setup/amp-basics-gain-vs-volume),
*(search extract)*; 403 on fetch). Fender Play has a five-minute "Amp EQ"
lesson ([Fender Play](https://www.fender.com/play/lessons/tone-amp-eq),
*(search extract)*).

**Gain amount for chords.** JustinGuitar has a lesson, "Learn Your Guitar Amp &
Settings" ([JustinGuitar](https://justinguitar.com/guitar-lessons/learn-your-guitar-amp-settings-bg-1607);
403 on fetch, so contents not verified). A JustinGuitar community reply says a
little gain suits picked notes and power chords, while too much gain "will not
be good for open chords"
([community thread](https://community.justinguitar.com/t/learn-your-guitar-amp-settings/87373),
*(search extract)*; forum, so secondary).

**Gain staging into amp sims.** MusicRadar explains that amp models are
non-linear: a hotter input distorts more, and a weak input can make a crunch
preset sound clean. It also notes that modellers and apps have their own input
levels
([MusicRadar](https://www.musicradar.com/how-to/how-to-maximise-tone-and-reduce-noise-on-your-guitar-rig-with-gain-staging),
*(search extract)*). A Line 6 support thread says gain and volume are
different, and that level problems stop models behaving as expected
([Line 6 forum](https://line6.com/support/topic/18585-gain-staging/),
*(search extract)*). I found **no official Line 6, Fractal or Neural DSP
gain-staging guide** in this pass. For NAM, the input level an audio interface
delivers matters for the same reason. That is an inference from how the models
work, not from a NAM document.

**Numeric genre settings.** These came only from secondary blogs and forums,
for example Guitarchalk's Fender "Magic Six" (volume 6, treble 6, mids 3,
bass 2) ([Guitarchalk](https://www.guitarchalk.com/fender-amp-settings/),
*(search extract)*), and a Seymour Duncan forum post with this caveat:
settings "ALL vary with the guitar/pups and specific amp"
([forum](https://forum.seymourduncan.com/threads/a-beginners-guide-to-dialing-in-your-amp.268333),
*(search extract)*). I found **no manufacturer source giving numeric genre
settings**.

**Manufacturer presets as a model.** Fender's "Tone" site organises presets by
genre (for example
[Top-40](https://www.fender.com/tone/genres/top-40) and
[Heavy-metal](https://www.fender.com/tone/genres/heavy-metal)), and its
Studio Pro article shows "start from a preset, then tweak gain and EQ"
([Fender](https://www.fender.com/articles/fender-studio/dial-in-tone-fender-studio-pro);
all *(search extract)*). This is evidence that "preset as starting point" is
an established teaching pattern.

---

## 5. Rights: captures, IRs, real amp and artist names, trademarks

- **Captures (`.nam`).**
  - On TONE3000, rights stay with each creator. TONE3000's ToS and API terms
    forbid commercial redistribution or bundling without written permission
    ([ToS](https://www.tone3000.com/terms),
    [API terms](https://www.tone3000.com/api/terms)).
  - The bundled demo models in the wasm repo carry no stated licence
    (above).
  - TONE3000 bans captures of current software and modelers
    ([policy](https://www.tone3000.com/policy)).
  - Whether a capture of a hardware amp is itself copyrightable is a legal
    question this note does not answer (**unverified**).
- **IRs.** These are licensed per pack: GPL-2.0+ (Guitarix BestPlugins),
  Voxengo's custom terms, and per-item CC on OpenAIR. "Free download" vendor
  packs usually come without verified redistribution rights (§1).
- **Naming real amps.**
  - **Industry practice.** Line 6's Helix models list gives models invented
    names such as "US Deluxe Nrm" and "Brit Plexi Nrm". It names the real amp
    only in a "based on" column, with this disclaimer: "All product names are
    trademarks of their respective owners, which are in no way associated or
    affiliated with Line 6… provided for the sole purpose of identifying the
    specific products that were studied". It lists Fender®, Marshall®,
    Hiwatt® and others as registered marks
    ([Line 6 Helix models list PDF](https://jp.line6.com/data/6/0a06433914b1a55c24990c43bd/application/pdf)).
  - TONE3000 does the opposite. Its titles must name the real gear,
    "[Brand] [Make and Model] [Year]", with a footer saying brand references are
    descriptive and imply no endorsement ([policy](https://www.tone3000.com/policy)).
  - **UK law.** Trade Marks Act 1994 s.11(2)(c) permits using a mark "for the
    purpose of identifying or referring to goods or services as those of the
    proprietor", provided the use is "in accordance with honest practices in
    industrial or commercial matters"
    ([legislation.gov.uk](https://www.legislation.gov.uk/ukpga/1994/26/section/11)).
  - **US law.** The *New Kids on the Block* "nominative fair use" test asks
    three things: is the product identifiable without the mark, is only as
    much of the mark used as needed, and is there no implied sponsorship
    ([summary of Playboy v. Welles](https://law.justia.com/cases/federal/appellate-courts/F3/279/796/506072),
    *(search extract)*).
  - These are not legal advice. Whether a preset called "Marshall-style crunch"
    is honest or nominative use is a **question for a lawyer**.
- **Effect names that are commercial pedal names.** Faust's `crybaby` and the
  WAM examples `BigMuff` and `TS9_Overdrive` carry commercial product names. I
  did not verify the trademark registrations for these names.
- **Artist names.** TONE3000 bans artist names in pack titles
  ([policy](https://www.tone3000.com/policy)). I found no source specifically on
  "sounds like [artist]" preset names. Personality and passing-off rights
  were **not researched**.

---

## What this means for Band mode

### Possible now in a web app (✅)
- A pedal layer from built-in Web Audio nodes, Tone.js (MIT) or Faust → Wasm.
  This covers drive, delay, reverb (including a Faust spring reverb),
  chorus/phaser, compressor, gate and wah. Pick Faust functions marked
  STK-4.3, MIT or LGPL-with-exception.
- Cab simulation with `ConvolverNode` and IRs the project has the rights to,
  or a synthetic speaker filter.
- A tuner from permissive JS pitch detection (pitchy 0BSD, PitchDetect MIT).
- A classic amp tone-stack and tube-stage sim via Faust's Guitarix-derived
  `tonestacks.lib`/`tubes.lib` (LGPL-2.1+).
- Applying amp/effects to a recorded DI at playback or render time, which
  avoids live-latency problems.

### Possible with caveats (⚠️)
- **NAM amp captures in Safari** via TONE3000's MIT wasm engine. It needs no
  COOP/COEP, so it fits GitHub Pages. Caveats:
  - iOS memory issues were fixed only recently (Aug 2026).
  - There are no iPhone CPU or latency figures.
  - It loads A2 files only.
  - Live monitoring adds web round-trip delay and hits the iOS 27 capture
    crackle bug (#67).
- **Capture sources.** Neither TONE3000's catalogue nor the repo's demo models
  are clearly licensed for bundling as built-in presets. That needs either a
  TONE3000 commercial agreement or permission, captures the project makes
  itself, or captures released under an explicit open licence (none verified
  here).
- **Example code.** WAM example pedals and amp (MIT) work in the browser but
  are research-example quality, with no phone measurements.
- **Copyleft sources.** GPL-licensed DSP and assets (Guitarix, AIDA-X, BYOD,
  Proteus models, BestPlugins IRs) bring copyleft obligations if used.
  openDAW is AGPL.

### Native-only (📱)
- AUv3 effect hosting, native low-latency audio sessions, and the existing
  native iOS NAM apps.
- AIDA-X, Guitarix, BYOD, Proteus and KlonCentaur as shipped (desktop or
  embedded plugins).

### Missing or not found (❌)
- A verified CC0 or CC-BY guitar-cab IR pack.
- Openly licensed, bundle-safe NAM captures of classic amp types.
- Any published iPhone Safari benchmark for NAM or WAM pedals.
- Manufacturer-published numeric "genre starting settings".
- Official gain-staging guidance from a major modeller vendor (this pass).

### "Foundation tone" ideas grounded in the sources
These are candidates for guided presets with explanations, not decisions.

1. **"Start at noon."** All EQ at 12 o'clock, then move one knob and listen
   (Marshall).
2. **"Gain is tone, volume is loudness."** A gain-vs-volume lesson on a clean
   amp (Marshall; Fender *(search extract)*).
3. **"The standard chain."** Tuner → compressor → wah → drive → modulation →
   delay → reverb, with amp/cab last. Show it as a starting point and invite
   reordering (BOSS).
4. **Genre EQ directions as presets.** Blues: bass and mids up, treble down.
   Rock: bass and mids up. Metal: mids down. Funk/clean: treble up. Lead:
   treble and mids up (Marshall). Pair each with a short "why".
5. **"Less gain for open chords, more for power chords and single notes"**
   (JustinGuitar community, secondary).
6. **"Stack drives light to heavy"** and **"put the gate where the noise
   is"** (BOSS).
7. **"Check your input level first."** Too quiet and a crunch preset sounds
   clean; too hot and it clips (MusicRadar *(search extract)*). This maps to
   an interface-level check before choosing tones.
8. **"Reverb last, delay after drive"**, and add delay or reverb for solos
   (BOSS ordering; the "for solos" framing is the founder's example, not a
   sourced rule).
9. **Naming convention.** Use descriptive style names with an optional "based
   on" note and a trademark disclaimer, in the Line 6 pattern. Whether to name
   brands at all is a rights decision (§5).

---

## Not verified / open questions

- iPhone CPU load, voice count and round-trip latency for NAM wasm, Faust and
  WAM pedals in Safari on iOS 27. This needs a device test.
- The licence of the demo `.nam` and IR files in `tone-3000/neural-amp-modeler-wasm`.
- The licences of NAM core's bundled dependencies (Eigen, AudioDSPTools).
- Whether RTNeural or NeuralAudio have working Wasm builds.
- The licence line for Faust `crybaby`/`autowah` and `tubes.lib`
  (`tonestacks.lib` is LGPL-2.1+).
- Redistribution terms for free vendor IR packs (Origin Effects, God's Cab,
  Metal Cabs, Devil's Lab), and which CC variant applies to OpenAIR items.
- The contents of the JustinGuitar lesson and the Fender gain/volume article
  (both returned 403). The iOS app listings (search extracts).
- Whether a capture of a hardware amp attracts copyright. Trademark
  registrations for pedal names. Legal judgement on "X-style" naming in UK and
  US.
