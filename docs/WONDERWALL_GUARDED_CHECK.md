# Wonderwall frozen-policy diagnostic

The new guard prevents silent audio from consuming harmonic chart positions in all six runs. It still does not establish a valid recording-specific arrangement: a deliberately reversed chart retains 60.2% / 70.2% of the full recording as chord labels, and the spectral reversed chart reaches every supplied position. **No output is accepted for playback, and no timing or chord-quality accuracy is measured.**

This follows the [previous section hypothesis](WONDERWALL_GUIDED_DRAFT.md) and the [independently frozen acceptance experiment](ACCEPTANCE_SCREEN.md). The 277.7803-second prepared audio, three untimed charts, their 167 supplied positions, and the original six comparison outputs are unchanged. The cached native NNLS packet is reused byte for byte; no new recognition, acquisition, teacher-chart edits, repeat-count changes or threshold selection occurs here.

The `balanced` policy was frozen at `2026-10-11T08:12:46.011066+00:00`, before these diagnostics. Its SHA-256 is `7a75786e45528622a86b5a6998452ef252c908f43a796c80d447c81b259c9ff3`. Quality margin is 0.08, added-tone ratio 0.12, and active-frame support fraction 0.50. All old decoder/grid defaults remain unchanged.

| Hypothesis / evidence | Old labeled coverage | Guarded labeled coverage | N seconds | X seconds / gaps | Old / guarded silent advances | Partial / unvisited | <350ms proposed positions | Near minimum active support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Guided / spectral | 85.4% | 54.5% | 27.77 | 98.56 / 502 | 1 / 0 | False / 0 | 35 | 25 |
| Guided / NNLS | 88.6% | 71.9% | 27.77 | 50.40 / 161 | 5 / 0 | False / 0 | 31 | 25 |
| Reversed order / spectral | 84.3% | 60.2% | 27.77 | 82.71 / 475 | 71 / 0 | False / 0 | 79 | 72 |
| Reversed order / NNLS | 87.3% | 70.2% | 27.77 | 54.88 / 158 | 83 / 0 | True / 15 | 83 | 82 |
| Simplified quality / spectral | 76.0% | 24.5% | 27.77 | 181.87 / 497 | 3 / 0 | False / 0 | 55 | 49 |
| Simplified quality / NNLS | 82.9% | 44.7% | 27.77 | 125.82 / 161 | 5 / 0 | True / 141 | 2 | 2 |

Labeled coverage divides retained non-N/non-X label seconds by the whole recording, including silence. It is not precision, recall, accuracy or harmonic-only coverage. `N` is the original-PCM RMS silence mask; `X` is abstention. Multiple short gaps show output fragmentation, not separately verified errors.

Both guided runs visit all 167 positions and have supporting active audio at every visited position. Their 35 / 31 sub-350ms proposed positions and 25 near-minimum-support positions still warrant caution. The reversed controls retain 79 / 83 sub-350ms positions and 72 / 82 near-minimum-support positions: the previous silent traversal is replaced by compressed progression through active audio. These descriptive counts do not validate section order.

The reversed-NNLS run abstains from the requested endpoint with 15 positions unvisited. The simplified-NNLS run visits only 26 / 167 positions and leaves 141 unvisited; its longest proposed position lasts 124.40 seconds. Partial progress is preserved rather than manufacturing timings for unseen positions. Substantial labels can remain in a partial path, so partial status is not complete chart rejection.

The guided variants mask 38.5% / 19.6% of active audio for quality checks. Without independent full-recording timing and rich-quality truth, we cannot distinguish useful rejection from removal of correct chords. Active dwell uses global template fit before quality masking; endpoint completion and supporting dwell do not verify the final rich chord labels. The player retains its existing automatic CREMA draft.

## Provenance and reproducibility

The six new outputs, exact copied untimed charts, byte-identical NNLS cache, frozen policy, and machine/Markdown summaries are in ignored local directory `experiments/generated/wonderwall-guarded-20261011`. All original JSON, policy and audio hashes were rechecked after inference; none was overwritten. The machine report preserves full output/source hashes, section intervals, masks, compression bins and unvisited indices.

- Prepared audio SHA-256: `88e1649a3efa33647b8a07a7fc5feab2540c588ce35e2f27a3a682f2c4553462`.
- Source section hypothesis SHA-256: `002054d85d182279118ac6673352f5221c0f4a873590f58bf0a30351437d2a3b`.
- Reused NNLS bytes SHA-256: `52766a21e5bbbd2ba0b1e8b14fe24e53910189fd8f0f1066c9fac322900e7ff2`.
- Shared frozen spectral arrays SHA-256: `fd5cee0f1aa1fd9dc2163024eb05852fc8926d4893cbce742a950cec913be084`.
- Guarded aligner SHA-256: `f25536fdf9c56e5fdb0d03e8441c91a60ee91961272afa47011b5b815e24e6b0`.
- Wrapper SHA-256: `1f575f02f082c8aa57928b7c7878061a7b07321bb891d30319f0c895e3e8ef65`.
- Machine summary SHA-256: `06b33a7e1211cb685e0dd44ea6bbb45f28b65823c1598b854b9b34d480459211`.

```sh
.venv-analysis/bin/python experiments/analysis/wonderwall_guarded.py \
  --output experiments/generated/wonderwall-guarded-new \
  --policy-sha256 7a75786e45528622a86b5a6998452ef252c908f43a796c80d447c81b259c9ff3
```

Use a new output directory. The wrapper refuses overwrites, verifies the frozen policy and implementation hashes before inference, validates old paired controls, and shares the same spectral arrays across the six new calls. Existing cached assets are required. It consumes no timed reference and does not retune on this song.

The centered offline acoustic and added-tone windows limit physical chord-change timing precision. Source separation is not used. Short/long dwell bins and near-minimum evidence remain descriptive diagnostics; there is no gold reference that turns them into measured arrangement errors. No change is deployed to the default player.
