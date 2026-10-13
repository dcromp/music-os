# Suggested practice path on the Mac player

Implemented 13 October 2026. The existing automatic play-along player now has
an optional eight-song rhythm path, using the reviewed first-ten proposal.
The visible label is **“Provisional order; choose any song.”** These are
practice suggestions. The order has not been measured against beginner
performance, and the teaching arrangements remain distinct from unreviewed
automatic recording charts.

| Step | Song | Entry focus | Existing starting drill |
|---:|---|---|---|
| 1 | Wild Thing | Steady open-chord changes | `steady-down` |
| 2 | Love Me Do | G/C/D changes; mutes and swing later | `steady-down` |
| 3 | Knockin’ On Heaven’s Door | Add Am while keeping changes steady | `steady-down` |
| 4 | Brown Eyed Girl | Down/up motion through changes | `steady-down` |
| 5 | Twist And Shout | D/G/A at a quicker feel | `steady-down` |
| 6 | House Of The Rising Sun | Six eighth counts grouped 3 + 3 | `six-anchor` |
| 7 | Wonderwall | Shared-finger shapes before syncopation | `steady-down` |
| 8 | Creep | Barre grips and C major → C minor | `steady-down` |

On a fresh page load, the player resumes the first available unpractised step,
falling back to the first path step when all are marked. It does not autoplay.
A song choice, seek or playback during optional metadata loading takes priority
over automatic resume. Missing or invalid metadata retains the existing initial
song choice.

The card shows a skill focus, useful prerequisites, a qualified setup note and
links to the previously reviewed primary teaching sources. **Use starting
drill** selects the song’s existing strumming exercise and brings its counts/arrows into view. It does not start
audio, alter timing, change chord display/transposition, or claim to reproduce
the recorded pattern. The existing pattern selector still offers later drills.

**Try next** selects the next available song after the current step that has
not been marked practised. It skips marked steps and wraps to earlier gaps.
Users can choose any song directly. If no other unpractised step remains, the
button is disabled; progress is never reset automatically. A smaller song pack
retains its matching steps and original step numbers, with an explicit available
step count.

Seven Nation Army and Come As You Are show separate riff guide cards. They have
no path checkbox or strumming-drill button. The guide distinguishes original
Open A from the standard-tuning Seven Nation Army adaptation, and D standard
for the Come As You Are studio lesson. The card states that chord labels and
strumming arrows do not teach the riff’s notes or fingering. These setup notes
do not assert an independently measured pitch match for the prepared audio.

## Optional progress

**Practised this step** is a reversible self-report that the user tried the
exercise. It is not mastery, a skill assessment, accepted chord/timing truth or
an arrangement review. Playing to the end does not mark a step.

Progress uses a separate `music-os-practice-progress:` browser-storage namespace
containing the path ID, revision, playback pack ID, step ID and audio SHA-256.
Saved values also identify the recording ID, sample rate and duration. They
cannot be transferred silently to another path, pack or audio version. Changed
teaching content should receive a new path revision.

Progress remains on this browser on this Mac. Invalid or blocked storage falls
back to unmarked state with an honest message; subsequent changes stay in the
tab when writing is unavailable. The player has no account synchronization or
progress export yet. Existing issue feedback, manual annotations, exposure
history and their storage identities are unchanged.

## Data and deployment

[learning.json](../experiments/review/learning.json) is tracked teaching
metadata, separate from generated playback manifests and detector outputs.
Its three input pins are:

| Input | SHA-256 |
|---|---|
| `catalogue/first-ten-review.json` | `d1bbcd7618e0aeaf4af954c6b2bc7307d1ea4b3378af55ed172e53c0b18d7bda` |
| `docs/FIRST_TEN_ARRANGEMENT_CHECK.json` | `5a7855d9c837e6086a511a896872476fed8dea76da6d6e289438729380d211ae` |
| `experiments/review/practice.json` | `0de69b0756570a7083d9796ddba181d70b80444965eacf382531909c0666c4ea` |

Every learning entry contains the exact recording ID, prepared-audio SHA-256,
sample rate and duration from the arrangement snapshot. Each rhythm step refers
to an existing drill on the same recording. The metadata contains no inferred
riff notation, chord events, beat timestamps or section timings.

The automatic player server allows the fixed optional `/learning.json` route.
After a server restart and page reload, the canonical ten-song command is:

```sh
cd /Users/davidcrompton/Documents/music-os
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-first-ten-v1 --port 8070
```

The page waits for optional strumming metadata before validating drill
references. A missing or invalid learning file, incompatible recording identity,
or unavailable referenced drill hides the learning card while audio/chord
playback and issue feedback remain available. The browser does not fetch the
pinned source documents or contact teaching sites automatically. Teaching links
open only when clicked and must be public HTTPS URLs without credentials.

## Verification

`node experiments/review/test.js` passes **62 checks**, comprising the 47
existing checks and 15 added learning/progress checks. New checks cover input
source hashes and recording identities, order/subset behavior, duplicate and
malformed metadata, wrong drill/audio pairing, unsafe URLs, reversible progress,
storage isolation and failure, next-song behavior and unchanged charts/feedback.

The live ten-song player on port 8070 passes browser verification for initial path, drill selection/visibility, next song, persisted resume, reversal, separate riff guidance, playback, seeking and Core chords. Progress and an explicitly synthetic issue report survive independently in the isolated port-8071 QA pack; no synthetic progress/issues were added to normal players. The original port-8068 player correctly retains its two exact matching path recordings. All 48 served assets match canonical bytes; private-route samples return 404. Ten audio files and twenty detector charts remain byte-identical to preparation inputs. The full standard Python suite runs 324 checks with 20 dependency skips; those dependency-specific checks also pass in their pinned environments. [Verification pins](PLAYALONG_LEARNING_PATH_RESULTS.json) and a local screenshot in `experiments/generated/player-proof-20261013/practice-path.jpg` preserve the evidence. These
focused helper results do not establish beginner learning outcomes or full-mix
chord accuracy.
