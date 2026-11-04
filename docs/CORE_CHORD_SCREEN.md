# Core-chord retrospective screen

48/48 saved CREMA/Chordino outputs rescored. No new inference, relabeling of saved charts, timing changes or independent validation.

The display rule removes selected extensions: Em7 → Em, Cadd9 → C, A7sus4 → Asus4. Suspensions remain distinct from major/minor chords. This is a simpler teaching task; higher agreement does not mean a more accurate detector.

| Candidate / family | Cases | Exact quality | Core quality | Root | Extension differences ignored | Remaining suspension/third errors |
|---|---:|---:|---:|---:|---:|---:|
| chordino | 24 | 61.5% | 72.8% | 83.9% | 32.876s | 34.338s |
| chordino/family/plain_control | 8 | 95.4% | 95.4% | 95.4% | 0.000s | 0.000s |
| chordino/family/rich_progression | 8 | 36.0% | 55.3% | 68.3% | 15.797s | 10.652s |
| chordino/family/same_root_contrasts | 8 | 53.0% | 67.7% | 88.1% | 17.078s | 23.686s |
| crema | 24 | 61.0% | 73.8% | 83.4% | 38.295s | 28.838s |
| crema/family/plain_control | 8 | 92.5% | 92.5% | 92.5% | 0.000s | 0.000s |
| crema/family/rich_progression | 8 | 42.8% | 60.9% | 66.7% | 14.816s | 4.705s |
| crema/family/same_root_contrasts | 8 | 47.7% | 67.9% | 91.1% | 23.479s | 24.133s |

Equal case means and duration-weighted interval overlap on reference harmonic time; core retains root/minor/suspension distinctions. Exact/core primary metrics omit bass, with bass scored separately. N/X/gaps/unsupported predictions cannot earn quality credit.

Additive seconds, duration-weighted rates, bass-aware rates, N/X/gap/unsupported coverage and condition/split subsets are preserved in JSON. Exact-quality accounting is checked against every original saved score, and every source hash is checked again after scoring.

## Limits

- This easier teaching task intentionally stops assessing selected extension differences; the detector itself is unchanged.
- Removing chord tones is a harmonic convention, not verification of fingering difficulty, song identity or substitute suitability.
- D versus Dsus4 and A versus Asus4 stay different; diminished, augmented, power and undeclared qualities stay unchanged.
- All 24 procedural recordings were previously scored; this is not fresh validation or real-song accuracy.
- Suspensions may be easier shapes than their corresponding major chord. Difficulty needs actual guitar fingerings and transitions.
- No source separation, key assistance, alignment or boundary correction is introduced.

## Reproduce

```sh
.venv-analysis/bin/python experiments/analysis/core_chord_screen.py --output experiments/generated/core-chord-screen-new
```

Requires the saved v2 rich-quality fixture and recognition packs; no model environment is needed. Choose a new output directory.
