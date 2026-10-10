# Phase 0 results — Mac experiment setup

10 October 2026 · Implementation branch: `codex/mac-analysis-phase0`

## Deliverables

- Isolated Python 3.12.10 environment with NumPy 2.2.6 on macOS arm64.
- Versioned chart JSON with explicit seconds, recording identity and analysis metadata.
- A generated 22-second fixture: C, Am, F, G, silence, Dm, Em and an inverted C voicing. This uses synthetic harmonic tones, not a physical guitar or commercial recording.
- A simple spectral-template baseline recognising major/minor triads and no-chord intervals.
- Local browser bench independent of Expo: source selection, chart switching, current/upcoming chords, playback-clock timing, seek/restart, offset and ratings/export.
- README status/deployment table and separate experiment setup guide.

## Measured baseline

| Measure | Observed result |
|---|---|
| Fixture duration | 22.0 seconds |
| Reference timeline | 8 events, covering the full recording |
| Baseline output | 11 events |
| Exact-label agreement by duration | 98.856% |
| Initial measured analysis runtime | 0.163 seconds |
| Subsequent CLI runs | About 0.030–0.031 seconds |

Runtime includes WAV loading and analysis, excludes interpreter/NumPy import and fixture generation, and is specific to this Mac and short fixture. It is not a GPU/cloud cost estimate. Extra output segments show brief label instability around transitions; high duration agreement does not remove that usability concern.

This fixture verifies input/output and basic chord/timing plumbing. It does not establish real-guitar performance, prove a pretrained model inferior, or select a production algorithm. No BTC/CREMA/All-In-One/Demucs comparison has run yet. The planned progressive synthetic suite and real-recording holdouts are Phase A work.

## Verification

- All 7 Python checks pass: known triads/silence, silence-only output, shifted-boundary scoring, invalid timelines/metadata, recording mismatch and protection against overwriting source audio/reference inputs.
- All 41 dependency-free Node checks pass: chart validation, half-open boundaries/gaps, display offsets, stopped clocks, candidate switching, Go/Restart, duration mismatch and CSV serialization.
- The prepare → analyze → evaluate CLI path ran using FFmpeg on the generated fixture and preserved the same agreement result.
- Live in-app browser on Mac loaded and played demo audio. At 3.0 seconds the reference chart showed Am; forward seeking to 14.0 showed Dm; switching to baseline retained 14.0; Restart returned to C at zero. Pause was observed with a stopped playback position.
- Saving a clearly labelled UI-only rating produced a saved row. Blob-download completion was not confirmed in the in-app browser; the Show CSV fallback visibly displayed the correct recording/analysis identity and escaped quoted notes. Test ratings were cleared after verification and are not founder/guitar evidence.

The full legacy Expo checks remain in [REUSE_AUDIT.md](REUSE_AUDIT.md). They do not describe this new bench's deployment or prove native app playback.

## Remaining founder test

Estimated 15–20 minutes after choosing a suitable recording: prepare the local WAV, run the baseline, load the same WAV and its JSON, play with guitar, record confusing timestamps and ratings. Synthetic tones can check basic interaction immediately, but actual guitar/music material is needed for useful algorithm decisions.

The previous analysis code was deleted, as confirmed by the founder. Phase A proceeds from this fresh baseline.
