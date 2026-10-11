# Automatic full-song drafts

The three imported songs now have complete play-along drafts without a founder
timing annotation step. Playback uses the unchanged CREMA timeline immediately.
Chordino supplies secondary evidence; differences produce optional check spots.
The user can simply play along and report a problem when they encounter one.

CREMA is the initial primary because it performed best on the small acoustic
GuitarSet pilot. That result does not establish its accuracy on these commercial
full mixes. The preparation tool does not vote models into a supposedly verified
answer, rewrite chords to fit a teacher chart, or turn agreement into confidence.

## Current automatic pack

Generated local artifact: `experiments/generated/automatic-playalong/manifest.json`.
Audio and predictions remain ignored by Git; the code and this documentation are
tracked. All timelines use the exact prepared WAV's clock and full duration.

| Recording | Duration | Primary segments | Root agreement | Major/minor agreement | Merged flags | Optional check spots |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Radiohead — Creep | 236.635 s | 52 | 94.2% | 85.6% | 30 | 8 |
| Oasis — Wonderwall | 277.780 s | 144 | 64.6% | 64.3% | 84 | 8 |
| The Animals — House of the Rising Sun | 248.546 s | 138 | 88.6% | 78.7% | 34 | 8 |

These percentages compare CREMA with Chordino, not with a correct chart. Root
coverage is respectively 96.4%, 89.5%, and 100.0% of prepared audio; major/minor
coverage is 94.6%, 87.7%, and 100.0%. No-chord, unresolved labels, and unsupported
quality comparisons are excluded from the appropriate denominator. The full
evidence JSON records coverage and comparison rules beside each fraction.

Creep also includes the existing full-song NNLS cyclic chart as an advanced
alternative hypothesis. Its supplied four-chord cycle and extra boundaries are
not evidence that it is correct. The short Wonderwall and House intro alignments
are excluded from this full-song pack because their IDs, audio hashes, and scope
do not match the full recordings. Chordino and additional charts never alter the
primary timeline.

Wonderwall includes a separate teacher-guide capo suggestion of 2; the other two
use 0. Raw detected labels remain sounding pitches, including inversions and
extensions. Any capo-shape display is a practice view rather than recorded-harmony
ground truth. Guide URLs and this distinction are included in manifest metadata.

The first founder feedback and [Wonderwall vocabulary audit](WONDERWALL_QUALITY_AUDIT.md)
identify a specific limit: CREMA cannot emit add9 or 7sus4, and the default
Chordino dictionary lacks those and suspensions. A capo view preserves whatever
quality was detected; it cannot supply a missing extension. [Rich-quality
controls](RICH_QUALITY_SCREEN.md) and [six Wonderwall hypotheses/controls](WONDERWALL_GUIDED_DRAFT.md)
are complete. Wrong extensions/order can survive current acceptance rules,
so the guided hypothesis remains a research artifact and does not replace
the primary player timeline.

## Build and run on Mac

From the repository checkout with `.venv-analysis` already installed:

```sh
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py build \
  --manifest experiments/generated/youtube-pilot/manifest.json \
  --output experiments/generated/automatic-playalong \
  --additional radiohead-creep-youtube-20261010=experiments/generated/real-alignment-v2/creep-full-nnls-cyclic.json

.venv-analysis/bin/python experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-playalong --port 8068
```

The build is a local, cached operation; it does not download audio or run model
inference. Choose a new output directory for a later build: existing packs are
never overwritten. The optional `--additional` argument may be omitted. Every
additional chart must describe the same complete prepared recording.

Open [the automatic player](http://127.0.0.1:8068/). The server binds only to
localhost and serves the player, manifest, and explicitly listed audio/chart/
evidence assets. Build specifications and other project files are outside its
allowlist. Symlink escapes and hard-link aliases to private pack files are
rejected, including checks on each request.

## Artifact contract

The manifest schema is `automatic-drafts-1.0`, with `gold: false`. Each case has
`id`, `name`, `recording`, `audio_url`, `primary_url`, `evidence_url`, `secondary`,
optional `additional`, `summary`, `source`, artifact hashes, and a zero-offset
source origin. `recording` contains the original ID, duration, sample rate, and
audio SHA-256. `primary.json` and `chordino.json` are byte-for-byte copies of the
saved version-1 chord charts, including native labels and uncalibrated native
scores when present. Preparation creates no new confidence score.

`evidence.json` uses `automatic-draft-evidence-1.0` and carries the same recording
identity. It contains comparison metrics, explicit parameters and semantics,
all raw label-disagreement spans, merged `flags`, and bounded `review_points`.
Review points contain `id`, `flag_id`, `start_seconds`, `end_seconds`, a prose
`reason`, and the stable `priority_kind`:

- `root_disagreement`: different enharmonic chord roots.
- `majmin_disagreement`: same root but supported major/minor families differ.
- `no_chord_disagreement`: one model predicts `N` and the other harmony.
- `unresolved_label`: a model predicts an unresolved or unparseable label.
- `boundary_disagreement`: an unpaired change within a 0.5-second tolerance.

Root comparison ignores inversions only for the metric. Major/minor comparison
reduces explicitly supported chord families; suspended, diminished, augmented,
power, and unknown qualities are excluded rather than silently made major.
Native chart labels retain all those distinctions. Changes are matched one to
one. Matching a boundary does not verify its musical timing.

Same-kind spans separated by at most 0.4 seconds merge; spans shorter than 0.4
seconds stay in the raw audit evidence without becoming label-warning work.
Check spots are selected by kind and then longest span, at least eight seconds
apart, with a maximum of eight six-second windows per recording. This is a simple
workload heuristic. Flags can occur where the primary is correct, and shared
errors can survive agreement. None of these checks block playback or require
the founder to annotate a song.

## Verification

Ten offline tests cover exact audio and model pairing, contiguous full-duration
coverage, preserved prediction bytes/native labels, different roots versus
major/minor qualities, unsupported-quality coverage, silence and unresolved
labels, shared-error semantics, one-to-one boundary matches, bounded optional
checks, failed-build cleanup, no-overwrite behavior, additional hypothesis scope,
and server allowlist/private-alias guards. The three-song build completed with
all source and copied-artifact hashes checked.

Source acquisition provenance remains in each case. House of the Rising Sun's
selected upload comes from an unofficial tribute channel. These are requested
local experiments; technical acquisition success does not establish commercial
distribution clearance. Accuracy evaluation continues through the automated
annotated-data screen, separate from ordinary play-along feedback.
