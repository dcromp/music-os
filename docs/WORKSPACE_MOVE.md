# Canonical Documents checkout

Completed 13 October 2026. Continue all work from `/Users/davidcrompton/Documents/music-os`. This is a Git repository on `codex/mac-analysis-phase0`, tracking `origin/codex/mac-analysis-phase0`; origin is `https://github.com/dcromp/music-os.git`. The existing draft PR remains [PR 1](https://github.com/dcromp/music-os/pull/1).

Source, plans, experiment tools/tests and historical preparation helpers are committed. Research audio, model weights, generated results, node modules and Python environments are saved locally and ignored by Git. They are needed for local research but are not source files to push into the repository.

The transfer verified 151,954 file/symlink entries and 6,356,031,501 file bytes. It includes every source research asset/pack, new model environment, node dependencies and the complete 60 MB Python 3.11 runtime used by CREMA. Existing durable analysis, YouTube and pinned scoring environments were retained. Disposable Python bytecode caches were omitted.

Eighty-three runtime text files were relocated. CREMA now points to `.runtime/cpython-3.11.13-macos-aarch64-none`, inside this checkout; console script shebangs and environment activation paths also point here. Native Chordino/NNLS executables have no temporary library dependencies. Historical JSON provenance remains unchanged, including old paths recorded when those runs occurred.

Three differing older local outputs were preserved before replacing their working copies: `baseline.json`, `metrics.json` and the initial GuitarSet pilot `report.json`. Their previous bytes are in `.migration-backup/2026-10-13/`. The complete transfer manifest and temporary research notes are in `experiments/local-research-notes/2026-10-13/`. One-off preparation/migration source scripts are committed under `experiments/archive/2026-10-13/`; current supported commands remain in the root README.

Verification covers copied hashes, relocated environment imports/entry points, canonical Python prefixes, native library paths and the full analysis checks plus dependency-specific checks. No model inference or player change was required for moving the workspace. The three source-separation runs are complete; nine derivative/resampling-control BTC runs remain pending, with accurate status in [SEPARATION_CHECK.md](SEPARATION_CHECK.md).

Restart the existing player from this folder:

```sh
cd /Users/davidcrompton/Documents/music-os
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py serve --pack experiments/generated/automatic-first-ten-v1 --port 8070
```

The tool serves localhost only. A Git push updates source and the draft PR; it does not create a public web deployment.
