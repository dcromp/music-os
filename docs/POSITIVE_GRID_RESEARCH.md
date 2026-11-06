# Positive Grid Spark: Spotify, backing tracks and what Bandmaker should take

Research for [#89](https://github.com/dcromp/music-os/issues/89), part of [#64](https://github.com/dcromp/music-os/issues/64).

**Researched 6 November 2026.** All pages were accessed on that date unless a citation says otherwise. This is product research from public sources. It is not legal advice. It builds on the [YouTube and Chordify terms note](YOUTUBE_CHORDIFY_TOS_RESEARCH.md) and the [song-access comparison](SONG_ACCESS_FEASIBILITY.md), and does not replace them.

Tags: **VERIFIED** means a primary source says it. **INFERENCE** is our reasoning. **UNKNOWN** means public evidence does not settle it. **OPINION** is a reviewer or user view. **Recollection** is unverified memory. "Excerpt" means only a search excerpt of the page was seen.

## Short answer

**How does the Spotify feature not break Spotify's terms?** Today, because it doesn't exist.

- Positive Grid [removed Spotify from the Spark app](https://help.positivegrid.com/hc/en-us/articles/25200624662925-Spotify-Integration-Removed-in-Spark-App-v4-1-1). Its [iOS release notes](https://help.positivegrid.com/hc/en-us/articles/8139979538829-Spark-App-Update-History-Release-Notes-iOS-iPadOS) date this to 11 November 2024.
- Auto Chord now [names YouTube as its song source](https://help.positivegrid.com/hc/en-us/articles/8140778307597-Auto-Chord). A song that isn't on YouTube can't be found or detected. Positive Grid gives copyright restrictions on music streaming as the reason.
- Before that, Spotify was most likely only a list of songs, with YouTube supplying the audio. That is inference: the old pipeline isn't documented. If so, it stepped around Spotify's analysis ban rather than complying with it.
- Positive Grid's own marketing is out of date. Its [app page](https://www.positivegrid.com/pages/spark-app) still advertises Spotify playlist import, which probably explains the impression.
- The open question moves to YouTube: how Positive Grid obtains the audio it analyses is not public. So Spark gives Jukebox no legal cover. We have the same unanswered question, and ours has a known answer that conflicts with YouTube's rules (§3).

**Backing track mode: a good idea, and Bandmaker can do it better.** Smart Jam listens to you play up to 8 bars through the phone mic, then offers 6 drum and bass tracks. Its weakest step is hearing your chords. Bandmaker already knows the chords, key and tempo, so it can skip that step.

**Mini DAW: it isn't there.** We found no multitrack, timeline editor or audio export in Spark. The nearest things are a 60-second amp looper and Smart Jam's chord timeline. GarageBand and iReal Pro are the better models.

**Top three for Bandmaker:**

1. A Drums member built from authored patterns with automatic fills and two simple controls, modelled on GarageBand's Drummer.
2. A "Play with the band" backing loop in the Song step, with count-in, per-member mixer and chord cues.
3. Sections on a simple timeline, saved on the device.

Details are in §6.

## 1. Auto chord detection

### What it does now

**VERIFIED.** The [Auto Chord help page](https://help.positivegrid.com/hc/en-us/articles/8140778307597-Auto-Chord) gives these steps:

1. Open the Music section of the Spark app.
2. Tap a song, or pick from saved songs or imported Apple Music playlists.
3. Chords display in real time as the song plays.

Search, looping, capo and 0.5/0.8/1.0x speed are in the [Spark NEO manual](https://assets.positivegrid.com/support/files/spark_neo_user_manual_v1_0_0.pdf).

**VERIFIED.** Other facts from Positive Grid:

- You can't use it on your own imported songs. The [app FAQ](https://help.positivegrid.com/hc/en-us/articles/47558817215245-Spark-App-FAQ) (updated 23 September 2026) cites copyright and sends users to the built-in YouTube search. It also says YouTube videos can be watched in the app.
- Apple Music is the only playlist import, and playlists [must be public](https://help.positivegrid.com/hc/en-us/articles/8140992954765-Import-Apple-Music-Playlist).
- It can't transpose a song.
- Bluetooth play-along from any device is [a separate speaker feature](https://www.positivegrid.com/products/spark-2). It is not chord detection.
- The [general app guide](https://help.positivegrid.com/hc/en-us/articles/47525938911117-Spark-App-User-Guide) lists Auto Chord across the Spark amps. The app [works only with an amp](https://help.positivegrid.com/hc/en-us/articles/47558817215245-Spark-App-FAQ).

**INFERENCE.** Apple Music entries act as pointers resolved to YouTube, because anything missing from YouTube fails. Audio plays inside the Spark app, not in Spotify or Apple Music. Playing Spotify through the amp over Bluetooth, which works but shows no chords, may be part of why the two features blur together.

### The Spotify history

| Date | Event | Status |
|---|---|---|
| Nov 2019 | Launch coverage [names Spotify, YouTube and Apple Music](https://www.premierguitar.com/positive-grid-unveils-the-spark). "Works with Spotify" was Positive Grid's own message. | VERIFIED |
| Mar 2020 | iOS release note fixes a Spotify **playlist** display state. | VERIFIED |
| 21 Mar 2024 | The help article on the removal is created, per its public metadata. Its original wording is unknown. | VERIFIED date |
| 11 Nov 2024 | iOS v4.1.0 notes say Spotify integration has been removed. | VERIFIED |
| 19 Nov 2024 | The help article is last edited. It blames changes on Spotify's side, says the two worked closely for months, and says saved songs survive. It names v4.1.1. | VERIFIED |
| 27 Nov 2024 | Spotify [closes audio features, analysis and other endpoints to new apps](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api). Existing extended-access apps are unaffected. | VERIFIED |
| 9 Jan 2025 | v4.1.1 ships. Its [App Store entry](https://apps.apple.com/us/app/spark-chords-backing-tracks/id1457653921) also says Spotify was removed. | VERIFIED |

The sources disagree on 4.1.0 or 4.1.1. Either way, the removal note was in the help centre before 27 November 2024. **So the November 2024 API change can't have been the trigger on these dates.** Which Spotify change was is **UNKNOWN**.

**INFERENCE: Spotify probably never supplied audio.** Four things point that way:

- The feature is documented as playlist import.
- Saved songs survived the removal.
- A [2021 New Atlas review](https://newatlas.com/music/positive-grid-spark-amp-review/) describes the app playing a video for a song it knows, and taking minutes to analyse one it doesn't.
- A forum user report (excerpt) describes imported songs showing chords with a video-unavailable error.

The analogue also fits: [Chord ai](https://chordai.net/?p=1218) resolves a shared Spotify song to a matching YouTube video.

### What can't be settled

- **Where analysis runs, UNKNOWN.** A server with shared results is likely (**INFERENCE**): the FAQ groups Auto Chord with network failures, reviews (excerpts) describe a database then analysis, and the App Store text claims coverage of millions of songs.
- **How audio reaches the analyser, UNKNOWN.** This is the crux.
- **Whether chords are stored or shared, UNKNOWN.**
- **Licensed chord partner: none named.** No page we read names one. This is not proof of absence.
- **Patent.** [US11398212B2](https://patents.google.com/patent/US11398212B2/en), assigned to Positive Grid, covers accompaniment and mentions a website, media service or local storage as a resource, plus pre-built chord information. A patent doesn't prove what a product does.
- **Privacy policy.** The [June 2026 policy](https://www.positivegrid.com/pages/privacy-policy) names none of Spotify, Apple Music or YouTube. Positive Grid's own terms of use were not found.

## 2. Spotify's terms

Documents: [Developer Terms](https://developer.spotify.com/terms) and [Developer Policy](https://developer.spotify.com/policy), both effective 15 May 2025; [user Terms](https://www.spotify.com/us/legal/end-user-agreement/), updated 4 September 2026; [User Guidelines](https://www.spotify.com/us/legal/user-guidelines/), undated.

| Topic | Clause | Gist |
|---|---|---|
| Analysis | Policy III.13 | "Do not analyze the Spotify Content or the Spotify Service for any purpose". Its examples are metrics and user profiling, but the list is expressly not limiting. |
| ML and AI | Policy III.14; Terms IV.2.a | No training models on, or ingesting into them, Spotify content. The User Guidelines have similar wording. |
| Synchronisation | Policy III.6 | No syncing sound recordings with visual media such as film, slideshows or video. |
| Mixing | Policy III.7 | No overlapping Spotify content with other audio. A backing band on top would hit this. |
| Data transfer | Policy III.9 | No moving data to another service, except a user's own data or playlist metadata. |
| Ripping | Terms IV.2.c, VI.5 | No stream-ripping or capture. |
| Commercial use | Policy IV.2–3; Terms III.1, V.5 | Streaming apps can't be sold or carry in-app payments. Narrow exceptions apply to non-streaming apps. |
| Web Playback SDK | [SDK docs](https://developer.spotify.com/documentation/web-playback-sdk) | Premium required. Commercial projects need prior written approval. |

We read the Policy clauses III.6, 7, 9, 13, 14 and IV.2–3 directly. The other clause numbers came through a page summariser, so check them before relying on them.

**Developer access has also narrowed (VERIFIED):**

- [Extended access tightened on 15 May 2025](https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access). The [quota page](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) requires an organisation, a launched service and 250k monthly users (excerpt for the figure).
- [Development Mode since February 2026](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security) is for non-commercial personal projects, with Premium and five users.
- Whether the postponed endpoint changes have since landed is **UNKNOWN**.

### Does the Spark feature conflict?

- **Today: no evident Spotify use, so no evident conflict (INFERENCE).** No API link means the Developer Terms shouldn't bind Positive Grid now.
- **Partnership or licence: UNKNOWN.** None is public. "Worked closely with Spotify" doesn't show a contract.
- **Past integration: can't be settled.** If only playlist metadata was used and the audio was YouTube's, III.6 and III.13 aren't obviously engaged. III.9's playlist-metadata exception may have helped. Whether matching Spotify tracks to YouTube fitted the rest of the Policy is not something public evidence can answer.
- **A plain app running beside Spotify (INFERENCE).** The user Terms bind the user. An app maker that never touches the Spotify Platform has no Developer Terms contract.

We found no public Spotify action against a chord-analysis app, but that search was shallow. [Spotify and labels v Anna's Archive](https://www.musicbusinessworldwide.com/spotify-and-record-labels-win-322m-default-judgment-against-pirate-site-annas-archive/) (trade press) concerned mass scraping, not analysis apps.

## 3. What this means for music-os

Spark and Jukebox are closer than they look. Both show chords alongside YouTube. Spark does it live for almost any song; Jukebox uses prepared charts for a curated 100. Copying Spark would not change our rights position.

**The existing problem stands.** Our charts are computed from yt-dlp copies, which conflicts with [YouTube Developer Policy III.E.1](https://developers.google.com/youtube/terms/developer-policies) unless YouTube approves in writing. The [27 October note](YOUTUBE_CHORDIFY_TOS_RESEARCH.md) sets out the options. Spark doesn't help: its method is undisclosed and could rest on a private arrangement.

| Route | Works on iPhone web? | Terms position | Verdict |
|---|---|---|---|
| **YouTube embed + prepared charts** (today) | Yes | Playback fits YouTube's player rules. Chart sourcing conflicts as above. | Keep for founder testing. Fix the chart source before public use. |
| **Spotify** | Web Playback SDK and the [iFrame API](https://developer.spotify.com/documentation/embeds/references/iframe-api) expose playback position, so synced cues are technically possible. | Analysis barred, sync doubtful, commercial use needs written approval, and five users or 250k monthly users. | Don't build without written permission. |
| **Apple Music (MusicKit)** | Subscriber playback is possible. No documented audio access was found. | [Developer Agreement 3.3.6(D)](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/) bars modifying content, monetising access, and synchronising unless documentation permits. [Guideline 4.5.2](https://developer.apple.com/app-store/review/guidelines/) warns sync rights may be needed. | Unsuitable for synced cues. |
| **Local files** | `<input type=file>` and [`decodeAudioData`](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData) should work (**INFERENCE**). Long-file decoding and in-browser chord models on iPhone are unmeasured. | No streaming contract applies. Audio must never be uploaded or shared. Song rights and chart copyright remain. | The cleanest route, for the few users with non-DRM files. Native can read only [non-DRM library items](https://developer.apple.com/tutorials/data/documentation/mediaplayer/mpmediaitem/hasprotectedasset.json). |
| **Microphone** | [`getUserMedia`](https://caniuse.com/stream) works. Best with music on another device. | Touches no service API. [Chord ai](https://chordai.net/?p=1218) does this. Inducement and "ingesting into a model" questions remain for a lawyer. | Possible later. Less accurate, and live timing only. |

**iPhone constraints.**

- A web page can't tap the audio in a YouTube iframe. YouTube's rules also bar separating it. The cross-origin silence behaviour is **recollection**, since the spec section wasn't reached.
- Native iOS has ReplayKit broadcast extensions, which [receive sample buffers after user consent](https://support.apple.com/en-sg/guide/security/seca5fc039dd/web). Whether Apple Music or Spotify audio reaches them is **UNKNOWN**, and Spotify's terms would bar it anyway.
- [caniuse lists `getDisplayMedia` on iOS Safari from 27.0](https://caniuse.com/mdn-api_mediadevices_getdisplaymedia). We could not confirm this from Apple or WebKit, and whether it carries another app's audio is **UNKNOWN**. Treat other-app capture as unavailable until a device test shows otherwise.
- Chart copyright is a separate issue on every route. [Ultimate Guitar says most of its tabs are licensed](https://help.ultimate-guitar.com/en/articles/6735517-website-licensing-on-ultimate-guitar-why-are-some-songs-blocked). Whether machine-derived timings need a publisher licence is **UNKNOWN**.

**For a lawyer, before anyone outside the founder uses it:**

1. Can YouTube-derived charts be cured, or is written YouTube approval needed?
2. Do scrolling chord cues count as "visual media" under Spotify III.6, or as synchronising under MusicKit?
3. Does a microphone mode create inducement or AI-wording risk?
4. Do chord charts and timings need a publisher licence in Norway and the EEA?
5. Is it worth asking Spotify or Apple for written permission?

## 4. Auto backing tracks: Smart Jam and Quick Jam

Sources: [Smart Jam help](https://help.positivegrid.com/hc/en-us/articles/8141249132941-Smart-Jam-Supported-Models-Only) and [Quick Jam help](https://help.positivegrid.com/hc/en-us/articles/47786754338701-Quick-Jam). **VERIFIED** unless tagged.

- **Models.** Spark 2, EDGE, LIVE, 40, MINI and GO. It needs an amp speaker because the phone mic listens to it. [NEO headphones can't use it](https://help.positivegrid.com/hc/en-us/articles/40848150035469-Why-doesn-t-the-Smart-Jam-or-Video-Recording-feature-in-the-Spark-app-work-with-Spark-NEO).
- **Flow.** Swipe to pick a drummer, tap a tempo, get 4 clicks, then play up to 8 bars (or stop at 4) with the phone about 0.5 m from the amp. A red bar warns of mic clipping. It handles 1 chord every 2 beats.
- **Output.** Drums and bass only. You swipe through 6 generated tracks. Redo records a new progression.
- **Four drummers.**
  - Dave (rock) builds Verse, Chorus, Bridge, Chorus from your progression.
  - Sharon (funk) follows your progression and strumming.
  - Charles (blues) offers straight or shuffle, 8 or 12 bars.
  - Jarvis (rock) responds live to your dynamics, after a level calibration.
- **Control afterwards.** Edit chords on a timeline, per section or with Apply to All Parts. Change BPM, turn bass on or off, transpose. No intensity, fill or per-drum control is documented.
- **Saving.** Login and saved slots. No audio or MIDI export is documented. The only capture is video recording, whose audio is [the phone mic hearing the amp](https://help.positivegrid.com/hc/en-us/articles/47558817215245-Spark-App-FAQ).
- **Quick Jam.** The same engine with no listening: preset progressions in Pop, Rock, Funk and Blues.
- **Cost.** The app is free for owners. No subscription tier was found on the [App Store listing](https://apps.apple.com/us/app/id1457653921). [Spark AI](https://help.positivegrid.com/hc/en-us/articles/29669237496845-Spark-AI) makes tone presets from text, not backing tracks.

**Is it AI?** Positive Grid calls Smart Jam an AI drummer and publishes no method. Android needs a one-time sound library download. **INFERENCE:** chord analysis plus pattern selection, played from local samples, not generated audio. Whether it works offline is **UNKNOWN**.

**What people say (OPINION, mostly old, no 2025–26 hands-on review found):**

- [LeftyGuitarist](https://leftyguitarist.com/positive-grid-spark-review/) found it worked quite well but mishears chords, and advises simple ones.
- [App reviews](https://justuseapp.com/en/app/1457653921/spark-amp-smart-jam-chords/reviews) split between good enough and unusable once you play anything complex.
- [A forum thread](https://forum.positivegrid.com/topic/4857/smart-jam-not-working-well) (excerpt) reports wrong bass notes, stray chords, 8 bars being too short, and trouble with complex chords.
- We found no credible evidence either way on repetitive drums or Bluetooth drift.

The theme is that the band is fine when it hears you correctly, and hearing you is where it fails.

## 5. The "mini DAW"

**We found no DAW in Spark.** The [App Store listing](https://apps.apple.com/us/app/id1457653921), [iOS release notes](https://help.positivegrid.com/hc/en-us/articles/8139979538829-Spark-App-Update-History-Release-Notes-iOS-iPadOS) and [Spark 2 guide](https://help.positivegrid.com/hc/en-us/articles/47901090662413-Spark-App-User-Guide-for-Spark-2) list no multitrack, timeline editor or audio export. This is absence of evidence: we did not use the app. **INFERENCE:** the founder saw the looper, Smart Jam's chord timeline or a mixer screen. Founder, if you remember where you saw it, that would confirm this.

**Looper ([help](https://help.positivegrid.com/hc/en-us/articles/47557771640461-Using-the-Looper-in-the-Spark-App-Supported-Models-Only), VERIFIED).** Spark 2 and EDGE; the [PEDAL guide](https://help.positivegrid.com/hc/en-us/articles/47499454651789-Spark-App-User-Guide-for-Spark-PEDAL) also lists it, though the FAQ says otherwise.

- One loop of up to 60 seconds, stored on the amp.
- Unlimited overdubs in one stack, not separate tracks. Undo covers the last layer only.
- Groove Looper adds a drum pattern, a 4-beat lead-in fill and an optional ending fill. [Tone can change per layer](https://www.positivegrid.com/blogs/positive-grid/the-spark-2-creative-groove-looper).
- Mix is loop and click volume only.
- On the phone it is one screen: a drum circle above a record/dub circle, with settings, undo and a mixer icon. No timeline is described. We did not see the screens.

**Real recording** happens over USB into [a computer DAW](https://help.positivegrid.com/hc/en-us/articles/28160784780685-Recording-with-Spark-2-USB-I-O) (**INFERENCE** for multitrack).

### Comparison

| | Spark | [GarageBand iOS](https://apps.apple.com/us/app/garageband/id408709785) | [iReal Pro](https://apps.apple.com/us/app/ireal-pro/id298206806) | [BandLab](https://help.bandlab.com/hc/en-us/articles/24226593087001-Generate-Ideas-with-SongStarter-AI) |
|---|---|---|---|---|
| Input | Chords played into the mic | Your parts; settings for the drummer | Typed or shared chord chart | Genre, mood, tempo, key |
| Band | Drums, bass | [Drummer](https://support.apple.com/guide/garageband-iphone/use-drummer-chs9692b2133/ios), Smart Instruments, loops | Piano, guitar, bass, drums and others; 50 styles | Generated idea, 3 variations |
| Control | Chords, BPM, bass toggle, transpose | XY pad (loud/soft, simple/complex), kit piece mutes, Fills slider, Swing, Follow | Tempo, transpose, looped sections, [mixer](https://www.irealpro.com/learn/customize-your-backing-tracks) | Regenerate, then edit in Studio |
| Tracks | None | Up to 32 | Fixed band | [16, or 32 with membership](https://help.bandlab.com/hc/en-us/articles/115002945433-Track-and-Project-Duration-Limits) (excerpt) |
| Export | None documented | [Song audio or project](https://support.apple.com/guide/garageband-iphone/share-songs-chs39284d66/ios) (excerpt) | Audio, MIDI, PDF, MusicXML | [M4A, WAV, MIDI per track](https://help.bandlab.com/hc/en-us/articles/115002959774-Downloading-Mixdowns-and-Tracks) (excerpt) |
| Phone layout | One screen per feature | Track view, region editing | Chart screen, thin transport, mixer sheet | Full mobile studio |
| Price | Free with amp | Free | $21.99, packs $6.99 | Free tier |

**INFERENCE.** iReal Pro is the closest match to Bandmaker's Song step: chart in, band out, and a small mixer. GarageBand's Drummer is the best control model, because it replaces a step grid with a few musical macros.

## 6. Recommendations for Bandmaker

These are ordered by value against effort, for today's no-build app. Effort is relative and unmeasured. They are proposals for founder review, and #64's no-code-before-workflow rule still applies.

They fit the settled direction: parts stay editable, this is not text-to-audio, and Band mode is [not a backing track over YouTube recordings](https://github.com/dcromp/music-os/issues/64).

### Adopt

| # | Idea | Taken from | Effort | Native needed? |
|---|---|---|---|---|
| 1 | **Drums member**: authored patterns, automatic fills, loud/soft and simple/complex controls, a Fills slider | GarageBand Drummer, Groove Looper's fills | Medium | No |
| 2 | **"Play with the band"**: looped Rhythm + Bass + Drums, count-in, chord cues, mixer sheet | iReal Pro, Smart Jam | Small after 1 (and possible first without drums) | No |
| 3 | **Sections and timeline, saved on device** | Dave's song form, Apply to All Parts, #68 | Medium | No, with storage caveats |
| 4 | **"Try another"**: a few variations to swipe through | Smart Jam's 6 tracks, BandLab's 3 | Small | No |
| 5 | **Export a mix** (WAV and project backup) | iReal Pro, GarageBand | Small to medium | No |
| 6 | **Play your own chords in**: a recorded take analysed for chords | Smart Jam's input | Large | Probably not; unmeasured |
| 7 | **Record your guitar over the band** | The looper, then #73 | Large, gated | Maybe (below) |

**1. Drums member.** Author a small original pattern library per feel, then generate the part by rule: pick a pattern for the section, thin or add hits from the complexity control, and insert a fill at the last bar of a section. This meets "mostly AI with auto fills" as far as the player can tell, stays fully editable, and needs no model runtime. [#65](https://github.com/dcromp/music-os/issues/65) found editable chord-following band parts only in closed desktop products, and Magenta's `@magenta/music` package was [last released in 2021](https://www.npmjs.com/package/@magenta/music). Real AI can replace the rule layer later, behind the same controls.

Sounds need a new source. The pinned FluidR3 bank has 128 melodic instruments and no full drum kit, only single sounds such as `synth_drum` and `melodic_tom` (checked against its file list). The [SFZ drum index](https://sfzinstruments.github.io/drums) lists CC0 kits such as Big Rusty Drums, but each kit's own licence needs confirming. The [Groove MIDI Dataset](https://magenta.withgoogle.com/datasets/groove) is CC BY 4.0 and could inform patterns with attribution.

**2. "Play with the band".** This is the backing track mode, and the most direct answer to what the founder saw. Use the [lookahead scheduling pattern](https://web.dev/articles/audio-scheduling), which suits [Web Audio on iPhone](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay) after a tap to start. Set `navigator.audioSession` to [avoid silent-switch muting](https://bugs.webkit.org/show_bug.cgi?id=251532). Because Bandmaker plays chords it already has, the player gets no mishearing, no mic setup and no amp.

**3. Sections and timeline.** A phone-sized timeline can be simple: a row of section blocks (Verse, Chorus), each showing bars and chords, with lit lanes per member as in prototype layout D. Tapping a block edits it. A "Make it a song" action can expand a 4-bar idea into Verse, Chorus, Bridge, Chorus, as Dave does. Copy Apply to All Parts for chord edits. No clip editing is needed at this stage. #86 deliberately left sections out, so they need their own design.

Storage needs care. Safari can [delete IndexedDB after 7 days without use](https://webkit.org/tracking-prevention/), though Home Screen apps are exempt. Call [`navigator.storage.persist()`](https://webkit.org/blog/14403/updates-to-storage-policy/) and offer a project backup file.

**How it fits the flow:**

- **Feel** sets starting tempo, swing and a default drum style. It works as Quick Jam does, but with the player's own choices.
- **Key** is unchanged.
- **Chords** gains "Hear it with the band", so the first reward arrives early.
- **Song** becomes the timeline, with Play with the band as its transport.
- **Drums** unlocks once there are chords, as Bass does in #86, and appears in the selector where it is currently marked not available.

One shared project model would serve all of this: sections holding bars, chords and each member's settings. That is also the first step towards #64's open question on an editable arrangement.

**7. Recording stays gated.** [WebKit bug 311451](https://bugs.webkit.org/show_bug.cgi?id=311451) reports degraded audio on iOS while the mic is open. The [web DAW note](https://github.com/dcromp/music-os/blob/research/bandmode-iphone-web-daw/docs/BANDMODE_IPHONE_WEB_DAW_RESEARCH.md) proposes five on-device tests. Run those first. Items 1 to 5 don't depend on them.

### Don't adopt

- **Live chord detection for any song, or streaming-service integration.** Spark's own history shows the dependency risk: an integration that lasted about five years ended on the other party's terms.
- **Mic-first input as the main route.** It is the step users complain about, and it solves a problem Bandmaker doesn't have.
- **A Jarvis-style live-following band.** [#66](https://github.com/dcromp/music-os/issues/66) found live following research-grade.
- **An ML drum model now.** It adds dependency and unknown iPhone performance. The checkpoint licences are also **UNKNOWN**.
- **Text-to-audio backing.** The founder has ruled it out.

### What would need a native app

**INFERENCE, supported by the web DAW note:**

- reliable background audio
- low-latency monitoring through effects
- multichannel interface input and channel choice
- MIDI (Web MIDI [isn't in Safari](https://webkit.org/b/107250)) and Audio Units
- guaranteed storage
- media library access to owned tracks
- ReplayKit capture

None of the top five items needs it.

## Limits of this research

- We did not use the Spark app or an amp. Layout descriptions come from help text, not screens.
- Directly re-checked by the lead researcher: Auto Chord and Smart Jam help pages, the Spotify removal article and its metadata, iOS release notes, the App Store listing, and Spotify Policy III and IV. The rest came from two research agents working from primary sources and has not been independently re-read.
- Spark's Android release notes were not read. They may explain the v4.1.0 and v4.1.1 mismatch.
- Unread or failed: Positive Grid's terms of use; `forum.positivegrid.com` (503; excerpts only); Chordify's pages (blocked by a bot check, and we stopped there); the Spark 2 manual PDF; the Web Audio spec's cross-origin section. Chordify facts come from the 27 October note.
- One agent's request to the help centre with a browser user agent, after a 403, was blocked and not retried. Those pages were read in the built-in browser instead.
- Prices and sale figures change, so check them before reuse.
