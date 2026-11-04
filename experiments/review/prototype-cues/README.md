# Throwaway YouTube cue prototype

Decision: [Choose the pilot playback and chord-cue experience](https://github.com/dcromp/music-os/issues/23).

The founder approved revised layout A for testing on 20 October 2026: current and next chords side by side, beat dots under each and vertical bar lines. `index.html` preserves this simulated design; it is not a recording chart.

Run `python3 experiments/review/prototype-cues/serve.py`, then open http://127.0.0.1:8075/live.html. The server allowlists five files and serves no audio, private drafts or repository directory listings. Network binding requires explicit approval; it has not been enabled. Stop with Ctrl+C.

`live.html` uses the visible official YouTube player. The three selectable recordings are mapped to the exact video IDs in the existing automatic-first-ten-v1 manifest. `recordings.json` copies native CREMA chord events without changing them, and records original chart SHA-256 and audio identity. No new audio extraction or inference occurs. This is deliberate provisional testing, not accepted catalogue practice. Existing source permissions and display prerequisites remain unresolved.

The source charts establish neither verified bars nor proven alignment to today's embedded upload. The live display therefore uses seconds; it does not fabricate the approved beat dots/bar lines. No duration scaling or timeline offset is applied. The selected original practice source/algorithm is not changed. No new strumming pattern or arrangement switching is claimed.

Controls: play, pause, native controls, seek, restart, back ten seconds and rates reported by the player. Position is read from the player at 100 ms intervals, with no free-running musical clock. Tab hiding requests pause; returning requires user playback. A manual cue-hide control supports interruptions; automatic ad identification and recovery are not established. Observation logs stay in memory, with copy/select fallback.

Validation on 20 October: JavaScript syntax passes. In the Codex in-app browser, Wild Thing and Creep loaded the official iframe and returned error 150; the app displayed the failure, hid cues and disabled transport. Successful playback, audible synchronisation, seeks, speed changes, and iPhone/iPad behaviour remain unverified. The Animals option is prepared but untested. Do not interpret readiness or available-rate reporting as successful playback.

Next: verify on Safari on the founder's device after network access is approved; capture device/browser/audio-output details and the observation log. Obtain verified recording-specific musical timing before claiming the dot/bar display is ready for real-song practice. Preserve this branch unmerged, with no application PR.
