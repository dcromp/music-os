# Short local listening review

The review now gives a concrete optional task: **start with Creep's first 20 seconds, replay it, and mark one or a few audible chord changes without seeing model charts.** Use `?` for an unknown chord. This first familiarisation task takes about **5–10 minutes**, with no required guitar session. Preparing independently checked chord/timing references for all three clips is separate work and may take **20–40 minutes or longer**; the small task is not a claim that gold annotations can be completed in five minutes.

## Current pack

Three first-20-second windows are frozen at source frames **0–441,000**, from the exact prepared mono 22,050 Hz PCM16 WAV files. Bounds are arbitrary listening windows, not verified intro endings or section boundaries. All three are development cases; none is a held-out recording.

| Window | Recording ID | Excerpt SHA256 |
| --- | --- | --- |
| Creep | `creep-listening-00-20` | `eed98c153e766509d226196d8a57abb35ba04668e6a4e456f0aaaef36b47572e` |
| Wonderwall | `wonderwall-listening-00-20` | `2469ecd73dc56013c4d99c5682e7586c29ddf4593c2aea634e770211c11e02d6` |
| House of the Rising Sun | `house-listening-00-20` | `943f3488d5c201c424e73f9145f0b64f5f6976abf11c4328a247a1e54ef82aa6` |

The final pack is `experiments/generated/listening-review-alignment/`. Each clip has five anonymous candidates: the three saved audio-only detectors plus spectral and NNLS evidence with bounded section hypotheses. Candidate identities and source parameters stay in `private-candidate-key.json`, which the server does not expose. Ordering is shuffled deterministically per case; this concealment is for review convenience, not a formal blinded study. Candidate chords may suggest which model produced them.

All predictions and alignment drafts remain unaccepted. A bounded Creep pass or a fixed maximum Wonderwall loop count prevents unbounded cycling, but does not prove the hypothesis or its timings correct. House's source upload is from an unofficial tribute channel; the pack preserves the exact imported version. Acquisition/source-use limitations remain in [YouTube import evidence](YOUTUBE_IMPORT_SMOKE.md).

## Run on the Mac

From the Music OS checkout, with the prepared imports and saved predictions present:

```sh
.venv-analysis/bin/python experiments/analysis/review_pack.py build \
  --spec experiments/fixtures/review-packs/first-intros-alignment.json \
  --output experiments/generated/listening-review-alignment

.venv-analysis/bin/python experiments/analysis/review_pack.py serve \
  --pack experiments/generated/listening-review-alignment --port 8068
```

Open `http://127.0.0.1:8068/`. The existing synthetic bench stays on port 8067. Build only once per output directory; the builder refuses to overwrite an existing review. For a changed specification, choose a new output directory and serve that pack. The source-only initial pack remains at `experiments/generated/listening-review/`, with its specification in `experiments/fixtures/review-packs/first-intros.json`.

1. Start with **Creep · first 20 seconds**. Play, pause, restart, or use **Go to seconds** and **Back 2 seconds** to inspect a change.
2. Press **Mark change now**, then edit its time, chord name or `?`, timing uncertainty, and confidence. Add a mark at zero if the starting chord is identifiable. Marks extend to the next mark, with the final mark ending at the clip end. An unlabelled initial gap stays explicit.
3. Download the annotation JSON. **Show JSON to copy** provides a fallback if browser downloads are unavailable. Drafts live only in tab memory; save before closing or reloading.
4. Optionally reveal anonymous candidates after saving your audio-only draft. Compare by replaying boundaries. Candidate events are never copied into manual annotations. Any later export records `candidate_exposure: "model-exposed"`.

Each export includes the review pack ID, excerpt recording ID and audio hash, original recording ID/hash, exact sample endpoints, source offset, uncertainty, notes, and elapsed wall time since first selecting the case in that tab. This timer includes pauses and time on other cases; it is not a measured active correction-cost metric. Times in annotation intervals are **excerpt-relative**; original time is excerpt time plus `origin.source_offset_seconds`.

Exposure flags persist in browser-local storage, keyed by pack ID, case ID and excerpt hash, so reloading does not turn a previously exposed review into an audio-only draft. If storage cannot be read or written, exports conservatively assume model exposure and identify the unavailable history. Only the exposure flag persists; manual marks and notes still require a download. These flags do not prove that a reviewer has never seen predictions outside this browser or after clearing browser storage.

Exports use `listening-annotations-1.0`, `status: "human-draft-needs-independent-verification"`, and `gold: false`. They are not automatically evaluation references. A separate verification step must check chord identities, physical change times, gaps, version pairing and uncertainty. Model-exposed corrections are useful curation evidence but must not be presented as independent timing gold.

## Add predictions or private untimed inputs

The builder accepts source-relative detector files as strings in each case's `candidates` list. New excerpt-local alignments need an explicit coordinate system:

```json
{
  "path": "experiments/generated/real-alignment-v2/creep-listening-00-20-nnls-sections.json",
  "time_origin": "excerpt"
}
```

Source predictions must match the original ID, WAV hash, duration and sample rate, and are cropped/rebased once. Excerpt predictions must match the excerpt ID, hash, duration and sample rate, and keep their local timestamps. Mismatches fail instead of silently pairing different audio or shifting times twice. The final specification is [first-intros-alignment.json](../experiments/fixtures/review-packs/first-intros-alignment.json).

An optional `untimed_chart` path validates and copies a finite untimed candidate into each case's private `untimed-chart.json`. It remains separate from `origin.json`, timed predictions, and manual annotations. No timestamped labels are fed into these chart inputs. The browser never requests private chart inputs, origin files, build specifications or model identity keys.

The standalone server binds only `127.0.0.1` and serves fixed static assets, one public manifest, cropped WAV files and anonymous JSON candidates. Public paths reject symlinks and hard-link aliases to private review files at startup and on every request. WAV byte ranges support seeking. It has no upload/annotation POST endpoint, directory listing, arbitrary file route or external request code; a Content Security Policy restricts page resources to the same local origin.

## Validation

Eight offline Python checks pass for exact PCM sample/origin preservation, source/excerpt prediction pairing, blinding, finite untimed separation, transactional failure/no-overwrite behaviour, and the server allowlist including private symlink/hard-link aliases. Eight JavaScript helper checks cover manual interval export and exposure provenance across sessions, conservative unavailable-storage handling, invalid/duplicate timestamps, candidate identity validation, and half-open intervals/gaps. These checks do not establish annotation quality or song accuracy.

```sh
.venv-analysis/bin/python -W error -m unittest discover \
  -s experiments/analysis/tests -p test_review_pack.py -v
node experiments/review/test.js
```

A live browser smoke verified all three audio windows load, exact 5.250-second seeking, blank manual drafts, audio-only/model-exposed export transitions, and the final five-candidate reveal. A separate smoke pack/origin verified model exposure remains recorded after reloading without marking the user's pack as exposed. Temporary UI test marks were discarded by reloading; no listening annotations or gold were manufactured by that test.
