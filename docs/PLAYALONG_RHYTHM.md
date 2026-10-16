# Chord duration and suggested strumming

Deployed and browser verified, 12 October 2026. This continuation addresses two founder
observations: the equally sized upcoming cards did not show how long to hold a
chord, and the player supplied no suggested strumming rhythm.

## Player changes

The current chord shows its full hold duration, remaining time and progress.
A proportional near-future strip gives longer chords more width, with a Now
marker following the prepared audio clock. Blank gaps, No chord and Unclear
remain distinct. Progress stops at the current chord's end even when the next
label starts later. Current and upcoming holds use the selected Full/Core and
capo display; raw source chords, timings and feedback stay unchanged.

Seconds remain available. Paired automatic beat estimates can add approximate
beat/bar duration labels only within their observed coverage. Bar counts need an
explicit pulse-per-bar convention. These are lengths, not verified bar numbers
or downbeats, and chord boundaries are not snapped to the grid.

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

Implementation passes 47 JavaScript helper checks and 239 distinct Python checks (223 in the standard environment plus 16 in the pinned evaluation environment). Isolated browser QA verifies estimated/seconds views, Core merging, 6/8 and syncopation choices, proportional strip widths, and feedback capture/persistence on a separate origin. The deployed port-8070 player verifies all ten guides, pattern selection, playback/pause and advancing hold progress. All 47 public assets match the Mac checkout; three sampled private paths return 404, and ports 8067/8068 are restored. The pack identity is unchanged, with no test issues added to the normal players. Next evaluate
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
