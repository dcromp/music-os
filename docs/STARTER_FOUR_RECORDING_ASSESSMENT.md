# First-four recording assessment

16 October 2026 · [Ticket 3: Check the first four recordings' audible changes and rhythm contrasts](https://github.com/dcromp/music-os/issues/3).

**Ticket 3 remains open.** This bounded pass verifies the exact inputs, accounts for the existing replay queue, rechecks primary teaching sources and records eleven inconclusive musical claims. It is a desk assessment, **not a listening review**. No independently checked boundary, recorded guitar rhythm, formal section or playable excerpt is accepted. [The reviewed-pack ticket](https://github.com/dcromp/music-os/issues/7) remains blocked.

The available session tools supply file/signal inspection and primary-source access, but no capable audio-listening reviewer. Saved independent annotations have no validated mapping to these cached editions and time origins. Those are the specific remaining capability/reference gaps; another detector agreement score would not resolve them.

## What is now recorded

The [versioned assessment](../catalogue/starter-four-recording-assessment-v1.json) binds each recording's audio/native-chart hashes, current private-draft revision/hash, source reports and exact half-open replay spans. It includes all **48 selected disagreement windows and 16 fixed coverage samples**, plus the specific native contrast/label targets required by the ticket. Selection is by recording ID; the all-ten report has other songs interleaved.

For every queued window the record preserves its source index/reason, exact seconds and a hash of its PCM replay slice. The 64 slices verify against the saved original audio. Sample rounding defines replay extraction only; it does not refine musical timestamps. The queue has **199.057 seconds of unique audio across the four recordings**; with all named claim targets the union is **277.445 seconds**. These are coverage durations, not measured human review time or proof those spans were heard.

| Recording | Bounded unresolved checks and existing coordinates | Result |
|---|---|---|
| Wild Thing | Separate G/A figure and paired contacts within native A contrast searches; saved common-hold search at 104.644–111.177 s. Fixed samples and selected disagreements are retained as well. | **Inconclusive.** A held label or full-mix transient does not establish guitar contacts, rests or the contrast's musical extent. |
| Love Me Do | Deliberate damp versus skipped/ringing contact, swing, and D-led contrast; saved C searches at 21.579–28.143 and 42.879–49.474 s. | **Inconclusive.** Low mix energy is not a guitar mute reference; neither teacher counts nor native D holds verify sections on this edition. |
| Knockin' on Heaven's Door — Dylan | Am/C responses; provisional G edits at 29.474–30.279 and 50.186–51.022 s; extra native Am at 82.50775510204082–83.06503401360544 s. | **Inconclusive.** Separation/template preference supports investigation but does not independently verify a G performance or either cue boundary. |
| Twist and Shout | Two A searches at 82.879–96.594 and 136.905–145.851 s; second native ending candidates 145.85142857142858 and 146.7501133786848 s; actual contacts and solo/ending coverage. | **Inconclusive.** The 0.899 s discrepancy remains. Neither intersection verifies a build-up; downstroke eighths remain a teaching option. |

Rounded seconds above are reading aids; the JSON retains the original values. Every candidate span is `provisional`; its independent check is `not_performed`, and the corresponding claim assessment is `inconclusive`. Accepted span/boundary lists are empty. Each record explicitly **rejects promotion** to reviewed learner content for lack of independent evidence. That rejection does not mean the musical hypothesis was audibly disproven.

The current draft revisions are Wild **2**, Love **2**, Dylan **3** and Twist **3**. None of their review checkboxes was marked heard, and no draft, model output or learner chart was changed. The existing two Dylan label edits and two Twist A intersections remain provisional.

## What the source check supports

Primary teacher pages were rechecked on 16 October. They corroborate practice proposals, not timestamped observations of the hash-bound recordings:

- Wild: paired contacts and holds in [Andy Guitar's lesson](https://www.andyguitar.co.uk/videos/electric-guitar-day-7-wild-thing), with the separate G/A figure in [Lauren Bateman's lesson](https://www.laurenbateman.com/wild-thing-chord-chart/). [Carl Brown](https://guitarlessons365.com/wild-thing-guitar-lesson-the-troggs/) describes multiple progressions. The simplified main loop is not enough to claim a complete recording arrangement.
- Love: [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-01-love-me-do) and [Brad Litton](https://www.simpleguitar.com/blog/howtoplaylovemedo) support damping, qualitative swing and contrasting accompaniment. Their teaching counts are not a common recording clock.
- Dylan: [Song Notes](https://songnotes.net/lessons/88/) supports the response alternation and optional Am7. [Jon MacLennan](https://www.jonmaclennan.com/blog/knockin-on-heaven%27s-door-chords) provides subdivision and a separate fingerstyle option; the previously identified Am/ii7 theory mismatch remains excluded.
- Twist: [Andy Guitar](https://www.andyguitar.co.uk/videos/beatles-guitar-day-02-twist-and-shout) and [Jon MacLennan](https://www.jonmaclennan.com/blog/twist-and-shout-chords) support an A contrast, distinct solo/ending tasks and a repeated-downstroke practice approach. They do not adjudicate either cached ending time.

The official [Isophonics documentation](https://isophonics.net/content/reference-annotations.html) ties its annotations to specified source CD audio. [Rock Corpus](https://rockcorpus.midside.com/timing_data.html) likewise defines time zero from its source files, including initial silence. Neither provides a transform to these cached uploads. The [existing reference-matching result](FIRST_TEN_REFERENCE_MATCHING.md) therefore stands; titles, similar duration and model agreement cannot transfer timing ground truth.

## Remaining work and ownership

The technical input/source assessment is complete. **The musical review has no defensible completion ETA until one of these routes is available:**

1. A capable reviewer hears the exact cached recordings, covering both the fixed and disagreement samples plus the named targets. Record the observations, independently chosen boundaries, uncertainty, reviewed excerpt and actual actor time. Keep a model-exposed curation decision distinct from a blind accuracy benchmark.
2. Obtain permitted canonical reference audio and establish an audio-derived offset/drift mapping, checked on reserved windows, before transferring its independently authored annotations. No gold-selected offset or retuning is acceptable.

This does not assign a transcription task to the founder. No reviewer/vendor was contacted or hired, and no paid service was invoked. A future reviewer can use the existing local [developer workspace](http://127.0.0.1:8073/) and the exact coordinates in the record. Human review/correction time remains **unmeasured**. Only this pass's evidence-assembly execution time is measured as agent technical work; research was not timed and no arrangement edits or audition occurred.

Keep ticket 3 open and ticket 7 blocked until at least one usable reviewed excerpt has actual evidence. All-inconclusive records are a useful handoff, not completion of the audible review. The existing draft validator intentionally retains `gold:false`; adding acceptance flags to it is not an alternative to that evidence.

## Verification and deployment

On this Mac, input/audio/native-chart identity, all current draft schemas, the 64 replay PCM slices and the complete selected/fixed accounting pass. All **39 frozen workflow pins** still pass; **45 reviewer and 48 learner public routes** retain unchanged asset bytes. No model was rerun or retuned. The changes are evidence and documentation, so historical regression results are retained without claiming a new full-suite run.

The existing learner and reviewer still listen on localhost **8070/8073**. No server, pack, practice/feedback identity, media, model or private-draft content was deployed or changed. Inputs and private sessions remain ignored; a Git clone alone does not include them.

From `/Users/davidcrompton/Documents/music-os`, this read-only command rechecks the pinned local files and all queued slices, including source selection equality:

```sh
.venv-analysis/bin/python -B - <<'PY'
import hashlib, json, wave
from pathlib import Path
r = json.loads(Path('catalogue/starter-four-recording-assessment-v1.json').read_text())
for item in r['inputs']:
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
native = json.loads(Path('experiments/generated/catalogue-change-check-20261016/report.json').read_text())
by_id = {c['id']: c for c in native['cases']}
count = 0
for c in r['cases']:
    source = by_id[c['id']]
    assert c['accepted_spans'] == c['accepted_boundaries_seconds'] == []
    assert c['usable_for_reviewed_pack'] is False
    with wave.open(c['audio_path'], 'rb') as w:
        rate, width = w.getframerate(), w.getsampwidth() * w.getnchannels()
        pcm = w.readframes(w.getnframes())
    assert len(c['windows']) == 16
    expected = {('selected-disagreement', i) for i in range(12)} | {('fixed-coverage', i) for i in range(4)}
    assert {(w['selection'], w['source_index']) for w in c['windows']} == expected
    for window in c['windows']:
        rows = (source['fixed_coverage_samples'] if window['selection'] == 'fixed-coverage'
                else source['boundary_review']['selected_review_windows'])
        original = rows[window['source_index']]
        assert all(window[k] == original[k] for k in ('start_seconds', 'end_seconds'))
        a, b = (round(window[k] * rate) for k in ('start_seconds', 'end_seconds'))
        assert [a, b] == window['replay_frame_interval']
        assert hashlib.sha256(pcm[a*width:b*width]).hexdigest() == window['replay_pcm_sha256']
        assert window['status'] == 'provisional' and window['independent_check'] == 'not_performed'
        count += 1
assert count == 64 and r['downstream_gate']['can_publish_reviewed_pack'] is False
print('PASS: pinned inputs, 64 source-selected replay slices, no accepted musical evidence')
PY
.venv-analysis/bin/python -B experiments/analysis/workflow_check.py
```

These checks establish record integrity, not musical correctness. Existing full [timing/rhythm diagnostics](CATALOGUE_TIMING_RHYTHM_CHECK.md) and [native timing review](STARTER_FOUR_TIMING_REVIEW.md) retain their original status and limitations.
