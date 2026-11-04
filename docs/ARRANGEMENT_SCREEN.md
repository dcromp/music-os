# Arrangement sequence diagnostic

25/25 cached comparisons completed. No chart is approved for playback.

The unrestricted acoustic chord sequence receives no chart order or repeat counts. Its global argmax is verified identical across each recording's controls. The stable view deletes runs shorter than 150ms; it never replaces labels or fills gaps. These are descriptive comparisons, not calibrated acceptance.

| Recording / chart | Source | Stable runs / chart runs | Raw / stable edits | Stable audio coverage | Matched stable duration | Mechanical failure |
|---|---|---:|---:|---:|---:|---|
| fresh-section_repeat-slow_arpeggio / correct | guarded-global-argmax | 16 / 9 | 19 / 9 | 46.6% | 52.4% | False |
| fresh-section_repeat-slow_arpeggio / wrong_section_order | guarded-global-argmax | 16 / 9 | 21 / 12 | 46.6% | 24.0% | True |
| fresh-section_repeat-slow_arpeggio / missing_repeat | guarded-global-argmax | 16 / 6 | 22 / 11 | 46.6% | 44.7% | True |
| fresh-section_repeat-slow_arpeggio / extra_repeat | guarded-global-argmax | 16 / 12 | 18 / 8 | 46.6% | 68.8% | True |
| fresh-section_repeat-soft_strum / correct | guarded-global-argmax | 10 / 9 | 10 / 2 | 51.5% | 79.8% | False |
| fresh-section_repeat-soft_strum / wrong_section_order | guarded-global-argmax | 10 / 9 | 13 / 8 | 51.5% | 18.9% | True |
| fresh-section_repeat-soft_strum / missing_repeat | guarded-global-argmax | 10 / 6 | 13 / 4 | 51.5% | 58.1% | True |
| fresh-section_repeat-soft_strum / extra_repeat | guarded-global-argmax | 10 / 12 | 9 / 5 | 51.5% | 79.8% | True |
| fresh-section_repeat-short_decay / correct | guarded-global-argmax | 14 / 9 | 18 / 5 | 56.0% | 86.4% | False |
| fresh-section_repeat-short_decay / wrong_section_order | guarded-global-argmax | 14 / 9 | 23 / 11 | 56.0% | 36.5% | True |
| fresh-section_repeat-short_decay / missing_repeat | guarded-global-argmax | 14 / 6 | 21 / 8 | 56.0% | 46.8% | True |
| fresh-section_repeat-short_decay / extra_repeat | guarded-global-argmax | 14 / 12 | 18 / 6 | 56.0% | 73.7% | True |
| fresh-section_repeat-bass_melody / correct | guarded-global-argmax | 11 / 9 | 9 / 2 | 51.7% | 94.8% | False |
| fresh-section_repeat-bass_melody / wrong_section_order | guarded-global-argmax | 11 / 9 | 13 / 7 | 51.7% | 32.7% | True |
| fresh-section_repeat-bass_melody / missing_repeat | guarded-global-argmax | 11 / 6 | 12 / 5 | 51.7% | 69.3% | True |
| fresh-section_repeat-bass_melody / extra_repeat | guarded-global-argmax | 11 / 12 | 9 / 3 | 51.7% | 98.5% | True |
| oasis-wonderwall-youtube-20261010 / guided | global-argmax | 466 / 164 | 652 / 332 | 80.2% | 36.7% | False |
| oasis-wonderwall-youtube-20261010 / guided | crema | 142 / 164 | 47 / 47 | 89.5% | 82.4% | — |
| oasis-wonderwall-youtube-20261010 / guided | chordino | 90 / 164 | 107 / 107 | 91.6% | 72.8% | — |
| oasis-wonderwall-youtube-20261010 / reversed-order | global-argmax | 466 / 165 | 680 / 359 | 80.2% | 27.1% | True |
| oasis-wonderwall-youtube-20261010 / reversed-order | crema | 142 / 165 | 75 / 75 | 89.5% | 68.3% | — |
| oasis-wonderwall-youtube-20261010 / reversed-order | chordino | 90 / 165 | 115 / 115 | 91.6% | 65.8% | — |
| oasis-wonderwall-youtube-20261010 / simplified-quality | global-argmax | 466 / 164 | 671 / 339 | 80.2% | 36.0% | True |
| oasis-wonderwall-youtube-20261010 / simplified-quality | crema | 142 / 164 | 28 / 28 | 89.5% | 93.0% | — |
| oasis-wonderwall-youtube-20261010 / simplified-quality | chordino | 90 / 164 | 91 / 91 | 91.6% | 85.0% | — |

## Synthetic ranking check

- raw: correct chart strictly has fewer edits than all three corrupt controls in 0/4 recordings; 2 recordings have a wrong control with fewer edits, and 2 have ties.
- stable: correct chart strictly has fewer edits than all three corrupt controls in 3/4 recordings; 1 recordings have a wrong control with fewer edits, and 0 have ties.

Lower edit distance and a mechanically complete path do not identify a correct chart. No score threshold is selected, and the raw/stable outcomes both remain in the report. A dash denotes no constrained-path mechanical check for a raw recognizer. Full edit traces, ignored duration and indistinguishable chart positions are saved in each diagnostic beside the summary, with hashes in the committed compact JSON.

## Limits

- Four procedural section recordings and Wonderwall were already exposed; this is a diagnostic, not fresh validation.
- Global argmax is independent of supplied chart order but uses the same chroma/templates; CREMA/Chordino are additional imperfect evidence, not gold.
- Unit-cost edit distance favors fewer edits, not verified arrangements; a wrong control can rank best. No threshold or filter is fitted here.
- Stable view discards runs below the declared 150ms without relabeling, bridging gaps or merging across discarded runs; real fast changes may be lost.
- Silence, unknown and unsupported intervals are excluded from harmonic comparison with duration coverage retained; confidence and correctness cannot follow from agreement.
- Bass and removed extensions are not verified; adjacent identical core positions cannot supply a repeat count.
- Mechanical failures make the constrained path incomplete. Mechanical success never approves playback.
- The full Wonderwall chart is a teacher-based, version-unverified section/count hypothesis with no timing reference.

## Reproduce

```sh
.venv-analysis/bin/python experiments/analysis/arrangement_screen.py --output experiments/generated/arrangement-screen-new
```

Uses the saved acceptance-validation, verified Wonderwall guard and original song detector packs. Choose a new directory; no models, acquisition, reference editing or founder transcription are required.
