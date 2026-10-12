# Paired ensemble chord comparison

Completed 12 October 2026 on three first-60-second publisher-paired JazzSAMBA
mixtures: Blue Bossa (development), Amazing Grace and When the Saints Go Marching
In (experiment holdouts). These are newly performed jazz ensembles, not original
commercial artist recordings. [Source/result pins](JAZZSAMBA_REFERENCE_RESULTS.json)
identify official demo commit `3715097238b33593d865d05b772e094642843612`, exact Git
blob/SHA-256 identities, annotation meaning, prepared WAVs and candidate settings.
Source: [publisher demo](https://github.com/pnlong/jazzsamba-demo), dataset DOI
[10.5281/zenodo.22943963](https://doi.org/10.5281/zenodo.22943963).

The publisher's written chord targets are aligned to musician-authored bar
grids. They are not note-level performed harmony or individually marked physical
chord attacks. The MP3 web encodings are paired by the publisher; FFmpeg honors
codec delay/padding and prepares exactly 60 seconds from zero without estimated
offsets or endpoint scaling. Leading unannotated gaps remain unknown. Unsupported
rich/slash/altered conversions remain X with their original symbols/fields saved.

| Candidate | Supported-chart major/minor agreement | Broader triad-projection agreement |
|---|---:|---:|
| Baseline | 28.5% | 28.9% |
| BTC | 69.2% | 65.9% |
| CREMA | 64.9% | 61.6% |
| ChordMini | 60.9% | 58.0% |
| Chordino | 57.2% | 55.5% |

Eligible coverage is 83.8% for supported labels and 93.0% for the separately
declared triad projection. The additional coverage includes difficult positions;
scores from different coverage should not be compared as detector improvements.
All fifteen runs and thirty reference-condition comparisons succeed.

The original CREMA/Chordino protocol was frozen before any inference. Baseline,
BTC and ChordMini were added after those outcomes; their unchanged-settings
extension is explicitly retrospective. Input selection and label projections
stay frozen, with no retuning. Training exclusion is unproven. These three jazz
clips support method comparison, not a claim that 69% of rock-song cues are
correct or that corrections are commercially affordable.

BTC deserves continued consideration, while CREMA remains a useful current
prototype draft. Curated repertoire should cache reviewed arrangements instead
of treating an automatic draft as a verified lesson. Correction effort and
ordinary guitar followability remain unmeasured by this comparison.

The dataset licence file could not be retrieved in the bounded official archive
attempt. This is local publisher-released research; neither source music nor
annotations are redistributed in Git, and the Python loader's MIT licence is not
used as an audio licence. Saved local pack:
`experiments/generated/jazzsamba-reference-v1`. Rescore without model runtimes:

```sh
.venv-pilot/bin/python experiments/analysis/jazzsamba_check.py \
  --protocol experiments/generated/jazzsamba-reference-v1/chord-extension-protocol.json \
  --output experiments/generated/jazzsamba-reference-v1/new-extension-rescore.json
```
