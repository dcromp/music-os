# music-os reuse audit

10 October 2026 · Source revision: `0083861` · Last application-code revision: `26d4580` (9 September 2024)

## Decision

Keep the Expo/React Native project and adapt its song-selection and playback UI later. It is an early YouTube play-along prototype, with enough structure to extend. It does not contain an audio-separation/chord-recognition pipeline. The founder subsequently confirmed the previous analysis code was deleted; build a fresh baseline separately in this repository. This audit describes source revision 0083861; new experiments and their live status are documented in the root README.

The current chord animation is unsuitable for judging recognition algorithms: it displays unrelated sample chords and ignores the supplied chord timestamps. The founder's sequencing decision is to evaluate algorithms on Mac first. Use an independent local-audio browser bench with a verified playback clock for guitar comparisons; repair and integrate the Expo player after selecting an initial pipeline. Existing app defects do not block offline analysis experiments.

## Scope and evidence

Inspected the tracked source, configuration, lockfile, tests and application history through the source revision above. No AGENTS.md was found in the checkout. Examined the earlier SongPlayer implementation in `7c6219e`; it is another YouTube/player-time attempt rather than an analysis engine and provides no reason to restore it wholesale.

Installed locked dependencies in a temporary checkout without lifecycle scripts. Ran TypeScript, the existing Jest suite, and Android/web bundle exports. No application source or dependency versions were changed for this audit. No simulator, device, browser playback or guitar session was run: native bundling success is not proof that playback works on a device. No local audio/model assets or analysis commands exist to exercise an audio import → recognition pipeline.

Environment: macOS arm64, Node `v25.8.1`, npm `11.11.0`. This is the audit environment, not a recommended or pinned deployment runtime.

**Mac availability:** this checkout configures iOS, Android and web, with no native macOS target. Running build tools on Mac does not establish a Mac app. Browser access is a potential route, but the recorded web build fails; live Mac playback has not been verified. Phase A's local browser bench will be new experiment tooling.

| Command | Result | What it establishes |
|---|---|---|
| `npm ci --ignore-scripts --no-audit --no-fund --cache /private/tmp/music-os-npm-cache` | Passed; 1,375 packages installed, with deprecation warnings | The checked-in lockfile can be installed in this environment |
| `./node_modules/.bin/tsc --noEmit` | Passed | Current TypeScript compiles; JavaScript is included via allowJs but checkJs is not enabled, limiting coverage of the core player/display |
| `CI=1 ./node_modules/.bin/jest --runInBand --watch=false` | Passed: one test and one snapshot | The Expo starter ThemedText rendering test passes; there is no playback, timing, chart or algorithm coverage |
| `CI=1 EXPO_OFFLINE=1 ./node_modules/.bin/expo export --platform android --output-dir /private/tmp/music-os-android-audit-20261010` | Passed | Metro/Hermes can bundle the Android target; native installation and playback remain unverified |
| `CI=1 EXPO_OFFLINE=1 ./node_modules/.bin/expo export --platform web --output-dir /private/tmp/music-os-web-audit-20261010` | Failed | The installed react-native-youtube-iframe web implementation imports missing `react-native-web-webview`; web is not a working baseline |

The default `npm test` script watches indefinitely; use the bounded command above for an audit/CI run. `npm run lint` was not run because the repository has no committed ESLint configuration and Expo may offer to install/configure tooling. The template `reset-project` script was inspected and not run; it moves the existing app out of the active routes.

## What is implemented

`package.json` uses `expo-router/entry`, Expo SDK 51, React 18.2 and React Native 0.74.5. Root `App.tsx` is an unused shell for this entry point.

The meaningful navigation path is:

`app/index.tsx` → `app/(tabs)/songs.tsx` → `app/screens/SongPlayer.js` → YouTube wrapper plus chord display.

Login/signup only navigate; there is no authentication backend. Profile, Tutorial and the separate Player tab are placeholders. Seven songs and their chord lists are hardcoded in the Songs screen. The card layout, routing, theming and playback wrapper are reusable starting points.

No implemented audio import, separation, chord/beat detection, analysis backend, data persistence, structured progression, strumming guide, practice loop, local-audio player, MIDI accompaniment or live-listening system was found. `react-native-sound` is listed as a dependency but not used by application code. A dependency entry is not an implemented capability.

## Component decisions

File links below refer to the audited source; later refactoring may move them.

