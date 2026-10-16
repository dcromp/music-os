# First ten: versions, practice proposals and automatic drafts

Checked 11 October 2026. Ten selected recordings are prepared, with CREMA and
Chordino automatic drafts. Recording selection and a first teaching-source
review are complete. Full-mix accuracy and complete arrangements remain
unmeasured; the proposed practice tracks are not released lessons.

The [selection specification](../catalogue/first-ten-review.json) is the frozen
pre-acquisition checkpoint pinned by the batch SHA-256. Its metadata-only status
records what was known before acquisition. Current results are in
[the evidence snapshot](FIRST_TEN_PREPARATION.json). Teacher chords, keys, capo
and proposed order were withheld from both detectors. Teacher charts are not
timed reference truth.

## Proposed practice tracks

These orders are project proposals based on the described skills. They need
recording-compatible shape, transition and rhythm checks before becoming app
lessons. Each richer step follows a simpler entry exercise. A few chords can
require difficult barres or rhythm; extensions can preserve useful shared fingers.

| Rhythm order | Song / selected performer | Entry exercise → later work | Primary teaching source |
|---:|---|---|---|
| 1 | Wild Thing / The Troggs | A/D/E changes → contrasting open-string figure | [Andy Guitar](https://www.andyguitar.co.uk/videos/electric-guitar-day-7-wild-thing) |
| 2 | Love Me Do / The Beatles | G/C/D on-beat strums → swing and muting | [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-01-love-me-do) |
| 3 | Knockin' On Heaven's Door / Bob Dylan | G/D/Am/C, slow steady changes → subdivisions and optional picking | [Jon MacLennan](https://www.jonmaclennan.com/blog/knockin-on-heaven%27s-door-chords) |
| 4 | Brown Eyed Girl / Van Morrison | G/C/D/Em accompaniment → down/up groove, optional intro lead | [Andy Guitar](https://www.andyguitar.co.uk/videos/brown-eyed-girl-by-van-morrison) |
| 5 | Twist And Shout / The Beatles | D/G/A with quicker changes → eighth-note build and optional riff | [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-02-twist-and-shout) |
| 6 | House Of The Rising Sun / The Animals | Am/C/D/small F/E, count six eighths → raked arpeggios and outro Dm | [Jon MacLennan](https://www.jonmaclennan.com/blog/house-of-the-rising-sun-guitar-lesson) |
| 7 | Wonderwall / Oasis | Shared-finger Em7/G/Dsus4/A7sus4/Cadd9 → syncopation and sections | [Setup/rhythm](https://guitarlessons365.com/wonderwall-guitar-lesson-oasis/), [Greg Shute chart](https://www.gregshuteguitar.co.uk/_files/ugd/4079b4_0a1b39a89c1a4776a5c8f553f259cb08.pdf) |
| 8 | Creep / Radiohead | G/B/C/Cm barres → major-to-minor change and verse arpeggios | [Andy Guitar](https://www.andyguitar.co.uk/videos/radiohead-creep), [Carl Brown](https://guitarlessons365.com/creep-guitar-lesson-radiohead/) |

| Riff order | Song | Entry exercise → later work | Setup distinction |
|---:|---|---|---|
| 1 | Seven Nation Army / The White Stripes | Single-note groove/muting → power shapes and sections | [Andy Guitar](https://www.andyguitar.co.uk/videos/electric-guitar-song-1-seven-nation-army-by-the-white-stripes) distinguishes a standard-tuning adaptation from original Open A. [Justin Guitar](https://www.justinguitar.com/songs/the-white-stripes-seven-nation-army-chords-tabs-guitar-lesson-bs-824) supplies fuller power-shape practice. |
| 2 | Come As You Are / Nirvana | Repeated riff → rhythm and suspended-chord sections | [Carl Brown](https://guitarlessons365.com/come-as-you-are-guitar-lesson-nirvana/) distinguishes studio D standard (DGCFAD) from common live E-flat standard. |

The player shows sounding chord labels, with an optional capo view. It does not
teach riffs or convert retuned guitar shapes. Come As You Are needs a separate
D-standard arrangement; Seven Nation Army needs an explicit choice of original
setup versus standard adaptation. Wonderwall's capo 2 and House's no-capo setup are explicitly verified
in this review; other missing capo assertions stay unknown rather than verified zeroes.
Its richer shapes remain a teaching proposal despite raw model vocabulary limits.

## Recording choices and preparation

Eight uploads are new. The exact Creep and Wonderwall audio and saved detector
files were reused byte-for-byte. The older House tribute stays in the original
three-song pack; this batch uses a label-distributed Animals recording.

- Brown Eyed Girl: selected the distributed *Blowin' Your Mind!* upload. Another artist-channel upload explicitly identifies a re-recording and was rejected; channel identity alone does not identify the performance.
- Love Me Do and Twist And Shout: selected *Please Please Me* 2009 remasters. Love Me Do is the album take, not an interchangeable original UK single or 2023 remix. The [Beatles album description](https://ukstore.thebeatles.com/collections/cd/products/please-please-me-remastered-cd) supports the take distinction.
- Knockin' On Heaven's Door: selected Dylan's *Pat Garrett & Billy The Kid* version rather than Guns N' Roses or a live performance.
- The new Animals upload is public, non-live and about 270 seconds. Rock Corpus annotations belong to their own master; its last annotated barline is not a complete-duration identity check. No gold timings, global offset or duration scaling were transferred.

The first preparation succeeded for nine cases; Twist And Shout returned HTTP
403. Failure status and those nine cases were preserved, with the complete
manifest withheld. Recovery verified their files and the same review SHA before
copying to a fresh directory. One normal public retry succeeded. No credentials,
cookies, proxies or access-control workarounds were introduced. Failure history
and recovery hashes remain in the ignored local caches.

Playback uses the exact mono 22,050 Hz PCM16 audio analysed by the models. All
20 charts identify the corresponding recording/hash/duration. Model agreement
and successful completion do not establish correctness. This is a local founder
experiment; commercial catalogue clearance remains separate roadmap work.

## Reproduce or restart

Prepared media and playback packs are gitignored. A source checkout contains
instructions and metadata, not recordings. Saved playback needs the analysis
environment only; new neural inference needs the separate model environments.

Acquire into a fresh project-local directory:

```sh
.venv-analysis/bin/python experiments/analysis/repertoire_batch.py prepare \
  --output experiments/generated/repertoire-first-ten-new \
  --python .venv-youtube/bin/python \
  --node /opt/homebrew/bin/node --ffmpeg /opt/homebrew/bin/ffmpeg
```

For a failed attempt add `--reuse-prepared experiments/generated/FAILED_PACK` to
a fresh run. The review must remain identical, and every reusable input must
pass verification before acquisition starts. A partial ten-song manifest is
never silently published.

The successful run is `repertoire-first-ten-v2`. Its inference manifest contains
only the eight new audio inputs, without teacher/reference fields:

```sh
.venv-crema/bin/python experiments/analysis/candidates/crema_adapter.py \
  --batch-manifest experiments/generated/repertoire-first-ten-v2/audio-only-inference-manifest.json \
  --output-root experiments/generated/repertoire-first-ten-v2
.venv-analysis/bin/python experiments/analysis/candidates/chordino_adapter.py \
  --batch-manifest experiments/generated/repertoire-first-ten-v2/audio-only-inference-manifest.json \
  --output-root experiments/generated/repertoire-first-ten-v2
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py build \
  --manifest experiments/generated/repertoire-first-ten-v2/manifest.json \
  --output experiments/generated/automatic-first-ten-v1
.venv-analysis/bin/python experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-first-ten-v1 --port 8070
```

The build target already exists on the audited Mac; use only the final serve
command to restart it. Another build requires a fresh name. The
[expanded player](http://127.0.0.1:8070/) keeps the original
[three-song player](http://127.0.0.1:8068/) and its feedback intact. New feedback
uses the ten-song pack identity.

## Next steps and estimates

| Step | Status | Remaining estimate |
|---|---|---|
| Exact uploads and teaching-source review | Complete | Selected versions and two proposed tracks saved |
| Automatic acquisition / reuse | Complete | 10/10 prepared; recovery and input hashes recorded |
| Raw detector drafts | Complete | Eight new runs per model; four exact cached charts reused |
| Expanded Mac playback | Deployed and browser verified | Ten cases, playback/seek/Core and 45 served asset hashes checked |
| Recording-compatible shapes, rhythm and sections | Next | About half a focused day for the first ten; begin with representative contrasts |
| Independent real-reference validation / correction effort | Next | 1.5–2.5 focused days including version matching and the checks above |

The agent prepares references and comparisons. The founder plays normally and
optionally taps a problem; source research and chord/timing annotation are not
prerequisites. Do not fit acceptance thresholds on exposed synthetic validation
cases. Product lessons and strumming guidance follow recording/arrangement checks.

## Verification completed

The standard Python suite ran 220 checks: 204 passed and 16 were skipped for
the separate `mir_eval` environment. Those 16 passed in the existing pinned
evaluation environment, giving 220 distinct passing checks including all
23 batch/recovery checks. An independent audit verified all source/WAV pairs,
recovery pins, cached bytes and 20 bounded ordered chart timelines.

The Mac copy contains 141 verified files across metadata, failed preparation,
successful preparation and playback packs. All 45 public assets served on 8070
match local bytes; three sampled private paths return 404. The original 8067
and 8068 pages remain available. Browser checks verified ready chord cues for
all ten songs, advancing playback, pause, backward seek, and Core chords on
Love Me Do. No test issue reports were added to either normal player.

Local screenshot: `experiments/generated/player-proof-20261011/first-ten.jpg`.
This deployment is a session-local server; restart the serve command after
reboot. Successful playback does not establish chord accuracy or an accepted
recording-specific teaching arrangement.

## Rhythm interface follow-up · 12 October

The existing ten-song pack on 8070 now adds hold lengths/progress, a proportional
timeline, approximate beat/bar units and two original strumming practice drills
per song. The original audio, charts and pack identity are unchanged.
[Rhythm evidence](PLAYALONG_RHYTHM.md) reports 239 distinct Python checks,
47 JavaScript helper checks and 47 matching served assets (the initial ten-song
deployment above had 45). Counts and suggested patterns remain unverified
practice aids; Wonderwall has beat lengths only while meter changes are unmapped.
