# Accompaniment review — 18 October 2026

[Ticket #4](https://github.com/dcromp/music-os/issues/4) remains open. This is a source and local-evidence assessment of Brown Eyed Girl, Creep and the selected 269.919-second Animals recording. No audio audition was performed, no excerpt is accepted, and new review suggestions do not change playback cues.

## House warnings

The original five warnings, their native times and their source links remain available under **Online chord checks**. Saved notes distinguish overlapping work from new proposals:

| Native replay span | Disposition | Evidence / next action |
|---|---|---|
| 6.409–15.697 s | Covered by provisional guide | Broad intro-order warning overlaps the two existing E corrections. Its whole window is not an accepted excerpt. |
| 11.146–12.539 s | Covered by provisional guide | E is already displayed provisionally; spectral and NNLS interior comparisons favour E over Em. Bounds remain native. |
| 90.093–93.066 s | E proposal, unapplied | Both methods favour E-family harmony over Em; E7 also fits. Exact voicing and physical changes require review. |
| 123.623–126.502 s | Inconclusive | Spectral favours Em while NNLS favours E. |
| 210.373–211.580 s | Inconclusive | NNLS favours Am; spectral E/Em/Am scores are close. Do not replace every Em with E. |

Five late native Dm cues also favour Dm in both methods. Preserve Am/Dm contrast without transferring the teacher's approximate outro timestamp to this recording. The exact recording identity, scores and unresolved checks are in [the versioned assessment](../catalogue/accompaniment-evidence-20261018.json); [warning annotations](../catalogue/house-warning-reviews-20261018.json) bind each note to its exact original warning, audio and chart.

## Brown and Creep

Brown's three longest native Em cues favour Em over E in both methods. The linked tie exercise motivates a beginner drill with continuous eighth-note hand movement: `D U D U — U D U`; miss the strings on 3 and let the preceding sound ring. This is not a mute or a transcription. The separate easy arrangement's printed 140 BPM does not justify changing the existing ~152 BPM grid or selecting a half/double tempo.

Creep retains B major and C minor in the teaching arrangement. One native Bm cue near 171.270 s favours B in both checks, but the Bm cue near 87.679 s and Bm7 near 172.756 s remain mixed; richer B7/Bm7 comparisons are retained. No blanket relabelling is applied. Practice guidance uses lighter playing followed by fuller strums, with variable verse picking rather than one prescribed recorded arpeggio.

House keeps six eighth-note counts grouped 3+3, two dotted-quarter pulses and gentle beginner anchors on 1 and 4. Root-led picking/raking and optional fingerstyle are distinguished. Small F and a no-capo teaching setup remain proposals; exact recording tuning, phase and contacts are unverified. [Seven rechecked primary teaching resources](../catalogue/accompaniment-source-review-20261018.json) support the practice choices without establishing exact recorded guitar parts.

## Method and limits

The [frozen input specification](../catalogue/accompaniment-quality-spec-20261018.json) selects 44 regions across three exact recordings, including twelve existing fixed coverage samples and directed contrast windows. The diagnostic computes 176 method/window comparisons: spectral and cached NNLS chroma, each over the whole region and its interior. Interior analysis excludes frames whose centered FFT support crosses a requested boundary (~186 ms spectral, ~743 ms NNLS windows). It retains native overlaps and active-duration weighting, and compares explicit alternatives plus all 24 major/minor triads.

Cosine scores are uncalibrated full-mix template similarities, not probabilities or accuracy percentages. Directed windows are model-exposed; they do not supply a representative accuracy estimate. Candidate agreement cannot establish physical timing, guitar contacts, setup or an accepted arrangement. No new inference/model tuning, numbered bars or duration-scaled transfers are introduced.

Actor/source: agent source inspection, diagnostic computation and browser checks only. The quality batch measured 0.7584 seconds of compute with existing caches. Research/editing duration and human review/correction effort were not measured; this is not an authoring-cost estimate. Per-recording status is explicitly deferred pending a capable listening review or independently matched reference.

## Reproduce and serve

From `/Users/davidcrompton/Documents/music-os`, use fresh filenames; both tools refuse overwrites. Cached audio, charts, NNLS and the prior online report must already exist locally; generated media/reports remain ignored.

```sh
.venv-analysis/bin/python -B experiments/analysis/accompaniment_quality_review.py \
  --spec catalogue/accompaniment-quality-spec-20261018.json \
  --output experiments/generated/accompaniment-review-20261018/quality-replay.json

.venv-analysis/bin/python -B experiments/analysis/warning_reviews.py \
  --report experiments/generated/online-chord-checks-20261017-final/report.json \
  --reviews catalogue/house-warning-reviews-20261018.json \
  --output experiments/generated/accompaniment-review-20261018/online-replay.json

.venv-analysis/bin/python -B experiments/analysis/workflow_check.py \
  --policy experiments/fixtures/selected-workflow-player-v5.json
```

Current local deployment:

```sh
.venv-analysis/bin/python -u -B experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-first-ten-v1 --port 8070 \
  --online-checks experiments/generated/accompaniment-review-20261018/online-reviewed-v2.json
```

Open [the normal player](http://127.0.0.1:8070/), select House and expand **Online chord checks**. Stop the server with Ctrl+C. The same original pack, path, step/pattern identifiers and browser-local feedback/progress identities are retained. Reload existing pages to load the new scripts/guide. Temporary port 8071 is used only for QA and stopped afterward. No public service or native app is deployed.

[Verification record](ACCOMPANIMENT_REVIEW_RESULTS.json) records tests, preservation, browser observations and remaining gates. Existing policies v1–v4 remain historical; v5 changes only the two practice/learning guide pins and inherits the other 37.
