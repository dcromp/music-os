# 0001 Repeat timing: one module, two measures

Date: 27 October 2026. Status: accepted (founder, #42). Does **not** reopen the frozen algorithm selection in [ALGORITHM_SELECTION.md](../ALGORITHM_SELECTION.md).

## Context

Two places judged whether repeated chord changes land on a consistent beat:

- The Strum Along exporter's **timing fix** (`strumalong/tools/build-songs.js`, 25 Oct) moves a change one beat when its repeats agree.
- The catalogue checker's **timing consistency** check (`experiments/analysis/strumalong/catalogue_checks.js`) feeds its pass/flag/fail verdict.

They gave the same song different numbers. Measured on 27 Oct over the 43 shipped songs, with both reading the same unfixed chart (evidence on #42): the exporter calls 191 changes one beat off, the checker 32 deviants, 17 of them in both. Of the exporter's 51 moves, the checker calls 10 about a beat off, and only 11 shift the change by 0.75 beat or more in time. The other 40 are rounding snaps.

The difference is what each measures:

| | Drawn timing (exporter) | Played timing (checker) |
|---|---|---|
| Position | integer beat the app draws, under the exporter's bar anchors | fractional beat-grid position mod beats per bar |
| Group key | 4-chord context over the Core default-view holds | from>to chord-family pair over family runs |
| Usual position | most common integer position | densest circular cluster (±0.5 beat) |
| Off | any other position (moves only exactly one beat) | 0.75–1.5 beats from the cluster; shift runs excluded |

A change at 0.45 beat against repeats at 0.55 is drawn on a different beat, but it sits in the same place in the audio grid. The fix is about what the learner sees; the verdict is about whether the chart disagrees with itself.

## Decision

1. **Keep both measures, behind one module**: `strumalong/lib/repeat-timing.js` (UMD, `window.StrumRepeatTiming`). It owns grouping by key, both judgements (`drawnGroups`/`drawnConsistency`/`drawnOffset`, `playedJudgement`/`usualPosition`) and both key builders (`contextKey`, `pairKey`). Callers keep turning their own timeline into positioned changes, so their change extraction is unchanged. The exporter uses drawn timing for the fix. The checker uses played timing for its verdict.
2. **No frozen behaviour changes.** The exported songs and `docs/STRUMALONG_CATALOGUE_CHECKS.json` stay byte-identical (`build-songs.js --check`, `catalogue_checks.js --check`). Replacing either measure with the other is an algorithm change: (a) would fail La Bamba, Boulevard of Broken Dreams, Bye Bye Love and raw Stir It Up against the 80% line; (b) would drop about 40 shipped snaps across about 25 songs. Either needs its own decision and evidence.
3. **One blip line**: `lib/core.js` `QUICK_BEATS` (0.75). The exporter's `BLIP_BEATS` and the checker's `plausibility.blip_beats` read it. The checker's 0.8-beat gap tolerance is a separate setting.
4. **One correction shape**: the module builds the `auto-timing` entry (`correction`) and reads it (`readCorrections` for the checker, `describe` for the app's Details).
5. **Exclusion stays manual.** `catalogue.json` `exclude` is a person's call and the excluded set is the checker's labelled negatives. The exporter only warns when the checker report on disk fails a shipped song. The checker itself still exits non-zero then.

## Consequences

- Two consistency numbers per song remain, but they are named measures from one place. Tables should say "drawn" or "played".
- A change to either measure is a change to `lib/repeat-timing.js` and shows up in both `--check` runs.
- Neither measure is an independent timing reference: both compare a chart with itself on an estimated grid.
