# Strum Along: iPhone strum-along web app (vibe-coded v0)

Started 24 October 2026 at the founder's request: "an app I can use on my iPhone so I can strum along with YouTube videos of top rock and pop songs". This is a fast, deliberately provisional build. It reuses the repo's existing charts, beat grids and practice patterns. Rough edges are recorded as GitHub issues so the work can be polished later instead of re-explored.

Founder choices made in chat on 24 October 2026:

- **Delivery:** GitHub Pages. The static app is public but unlisted. It is deployed from a dedicated `gh-pages` branch built from `strumalong/` only, so deployment stays separate from source pushes.
- **Songs:** the 10 prepared recordings plus new rock/pop additions imported now. Additions use the existing yt-dlp importer and frozen CREMA and rhythm-grid tools. Their charts are automatic and unreviewed.

Founder feedback on 25 October 2026, after using the first build:

- **Strumming songs only.** "There should be enough pop and rock songs to not worry about finger patterns." Picked, arpeggiated and riff songs leave the app (see "Catalogue config" for the list and reasons).
- **Progressive difficulty.** Songs needing barre chords (Creep's B and Cm) should come later. The library is now grouped into five levels (see "Difficulty levels").
- **Bar lines landed mid-chord** (Good Riddance). The single song-wide bar phase is replaced by chord-anchored bars (see "Bar model").

Later the same day, after the 36-song build:

- **Riptide** "is more a ukulele song": excluded in the catalogue config.
- **Automate basic checks.** "The idea of a curated list is that we can automate basic checks like chords and instruments."
- **Zombie chord mis-timings.** One chord was held a beat too long before going into three beats of the next one, "but every other time that sequence is played the timing is correct". The exporter now moves such a change by one beat to match the other repeats (see "Timing fix").

## Non-negotiable constraints (from the repo and tickets)

- Never alter frozen inputs. These are `experiments/review/{rhythm,practice,learning}.json`, everything under `experiments/generated/*` for existing packs, and `automatic_drafts.py`, `rhythm_grid.py` and the other files pinned by `experiments/fixtures/selected-workflow-player-v5.json`. Read them and copy what you need. New outputs go in new files or directories.
- All charts are **provisional automatic drafts** (#22: nothing is accepted). The UI says so without nagging: one badge per song plus a details line.
- Strum patterns are **practice suggestions** (glossary). Never call them "recorded strumming" or a transcription.
- Beats come from an **estimated** grid. Bars are **approximate**: downbeats are not verified.
- The catalogue holds **strumming songs** only. Riff, picked and arpeggiated songs are excluded in `strumalong/data/catalogue.json` with a reason, not deleted from the packs. The app no longer has a riff mode.
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
  app.js                    # DOM rendering, routing, YouTube adapter, render loop, wake lock
  styles.css
  lib/chords.js             # chord shape vocabulary: parse, capo shape/sounding, core label (UMD: window.StrumChords + module.exports)
  lib/core.js               # pure timeline/cue/strum helpers (UMD: window.StrumCore + module.exports)
  lib/repeat-timing.js      # repeat timing: groups repeated changes, drawn/played judgements, auto-timing entry (UMD: window.StrumRepeatTiming)
  lib/shapes.js             # chord grip table + SVG renderer (UMD: window.StrumShapes + module.exports)
  lib/session.js            # practice session: playback rules + persistence (UMD: window.StrumSession + module.exports)
  lib/library.js            # Jukebox journey rules: search, shelves, similar songs, Surprise me (UMD: window.StrumLibrary)
  songs/index.json          # catalogue summary (generated)
  songs/<id>.json           # one per recording (generated)
  data/catalogue.json       # which recordings ship: packs to read, exclusions with reasons, level overrides
  data/additions.json       # authored metadata for the v1 additions: capo, setup notes, practice patterns
  data/additions-v2.json    # (future) the same for the v2 additions pack; skipped while missing
  tools/build-songs.js      # node exporter: catalogue.json + packs -> songs/*.json (not deployed logic, harmless if published).
                            # exportSong(draft, metadata, settings) -> {song, card, report} is pure; the rest is its filesystem adapter
  test/*.test.js            # node:assert tests; run: node strumalong/test/run.js
  manifest.webmanifest, icons/, .nojekyll
```

Plain static files with no bundler and no npm install. Scripts are classic `<script defer>` tags in this order: `lib/chords.js`, `lib/core.js`, `lib/repeat-timing.js`, `lib/shapes.js`, `lib/session.js`, `lib/library.js`, `app.js`. core.js and shapes.js use chords.js; session.js uses core.js.

## Data schema

### `songs/index.json`

```json
{ "schema": "strumalong-catalogue-2",
  "groups": [ {"id":"level-1","level":1,"title":"Level 1 · First chords","note":"Up to three easy shapes from A, D, E, Em and Am."},
              {"id":"level-2","level":2,"title":"Level 2 · Open chords","note":"..."} ],
  "songs": [ { "id":"troggs-wild-thing-youtube-20261011", "title":"Wild Thing", "artist":"The Troggs",
               "group":"level-1", "order":1, "level":1, "level_label":"First chords",
               "video_id":"bLJkrOYHNw8", "duration_seconds":155.35,
               "bpm":103, "meter_label":"4/4 assumed", "capo":0,
               "core_shapes":["A","E","D"], "playable_embed": true, "embed_note":"" } ] }
```

- One group per level that has songs, in level order, each with a one-line explanation. `songs` is listed level by level.
- `order` is the position within the level: fewest `changes_per_min` first, then slower tempo, then title.

### `songs/<id>.json`

```json
{ "schema": "strumalong-song-2",
  "id": "...", "title": "Wild Thing", "artist": "The Troggs", "group": "level-1", "order": 1, "level": 1,
  "recording": { "id": "...", "duration_seconds": 155.352, "audio_sha256": "..." },
  "videos": [ { "video_id": "bLJkrOYHNw8", "uploader": "The Troggs - Topic", "kind": "analysed",
                "offset_seconds": 0, "timing_checked": true, "note": "Chart computed from this upload's audio." } ],
  "chart": { "source": "CREMA automatic draft", "sha256": "...", "status": "provisional",
             "corrections": [ { "id":"...", "start":23.777, "end":26.099, "from":"E", "to":"A", "note":"Founder report; provisional" } ] },
  "capo": 0, "capo_source": "catalogue|suggested|none",
  "setup_note": "Standard tuning (EADGBE).",
  "difficulty": { "level":1, "label":"First chords", "main_shapes":["A","E","D"], "hardest_shape":"A",
                  "tier_reason":"A, E, D: all first-chord shapes (tier 1), 3 main shapes. ...",
                  "changes_per_min":30.2, "median_hold_beats":2,
                  "computed_level":3, "override_reason":"..." },
  "rhythm": { "status":"estimated", "bpm":103.4, "beats_per_bar":4, "beats_per_bar_assumed":false,
              "meter_label":"4/4 assumed", "bar_phase":0, "bar_phase_confident":false, "bar_phase_share":0.4,
              "bar_model":"anchored-1", "bar_confident_pct":100 },
  "beats": [0.232, 0.813, ...],
  "chords": [ { "s":0, "e":2.415, "l":"N", "b":0 }, { "s":2.415, "e":4.087, "l":"A", "b":0 },
              { "s":23.777, "e":26.099, "l":"A", "c":1, "b":0 }, { "s":90.1, "e":92.2, "l":"D", "b":3, "a":1 } ],
  "strumming": { "note":"...", "source":"authored|level-default",
                 "patterns":[ {"id":"steady-down","name":"Start: steady downstrokes","counts":["1","2","3","4"],"strokes":["D","D","D","D"],"description":"..."} ] },
  "learning": { "skill_focus":"...", "prerequisites":"...", "sources":[{"title":"...","url":"..."}] },
  "provenance": { "pack":"automatic-first-ten-v1", "manifest_sha256":"...", "rhythm_sha256":"...", "practice_sha256":"...",
                  "learning_sha256":"...", "catalogue_sha256":"..." } }
```

- Times are seconds, rounded to 3 decimals.
- `l` is the **sounding** label after display corrections. `N` means no chord and `X` means unclear.
- `c:1` marks a corrected event (a label correction or alias).
- `t:1` marks an event whose start the timing fix moved by one beat (see "Timing fix"). The previous event ends at the same time.
- `b` and `a` are the chord's bar anchor (see "Bar model"): `b` is the bar phase while the chord is held, and `a:1` marks an approximate anchor. Chords outside the beat grid have no `b`.
- Shape (capo) and Core labels are computed at runtime by `lib/core.js`, using `lib/chords.js`.
- `chart.corrections` holds label corrections (`{id, start, end, from, to, note}`) and, when the timing fix moved anything, one entry `{id:"auto-timing", kind:"timing", count, start, end, note, moves:[{at, was, from, to, shift, agree}]}`. `at`/`was` are the new and raw start times, `from`/`to` the default-view labels (Core shapes at the song's capo), `shift` −1 (one beat earlier) or +1 (later), and `agree` how many repeats of the sequence sat where the change now sits (e.g. `"7/8"`). Details shows the note and the list of moves.
- When `beats_per_bar` is null (Wonderwall), the exporter writes 4 and `beats_per_bar_assumed: true`.
- `bar_phase` is the old song-wide heuristic: a chord-start residue vote, not a verified downbeat. Every native chord start that is not N or X and lies strictly inside the beat grid votes for `round(beatPosition(start)) mod beats_per_bar`. Ties keep the lowest residue. `bar_phase_confident` is true when there are at least 8 votes and the winning share is at least 0.7; an assumed meter is never confident. `bar_phase_share` records the share. Since the bar model, these fields are only the fallback for chords without `b` and a summary.
- `bar_confident_pct` is the share of chord beats under a confident (not approx) anchor.
- `strumming.source` is `authored` for the prepared songs' `practice.json` patterns and for patterns in an additions metadata file, and `level-default` when the song had none (see "Difficulty levels").
- `core_shapes` (index card chips) is exactly `difficulty.main_shapes`: the main shapes the level was computed on (see "Difficulty levels"), longest first, with no cap. Both come from one Arrangement profile (`tools/arrangement-profile.js`).
- A video entry carries `embeddable: false` only when that upload is known not to play in an embed. The app then starts on the first embeddable entry. The exporter writes only the analysed upload: alternate-video overrides were removed in #44 because no metadata used them. `playable_embed: false` in additions metadata therefore stops the export of that song until alternates return.

## Catalogue config (`strumalong/data/catalogue.json`)

The single place that says which recordings are in the app. The exporter reads nothing else to decide membership. Paths are relative to the repo root.

- `packs`: read in order.
  - `kind: "prepared"` (`automatic-first-ten-v1`): the pack `dir` plus its frozen `rhythm`, `practice` and `learning` files. `required: true`, so a missing pack stops the build.
  - `kind: "additions"`: the pack `dir`, its `rhythm.json` and an authored `metadata` file (`strumalong-additions-1` schema). `strumalong-additions-v1` uses `data/additions.json`. `strumalong-additions-v2` (pack `experiments/generated/strumalong-additions-v2/`, metadata `strumalong/data/additions-v2.json`) is configured now and skipped with a log line until both exist. An optional pack is skipped gracefully when missing or unusable; a required one stops the build.
- `exclude`: `{recording_id, title, reason}`. Excluded recordings are skipped before building, so they need no title or metadata.
- `level_overrides`: `{recording_id, level, reason}`. The song keeps `difficulty.computed_level` and shows `override_reason` in Details. A recording cannot be both excluded and overridden.
- `timing_fix_off` (optional): `{recording_id, reason}` turns the timing fix off for one song (see "Timing fix"). No song uses it yet.
- The exporter warns about an override or a `timing_fix_off` entry for a song that is not built, and about a manifest case without metadata.

Dropped on 25 October 2026 (founder feedback), still in their packs:

| Song | Reason |
|---|---|
| Radiohead – Creep | Needs barre chords (B, Cm) and the verse is picked, not strummed. |
| The Animals – The House of the Rising Sun | Arpeggiated picking, not strumming. |
| The White Stripes – Seven Nation Army | Riff song; no strummed chord part. |
| Nirvana – Come as You Are | Riff song; no strummed chord part. |
| The Beatles – Love Me Do | Harmonica-led; not a guitar song. |
| Green Day – Good Riddance (Time of Your Life) | The recorded guitar is picked, not strummed. |
| Lynyrd Skynyrd – Sweet Home Alabama | Picked riff, not strumming. |
| America – A Horse with No Name | The automatic chart cannot tell its two chords apart; needs a hand-checked chart. |
| Vance Joy – Riptide | Founder (25 Oct, second round): more a ukulele song than a guitar song. |

13 songs remain. With the riff songs gone, the exporter's riff mode, the learning-path, riff and "also available" groups, and the Come as You Are alternate-video constants were removed. Generic alternate videos (`alternates` in additions metadata) remained until #44 removed them as unused.

## Bar model

The problem: one song-wide `bar_phase` anchored every bar line and the strum count "1", even when the vote was weak. Good Riddance's chord changes fell on bar positions 0–3 at 32/21/25/15, so most bar lines landed one to three beats into a chord. The beat grid or the chart slips by a beat now and then (Wild Thing's last third), and one phase cannot follow that.

**Objective**, measured per song by `barMetrics` in `tools/build-songs.js` on exactly what `lib/core.js` draws:

- `on_bar_or_half`: % of chord changes (chord holds that are not N and not quick) whose first beat is a bar start or the half-bar.
- `weird`: drawn bar lines that fall 1 beat after a change or 1 beat before the next change, inside a hold of 3+ beats.
- `split`: short holds (2 to `beats_per_bar` beats) with a bar line inside them, such as "○○|○○" for a one-bar chord.
- `restarts`: bar starts that come less or more than a bar after the previous one, where the strum count restarts.
- `approx_pct`: % of chord beats under an approximate anchor.

**Model** (`barAnchors`, exporter): a Viterbi pass over the chord changes of the default-view timeline (Core merges; they do not depend on the capo view). Each change takes one of the `beats_per_bar` phases or **hold-relative** (the change starts a bar, with further lines every `beats_per_bar` beats inside long holds). The costs live in `BAR_COST`:

- 1 per weird line and 1 per split hold.
- 0.5 per change off the bar and half-bar. 0.1 per change on the half-bar, or 0.5 if a hold of a bar or longer starts there.
- 1.75 per phase switch (a local slip) and 2.5 to enter or leave hold-relative.
- 0.8 per hold-relative restart after a hold that is not a whole number of bars, and 0.1 per hold-relative hold, so a steady phase wins whenever it draws the same bars.

This gives three cases:

- One run of one phase is the old **global** phase. Five songs (Zombie, Have You Ever Seen the Rain, Brown Eyed Girl, Bad Moon Rising and Free Fallin') get exactly that.
- Several runs are **local** phases that follow a slip.
- Hold-relative bars are the fallback where no phase fits. No current song needs them; a three-beat song on a four-beat grid does.

A phase run is **confident** when it has at least 8 changes, at least 80% of them on a bar or half-bar, at least as many on the bar as on the half-bar, and the meter is not assumed. Hold-relative and unconfident runs are approx. N, X and quick holds take the anchor of the run they sit in; in a hold-relative run a quick hold takes the next hold's anchor, as a pickup.

**Storage and consumption.** The exporter writes `b`/`a` on each native chord (`applyBarAnchors`). Natives inside one Core-merged hold share it, so Full view draws the same bars as Simple view. `lib/core.js` builds a per-beat anchor map: each grid beat takes the anchor of the chord whose dots own it, `round(startBeat)` to `round(endBeat) − 1`. Beats no chord owns take the nearest owned anchor, earlier first. Bar lines, NEXT's bar-start border and the strum count all read this one map, so a drawn bar line is always where the count reads 1, and the reverse holds too. A song without `b` behaves exactly as before.

**Results** on 25 October 2026 (before = song-wide `bar_phase`, after = anchored):

| Song | changes on bar/half % | weird | split | restarts | approx % |
|---|---|---|---|---|---|
| Wild Thing | 64.5 → 85.5 | 10 → 0 | 13 → 0 | 0 → 1 | 100 → 0 |
| Zombie | 92.6 → 92.6 | 6 → 6 | 0 → 0 | 0 → 0 | 0 → 0 |
| Take Me Home, Country Roads | 91.7 → 98.3 | 4 → 0 | 12 → 0 | 0 → 2 | 100 → 8.9 |
| Knockin' on Heaven's Door | 95.3 → 96.9 | 2 → 1 | 2 → 1 | 0 → 0 | 100 → 1.8 |
| Bad Moon Rising | 100 → 100 | 2 → 2 | 0 → 0 | 0 → 0 | 0 → 0 |
| Riptide | 69.8 → 90.6 | 20 → 4 | 25 → 1 | 0 → 4 | 100 → 4.8 |
| Free Fallin' | 58.3 → 58.3 | 12 → 12 | 0 → 0 | 0 → 0 | 100 → 100 |
| Wonderwall | 94.4 → 95.8 | 5 → 4 | 5 → 2 | 0 → 3 | 100 → 100 |
| Brown Eyed Girl | 98.1 → 98.1 | 2 → 2 | 0 → 0 | 0 → 0 | 0 → 0 |
| Twist and Shout | 94 → 96 | 6 → 2 | 2 → 0 | 0 → 3 | 100 → 7.8 |
| Island in the Sun | 96.4 → 97.6 | 1 → 0 | 3 → 1 | 0 → 2 | 100 → 4.3 |
| Have You Ever Seen the Rain | 100 → 100 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| Don't Look Back in Anger | 94.3 → 95 | 4 → 3 | 2 → 1 | 0 → 1 | 100 → 0.8 |
| *Good Riddance (dropped)* | 60.6 → 85.1 | 13 → 5 | 22 → 5 | 0 → 4 | 100 → 28.6 |

Across the 13 songs, weird lines fall from 74 to 36 and split holds from 64 to 6. The remaining lines are mostly in the chart, not the bars:

- **Zombie:** a chord detected one beat late after a correct bar line. The timing fix now moves it (and three more Zombie changes) onto the other repeats: 6 → 2 weird lines.
- **Free Fallin':** D is held 4n+1 beats before G arrives on beat 2. That is the song's push, and every phase draws it the same way.
- **Wonderwall:** 2/4 bars. It stays approx because its meter is assumed.

Many songs lose the "approx bars" label because a steady phase now fits changes on the bar or the half-bar, where the old rule needed 70% on one exact residue. The exporter prints this table on every build.

## Timing fix

The problem (founder, 25 October 2026): in Zombie one Em → C change came a beat late, so Em showed 5 beats and C 3, while the other seven times the band plays G Em C G each chord gets 4. CREMA places most changes well, but now and then one lands a beat early or late. Pop songs repeat their chord sequences with the same bar placement, so the repeats are the check: a change that sits exactly one beat from where the other repeats of the same sequence sit is moved by one beat to match them.

It is a **display-level** correction in the exporter (`applyTimingFix` in `tools/build-songs.js`). Its grouping and judgement are the *drawn timing* measure of `lib/repeat-timing.js`, which also builds the `auto-timing` entry; the catalogue checker uses the same module's *played timing* measure ([ADR 0001](adr/0001-repeat-timing-two-measures.md)). The raw chart (`primary.json`) is unchanged, labels never change, and every move is recorded. It runs before the bar anchors and the difficulty, so both use the fixed chart.

**What is compared.**

- A *change* is the start of a default-view hold (Core shapes at the song's capo, so `Em`/`Em7` blips do not split a sequence) between two in-grid chord holds that are not N, X or quick. Moves never cross N or X and never touch chords outside the beat grid.
- Its *group* is its four-label context: previous, from, to and next label. "G Em C G" is one group; "Em C Em C" is another.
- Its *position* is the beat of the change within the bar under a provisional phase: the bar-model Viterbi (`barAnchors`) run on the current chart, ignoring any stored `b`/`a`. A lone wrong change cannot pull a phase run onto itself, because two phase switches cost more than one off-bar change. A phase run that starts at a change may be a beat-grid slip, so such a change is never moved.
- The hold lengths (beats each of the two chords is held) are a second, phase-free check. Repeats that agree on position also agree on lengths, so a phase artefact alone can never justify a move.

**The rule.** A change moves by one beat only when all of these hold (`TIMING_FIX`):

1. Its group has at least 4 repeats. The most common position holds at least 60% of them and at least 3 repeats.
2. The change is exactly one beat from that position. Two beats or more is treated as a different arrangement.
3. Both holds sit in the same phase run.
4. Under a confident bar phase, the move does not take a change off the bar or half-bar line. Where the bars are a guess (approx bars), the repeats alone decide. This keeps Wild Thing's E → D pushes as they are.
5. After the move, neither hold's length is further from the majority's median length, the sum is closer, and it is within 1 beat in total. Both holds, and the native chord that gets shorter, stay at least 1 beat long.
6. Neither native chord carries a correction or alias (`c:1`), and the boundary has not been moved before (`t:1`). Each boundary moves at most once.

The moved change takes the majority repeats' median offset from their beat, so it looks like the repeats it now matches (across the catalogue, the median chord start is 93 ms before its beat). That offset is clamped so the change still rounds to the target beat and moves at most one beat in time. Many moves are a small time shift for a change that sat almost halfway between two beats: for example 0.16 beat in Save Tonight, which flips how it rounds. Passes repeat until nothing moves; neighbouring boundaries wait for the next pass. The fix is therefore **idempotent**: run on its own output, it moves nothing.

**Record.** Moved chords carry `t:1`. `chart.corrections` gets one `auto-timing` entry with the note "N chord changes moved by one beat to match the other repeats of the same sequence (automatic; raw chart unchanged)" and the list of moves (see "Data schema"). Details shows that line with each move's time, labels and direction. The cue UI is unchanged. A song can opt out with `timing_fix_off` in the catalogue config.

**Results** on 25 October 2026. Consistent is the % of changes in repeated sequences (3+ repeats) at their group's usual position, measured before and after under one reference phase (the unfixed chart's). Weird, split and on bar+half are the anchored-bar metrics ("Bar model") without → with the fix. Songs with no moves are left out; none of them changed.

| Song | moved | consistent % | weird | split | on bar+half % |
|---|---|---|---|---|---|
| Zombie | 4 | 94.5 → 100 | 6 → 2 | 0 → 0 | 92.6 → 96.8 |
| Sit Down | 1 | 93.4 → 95.1 | 3 → 2 | 0 → 0 | 95.5 → 97 |
| Wild Thing | 1 | 87.9 → 89.4 | 0 → 0 | 0 → 0 | 85.5 → 86.8 |
| What's Up? | 1 | 96.6 → 98.3 | 2 → 1 | 0 → 0 | 96.7 → 98.3 |
| Budapest | 4 | 89.4 → 97.9 | 6 → 2 | 0 → 0 | 89.6 → 97.9 |
| Lucky Man | 2 | 98 → 100 | 2 → 0 | 0 → 0 | 98.2 → 100 |
| Knockin' on Heaven's Door | 1 | 98.2 → 100 | 1 → 0 | 1 → 0 | 96.9 → 98.4 |
| Heart of Gold | 1 | 98.7 → 100 | 4 → 4 | 0 → 0 | 87.8 → 88.9 |
| Free Fallin' | 9 | 92.2 → 100 | 12 → 12 | 0 → 0 | 58.3 → 51.2 |
| Wagon Wheel | 6 | 94.9 → 100 | 7 → 1 | 0 → 0 | 94.1 → 99.2 |
| Brown Eyed Girl | 2 | 97.8 → 100 | 2 → 0 | 0 → 0 | 98.1 → 100 |
| I'm Yours | 1 | 98.1 → 100 | 5 → 4 | 1 → 1 | 97.4 → 98.7 |
| Breakfast at Tiffany's | 4 | 89.3 → 92.1 | 9 → 7 | 2 → 0 | 67.9 → 70.4 |
| Twist and Shout | 2 | 90.8 → 92.9 | 2 → 0 | 0 → 0 | 96 → 98 |
| Ho Hey | 1 | 94.7 → 100 | 3 → 3 | 1 → 1 | 85.7 → 88.6 |
| Don't Look Back in Anger | 2 | 96.5 → 98.3 | 3 → 2 | 1 → 1 | 95 → 96.5 |
| Learning to Fly | 15 | 81.6 → 88.7 | 1 → 1 | 1 → 1 | 68.2 → 61.4 |
| Save Tonight | 8 | 83.7 → 87.7 | 0 → 0 | 1 → 1 | 93.5 → 97.2 |
| Torn | 1 | 98.2 → 100 | 1 → 0 | 0 → 0 | 98.8 → 100 |

There are 66 moves in 19 songs. Weird lines fall from 69 to 41 over these songs, split holds from 8 to 5, and no song gains a weird line, a split hold or approx bars. The exception is the bar fit of two approx-bar songs with pushes: Free Fallin' and Learning to Fly. Most of their repeats round a change that falls about halfway between beats onto the off-beat, and the fix makes the rest agree. Weird lines and approx bars stay the same.

**Zombie, for spot-checking by ear** (Simple view labels; times in the app's m:ss):

| Time | Change | Move | Repeats agreeing | Holds before → after |
|---|---|---|---|---|
| 2:13 | Em → C | one beat earlier (133.933 → 133.214 s) | 7 of 8 "G Em C G" | Em 5 + C 3 → 4 + 4 |
| 3:58 | C → Em | one beat later (238.237 → 238.510 s) | 3 of 5 "Em C Em C" | C 3 + Em 5 → 4 + 4 |
| 4:14 | C → Em | one beat later (254.212 → 254.857 s) | 3 of 5 "Em C Em C" | C 3 + Em 5 → 4 + 4 |
| 4:36 | G → Em | one beat later (276.689 → 276.910 s) | 7 of 8 "C G Em C" | G 7 + Em 5 → 8 + 4 |

After the fix, every Zombie change in a repeated sequence sits with its repeats. Four changes remain off the bar line, each left alone:

- **0:07 G (intro)** starts a beat before the bar after a 10-beat Em. This sequence is played only once, so there is no repeat to compare with.
- **3:35 and 4:19 D** fall on the half-bar (C 2 + D 2). Both repeats agree, and the half-bar is a normal place for a change.
- **4:41 D and 4:46 Em** (C 3, D 7, Em 6 near the end) belong to a sequence played only once, so there is no repeat to compare with.

Print any song's moves and left-alone changes with reasons using `node strumalong/tools/build-songs.js --timing-detail=<id fragment>`. The build report always lists the per-song table and every move.

**Limitations.**

- The fix trusts the majority. If most repeats of a sequence are wrong the same way, the right one is moved to match them. The 3-of-5 groups (Zombie's "Em C Em C", Lucky Man's "A G A G") are the weakest evidence.
- It only sees label sequences. A change that is a beat off in a sequence played fewer than 4 times, or two beats off, is not touched.
- For pushes (a change halfway between beats), it makes the rounding consistent but does not choose the musically better side.

## Difficulty levels

Lead decision, 25 October 2026. Shapes are what the player frets: Core shapes at the song's default view (capo shapes, Simple).

| Tier | Shapes |
|---|---|
| T1 | A, D, E, Em, Am and A7, D7, E7, Am7, Em7, Asus2, Asus4, Dsus2, Dsus4, Esus4 |
| T2 | G, C, Dm, G7, C7, B7, Cadd9, Cmaj7, Fmaj7, Dm7, G/B, D/F#, C/G |
| T3 | F (incl. mini-F), Bm, Bm7, F#m: first barre-type shapes |
| T4 | every other shape (B, Bb, Cm, C#m, G#m, Gm, F#, Eb, Ab, Db, Fm, dim …) |

Other slash shapes take their root shape's tier, because the diagram omits the bass note.

- **Main shapes** are Core shapes covering at least 4% of chord time (slash shapes at least 10%), ignoring N, X and blips (holds under 0.75 beat). They are also the card chips, so a card always shows the shapes its level counts (one rule since 27 October 2026, [#41](https://github.com/dcromp/music-os/issues/41); before, the card used 3% with blips and at most 6 chips, and 7 of 43 cards differed).
- **Changes per minute** counts label changes between consecutive non-blip chord holds, but not across N or X, per minute of non-blip chord time.
- **Median hold** is in beats per non-blip chord hold.

| Level | Rule (`arrangementProfile` in `tools/arrangement-profile.js`) |
|---|---|
| 5 · Barre chords | any T4 main shape |
| 4 · First barre (F / Bm) | any T3 main shape, no T4 |
| 3 · More changes | all ≤ T2 with 5+ main shapes; or an L1/L2 song with quick changes (median hold ≤ 2 beats at ≥ 120 BPM, or ≥ 40 changes/min) or an authored `needs_syncopation: true` |
| 2 · Open chords | all ≤ T2 with ≤ 4 main shapes, or all T1 with 4+ |
| 1 · First chords | all T1 with ≤ 3 main shapes |

`tier_reason` states the main shapes, the hardest tier and the pace. A `level_overrides` entry in the catalogue config replaces the level and keeps the computed one.

**Expected level and shapes.** An additions metadata entry's `expected_level` and `expected_shapes` are editorial research drafts. The exporter compares them with the built profile (after any override) and reports only: a level mismatch is a `WARN` line (counted, never failing the build), and shape-set mismatches are listed under "Expected shapes" in the build report. `chart_check` is research bookkeeping and is not read.

**Label aliases (25 Oct 2026).** An additions metadata entry may carry `label_aliases: {map: {chartLabel: displayLabel}, note}` when the automatic chart names a chord differently from the grip players use. It was built for A Horse with No Name (chart `F#m7`, `Dmaj7/F#`, `Dmaj7`, `D`, `D/F#` → the two-finger `D6add9/F#` grip `200200`, a tier-1 shape), but that song was then excluded: its chart misses most of the bar-by-bar changes. Aliased events carry `c:1`, and each alias is listed in `chart.corrections` with the span of the events it relabels. Timings never change.

**Zero-beat holds.** A hold that owns no grid beat after rounding (for example 0.87 beat from 30.52 to 31.39) is shown as a quick change, so neighbouring holds still hand over beats exactly.

Default practice patterns, used only for songs with no authored patterns (an additions entry without `strumming.patterns`):

| Level | Start | Next |
|---|---|---|
| 1 | steady downstrokes | down-up eighths |
| 2 | down-up eighths | D — D U — U D U |
| 3 | D — D U — U D U | let count 3 ring (D U D U — U D U) |
| 4, 5 | D — D U — U D U | anchor beats 1 and 3 (D — D U D — D U) |

A meter other than 4 beats per bar gets steady downstrokes and down-up eighths at any level. Prepared songs keep their `practice.json` patterns, and the v1 additions keep their authored ones.

Levels on 25 October 2026:

| Level | Song (order) | Main shapes | Changes/min | Why |
|---|---|---|---|---|
| 1 | Wild Thing | A E D | 30.2 | Override: all T1, but 30.2/min reaches the quick line (computed L3). Kept first, as in the original learning path. |
| 2 | Zombie | Em G C D | 18.5 | open, 4 shapes |
| 2 | Take Me Home, Country Roads (capo 2) | G D C Em | 19.1 | open, 4 shapes |
| 2 | Knockin' on Heaven's Door | G D Am C | 26.1 | open, 4 shapes |
| 2 | Bad Moon Rising | D G A | 28.7 | open, 3 shapes |
| 2 | Riptide (capo 1) | C Am G | 29.0 | open, 3 shapes (F is 3.1%, not a main shape) |
| 3 | Free Fallin' (capo 3) | D G A | 30.7 | quick changes |
| 3 | Wonderwall (capo 2) | Em G C D | 34.0 | quick changes |
| 3 | Brown Eyed Girl | G D C | 34.2 | quick changes (~152 BPM) |
| 3 | Twist and Shout | A D G | 40.2 | quick changes; median hold 2 beats at ~123 BPM |
| 3 | Island in the Sun | D G Em Am | 51.4 | quick changes |
| 4 | Have You Ever Seen the Rain | C G F Am | 18.2 | F (T3) |
| 4 | Don't Look Back in Anger | C G F Am Em | 29.8 | F (T3) |

Level 5 is empty now; Creep would have been Level 5 (B, Cm).

## `lib/chords.js` API: chord shape vocabulary (pure, unit-tested)

The one implementation of chord-label maths for the app, the exporter and the catalogue checks. Its pitch-class and quality tables are internal. The frozen Mac review player (`experiments/review/app.js`) keeps its own copy as evidence. On 27 October `shapeForCapo` and `coreLabel` matched its `transposePracticeLabel` and `coreChordLabel` on 6,462 labels at every capo from 0 to 12 ([#45](https://github.com/dcromp/music-os/issues/45)).

- `parse(label)` returns `{root, rootPc, quality, bass, bassPc}` or null for N, X, junk and an unreadable bass. quality is the suffix as written, without a Harte `:`. A degree bass (`G/b7`) gets its pitch class.
- `shapeForCapo(sounding, capo)` returns the chord shape fretted with that capo (`A`, 2 → `G`). A flat root keeps flat spelling. A note bass moves; a degree bass is kept. It throws for a capo outside 0–12.
- `soundingForCapo(shape, capo)` is the reverse, with sharp spelling (`G/B`, 2 → `A/C#`). The catalogue checks use it to turn teaching shapes into sounding chords.
- `coreLabel(label)` removes known extensions: m7 → m, maj7/7/add9 → major, 7sus4 → sus4. Suspensions and unknown qualities stay unchanged.
- `normalize(label)` maps a label onto one of `QUALITIES` for diagrams (`Am9` → `m7`, `simplified: true`). It also accepts Unicode sharp/flat signs and `C6/9`.
- `noteName(pc)` returns the sharp spelling of a pitch class.

## `lib/core.js` API (pure, unit-tested)

Ported helpers from `experiments/review/app.js` keep their names and behaviour. Each carries a comment naming its source line.

- `shapeLabel(sounding, {capo, view:'shapes'|'sounding', quality:'core'|'full'})`
- `buildTimeline(song, opts)` returns display events `{s,e,label,full,sounding,c}`. Adjacent equal labels are merged after transforms. Merges never bridge N or X.
- `chordIndexAt(events, t)` is a binary search that returns the index, or -1.
- `beatPosition(beats, t)` returns a fractional beat index or null, as in the Mac player.
- `cueAt(timeline, song, t)` returns:
  `{ now:{label, idx, startBeat, beats, dots:[{state:'past'|'active'|'future'}], barBefore:[dotIndex...], seconds, remaining}, next:{...}|null, beatsUntilChange:int|null, secondsUntilChange, inBeatGrid:bool }`
  - **Dot count** is `round(endBeat) − round(startBeat)`, with a minimum of 1, so each grid beat belongs to exactly one hold.
  - **Short spans:** if the span is under 0.75 beat, set a `quick:true` flag and show one dot.
  - **Long spans:** cap at `2*beats_per_bar` dots and set `more:n` for the rest. The UI shows something like "+4".
  - **Bar lines:** place one before dot k when beat `B = round(startBeat)+k` is a bar start under the per-beat anchor, `(B - phase(B)) mod bpb == 0`, and k>0 (see "Bar model"). The same anchor drives the strum count, so a bar line is always where the strum count reads 1. When the anchor at the hold's first beat is approximate, the part has `approx: true`, NEXT gets no solid bar-start border (`barStart: null`), and `cue.approxBars` (from the anchor at the current beat) makes the UI show "approx bars". A song without `b` fields uses `bar_phase` everywhere, approximate unless `bar_phase_confident`.
  - **Outside the beat grid:** fall back to seconds, with `dots` empty and `seconds` set.
- `strumStep(song, pattern, t)` returns the index into `pattern.strokes` at time t, or null outside the grid.
  - `stepsPerBeat = pattern.counts.length / bpb`
  - `pos = ((beatFloat - phase(floor(beatFloat))) mod bpb + bpb) mod bpb`, with `phase` the per-beat anchor
  - `step = floor(pos*stepsPerBeat)`
- `barAnchorAt(song, beat)` returns `{phase, approx, bar, half, anchored}` for an integer grid beat (a fractional one uses its floor). `bar` means the strum count reads 1 there. The per-beat map is cached per song object and rebuilt when `song.chords`, `song.beats` or the rhythm fields change identity or value.
- `cueTime(playerSeconds, offsetSeconds, nudgeMs, latencyMs, rate)` returns `player + offset + nudge/1000 − latency/1000 × rate`. Latency is wall-clock delay, so at 0.5× it covers half as much media time. The nudge and offset are media time and are not scaled. A rate that is not a positive number counts as 1.
- `formatTime(s)` returns "m:ss".

## `lib/shapes.js` API

- `getShape(label)` returns `{name, frets:[6 ints|-1 low E→high e], fingers:[6 ints|0], baseFret, barre:{fret,from,to}|null, note}` or null.
  - Slash chords fall back to their root shape with `note:"bass note omitted"`, unless an explicit grip exists (G/B, D/F#, C/G).
  - Coverage must include every Core and Full shape label that appears in any built song, at its default capo view. Unknown labels return null, and the UI then shows the name only.
- `renderShapeSVG(shape, {size})` returns an accessible SVG string with `role="img"` and an `aria-label` that names the chord and frets. It has 6 strings and 5 frets, × and ○ markers, a barre bar, a base-fret label, and uses `currentColor` so it themes.

## `lib/session.js` API (practice session)

This module takes playback events in and gives cue time, the resume point and saved settings out. It has no DOM, timers or network access. It reaches the outside world only through two adapters. The tests in `test/session.test.js` drive it with a fake player and a Map.

- **Storage adapter** `{getItem, setItem}`: `localStorage` in the app, `mapStorage(new Map())` in tests. Every access is guarded.
- **Player adapter** `{currentTime, duration, playbackRate, availableRates, seekTo, cue, play, pause, setRate, destroy}`: `youTubeAdapter(YT.Player)` in `app.js`, a fake in tests. Every call is guarded, and a throwing player keeps the last known value.
- `createStore(storage)` owns the v1 keys and JSON (see **Persistence**). It provides:
  - `settings()`, a sanitised, frozen value
  - `setQuality`, `setView`, `setDiagrams`, `setPattern(songId, id)`
  - `latency()` / `setLatency(ms)`, clamped to ±1000
  - `nudge(videoId)` / `setNudge(videoId, ms)`, clamped to ±30000
  - `saveLast(id, t)`
  - `resumePoint(songs)`, the library chip: `{song, t}`, where `t` is 0 under 5 s or within 5 s of the end
  - `favourites()` / `toggleFavourite(id)` (returns the new state), in the order they were added
  - `plays()` / `recordPlay(id)` (returns the new count), the finished-play count per song
- `createSession({song, store, resume, now})`, one per song page:
  - **Events in:** `attach(player)`, `playerReady()`, `stateChange(code)`, `rateChange(r)`, `error(code)`. `error` returns `{action:"switch"|"fail"|"retry"}`; a fail carries `reason` `referrer`, `unavailable` or `no-embed`.
  - **Transport:** `play`, `pause`, `seek`, `setRate`, `retry`.
  - **Learner settings:** `nudgeBy`, `resetNudge`, `setQuality`, `setView`, `setPattern`.
  - **Exit:** `saveLast`, `leave`.
  - **`tick()`** returns `{pt, t, cue}`. It holds a resumed start until the first play, runs the ad guard while playing, and saves the last-played position every 5 s.
  - **Read-only fields:** `video`, `state`, `played`, `ready`, `failed`, `ad`, `rate`, `pt`, `timeline`, `patternId`, `nudgeMs`, `controllable`, `playing`. `epoch` increments whenever cached cue rendering is stale: a new timeline, rate, video or failure.

## `lib/library.js` API (Jukebox journey)

Pure rules over the catalogue summaries, tested in `test/library.test.js`.

- `search(songs, query)`: songs whose title or artist contains every query word, ignoring case, accents and apostrophes. An empty query returns `[]`.
- `shelves(catalogue, favouriteIds)`: `[{id, title, note, songs}]`, with favourites first, then one shelf per level group in catalogue order, then "Other songs". Empty shelves are dropped.
- `similar(songs, song, limit = 5)`: songs that share at least one core shape and are at most one level harder. Ordered by most shared shapes, then fewest new shapes, then easier, then catalogue order.
- `surprise(songs, {lastId, plays, rng})`: a random song no harder than the hardest level played (at least level 2), avoiding the song just played.

## UI

The end-user journey is **Jukebox** (founder's choice from the journey prototype, 27 October 2026, #53; prototype on branch `prototype/strumalong-journey`). Find a song fast, see a short get-ready sheet, play, then get offered "another like this". Strum Along supports lessons taken elsewhere; it does not teach.

- **Library (`#/`).**
  - The header reads "Strum Along · music-os", with a **🎲 Surprise me** button (see `surprise`, which opens that song's get-ready sheet), the line "Provisional automatic chord charts. For personal practice." and a **search** box (title or artist). While the box has text, matching cards replace the shelves. The query is kept while moving between pages.
  - A last-played song gets a resume chip ("Resume … at m:ss", or "Play again: …"). It opens the player directly.
  - **Shelves** scroll horizontally. "★ Your favourites" comes first when there are any, then one shelf per level ("Level 1 · First chords" … "Level 5 · Barre chords") with its one-line explanation, easiest first. Each card shows the title, artist and main shapes as chips, plus a capo badge and the "timing unchecked" / "alternate video" badge where they apply. Cards open the get-ready sheet.
- **Get ready (`#/ready/<id>`).** The same top bar as the song page. ~BPM (or "No capo"), the setup note, diagrams of the main shapes ("You'll need"), the first practice pattern as a stroke grid with counts (labelled a practice suggestion), a big **▶ Play** link to `#/song/<id>` and a ☆/★ Favourite toggle. The YouTube player only loads on the song page, so the learner presses Play there as well.
- **After the song.** When the video ends, a panel opens at the top of the cue column. It shows "Nice one", the play count on this phone, **↻ Again** (restart and play), Favourite, Surprise me, and up to five "Another like this" cards (`similar`). Playing again hides it. Nothing is placed over the player.
- **Song (`#/song/<id>`), portrait, top to bottom:**
  1. A top bar with a back link, the title, and the capo, level ("Level 2", titled with its label) and provisional badges.
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
  7. **Details** (collapsed): setup note, level with its reason (or the override reason), skill focus, sources (links), chart status, beats and bars (how much of the song shows approx bars), corrections (label corrections, and the timing fix's line with each moved change), the strumming note, the video's uploader, and "Open on YouTube".
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
- **Persistence.** The localStorage keys are `music-os-strumalong-v1:` + `settings`, `offset:<video_id>`, `last` (`{id, t}`), `latency` (a global ms offset for Bluetooth), `favourites` (an array of song ids) and `plays` (`{id: count}`). Wrap every access in try/catch.

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
| Green Day – Good Riddance (Time of Your Life) | excluded 25 Oct: picked |
| Oasis – Don't Look Back in Anger | |
| Creedence Clearwater Revival – Have You Ever Seen the Rain | |
| Creedence Clearwater Revival – Bad Moon Rising | |
| Tom Petty – Free Fallin' | capo 3 shapes |
| Weezer – Island in the Sun | |
| John Denver – Take Me Home, Country Roads | capo 2 shapes |
| Lynyrd Skynyrd – Sweet Home Alabama | excluded 25 Oct: picked riff |
| Vance Joy – Riptide | capo 1 shapes |
| *Fallbacks:* The Beatles – Let It Be; Counting Crows – Mr. Jones; Blind Melon – No Rain; The Lumineers – Ho Hey; R.E.M. – Losing My Religion | |

Steps:

1. Import with `experiments/analysis/youtube_import.py`. Recording IDs follow `<artist>-<song>-youtube-20261024`. The source-use note is "Requested local founder strum-along app, 24 Oct 2026; personal testing; commercial clearance not established".
2. Run CREMA with the **unchanged** settings used for `automatic-first-ten-v1`.
3. Run the `rhythm_grid.py` pulse grid with a source-informed tempo prior. The prior goes in a new config, `experiments/fixtures/rhythm-strumalong-additions-v1.json`.
4. Write a new gitignored pack at `experiments/generated/strumalong-additions-v1/` that mirrors the `automatic-first-ten-v1` manifest structure, plus its own `rhythm.json`.
5. Authored capo, setup notes and two practice patterns per song go in `strumalong/data/additions.json`. These are suggestions and are labelled as such.

A **v2 pack** follows the same steps into `experiments/generated/strumalong-additions-v2/`, with metadata in `strumalong/data/additions-v2.json` (same `strumalong-additions-1` schema). Song choice is researched in `docs/STRUMALONG_SONG_RESEARCH.md`, which is another workstream. In the metadata, `strumming.patterns` is optional: without it the song gets its level's default patterns. `needs_syncopation: true` marks a song whose strum needs syncopation, which moves an L1/L2 song to L3. `catalogue.json` already lists the pack, and the exporter builds it once its manifest, `rhythm.json` and metadata exist. Exclude any import that turns out picked or riff-based in `catalogue.json` with a reason.

## Verification

- `node strumalong/test/run.js` passes. Besides unit tests, it checks on the built songs that every beat's count 1 matches a bar start in both directions, and that the anchored bars never add weird or split lines over the song-wide phase. It also checks that the overall count is at least halved, and that the anchors can be rebuilt from the chart and grid.
  - For the timing fix, it checks that re-running it on the unfixed chart (rebuilt from each move's `was`) gives exactly the recorded moves and the shipped chords, with the same labels. It checks that re-running it on the shipped chords moves nothing, and that every move is one drawn beat and at most one beat in time. Neither neighbouring hold may drop under a beat. Repeats must be at least as consistent, with no added weird or split lines or approx bars. Zombie's 2:13 Em → C must be moved.
- `node strumalong/tools/build-songs.js --check` prints CHECK OK. `scripts/deploy-strumalong.sh` runs it after the tests and stops if `songs/` is stale.
- The existing `node experiments/review/test.js` still reports 96 checks.
- The frozen-pin check passes: `.venv-analysis/bin/python -B experiments/analysis/workflow_check.py --policy experiments/fixtures/selected-workflow-player-v5.json`.
- A browser check at `http://localhost:<port>/` in a 390×844 viewport covers the library, a song page, YouTube load and play, cues advancing, and the error fallback.
- After deployment, the Pages URL is checked the same way.
- Behaviour on the iPhone itself (Safari and Home Screen) is the founder's check. Record what is and isn't verified.
