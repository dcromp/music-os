# Section and acoustic-evidence diagnostics — 10 October 2026

Ten real-audio alignment drafts compare the same frozen decoder with spectral or native NNLS-Chroma evidence. All are **unaccepted development drafts**, without independently checked timing references. Cycle counts, segment counts and conflict rules are diagnostics, not real-song accuracy scores.

## Full Creep

Both runs use the same full prepared recording and untimed cyclic G–B–C–Cm hypothesis:

| Acoustic method | Path changes | Cycle wraps | Timeline events | Active acoustic conflict |
|---|---:|---:|---:|---:|
| Spectral | 124 | 31 | 827 | 19.8% |
| NNLS | 68 | 17 | 194 | 8.5% |

NNLS reduces cycling and short unknown gaps, but the remaining cycles are unverified. Its wider window may hide or shift changes. Cosine scores behave differently across feature methods, so a smaller conflict percentage does not establish greater correctness. Neither full-song draft is accepted for learner playback.

## First-20-second windows with finite prefixes

Windows were frozen before these runs and cropped at exact PCM frames 0–441000. They are listening conveniences, **not verified section boundaries**. Each uses `end_policy: any`:

- Creep: one candidate G–B–C–Cm pass.
- Wonderwall: up to four candidate F#m7–A–Esus4–B7sus4 loops, preserving sounding pitches and suspensions for the capo-2 shapes.
- House: Am–C–D–F–Am–E–Am–E intro followed by Am–C–D–F. E versus E7 remains a human-source disagreement; this candidate is simplified.

| Window | Acoustic method | Path changes | Timeline events | Active conflict | Unvisited expected positions |
|---|---|---:|---:|---:|---:|
| Creep | Spectral | 2 | 79 | 22.8% | 1 |
| Creep | NNLS | 3 | 23 | 10.2% | 0 |
| Wonderwall | Spectral | 7 | 31 | 3.8% | 8 |
| Wonderwall | NNLS | 7 | 25 | 14.0% | 8 |
| House | Spectral | 11 | 36 | 10.4% | 0 |
| House | NNLS | 11 | 25 | 16.4% | 0 |

Partial end policy allows a window to stop inside its declared prefix. Unvisited positions remain visible rather than forcing late transitions. A finite sequence prevents additional cycles by construction; it does not prove that its count/order is correct. Proposed section intervals are path intervals, not independently checked structure.

On the same 20-second Creep window, unrestricted cycling produced 14 changes / three wraps with spectral evidence and six changes / one wrap with NNLS. The finite candidate limits the draft to four supplied positions. That isolates the effect of a declared prefix while leaving its musical validity to listening review.

## Evidence and next decision

All settings stayed fixed. NNLS extraction consumes no chart or timing reference. Its 92.9 ms hop and 743 ms window are broader than the spectral method; interpolation onto the common 25 ms grid adds no information. The original short-window PCM silence mask remains fixed. Extraction and cached alignment runtimes are recorded separately.

[JSON evidence](REAL_ALIGNMENT_DIAGNOSTICS.json) records all ten runs, hashes, runtimes, unknown durations and diagnostics. [NNLS setup](NNLS_CHROMA_EVIDENCE.md) and [section setup](CHART_ALIGNER_SETUP.md) describe reproduction. The [paired synthetic comparison](ACOUSTIC_ALIGNMENT_COMPARISON.md) remains conditional timing with correct harmony supplied.

Next save a blind listening pass before revealing anonymous charts, then repeat/refine marks before scoring. [Human-source research](REAL_REFERENCE_SOURCES.md) found an Animals corpus reference, but its recording is longer than our import; no timestamp transform or direct score is justified. These familiar windows are development cases. Fresh material remains necessary for held-out validation.
