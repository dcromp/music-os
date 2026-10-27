# Band mode research: what an iPhone web app can do as an AI-assisted DAW

Research for [#67](https://github.com/dcromp/music-os/issues/67) (part of #64).
Done by an AI agent (Claude Code). All sources were checked on
**27 October 2026**. This note gathers facts and does not make product decisions.

**Versions covered.** The current release is Safari 27 on iOS 27. Safari 27.0
was released on 14 September 2026
([Safari 27 release notes](https://developer.apple.com/documentation/safari-release-notes/safari-27-release-notes)),
and the bug reports cited below mention iOS 27.0.1. Where a fact applies to an
earlier version only, the note says so. Browser support data comes from MDN's
[browser-compat-data](https://github.com/mdn/browser-compat-data) at commit
`bf12f642` (27 October 2026). For every API used here, BCD records Safari on
iOS as matching desktop Safari. On iPhone, every browser uses WebKit, so Chrome
and Firefox on iOS behave like Safari. The one exception is the EU, where
other engines are allowed ([App Review Guideline 2.5.6](https://developer.apple.com/app-store/review/guidelines/#2.5.6),
[Apple: alternative browser engines](https://developer.apple.com/support/alternative-browser-engines/),
EU only, iOS 17.4+).

**How the sources were read.** I opened these WebKit bugs directly: 211192,
311639, 281978, 259193, 311451, 326286, 218012, 251091, 226240, 261554,
291892, 226620, 239602, 269777 and 269937. Several others are cited from
search-result extracts of their pages: 154538, 174833, 195093, 210231, 221530,
237322, 251350, 251532 and 295518, along with Apple forum 804765, tfjs #8733,
the Wasmer docs, the HAL paper, and the Soundtrap and BandLab help pages.
Those are good leads but less firmly checked.

**Status key.** ✅ works · ⚠️ works with caveats · ❌ doesn't work on iPhone Safari.
"Unverified" means no primary source was found and the fact should be measured
on a device.

## Summary table

| Capability | Status | Key source |
| --- | --- | --- |
| `getUserMedia` microphone capture (HTTPS) | ✅ | [BCD MediaDevices](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia#browser_compatibility) |
| Choosing a USB/Lightning interface as input | ⚠️ often works; long-running regressions | [WebKit 211192](https://bugs.webkit.org/show_bug.cgi?id=211192), [311639](https://bugs.webkit.org/show_bug.cgi?id=311639) |
| Choosing the output device (`setSinkId`, `selectAudioOutput`) | ❌ (`setSinkId` macOS only, media elements only) | [Safari 18.4 blog](https://webkit.org/blog/16574/webkit-features-in-safari-18-4/), BCD |
| Stereo or multichannel input (`channelCount`) | ❌ constraint not supported; channel layout unreliable | BCD, [WebKit 281978](https://bugs.webkit.org/show_bug.cgi?id=281978), [259193](https://bugs.webkit.org/show_bug.cgi?id=259193) |
| `echoCancellation: false` | ⚠️ honoured, but changes routing and quality | BCD, [WebKit 326286](https://bugs.webkit.org/show_bug.cgi?id=326286), [311451](https://bugs.webkit.org/show_bug.cgi?id=311451) |
| `autoGainControl` / `noiseSuppression` constraints | ❌ not supported | BCD |
| `sampleRate` / `sampleSize` constraints | ⚠️ supported since Safari 18.6 (per `getSupportedConstraints`) | BCD |
| Input latency reporting (`MediaTrackSettings.latency`) | ❌ | BCD |
| `AudioContext.baseLatency` / `outputLatency` | ✅ (`outputLatency` since 18.4); accuracy unverified | BCD, [web.dev](https://web.dev/articles/audio-output-latency) |
| AudioWorklet | ⚠️ supported since 14.1; history of glitch bugs | BCD, [WebKit 226240](https://bugs.webkit.org/show_bug.cgi?id=226240), [251091](https://bugs.webkit.org/show_bug.cgi?id=251091) |
| OfflineAudioContext (mixdown/export) | ✅ | BCD |
| WebCodecs `AudioEncoder`/`AudioDecoder` | ✅ since Safari 26 | [Safari 26 blog](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/) |
| MediaRecorder | ✅ (ALAC and PCM since 26) | Safari 26 blog |
| Background playback | ⚠️ needs `audioSession.type = "playback"`; Home Screen app bugs | [WebKit 261554](https://bugs.webkit.org/show_bug.cgi?id=261554), [291892](https://bugs.webkit.org/show_bug.cgi?id=291892) |
| Background recording in a Home Screen app | ❌ (reported broken) | [WebKit 239602](https://bugs.webkit.org/show_bug.cgi?id=239602), [226620](https://bugs.webkit.org/show_bug.cgi?id=226620) |
| Web MIDI | ❌ declined by WebKit | [WebKit tracking prevention](https://webkit.org/tracking-prevention/) |
| Web Bluetooth / WebUSB / WebHID / Web Serial | ❌ | BCD |
| IndexedDB / OPFS storage | ✅ large quotas; ⚠️ eviction rules | [WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/) |
| Offline PWA (service worker) | ✅ | BCD, Safari 27 notes |
| WebGPU | ✅ since iOS 26 | [Safari 26 blog](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/), [gpuweb status](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status) |
| WebAssembly SIMD / threads | ✅ (threads need cross-origin isolation) | [webassembly.org features.json](https://github.com/WebAssembly/website/blob/main/features.json) |
| Wasm memory64 / relaxed SIMD | ❌ (behind a flag) | features.json |
| WebNN | ❌ | BCD (`navigator.ml`) |
| Large on-device models | ⚠️ practical memory far below 4 GB | [WebKit 269777](https://bugs.webkit.org/show_bug.cgi?id=269777), [269937](https://bugs.webkit.org/show_bug.cgi?id=269937) |

---

## 1. Recording through a USB or Lightning audio interface

### Permissions
- ✅ `navigator.mediaDevices.getUserMedia` has been in Safari since 11 and
  needs a secure context (HTTPS)
  ([BCD](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia#browser_compatibility)).
  GitHub Pages serves over HTTPS, which meets this.
- ⚠️ Until the user grants access, `enumerateDevices` lists only the default
  devices. Device IDs and labels are withheld until then
  ([WebKit 174833](https://bugs.webkit.org/show_bug.cgi?id=174833), Eric Carlson;
  [WebKit 195093](https://bugs.webkit.org/show_bug.cgi?id=195093);
  [MDN MediaDeviceInfo](https://developer.mozilla.org/en-US/docs/Web/API/MediaDeviceInfo)).
  The pattern suggested in 195093: store the chosen `deviceId`, request it with
  `{deviceId: {exact: id}}`, and fall back on `OverconstrainedError`.
- `Permissions.query` exists in Safari since 16 (BCD). This note did not check
  whether `"microphone"` permission is remembered across launches of a Home
  Screen web app (**unverified**).

### Device selection
- ⚠️ **Choosing the interface as input.** iOS treats a class-compliant USB
  interface as an audio route. On iPhone 15 and later it connects through USB-C
  ([Apple: USB-C on iPhone](https://support.apple.com/en-us/105099)). Older
  phones need Apple's Lightning to USB camera adapter. Apple's support page
  does not document class-compliant audio interfaces, so that detail is
  unverified from a primary source. In Safari, picking the interface has a long
  bug history:
  - [WebKit 211192](https://bugs.webkit.org/show_bug.cgi?id=211192), "USB
    microphone not recognized iOS Safari", has been REOPENED since 2021. Users
    reported problems from iOS 14.5 through 18.4: some microphones work, and in
    other cases Safari falls back to the built-in mic.
  - [WebKit 311639](https://bugs.webkit.org/show_bug.cgi?id=311639) (April
    2026, iOS 26.3): Safari used the built-in mic instead of a USB interface
    that Voice Memos used correctly. The trigger was the input volume-control
    range in the device's USB descriptors. WebKit closed it as **MOVED**
    (5 May 2026, rdar 174235305): the fix belongs in Apple's audio stack below
    WebKit. This note found no confirmation of a fix in iOS 27.
- ❌ **Choosing the output.** `AudioContext.setSinkId`, `sinkId` and
  `MediaDevices.selectAudioOutput` are not supported in Safari (BCD). The
  speaker-selection API in Safari 18.4 is described as "on macOS" and covers
  `HTMLMediaElement.setSinkId` only
  ([Safari 18.4 blog](https://webkit.org/blog/16574/webkit-features-in-safari-18-4/)).
  On iPhone, output follows the system route.

### Channels
- ❌ The `channelCount` constraint is not supported. Safari does not report it
  in `getSupportedConstraints` or accept it in `applyConstraints` (BCD).
- ⚠️ The channel layout of captured tracks is unreliable:
  - [WebKit 281978](https://bugs.webkit.org/show_bug.cgi?id=281978) (NEW, iOS
    17.6.1 and macOS Safari 18): with `echoCancellation: false`, a mono device
    gives a stereo track with audio only on the left channel. `channelCount`
    has no effect.
  - [WebKit 259193](https://bugs.webkit.org/show_bug.cgi?id=259193) (NEW): a
    mono device gives two channels, the second silent.
  - [WebKit 210231](https://bugs.webkit.org/show_bug.cgi?id=210231) (2020): a
    stereo source defaulted to one channel and kept only the left.
  - On Apple's forums, a developer reported that with echo cancellation off,
    macOS Safari 26 records stereo even when `channelCount: 1` is set
    ([forum thread 804765](https://developer.apple.com/forums/thread/804765)).
  - In practice, a 2-in interface (guitar on input 1, mic on input 2) cannot be
    recorded as two separate tracks with confidence. This note found no source
    showing more than two channels captured on iOS Safari (**unverified**).
    A single-guitar DI track is the safe assumption. Even then, the app would
    need to detect which channel holds the signal, because Safari does not
    report this.

### Sample rate and sample size
- ⚠️ Safari 18.6 added `sampleRate` and `sampleSize` to
  `getSupportedConstraints`. `applyConstraints` has listed them since 11 (BCD).
  This note did not check whether iOS honours a requested rate or simply
  reports the hardware rate (**unverified**).
- Sample-rate bugs on iOS have a history. [WebKit 154538](https://bugs.webkit.org/show_bug.cgi?id=154538)
  (iOS 9) reported a 44.1→48 kHz switch with distortion, worked around by
  recreating the `AudioContext`. [WebKit 251350](https://bugs.webkit.org/show_bug.cgi?id=251350)
  (iOS 15.6–16.2) reported an AudioWorklet receiving fewer samples per second
  than the set `sampleRate`. A prototype should create its `AudioContext`
  *without* forcing `sampleRate`, check `context.sampleRate` against
  `track.getSettings().sampleRate`, and log both.

### Disabling processing (echo cancellation, AGC, noise suppression)
- ⚠️ `echoCancellation` is the only processing constraint Safari supports.
  `autoGainControl` and `noiseSuppression` are ❌ (BCD). The reporter of
  [311451](https://bugs.webkit.org/show_bug.cgi?id=311451) says the same.
- ⚠️ Turning echo cancellation off has side effects on iPhone. These are the
  main audio problems on iOS 27:
  - [WebKit 326286](https://bugs.webkit.org/show_bug.cgi?id=326286), "REGRESSION
    (iOS 26.2 – 27): Audio output crackles while getUserMedia mic capture with
    echo cancellation is active". The bug is NEW and InRadar, with several
    reproductions on iPhone 16 Pro / iOS 27.0.1 in October 2026. With echo
    cancellation **on**, all page audio crackles, including an AudioWorklet
    sine tone. With it **off**, audio is clean but output moves to the
    **earpiece (receiver)** at low volume. `applyConstraints` on a live track
    does not switch modes.
  - [WebKit 311451](https://bugs.webkit.org/show_bug.cgi?id=311451), "Degraded
    audio quality with microphone enabled" (NEW, iOS 26.4, still present in
    iOS 27 betas): once capture starts, playback drops to a lower sample rate
    and stereo collapses to mono, **whether or not** `echoCancellation: false`
    is set.
  - [WebKit 218012](https://bugs.webkit.org/show_bug.cgi?id=218012): playback
    volume drops once the mic is granted. A WebKit engineer explained that
    starting capture changes the audio session category. The bug is closed
    "configuration changed", but users still report it on iOS 18.6 (March 2026).
  - This note found no report of what happens to routing and quality when a
    USB interface is *both* input and output, which is the Band-mode setup. It
    is plausible that output then goes to the interface instead of the
    earpiece, but this is **unverified** and is the first thing to test on a
    device.
- `navigator.audioSession.type` (Safari 16.4+, BCD) can be set to
  `"play-and-record"` or `"playback"`
  ([W3C Audio Session draft](https://w3c.github.io/audio-session/), editors
  from Apple and Mozilla). Users report that setting it helps in some cases and
  is inconsistent in others (218012). `audioSession.state` and its
  `statechange` event are not supported (BCD), so the page cannot observe
  interruptions this way.

### Ringer switch
- ⚠️ By default, Web Audio on iOS is an "ambient" session and is muted by the
  silent switch. Setting `navigator.audioSession.type = "playback"` (or
  `"play-and-record"`) avoids this
  ([WebKit 251532](https://bugs.webkit.org/show_bug.cgi?id=251532), youenn
  fablet; [WebKit 237322](https://bugs.webkit.org/show_bug.cgi?id=237322)).

## 2. Latency

### What the platform reports
- ✅ `AudioContext.baseLatency` (Safari 14.1) and `outputLatency` (Safari 18.4)
  are available, as is `getOutputTimestamp` (14.1) (BCD;
  [web.dev outputLatency](https://web.dev/articles/audio-output-latency)).
- ❌ There is no input-latency figure. `MediaTrackSettings.latency` and the
  `latency` constraint are not supported (BCD). Input latency has to be
  measured.
- `latencyHint` is accepted (14.1, BCD). This note did not check whether iOS
  changes its buffer size in response (**unverified**). WebKit asks for a
  128-frame render quantum once Web Audio is active. In Safari 16 a bug left
  the buffer at **960 frames** while capture was running, which distorted
  AudioWorklet output. It was fixed in February 2023
  ([WebKit 251091](https://bugs.webkit.org/show_bug.cgi?id=251091), Chris Dumez).
- The Web Audio spec warns that latency values can be used for fingerprinting,
  so browsers may coarsen them (cited via
  [web.dev](https://web.dev/articles/audio-output-latency)). This note did not
  check how accurate Safari's figures are on iPhone, and found no WebKit
  statement either way (**unverified**).

### What developers measure in practice
- This note found **no published iPhone Safari round-trip measurement** (web
  audio in, through the graph, out). That number has to come from a device
  test.
- For native iOS, Superpowered sets 10 ms round trip as the pro-audio target
  and says the default iOS audio session mode "adds around 30 ms of additional
  latency" compared with measurement mode
  ([Superpowered latency](https://superpowered.com/latency)). Native apps can
  set `AVAudioSession` mode `.measurement` and `setPreferredIOBufferDuration`
  ([Apple](https://developer.apple.com/documentation/avfaudio/avaudiosession/mode-swift.struct/measurement),
  [Apple](https://developer.apple.com/documentation/avfaudio/avaudiosession/setpreferrediobufferduration(_:))).
  Web pages cannot set either.
- On desktop, browser AudioWorklet loopback measured about 14–41 ms, against
  11 ms in Reaper ([jefftk 2020](https://jefftk.com/p/audioworklet-latency-firefox-vs-chrome)).
  Safari was not tested. This is only an order-of-magnitude guide.
- A method exists for measuring round trip in browser DAWs automatically
  (Web Audio Conference 2025, MLS-based,
  [HAL hal-05154354](https://hal.univ-lyon2.fr/S2A/hal-05154354v2)).

### Monitoring and take compensation
- ⚠️ **Live monitoring through the browser** (mic → graph → speakers) would
  add the full web round trip on top of the issues in §1. Monitoring through
  the interface's own direct-monitor knob needs nothing from the browser and
  avoids the problem.
- ✅ **Compensating takes** is possible without true low latency. Schedule
  playback against `AudioContext.currentTime`, record input in an AudioWorklet
  with sample-frame timestamps, and shift each take by a measured round-trip
  offset. A loopback calibration (play a click, detect it in the input, store
  the offset per device and route) gives that offset. `outputLatency` can seed
  the estimate, but the input half has to be measured. This method is my
  design inference from the APIs above. This note did not find a WebKit
  source describing it.

## 3. Audio engine

- ✅ **Core nodes.** The usual Web Audio nodes are all available: buffer
  source, gain, biquad, IIR, convolver (reverb), dynamics compressor,
  waveshaper (distortion), delay, stereo panner, oscillator and constant
  source (BCD `BaseAudioContext`).
- ⚠️ **AudioWorklet** has been in Safari since 14.1 (BCD).
  `AudioWorklet.port` is not supported (BCD); `AudioWorkletNode.port` works.
  There are known glitch reports:
  - [WebKit 226240](https://bugs.webkit.org/show_bug.cgi?id=226240) (NEW, iOS
    14, last comment 2023): "Each time any AudioWorklet is used on iOS it
    creates glitches" for the rest of the context's life. A commenter thinks it
    may duplicate the fixed 251091. Its status on iOS 27 is unverified.
  - [WebKit 326286](https://bugs.webkit.org/show_bug.cgi?id=326286) (above):
    an AudioWorklet tone crackles on iOS 27 while echo-cancelled capture is
    running.
- ⚠️ **Track and effect counts.** This note found no primary benchmark for
  iPhone Safari. Web Audio renders the whole graph on a single real-time audio
  thread ([Web Audio API spec](https://webaudio.github.io/web-audio-api/#rendering-loop)),
  so the limit is one core's budget per 128-frame quantum (about 2.7 ms at
  48 kHz). Practical counts need measuring on the target phone
  (**unverified**).
- ✅ **Sample playback and synthesis.** `AudioBufferSourceNode` plus
  `decodeAudioData` handle samples. Safari 27 fixed MP4/Opus and multichannel
  WebM decoding ([Safari 27 notes](https://developer.apple.com/documentation/safari-release-notes/safari-27-release-notes)).
  Synthesis can use oscillators, AudioWorklet DSP or Wasm DSP. Wasm SIMD
  (16.4) and threads (14.5 on iOS) are available
  ([features.json](https://github.com/WebAssembly/website/blob/main/features.json)).
  Threads and `SharedArrayBuffer` need **cross-origin isolation**
  (COOP/COEP headers;
  [MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements)).
  GitHub Pages cannot set those headers
  ([community discussion 13309](https://github.com/orgs/community/discussions/13309)).
  The usual workaround is a service worker that adds them, such as
  coi-serviceworker ([Wasmer docs](https://docs.wasmer.io/sdk/wasmer-js/how-to/coop-coep-headers)).
  This matters for lock-free ring buffers between the worklet and workers
  (for example [ringbuf.js](https://github.com/padenot/ringbuf.js), MPL-2.0).
- ✅ **Offline rendering and export.** `OfflineAudioContext` with
  promise-based `startRendering` and `suspend`/`resume` works (14.1, BCD).
  WebCodecs `AudioEncoder`/`AudioDecoder` arrived in Safari 26, and
  MediaRecorder gained ALAC and PCM
  ([Safari 26 blog](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)).
  WAV can be written in JS. A finished file can be handed to the user with
  `navigator.share({files})` (Safari 14, BCD). `showSaveFilePicker` is
  ❌ (BCD). An offline render holds the whole mix in memory. As a sizing
  guide (my arithmetic): 4 minutes of 48 kHz stereo float32 is about 92 MB.
- ⚠️ **Background audio.**
  - In a Safari tab, Web Audio keeps playing in the background once
    `navigator.audioSession.type = "playback"` is set. Before iOS 17.5 this was
    a regression ([WebKit 261554](https://bugs.webkit.org/show_bug.cgi?id=261554),
    fixed 2024).
  - In Home Screen web apps, [WebKit 291892](https://bugs.webkit.org/show_bug.cgi?id=291892)
    (NEW) reports that Web Audio can be silent after returning from the
    background, even though the context reports `"running"`. Reports cover
    iOS 18 and iOS 26.0, and one user said it was fixed in iOS 26.2 beta.
    See also [295518](https://bugs.webkit.org/show_bug.cgi?id=295518).
  - ❌ Mic capture in a **Home Screen** app stops when the app is backgrounded
    or the screen locks, while a Safari tab keeps it
    ([WebKit 239602](https://bugs.webkit.org/show_bug.cgi?id=239602),
    [226620](https://bugs.webkit.org/show_bug.cgi?id=226620) latest comment
    October 2024). Phone calls suspend capture and mute the track. Pages
    should check `track.readyState`/`muted` and call `getUserMedia` again.
  - ✅ Screen Wake Lock works in Home Screen web apps since iOS 18.4 and can
    keep the screen on during a take
    ([Safari 18.4 blog](https://webkit.org/blog/16574/webkit-features-in-safari-18-4/), BCD).

## 4. Web MIDI

- ❌ **Not supported** in Safari on any platform (BCD `requestMIDIAccess`).
  WebKit lists "Web MIDI API" among features it has decided not to implement
  "due to fingerprinting, security, and other concerns"
  ([webkit.org/tracking-prevention](https://webkit.org/tracking-prevention/)).
  Safari 27 shipped no MIDI changes. Because every iOS browser uses WebKit
  (outside the EU), Chrome on iPhone doesn't support it either.
- ❌ No low-level hardware access is available as a route around this: Web
  Bluetooth, WebUSB, WebHID and Web Serial are all unsupported (BCD).
- Options that remain:
  - On-screen instruments and touch input (works).
  - ✅ Gamepad API (Safari 10.1, BCD) for game controllers. A Bluetooth keyboard
    also arrives as ordinary key events.
  - **Audio-to-MIDI** in the page from the guitar signal, for example Spotify's
    Basic Pitch ([basic-pitch-ts](https://github.com/spotify/basic-pitch-ts),
    Apache-2.0, a "lightweight" polyphonic transcription model).
  - **Wrapper apps.** "Web MIDI Browser" on the App Store
    ([id953846217](https://apps.apple.com/app/id953846217)), and the
    open-source [MIDIWebView](https://swiftpackageregistry.com/bloxidge/MIDIWebView),
    which injects a Web MIDI polyfill into a `WKWebView`. This approach means
    shipping a native shell.
  - Native **Core MIDI** ([Apple](https://developer.apple.com/documentation/coremidi)).

## 5. Storage and offline

- ✅ **Quotas** (Safari 17+, [WebKit storage policy, Aug 2023](https://webkit.org/blog/14403/updates-to-storage-policy/)).
  In a browser app, each origin may use up to 60% of total disk and all
  origins together up to 80%. Home Screen web apps get the same quotas as a
  browser app. Cross-origin iframes get 10% of their parent's quota.
  `navigator.storage.estimate()` is available since 17 (BCD).
- ⚠️ **Eviction.** Data is removed per origin in least-recently-used order
  when the overall quota is exceeded, under storage pressure, or after a long
  time without interaction. `navigator.storage.persist()` exists (15.2), and
  WebKit grants it "based on heuristics like whether the website is opened as
  a Home Screen Web App" (same post). ITP deletes script-writable storage
  (IndexedDB, Cache, service workers) after **7 days without user
  interaction** in Safari. Home Screen web apps are **exempt**, and their data
  is "kept separate from Safari"
  ([tracking prevention](https://webkit.org/tracking-prevention/)). So
  projects saved in a Safari tab will not appear in the installed app, and the
  reverse.
- ✅ **OPFS.** `navigator.storage.getDirectory()` and
  `createSyncAccessHandle` (worker-only, sync methods since 16.4) have been
  available since 15.2. `createWritable` / `FileSystemWritableFileStream` were
  added in Safari 26 (BCD). OPFS suits large audio takes better than
  IndexedDB blobs. The storage-policy post names "File System" among the APIs
  its quota covers, but does not mention OPFS by name.
- Safari 27 fixed IndexedDB bugs: a version-0 database after an aborted
  upgrade, worker connections not recovering after a network-process crash,
  and transactions blocked by another page that was suspended in the
  background ([Safari 27 notes](https://developer.apple.com/documentation/safari-release-notes/safari-27-release-notes)).
- ✅ **Offline PWA.** Service workers and Cache API work. Safari 26 opens every
  site added to the Home Screen as a web app by default, with "zero
  requirements for 'installability'"
  ([Safari 26 blog](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)).
  Safari 27 added the service worker static routing API (Safari 27 notes).
- No user-visible file export picker exists (`showSaveFilePicker` ❌). Export
  goes through `navigator.share` or a download link.

## 6. On-device ML in the browser

- ✅ **WebGPU** has shipped and been on by default since iOS 26
  ([Safari 26 blog](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/),
  [gpuweb implementation status](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)).
  Safari 27 added WGSL `clip_distances` and fixed `onuncapturederror`
  ([Safari 27 beta blog](https://webkit.org/blog/17967/news-from-wwdc26-webkit-in-safari-27-beta/)).
- ✅ **WebAssembly** in Safari supports SIMD (16.4), threads (14.5 on iOS),
  exceptions, GC (18.2) and JSPI (27). ❌ memory64 and relaxed SIMD are
  flag-only ([features.json](https://github.com/WebAssembly/website/blob/main/features.json)).
  So the 32-bit 4 GB address limit applies.
- ❌ **WebNN** is not available (BCD `navigator.ml`).
- ⚠️ **ONNX Runtime Web** offers `wasm`, `webgpu`, `webgl` and `webnn`
  execution providers, and "only a subset" of operators run on GPU providers
  ([ORT Web](https://onnxruntime.ai/docs/tutorials/web/)). Its WebGPU page
  still mentions only Safari Technology Preview
  ([ORT WebGPU EP](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html)).
  The documentation lags iOS 26, and this note found no official ORT statement
  about iPhone (**unverified**). ORT limits: protobuf files up to 2 GB,
  external data needed beyond that, and models over 4 GB not supported. The
  docs recommend caching models in Cache API or OPFS
  ([ORT large models](https://onnxruntime.ai/docs/tutorials/web/large-models.html)).
- ⚠️ **Practical memory ceiling on iPhone.** It sits well below 4 GB and
  varies:
  - [WebKit 269777](https://bugs.webkit.org/show_bug.cgi?id=269777) (iOS 17):
    about 1 GB of Wasm memory on first load, 300–500 MB after a reload.
  - It was merged into [269937](https://bugs.webkit.org/show_bug.cgi?id=269937).
    There, WebKit enlarged the Gigacage for Wasm in May 2024
    ([272171](https://bugs.webkit.org/show_bug.cgi?id=272171)) and enabled
    Wasm fast memory on iOS ([272232](https://bugs.webkit.org/show_bug.cgi?id=272232)).
    No shipping version was given.
  - iOS kills the tab and reloads it rather than failing `memory.grow()`
    ([WebKit 221530](https://bugs.webkit.org/show_bug.cgi?id=221530)).
  - This note found no current (iOS 27) measurement (**unverified**).
- **What this suggests for model size (inference, not measured).** Small
  models such as pitch and onset detection, chord or beat models, and Basic
  Pitch (Apache-2.0) are realistic. Multi-hundred-MB models such as source
  separation (Demucs, MIT, [archived](https://github.com/facebookresearch/demucs))
  or local LLMs ([WebLLM](https://github.com/mlc-ai/web-llm), Apache-2.0,
  needs WebGPU) are at the edge of the memory budget, and download size and
  storage also count. Transformers.js
  ([Apache-2.0](https://github.com/huggingface/transformers.js)) runs on ORT
  Web. This note found no iPhone-specific benchmark for it.
- An early iOS 26 WebGPU bug report shows rough edges: TensorFlow.js
  video-frame import on iOS 26 WebGPU gave rotated landmarks
  ([tfjs #8733](https://github.com/tensorflow/tfjs/issues/8733)).
- Cloud inference over `fetch` is unaffected by any of these limits. Choosing
  between cloud and on-device inference is a product decision and is left
  open here.

## 7. Existing web DAWs and libraries

Licences come from each repository's GitHub licence field or `package.json`,
checked on 27 October 2026.

| Project | What it is | Licence | Notes |
| --- | --- | --- | --- |
| [Tone.js](https://github.com/Tonejs/Tone.js) | Transport, scheduling, synths, effects over Web Audio | MIT | Active (pushed Oct 2026) |
| [@tonejs/midi](https://github.com/Tonejs/Midi) | MIDI file read/write | MIT | No commits since 2023 |
| [wavesurfer.js](https://github.com/katspaugh/wavesurfer.js) | Waveform display, regions | BSD-3-Clause | Active |
| [waveform-playlist](https://github.com/naomiaro/waveform-playlist) | Multitrack editor (record, trim, fades, export) | MIT | Active; closest open "editable multitrack" building block |
| [openDAW](https://github.com/andremichelle/openDAW) | Full open-source browser DAW | AGPL-3.0 | Active; good to learn from; AGPL affects reuse |
| [GridSound](https://github.com/gridsound/daw) | Browser DAW | AGPL-3.0 | Active |
| [Elementary](https://github.com/elemaudio/elementary) | Functional audio DSP (web + native) | MIT | Last push Jan 2026 |
| [Faust](https://github.com/grame-cncm/faust) | DSP language → Wasm/AudioWorklet | LGPL-2.1 (compiler, per COPYING) | Active |
| [Web Audio Modules](https://github.com/webaudiomodules/sdk) | Plug-in standard for web | MIT (npm `@webaudiomodules/sdk`, `/api`) | Web counterpart to AUv3 |
| [smplr](https://github.com/danigb/smplr) | Sampled instruments (piano, drums, soundfonts) | MIT (`package.json`) | Active |
| [signalsmith-stretch](https://github.com/Signalsmith-Audio/signalsmith-stretch) | Time-stretch / pitch-shift | MIT | Active |
| [ringbuf.js](https://github.com/padenot/ringbuf.js) | Lock-free SAB ring buffer for worklets | MPL-2.0 | Needs cross-origin isolation |
| [Meyda](https://github.com/meyda/meyda) | Audio features | MIT | |
| [Essentia.js](https://github.com/MTG/essentia.js) | MIR algorithms (Wasm) | AGPL-3.0 | |
| [Basic Pitch](https://github.com/spotify/basic-pitch-ts) | Audio→MIDI model | Apache-2.0 | TS repo last pushed 2023 |
| [Magenta.js](https://github.com/magenta/magenta-js) | Music ML models in browser | Apache-2.0 | |
| [Strudel](https://github.com/tidalcycles/strudel) | Live-coding patterns | AGPL-3.0 | Archived on GitHub |
| [Chrome Labs web-audio-samples](https://github.com/GoogleChromeLabs/web-audio-samples) | AudioWorklet/Wasm design patterns | Apache-2.0 | Reference patterns |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) / [Transformers.js](https://github.com/huggingface/transformers.js) / [WebLLM](https://github.com/mlc-ai/web-llm) | Browser ML runtimes | MIT / Apache-2.0 / Apache-2.0 | |

**Commercial web DAWs on iPhone.** I could not fetch either vendor's help page
directly (HTTP 403). The following comes from search-result extracts of those
pages, so treat it as **partly verified**:
- **Soundtrap** recommends Chrome or Edge, lists Safari for Mac, and points
  iOS users to its app
  ([Soundtrap browser support](https://support.soundtrap.com/hc/en-us/articles/205664381-Browser-support),
  [system requirements](https://support.soundtrap.com/hc/en-us/articles/360017434459-What-Are-the-System-Requirements-for-the-Soundtrap-App)).
- **BandLab** recommends Chrome on computers and offers native iOS and Android
  apps. Mobile browsers aren't addressed
  ([BandLab requirements](https://help.bandlab.com/hc/en-us/articles/900001558383-Supported-Platforms-and-System-Requirements)).

Neither vendor offers its browser studio as the iPhone experience. Both ship
native apps on iPhone. This is an observation about their choices, not a
documented reason.

## 8. Breaking points where native iOS is needed

Each item below is something native iOS can do and an iPhone web page cannot,
going by the sources above:

| Need | Web on iPhone | Native |
| --- | --- | --- |
| Pick input port / multichannel input | No `channelCount`; input selection buggy (211192, 311639) | `setPreferredInput`, `setPreferredInputNumberOfChannels` ([Apple](https://developer.apple.com/documentation/avfaudio/avaudiosession/setpreferredinputnumberofchannels(_:))) |
| Raw, unprocessed capture with clean full-quality playback | Echo cancellation on → crackle on iOS 27; off → earpiece routing; quality drop either way (326286, 311451) | `.playAndRecord` without voice processing played cleanly (reporter's native test in 326286); `.measurement` mode |
| Low, controllable latency | No buffer-size control; no input latency figure | `setPreferredIOBufferDuration`; `AVAudioSession` input/output latency |
| Choose output device | ❌ | Route control via `AVAudioSession` |
| MIDI controllers | ❌ | Core MIDI |
| Third-party instruments and effects | Web Audio Modules only (web ecosystem) | AUv3 hosting ([Apple](https://developer.apple.com/documentation/audiotoolbox/audio-unit-v3-plug-ins)) |
| Record or play with screen locked / app backgrounded | Playback ⚠️; Home Screen recording ❌ | `UIBackgroundModes` `audio` ([Apple](https://developer.apple.com/documentation/bundleresources/information-property-list/uibackgroundmodes)) |
| Large on-device models | Wasm 32-bit, practical ceiling below 1 GB reported | Core ML / Metal with app memory budget (not researched here) |

[AudioKit](https://github.com/AudioKit/AudioKit) (MIT, active) is the main
open-source Swift audio framework for the native route. A hybrid is also
possible: a `WKWebView` shell running the web UI and engine, with native
capture and MIDI bridged in, as MIDIWebView does. In a `WKWebView`, mic
capture is muted in the background unless the app declares the `audio`
background mode ([WebKit 226620](https://bugs.webkit.org/show_bug.cgi?id=226620),
youenn fablet).

## What this means for Band mode

What a web-first prototype on iPhone (iOS 27) **can** do, based on the
sources above:
- Play an editable multitrack arrangement with samples, synths and built-in
  effects in Web Audio, and render a mixdown offline to WAV/AAC/ALAC. The
  result can be shared with the system share sheet.
- Record a **single guitar track** through a class-compliant interface over
  HTTPS, once the user allows the mic, and align takes to the arrangement
  with a measured latency offset.
- Store projects and takes locally in OPFS/IndexedDB with large quotas, and
  run offline as a Home Screen app, which is also exempt from the 7-day ITP
  wipe.
- Run small on-device models (pitch, onset, chord, audio-to-MIDI) with
  WebGPU or Wasm SIMD. Larger models or cloud calls are an open choice.

What it **can't** do, or can do only with caveats:
- Guarantee clean, full-quality recording and playback at the same time.
  On iOS 26.2–27, open mic capture currently either crackles (echo
  cancellation on) or moves output to the earpiece at low volume (echo
  cancellation off), and quality drops in both cases (326286, 311451). It is
  **untested** whether a USB interface used for both input and output avoids
  this. That test decides most of the web-first question.
- Choose the input or output device reliably, or record more than one
  input channel as separate tracks.
- Offer low-latency software monitoring that it can measure. Direct
  monitoring on the interface is the practical workaround.
- Use MIDI controllers (no Web MIDI, Bluetooth or USB APIs).
- Record while the Home Screen app is backgrounded or locked. Playback after
  backgrounding has had intermittent silence bugs.
- Host AUv3 instruments or effects.
- Use Wasm threads or SharedArrayBuffer on GitHub Pages without a service
  worker workaround for COOP/COEP headers.

Where native (or a native shell) would be needed: multichannel or
port-selected input, raw capture without voice processing, buffer-size
control, MIDI, AUv3, background recording, and larger on-device models. The
native column in §8 lists the API for each.

### Device tests that would settle the open questions

These are unverified items that only a test on a device can answer:
1. Interface as input and output: does output stay on the interface, and is
   audio free of crackle, with `echoCancellation` on and with it off?
2. Does `getSettings()` report the true sample rate and channel count? Which
   channel carries the guitar?
3. Round-trip latency from a loopback click, compared with
   `baseLatency + outputLatency`.
4. How many tracks with effects (and one AudioWorklet) play before dropouts on
   the founder's iPhone?
5. Wasm memory ceiling on iOS 27, on first load and after a reload.
