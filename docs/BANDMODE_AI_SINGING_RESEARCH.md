# Band mode research: AI singing voices for an editable lead singer

Research for [#69](https://github.com/dcromp/music-os/issues/69), part of
[#64](https://github.com/dcromp/music-os/issues/64). Sources checked
**27 October 2026** by an AI research agent (Claude Code). No accounts were
created, nothing was bought and no vendor was contacted, so every runtime,
quality and price statement comes from public documents. Nothing here was
listened to or benchmarked.

**The question.** Band mode wants an "AI lead singer". The player writes melody
notes and lyrics they can edit, and gets a sung vocal back. The alternative,
generating a finished song from a text prompt, has been rejected. This note
records what exists. It makes no product decisions.

**Source quality.** Primary sources are product pages, official docs, EULAs,
repos, model cards, papers and statutes. Where only press, retailer or
aggregator pages were reachable, the citation says so. Dreamtonics' own sites
(`dreamtonics.com`, `sv2.docs.dreamtonics.com`) sit behind a Cloudflare
JavaScript challenge that blocked automated reading. Synthesizer V facts
therefore come from a Synthesizer V voice EULA (primary), search-indexed
excerpts of the docs, and press or retailer pages. Each of these is flagged
where it is used.

---

## 1. Three kinds of technology

| Kind | What the player gives | What stays editable | Examples |
|---|---|---|---|
| **A. Singing voice synthesis (SVS)** | Notes (MIDI-like: pitch, start, length) plus lyrics or phonemes | Everything: each note, syllable, pitch curve, timing and expression parameter | Synthesizer V, ACE Studio, VOCALOID, CeVIO AI, Emvoice, DiffSinger/OpenUtau, SoulX-Singer |
| **B. Singing voice conversion (SVC)** | A sung recording (the player's guide vocal) plus a target voice | Only the recording. To change a note you re-sing it. Some tools transcribe audio to MIDI as a bridge to Kind A | RVC, Seed-VC, SoulX-Singer-SVC, Kits.ai, ACE Studio vocal changer, Dreamtonics Vocoflex, VOCALOID6 Vocalo Changer, ElevenLabs Voice Changer (speech) |
| **C. Song / audio generators** | A text prompt and lyrics, sometimes with an uploaded instrumental | Lyrics and sections can be regenerated. The melody is chosen by the model and has no note-level control | Suno (incl. Add Vocals, Studio), Udio, Eleven Music, ACE-Step, YuE |

The brief (notes plus lyrics in, sung vocal out, editable) is a description of
**Kind A**. Kind B fits when the player sings a guide. Kind C is the
prompt-to-song workflow the founder rejected. It appears below only to record
how much it can be edited.

---

## 2. Singing voice synthesis from notes and lyrics (Kind A)

### 2.1 Synthesizer V Studio 2 (Dreamtonics)

- **Input.** A piano-roll of notes with lyrics. Phonemes can be overridden.
  Scripts can read and write notes, groups, parameters and tracks. The
  scripting API supports JavaScript (ES5.1, Duktape) and Lua 5.4
  ([Scripting manual](https://resource.dreamtonics.com/scripting/)). Version
  2.1.1 in July 2025 extended scripting to retakes, pitch control points,
  vocal-mode parameters and consonant timing
  ([KVR news via search index](https://www.kvraudio.com/news-print.php?id=64457);
  not read in full).
- **Editing.** AI-generated pitch curves are combined with Smart Pitch
  Controls and a Pitch Deviation parameter
  ([docs: pitch](https://sv2.docs.dreamtonics.com/en/pitch), search excerpt
  only). Vocal Modes can be applied separately to pitch, timbre and
  pronunciation, alongside Loudness, Tension, Breathiness, Gender and Tone
  Shift sliders ([docs: version changes](https://sv2.docs.dreamtonics.com/en/prev-version-changes),
  search excerpt;
  [Mix review](https://www.mixonline.com/technology/reviews/others/dreamtonics-synthesizer-v-studio-2-pro-review)).
- **Languages.** Singing in English, Japanese, Mandarin, Cantonese, Spanish
  and Korean (Korean added in Studio 2), with cross-lingual singing. French,
  German, Brazilian Portuguese and Italian are listed as beta
  ([Wikipedia](https://en.wikipedia.org/wiki/Synthesizer_V); secondary).
- **Quality evidence.** Positive reviews
  ([Sound On Sound review](https://www.soundonsound.com/reviews/dreamtonics-synthesizer-v-studio-2-pro?amp),
  [Mix](https://www.mixonline.com/technology/reviews/others/dreamtonics-synthesizer-v-studio-2-pro-review)).
  No published listening-test numbers were found.
- **Runtime and cost.** A desktop app and plugin for Windows and macOS.
  Studio 2 was released on 21 March 2025
  ([Wikipedia](https://en.wikipedia.org/wiki/Synthesizer_V)). The free Basic
  edition exists; Pro launched at US$99 and voices are sold separately
  (about US$79 list) ([Dreamtonics store listing via search](https://store.dreamtonics.com/product/bundle-synthesizer-v-studio-2-pro-any-voice-database);
  [Sound On Sound news](https://www.soundonsound.com/news/dreamtonics-expand-synthesizer-v-studio-2-pro)).
  Current prices were not verified. **No public web API, server SDK or OEM
  programme was found.**
- **Licence (primary).** The Synthesizer V AI Megpoid EULA
  ([PDF](https://www.ssw.co.jp/products/synth_v/megpoid/ssvmg1_license_agreement_en.pdf),
  2023) is one voice's EULA and other voices may differ. Its terms:
  - Clause 10: synthesized sound may be used commercially or non-commercially
    free of charge "except as otherwise specified".
  - Clause 8: one computer per licence.
  - Clause 12: contact the licensors to embed the product in another product
    commercially.
  - Clause 13(9) and 13(10) prohibit sublicensing, lending and renting.
  - Clause 13(12) prohibits leaving the product operable by people who do not
    own it.
  - Clause 13(14) prohibits using rendered audio as input to any singing or
    speech synthesis model.
  - Clause 13(15) prohibits "using the product through a network".
  - Community guidance says each voice ships its own `license.txt`, and some
    third-party voices (e.g. POPY and ROSE) carry stricter terms
    ([SynthV forum](https://forum.synthesizerv.com/t/topic/10389);
    [forum guide](https://forum.synthesizerv.com/t/topic/6220)).
- **Maturity.** A shipping product for desktop users. As a back end for a
  multi-user web app, the EULA terms above rule it out unless a separate
  agreement is made.

### 2.2 ACE Studio (Timedomain)

- **Input.** MIDI and lyrics. Also a Vocal-to-MIDI tool that turns a sung
  recording into MIDI plus lyrics ([acestudio.ai](https://acestudio.ai/)).
- **Editing.** A piano-roll DAW with choir and ensemble modes. The page read
  gave little parameter detail.
- **Languages and voices.** 8 languages for vocal synthesis. The homepage
  says "140+" voices and the pricing page says "160+ royalty-free pre-made
  voices" ([home](https://acestudio.ai/), [pricing](https://acestudio.ai/pricing/)).
- **Voice cloning.** Users can upload vocal samples and train their own
  singing model ([home](https://acestudio.ai/)). Artist has 1 vocal-synth
  clone slot and 1 vocal-changer slot; Artist Pro has 5 and 10
  ([pricing](https://acestudio.ai/pricing/)).
- **Runtime and cost.** A desktop app on a credit-based subscription: Artist
  US$16.58/mo (2,500 credits) and Artist Pro US$22/mo (5,000 credits), both
  shown at 20% off on a "rent-to-own" two-year term
  ([pricing](https://acestudio.ai/pricing/)). Enterprise and team seats are
  mentioned without prices. **No public developer API was found**
  ([search summary](https://app.dealroom.co/companies/ace_studio); aggregator
  pages describing an "ACE Studio API" mix it up with ACE-Step and were
  disregarded).
- **Licence.** Voices are marketed as "royalty-free". **The terms of service
  could not be read**: the pages are JavaScript-rendered and the guessed URLs
  returned nothing usable. Network use, embedding and clone-consent clauses
  are unverified.
- **Maturity.** A shipping product for desktop users. No route to a web app
  back end was found.

### 2.3 VOCALOID6 and Mobile VOCALOID Editor (Yamaha)

- **Input.** Melody plus lyrics, using the VOCALOID:AI engine. VOCALO CHANGER
  turns your own sung input into the voicebank's voice, which makes it an SVC
  tool too ([VOCALOID6](https://www.vocaloid.com/en/vocaloid6/)).
- **Editing.** Accents, vibrato, rhythmic feel, 100+ style presets,
  doubling, and ARA2 integration with DAWs
  ([VOCALOID6](https://www.vocaloid.com/en/vocaloid6/)).
- **Languages and voices.** One voicebank can mix Japanese, English and
  Chinese lyrics. 20 VOCALOID6 voicebanks as of v6.9; V3–V5 banks also load
  ([VOCALOID6](https://www.vocaloid.com/en/vocaloid6/)).
- **On iPhone.** A subscription version of *Mobile VOCALOID Editor* with the
  VOCALOID:AI engine launched on the App Store on 20 October 2025: US$3.99
  per month with a 14-day trial, 40+ purchasable voicebanks, and MIDI input
  ([Yamaha press release](https://www.yamaha.com/en/news_release/2025/25102001/);
  [App Store](https://apps.apple.com/app/mobile-vocaloid-editor/id947797108)).
  This is a **native** app. It shows that neural singing synthesis runs on an
  iPhone, but it is not something a web app can call.
- **Licence (primary).** The VOCALOID6 voicebank EULA
  ([Zola EULA PDF](https://www.ssw.co.jp/products/vocaloid6/zola/va6zola_license_agreement_en.pdf)):
  - §3: Synthesized Singing may be used commercially. A carve-out applies
    when it is coupled with Yamaha trademarks or product names; the sentence
    is incomplete in the source.
  - §4(2): no output that violates the publicity rights of the original
    voice artist.
  - §4(3): the product may not be used "as a component of your software or
    the third party's software".
  - §4(5)(iii): it may not be placed on a network accessed by multiple users.
  - §4(8): it may not be provided to third parties as a studio or rental
    service.
  - §2.2: one computer per licence.
  - No public developer SDK or OEM programme was found.
- **Maturity.** A shipping product for desktop and native iOS users. The
  EULA rules out serving it from a web app back end without a separate
  agreement.

### 2.4 CeVIO AI (Techno-Speech / CeVIO project)

- Japanese-focused speech and song synthesis, sold per character. Prices seen
  start at ¥6,600 in 2021-era coverage; a retailer notes that commercial use
  may need additional licences and that activation needs internet access
  ([ondoku3 blog](https://ondoku3.com/en/post/cevio-ai/);
  [Soundhouse listing](https://www.soundhouse.co.jp/en/products/detail/item/318142)).
  Both are secondary sources.
- **Not verified:** current pricing, song-voice languages beyond Japanese,
  and the official commercial-use terms. The official site was not reached.
- **Maturity.** A shipping desktop product with a Japanese-language focus. No
  API was found.

### 2.5 Emvoice One

- A VST/AU/AAX plugin where you type words onto notes. Rendering happens in
  the vendor's **cloud**, so the plugin needs internet access to install and
  run ([emvoiceapp.com meta description](https://www.emvoiceapp.com/);
  [MusicTech](https://musictech.com/news/emvoice-one);
  [KVR](https://www.kvraudio.com/product/emvoice-one-by-emvoice)).
- Four voices (Keela, Lucy, Jay, Thomas). KVR lists them at US$99 each; an
  older MusicTech article says US$199. Unlicensed voices are limited to an
  eight-note range ([KVR](https://www.kvraudio.com/product/emvoice-one-by-emvoice)).
  English.
- Rendering is already server-side, but **no public API or licence for third
  parties to use that cloud was found**. EULA not read.
- **Maturity.** A shipping plugin. No route to a web app back end was found.

### 2.6 DiffSinger (OpenVPI) and OpenUtau: open source

- **What it is.** DiffSinger is a diffusion acoustic model that turns a score
  into a mel-spectrogram (AAAI 2022, [arXiv:2105.02446](https://arxiv.org/abs/2105.02446)).
  The paper reports that it beats prior SVS on a Chinese dataset; the
  abstract gives no numbers. The OpenVPI fork adds 44.1 kHz output and
  variance models that predict and control pitch, energy and breathiness. It
  is **Apache-2.0**, has about 3.2k stars, and its README forbids generating
  anyone's voice without consent ([repo](https://github.com/openvpi/DiffSinger)).
- **Editor.** OpenUtau is an MIT-licensed, cross-platform (Windows, macOS,
  Linux) open singing-synthesis editor with a MIDI and pitch editor
  ([repo](https://github.com/stakira/OpenUtau)). It renders DiffSinger
  voicebanks on CPU by default, or on DirectML or CoreML GPU, with an
  nsf-hifigan vocoder. Expression curves depend on the voicebank: gender,
  velocity, energy, breathiness, tension, voicing and voice colour
  ([wiki: DiffSinger support](https://github.com/stakira/OpenUtau/wiki/DiffSinger-support)).
- **Input.** Notes, lyrics and phonemes, using a phonemizer per language that
  depends on the voicebank.
- **Voicebank licences vary by creator; most restrict commercial use.**
  Examples:
  - [Ameko](https://hoodypprojectameko.carrd.co): CC BY-NC-ND 4.0 plus Commons
    Clause.
  - [NoLyui](https://nolyui.carrd.co/): original music may be released
    commercially, but the bank and its output may not be resold.
  - [MindLess/AltEOS](https://alteos-mindless.carrd.co/): needs a paid
    commercial licence.
  - [Peiton](https://nebm.gumroad.com/l/vvhyg): a US$30 commercial licence.
  - None of the banks checked grant rights to run them as a hosted service for
    other users. That would need a direct agreement with each bank's creator.
- **Browser.** No in-browser DiffSinger port was found. Browser TTS with ONNX
  Runtime Web exists (e.g. [vits-web](https://github.com/diffusionstudio/vits-web)),
  but that is speech, not singing.
- **Maturity.** Usable open source and used by hobbyists. Running it behind a
  web app is technically possible on a server (ONNX/PyTorch). Running it in
  the browser is unproven. Rights depend on the voicebank.

### 2.7 SoulX-Singer (Soul AI Lab), released 2026

- **Input.** Either a MIDI score with lyrics, or an F0 melody contour. It does
  **zero-shot** singing in a new voice from a short prompt, with no
  fine-tuning. Lyrics can be edited while the original prosody is kept. It
  includes a web MIDI editor for correcting lyrics, pitch and timing. Mandarin,
  English and Cantonese, trained on 42,000+ hours
  ([repo](https://github.com/Soul-AILab/SoulX-Singer);
  [arXiv:2602.07803](https://arxiv.org/abs/2602.07803)).
- **Timeline.** Code and models 6 February 2026; Hugging Face demo 9 February;
  SVC variant 16 March ([repo](https://github.com/Soul-AILab/SoulX-Singer)).
- **Licence.** Code is Apache-2.0, and the README says code and weights may be
  used. The README positions it for research, education and legitimate uses,
  and asks that it not be used to impersonate people without authorisation
  ([repo](https://github.com/Soul-AILab/SoulX-Singer)). The **weights
  licence on the Hugging Face model card was not checked separately.**
- **Quality evidence.** The authors claim state of the art on their own
  benchmark, SoulX-Singer-Eval. There is no independent evaluation, and MOS
  numbers were not read (abstract only).
- **Runtime.** Python with a GPU expected. No hardware figures are published.
- **Maturity.** Research-grade to early usable open source. It is the closest
  open match found to "notes + lyrics → sung vocal in a chosen voice".

### 2.8 Other research toolkits

- **ESPnet-SVS / Muskits**: score (lyrics, durations, pitches) to singing,
  with a public demo ([demo](https://espnet-svs.hf.space)). Research-grade.
- **Sinsy** (Nagoya Institute of Technology): HMM-based. The `midi2voice`
  wrapper scrapes the sinsy.jp website rather than calling a stable API
  ([midi2voice](https://github.com/mathigatti/midi2voice/blob/master/README.md)).
  Old quality, not suitable for production.
- **WeChat mini-program singing synthesis**: a hosted, asynchronous API, female
  voice only, inside the WeChat platform
  ([docs](https://developers.weixin.qq.com/doc/aispeech/en/mini_program/svs.html)).
  Not usable from an iPhone web app outside WeChat.

### 2.9 Hosted notes+lyrics singing API

**None found.** Searches found no general-purpose, documented commercial web
API that accepts notes plus lyrics and returns a sung vocal. The commercial SVS
vendors (Dreamtonics, Yamaha, Timedomain, Emvoice) sell desktop or native
software. The two EULAs read forbid network or service use and embedding
without a separate agreement. This is an absence of evidence from public
pages: a private enterprise or OEM licence from one of these vendors may exist
and would only be confirmed by contacting them, which was out of scope.

---

## 3. Voice conversion from the player's guide vocal (Kind B)

| Option | Input → output | Runtime / latency | Cost | Licence / consent | Maturity |
|---|---|---|---|---|---|
| **RVC** ([repo](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)) | Audio → target voice; trains a voice from ≤10 min of clean audio | Local GPU (CUDA), or CPU/DirectML. About 170 ms end-to-end real-time, 90 ms with ASIO | Free | MIT code. The page read had no consent disclaimer. Voice models are whatever users train | Usable open source, widely used |
| **Seed-VC** ([repo](https://github.com/Plachtaa/seed-vc)) | Audio → zero-shot target from a 1–30 s reference; singing model at 44.1 kHz with F0 conditioning | GPU. About 300 ms algorithmic plus about 100 ms device delay; 430 ms measured on an RTX 3060 laptop | Free | GPL-3.0. **Archived 21 Nov 2025 (unmaintained)** | Usable open source, frozen |
| **SoulX-Singer-SVC** ([repo](https://github.com/Soul-AILab/SoulX-Singer)) | Source singing + prompt voice → converted singing; no lyrics or MIDI needed | GPU | Free | Apache-2.0 code; non-impersonation clause | Research-grade |
| **Kits.ai** ([site](https://www.kits.ai/), [API quick start](https://docs.kits.ai/api-reference/introduction/quick-start)) | Audio file → royalty-free or custom voice. REST API (`POST …/voice-conversions`, multipart `voiceModelId` + `soundFile`, bearer token), job-based | Server, asynchronous. Latency not documented | Paid plans "start at $10/month" ([site](https://www.kits.ai/)). Other Kits pages say $9.99 and $14.99; per-call API price not found | Claims every library voice is licensed from the artist, with revenue share. Commercial terms not read | **Shipping, with a public API** |
| **ACE Studio vocal changer** | Audio → ACE or cloned voice | Desktop | In the subscription (§2.2) | ToS not read | Shipping (desktop) |
| **Dreamtonics Vocoflex** | Live or recorded voice → morphed singing voice, in real time | Desktop plugin (VST3/AU/AAX, standalone) | US$199 list (2025 review) | Identity verification required; watermarking identifies the creator ([Sound On Sound](https://www.soundonsound.com/news/real-time-voice-morphing-dreamtonics-vocoflex), [Beat review PDF](https://resource.dreamtonics.com/documents/reviews/Beat_231_04-2025_EN_vocoflex.pdf)) | Shipping (desktop) |
| **VOCALOID6 Vocalo Changer** | Your singing → voicebank voice | Desktop | Bundled | VOCALOID EULA (§2.3) | Shipping (desktop) |
| **ElevenLabs Voice Changer** ([docs](https://elevenlabs.io/docs/overview/capabilities/voice-changer)) | Audio (≤5 min per segment) → library or cloned voice; `eleven_multilingual_sts_v2` | Server API | 1,000 credits ("characters") per minute | Professional clones only of **your own** verified voice, never someone else's even with consent ([help](https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/can-i-create-a-professional-voice-clone-of-someone-elses-voice.md)) | Shipping. **Docs say nothing about singing or pitch preservation; built for speech** |

**Editability.** Every Kind B tool converts audio. Notes and lyrics are not
edited directly: a wrong note is fixed by re-singing it or by pitch-correcting
the guide before conversion. ACE Studio's Vocal-to-MIDI is the one documented
bridge from a guide vocal into an editable note-and-lyric track. It is
desktop-only.

**Real time.** The open-source real-time figures (90–430 ms) assume a local
desktop GPU. Nothing found does real-time singing conversion in iPhone Safari.

---

## 4. Song generators (Kind C): what stays editable

- **Suno.**
  - *Add Vocals* puts a vocal over an uploaded or generated instrumental from
    lyrics plus a style text. The only other control is an "Audio Strength"
    slider. It is in beta for Pro and Premier
    ([help](https://help.suno.com/en/articles/6882817)). The page shows **no
    control over melody or notes**.
  - Suno Studio exports the mix, stems or MIDI
    ([help: exporting](https://help.suno.com/en/articles/8128193)). Studio 2.0
    adds MIDI support and is limited to Premier
    ([RouteNote](https://routenote.com/radar/suno-studio-2-0-launches-with-midi-support-ai-chat-and-advanced-stem-separation/);
    secondary). MIDI is derived from the generated audio. Re-voicing *edited*
    vocal MIDI is not documented.
  - Commercial rights apply only to songs made on paid plans
    ([help](https://help.suno.com/en/articles/2410177)).
  - Suno settled with Warner Music in November 2025. Under the deal it moves
    to licensed models in 2026 and caps or charges for downloads
    ([Billboard](https://billboard.com/pro/suno-warner-music-sign-ai-licensing-deal-settle-lawsuit/)).
  - There is **no self-serve API**: an early-access partner programme was
    announced in July 2026 ([Digital Music News](https://www.digitalmusicnews.com/2026/07/03/suno-is-opening-an-api-partner-program/)).
    Unofficial wrappers reverse-engineer private endpoints.
- **Udio.** Since the October 2025 UMG settlement, downloads of audio and
  stems are disabled and creations stay in a "walled garden" until a licensed
  relaunch. No confirmed relaunch date was found as of October 2026
  ([Digital Music News](https://www.digitalmusicnews.com/2025/10/29/umg-udio-deal-everything-we-know/);
  [tech-insider](https://tech-insider.org/?p=9087), secondary).
- **Eleven Music (ElevenLabs).**
  - Prompt to song, with vocals or instrumental only, lyrics in several
    languages, tracks of 3 s to 5 min, and section-level editing and
    inpainting of sound and lyrics. Composition plans are supported in v2.5.
  - An audio reference (≤30 s) guides style but is **not a melody source**.
    There is **no MIDI or melody input**.
  - The API needs a paid plan. The output is described as "cleared for nearly
    all commercial uses", subject to the Music Terms
    ([docs](https://elevenlabs.io/docs/overview/capabilities/music)).
- **ACE-Step 1.5.** An open model (MIT): text2music, cover, repaint, extract,
  "lego" and complete. Reference audio is accepted, but there is no MIDI
  input. It needs <4 GB VRAM, and the card claims a full song in <10 s on an
  RTX 3090. The card says the output may be used commercially
  ([model card](https://huggingface.co/ACE-Step/acestep-v15-base)).
- **YuE.** An open model (Apache-2.0, credit requested) that turns lyrics into
  a full song with vocal and accompaniment tracks
  ([model card](https://huggingface.co/m-a-p/YuE-s1-7B-anneal-en-cot/blob/main/README.md)).
  There is no note-level melody control.

**Conclusion for Kind C:** none of these generators takes a user-written note
melody and sings it exactly. The best they offer is to regenerate lyrics or
sections (Eleven Music, Suno) or to export stems or MIDI after generation
(Suno Studio). The melody remains the model's choice.

---

## 5. How it would run behind an iPhone web app

**In the browser.**
- Safari ships WebGPU in iOS 26
  ([web.dev](https://web.dev/blog/webgpu-supported-major-browsers)).
- ONNX Runtime Web offers wasm, WebGPU, WebNN and WebGL back ends. It
  supports only a subset of operators off-CPU and advises running large
  models on a server
  ([ORT Web docs](https://onnxruntime.ai/docs/tutorials/web/)).
- No in-browser singing synthesiser was found, only speech TTS
  ([vits-web](https://github.com/diffusionstudio/vits-web)).
- Mobile VOCALOID shows that singing synthesis can run on iPhone hardware, but
  natively (§2.3).
- In-browser singing is therefore **unproven**. iPhone Safari memory limits
  for such models were not researched.

**On a server.**
- The open-source routes (DiffSinger, SoulX-Singer, RVC, Seed-VC) run in
  Python or ONNX on a GPU.
- Reference rental prices: T4 about US$0.59/h, L4 about US$0.80/h, A10 about
  US$1.10/h, A100-40GB about US$2.10/h
  ([Modal pricing](https://modal.com/pricing)).
- **Cost per sung minute was not measured.** No real-time factors were
  published for these SVS models. One sung minute would cost about US$0.01–0.02
  of L4 time at a real-time factor of 1. This is arithmetic, not a benchmark.
  Cold starts, model loading and idle time would dominate at low volume.
- Rendering is a request-response (offline) job. Each edit would mean
  re-rendering a phrase or a song, not live performance.

**Through an API.**
- Usable public APIs found: Kits.ai (singing voice conversion from audio) and
  ElevenLabs Voice Changer (speech-oriented) and Eleven Music (prompt songs).
  None takes notes plus lyrics.
- Latency for a whole render is not documented for any of them.

**Real-time.** Low-latency figures exist only for local desktop GPU
conversion (§3).

---

## 6. Rights

**Licences for voicebanks and models.**
- Commercial desktop SVS output is generally cleared for commercial *music*
  (Synthesizer V EULA cl. 10; VOCALOID6 EULA §3).
- The same EULAs forbid running the engine through a network, embedding it in
  other software, or offering it to third parties as a service. They also
  forbid using rendered audio to train synthesis models (SynthV cl. 12,
  13(14), 13(15); VOCALOID §4(3), 4(5)(iii), 4(8)).
- Open-source code licences are permissive: Apache-2.0 for DiffSinger and
  SoulX-Singer code, MIT for RVC, OpenUtau, ACE-Step and others. GPL-3.0
  applies to Seed-VC.
- Community voicebanks carry separate licences, and many are non-commercial
  (§2.6).

**Voice likeness and consent.**
- **Tennessee ELVIS Act**: in force since 1 July 2024. It adds voice,
  including simulated voice, to publicity rights. Commentators note that
  liability may reach technology providers that enable unauthorised
  replication, not only the people who publish it
  ([HB2091](https://www.capitol.tn.gov/Bills/113/Bill/HB2091.pdf), not opened;
  [Manatt summary](https://manatt.com/insights/newsletters/client-alert/tennessees-elvis-act-expands-publicity-rights-for)).
- **US NO FAKES Act of 2026** (S. 4591): introduced 20 May 2026 and passed
  the Senate Judiciary Committee on 18 June 2026
  ([Sen. Blackburn release](https://www.blackburn.senate.gov/2026/6/blackburn-coons-bipartisan-bill-to-protect-individuals-and-creators-from-deepfakes-passes-senate-judiciary-committee)).
  It would create a federal right over digital replicas of voice, with notice
  and takedown. **Not law as far as found**; floor status after June not
  verified.
- **EU AI Act Article 50**
  ([Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)):
  transparency duties apply from 2 August 2026. Providers must mark synthetic
  audio as machine-readable. Deployers must disclose deepfakes, which include
  audio resembling existing persons. Secondary sources report a grace period
  to 2 December 2026 for the marking duty on systems already on the market
  ([SRD Rechtsanwälte](https://www.srd-rechtsanwaelte.de/en/blog/deepfake-labelling-under-the-ai-act-what-the-new-eu-guidance-clarifies)).
  The amending text was not checked.
- **Vendor consent rules**:
  - ElevenLabs: professional clones only of your own verified voice.
  - Vocoflex: identity verification and watermarking.
  - DiffSinger and SoulX-Singer READMEs: no use without consent or
    authorisation.
  - VOCALOID EULA §4(2): no output that violates the original voice artist's
    publicity rights.

**Platform rules.**
- Spotify's September 2025 policy allows vocal impersonation only with the
  artist's authorisation, and adopted DDEX AI-use credits covering AI vocals
  ([TechRadar](https://www.techradar.com/ai-platforms-assistants/spotify-is-cracking-down-on-ai-voice-clones-with-new-impersonation-rules-for-music-uploads),
  secondary; the original newsroom post was not read).
- Suno warns that monetising requires being the exclusive rights-holder of
  all material, lyrics included
  ([help](https://help.suno.com/en/articles/2410177)).

---

## 7. What this means for Band mode

Findings only. No product decisions.

**Possible now**
- Notes plus lyrics to a high-quality, fully editable sung vocal, **in desktop
  or native apps** (Synthesizer V, ACE Studio, VOCALOID6, Mobile VOCALOID
  Editor on iPhone). The editing model these tools share is the reference
  design: a piano roll of notes, a syllable per note, pitch curves and
  expression sliders.
- Hosting open-source SVS (DiffSinger-family, SoulX-Singer) on a rented
  server GPU and calling it from a web app, as offline renders. The code
  licences permit it.
- Converting a player's recorded guide vocal to another singing voice through
  a public server API (Kits.ai) or self-hosted RVC.

**Possible, with caveats**
- **A commercial-grade voice behind a web app.** The main commercial SVS
  EULAs read forbid network or service use and embedding. Using one would
  need a separate agreement that was not found publicly. Open voicebanks
  mostly forbid commercial use or say nothing about hosted use.
- **An open-source "AI lead singer".** SoulX-Singer offers zero-shot voices
  with MIDI and lyrics input, but it is months old, the quality claims come
  from the authors, its languages are Mandarin, English and Cantonese, and it
  needs a GPU. DiffSinger quality depends on the voicebank.
- **Editing turnaround.** Server rendering means re-rendering after an edit.
  Latency and cost per minute are unmeasured.
- **The player's own voice as a guide.** Kind B keeps the performance
  editable only by re-singing it. ACE Studio's Vocal-to-MIDI shows that
  audio-to-editable-notes is possible, but it is desktop-only.
- **Rights.** Voice likeness laws (ELVIS Act, EU AI Act Art. 50, the pending
  NO FAKES Act) and Spotify policy favour licensed or consenting voices and
  disclosure of AI vocals.

**Research-grade**
- Zero-shot singing in a new voice from a short prompt (SoulX-Singer,
  Seed-VC).
- Running singing synthesis in iPhone Safari (WebGPU or wasm). Neither a port
  nor a benchmark was found.

**Not found / doesn't appear to exist publicly**
- A public, documented web API that takes notes plus lyrics and returns a
  sung vocal.
- A song generator (Suno, Udio, Eleven Music, ACE-Step, YuE) that sings a
  user-written note melody exactly. Their editing works on lyrics and
  sections, not notes.
- Real-time AI singing conversion in mobile Safari.

---

## 8. Not verified

- Dreamtonics' official pages (Cloudflare challenge). Synthesizer V features,
  languages and prices are from search excerpts, Wikipedia, reviews and
  retailers. Current prices are unconfirmed.
- Whether the Megpoid EULA clauses (network use, embedding, training) apply
  to every Synthesizer V voice and to the Studio 2 editor EULA. Only one
  voice EULA was read.
- ACE Studio's terms of service (could not be loaded) and whether any
  enterprise or API offering exists.
- CeVIO AI official terms, prices and languages; Emvoice's EULA and current
  prices.
- SoulX-Singer's weights licence on Hugging Face and its MOS numbers.
- Kits.ai API per-call pricing, latency and commercial terms.
- Whether ElevenLabs Voice Changer preserves sung pitch.
- Whether Suno Studio can re-sing edited vocal MIDI.
- Udio relaunch status; NO FAKES Act floor status after June 2026; final EU
  Article 50 guidance and the grace-period text.
- Any real-time factor, latency or quality measurement. Nothing was run or
  listened to.
