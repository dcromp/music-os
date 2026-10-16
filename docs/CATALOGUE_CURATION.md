# Starter catalogue preparation and separate corrections

Updated 14 October 2026. **Stage 2 is in progress: automated preparation and the correction workspace are complete; recording acceptance is pending.** Ten exact cached recordings have source-guided worklists and a separate developer reviewer. The later [first-four continuation](STARTER_FOUR_CATALOGUE_CHECK.md) adds source notes and two provisional label edits. This page records the preceding tooling checks; its [machine-readable evidence](CATALOGUE_CURATION_RESULTS.json) remains historical. No accepted arrangements, human correction minutes or recording accuracy scores follow from these milestones.

## What is prepared

The workspace contains 2,024.1 seconds of audio, unchanged native BTC/CREMA charts, 118 suggested replay windows and 32 project-authored grip examples across eight rhythm-song palettes. The two riff tracks retain distinct riff/section work items rather than invented strumming grips. Forty replay windows are fixed coverage samples, including places where both models might share an error; the other 78 come from bounded model disagreements. Short events, disagreement counts and their union duration are workload hints, not verified errors or correction cost.

Every worklist joins the selected recording's ID, audio SHA-256, sample rate and duration to the existing teaching-source context. Building and serving verify native chart hashes, contiguous paired outputs and exact WAV identity. New files copy the cached audio/chart bytes; the selected pack and normal player's charts stay unchanged. The existing Stage 1 verifier still checks all 39 frozen files.

Grip examples list six strings from low to high, with `x` for mute and `0` for open. Symbolic checks verify each declared pitch-class set and lowest bass note in standard tuning; the source palette states any uniform retuning/capo assumption separately. An unconfirmed capo leaves sounding pitches unspecified. Wonderwall includes Em7, Dsus4, A7sus4, Cadd9 and G/F# examples; capo 2 changes the sounding pitches while preserving the played shape. These checks do not establish the exact recorded voicing, physical playability, transition difficulty or audible suitability.

