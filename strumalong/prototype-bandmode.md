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
