# Local guitar testing bench

Open this interface through the project's local experiment server. It uses plain browser audio playback and has no npm dependencies. No files or ratings are uploaded. The interface requests only local demo metadata, JSON charts and audio from the same server.

1. Generate the demo and press **Load demo**, or select a local audio file and its analysis JSON.
2. Play using the built-in audio controls. Enter an **Audio position (seconds)** and press **Go** (or Enter) to seek precisely. **Restart** returns to zero. Both preserve whether playback is paused or playing and are disabled until audio metadata loads. Seek, pause, replay or change chart versions; chord position always comes from `audio.currentTime`.
3. Set a display offset only if needed. Displayed chart time is `audio time + offset`: positive values show later events earlier; negative values delay them. Zero is the default. Switching candidates preserves audio playback and the chosen offset.
4. Optionally hide algorithm names for comparisons. Candidate order is unchanged; randomise order in the server manifest if required.
5. Rate followability and enjoyment and save a session. Download the CSV before closing the tab; saved rows are held only in memory. If the browser cannot download files, press **Show CSV** and manually copy its read-only text into a local `.csv` file. Both options use the same CSV content. Spreadsheet-formula-like text is prefixed with an apostrophe for safe import; numerical offsets retain their values.

## Chart validation

The bench accepts schema version `1.0`, positive recording duration/sample rate, analysis identity and runtime, and nonempty, ordered, nonoverlapping chord intervals within the declared recording duration. Optional confidence must be in `[0,1]`. Optional beat/downbeat arrays must contain strictly increasing times within the recording. Intervals are half-open: `[start_seconds, end_seconds)`; gaps show no labelled chord. The upcoming change is separate from the current chord.

After audio metadata loads, the bench rejects a duration mismatch greater than the larger of 0.1 seconds or 0.1 percent of chart duration. Matching duration is only a check, not proof of recording identity: choose the exact audio used to generate the chart. JSON can be loaded before audio. The UI never treats a missing or invalid chart as a successful comparison.

## Checks

Run the dependency-free validation and timing checks from the repository root:

```sh
node experiments/bench/test.js
```

These tests exercise the actual UI script in a minimal Node DOM stub: interval boundaries and gaps, invalid charts, offset direction, audio-duration checks and candidate switching. They do not replace a live browser/audio smoke test.

## Server contract

Serve `index.html`, `style.css` and `app.js` together. **Load demo** fetches `/api/demo` with this shape:

```json
{
  "audio_url": "/data/demo.wav",
  "candidates": [
    {"name": "Baseline", "url": "/data/baseline.json"},
    {"name": "Alternative", "url": "/data/alternative.json"}
  ]
}
```

URLs must resolve to the same local origin. Return JSON and audio with suitable content types. To support audio seeking reliably, serve byte-range requests (`Range`, `206` and `Content-Range`), or use short fully downloaded audio files. The demo route should return a useful non-2xx response when generated assets do not exist. No rating POST endpoint is needed.

The front end supports local file pickers independently of the demo endpoint. Safari/Chrome format support still applies. Run a live browser/guitar smoke test before using ratings as evidence of a reliable practice interface.
