# Experimental known-chart alignment baseline

The local NumPy tool in `experiments/analysis/chart_aligner.py` aligns a **given ordered chord sequence** to 16-bit PCM WAV audio. It is a timing baseline for a curated catalogue, not another chord-recognition model. It does not fetch music or chord sources. No package beyond the existing `.venv-analysis` NumPy environment is required.

Its first conditional synthetic screen completed 64 cases. See [ALIGNMENT_SCREEN.md](ALIGNMENT_SCREEN.md) for timing results and limitations. It has not established real-song timing accuracy or readiness for a learner-facing app.

## Untimed input

```json
{
  "schema_version": "untimed-chart-1.0",
  "recording": {
    "id": "recording-version-id",
    "title": "Exact recording title",
    "audio_sha256": "optional exact WAV file SHA256"
  },
  "sequence": ["G", "B", "C", "Cm"],
  "mode": "cyclic",
  "start_policy": "first",
  "end_policy": "any",
  "metadata": {
    "key": "G",
    "capo": 0,
    "source_references": ["reviewed chart source URL"],
    "note": "An explicit ordered four-chord loop assumption"
  }
}
```

`sequence` contains strings only. Event timestamps, durations and beat timestamps are rejected anywhere in the input, including metadata. The optional audio hash is checked against the exact WAV file before inference. Hashes contain no timing gold.

- `mode: finite` is the default. Each supplied position is visited in order, without skipping or repeating it; the last position must be reached by default.
- `mode: cyclic` must be explicit. The final position may advance to the first. The audio determines how many cycles the baseline proposes. This is an assumption that the supplied loop applies to the entire chosen excerpt, not discovery of a song's sections.
- `start_policy: first` is the default. Explicit `any` permits a partial excerpt to start at another chart position.
- `end_policy: last` is the finite default; cyclic defaults to `any`. Explicit `any` permits an incomplete sequence at the end. Unvisited positions are reported for review.

Key, capo and source metadata are preserved separately, without affecting the path. **Supply sounding pitches**, after reviewing any capo-shape conversion yourself. No transposition or key-based substitution is performed.

Supported templates include major, minor, major seventh, dominant seventh, minor seventh, power, sus2, sus4, dominant 7sus4, add9, diminished, diminished seventh and augmented chords. Conventional forms such as `F#m7` and colon forms such as `F#:min7` are supported. Flat roots are accepted. Slash-bass suffixes are preserved in labels but ignored by the pitch-class template; they do not establish inversion accuracy. Unsupported qualities are rejected rather than silently simplified.

## Run on local prepared audio

From the repository root:

```sh
.venv-analysis/bin/python experiments/analysis/chart_aligner.py align \
  --audio /path/to/audio.wav \
  --chart /path/to/untimed-chart.json \
  --output experiments/generated/example-alignment.json
```

It refuses to overwrite or alias either input, including existing hardlinks, even with `--overwrite`. Symlink outputs are rejected. Results publish atomically; without `--overwrite`, creation is exclusive and preserves a concurrent new file. Existing output files require explicit `--overwrite`. The synthetic screening runner preflights every artifact against all suite inputs before writing. Default maximum audio length is ten minutes; use a reviewed excerpt for a source chart that describes only one section. Do not run an intro progression over a whole song unless that is a documented assumption being tested.

## What the algorithm actually does

Audio is reduced to centred spectral pitch-class frames, using approximately 180 ms windows and a 25 ms hop. Equal-weight chord templates give raw cosine similarities. An adjacent-only Viterbi path permits staying on the current chart position or advancing one position, with a minimum dwell and a transition penalty. Chord durations remain variable; there is no beat grid or fixed bar length.

The requested default minimum duration is 150 ms. Interior proposed chart positions use a nominal hop-grid dwell rounded up to an integer number of hops (about 175 ms at the prepared 22,050 Hz sample rate). The terminal position is checked against the **actual clipped audio end**, so it must last at least the requested 150 ms; it can be shorter than the nominal rounded interior dwell. Audio shorter than the requested minimum is rejected. This constraint applies to the proposed chart path, while acoustic `N`/`X` masks may produce shorter displayed gaps or chord fragments. Default transition penalty is 0.12. There is no maximum chord duration and no prior on expected loop duration. These are starting parameters, not empirically validated timing or confidence thresholds.

RMS silence becomes `N`. Gross conflicts between the assigned chord and the broader template vocabulary become `X`; they are not filled with a confidently asserted chord. Adjacent `N`/`X` gaps merge in the displayed timeline even if the proposed chart path changes inside them. The unmasked proposed path remains in the evidence. Conflict checks use uncalibrated template scores: assigned cosine below 0.45 or best-vocabulary minus assigned cosine above 0.30. A brief forced wrong event can trigger review even when the whole-recording mismatch fraction is small.

Output is the existing common timed-chart schema `1.0`, with audio/chart/source-reference hashes, copied untimed inputs, per-event raw score summaries, frame evidence and diagnostics. No `confidence` field is emitted. `no_large_mismatch_detected` only means the particular diagnostic rules found no large conflict; it is not a quality certificate, and every result requires human review.

## Known limits and next evidence

Spectral templates ignore instrument identity, tuning variation and slash-bass voicing. Vocals, bass, distortion and percussion can dominate the evidence. Transitions between identical pitch-class templates cannot be timed from this evidence alone and are flagged. A wrong finite sequence can be forced into a path, while unconstrained cycling can propose too many repeats in a dense recording. Review the gaps, event scores, proposed cycles and raw acoustic conflicts before caching a chart.

The model consumes no reference timestamps. Tests check nonuniform and offbeat changes, explicit cyclic repetition, silence, wrong chord sequences and ordering, source hashes, output guards, malformed/timed inputs, honest suspended chords, and the dynamic-programming objective against exhaustive small paths. The timing scorer rejects partially covered references; create a fully annotated excerpt before calculating timing metrics.

```sh
.venv-analysis/bin/python -W error -m unittest \
  experiments/analysis/tests/test_chart_aligner.py -v
```

The next useful evaluation is exact recordings with reviewed section order and independently checked timestamps. Conditional synthetic timing results do not substitute for that work.
