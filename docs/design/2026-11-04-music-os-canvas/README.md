# Music OS design iteration, 4 November 2026

iPhone (390×844) design canvas for Music OS: a music learning and creativity aide with two modes, **Jukebox** and **Bandmaker**. Made in a Claude Design canvas: https://claude.ai/artifact/SMmZXxNaWjSm2NJbeLZHu6 (private to the founder).

These are design comps, not production code. The app's existing code informed the features only; layout and visuals are new. The `.dc.html` files are Claude Design component files and need the canvas runtime (`support.js`) to render. `canvas.json` holds the layout and sticky notes.

## Look

Dark stage ground (`#14110E`), amber `#F2A93B` for Jukebox, teal `#5CC8B5` for Bandmaker, so each mode keeps one colour. Type: Bricolage Grotesque (display), Inter (body), JetBrains Mono (chords, counts).

## Screens

| File | Screen |
|---|---|
| `Main.dc.html` | Home: Jukebox card, Bandmaker card (New song / My songs), Connect guitar |
| `Jukebox-Library.dc.html` | Surprise me, search, All/Rock/Pop, level, themed shelves; songs open straight into playing |
| `Jukebox-Play.dc.html` | Play along with setup built in; one relevant line under the video ("Three shapes you know" or "One new shape here: D"), tap for the breakdown. `firstVisit` tweak shows the new-shape state |
| `Jukebox-Breakdown.dc.html` | Song breakdown opened from the bar: setup, shape diagrams, chord loop, strum patterns |
| `Bandmaker-Songs.dc.html` | My songs list, with which band members have a part |
| `Bandmaker-Feel.dc.html` | New song step 1: feel |
| `Bandmaker-Key.dc.html` | Step 2: key (interactive: major/minor, guitar-friendly keys ranked by easy shapes, the 7 notes, chords you get) |
| `Bandmaker-Foundation.dc.html` | Step 3: chords in the key and suggested sequences |
| `Bandmaker-Bass.dc.html` | Bass member: four bass-line styles and a playable tab following the chords |

## Decisions in this iteration

- **Song setup merged into Play along.** For easy or known songs nobody wants to click through setup each time. The breakdown is an optional press and never opens on its own.
- **No separate Bandmaker start screen.** Home already offers New song and My songs.
- **Band member selector (from direction A) on top of every Bandmaker screen**, combined with the **guided foundation (from direction B)**: feel, key, chords, song. A new song starts on Rhythm; other members are dimmed until there are chords, then follow them. Direction C (song map) was dropped.
- **Key step matters** both for learning what keys are and for setting the song's feel foundation.
- **Bass part kept** as designed.
- **Drums** will be largely AI, GarageBand-style: auto fills, or choose where fills go. Not designed yet.

## Open

- Chords step (step 3) is still drawn for G major only; it should follow the chosen key.
- Step 4 (song: sections and lengths) is not drawn.
- Should a Jukebox song end with a nudge to try its chords in Bandmaker? Where does "Another like this" go now that setup is merged?
