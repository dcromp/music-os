# Chord duration and suggested strumming

Initially deployed and browser verified, 12 October 2026; player guidance updated
17 October. The original continuation addressed two founder
observations: the equally sized upcoming cards did not show how long to hold a
chord, and the player supplied no suggested strumming rhythm.

## Player changes

The current chord shows its full hold duration, remaining time and progress.
A proportional near-future strip gives longer chords more width, with a Now
marker following the prepared audio clock. Blank gaps, No chord and Unclear
remain distinct. Progress stops at the current chord's end even when the next
label starts later. Current and upcoming holds use the selected Full/Core and
capo display; raw source chords, timings and feedback identities are preserved.

The 17 October update makes the duration visible inside each scrolling chord,
using compact numbers such as **~½**, **~1** and **~2** under the estimated-bars legend. The Now and Coming up cards retain the full units. Irregular
estimates retain decimals instead of snapping to half bars. Longer holds have
internal divisions one estimated bar-length apart, measured from that chord's
original onset using the local variable-tempo pulse timestamps. These are
hold-relative duration marks, not the recording's measure starts. Clipping the
scrolling window does not reset that origin or shorten the total duration
caption; continuation arrows identify a hold that extends beyond the view.
The track has a 960-pixel minimum width. Narrow screens can scroll it horizontally; very short clipped edge fragments retain full tooltip and accessible descriptions. The Now and
Coming up cards also keep prominent readable lengths.

Seconds remain available. Paired automatic beat estimates can add approximate
beat/bar duration labels only within their observed coverage. Bar counts need an
explicit pulse-per-bar convention. These are lengths, not verified bar numbers
or downbeats, and chord boundaries are not snapped to the grid.

## Reported display corrections

Founder play-along feedback on 17 October identifies **A near 25 seconds in
Wild Thing**, where the native CREMA chart says E. A separate provisional
display correction covers the containing native span,
23.777233560090703–26.09922902494331 seconds. The report does not verify the
entire span or its physical change boundaries. The raw E event and its original
timing remain unchanged; an on-screen note identifies the reported correction.
This is not a promoted verified arrangement or independent timing reference.

The overlay requires the exact playback pack, recording/audio identity, primary
chart SHA-256, analysis ID and native event boundaries/label. A mismatch leaves
the original chart visible. Feedback records both raw E and displayed A, plus
the correction ID, provisional status and reported time. The existing browser
feedback key and practice identity remain unchanged.

The server's `X-Music-OS-Chart-SHA256` response header binds a digest to the exact
chart bytes it serves. Browsers with WebCrypto compute the digest directly;
embedded browsers without it use this local-server header. Without a valid
digest the correction is not applied and original playback remains available.
Pack/chart/teaching JSON requests bypass stale browser caches when a localhost port is reused. The subsequent [cache follow-up](PLAYER_CACHE_FOLLOWUP.json) also serves allowlisted HTML, scripts, styles and JSON as current `200`/`no-store` responses, replacing legacy conditional caches. A page already open still needs one reload or a fresh tab; **17 Oct update** identifies the current HTML. Advanced source details show the effective chart digest, analysis and pack ID. This local provenance check does not prove musical accuracy.

Dylan's single detected Am7 is retained in the raw/full chart. The existing
Core chords choice shows Am, just as Em7 can show Em; no additional label or
boundary change is made for that observation.

## House intro correction and source lookup

