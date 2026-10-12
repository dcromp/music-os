# Nominal barline agreement diagnostic

Completed 12 October 2026 using the saved BeatThis `final0` and `small0`
outputs for ten paired GuitarSet microphone recordings, totalling 317.022
seconds. [The report](NOMINAL_DOWNBEAT_CHECK.json) preserves the four development
and six experiment-holdout recordings separately, every supplied reference
barline, every saved predicted downbeat, input hashes and missed/extra events.

This is a **retrospective extra metric added after the model outputs were
exposed**. The experiment split predates inference; this downbeat metric does
not. No models were rerun, settings selected, phase offsets fitted, chord
boundaries snapped or product acceptance threshold added.

The references are GuitarSet's **nominal metronome/lead-sheet bar positions**,
not manually marked physical bar starts. Predictions are compared directly to
the 152 supplied positions with the existing chronological maximum-cardinality
one-to-one matcher at its unchanged 70ms and 150ms tolerances. Matching has no
warm-up or endpoint trim. A native event at/beyond the recording endpoint, or
before zero, remains a forced extra even if it lies within tolerance of a
reference. This diagnostic does not infer additional reference barlines after
the annotation's last supplied position. Unmatched events are disagreements
with this finite nominal grid; they are not proven physical false positives.

| Nominal-grid measure | final0 | small0 |
|---|---:|---:|
| All ten: F1 at 70ms | 70.6% | 66.1% |
| All ten: F1 at 150ms | 70.6% | 67.7% |
| Four development: F1 at 70ms | 78.6% | 69.7% |
| Four development: F1 at 150ms | 78.6% | 69.7% |
| Six experiment holdouts: F1 at 70ms | 65.4% | 63.6% |
| Six experiment holdouts: F1 at 150ms | 65.4% | 66.4% |
| All ten: matched / missed / extra at 70ms | 125 / 27 / 77 | 123 / 29 / 97 |
| All ten: matched / missed / extra at 150ms | 125 / 27 / 77 | 126 / 26 / 94 |
| Saved out-of-recording downbeat events | 0* | 1 |

F1 values above are micro scores from pooled matched/missed/extra event counts;
the JSON also reports per-recording macro scores, precision and recall. Both
checkpoints match 70 of the 92 experiment-holdout reference positions at 70ms,
but also produce 52 (`final0`) or 58 (`small0`) unmatched estimates there.
Matching many bar positions while producing extra starts would still give a
learner a misleading bar count. The BN3 solo remains particularly weak:
`final0` matches 4/16 nominal positions with 16 extra estimates; `small0`
matches 6/16 with 14 extras at 70ms. Some clean comping cases agree closely,
but this is not a reliable general bar-start result.

`small0` has consistent raw, bounded and outside-event audit lists. Its
28.8-second event on the SS1 comping recording equals the exact endpoint and
is included in every relevant extra count. **\*`final0` is a legacy prediction
packet containing only its saved downbeat list**. All 202 saved estimates are
scored and none is outside the recording; native completeness before earlier
interface handling is unverified. This limitation is recorded per case and
must accompany comparison claims. A raw native audit is required before
claiming the `final0` count covers every original model output.

ARTBeaT supplies beats without verified bar positions in our packets, so this
scorer refuses it instead of turning every fourth beat into invented bar gold.
Model-training exclusion and accuracy on the app's popular-song recordings
remain unproven. Physical downbeat accuracy stays explicitly unmeasured. Keep
the player's approximate counts/seconds fallback; these results do not
promote neural downbeats, numbered bars or timing snaps into the app.

The new scorer has 16 passing checks in the standard and pinned Python
environments. They cover phase and rate errors, empty estimates, exact recording
identity, endpoint/negative events, raw/bounded audit consistency, absent bar
references, separate splits and read-only report publication. Rescore the
saved inputs without models to a new output path:

```sh
.venv-pilot/bin/python experiments/analysis/nominal_downbeat_eval.py \
  --references experiments/generated/guitarset-rhythm-reference-v1/references.json \
  --predictions experiments/generated/guitarset-rhythm-reference-v1/beatthis-final0-predictions.json \
  --predictions experiments/generated/guitarset-rhythm-reference-v1/beatthis-small0-predictions.json \
  --output experiments/generated/guitarset-rhythm-reference-v1/new-nominal-downbeat-report.json
```

The original pulse scorer, beat adapter, checkpoint files, references and
player remain unchanged by this diagnostic.
