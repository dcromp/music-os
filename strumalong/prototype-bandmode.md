# Band-member UI prototype (#73)

Throwaway revision, 29 October 2026. Question: which workspace presentation best supports the founder's Home → project → swipeable band-member structure?

Run from this checkout:

```sh
python3 -m http.server 8094 --bind 127.0.0.1 --directory strumalong
```

Open http://localhost:8094/prototype-bandmode.html?variant=A.

- A: focused member studio.
- B: whole-band timeline above the current member's editor.
- C: member guidance beside the editor (stacked on narrow screens).

The floating arrows or keyboard left/right change layouts and update `?variant=`. Member buttons, member arrows and horizontal touch swipes in the workspace change members. Home offers Jukebox recommendations, an example saved project and a new project. Singer combines songwriting, lyrics and voice. Shared Connect guitar setup covers input, signal and tuning.

Everything is in memory. Audio, interface connection, tuning and takes are simulated and labelled. The prototype does not detect a Focusrite. The switcher appears only on localhost or a local file; this file must not be included in production deployment.

Verification: script syntax check and interactive desktop browser checks for Home, opening the example project, A/B/C switching, member navigation, setup dialog and simulated take. Real iPhone swiping/audio and device-sized rendering remain unverified.

Verdict: awaiting founder review; no winning layout has been selected. Prior agreed structure is recorded on #64 and #73. This branch is evidence, not production implementation.

## Rhythm foundation revision (D), 29 October

Founder chose B's rhythm-only timeline plus A/C guidance. D now explores section lengths, chord progression suggestions, a recording flow, clip edits and pedals. Open `http://localhost:8094/prototype-bandmode.html?variant=D&member=rhythm` directly. A/B/C stay available as prior comparisons.

- Foundation: bars per section, tempo and editable four-bar chord suggestions.
- Record: simulated count-in or armed/first-note start; section-end, silence or manual stop. Two seconds of silence is a proposal awaiting review.
- Edit: pointer drag, edge trimming, accessible numeric edits, section movement, duplicate, remove and restore. Original source length stays intact. Takes have separate visible lanes.
- Pedals: add, remove, bypass and change amounts; dry comparison. These are UI state only.
- Metronome: actual synthesized clicks at the chosen tempo. No microphone access, real recording or DSP.

Verified in the desktop browser: changing verse length to 12 bars, choosing a progression, simulated auto-start/silence-stop take, dragging a clip two bars, trimming one bar from its end, moving it into Chorus, adding/bypassing/removing a pedal, and starting/stopping the metronome UI. Script syntax passes. iPhone touch behaviour and real audio remain unverified.

Verdict: combined direction selected; the specific Foundation / Record / Edit / Pedals tab layout awaits founder review. Keep this prototype out of production.

## Saved Song Chords reference and helper, 29 October

The founder's complete pasted text is preserved unchanged in `docs/reference/SONG_CHORDS_USER_REFERENCE.md` and in the locally viewable `strumalong/prototype-song-chords-reference.md`. Separate provenance, theory corrections and source links are in `docs/reference/SONG_CHORDS_REFERENCE_NOTES.md`.

Foundation now offers all 15 major-key spellings and all 12 chord columns, grouped as Basic / Rock-blues / More colour. Nine illustrative progressions can populate a section. Every bar can be changed independently, with conventional Roman numerals and a short explanation. Changing the section key transposes the guide, not recorded audio. The bar count expands the existing pattern. Hear section synthesizes major/minor triads at the selected tempo, highlights the current bar and supports cancellation.

Verification: JavaScript syntax; browser change G→C→C♭ with correctly displayed spellings, minor-iv suggestion, individual Dm edit, 8→12-bar expansion, preview start/stop without console errors, and chosen chords carried into Record. Original reference compared byte for byte with the attachment. Real guitar audio and iPhone behaviour remain unverified. Minor-mode teaching and extra alterations are saved reference material, not implemented modes in this revision.

Verdict: requested chord-helper integration is ready for founder review. All prototype state resets on reload.

## Feel-first follow-up, 30 October (#77 → #73)

Implements the research's proposed flow: feel → compare two starts → practical starting key → small palette → editable progression. Initial invitations are Happy/uplifting, Sad/reflective and Heavy/aggressive, with Explore and Neither exits. Six recipes use the research's chords, tempos, standard-tuning voicings and contrasting rhythm/articulation specifications. Choosing a recipe changes the project tempo and current section guide; audio clips are not retimed/transposed. Four bars load unless existing clips require a longer section.

Major, minor (including B7) and third-free power-chord palettes are explicit. Key changes are tucked under details, along with singing-fit guidance. Hear individual chords; swap, repeat or return home; Undo and reset; use an easier heavy practice tempo; adjust rhythm and preview tone separately. Full chord controls remain accessible.

Renderer: deterministic-plucked-string-v1, Web Audio, no samples/network/microphone. Uses the specified guitar voicings where available, alternating strokes/plucks, short damping for muted strokes and a moderate waveshaper for drive. Uses fixed gain with driven-output compensation, not perceptually validated loudness matching. The last playback manifest is exposed in Prototype state: recipe ID, notes, exact onset/duration times, BPM, pattern, tone, sample rate and core/tail duration. A 2.5-second render tail follows four-bar timing. No claim of recorded-guitar realism or accepted emotional effect.

Validation: syntax and interactive desktop browser checks for minor B7 preview/application, unchanged example clip, power-chord preview/application, easier 84-BPM practice, guide editing/Undo and preview cancellation. Remaining: founder listening judgment, real iPhone interaction and credible-guitar/palm-mute comparison. All recording and input remain simulated. Research source: `research/feel-to-musical-choices:docs/FEEL_TO_MUSICAL_CHOICES_RESEARCH.md` (82972ad).

The research's three practical starts are implemented for review; no founder choice among the six examples is recorded yet. All UI edits reset on reload.