| Component | Evidence | Decision |
|---|---|---|
| Expo Router shell and theme utilities | [package.json](../package.json), [root layout](../app/_layout.tsx), [tab layout](../app/(tabs)/_layout.tsx) | **Reuse/adapt.** Keep Expo initially. Reduce routes to the practice flow and verify the chosen platform before broad dependency upgrades. |
| Song cards | [songs.tsx](../app/(tabs)/songs.tsx), lines 37–137 | **Adapt.** Load a shared catalogue by stable recording/arrangement ID; derive categories from actual skills. IDs currently repeat across the two lists, and category labels do not match several listed chord sets. |
| Active player screen | [SongPlayer.js](../app/screens/SongPlayer.js), lines 21–66 | **Adapt.** Retain composition of playback and chart; resolve the selected recording and chart from one data source. Metadata currently arrives through route parameters, but no chart is passed to the display. |
| YouTube wrapper | [YoutubePlayerComponent.js](../app/components/YoutubePlayerComponent.js), lines 14–42 | **Adapt.** Keep embedded-player integration if verified on the target. Expose numeric media time and state, handle readiness/errors/source changes. Current-time retrieval is a button action, not continuous synchronization. Web support is blocked by the missing optional peer dependency. |
| Chord/beat/bar visual components | [ChordProgressionDisplay.js](../app/components/ChordProgressionDisplay.js), lines 6–22 and 83–95 | **Adapt visuals; replace timing logic.** Preserve a readable bar preview if guitar testing supports it; derive labels/highlights from actual event times. |
| Independent chord timer | [ChordProgressionDisplay.js](../app/components/ChordProgressionDisplay.js), lines 28–59 | **Replace.** It always reads sampleSongData and treats each chord interval as one four-beat bar. With 120 BPM it advances every two seconds despite 15-second intervals, then wraps twelve entries every 24 seconds. It ignores barStartTimes, interval boundaries and timeSignature. |
| Synchronization hook | [useTimeSynchronization.ts](../app/hooks/useTimeSynchronization.ts), lines 14–54 | **Adapt concept, consolidate implementation.** Unused sketch of player polling plus local interpolation; assumes speed 1 and needs explicit seek/replay/buffering/source-change handling and stale async-result protection. |
| Player-state hook | [useYoutubePlayer.ts](../app/hooks/useYoutubePlayer.ts), lines 3–31 | **Consolidate or remove.** Unused; checks numeric state 1 while the installed iframe wrapper delivers string states such as playing. Its videoId argument is unused. |
| Song schema | [Song.ts](../app/types/Song.ts), lines 1–18 | **Extend.** Timed chord intervals are useful, but units/version/provenance are absent and catalogue types are duplicated. Add explicit timestamp units, recording identity, analysis/arrangement versions, beat/downbeat events and sections. |
| Sample data | [sampleSongData.json](../app/data/sampleSongData.json) | **Keep only as an explicitly synthetic fixture or replace.** Its arbitrary progression is not a verified chart for its linked recording. Bar times and lyrics have no corresponding fields in Song; don't treat them as benchmark annotations. |
| Placeholder auth/Profile/Tutorial/Player tab | [index.tsx](../app/index.tsx), [signup.tsx](../app/signup.tsx), [tabs](../app/(tabs)/) | **Defer.** Give the founder direct access to songs/practice; introduce these only when required by a real user flow. |
| Starter assets/components and text snapshot | [components](../components/), [test](../components/__tests__/ThemedText-test.tsx) | **Keep selectively.** Useful UI utilities; supplement with meaningful timeline and playback tests when implementing those behaviours. |

## Structure and quality issues

- Components, hooks and types currently live inside `app/`, the Expo Router route tree. Move non-route modules outside it and verify the resulting route manifest; default-exported helper components can become unintended pages. This is a structure finding, not a measured device-navigation failure.
- The player/display are JavaScript despite a strict TypeScript configuration. Convert the touched core to TypeScript or enable appropriate checking; replace the local incomplete iframe declaration with types that reflect the installed API.
- Source elapsed time is formatted into text before reaching the screen; the chart never receives it. Keep milliseconds/seconds as numeric state and format only for display.
- The four-beat layout and fixed-tempo timer do not support variable beat maps or changes inside a bar. Event timelines must remain independent of the optional bar-grid visualization.
- Catalogue chord sets and grouping are manually entered examples and require musical review. The current sample and selected recording must not be used for recognition-accuracy claims.
- The September 2024 stack needs a compatibility check for the chosen present-day device/build workflow. Do not upgrade everything before capturing a reliable fixture and playback baseline.

## Ordered implementation backlog

1. **Build a fresh baseline on Mac.** The previous analysis workflow was deleted. Use an isolated environment and command-line adapters; record hardware, tool/model versions, output and runtime. Begin offline comparisons without repairing Expo or developing iOS.
2. **Define and validate the interchange format.** Use versioned JSON with explicit units and recording/arrangement IDs. Preserve source analysis and reviewed arrangements independently. Create a synthetic timing fixture and a manually checked excerpt; the old sample is not reference truth.
3. **Run staged algorithm experiments and guitar comparisons.** Compare BTC/CREMA/baseline, then separation inputs, then smoothing and simplification. Build a small local-audio browser bench independent of Expo, using the audio element's playback clock. Validate pause/resume, seek and replay with known timings before interpreting guitar ratings.
4. **Choose an initial analysis pipeline.** Record held-out quality, Mac runtime/memory, correction effort, setup difficulties and guitar ratings. The founder should be able to repeat the run and explain why the chosen output is more useful.
5. **Choose the first product platform and integrate outputs.** After Phase A, adapt the preserved Expo shell or continue with a browser product. For Expo, move helpers/data/types outside routes, resolve stable IDs, consolidate the hooks and replace the free-running display clock. For its web target, fix the WebView dependency or add a platform-specific official iframe adapter and verify static rendering. Check current device/build compatibility before starting iOS work.
6. **Validate the integrated product player.** Check the selected recording/chart, pause/resume, forward/backward seek, replay, buffering, source changes and supported speeds on the chosen target. Add focused timing/state tests as part of implementation. Native bundling alone is insufficient evidence.
7. **Add practice guidance and progression.** Progress logging, strumming guidance, arrangement difficulty, recommendations and the fixed-tempo MIDI band remain new capabilities.

**First acceptance gate:** an initial algorithm choice with reproducible Mac commands, measured quality/runtime and guitar play-test evidence from a verified local bench. **Later integration gate:** the product player stays aligned through state changes and supports a complete session without manual chart resets. Neither gate is claimed as passed by this audit.
