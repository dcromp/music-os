# Neural beat candidates and duration-count tradeoffs

Completed 12 October 2026. [Beat This!](https://github.com/CPJKU/beat_this) is an
official published neural beat/downbeat tracker with MIT code and model weights.
The full `final0` and smaller `small0` models were selected before inference with
CPU, one thread, full precision and default minimal postprocessing; no DBN,
reference timing, source-tempo hint or fitted offset. Package version 1.1.0,
Torch/Torchaudio 2.6.0 and checkpoint hashes are pinned. The models are 81.1 MB
and 8.45 MB; reported runtime is local inference, not a hosting-price estimate.

[Five new external challenges](../experiments/fixtures/beat-candidate-selection.json)
were frozen before acquisition or model output. The earlier ten GuitarSet inputs
and three ARTBeaT clips are explicitly retrospective controls.
[Complete results](BEAT_CANDIDATE_RESULTS.json) preserve identities, source/reference
hashes, missed/extra pulses, count coverage and runtimes. Pretrained training
exclusion is not established; experiment holdout is not that claim.

| Whole-recording pulse F1 at 70ms | Existing default tracker | Full neural | Small neural |
|---|---:|---:|---:|
| Five new external challenges | 65.1% | 67.5% | 67.0% |
| Prior ten nominal guitar grids | 63.3% | 81.6% | 84.8% |
| Prior three external clips | 76.3% | 74.4% | 81.0% |
| Prior fluctuating-tempo piano clip | 51.7% | 68.6% | 90.3% |

Neural columns include invalid native endpoint events as extra pulses. Small0
performs best on the variable-tempo piano while costing much less model storage.
It is not uniformly better: fresh rhythmic deception scores 64.6% versus 97.6%
default/98.9% full, while fresh syncopation is 55.8% versus 26.8%/27.1%. The
previous distorted-guitar 7/8 clip also exposes neural pulse-level ambiguity.
No parameters were changed in response to these results.

Better beat agreement does not automatically produce better bar lengths. On the
ten nominal guitar recordings, mean absolute count error is 0.717 beats for full
and 0.545 for small, versus 0.084 for the existing tracker with declared tempo
guidance. Supported windows are 555/568, 547/568 and 531/568 respectively; these
overlapping intervals are not independent recordings. Half/double pulse levels
can preserve many matching beats while corrupting duration units. Retain curated
tempo/meter conventions before making bar-length claims.

## Endpoint handling and reproducibility

The first strict neural wrapper rejected the layered clip because the model
emitted a pulse exactly at 17.5 seconds, equal to the WAV endpoint. The raw audit
is saved. The revised bounded interface retains every raw timestamp and separately
lists out-of-recording events; those events count as forced extras in the native
whole-recording audit. It neither shifts events nor hides the endpoint failure.
One invalid pulse appears in each neural output for the prior external packet,
and one in small0's guitar packet. Fresh-five outputs have none. Legacy final0
guitar output passed strict in-range checks but lacks a separately saved raw list;
that provenance difference is retained.

Native downbeat arrays remain research estimates. This pulse comparison does not
validate bar starts, strumming patterns or chord boundaries. No existing player
metadata or charts are replaced. A separate nominal-grid downbeat diagnostic is
being evaluated, with its source meaning stated independently.

Create `.venv-beatthis` separately and install
`experiments/analysis/requirements-beat-this.txt`. Put the official checkpoints
under `experiments/candidate-assets/beat-this-1.1.0/`; their source/hash pins are
saved locally. Example using a fresh output path:

```sh
.venv-beatthis/bin/python experiments/analysis/beat_this_adapter.py \
  --manifest experiments/generated/beat-candidate-fresh-v1/manifest.json \
  --config experiments/generated/beat-candidate-fresh-v1/config.json \
  --checkpoint experiments/candidate-assets/beat-this-1.1.0/small0.ckpt \
  --output experiments/generated/beat-candidate-fresh-v1/new-small0-predictions.json
```

Saved predictions need only `.venv-pilot` and `rhythm_reference_eval.py` to
rescore. The native-extra audit must remain beside bounded metrics. Keep small0
as a promising tempo-adaptive candidate; preserve the current guided duration
method until units, meter and target recordings are independently checked.
