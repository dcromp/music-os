# YouTube pilot playback research

19 October 2026 · Source checkout `1de7238` · [Establish YouTube playback and synchronisation limits](https://github.com/dcromp/music-os/issues/21) · [Curated YouTube pilot map](https://github.com/dcromp/music-os/issues/19)

## Question and finding

Can a visible YouTube recording drive adjacent play-along chords and useful practice controls? **The documented interface supplies the necessary basic controls; useful synchronisation on the pilot target remains unmeasured.** This research does not choose the delivery platform or establish musical accuracy, rights clearance, continuous availability or seamless loops. Scope: a free private pilot, founder first, then a few guitarists, with 10–20 curated songs. No application changes, dependency installs, video downloads or playback experiments were performed.

## Documented player capabilities

The following compact inventory comes from the current [official IFrame API reference](https://developers.google.com/youtube/iframe_api_reference):

| Area | Documented behaviour |
|---|---|
| Controls and time | `playVideo`/`pauseVideo` control playback; `getCurrentTime` returns elapsed seconds. |
| Readiness | `onReady` means API calls can be received, not that audio has begun. |
| State | `onStateChange`: unstarted −1, ended 0, playing 1, paused 2, buffering 3, cued 5. |
| Buffer | `getVideoLoadedFraction` reports a buffered fraction, not a delivery deadline. |
| Seeking | `seekTo` preserves paused state; otherwise it plays. It can land on an earlier keyframe unless target data is downloaded. `allowSeekAhead` controls fetching unbuffered data. |
| Speed | Query `getAvailablePlaybackRates`; confirm changes through `onPlaybackRateChange`. Requests can fail; cue/load resets speed to 1. |
| Segment end | Cue/load accepts `endSeconds`; seeking cancels that bound. |
| Failures | Errors include invalid parameters (2), HTML5 failure (5), missing/private video (100), embedding denied (101/150). |
| Blocked start | `onAutoplayBlocked` reports blocked scripted playback. |

Unspecified: clock-error bounds, public ad-transition events and seamless A/B loops. These need target measurements.

## Presentation, interruptions and devices

Single-recording repetition uses `loop=1` together with `playlist=VIDEO_ID`. This is whole-video repetition. `controls=0/1` is supported; `modestbranding` is ineffective, and `rel=0` restricts related videos to the same channel rather than removing them. `playsinline=1` concerns iOS mobile browsers and appropriately configured WebViews. Set `enablejsapi=1` and the host `origin` when constructing a controllable embed. These are documented parameters, not proof the existing wrapper exposes every one correctly. [Player parameters](https://developers.google.com/youtube/player_parameters).

The embedded viewport must be at least 200×200 pixels, with controls fitting fully; YouTube recommends at least 480×270 for 16:9. Nothing may obscure the embedded player, including its controls. Automatic playback requires more than half the player to be visible, and only one automatic player may run simultaneously per page/screen. Current client identification requires `HTTP Referer` or the documented environment-specific alternative; suppressing identity can produce blocked playback. WebViews require explicit attention to this setup. [Required minimum functionality](https://developers.google.com/youtube/terms/required-minimum-functionality).

Ads can appear in embedded videos, including skippable and non-skippable ads. An embedder cannot assume an uninterrupted practice session. [YouTube’s embedded-ad explanation](https://support.google.com/youtube/answer/132596?hl=en). API policy prohibits obstructing ads, background players and separating or modifying the audiovisual components. Therefore an isolated backing track is a separate future rights/product decision, not a player feature available merely by embedding YouTube. [Developer policies, sections III.I.5–9](https://developers.google.com/youtube/terms/developer-policies#i.-additional-prohibitions).

Age-restricted recordings generally cannot play on third-party sites. Missing referrer identification produces error 153. Recheck actual selected recordings and provide an unavailable state; opening YouTube externally cannot keep adjacent in-app chords in view. [Embedding help](https://support.google.com/youtube/answer/171780?hl=en). Regional/account/network differences remain target-test cases, not something a successful founder session excludes.

Chrome permits muted autoplay more broadly than audible autoplay; interaction, engagement and iframe permissions affect sound. [Chrome autoplay policy](https://developer.chrome.com/blog/autoplay/). WebKit advises assuming a user gesture is required and handling denied playback; its cited macOS article is historical guidance, not a present-device test. [WebKit autoplay guidance](https://webkit.org/blog/7734/auto-play-policy-changes-for-macos/). Native iPhone WebViews also need inline-playback configuration. [Apple `allowsInlineMediaPlayback`](https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/allowsinlinemediaplayback). Provisional recommendation: begin with a visible, user-started player and chords beside/below it, preserving native controls and branding. Do not select a native platform from these facts alone.

## Existing-code audit

Source links below describe checkout `1de7238`, extending the [reuse audit](REUSE_AUDIT.md):

- [YouTube wrapper](../app/components/YoutubePlayerComponent.js), lines 14–42: `getCurrentTime()` is an asynchronous button action, formatted into text. No continuously supplied numeric clock, readiness/error handling or rate handling exists here.
- [Player screen](../app/screens/SongPlayer.js), lines 40–66: receives time text, but sends only `isPlaying` to the chord display. [Chord display](../app/components/ChordProgressionDisplay.js), lines 28–59 and 83–95: uses unrelated sample data and an independent fixed-tempo timer, repeating every chord across four beats.
- [Unused synchronisation sketch](../app/hooks/useTimeSynchronization.ts), lines 14–54: polls once per second and interpolates wall time at 50 ms intervals, assuming speed 1 without explicit source-generation/seek/buffering handling. [Unused state hook](../app/hooks/useYoutubePlayer.ts), lines 19–31: expects numeric states, whereas the active screen expects wrapper strings. [Local declaration](../react-native-youtube-iframe.d.ts) is incomplete.
- [Local review player](../experiments/review/app.js), `createPlaybackFrameLoop` and `updateClock`: reads the local audio element’s `currentTime` on visible frames. Its [recorded clock check](PLAYER_FRAME_CLOCK_CHECK.json) measures one local rendering pass and explicitly disclaims a guaranteed latency or verified musical attack. It never exercises the YouTube iframe, wrapper bridge, network, ads or different upload edits. Its results cannot validate the old integration.

## Bounded future prototype agenda — HITL, not executed

After choosing a target, use one minimal official embed with adjacent known cues before repairing the old screen. Pin exact recording IDs and independently check cue times; do not transfer local charts by duration scaling.

1. Record OS/browser/version, audio output, viewport, network and login state. Capture timestamped API reads, request/response times, states and rendered labels; distinguish internal display freshness from audible musical alignment.
2. With the founder playing guitar, check start, pause/resume, native-control seeks, buffered/unbuffered backward/forward jumps, replay, buffering recovery, rapid recording changes and available slower speeds. Reject stale reads after source changes; compare audible boundaries with chart cues.
3. Repeat short sections and whole recordings. Measure seek landing, restart gap and end overshoot. Observe ads and return to content without obscuring or bypassing them; record whether a trustworthy song clock can be maintained. Decide whether section repeats are useful enough to include.
4. Test denied autoplay, invalid/unavailable embeds, reload and return from another tab. Show recoverable states and prevent false moving chords. Test headphones/Bluetooth separately if included in scope.

Exit evidence: an observed capability matrix, timing-error/recovery samples, founder judgement and an explicitly chosen support target. Set a tolerable synchronisation threshold through that live trial; this research supplies no invented millisecond promise. Keep uncertain controls out of the first specification until their benefit and failure behaviour are understood.
