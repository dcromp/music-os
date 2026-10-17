# Online chord checks

The catalogue preparation command searches for primary teaching pages, fetches
derived chord facts and compares them with the exact cached native chart.
Results appear in **Online chord checks** in the existing Mac player, with
source links and replay buttons. No source lookup or model inference runs while
playing. The founder does not need to find charts or enter timestamps.

## Run

From `/Users/davidcrompton/Documents/music-os`, using the existing Python 3.12
analysis environment and cached first-ten pack:

```sh
.venv-analysis/bin/python -B experiments/analysis/online_chords.py \
  --output experiments/generated/online-chord-checks-20261017

.venv-analysis/bin/python -u -B experiments/analysis/automatic_drafts.py serve \
  --pack experiments/generated/automatic-first-ten-v1 --port 8070 \
  --online-checks experiments/generated/online-chord-checks-20261017/report.json
```

Use an unused output directory for each run; previous reports are never
overwritten. Stop a server with Ctrl+C before starting its replacement on the
same port. Reload the player once after upgrading its script. The optional
report is served only at `/online-chords.json`; omitting the option retains
ordinary playback. Restart this command after reboot. No public hosting or
background service is installed.

The default cache is `experiments/generated/online-source-cache-v1/`. Fresh
successful facts are reused for seven days; retrieval failures have a shorter
retry window. `--refresh` requests new facts. For a reproducible network-free
rerun with fresh cached facts:

```sh
.venv-analysis/bin/python -B experiments/analysis/online_chords.py --offline \
  --output experiments/generated/online-chord-checks-offline-replay
```

Missing or expired cache entries become explicit unavailable sources, rather
than a clean result. The two flags cannot be combined. The module uses the
standard library for search, HTTP, HTML parsing and caching; chord normalization
uses the existing analysis code. No search API key or paid inference is needed
for this local experiment.

## What is checked

- DuckDuckGo Lite supplies discovered URLs. Previously researched primary
  teaching URLs are also tried, so a search-provider failure does not discard
  useful sources. The provider's public HTML is a best-effort dependency, not a
  contracted API; blocked, failed and unrecognised responses are distinct from
  a successful empty search.
- Fetches are bounded by an allowlist of teacher domains, response sizes and
  timeouts. Redirects stay within that boundary, robot exclusions are respected,
  and challenges or inaccessible pages remain recorded failures. There is no
  login, challenge bypass, video download or PDF/chart bulk importer here.
- Extraction looks for explicit chord vocabulary and a short explicitly named
  intro in lesson content. Navigation, comments and arbitrary capital letters
  are not chord evidence. Unsupported layouts and conflicting setup text
  abstain. Search snippets are not used as chord answers.
- Enharmonic roots, capo and uniform retuning become sounding pitches, including
  slash bass. Rich source labels remain saved; comparison reduces declared
  extensions conservatively and retains suspensions. Source setup wins over
  seed metadata. Missing fields on a known seed may use an explicitly labelled
  catalogue teaching hypothesis; a newly discovered source with unknown setup
  abstains. This is not proof that a teaching setup matches the recording.
- At least two distinct source groups are required for warnings. A publisher
  or byte-identical page counts once. The union retains optional variants;
  agreement is not a confidence score or proof of independent transcription.
- Native chords outside the extracted palettes, or with an uncovered quality,
  receive review hints. An incomplete teaching palette cannot prove that a
  chord is wrong: it may describe another section, voicing or arrangement.
- Two matching explicit intro orders can flag a diverging native opening after
  at least three matching changes. The replay region uses existing native cue
  boundaries. No forced full-song alignment or missing-chord timestamp is
  invented. Competing corroborated intro orders abstain.

The two riff songs remain outside chord-palette assessment. A palette alone
cannot catch Wild Thing's A/E substitution near 25 seconds because both labels
belong to the source vocabulary. Untimed online chords cannot validate its
opening D timestamp. These remain explicit negative controls.

## Identity, storage and limits

Every case carries the exact recording ID, audio hash, duration/sample rate,
primary-chart SHA-256 and analysis ID, plus the pack ID. The server checks the
report when starting and before serving its actual response bytes; the browser
checks it against the loaded chart again. Stale or invalid optional metadata
cannot replace chords or disable playback. Source statuses and coverage are
visible even when no comparison is possible.

Raw charts/audio, existing detector evidence, frozen selection policy,
practice guides and browser feedback/progress keys remain unchanged. This
feature does not accept #3's musical review or unblock #7's reviewed pack.
Source and model agreement supply review suggestions, not independent timing
references or accurate strumming. The House example can expose an E/Em quality
conflict and intro-order discrepancy; it does not establish the physical extent
of the missing E inside a long Am event.

Caches and reports contain URLs, timestamps, retrieval/content hashes and
derived musical facts; fetched page HTML, lyrics and full third-party charts
are not retained or published. Generated files stay ignored. Public availability
and source-use rights remain separate from this local technical check.

## Verification

Run focused source/check tests, followed by the ordinary analysis suite and
player checks. [Completion evidence](ONLINE_CHORD_CHECK_RESULTS.json) records
the actual ten-song network run, cached replay, unchanged native hashes,
workflow pins and browser verification. It distinguishes diagnostic flags from
confirmed errors and records unavailable source coverage.
