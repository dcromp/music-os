# App structure and Band mode

Agreed with the founder on 29 October 2026. Tracking: [decision map #64](https://github.com/dcromp/music-os/issues/64) and [prototype #73](https://github.com/dcromp/music-os/issues/73).

## Home

- **Jukebox:** jump into recommended song choices.
- **Band Mode:** open a previously saved project or create a new project.

## Band project

Use GarageBand's instrument-screen navigation as the reference, with swiping between **band members**. Each member has its own workspace within the project. Members are freely accessible rather than mandatory sequential steps:

**Singer · Rhythm guitarist · Drummer · Bassist · Lead guitarist · Producer**

**Singer** merges songwriting, lyrics and vocals: shaping the song, writing words, developing the melody and choosing or recording the voice. Songwriter and Lyricist are no longer separate members. Drummer and Bassist have separate workspaces.

A persistent **Connect guitar** button at the bottom opens shared setup for choosing the input, checking that audio is coming through and tuning. This setup serves the whole project.

## Rhythm guitar direction

After reviewing the new A/B/C layouts on 29 October, the founder chose the rhythm-only timeline from B combined with A/C's focused workspace and guidance. Rhythm guitar is the most important and complex part of the app: it is where the player builds the song's musical foundation.

- Set the length of sections, including the number of bars per verse.
- Get help choosing chord sequences to try and record.
- Record guitar, move clips with drag and drop, and trim audio.
- Keep raw audio available while adding, removing or bypassing effects to try different pedals.
- Provide a metronome.
- Explore optional recording that starts when the player begins playing and stops automatically. Trigger thresholds, treatment of intentional rests and the stopping rule remain open design questions.

Singer retains songwriting, lyrics and vocals. Rhythm's section-length and chord tools build the musical foundation shared by the band.

## Prototype evidence

This decision supersedes the earlier eight-step navigation and setup embedded in the recording step. The new prototype is on `codex/band-member-prototype`, in `strumalong/prototype-bandmode.html`. A/B/C are retained as comparisons; the combined rhythm workspace is **D** (distinct from the earlier Claude artifact's layout D).

Local preview: http://localhost:8094/prototype-bandmode.html?variant=D&member=rhythm . It is a throwaway prototype, not a production deployment. Takes, interface connection and effects remain simulated; the metronome generates sound. The UI has section lengths, chord suggestions, clip dragging/trimming, pedal controls and a simulated recording state flow. Desktop interaction checks pass; real iPhone/audio behaviour remains unverified.

Next: founder review of the combined rhythm workspace, especially whether the Foundation / Record / Edit / Pedals tabs make its scope manageable. This tab split and the prototype's two-second silence proposal are not yet founder-approved decisions.

## Chord-helper reference and prototype

On 29 October the founder supplied a Song Chords table and teaching summary and requested that it be saved and integrated into Foundation. The [complete original](reference/SONG_CHORDS_USER_REFERENCE.md) is preserved unchanged; [provenance and interpretation notes](reference/SONG_CHORDS_REFERENCE_NOTES.md) keep corrections separate.

The prototype now offers all 15 major-key spellings and 12 chord columns, Basic / Rock-blues / More-colour suggestions, individual bar editing and synthesized triad previews at the selected tempo. Section-key changes transpose the guide only. Minor-mode teaching and additional alterations remain preserved reference material for later work, rather than implemented modes.

## Feel-led beginner guidance — agreed 30 October 2026

Start by asking how the player wants the song to feel, then guide them through **feel → suggested key → chord choices → progression**. Happy/uplifting, sad/reflective and heavy/aggressive are initial examples, not a fixed or exhaustive taxonomy.

Offer two short musical examples to hear, recommend a playable starting key, and explain the recommendation in practical terms. Combine major/minor colour with tempo, rhythm and tone; do not assign a guaranteed emotion to a particular key name. Consider familiar guitar shapes, open strings/capo options and vocal range where relevant. Every recommendation remains editable.

### Next research brief

**How can we help a beginner turn an intended feeling into musical choices?**

Investigate evidence and teaching material for mood, major/minor/modal colour, tempo, rhythm and tone; practical key selection for guitar and singing; and guidance at each of the three layers (key, chord palette, progression). Distinguish supported tendencies from teaching heuristics. Use the findings to propose a small set of explained, audible starting choices for the Foundation prototype.

This is an agreed product direction and research brief. The research and feel-led prototype UI are not yet complete.

## 31 October iPhone follow-up

The founder authorized a Pages pilot: Home offers Jukebox and Bandmaker, and Bandmaker opens straight into the chord recommender. The feel-first research (#77) is applied as six editable examples with synthesized previews. This bounded pilot omits saved projects, the member workspace and recording; those remain the larger Band Mode direction. The 100-song Jukebox is retained. Source: `codex/bandmaker-pages`; feedback: #73.
