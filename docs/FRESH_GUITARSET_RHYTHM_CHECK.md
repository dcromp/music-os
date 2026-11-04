# Fresh paired guitar pulse/count check

Completed 12 October 2026. The frozen ten recordings total 317.022 seconds, with
four development and six experiment-holdout inputs. The
[selection](../experiments/fixtures/rhythm-reference-selection.json) predates
acquisition and inference. [Results](FRESH_GUITARSET_RHYTHM_RESULTS.json) preserve
source hashes, missed/extra pulses, coverage and every split. No settings changed
after the earlier six-recording diagnostic.

Official Zenodo acquisition returned 504/timeouts. A pinned public CC-BY mirror
at revision `4b649de5ebc78328b3b1e1df5ea1196c2646e143` supplied selected byte ranges.
Its last 65,536 bytes, including the ZIP index, match the previously acquired
official archive byte-for-byte. Selected entries pass official CRC/size checks;
JAMS hashes match the frozen selection. The whole 657 MB archive was not fetched
or hash-verified. FFmpeg only converts rate/channels/PCM format, without offsets,
trimming, padding or gain changes.

References are nominal metronome/lead-sheet beat positions, not marked physical
guitar attacks. Guided extraction receives only the filename's nominal tempo and
a declared ±15% range. Reference timestamps are withheld. Counts use overlapping
half/one/two-bar windows inside detected coverage; no extrapolation or downbeat
score is manufactured.

| Measure | Default 120 | Tempo guided |
|---|---:|---:|
| All ten: whole-recording F1 at 70ms | 63.3% | 66.6% |
| All ten: whole-recording F1 at 150ms | 75.9% | 81.0% |
| All ten: supported count windows | 533/568 | 531/568 |
| All ten: mean absolute count error | 0.779 beats | 0.084 beats |
| Six holdouts: F1 at 70ms | 53.0% | 57.7% |
| Six holdouts: F1 at 150ms | 69.2% | 77.2% |
| Six holdouts: supported count windows | 323/344 | 321/344 |
| Six holdouts: mean absolute count error | 1.245 beats | 0.097 beats |

Guidance corrects several tempo-level failures but does not uniformly improve
phase. On the 85-BPM Rock2 recording, count error falls 3.863→0.064 beats while
70ms F1 falls 66.0%→42.2%. The BN3 solo remains weak at 17.1% F1 with either
condition. A useful duration estimate does not establish the location of beats
or bar starts. Keep approximate count labels and seconds fallback; do not snap
chord boundaries. These exposed holdouts cannot become fresh validation after
retuning. Model-training exclusion and popular-song accuracy are unproven.

Full local references, predictions and reports are under
`experiments/generated/guitarset-rhythm-reference-v1`. Rescore without models:

```sh
.venv-pilot/bin/python experiments/analysis/rhythm_reference_eval.py \
  --references experiments/generated/guitarset-rhythm-reference-v1/references.json \
  --predictions experiments/generated/guitarset-rhythm-reference-v1/nominal-tempo-guided-predictions.json \
  --output experiments/generated/guitarset-rhythm-reference-v1/new-guided-rescore.json \
  --condition nominal-tempo-guided
```
