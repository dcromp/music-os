# Original-exercise pilot: content route and budget

Specified 16 October 2026 for [the launch-content route ticket](https://github.com/dcromp/music-os/issues/9), building on [song-access feasibility](SONG_ACCESS_FEASIBILITY.md).

**Decision: proceed with local preparation; hold a paid launch.** The concrete first route is three short, project-authored practice exercises rendered from an event score without third-party recordings, samples, soundfonts, copied riffs or lyrics. This avoids making the pilot depend on extracting popular-song audio. It does not establish commercial clearance, a ready lesson catalogue or demand for unfamiliar exercises. The popular-song review programme continues separately.

## Representative recording and provenance

The existing `l3-pluck-036` diagnostic is the reproducible input example. Its analytic oscillator/envelope code produces C–Am–F–G with two-second holds, four repeated attacks per chord, and half a second of silence at each end. It is synthesized triads, not a recorded guitar or a verified guitar voicing. Exact identities, source hashes, checks and budget inputs are in the [evidence record](ORIGINAL_EXERCISE_ROUTE.json).

| Item | Exact identity |
|---|---|
| Input | `experiments/generated/synthetic-suite/cases/l3-pluck-036/audio.wav` |
| Format | 9 s; mono PCM16; 22,050 Hz; 198,450 frames; 396,944 bytes |
| WAV SHA-256 | `cecb906c3f8167f79823dcfeffac3b625e786641523261f7b506e2c1239bd6dd` |
| Intended event score | Same directory, `reference.json`; SHA-256 `2da03a8e433533d546eb8e0b5d7d886c4c3952df82bf1bb3fe45b58da08f218b` |
| Generator | `experiments/analysis/synthetic_suite.py`, source commit `389a66364081b0798cb2fb049524a8eadc8eaa29`; recipe in the evidence record |
| Existing diagnostics | Same directory, immutable `btc.json` and `crema.json`; separate identities/hashes in the record |
| Permission state | Project-local procedural input with no external media acquisition. Commercial operator/contributor authority and release terms remain unrecorded; this report does not grant them. |

Fresh in-memory regeneration matches the entire saved WAV byte-for-byte on Python 3.12.10 / NumPy 2.2.6. The authored score matches the generator events; all three chart schemas and the cached audio/prediction identity checks pass. No neural inference ran. BTC's historical warm per-file time is 0.0511 s; this excludes shared setup and is neither a cloud quote nor a human review cost.

Both cached detectors extend G through the final silence; CREMA also emits Cmaj7/Fmaj7 for plain generated C/F. Keep these native predictions as diagnostics. For generated exercises, the authored event score supplies the intended arrangement; detector agreement cannot approve it. An eventual live-guitar rendition would need a new recording ID, permission record and timing review. The [selected BTC/CREMA workflow](ALGORITHM_SELECTION.md) for recorded music stays fixed.

## Small catalogue and player contract

Propose **three exercises of up to two minutes each**, with no lyrics, famous-song names, covers or user uploads in this pilot. All three are **planned**, not generated or approved lessons:

| Exercise | Teaching purpose | Required review |
|---|---|---|
| One-chord pulse | Steady downstrokes, a count-in and rests | Comfortable grip, audible pulse, correct rest/count labels |
| Two-chord change | Change between two open shapes over whole-bar holds | Feasible transitions, honest hold lengths and authored strum cue |
| Four-chord loop | C–Am–F–G with a reviewed small F grip, or an explicitly reauthored easier progression | Every sounding voicing matches the taught shape; gradual tempo and change difficulty |

The nine-second diagnostic demonstrates provenance and processing, not the finished four-chord lesson. The displayed half-second attacks do not establish a down/up stroke direction. Author that practice instruction explicitly and test it. A starting 120 BPM / four-beat exercise convention is a proposal for the new scores, not a meter annotation added to old research audio.

```text
authored score + contributor/asset permission record
    → render once → audio hash + event-score hash
    → optional offline diagnostic prediction, kept separate
    → review sounding voicings, event timing, holds and strumming
    → versioned arrangement and audio in a new practice pack
    → browser audio clock → chord/hold/rhythm cues + ordinary practice progress
```

Before publication, each pack entry must bind the recording ID/hash, score revision/hash, arrangement revision, reviewer/evidence, permission record and status. Keep `diagnostic`, `draft` and `reviewed` explicit. Include only reviewed entries in the paid pack; revise or withdraw an entry when permission or musical evidence changes. Keep the old ten-song research cache and its learner progress/feedback identities separate. The current pack builder produces **unreviewed** drafts and has no guide for this synthetic ID; publishing reviewed exercises requires an explicit integration step. No existing learner pack was changed by this design.

Use one visible HTML audio player for the independently permitted file, with play/pause, seeking, volume and a cursor driven by `currentTime`. Show seconds where reviewed counts are absent. Loops and speed changes must follow actual media time and pass target-browser/device checks; no sample-accurate loop promise. Local playback exists in the Mac tools, but this exercise pack, its learning path, public hosting and checkout are not deployed. Offline delivery and background playback are outside this first pilot. Stems and part removal are also outside it; the later pocket-band engine can generate separately owned parts rather than assume a separation model grants permission.

## Uses to clear before distribution

Composition and sound recording are distinct rights categories; the [US Copyright Office explanation](https://www.copyright.gov/engage/musicians/) is a useful checklist, not a Norway/worldwide clearance. Record any publisher or collecting-society mandate: [TONO explains that membership affects self-management](https://www.tono.no/faq-items/kan-jeg-som-tono-medlem-egenforvalte-musikken-min-2/).

| Proposed use | Basis / unresolved item |
|---|---|
| Render, retain and analyse the source audio | Analytic generation is evidenced. Record who can authorize the generator, event score and output for the intended operation. No commercial grant is inferred from a file being in Git. |
| Cache/backup and deliver the recording in a paid browser product | Obtain/record authority for the composition and rendered recording, commercial playback/copies, launch territories, duration and any contributor/collecting-society restrictions. |
| Display timed chords, grips, counts and authored strumming; simplify/transpose | Keep project-authored teaching materials and their contributor permission together with the score. Check the taught arrangement and permitted adaptations; do not scrape a teacher's chart or artwork. |
| Ship code or model weights | This proposed player ships audio/data, not inference weights. Preserve applicable frontend notices; settle the project's release/contributor terms. If production analysis or model distribution is added, review its specific code/weight terms separately: [BTC](BTC_SETUP.md), [CREMA](CREMA_SETUP.md). |
| Offline copies, separated stems or muting parts | Not proposed for this pilot. Add their exact uses to the permission record before implementing them. |

No root project licence or contributor release record establishing these commercial grants was found in the audit. The vendored Matt Pocock MIT licence applies to those skills; it is not an audio or whole-product licence. Do not add a blanket licence on behalf of an unknown rightsholder. The required next step is an operator/contributor provenance and release review for these specific original assets; no vendor contact is needed for this design ticket.

For a later popular-song pilot, obtain terms covering the exact master/version, underlying composition, territories, permitted analysis/retention, teaching/arrangement display, commercial playback and removal/expiry. Obtain separate terms for stems or downloads if proposed. An official YouTube embed is a distinct playback option: retain its visible controls, attribution, ads and normal functionality; keep our practice value independent of embedded viewing. [YouTube's policies](https://developers.google.com/youtube/terms/developer-policies) restrict extraction/caching and component separation, and prohibit charging for embedded viewing. [IFrame controls](https://developers.google.com/youtube/iframe_api_reference) do not supply raw analysis audio or guaranteed precise loops. No permission or price is inferred from Chordify's existence, and API request quotas are not music royalties.

## One-time preparation budget

Keep costs per recording/arrangement separate from service costs per month. The [machine-readable inputs](ORIGINAL_EXERCISE_ROUTE.json) distinguish facts from assumptions.

| Item | Current evidence / budget treatment |
|---|---|
| Authoring and review | Illustrative only: 3 × (45 min authoring + 30 min musical review) × $30/hour = **$112.50**. Actual correction minutes and any teacher rate remain unmeasured. Revision rounds add to this. |
| Render/analysis compute | The example reproduces locally; cached BTC timing is historical. Record fresh setup, render/inference wall time and the actual execution supplier before assigning a production cost. No per-play inference is proposed. |
| Permissions / contributor agreements | Unquoted. A fully controlled original may avoid an outside catalogue fee; do not put an unverified zero into the launch budget. |
| Product integration, content QA and targeted terms review | Not covered by $112.50. Scope browser pack integration, payment/account/privacy work and any specialist review before committing a total. |

## Recurring budget and sensitivity

Illustrative **USD** planning case, not selected pricing or supplier terms: 100 payers at $4/month; each plays 120 complete two-minute exercises per month. Mono PCM16/22,050 Hz is deliberately used without assuming compression savings. Each file is 5,292,044 bytes; three files are 15,876,132 bytes. That workload delivers about **63.50 GB/month** and, assuming five GET/range requests per play, **60,000 reads/month**. Real seeking/retries/cache behaviour must be measured.

As one verifiable storage component, [R2 Standard's public tariff](https://developers.cloudflare.com/r2/pricing/) checked 16 October lists $0.015/GB-month, $4.50/million Class A and $0.36/million Class B operations, with direct egress free. Its monthly included amounts are 10 GB-month, one million A and ten million B operations. This audio-only scenario, assuming 100 writes/month and available account allowances, fits the included amounts. That is a conditional **$0 audio-object component**, not a total hosting bill; other account traffic and metered services can change it. No provider account or public bucket was created.

| Monthly component | Illustrative amount / unresolved dependency |
|---|---|
| Gross receipts | $400 before taxes, refunds and fees |
| Content payments | **Unknown** pending the original-asset release record; popular-song quotes entirely unknown |
| Audio object storage/reads/direct egress | Conditional $0 above; verify account allowances and actual requests |
| Other web hosting, auth, monitoring, domain/backups | $20 **placeholder allowance**, not a quote or selected service |
| Payment processing | $46 using **assumed** 4% + $0.30 per monthly payer; replace with chosen provider/country/currency/tax treatment and include refunds/FX/chargebacks |
| Support labour | $50 using **assumed** 1 minute/payer/month at $30/hour; measure rather than treat founder time as free |
| Tax/VAT, mobile/platform fees | Unresolved; not deducted here. This is a browser proposal, with no app-store launch assumed. |

The arithmetic leaves **$284/month before unknown content payments, tax, catalogue amortisation and omitted integration costs**. It is not profit. At these assumptions each additional support minute per payer consumes $50/month: another 5.68 minutes would exhaust that remainder even before unknown costs. Recheck demand and support effort before promising an unlimited cheap catalogue.

Use `receipts − tax/refunds − payment/platform fees − content payments − hosting − support` for recurring contribution, then separately deduct chosen amortisation of authoring/review/integration. Price, tax jurisdiction and payment supplier remain decisions; no external service was purchased.

## Ship / hold and next actions

| Gate | Decision / next evidence |
|---|---|
| Local provenance and processing preparation | **Proceed.** Exact synthetic input, deterministic render and cached diagnostic identity are verified. |
| Paid original-exercise pilot | **Hold.** Record the specific commercial grants/authority; author and musically review the three actual drills; integrate and test a separate pack and its controls; measure ordinary guitar followability; select launch territory/payment/hosting terms and fill the unknown budget rows. |
| Paid popular-song catalogue | **Hold.** Exact-version content/teaching/analysis permissions and quotes, recording acceptance and production player checks remain open. The YouTube research cache is not a launch catalogue. |

This completes the route **specification**, not a product launch or a musical acceptance gate. Work on the existing recording reviews remains unblocked by supplier permissions for this proposed future pilot; no founder transcription or vendor contact was added.

## Recheck without changing caches

From the canonical checkout, this verifies all recorded local source/assets and regenerates only the representative audio in memory. It writes no cache or media:

```sh
.venv-analysis/bin/python -B - <<'PY'
import hashlib, io, json, sys, wave
from pathlib import Path
sys.path.insert(0, 'experiments/analysis')
import lab, numpy as np, synthetic_suite as suite
from automatic_drafts import paired_recording, verified_audio
report = json.loads(Path('docs/ORIGINAL_EXERCISE_ROUTE.json').read_text())
for asset in report['sources'] + report['assets']:
    path = Path(asset['path'])
    assert path.stat().st_size == asset['bytes'], path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256'], path
base = Path(report['assets'][0]['path']).parent
reference = lab.load_chart(base / 'reference.json')
btc, crema = (lab.load_chart(base / f'{name}.json') for name in ('btc', 'crema'))
verified_audio(base / 'audio.wav', paired_recording(btc, crema))
events = suite.events_for(report['recipe'])
assert events == reference['chords'] == report['authored_score']
pcm = (suite.render(report['recipe'], events) * 32767).astype('<i2').tobytes()
buffer = io.BytesIO()
with wave.open(buffer, 'wb') as output:
    output.setnchannels(1); output.setsampwidth(2)
    output.setframerate(suite.SAMPLE_RATE); output.writeframes(pcm)
assert buffer.getvalue() == (base / 'audio.wav').read_bytes()
print('PASS: source/asset hashes, chart identities and byte-exact procedural audio')
PY
```

The generated inputs and native caches remain ignored local research files; a Git clone alone does not contain them. [Synthetic setup](SYNTHETIC_RESULTS.md) describes regeneration. Compatibility checks are not new live-player or guitar-session evidence. Existing Mac services remain on 8070/8073; no public or exercise-specific deployment was made.