The founder confirmed **E major**. [Jon MacLennan](https://www.jonmaclennan.com/blog/house-of-the-rising-sun-guitar-lesson) and [Jonathan Richter](https://richterguitar.com/house-of-the-rising-sun-the-animals/) both teach Am–C–D–F / Am–E–Am–E. Their order supports the label choice, not exact recording boundaries. The long native Am at 6.409–11.146 seconds now has a separate provisional E span at 7.988–9.474 seconds from the paired secondary detector, preserving Am on both sides. The following Em cue displays E with its native bounds. Its 12-second metadata point is explicitly representative, not an additional founder timestamp; the UI says “Reported intro correction” without attributing that time to the user.

Split overlays must stay inside an exactly matched native parent cue. Feedback retains raw Am/Em, displayed E, the proposed display interval and time provenance. Old feedback remains readable. The [proposal record](../catalogue/house-intro-feedback-20261017.json) and [verification](HOUSE_INTRO_FEEDBACK_UPDATE.json) preserve the source and timing limits. No full-song chart is promoted.

Online source research currently runs through the agent and saved catalogue records; automatic web search/consensus is not an implemented app or preparation feature. The source-to-player gap is explicit in the README.

## Beat and meter evidence

The producer uses the existing librosa environment, with onset strength and
native beat tracking on the exact prepared audio. Local beat timestamps allow
tempo variation instead of deriving all durations from one constant BPM.
[Love Me Do's tempo analysis](https://midi.org/may-24-tempo-track-tweaks) illustrates
why a fixed tempo is insufficient. Rhythm metadata is matched by recording ID,
audio SHA-256, sample rate and duration; missing or invalid data falls back to
seconds without blocking playback.

The local multi-prior diagnostic found material pulse ambiguity. Creep produced
92/185 pulses per minute, Wonderwall about 70/117/172, and House about 78/117/235.
A regular grid does not establish which musical pulse was detected. We use
curated pulse ranges where primary notation provides a useful starting point:

| Song | Source evidence used as a prior | Display convention |
|---|---|---|
| Creep | [Drumeo](https://drumeoblog.s3.amazonaws.com/beat/wp-content/uploads/2021/11/08134434/15.-Creep.pdf): quarter note 93, 4/4 | Approximate four-quarter bar lengths; source is not exact-upload gold |
| Wonderwall | [Oasis Musicnotes edition](https://www.musicnotes.com/sheetmusic/oasis/wonderwall/MN0053372): quarter 88. [Drumscore](https://bypass.drumscore.com/sheet-music/browse-by-artist/score/952-oasis-wonderwall-drum-sheet-music-tab) describes 4/4 and 2/4 | Beat lengths only; local meter transitions remain unchecked |
| House Of The Rising Sun | [Jon MacLennan](https://www.jonmaclennan.com/blog/house-of-the-rising-sun-guitar-lesson): six eighths with anchors at 1/4 | Proposed 6/8 convention: two dotted-quarter pulses per bar; acoustic pulse range is a project hypothesis |
| Seven Nation Army | [Drumscore](https://bypass.drumscore.com/sheet-music/browse-by-artist/score/12768-the-white-stripes-7-nation-army-drum-sheet-music-tab): 124, 4/4 | Four-quarter practice convention |
| Come As You Are | [Musicnotes](https://www.musicnotes.com/sheetmusic/nirvana/come-as-you-are/MN0069767): quarter 120, 4/4 | Four-quarter practice convention; sounding labels remain distinct from D-standard shapes |
| Brown Eyed Girl | [Drumscore](https://drumscore.com/sheet-music/browse-by-artist/score/14285-van-morrison-brown-eyed-girl-drum-sheet-music-tab): 151, 4/4 | Four-quarter practice convention |
| Twist And Shout | [Drumscore](https://www.drumscore.com/sheet-music/browse-by-artist/score/14622-the-beatles-twist-and-shout): 123, 4/4 | Four-quarter practice convention |

Dylan uses a proposed slow-ballad pulse range; Wild Thing and Love Me Do use the
tracker's default starting prior. Their metrical level and recording structure
remain unverified. Source notation describes its own teaching/transcription
arrangement and supplies no timestamp gold for these uploads.

In House's 6/8 convention, 78 dotted quarters, 117 quarters and 234 eighths per
minute can describe the same speed: a bar contains two dotted quarters, three
quarters or six eighths. Dividing every detected BPM by four would be misleading.
The configuration records units and hypotheses in
[the pulse configuration](../experiments/fixtures/rhythm-first-ten.json).

## Suggested strumming

The count-and-arrow presets are original project exercises, not copied recorded
strumming transcriptions. Begin with steady downstrokes, then optionally add
alternating down/up movement. Down/up arrows correspond to D/U; a dash means
skip the stroke while keeping the hand moving. Change shape at the chord cue;
short holds may use only part of a pattern.

House starts with two gentle downstrokes on eighth-note counts 1 and 4, then
six-count alternating motion. The recorded guitar's arpeggio remains a later
lesson. Wonderwall has a simple four-count start and a syncopation exercise;
that drill does not supply every recorded pattern or meter change. Riff songs
use chord-rhythm practice suggestions, with an explicit note that these arrows
do not teach the recorded riff. Creep's verse arpeggios are also later work.

The [practice metadata](../experiments/review/practice.json) pins each suggestion
to the prepared recording. It loads independently of beat estimates. A pattern
selection is optional and needs no founder annotation or timing work.

## Reproduce

New beat extraction needs the existing separate CREMA/librosa environment;
saved browser playback needs no neural or beat-analysis runtime:

```sh
.venv-crema/bin/python experiments/analysis/rhythm_grid.py \
  --manifest experiments/generated/automatic-first-ten-v1/manifest.json \
  --config experiments/fixtures/rhythm-first-ten.json \
  --output experiments/review/rhythm.json
```

The saved output is already present; use a fresh path to compare another run.
Only an intentional replacement uses `--overwrite`. The fixed metadata routes
are `/rhythm.json` and `/practice.json`; arbitrary project paths stay private.
The existing pack identity and audio are preserved, so saved feedback continues
to belong to the same recording.

## Status and next checks

The original 12 October implementation passed 47 JavaScript helper checks and 239 distinct Python checks (223 in the standard environment plus 16 in the pinned evaluation environment). Its isolated browser QA verified estimated/seconds views, Core merging, 6/8 and syncopation choices, proportional strip widths, and feedback capture/persistence on a separate origin. The deployed port-8070 player verified all ten guides, pattern selection, playback/pause and advancing hold progress. All 47 public assets matched the Mac checkout; three sampled private paths returned 404. Those deployment and count results are historical; current service status is in the README.

**Earlier 17 October player verification:** 136 JavaScript checks (74 player, 48 bench, 14 curation) pass; 440 Python tests are discovered, with 420 passed and 20 optional-dependency skips. The explicit player-v2 audit verifies 39 pins and ten selected cases. Browser QA verifies the A cue at 25 s, Dylan Core Am/full Am7 at 47 s, seconds fallback, all ten song choices, Love Me Do outside the path, and feedback persistence/removal on an isolated origin. Default and narrow-screen geometry checks confirm proportional horizontal blocks, readable ordinary short-hold numbers and local horizontal scrolling without page overflow. Tiny clipped edge blocks retain complete tooltip/accessibility descriptions. [Verification record](PLAYALONG_FEEDBACK_UPDATE.json). Current guide
metadata is pinned by `experiments/fixtures/selected-workflow-player-v3.json`;
37 earlier frozen inputs stay unchanged and only two guide pins are versioned.
The saved beat grid, raw charts/audio and playback/storage identities remain
unchanged. Next evaluate
beat-level/count usefulness against independently checked real excerpts, verify
recording-compatible strumming by section, and measure followability during
normal guitar practice. The broader reference milestone remains 1.5–2.5 focused
days; this interface addition does not establish an accurate full arrangement.

## Procedural beat sanity check

The [saved sanity report](RHYTHM_SANITY.json) evaluates five generated percussive
fixtures at 87, 93, 124 and 151 pulses/minute plus a 73→83 ramp centred near 78.
Known pulse timestamps were kept separate from extraction. At the predeclared
150ms tolerance, 155/160 pulses match, with no extras and five missed final
pulses. Maximum error among matched pulses is 33.5ms; maximum distance for any
reference pulse is 708.5ms, including misses. Both are retained so trimming does
not hide failures. Counts inside leading/trailing silence are also reported.

These tests check pulse-tracking behavior with declared tempo-level ranges.
They do not validate the chosen musical beat unit, downbeats, bar phase or
real-song meter. The UI uses seconds outside observed coverage. Exact inputs,
references and native predictions are saved in the ignored local
`experiments/generated/rhythm-screen-v1/` pack; their hashes are in the report.

The subsequent [six-recording paired diagnostic](RHYTHM_REFERENCE_CHECK.md)
checks nominal-grid pulse agreement and half/one/two-bar duration counts. A tempo
range fixes one pulse-level failure, but phase remains uneven; no downbeats or
first-ten arrangements are verified. The frozen fresh selection awaits its
source host. This continuation adds 20 evaluator checks, with no player changes.

The [deployment snapshot](PLAYALONG_RHYTHM_RESULTS.json) records code/config/data
hashes and the saved preview. The player is a session-local server; restart
`automatic_drafts.py serve --pack experiments/generated/automatic-first-ten-v1
--port 8070` after reboot or an interrupted tool session. The local screenshot
is `experiments/generated/player-proof-20261012/rhythm-strumming.jpg`.
