# Strum Along: iPhone strum-along web app (vibe-coded v0)

Started 24 October 2026 at the founder's request: "an app I can use on my iPhone so I can strum along with YouTube videos of top rock and pop songs". This is a fast, deliberately provisional build. It reuses the repo's existing charts, beat grids and practice patterns. Rough edges are recorded as GitHub issues so the work can be polished later instead of re-explored.

Founder choices made in chat on 24 October 2026:

- **Delivery:** GitHub Pages. The static app is public but unlisted. It is deployed from a dedicated `gh-pages` branch built from `strumalong/` only, so deployment stays separate from source pushes.
- **Songs:** the 10 prepared recordings plus new rock/pop additions imported now. Additions use the existing yt-dlp importer and frozen CREMA and rhythm-grid tools. Their charts are automatic and unreviewed.

## Non-negotiable constraints (from the repo and tickets)

- Never alter frozen inputs. These are `experiments/review/{rhythm,practice,learning}.json`, everything under `experiments/generated/*` for existing packs, and `automatic_drafts.py`, `rhythm_grid.py` and the other files pinned by `experiments/fixtures/selected-workflow-player-v5.json`. Read them and copy what you need. New outputs go in new files or directories.
- All charts are **provisional automatic drafts** (#22: nothing is accepted). The UI says so without nagging: one badge per song plus a details line.
- Strum patterns are **practice suggestions** (glossary). Never call them "recorded strumming" or a transcription.
- Beats come from an **estimated** grid. Bars are **approximate**: downbeats are not verified.
- Riff songs (Seven Nation Army, Come As You Are) get no strum drill. Show the riff note instead.
- YouTube rules:
  - Keep the official visible player and put nothing over it.
  - The player must be at least 200×200 CSS px.
  - No background or audio-only play, and no download.
  - Send a Referer, using `strict-origin-when-cross-origin`.
- Never serve from `127.0.0.1` or a LAN IP. YouTube rejects IP-literal referrers, which is the likely cause of the earlier "error 150". Use `http://localhost:<port>` locally and the https Pages URL on the phone.
- Never stretch or scale timings onto a different upload. An alternate video needs its own timing check. Without one, it is offered only with a visible "timing unchecked" note and the user's nudge offset.
- No lyrics anywhere: data, UI or issues.
- Keep the localStorage prefix `music-os-strumalong-v1:`. It must not collide with the Mac player's `music-os-review-exposure:`, `music-os-practice-progress:` or `music-os-playalong-feedback:` prefixes.

## Layout

```
strumalong/                 # deployable root (published to gh-pages as-is)
  index.html                # app shell; hash routes: #/ (library), #/song/<id>
  app.js                    # DOM, routing, YouTube controller, render loop
  styles.css
  lib/core.js               # pure timeline/cue/strum helpers (UMD: window.StrumCore + module.exports)
  lib/shapes.js             # chord grip table + SVG renderer (UMD: window.StrumShapes + module.exports)
  songs/index.json          # catalogue summary (generated)
  songs/<id>.json           # one per recording (generated)
  data/additions.json       # authored metadata for new songs: capo, setup notes, practice patterns
  tools/build-songs.js      # node exporter: repo packs -> songs/*.json (not deployed logic, harmless if published)
  test/*.test.js            # node:assert tests; run: node strumalong/test/run.js
  manifest.webmanifest, icons/, .nojekyll
```

Plain static files with no bundler and no npm install. Scripts are classic `<script defer>` tags in this order: `lib/core.js`, `lib/shapes.js`, `app.js`.

## Data schema

### `songs/index.json`

```json
{ "schema": "strumalong-catalogue-1",
  "groups": [ {"id":"path","title":"Suggested practice path","note":"Provisional order; choose any song."},
              {"id":"more","title":"More rock & pop","note":"New automatic charts, not yet reviewed."},
              {"id":"riff","title":"Riff songs","note":"No strumming guide; the chord display does not teach the riff."},
              {"id":"outside","title":"Also available","note":""} ],
  "songs": [ { "id":"troggs-wild-thing-youtube-20261011", "title":"Wild Thing", "artist":"The Troggs",
               "group":"path", "order":1, "video_id":"bLJkrOYHNw8", "duration_seconds":155.35,
               "bpm":103, "meter_label":"4/4 assumed", "capo":0,
               "core_shapes":["A","D","E"], "playable_embed": true, "embed_note":"" } ] }
```

### `songs/<id>.json`

```json
{ "schema": "strumalong-song-1",
  "id": "...", "title": "Wild Thing", "artist": "The Troggs", "group": "path", "order": 1,
  "recording": { "id": "...", "duration_seconds": 155.352, "audio_sha256": "..." },
  "videos": [ { "video_id": "bLJkrOYHNw8", "uploader": "The Troggs - Topic", "kind": "analysed",
                "offset_seconds": 0, "timing_checked": true, "note": "Chart computed from this upload's audio." } ],
  "chart": { "source": "CREMA automatic draft", "sha256": "...", "status": "provisional",
             "corrections": [ { "id":"...", "start":23.777, "end":26.099, "from":"E", "to":"A", "note":"Founder report; provisional" } ] },
  "capo": 0, "capo_source": "catalogue|suggested|none",
  "setup_note": "Standard tuning (EADGBE).",
  "rhythm": { "status":"estimated", "bpm":103.4, "beats_per_bar":4, "beats_per_bar_assumed":false,
              "meter_label":"4/4 assumed", "bar_phase":0, "bar_phase_confident":false },
  "beats": [0.232, 0.813, ...],
  "chords": [ { "s":0, "e":2.415, "l":"N" }, { "s":2.415, "e":4.087, "l":"A" }, { "s":23.777, "e":26.099, "l":"A", "c":1 } ],
  "strumming": { "note":"...", "patterns":[ {"id":"steady-down","name":"Start: steady downstrokes","counts":["1","2","3","4"],"strokes":["D","D","D","D"],"description":"..."} ] },
  "learning": { "skill_focus":"...", "prerequisites":"...", "sources":[{"title":"...","url":"..."}] },
  "riff": null | { "note": "The chord display and strumming arrows do not teach the riff. ..." },
  "provenance": { "pack":"automatic-first-ten-v1", "manifest_sha256":"...", "rhythm_sha256":"...", "practice_sha256":"...", "learning_sha256":"..." } }
```

- Times are seconds, rounded to 3 decimals.
- `l` is the **sounding** label after display corrections. `N` means no chord and `X` means unclear.
- `c:1` marks a corrected event.
- Shape (capo) and Core labels are computed at runtime by `lib/core.js`.
- When `beats_per_bar` is null (Wonderwall), the exporter writes 4 and `beats_per_bar_assumed: true`.
- `bar_phase` is a heuristic chord-start residue vote, not a verified downbeat. Every native chord start that is not N or X and lies strictly inside the beat grid votes for `round(beatPosition(start)) mod beats_per_bar`, which is the beat the app draws as that hold's first dot. Ties keep the lowest residue. `bar_phase_confident` is true when there are at least 8 votes and the winning share is at least 0.7; an assumed meter is never confident. `bar_phase_share` records the share.
- `core_shapes` (index card chips) lists the Core shapes at the song's capo by chord seconds. Shapes under 3% of chord time are dropped, as are slash shapes under 10%. The list is longest first and holds at most 6.
- A video entry carries `embeddable: false` only when that upload is known not to play in an embed (Come as You Are's age-restricted analysed upload). The app then starts on the first embeddable entry.

## `lib/core.js` API (pure, unit-tested)

Ported helpers from `experiments/review/app.js` keep their names and behaviour. Each carries a comment naming its source line.

- `transposePracticeLabel(label, capo)` and `coreChordLabel(label)` follow the Mac player.
- `shapeLabel(sounding, {capo, view:'shapes'|'sounding', quality:'core'|'full'})`
- `buildTimeline(song, opts)` returns display events `{s,e,label,full,sounding,c}`. Adjacent equal labels are merged after transforms. Merges never bridge N or X.
- `chordIndexAt(events, t)` is a binary search that returns the index, or -1.
- `beatPosition(beats, t)` returns a fractional beat index or null, as in the Mac player.
- `cueAt(timeline, song, t)` returns:
  `{ now:{label, idx, startBeat, beats, dots:[{state:'past'|'active'|'future'}], barBefore:[dotIndex...], seconds, remaining}, next:{...}|null, beatsUntilChange:int|null, secondsUntilChange, inBeatGrid:bool }`
  - **Dot count** is `round(endBeat) − round(startBeat)`, with a minimum of 1, so each grid beat belongs to exactly one hold.
  - **Short spans:** if the span is under 0.75 beat, set a `quick:true` flag and show one dot.
  - **Long spans:** cap at `2*beats_per_bar` dots and set `more:n` for the rest. The UI shows something like "+4".
  - **Bar lines:** place one before dot k when `(round(startBeat)+k - bar_phase) mod bpb == 0` and k>0. This single `bar_phase` anchor drives both the bar lines and the strum count, so a bar line is always where the strum count reads 1. Nothing is anchored to the hold, because the strumming hand keeps one pendulum across chord changes. When `bar_phase_confident` is false, the lines still use `bar_phase`, the UI labels them "approx bars", and NEXT gets no solid bar-start border (`barStart: null`).
  - **Outside the beat grid:** fall back to seconds, with `dots` empty and `seconds` set.
- `strumStep(song, pattern, t)` returns the index into `pattern.strokes` at time t, or null outside the grid.
  - `stepsPerBeat = pattern.counts.length / bpb`
  - `pos = ((beatFloat - bar_phase) mod bpb + bpb) mod bpb`
  - `step = floor(pos*stepsPerBeat)`
- `suggestCapo(chords)` is exported for the exporter. For each capo from 0 to 7 it scores the share of chord seconds whose core shape is one of the easy open shapes A, Am, C, D, Dm, E, Em, G. F, Bm and B7 get half credit. It returns `{capo, score, scores[]}`, preferring the lower capo on near-ties (within 0.03).
- `cueTime(playerSeconds, offsetSeconds, nudgeMs, latencyMs, rate)` returns `player + offset + nudge/1000 − latency/1000 × rate`. Latency is wall-clock delay, so at 0.5× it covers half as much media time. The nudge and offset are media time and are not scaled. A rate that is not a positive number counts as 1.
- `formatTime(s)` returns "m:ss".

## `lib/shapes.js` API

- `getShape(label)` returns `{name, frets:[6 ints|-1 low E→high e], fingers:[6 ints|0], baseFret, barre:{fret,from,to}|null, note}` or null.
  - Slash chords fall back to their root shape with `note:"bass note omitted"`, unless an explicit grip exists (G/B, D/F#, C/G).
  - Coverage must include every Core and Full shape label that appears in any built song, at its default capo view. Unknown labels return null, and the UI then shows the name only.
- `renderShapeSVG(shape, {size})` returns an accessible SVG string with `role="img"` and an `aria-label` that names the chord and frets. It has 6 strings and 5 frets, × and ○ markers, a barre bar, a base-fret label, and uses `currentColor` so it themes.

## UI

- **Library (`#/`).**
  - Grouped song cards. Each shows the title, artist, up to 6 Core shape chips, ~BPM and a capo badge. When the analysed upload can't be embedded, the card also gets a "timing unchecked" badge (or "alternate video" if the alternate's timing was checked).
  - A last-played song gets a resume chip.
  - The header reads "Strum Along · music-os", with the line "Provisional automatic chord charts. For personal practice."
- **Song (`#/song/<id>`), portrait, top to bottom:**
  1. A top bar with a back link, the title and the provisional badge.
  2. The YouTube player at full width, 16:9, with nothing on top.
  3. The **cue panel**, layout A as approved in #23.
     - The NOW chord is large, with the NEXT chord immediately to its right.
     - Beat dots sit under both chords: ● marks the active beat, ◉ past beats in the current hold, ○ future beats.
     - Vertical bar lines separate bars.
     - A line below reads "3 beats to change", or "4.2 s to change" outside the grid. Seconds are wall-clock: they are divided by the playback rate. Before the first play it reads "Loading video…", then "Tap ▶ to start" (or "Capo N on, then tap ▶").
     - A compact Play/Pause button sits at the right of that line, so playback can start with the player and cues on screen. It stays visible and usable above the Hide-cues and ad covers.
     - Quick changes get a "quick" marker.
  4. The **strum panel**: the pattern's strokes as ↓/↑/· cells with counts underneath. The current step is highlighted from the beat grid. A small selector chooses between the Start and Next patterns. The label is "Suggested practice pattern, not the recorded part".
  5. **Chord diagrams** for NOW and NEXT. They always draw the capo-shape grip, the shape the hand holds. In Sounding view the caption keeps the sounding name and a note reads "G shape, capo 2".
  6. **Controls**:
     - Big Play/Pause.
     - "−10 s", restart, speed (`getAvailablePlaybackRates`), and "Hide cues" for interruptions.
     - A **sync nudge** (−/+ 50 ms, showing the current offset), saved per video in localStorage.
     - A **View** group: Simple (Core) or Full chords, Capo shapes or Sounding when the capo is above 0, and Diagrams on or off.
  7. **Details** (collapsed): setup note, skill focus, sources (links), chart status, corrections, the video's uploader, and "Open on YouTube".
- **Song (`#/song/<id>`), landscape at 700 px wide or more:** a two-column grid, with the player and controls on the left and cues, strum and diagrams on the right.
- **Theme.** Use the palette of layout A and the Mac player: background `#f4f1e8`, text `#222b27`, accent `#22543e`, panels white with `#d4d8cc` borders. Add a dark mode via `prefers-color-scheme`.
- **Sizing.** Large tap targets of at least 44 px. Respect safe areas with `viewport-fit=cover` and `env(safe-area-inset-*)`.
- **iOS Home Screen.** Set the `apple-mobile-web-app-capable` meta and add a manifest and `apple-touch-icon`.

## Playback and sync

- Load `https://www.youtube.com/iframe_api` once. Create `new YT.Player(el, {videoId, playerVars:{playsinline:1, rel:0, controls:1, enablejsapi:1, fs:0, origin:location.origin}})`.
- **Clock.** Render from a `requestAnimationFrame` loop. Read `player.getCurrentTime()` every frame; it is already wall-clock interpolated inside the API.
  - Cue time is `t = playerTime + videoOffset + userNudge − latency × playbackRate` (`cueTime`).
  - Only animate while the state is 1, playing. On pause, keep the cue static at the paused position.
  - On buffering, or with state -1 or 5, show the last cue with a "waiting" note.
- **Ad / wrong-video guard.**
  - When `|getDuration() - recording.duration_seconds| > 3` while playing, hide the cues and show "Ad or different video, cues paused".
  - Recheck every frame and resume automatically.
- **Errors.**
  - An entry marked `embeddable: false` is skipped at start, with no error or switch message.
  - 101, 150 or 152: try the next entry in `song.videos`. Show "Playing <uploader>'s official video instead; the analysed upload can't play here", plus its note and "timing unchecked" if that applies. The switch message clears once playback starts. With no entries left, show "This video can't play inside the app", an "Open on YouTube" link and a non-synced chord list.
  - 153: "Player configuration error (referrer)". Do not retry.
  - 100: "Video unavailable".
  - 2 or 5: offer a retry button.
- **Wake Lock.** Call `navigator.wakeLock.request('screen')` on Play and again on `visibilitychange` to visible while playing, inside try/catch. The lock is kept while paused, because chords are read during a pause. It is released when the song ends (state 0) or the page is left. Before iOS 18.4, Wake Lock does not work in Home Screen web apps.
- **Visibility.** Pause the video when the page becomes hidden.
- **Gestures.** Both Play buttons call `player.playVideo()` from the click handler. If the player frame is not fully in the viewport, it is first scrolled into view. If `onAutoplayBlocked` fires, show "Tap ▶ in the video to start".
- **Load failures.** Every message that says to reload carries a Reload button of at least 44 px. After 15 s without the IFrame API, the cached API promise is dropped, so the next song page retries the load.
- **Persistence.** The localStorage keys are `music-os-strumalong-v1:` + `settings`, `offset:<video_id>`, `last` (`{id, t}`) and `latency`, which is a global ms offset for Bluetooth. Wrap every access in try/catch.

## Additions pipeline (new songs)

Target: about 10 new strum-friendly rock/pop hits. Prefer:

- a steady tempo and a strummed guitar part;
- open chords, or open shapes under a common capo;
- no tempo changes, irregular bars or pickups (#22);
- an official **"Artist - Topic"** upload of the original studio recording that is embeddable and **not age-restricted**.

First picks, with fallbacks in order:

| Song | Notes |
|---|---|
| The Cranberries – Zombie | |
| Green Day – Good Riddance (Time of Your Life) | |
| Oasis – Don't Look Back in Anger | |
| Creedence Clearwater Revival – Have You Ever Seen the Rain | |
| Creedence Clearwater Revival – Bad Moon Rising | |
| Tom Petty – Free Fallin' | capo 3 shapes |
| Weezer – Island in the Sun | |
| John Denver – Take Me Home, Country Roads | capo 2 shapes |
| Lynyrd Skynyrd – Sweet Home Alabama | |
| Vance Joy – Riptide | capo 1 shapes |
| *Fallbacks:* The Beatles – Let It Be; Counting Crows – Mr. Jones; Blind Melon – No Rain; The Lumineers – Ho Hey; R.E.M. – Losing My Religion | |

Steps:

1. Import with `experiments/analysis/youtube_import.py`. Recording IDs follow `<artist>-<song>-youtube-20261024`. The source-use note is "Requested local founder strum-along app, 24 Oct 2026; personal testing; commercial clearance not established".
2. Run CREMA with the **unchanged** settings used for `automatic-first-ten-v1`.
3. Run the `rhythm_grid.py` pulse grid with a source-informed tempo prior. The prior goes in a new config, `experiments/fixtures/rhythm-strumalong-additions-v1.json`.
4. Write a new gitignored pack at `experiments/generated/strumalong-additions-v1/` that mirrors the `automatic-first-ten-v1` manifest structure, plus its own `rhythm.json`.
5. Authored capo, setup notes and two practice patterns per song go in `strumalong/data/additions.json`. These are suggestions and are labelled as such.

## Verification

- `node strumalong/test/run.js` passes.
- `node strumalong/tools/build-songs.js --check` prints CHECK OK. `scripts/deploy-strumalong.sh` runs it after the tests and stops if `songs/` is stale.
- The existing `node experiments/review/test.js` still reports 96 checks.
- The frozen-pin check passes: `.venv-analysis/bin/python -B experiments/analysis/workflow_check.py --policy experiments/fixtures/selected-workflow-player-v5.json`.
- A browser check at `http://localhost:<port>/` in a 390×844 viewport covers the library, a song page, YouTube load and play, cues advancing, and the error fallback.
- After deployment, the Pages URL is checked the same way.
- Behaviour on the iPhone itself (Safari and Home Screen) is the founder's check. Record what is and isn't verified.
