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
