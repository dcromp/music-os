# Band mode: music AI for creating and editing editable band parts

> *Research by AI (Claude Code), 27 October 2026.* Answers
> [issue #65](https://github.com/dcromp/music-os/issues/65) (part of #64).
> All sources were checked on 27 October 2026 unless noted. Where a claim
> rests on a secondary source, or could not be checked against the owner's
> page, it is flagged **(unverified)**. This note reports what exists. It does
> not choose a product direction.

## The question

What can music AI do today to create and edit the **band parts** (drums, bass,
keys) for a player's own song so that the result stays **editable**, rather
than a finished audio file? "Editable" here means one of:

1. **Symbolic**: notes (MIDI or similar) that the player can change one by one.
2. **Parametric**: a part made from settings (style, complexity, fills,
   chords) that can be changed and regenerated.
3. **Audio stems**: separate audio tracks per instrument. These can be muted,
   replaced, cut and regenerated, but individual notes cannot be edited.

These three levels come up throughout the note.

---

## 1. Symbolic (MIDI-level) generation of drums, bass and keys

| System | What it does | Control | Output | Licence | How it runs | Maturity |
|---|---|---|---|---|---|---|
| **MIDI-GPT** (Metacreation Lab) | Multitrack generation; fills missing bars or adds a new track while keeping the rest | Instrument, note density, polyphony, note length; `prism`/`expressive` models add key, pitch range, pitch classes and genre, per bar or overall | MIDI | Code MIT; **weights non-commercial research and education only** (gated on Hugging Face) | Python API, HTTP server, OSC server; prebuilt wheels for Linux/macOS/Windows | Usable open source, research licence ([repo](https://github.com/Metacreation-Lab/MIDI-GPT)) |
| **Anticipatory Music Transformer** (Stanford CRFM) | Generates MIDI given a time span; can generate an accompaniment to a supplied melody; infilling | Melody/events as control input, time spans | MIDI | Apache 2.0; weights on Hugging Face (`stanford-crfm`) | Self-host, Python | Usable open source ([repo](https://github.com/jthickstun/anticipation), [paper](https://arxiv.org/abs/2306.08620)) |
| **Composer's Assistant 2** | Fills in MIDI inside the REAPER DAW: you blank some bars or tracks and it writes them to fit the rest | Global and per-track controls set before generating (ISMIR 2024 paper adds fine-grained control) | MIDI in REAPER | MIT; trained only on public-domain and permissively licensed MIDI | Local server on the user's machine; no network calls; REAPER only | Usable open source, v2.1.0 ([repo](https://github.com/m-malandro/composers-assistant-REAPER)) |
| **text2midi** (AMAAI Lab) | Text prompt to multitrack MIDI file | Text only; prompt may name chords, key, tempo, time signature, instruments, style | MIDI | MIT; weights on Hugging Face | Self-host; CUDA, Apple MPS or CPU | Research-grade, AAAI paper ([repo](https://github.com/AMAAI-Lab/Text2midi)) |
| **MIDI-LLM** | Llama 3.2 1B extended with MIDI tokens; text-to-multitrack-MIDI, plus lead-sheet (melody and chords) generation and infilling | Text; partial lead sheet | MIDI | Paper CC BY 4.0; **code/weight release not confirmed** on the arXiv page | Uses vLLM | Research-grade, ISMIR 2026 ([arXiv 2511.03942](https://arxiv.org/abs/2511.03942)) |
| **Aria** (EleutherAI) | Continues an existing MIDI file | Prompt with existing music only | MIDI | Apache 2.0 | Self-host, 0.7B parameters | Usable open source, but **solo piano**; multitrack only lightly trained ([model card](https://huggingface.co/loubb/aria-medium-base)) |
| **ChatMusician** | LLaMA2 model that reads and writes ABC notation (text music); composes from text, chords, melodies, motifs, forms | Text and symbolic prompts | ABC notation (convertible to MIDI) | Weights licence not stated on the paper page **(unverified)** | Self-host | Research-grade, Feb 2024 ([arXiv 2402.16153](https://arxiv.org/abs/2402.16153)) |

Commercial MIDI generators (all **unverified** beyond retailer or review
pages):

- **Staccato**: AI MIDI co-writer from text prompts and reference tracks,
  standalone or VST3/AU/AAX plugin; the Basic tier is personal, non-commercial
  use only ([Best Service listing](https://www.bestservice.com/en/staccato_pro.html),
  [Basic](https://www.bestservice.com/en/staccato_basic.html)).
- **Lemonaide**: melodies and chords as MIDI and audio; a review says BeatStars
  bought it in January 2026 ([review](https://www.aimusicpreneur.com/ai-tools/lemonaide-ai/)).
- **Scaler 3**: chord suggestions from existing harmonic context and a phrase
  generator that follows chords ([review](https://unison.audio/scaler-3/)).

**Summary of this section.** There are working open-source models that
generate or fill in MIDI given surrounding music, and some that take text.
None of the open ones combines all of: drums + bass + keys together,
conditioning on a chord chart, tempo **and** song sections, a licence that
allows commercial use, and a size that runs in a phone browser. Chord
conditioning, where it exists, comes either from the surrounding notes
(infilling) or from text. Explicit "this chord chart, these sections" input
is in research papers (for example
[SymphonyGen](https://arxiv.org/pdf/2604.25498) uses a harmony skeleton, and
[M6(GPT)3](https://arxiv.org/html/2409.12638) takes chord progressions as a
JSON structure), not in shipping tools.

---

## 2. Directing parts in words ("busier chorus", "fill before the bridge")

Patterns that exist:

1. **LLM chooses and calls tools over a shared song state.** Loop Copilot
   (2023, revised 2024) uses an LLM to read the user's request and pick a
   backend model for each step, and keeps the key musical attributes in a
   central table so repeated edits stay consistent
   ([arXiv 2310.12404](https://arxiv.org/abs/2310.12404)). It is research and
   appears to be audio-focused.
2. **LLM writes MIDI clips directly.** A 2023 paper used ChatGPT to turn
   language into MIDI clips inside a DAW
   ([arXiv 2312.03479](https://arxiv.org/html/2312.03479v1)). Open-source MCP
   servers now let Claude and other LLMs create tracks, MIDI clips and notes in
   Ableton Live, for example
   [ableton-mcp-extended](https://github.com/uisato/ableton-mcp-extended) (MIT).
   These are hobby projects, not products.
3. **LLM edits settings, not notes.** Instead of writing notes, the LLM changes
   parameters of a rule-based or model-based player (style, complexity,
   intensity, fill on/off) and the player regenerates. No shipping product was
   found that exposes this through free text; the parameter players
   themselves (Logic Session Players, section 5) are controlled with knobs.
4. **Chat inside a product.** Suno Studio 2.0 (Aug 2026) added a beta chat bar
   that can create instruments and vocals, help design plugins and "tidy up"
   a session ([Suno blog](https://suno.com/blog/studio-2)). Its output is
   audio. A commercial plugin, MIDI Agent, says it generates and rewrites MIDI
   sections from prompts using several LLM providers
   ([Product Hunt](https://www.producthunt.com/@midiagent), **unverified**).

How well it works: a Cal Poly thesis (2026) states there is "currently no
robust AI-based system" that reliably turns free-form language into edits on
symbolic scores ([flyer](https://ceng.calpoly.edu/sites/default/files/2026-08/Thesis%20Flyer%20-%20Lim%20%281%29.pdf)).
No benchmark was found that measures instructions like "busier chorus"
against a structured arrangement.

---

## 3. Songwriting help: chords, structure, melody, lyrics

- **Hookpad Aria** (Hooktheory) is the clearest shipping example. It writes
  chords for a melody, a melody for chords, or both, and can fill a gap in the
  middle of a song using the bars around it. It is the Anticipatory Music
  Transformer fine-tuned on Hooktheory's TheoryTab database of over 50,000
  pop song analyses. Output is a lead sheet (editable notes and chords). Since
  March 2024 it produced 318k suggestions for 3k users, of which 74k were
  accepted. Listed at $14.99/month as a Hookpad add-on
  ([Aria page](https://hooktheory.com/hookpad/aria),
  [ISMIR 2024 LBD](https://ismir2024program.ismir.net/lbd_489.html)).
- **MIDI-LLM** reports the best acceptance rate among the models it tested for
  "zero-to-one" lead-sheet generation, in a blind study with 58 Hookpad Aria
  users ([arXiv 2511.03942](https://arxiv.org/abs/2511.03942)).
- **Logic Pro Chord ID** (Logic Pro 12, Jan 2026) turns an audio or MIDI
  recording into a chord progression on the chord track, which the Session
  Players then follow ([Apple announcement via BusinessWire](https://www.businesswire.com/news/home/20260113468282/en/Apple-introduces-Apple-Creator-Studio-an-inspiring-collection-of-the-most-powerful-creative-apps)).
  Logic Pro 12.3 improved extended chords and inversions
  ([Synth Anatomy](https://synthanatomy.com/2026/06/apple-logic-pro-12.html), secondary).
- **Band-in-a-Box 2026** can generate chords for an intro, and its new
  AI-Notes transcribes audio to MIDI ([manual, ch. 3](https://www.pgmusic.com/manuals/bbw2026full/chapter3.htm)).
- **General-purpose LLMs** (Claude, ChatGPT etc.) are commonly used for lyrics,
  structure and chord-progression ideas as text. No primary source measuring
  their musical quality for this was checked; ChatMusician's paper (2024) reports its
  own model beat a GPT-4 baseline on composition and beat LLaMA2 and GPT-3.5
  zero-shot on its college-level music-theory benchmark
  ([arXiv 2402.16153](https://arxiv.org/abs/2402.16153)). Those comparisons
  are with 2023-era models.
  Text chord charts from an LLM are trivially editable, which matters more
  here than quality.

---

## 4. Audio generation models

| Model / service | Does | Editable? | Licence / terms | Runs | Maturity |
|---|---|---|---|---|---|
| **Magenta RealTime 2** (Google) | Streams instrumental audio live; steered by text, example audio **and MIDI** (per-frame note on/sustain vector); ~200 ms control latency; 48 kHz stereo | Audio only out, but takes the player's MIDI as conditioning | Code Apache 2.0, **weights CC BY 4.0**; Google claims no rights in outputs; trained on ~71k hours of mostly instrumental stock music | On-device; 2.4B (base) and 230M (small) parameters; no hosted provider | Usable open source, new (2026); evaluation report "forthcoming" ([model card](https://huggingface.co/google/magenta-realtime-2)) |
| **ACE-Step 1.5 / XL** | Full songs with vocals, 10 s to 10 min; Repaint (regenerate a region), Cover, plus Extract, Lego and Complete on base models; stem separation and track layering | Audio; region regeneration and layering | Code MIT; weight licence not stated separately on the repo page; no training-data statement | Self-host; under 4–6 GB VRAM for the smallest setup; Apple Silicon via MPS/MLX; DiT 2B/4B, LM 0.6–4B | Usable open source ([repo](https://github.com/ace-step/ACE-Step-1.5)); XL released 2026-04-02 |
| **Stable Audio 3.0** (Stability AI) | Instrumental music and SFX, up to 6 min 20 s; no vocals | Audio | Community Licence: free commercial use under $1M annual revenue; Enterprise above, with indemnity. Trained on licensed AudioSparx plus Creative Commons Freesound audio (1.28M recordings) | Small/Small SFX/Medium as open weights (runs on a MacBook Pro M4); Large via API | Shipping + usable open weights ([Stability explainer](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared), updated 9 Sep 2026) |
| **MusicGen (Melody)** (Meta) | Text + a reference melody (chroma) to audio | Audio | Code MIT, **weights CC BY-NC 4.0** (non-commercial); ~20k hours licensed music | Self-host, 1.5B | Older research model ([model card](https://huggingface.co/facebook/musicgen-melody)) |
| **Diff-A-Riff** (Sony CSL) | Generates a single-instrument accompaniment that fits a given music context; control by reference audio, text or both | Audio stem that fits existing tracks | Research; a public prototype was announced Nov 2024 (naming unclear) | ~0.5 s per 10 s on GPU | Research-grade ([arXiv 2406.08384](https://arxiv.org/abs/2406.08384)) |
| **Lyria 3 / Lyria 3 Pro** (Google) | Text (and image) to stereo audio, vocals and lyrics; Pro does up to ~3 min with intros/verses/choruses/bridges | Audio only; no stems or MIDI mentioned | SynthID watermark and C2PA credentials on all output; trained on material YouTube/Google "have a right to use"; output filtered against existing content | Vertex AI API, public preview (8 Apr 2026) | Shipping API ([Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/lyria-3-and-lyria-3-pro-on-vertex-ai/)) |
| **Eleven Music** (ElevenLabs) | Text to song with or without vocals, 3 s–5 min; "composition plans" per section; inpainting (regenerate one section); 30 s audio reference; fine-tunes on your own tracks | Section-level regeneration; no stems or MIDI on the capability page (a marketing page lists stems on self-serve **(unverified)**) | Free plan needs attribution and has no downloads; paid plans allow most commercial use except film/TV/radio/studio games below Enterprise; user keeps rights in input and output; prompts may not name real artists or songs | API (paid) | Shipping ([capabilities](https://elevenlabs.io/docs/overview/capabilities/music), [music terms](https://elevenlabs.io/music-terms), updated 9 Oct 2026) |
| **Suno** (models behind Suno and Suno Studio) | Full songs; in Studio, generates new stems into an existing timeline; MIDI clips can seed new audio generations | Audio stems; MIDI extracted *from* audio (see section 5) | See section 6 | Web only | Shipping |

**Do any keep results editable?** Partly:

- **Conditioning on the player's own material** exists. Magenta RealTime 2
  takes MIDI; Suno Studio 2.0 takes MIDI clips as prompts; Moises AI Studio and
  Suno Studio generate a stem against existing audio; Diff-A-Riff does this in
  research.
- **Stem output** exists (Suno Studio, Moises, ACE-Step layering). Stems are
  editable at track level, not note level.
- **Native MIDI out from an audio model** was not found. Where MIDI is offered
  (Suno "Get MIDI", Band-in-a-Box AI-Notes, BandLab Audio-to-MIDI), it is a
  transcription of generated or recorded audio, with the usual transcription
  errors.

---

## 5. Products doing something close

| Product | What it does | Editability of AI output | Doesn't do | Platform |
|---|---|---|---|---|
| **Logic Pro Session Players** (Drummer, Bass Player, Keyboard Player, Synth Player) | Virtual players that follow the chord track (or per-region chords); Bass has eight players, complexity/intensity, slides, mutes, dead notes; Keyboard has four styles; Synth Player added in Logic Pro 12 | **High.** Parametric (change style, complexity, regenerate) and convertible to normal MIDI regions for note editing. Converting back loses note edits ([iPad guide](https://support.apple.com/guide/logicpro-ipad/lpip23a32573/ipados)) | No text instructions; no songwriting; Apple says patterns follow chords, Sound On Sound calls them largely preset-based phrases ([SOS](https://www.soundonsound.com/techniques/logic-pro-synth-players?amp)) | Mac and iPad only, not iPhone; M-series recommended ([Apple Newsroom, May 2024](https://www.apple.com/newsroom/2024/05/logic-pro-takes-music-making-to-the-next-level-with-new-ai-features/); [Logic Pro 12, Jan 2026](https://www.businesswire.com/news/home/20260113468282/en/Apple-introduces-Apple-Creator-Studio-an-inspiring-collection-of-the-most-powerful-creative-apps)) |
| **GarageBand (iPhone/iPad)** | Drummer ("virtual session drummers"), Smart Instruments, Live Loops | Drummer parts are settings-driven; Apple's GarageBand page does not mention Session Players, Bass/Keyboard Player or a chord track | No bass/keys players found for iPhone | iOS ([apple.com/garageband](https://www.apple.com/garageband/)) |
| **BandLab SongStarter** | From a genre, a mood, or up to 50 characters of lyrics/emoji, gives 3 short ideas (beat, melody, chords) which open in BandLab Studio; built with Google on TensorFlow (2022) | Opens in a DAW for editing; whether as MIDI or audio was not confirmed. BandLab's separate "Smart Tools" (Layer, Extend, Recompose on MIDI) are described only by third-party guides **(unverified)** | Not a full arrangement tool | Web and mobile ([GearNews, Mar 2022](https://www.gearnews.com/introducing-bandlab-songstarter-a-source-for-that-creative-spark); help page returned 403) |
| **Band-in-a-Box 2026** | Type a chord chart, pick a style, and it generates a full band. RealTracks are recorded audio phrases; MIDI tracks and MIDI SuperTracks are notes; Playable RealTracks let you switch a part to MIDI notes with a matching sound; AI-Notes and AI-Stems transcribe and split audio | **High for MIDI tracks**; RealTracks are audio | Desktop-first; no text direction | Windows and Mac (Mac release 21 Apr 2026); Android app included; iOS app access listed in a bonus pack ([manual ch. 3](https://www.pgmusic.com/manuals/bbw2026full/chapter3.htm), [packages](https://www.pgmusic.com/bbmac.packages.htm)) |
| **Suno Studio 2.0** (13 Aug 2026) | Browser DAW: generate stems into an existing song, two takes per generation, comping, record audio, import/record/edit MIDI with a built-in synth; MIDI clips seed audio generation; beta chat bar | Audio stems (multitrack export, 32-bit/48 kHz unlimited for Premier); "Get MIDI" converts a stem to MIDI for 10 credits ([export help](https://help.suno.com/en/articles/8128193)) | No VST/AU hosting; generated parts are audio, not notes; **Safari has no Web MIDI** so MIDI input needs another browser | Web, Premier plan only ([intro](https://help.suno.com/en/articles/7940161), [blog](https://suno.com/blog/studio-2)) |
| **Moises AI Studio / Stem Generation** (live since 19 Aug 2025) | Upload or record an idea; it generates drums, bass, guitar, keys or strings that follow its key, tempo and chords; genre presets or text; per-stem control of how closely it follows the project; Smart Selection fills a highlighted section | Audio stems; regenerate, audition takes. No MIDI output mentioned | No note-level editing | Browser, desktop and mobile apps ([feature page](https://moises.ai/features/stem-generation), [announcement](https://moises.ai/newsroom/product-announcements/ai-studio-tool-music-creator)) |
| **Udio** | Text-to-song | Downloads of audio, video and stems disabled since 29 Oct 2025 under the UMG settlement; a licensed "walled garden" platform was planned | Not usable for export | **(unverified)**: Udio help pages could not be read; status from secondary sources ([RouteNote](https://routenote.com/blog/udio-temporarily-reopens-downloads-amid-creator-outcry/)) |
| **Hookpad Aria** | See section 3 | Lead sheet notes and chords | Not a band arranger | Web |

---

## 6. Rights: outputs and training data

| Provider | Who owns / may use outputs | Training data stated |
|---|---|---|
| **Suno** ([terms](https://suno.com/terms), revised 10 Aug 2026, effective 3 Sep 2026) | Free/Basic: personal, non-commercial only. Pro/Premier: Suno assigns its rights in outputs, but commercial use only for outputs obtained through an allowed download within the monthly allowance; no commercial use of Remixes; Suno does not promise copyright exists in any output. Users grant Suno a perpetual, irrevocable licence to their content, including for training Suno's models, and may not use outputs to train other AI | Not stated in terms. Warner settled and partnered with Suno in Nov 2025 (secondary: [Music in Africa](https://www.musicinafrica.net/magazine/suno-adjusts-ai-music-ownership-terms-after-warner-music-partnership)) |
| **ElevenLabs Music** ([music terms](https://elevenlabs.io/music-terms), 9 Oct 2026) | User keeps rights in input and output; plan sets uses (see section 4); user must clear outputs before use; watermarks not guaranteed | Not stated in terms; marketing says licensed |
| **Google Lyria 3** ([blog](https://cloud.google.com/blog/products/ai-machine-learning/lyria-3-and-lyria-3-pro-on-vertex-ai/)) | Bound by Google Cloud terms and prohibited-use policy; indemnity not mentioned on the page | Material YouTube/Google "have a right to use" |
| **Magenta RealTime 2** ([card](https://huggingface.co/google/magenta-realtime-2)) | Google claims no rights in generated outputs; weights CC BY 4.0 | ~71k hours stock music |
| **Stable Audio 3.0** ([explainer](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared)) | Commercial use free under $1M revenue; Enterprise licence (with indemnity) above | Licensed AudioSparx + CC Freesound |
| **MusicGen** ([card](https://huggingface.co/facebook/musicgen-melody)) | Weights non-commercial | Licensed Meta/Shutterstock/Pond5 |
| **MIDI-GPT** ([repo](https://github.com/Metacreation-Lab/MIDI-GPT)) | Weights non-commercial research/education | — |
| **Composer's Assistant** ([repo](https://github.com/m-malandro/composers-assistant-REAPER)) | MIT | Public-domain and permissively licensed MIDI only |
| **Anticipatory Music Transformer**, **Aria**, **text2midi** | Apache 2.0 / Apache 2.0 / MIT | Lakh MIDI (AMT, per [Hooktheory](https://www.hooktheory.com/blog/generative-ai-songwriting/)); Aria-MIDI piano transcriptions; SymphonyNet + MidiCaps. Note: a permissive code/weight licence does not settle the rights status of the training MIDI |
| **Moises** ([feature page](https://moises.ai/features/stem-generation)) | "Your audio and ideas remain yours"; uploads used only for conditioning, then discarded; never used for training. Full terms not checked | Not stated |
| **BandLab SongStarter** | Patterns described as royalty-free (2022 press) | Not public |

**Copyright in AI parts (US).** The US Copyright Office's January 2025 report
says AI output is protected only where a human contributes enough expressive
content: human material perceptible in the output, or creative selection,
arrangement or modification of it. Prompts alone are not enough
([Copyright Office, Part 2](https://copyright.gov/newsnet/2025/1060.html)).
For an editable workflow, this means the player's own written and edited
parts carry the clearest claim. No UK or EU primary source was checked.

---

## What this means for Band mode

Framed for an editable workflow on an iPhone web app. These are the facts as
found, not a recommendation.

**Possible now**

- Chord-following band parts that are editable as notes or as settings. Logic
  Pro Session Players and Band-in-a-Box both do this, which shows the pattern
  works. Neither runs on iPhone in a browser, and neither is a component that
  can be licensed into another app.
- Lead-sheet help (chords for a melody, melody for chords, fill a gap) as
  editable notes: Hookpad Aria in product; Anticipatory Music Transformer
  (Apache 2.0) underneath.
- Open, permissively licensed MIDI models that fill in or continue parts given
  surrounding music: Anticipatory Music Transformer, Composer's Assistant (MIT,
  clean training data), Aria (piano only), text2midi (MIT, text only).
- An LLM reading and writing a structured arrangement (chords, sections,
  notes as text/JSON) and calling tools: this is how the Ableton MCP projects
  work today.
- Generating an **audio** stem that fits the player's recording (Moises, Suno
  Studio), with commercial terms on paid plans.

**Possible with caveats**

- Running a symbolic model on the server behind the web app: the open models
  are small enough (0.7B–1B class for Aria/MIDI-LLM; MIDI-GPT smaller), but
  the best-controlled one (MIDI-GPT) is non-commercial, and none is trained
  specifically on drums+bass+keys following a chord chart with sections.
- LLM direction of edits ("busier chorus"): workable if the LLM changes
  parameters or calls a generator over a structured song model; no product or
  benchmark shows free-text note editing is reliable.
- Audio models conditioned on the player's MIDI (Magenta RealTime 2,
  CC BY 4.0) or audio (Suno Studio, Moises): output is audio, editable only as
  whole stems. Getting notes back needs transcription.
- MIDI input from a keyboard in the browser: Safari on iOS does not support
  Web MIDI ([caniuse](https://caniuse.com/midi)). Audio input from a USB
  interface is a separate path not covered here.
- Rights: commercial use is plan-dependent (Suno, ElevenLabs), revenue-capped
  (Stable Audio) or barred (MusicGen, MIDI-GPT weights). Copyright in purely
  generated parts is uncertain in the US.

**Research-grade**

- One model that takes a chord chart, tempo, sections and style and writes
  coordinated drums, bass and keys as MIDI (MIDI-LLM, SymphonyGen, M6(GPT)3 are
  papers; code/weights not confirmed for MIDI-LLM).
- Accompaniment-stem generation as an open model (Diff-A-Riff).
- Loop Copilot-style multi-turn editing with a shared musical state.

**Not found / doesn't exist (as of 27 Oct 2026)**

- An audio generation model that outputs native MIDI rather than transcribed
  MIDI.
- A shipping product where the player types an instruction and the band's MIDI
  parts are edited note-accurately and reliably.
- An iPhone-browser product with chord-following, note-editable AI band parts.

## Not verified

- Udio's current download and platform status (help pages unreadable).
- BandLab Smart Tools and SongStarter output format (official help page
  returned 403).
- ElevenLabs stem output; Staccato, Lemonaide, Scaler 3 details; MIDI Agent.
- ACE-Step weight licence (repo page shows MIT for code only).
- Suno MIDI extraction quality; plan required for "Get MIDI".
