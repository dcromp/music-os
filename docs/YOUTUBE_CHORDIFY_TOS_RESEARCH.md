# Chordify, YouTube's terms and Strum Along

**Researched 27 October 2026.** This note is product research from public first-party sources. It is not legal advice and does not replace a review by a lawyer or YouTube's own policy team. Claims we could not confirm are marked **UNCONFIRMED**. Each citation gives the date the page shows, or "accessed 2026-10-27" when it shows none. No media was downloaded for this research.

This note builds on, and does not replace, the [song-access comparison](SONG_ACCESS_FEASIBILITY.md) (12 October). It also follows two earlier pilot research notes: [source research](https://github.com/dcromp/music-os/blob/382082a7c7bb733492f2748d250ce3ef1b38f403/docs/YOUTUBE_PILOT_SOURCE_RESEARCH.md) and [playback research](https://github.com/dcromp/music-os/blob/095c7509f83f8eda943a5bf2e10494e83f9ee439/docs/YOUTUBE_PILOT_PLAYBACK_RESEARCH.md), both from 19 October. The code facts below come from `claude/jukebox-shelves` at `add01c3`. Its `strumalong/` tree is identical to `883d0eb`, the build deployed on 27 October.

## Executive summary

- **Chordify plays YouTube through the official embedded player.** Its terms say so, and its song pages load the YouTube IFrame API into a roughly 300×200 px player slot. Nothing we found says Chordify has a special YouTube partnership.
- **Chordify has not said how its servers get the audio they analyse.** The ad-free claim also turns out to be narrow:
  - Its Premium tier promises "No commercial advertising". YouTube's policy forbids blocking YouTube's own ads, so that most likely means Chordify's own ad slots only. This is our inference.
  - Why some users see no YouTube ads is not explained by any primary source (UNCONFIRMED).
  - Chordify does license lyrics, through LyricFind.
  - A 2024 profile says the founders work with music publishers, but no deal or partner is named.
- **Strum Along's playback already matches YouTube's player rules.** It uses the official, visible IFrame player at least 200×200 px. Nothing covers the player, the app never touches ads, and playback pauses when the app is in the background. It uses only the documented speed and seek functions and sends a Referer header.
- **The clear conflict is how the charts are made.** Every chart is "computed from this upload's audio", using a copy downloaded with yt-dlp and cached locally. Several rules forbid this without prior written permission:
  - [Developer Policies III.E.1](https://developers.google.com/youtube/terms/developer-policies) bans downloading or caching YouTube content.
  - The [YouTube Terms](https://www.youtube.com/t/terms?hl=en&gl=US) forbid downloading and automated access.
  - [App Store guideline 5.2.3](https://developer.apple.com/app-store/review/guidelines/) would also apply to a native app.

  The repo already treats this as research-only, not commercial clearance.
- **Recommendation:** keep the embed exactly as it is, and change where the chord timings come from. Options:
  - ask YouTube for written approval;
  - analyse licensed or artist-authorised audio;
  - analyse the user's own audio on their device;
  - use authored or licensed chord-timing data aligned to the embed.

  Before anyone outside the founder uses the app, add the required YouTube Terms link and a privacy policy. Charge for practice features, never for watching. Apple Music (MusicKit) and Spotify are not workable substitutes for analysis or synced cues.

## 1. How Chordify uses YouTube

### Playback: the official embedded player

- **Terms:** Chordify's terms, clause 2.8, say embedded videos play through YouTube API Services and are subject to YouTube's Terms of Service. Clause 1.1 covers the website, the apps, "Chordify Embed" and a Chordify API. [Chordify terms](https://chordify.net/pages/terms-and-conditions/) (no date shown; accessed 2026-10-27)
- **Live song page:** we inspected the page structure of a live song page without accepting cookies (accessed 2026-10-27). It showed:
  - a `div#youtube` player slot of about 296×200 px;
  - YouTube's IFrame API loaded (`window.YT` present);
  - songs keyed as `youtube:<videoId>`.

  No player iframe appeared before cookie consent, so we did not see the iframe itself. This is consistent with the official IFrame Player API. [Example song page](https://chordify.net/chords/coldplay-songs/yellow-3-chords)
- **Original 2012 design:** the founders' 2012 paper describes the YouTube video playing next to the chord grid. [de Haas, Magalhães, ten Heggeler, Bekenkamp & Ruizendaal, *Chordify: Chord transcription for the masses*, ISMIR 2012](https://dreixel.net/research/pdf/cctfm.pdf)
- **Mobile apps:** no primary source says what the iOS and Android apps use. A web view showing the embed would be what YouTube recommends (see §2.4), but this is **UNCONFIRMED**.
- **Privacy statement:** it tells users that embedded YouTube videos share data with YouTube and links to Google's privacy policy. It lists YouTube cookies as "functional" and DoubleClick/`_gads` cookies as advertising. We did not find two things YouTube requires: an explicit statement that the service "uses YouTube API Services" (Developer Policy III.A.2.b) and a link to Google's security settings (III.A.2.h). The second may not apply to a service that only embeds videos (**UNCONFIRMED**). [Chordify privacy statement](https://chordify.net/pages/privacy-policy/) (privacy statement amended 15 September 2022; cookie statement updated 18 September 2024)

### Ads: why viewers may see none

- **Free tier:** Chordify's free tier shows ads. [Is Chordify free?](https://support.chordify.net/hc/en-us/articles/360001945038-Is-Chordify-free) (updated about 2019)
- **Premium:** Premium and Premium Plus list "No commercial advertising", plus tempo and key changes. [Chordify Premium](https://chordify.net/premium) (accessed 2026-10-27)
- **Why "no commercial advertising" probably means Chordify's own ads:** Chordify runs its own ad slots (the DoubleClick cookies above). [Developer Policy III.I.5](https://developers.google.com/youtube/terms/developer-policies) forbids API clients from blocking or replacing YouTube's ads. So the Premium promise most plausibly covers Chordify's ads only. That is our inference; Chordify does not say.
- **Why a viewer might see no YouTube ad:** no primary source explains it (**UNCONFIRMED**). Plausible causes include:
  - an unmonetised video;
  - YouTube's own choices about ads in embeds;
  - the viewer's YouTube Premium status;
  - an ad blocker.
- **YouTube Premium in third-party embeds:** YouTube's Premium page promises ad-free viewing "across devices and platforms with access to YouTube" but does not mention third-party embeds. Whether Premium removes ads in embeds is **UNCONFIRMED**. [YouTube Premium benefits](https://support.google.com/youtube/answer/6308116) (accessed 2026-10-27)

### Analysis audio and licensing

- **Unavailable videos:** if a YouTube video is unavailable, Chordify says there is no audio for it. The user can still play along with the chords without music, upload their own copy, or pick another upload. Two things follow:
  - Playback audio is not served from a Chordify-held copy.
  - The chords were computed earlier from *some* copy of the audio. How that copy was obtained is not disclosed.

  [My YouTube video won't play](https://support.chordify.net/hc/en-us/articles/360016231697-My-YouTube-video-won-t-play) (updated about September 2026); [song page](https://chordify.net/chords/coldplay-songs/yellow-chords) (accessed 2026-10-27)
- **Chordify's own descriptions of the pipeline:** the 2015 abstract says chords are extracted "from musical sources like Youtube", using Sonic Annotator features and HarmTrace. Today's Premium page talks of deep neural networks plus human music researchers. Neither says how the YouTube audio reaches the analysis servers. **Whether Chordify downloads YouTube audio is UNCONFIRMED, so do not claim that it does.** [Magalhães, *Chordify: three years after the launch*, ISMIR 2015 LBD](https://ismir2015.ismir.net/LBD/LBD42.pdf)
- **How the founders framed legality in 2012:** a user's uploaded files are locked to that user's session and never shared. They argued this means the service cannot redistribute music except through YouTube and SoundCloud. Uploads are now a Premium feature, and Deezer cookies are still listed. We found no primary evidence of Spotify or Apple Music as sources. [ISMIR 2012 paper](https://dreixel.net/research/pdf/cctfm.pdf)
- **Licensing:**
  - **Lyrics, confirmed:** song pages credit LyricFind and publishers such as Universal Music Publishing Group. The terms limit lyrics to personal, non-commercial use.
  - **Music publishers:** a 2024 TechLeap profile says the founders work with music publishers to respect copyright, without naming any. [TechLeap](https://techleap.nl/blog/chordify-striking-the-right-note-in-music-education-and-ai-innovation) (25 September 2024; secondary profile)
  - **No other deal found:** we found no named agreement with a collecting society, a label, or YouTube itself.
  - **CEO interview:** a 2026 interview with CEO Bas de Haas exists, but we did not read it (**UNCONFIRMED**).
- **What this means for us:** Chordify shows that people pay for chord-along products built around the YouTube embed. It does not show a public route to analysis audio, and it is not a data source we may reuse. Its terms restrict automated collection (see the [song-access comparison](SONG_ACCESS_FEASIBILITY.md)).

## 2. The rules that apply

### 2.1 YouTube Terms of Service

[Terms of Service](https://www.youtube.com/t/terms?hl=en&gl=US) (effective 15 December 2023; the Norwegian-locale copy served to us was older, so we used the en/US version). The relevant restrictions:

| Rule | What it says |
|---|---|
| No downloading or modifying | No accessing, reproducing, downloading, distributing or modifying the Service or Content, except where the Service or YouTube and the rights holders expressly permit it in writing |
| No circumvention | No circumventing or interfering with the Service, including copy-prevention features |
| No automated access | No automated access, including scrapers, except search engines or with prior written permission |
| Personal use | Content is for personal, non-commercial use only |
| Ads around Content | Limits on selling ads or sponsorships on or around Content |
| Embedding allowed | Showing videos through the embeddable player is expressly permitted |

### 2.2 YouTube API Services Terms and Developer Policies

The [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) (updated 2026-09-14) require:
- a published privacy policy that the app follows (§7);
- Google's EU User Consent Policy for EU users (§9.2), relevant to Norway and the rest of the EEA (our inference);
- no implied endorsement by YouTube (§13);
- acceptance that YouTube may audit API clients (§6).

The [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) (updated 2026-10-15; numbering checked directly) are the operative rules:

| Topic | Section | Rule |
|---|---|---|
| Downloading or caching | III.E.1 | No downloading, importing, backing up, caching or storing copies of audiovisual content, and no offline playback, without prior written approval |
| Separating audio from video | III.I.7–8 | Don't separate, isolate or modify the audio or video components, or promote them separately |
| Ads | III.I.5 | Don't modify, interfere with, replace or block YouTube's ads |
| Player | III.I.4, III.I.6 | Don't obscure or disable player functions or links; don't modify, build on or block the player |
| Background play | III.I.9 | No playing content, including audio, from a player that isn't shown on the user's current page or screen |
| Charging and gating | III.F.3.a–c | Don't charge to watch embedded content, gate playback behind actions (login is allowed), or reward views or likes |
| Ads beside YouTube content | III.G.1.c–d, III.G.2.c | Selling ads on or in the player needs written approval; ads on pages showing YouTube data need enough independent content; ad-supported apps are otherwise allowed |
| User-facing terms | III.A.1–2 | Link the YouTube Terms; prominent privacy policy saying the app uses YouTube API Services and linking Google's privacy policy |
| Mobile apps | III.B.1 | Non-website clients must be remotely updatable |
| Labelling our own data | III.E.4.h, III.F.2 | Label metrics that don't come from YouTube; our content must not look like YouTube's |
| Stored API data | III.E.4 | Most data fetched through the API must be refreshed or deleted within 30 days |

The [Developer Policies Guide](https://developers.google.com/youtube/terms/developer-policies-guide) (updated 2026-09-14) gives these as prohibited examples:
- background play;
- audio extraction or MP3 download;
- offline download outside YouTube Premium;
- blocking or replacing ads;
- charging for what is free on YouTube.

The guide does not name playback-speed controls. That speed control is fine as long as it uses the documented API is our reading (**UNCONFIRMED**).

### 2.3 Required Minimum Functionality and the IFrame player

- **[Required Minimum Functionality](https://developers.google.com/youtube/terms/required-minimum-functionality) (updated 2026-10-15):**
  - player viewport at least 200×200 px, with its controls inside;
  - nothing covering any part of the player or its controls;
  - no actions triggered by hovering over or touching the player;
  - autoplay or scripted playback only when more than half the player is visible, and only one such player per screen;
  - apps must send a valid Referer and should use the operating system's web view;
  - no changes to the player beyond what the documentation allows.
- **[IFrame Player API](https://developers.google.com/youtube/iframe_api_reference) and [player parameters](https://developers.google.com/youtube/player_parameters) (both updated 2026-10-15):**
  - `setPlaybackRate` is only a request: confirm the result with `onPlaybackRateChange`, and offer only the speeds `getAvailablePlaybackRates` returns;
  - `seekTo` is documented;
  - `onAutoplayBlocked` reports playback the browser blocked;
  - `playsinline=1` keeps playback inline on iOS, where the default is full screen.
- **[Embed help](https://support.google.com/youtube/answer/171780) (accessed 2026-10-27):**
  - apps should show the embedded player in a web view;
  - a missing Referer gives error 153;
  - creators can disable embedding;
  - privacy-enhanced (no-cookie) embeds show non-personalised ads.

### 2.4 App Store, Apple Music (MusicKit) and Spotify

- **[App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) (updated 16 October 2026):**
  - **5.2.3:** no saving, converting or downloading media from YouTube, SoundCloud, Vimeo and similar sources without explicit authorisation. Streaming may also breach those services' terms, and Apple may ask for proof of authorisation.
  - **5.2.2:** using or displaying another service's content needs that service's terms to permit it.
  - **5.2.1:** no protected third-party material without permission.
  - **4.2 / 4.2.2:** an app must be more than a repackaged website or a collection of links.
  - **2.5.4:** background audio only for its intended purpose.
- **[Apple Developer Program License Agreement §3.3.6(D)](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/) (MusicKit; accessed 2026-10-27):**
  - MusicKit may only give users access to their own Apple Music subscription;
  - no charging for, or indirectly monetising, that access;
  - playback must be user-started, with standard controls;
  - no downloading, uploading or modifying the content;
  - no synchronising with other content, unless Apple's documentation permits it;
  - playback only as rendered by MusicKit.

  Audio analysis is effectively excluded, and synced chord cues are doubtful (our inference). Whether MusicKit's player can change tempo is **UNCONFIRMED**.
- **[Spotify Developer Policy](https://developer.spotify.com/policy) and [Developer Terms](https://developer.spotify.com/terms) (both effective 15 May 2025):**
  - no synchronising recordings with visual media (Policy III.6);
  - no analysing Spotify content for any purpose (III.13);
  - no training ML or AI models on it (III.14);
  - no stream-ripping (Terms IV.2.c.iii).

  Spotify also [closed its Audio Features and Audio Analysis endpoints to new apps on 27 November 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api).

## 3. Mapping the rules onto Strum Along

What the app does today:
- **Hosting:** a static web app at https://dcromp.github.io/music-os/, public but unlisted, for the founder's personal testing in Norway. That scope was set on [issue #26](https://github.com/dcromp/music-os/issues/26) on 20 October; work is tracked in [#28](https://github.com/dcromp/music-os/issues/28) and [#53](https://github.com/dcromp/music-os/issues/53).
- **Catalogue:** 43 songs on Jukebox shelves.
- **Playback:** the official YouTube IFrame player (`strumalong/app.js`), with player parameters `playsinline:1, rel:0, controls:1, enablejsapi:1, fs:0` plus `origin`, and the page sends a Referer header (`strict-origin-when-cross-origin`).
- **Charts:** each song file says "Chart computed from this upload's audio". The audio was downloaded with the yt-dlp importer ([YOUTUBE_IMPORT.md](YOUTUBE_IMPORT.md)) and cached, gitignored, under `experiments/local-audio/youtube/`.
- **Catalogue checks:** run the YAMNet and Demucs 6-stem models locally on that audio (README, 27 October).
- **What is deployed:** the `gh-pages` branch holds no audio files, only chord, beat and metadata JSON.

### Clearly allowed (keep)

- **Official, visible embed:** the player fills the frame, which is well over 200×200 px on a 390 px-wide phone. The cue panel's "Cues hidden" and "Ad or different video, cues paused" covers sit over our own cue panel, not the player (RMF; III.I.4, III.I.6).
- **Ads left alone:** when an ad plays, the app only pauses its own cues and does nothing to the player (III.I.5).
- **No background play:** the app pauses on `visibilitychange` when hidden, and scrolls the player into view before starting playback (III.I.9; App Store 2.5.4).
- **Documented controls only:** playback speed (from `getAvailablePlaybackRates`, confirmed by the change event), seeking and cueing, all documented IFrame API calls. User-started play with `onAutoplayBlocked` handled, `playsinline`, `rel:0` and `fs:0` are documented parameters too. Whether a speed control needs prior agreement is unclear (see "grey areas").
- **Referer header:** sent as RMF requires; the app uses the `localhost` name, not an IP address, for local testing.
- **"Open on YouTube" links:** these deep links to the watch page are always allowed.
- **Our own data, clearly labelled:** chords, suggested strum patterns and the timing adjustment are our data, labelled as "provisional", "estimated" and "a practice suggestion, not the recorded part". No lyrics are shown (III.E.4.h, III.F.2).
- **No YouTube data is cached:** the deployed site holds no audio and stores no YouTube data fetched through the API.
- **No charging or gating:** the app is free with no login, so III.F.3 and III.G are not triggered today.

### Clearly not allowed without prior written approval

- **Downloading audio to compute charts:** using yt-dlp to download and keep a copy of each upload's audio (YouTube Terms; Developer Policy III.E.1; the guide's audio-extraction example). The importer's limits and its source-use note only record that this is a research experiment. They do not grant permission. Calling YouTube's servers with an automated tool outside the API is also restricted under the Terms.
- **Separating stems from that audio:** running Demucs on the downloaded copy. III.I.7 is written about the client's own features; this is a separate act on a copy we were not permitted to make, so its status follows from the download problem.
- **Shipping any of this in an iOS app:** a native app that downloaded, converted or analysed YouTube media would also break App Store 5.2.3, and Apple may ask for proof of authorisation under 5.2.2.
- **Future features that need the audio:** offline play, "remove the guitar", screen-off backing or audio-only modes would all break III.E.1, III.I.7–9 or III.I.9 with YouTube as the source.

### Grey or not yet settled

- **The charts themselves:** chord names and timings are facts *about* a recording. But each published chart was derived from a copy that was not permitted. Whether the charts can be kept, or must be rebuilt from a permitted source, is a question for a lawyer.
- **Whether the charts also need copyright permission:** a chord arrangement is a separate question that YouTube's terms do not cover. It may need a music-publisher licence to teach or display, which is why Chordify works with publishers and JustinGuitar pays song fees (see [plan.md](../plan.md) sources).
- **Playback-speed control:** it uses documented API calls, but the policy guide does not mention it. Confirm before marketing it as a feature (**UNCONFIRMED**).
- **Public but unlisted site:** anyone with the URL can reach it, so the absent Terms link (III.A.1) and privacy policy (III.A.2, API Services Terms §7) are already gaps. They become required before any wider pilot. The EU consent rule (§9.2, Norway/EEA) could also require a cookie-consent step before loading the embed, or the privacy-enhanced no-cookie domain (our inference; check before use).
- **How "embed status" is checked:** the catalogue checks record whether each video can be embedded. If that comes from YouTube Data API data, III.E.4's 30-day refresh applies. If it comes from yt-dlp, it falls under the automated-access concern. This note did not check which tool is used.
- **Future subscription:** a subscription is allowed if it buys *our* practice features. A paywall on watching is not (III.F.3.a). Ads around the player need enough independent content (III.G.1.d) and must never sit in or on the player (III.G.1.c).
- **Native iOS wrapper:** a WKWebView embed with inline playback and a valid Referer is the documented route. The app must also be more than a repackaged website (App Store 4.2) and be remotely updatable (III.B.1).

## 4. Compliant design options

| Option | What it gives | What still needs work |
|---|---|---|
| **A. Keep the official embed, with chords from a permitted source** (recommended baseline) | Familiar recordings with ads left alone; our chords, strumming and Jukebox beside the player | A permitted source for the timings (one of B–E). Cue timing must follow the embed's clock. Our existing sync nudge handles small offsets |
| **B. Ask YouTube for written approval** for analysis copies of specific uploads | Keeps today's pipeline | III.E.1 allows prior written approval, but no public application route or price exists. The rights holders' permission is also needed under the Terms |
| **C. Licensed or artist-authorised audio** for analysis (and possibly playback) | Exact masters, stems and offline play if the licence allows; no YouTube dependence | Fees and repertoire unknown; may not match the YouTube upload's timing, so check each recording's alignment |
| **D. The user's own audio, analysed on their device** (Chordify's upload model) | Full audio features for that user; nothing redistributed | The result can't feed a shared catalogue without separate rights. Analysis on the phone (BTC/CREMA) is unproven there |
| **E. Authored or licensed chord-timing data**, aligned by people or by tapping along to the embed's clock | No audio copy needed at all | Human effort or a data licence (e.g. a Hal Leonard enquiry); arrangement copyright still applies |
| **F. Deep-link out to YouTube** | Always permitted | Our cues can't follow playback there; only a static chord list |
| **G. Apple Music (MusicKit) or Spotify** | Licensed playback | Not usable for this product: analysis and sync are barred (MusicKit §3.3.6(D)(b)–(d); Spotify Policy III.6, III.13) |

## 5. Recommendations for Strum Along

1. **Keep the player as it is.** Visible, at least 200×200 px, nothing on it, ads left alone, paused in the background, documented calls only. Add a regression check that nothing ever overlays `.player-frame`.
2. **Treat the yt-dlp caches and every chart derived from them as research-only.** That is already the repo's position. Before any audience beyond the founder, choose a permitted chord-timing source from options B–E. Record that choice on [#19](https://github.com/dcromp/music-os/issues/19)/[#25](https://github.com/dcromp/music-os/issues/25) as a pre-use requirement.
3. **Before sharing the URL with anyone, add:**
   - a YouTube Terms link and a short privacy policy (III.A.1–2);
   - a decision on EU consent or the privacy-enhanced embed.
4. **Charge only for our features:** learning path, arrangements, progress. Never paywall playback, and never sell ads in or on the player.
5. **For a native iOS app,** embed in a WKWebView with inline playback and a Referer header. Ship no download, stem or audio-only features. Have written authorisation ready for Apple's 5.2.2/5.2.3 review.
6. **Don't rely on Chordify as precedent** for analysis audio. Its sourcing is undisclosed. Copy the parts that are documented: the official embed, user uploads kept private to each user, and work with publishers.
7. **Get a targeted legal and YouTube-policy review** of the chosen chord source and arrangement display before any monetisation. This matches [plan.md §10](../plan.md).