The supplementary [source update](../catalogue/curation-source-updates.json) corrects earlier Wonderwall meter wording without rewriting the frozen source report. Inspected [Carl Brown lesson text](https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/) and [Greg Shute teaching PDF text](https://www.gregshuteguitar.co.uk/_files/ugd/4079b4_0a1b39a89c1a4776a5c8f553f259cb08.pdf) support capo-2/setup and section distinctions, but do not establish specific 4/4-to-2/4 changes in the selected upload. Keep its exact local meter unverified and bar estimates disabled until checked. No lyrics, full third-party charts or transcribed tabs were added.

## Run and use the developer reviewer

The clean workspace is running locally at [port 8073](http://127.0.0.1:8073/). It is content-preparation tooling. The founder can keep using [ordinary play-along on port 8070](http://127.0.0.1:8070/) with no transcription assignment.

After reboot, from `/Users/davidcrompton/Documents/music-os`:

```sh
.venv-analysis/bin/python experiments/analysis/curation.py serve \
  --pack experiments/generated/catalogue-curation-20261014 --port 8073
```

To prepare another workspace from the existing selected native outputs, use an unused output directory. Existing outputs are not overwritten:

```sh
.venv-analysis/bin/python experiments/analysis/curation.py build \
  --output experiments/generated/catalogue-curation-next
```

Defaults select `automatic-first-ten-selected-v1`, the frozen first-ten source context and the separate source-attribution update. Building needs the local ignored inputs, not model inference. Stop a foreground server with Ctrl+C. Servers bind only to `127.0.0.1`; this is not public hosting or an installed background service. Source pushes do not transfer caches/drafts or deploy servers.

Choose a recording and inspect its source work items. Suggested windows replay bounded spans; **Go to seconds** handles exact seeking. Switch between working corrections, raw BTC and raw CREMA. A sounding-chord replacement applies only to the entered half-open interval; gaps, no-chord `N`, unknown `X` and native intervals outside it are preserved. Capo-relative teaching shapes belong in setup notes, not in sounding-label corrections.

Sections and setup/rhythm notes are separate draft content. A checked replay window only records inspection of that window. Neither edits nor checkboxes approve a whole song or create independent reference labels. This workspace deliberately has no lesson-promotion action.

**Save separate draft** writes atomically to the pack's ignored `private-drafts/<recording-id>.json` directory. Pack, recording and native chart identities must match. A stale revision returns 409 and leaves unsaved in-tab work available for **Export draft backup**. Private drafts are not served as static files, and the API rejects cross-origin writes, unsupported bodies, duplicate JSON fields and nonfinite values. This local draft store has no public authentication/hosting design.

## Correction effort

Review time begins only with an explicit **Start review** and reviewer choice: human, agent or QA. **Pause review**, save, export and recording changes finish the active session. Leaving the window or hiding the page pauses and attempts a save. With playback paused, a minute without interaction triggers a pause; continuous playback refreshes activity. A session is capped at 30 minutes. Playback time is retained after an automatic song ending; delayed idle checks exclude time beyond the cutoff.

The 60-second idle grace can include inactive time and is not proof of continuous attention. This measures declared session time rather than exact hand-on-keyboard editing. Agent and QA sessions never contribute to human correction cost. Automated pack building and symbolic grip checks do not start review sessions. The preceding tooling verification had no saved sessions/corrections. The [first-four continuation](STARTER_FOUR_CATALOGUE_CHECK.md) now has explicit agent draft-entry sessions, four note drafts and two provisional labels. These short entry sessions exclude source research, automated analysis and musical validation; **human correction cost remains unmeasured**, with no minutes-per-audio-minute estimate.

## Verification completed

- Python: 360 discovered, 340 passed, 20 optional-dependency skips. New coverage includes 15 curation and six grip tests: exact pairing/copying, malformed recording metadata, startup tampering, bounded edits, revision conflicts, isolated storage/routes and actor-specific effort.
- JavaScript: 124 checks passed—62 existing play-along, 48 bench and 14 curation checks. New tests cover exact replacement spans, raw preservation/gaps, rich labels, draft identity, long playback followed by idle, delayed idle cutoffs and the session cap.
- Live isolated QA: dummy chord/section/notes saved and survived reload; seeking to the edited span differed from raw BTC at the same audio time. Changing songs paused/saved QA sessions and cleared transient fields. A bounded replay followed by inactivity saved a full 74.0-second QA session with human review still unmeasured. Test data is explicitly QA-only and stays in separate ignored packs.
- Deployment/isolation at the tooling verification: all 45 public reviewer assets matched disk, five private/repository route probes returned 404 and all ten normal drafts were blank. The later first-four pass now has four saved drafts and two provisional labels. The existing port-8070 player's 48 assets and manifest identity are unchanged. Ports 8067/8068 remain available. Temporary reviewer QA servers on ports 8074/8075 were stopped after checks.

Verification of software behavior does not certify musical accuracy. The 20 skipped checks require separate optional evaluation/separation environments; earlier runs are historical evidence, not fresh passes in this run. No fresh inference or public deployment was performed.

## Remaining Stage 2 work

| Step | Status | Indicative remaining effort |
|---|---|---|
| Exact inputs, automatic worklists and source-guided grip proposals | Complete | Evidence above; no recording acceptance implied |
| Separate correction persistence, explicit review timer and live QA | Complete | Developer reviewer available on port 8073 |
| First four source/pitch pass and provisional content | Complete diagnostic | Four teaching proposals/note drafts; two provisional Dylan G labels after controlled vocal-removal checks |
| First four physical timing, contrast and rhythm review | Next | Roughly half a focused day; note drafts and native bounds are not accepted timings |
| Contrasting rhythm/riff and setup/section checks | Pending | Roughly one focused day; investigate actual audio and retain unresolved spans |
| Independent recording checks and correction-effort report | Pending | Roughly half to one focused day; source availability can extend elapsed time |
| Founder practice usefulness trial | Stage 3 pending | Two-week elapsed trial after representative arrangements are checked |

The next recording/arrangement pass remains estimated at **1.5–2.5 focused days**, excluding unavailable-source waiting. Check selected-upload pitch/setup, sounding harmony versus played shapes, physical change timing, section coverage and suitable rhythm. Keep independent reference matching separate from model-exposed editorial corrections; unproven master/time-origin pairs receive no accuracy score. Riff songs and Wonderwall require distinct treatment. Promotion into learner playback will need reviewed arrangement evidence and preserved feedback/progress identity. No founder input currently blocks the next technical work, and manual transcription is not required.
