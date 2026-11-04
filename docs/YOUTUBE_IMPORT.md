# Local YouTube audio experiments

The Python library [yt-dlp](https://github.com/yt-dlp/yt-dlp) successfully imported **Creep, Wonderwall and House of the Rising Sun** from the existing Music OS song list on 10 October 2026. All three prepared recordings then ran through the baseline, CREMA and Chordino. See [the smoke report](YOUTUBE_IMPORT_SMOKE.md).

The old `react-native-youtube-iframe` wrapper supplies embedded playback and player time, not decoded audio for analysis. The new importer is separate offline experiment tooling. This proves the technical route works on this Mac; it does not establish a commercial sourcing agreement or confirm speculation about paying YouTube per video. Keep that product workstream in [the plan](../plan.md).

## Setup

Tested with Python 3.12.10, yt-dlp 2026.08.19, its installed EJS package, Node 25.8.1 and local FFmpeg. Use an isolated environment rather than changing the existing global yt-dlp installation:

```sh
cd /Users/davidcrompton/Documents/music-os
/Users/davidcrompton/miniforge3/bin/python -m venv .venv-youtube
.venv-youtube/bin/python -m pip install -r experiments/analysis/requirements-youtube.lock
```

The lock records the installed dependency versions. Node and FFmpeg must also be available; on the tested Mac they are `/opt/homebrew/bin/node` and `/opt/homebrew/bin/ffmpeg`.

## Inspect and import one recording

The commands below inspect one URL and then prepare that recording. An existing recording ID is refused; choose a new ID for a deliberate new acquisition.

```sh
.venv-youtube/bin/python experiments/analysis/youtube_import.py \
  --node /opt/homebrew/bin/node metadata \
  'https://www.youtube.com/watch?v=XFkzRNyygfk'

.venv-youtube/bin/python experiments/analysis/youtube_import.py \
  --node /opt/homebrew/bin/node import \
  'https://www.youtube.com/watch?v=XFkzRNyygfk' \
  --recording-id creep-local-experiment \
  --source-use 'Requested local founder algorithm experiment; commercial clearance not established'
```

The importer accepts one explicit HTTPS YouTube watch/shorts/embed or youtu.be URL. It rejects playlists, searches, live recordings, unknown/over-ten-minute durations and restricted availability. Downloads are bounded to 32 MiB and 180 seconds, with separate metadata and decoding limits. It uses no browser cookies, credentials, configured proxy, geo bypass, plugins or remotely fetched executable components. The installed EJS package runs in the specified local Node runtime.

## Saved evidence and timing

Each successful import writes a gitignored directory under `experiments/local-audio/youtube/<recording-id>/` containing:

- `source.m4a` (or the selected audio format): the acquired source, with its hash.
- `audio.wav`: mono, 22,050 Hz, PCM16 audio used for both analysis and local playback.
- `manifest.json`: minimal source identity, hashes, prepared duration, tool version and source-use note.

Raw extractor metadata, signed stream URLs and upstream logs are discarded. The manifest is published after the completed audio files. The importer stages its work and refuses to overwrite an existing recording directory.

Use the **exact prepared WAV** when reviewing detector timings. Embedded playback can have a different decoder origin; substituting it has not been checked. Source duration metadata also differs slightly from decoded duration, so annotations must follow the prepared file rather than the rounded video duration.

The deployed checkout contains the three cached imports and saved detector outputs. The new recordings are available through local file selection in the optional bench; the existing **Load synthetic suite** button still loads only synthetic cases. No founder guitar task is assigned yet. CREMA/BTC/ChordMini inference environments remain separate research setup; saved charts can be inspected without them. Baseline, chart alignment and the previously deployed native Chordino can run locally.

## Next use

Review exact versions and select fully annotated excerpts before scoring real-song timing. Candidate untimed charts are under `experiments/fixtures/untimed-charts/`: Creep is an explicitly simplified cyclic hypothesis; Wonderwall and House are **intro-only** candidates pending excerpt selection. They are not checked whole-song arrangements. See [the alignment setup](CHART_ALIGNER_SETUP.md).
