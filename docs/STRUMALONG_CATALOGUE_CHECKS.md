# Strum Along catalogue checks

Date: 25 October 2026. Tool: `experiments/analysis/strumalong/catalogue_checks.js`. Report: `docs/STRUMALONG_CATALOGUE_CHECKS.json`. Tests: `experiments/analysis/strumalong/catalogue_checks.test.js`. No lyrics appear in any input or output.

Founder feedback on 25 October 2026: "The idea of a curated list is that we can automate basic checks like chords and instruments." Riptide "is more a ukulele song", and Zombie "has some chord mis timings ... a chord is 1 beat before going into the 3 beats of a different chord, but every other time that sequence is played the timing is correct". This tool is that automation. It gives every candidate recording in the packs listed in `strumalong/data/catalogue.json` a verdict of **pass**, **flag** or **fail**, each with reasons. Excluded recordings are checked too. They are the founder's labelled negatives, so they show what the checks can and cannot catch.

A verdict means "no automated check objected", not "verified". The charts are automatic CREMA drafts, the beat grids are estimated, and nothing here listens to the audio. Every verdict lists what was *not* checked (`not_checked`).

## Run

```
node experiments/analysis/strumalong/catalogue_checks.js            # text table, writes docs/STRUMALONG_CATALOGUE_CHECKS.json
node experiments/analysis/strumalong/catalogue_checks.js --json     # full report on stdout
node experiments/analysis/strumalong/catalogue_checks.js --markdown # summary table in markdown (the snapshot below)
node experiments/analysis/strumalong/catalogue_checks.test.js       # tests (plain node, node:assert)
```

Other flags: `--no-write`, `--out <path>`, `--check` (exit 1 when the report on disk is stale; the report has no timestamp, so a rerun on unchanged inputs is byte-identical) and `--strict` (also exit 1 when a shipped song is flagged).

**Exit code.** Non-zero when a *shipped* song fails a hard gate. "Shipped" means the recording is in the catalogue and not excluded. Excluded songs may fail without stopping the run. A flag alone never stops it unless `--strict` is given.

The tool is read-only on every input: the frozen packs, `experiments/review/*.json`, the exported `strumalong/songs/*.json`, and the fixtures. It writes only the report. It does not read audio.

## Verdicts

- The song verdict is the worst status among the checks that ran: fail > flag > pass.
- `unknown` (embed), `not run` (instrument) and `no reference` (chords) never lower a verdict. They are listed in `not_checked`, and in the tables as `?`, `-` and `no ref`.
- `few` in the Timing column means too few repeated changes to judge. `fixed` means the raw chart had mistimed repeated changes and the exporter's auto-timing removed them.
- Songs with an exported `songs/<id>.json` are judged on **what ships** (display corrections and the exporter's timing fixes included). Others are judged on the pack's raw CREMA chart on the pack's beat grid. The report says which (`view_source`).

## Inputs

| Check | Reads |
|---|---|
| Chords | `experiments/analysis/strumalong/expected-chords.json` (v1) and `expected-chords-v2.json` (v2). For the first ten: `catalogue/first-ten-review.json` (teaching chord set at the teaching capo, converted to sounding chords) plus, when present, `experiments/generated/accompaniment-review-20261018/online-reviewed-v2.json` (sounding palettes of the usable teaching sources, as *accepted extras*). Seven Nation Army and Come as You Are have no reference. |
| Tempo | `experiments/fixtures/rhythm-first-ten.json`, `rhythm-strumalong-additions-v1.json`, `-v2.json` (prior ranges), and the pack's `rhythm.json` (pulse, beat times). |
| Plausibility | The chart and beat grid, plus the expected chords for the "progression has several families" test. |
| Timing | The exported song (`chords`, `beats`, `rhythm`, per-chord `b`, `a`, `c`, `t`, and `chart.corrections` of kind `timing`), or the pack chart and grid. |
| Embed | `experiments/fixtures/strumalong-additions-candidates-v1.json` and `-v2.json` (per-entry `embed` and the fixture-level `checked` text), the exported `songs/index.json` card (`playable_embed`), and one fact recorded in git history. |
| Instrument | `experiments/generated/strumalong-instrument-tags.json`, if it exists. |

`generated_from` in the report records the SHA-256 of the catalogue, every pack manifest and rhythm file, every fixture and reference file, the song index, and per song the chart and exported-song hashes.

## The checks

Chord families: a label is reduced to a root and a quality (major, minor, sus, power `5`, dim, aug). Sevenths, add9 and slash basses fold into the triad, so Em7 is Em, Cmaj7 is C and D/F# is D. Enharmonics agree (Bb is A#). A sus or power chord satisfies either the major or the minor chord on its root. Relative major and minor do not match. A **main** family covers at least 4% of chord time. N and X are not chord time.

### 1. Chords

- **cover**: share of chord time in the expected families (plus accepted extras).
- **missing**: an expected family with under 1% of chord time. **weak**: under 4%.
- **unexpected main**: a chart family of at least 4% that matches no expected family.
- **fail** when cover is under 50%. **flag** when cover is under 80%, when one of the first three listed expected families is missing, or when an unexpected main family is at least 8%.
- Missing chords beyond the first three are reported but do not flag. The expected lists put the main progression first and the brief chords last, and several carry notes such as "Em and Am are brief".

Can tell: wrong key, wrong model output, a progression that lost a core chord. Cannot tell: whether the expected list is right (several are marked medium or low confidence in their source files; Island in the Sun is "low"), whether chords sit in the right place, or whether the part is strummed.

### 2. Tempo

- Pulse inside the prior range `tempo_min_bpm`..`tempo_max_bpm`. Outside is a **flag**, more than 10% outside a **fail**. A pulse within 1.5% of a range edge **flags** as a range possibly clipping the real tempo.
- Pulse within 8% of half or double `start_bpm`: half/double-time suspicion (flag).
- Median chord hold of 12 beats or more, or 1 beat or less: the grid may be double or half time (flag).
- The beat grid's own median spacing differs from `pulse_bpm` by more than 4%, or the spacing varies by more than 8%: the grid wanders (flag).
- Recordings with no range in the fixture (Wild Thing, Love Me Do: "default tracker prior") are compared only on the start tempo and listed as `tempo range (default prior)` in `not_checked`.

Can tell: a tracker failure, a grid that disagrees with itself, an implausible chord rate. Cannot tell: a half or double grid that sits inside the range and agrees with the chart. The ranges were set from published tempo markings *before* the tracker ran and were passed to it, so "inside the range" mostly confirms the config. No song is flagged on tempo among the shipped ones.

### 3. Chart plausibility

A **hold** is a run of one chord family, with N and X breaking it. A stray blip (under 0.75 beat) between two runs of the same family is absorbed, so one wrong frame does not split a long hold.

- **long_hold_share**: share of chord time in single holds of 24 beats or more. Also `long_hold_count`, `max_hold_beats`, top family, N/X share.
- **fail** needs all of: at least two expected families, at least 25% of chord time in long holds, at least 3 separate long holds (one break or solo is legitimate), and a hold of 32 beats or more (eight bars of 4/4). This is the A Horse with No Name signature: Em for up to 52 beats where the song alternates every bar.
- **flag** when the progression has two or more families (expected, or the chart's own main families when no reference exists) and 10% or more of chord time is in long holds, or any hold lasts 32 beats or more, or N+X is at least 20% of the recording (fail at 50%).

Can tell: charts that merge alternating chords into long holds, and charts that are mostly N or X. Cannot tell a chart that merged chords into *short* wrong holds, or a long hold that is real. Wild Thing holds A for 38 beats from 24 s and 33 beats from 92 s, which may well be real breaks. The tool flags it and nobody has listened to it.

### 4. Timing consistency

The founder's test: "every other time that sequence is played the timing is correct". Defined on family labels with blips removed:

- A **change** is the boundary between two consecutive real chords with no N or X between them.
- Its **position** is the fractional beat index of the new chord's start, modulo beats per bar. Absolute phase never matters.
- A **group** is all changes with the same from>to pair. It is **eligible** with at least 4 changes where 60% lie within half a beat of one position (the group's *usual position*).
- A **deviant** is a change in an eligible group 0.75 to 1.5 beats from its usual position. Under 0.5 beat is the grid's noise. A half bar or more off (1.5 beats in 4/4) is a different placement of the same change, not a mistiming. Those are counted as `half_bar_placements` and never flagged. On a 2-beat bar a one-beat offset is already a half bar, so nothing can be reported (Bad Moon Rising).
- Three or more consecutive deviants in the same direction are a **shift**: a whole stretch that sits a beat off (the grid or the chart slipped). The report says whether the exporter's per-chord bar anchors (`b`) follow it.
- **consistency** = 1 − isolated deviants / eligible changes.

Verdicts: **flag** with 2 or more isolated deviants, or with shifts that the exporter's anchors do not follow covering 10% or more of repeated changes. **Fail** under 80% consistency (not on an assumed meter). Each deviant is listed with its time, the change, its offset in beats, and the hold lengths either side, so the Zombie signature (5 beats, then 3) is visible: `from_hold_beats` 5.36 and `to_hold_beats` 2.71 at 133.9 s.

**Exporter auto-timing.** On 25 October the exporter began moving mistimed repeated changes itself. The tool reads what it writes: `t:1` on the moved chord and a `chart.corrections` entry with `kind: "timing"` (id `auto-timing`) whose `moves` hold `at`, `was`, `from`, `to`, `shift` and `agree`. Other per-chord keys it has not seen are listed under `exporter.other_chord_keys`. A fix that agrees with its group by construction proves nothing, so for such songs the tool also analyses the raw pack chart and reports both: `auto_timing.raw_chart` (deviants before) and `shipped_deviants` (after). It measures each move: how far the change was from its group's usual position, how far the exporter moved it (a whole beat or a small snap), and where it ends up. It flags a song when 2 or more moves leave a change 0.25 beat or more further away than before, or when 10% of changes needed the fix.

Can tell: isolated one-beat slips and steady phase slips in sequences that repeat. Cannot tell: a mistiming in a part played once, a mistiming under about 0.75 beat (indistinguishable from the grid's noise), or whether the *grid* or the *chart* slipped. Downbeats are not verified, so "usual position" is the song's own habit, not a true bar position.

### 5. Embed

- `fail` for a recording with a recorded age restriction. Today that is Come as You Are only, from the 24 October build (git `60330ce` `AGE_RESTRICTED`; the gh-pages app skipped the upload).
- `flag` when the exported index card says `playable_embed: false`, or a candidate entry records an embed value other than OK.
- `pass` when a candidate entry says `embed: "OK"`, or the fixture-level `checked` text records "playability OK" (v1 on 24 October, v2 on 25 October, both with a github.io Referer).
- `unknown` otherwise: the first ten, except Come as You Are. The exporter's `playable_embed: true` is a default, not evidence, so it is not used.

Can tell: only what was recorded. Nothing here calls YouTube, so a video removed or restricted later is not seen.

### 6. Instrument (slot, not run yet)

The tool reads `experiments/generated/strumalong-instrument-tags.json` if it exists. Without the file every song shows `not run` and the verdict does not change. The file is written by a tagger the lead will add after the founder approves a model download. Schema `strumalong-instrument-tags-1`:

```json
{ "schema": "strumalong-instrument-tags-1",
  "model": { "name": "...", "version": "...", "sha256": "..." },
  "recordings": {
    "<recording_id>": {
      "audio_sha256": "<sha256 of the pack's prepared audio, optional but checked when present>",
      "model": "<optional per-recording override>",
      "scores": { "guitar": 0.0, "acoustic_guitar": 0.0, "electric_guitar": 0.0, "strum": 0.0, "ukulele": 0.0, "piano": 0.0, "harmonica": 0.0, "banjo": 0.0, "mandolin": 0.0 } } } }
```

Scores are probabilities in [0, 1] aggregated over the whole recording (state the aggregation in `model`). A bare map from recording id to `{model, scores}` is accepted too. Gates:

- **fail**: a non-guitar tag (ukulele, piano, harmonica, banjo, mandolin, accordion, organ, keyboard, synthesizer, violin, harp) of at least 0.30 that is 0.15 or more above the best guitar tag (guitar, acoustic_guitar, electric_guitar, steel_guitar).
- **flag**: such a tag at or above the best guitar tag; or a best guitar tag under 0.25; or a `strum` tag under 0.20 when the model has one; or invalid scores; or an `audio_sha256` that does not match the pack's audio (stale tags).

Can tell (once run): that a recording is not guitar-led. Cannot tell: that the guitar is picked or plays a riff rather than strums. Whether a tagger's strum score separates picking from strumming is untested.

## Thresholds

All thresholds live in `T` in the script and are printed into the report under `thresholds`; that copy is authoritative.

| Check | Threshold |
|---|---|
| Main family | at least 4% of chord time |
| Chords | cover fail under 50%, flag under 80%; missing under 1%; first 3 expected are core; unexpected main flags at 8% |
| Tempo | edge pin 1.5%; fail more than 10% outside range; half/double window 8%; median hold at least 12 or at most 1 beat; grid spacing gap 4%; spacing variation 8% |
| Plausibility | long hold 24 beats; flag at 10% of chord time or a 32-beat hold; fail at 25% and 3 long holds and a 32-beat hold with 2+ expected families; N+X flag 20%, fail 50% |
| Timing | group of 4+ changes, 60% within 0.5 beat; deviant 0.75 to 1.5 beats; shift of 3+; flag at 2 isolated deviants or 10% unfollowed shift; fail under 80%; auto-timing worse by 0.25 beat twice, or 10% of changes moved |
| Instrument | see above |

## Report schema

`strumalong-catalogue-checks-1`: `generated_from`, `thresholds`, `summary`, `unmatched_exclusions` (an excluded id that names no recording in any available pack), and `songs`. Each song has `recording_id`, `title`, `artist`, `pack`, `shipped`, `excluded_reason` (excluded only), `exported`, `view_source`, `chart_sha256`, `exported_sha256`, `checks` (`chords`, `tempo`, `plausibility`, `consistency`, `embed`, `instrument`, each with a `status`, `reasons` and its measurements), `verdict`, `reasons`, `notes` and `not_checked`.

## Snapshot, 25 October 2026

Generated from the checkout at the time, with the exporter's auto-timing present. Refresh with `--markdown`. The `songs_index_sha256` in the report says which export it saw.

| Song | Ships | Chords | Tempo | Plausibility | Timing | Embed | Instrument | Verdict | Flagged by |
|---|---|---|---|---|---|---|---|---|---|
| Wild Thing (The Troggs) | yes | pass | pass | **FLAG** | pass | ? | - | **FLAG** | plausibility |
| Knockin' on Heaven's Door (Bob Dylan) | yes | pass | pass | pass | pass | ? | - | pass | - |
| Brown Eyed Girl (Van Morrison) | yes | pass | pass | pass | pass | ? | - | pass | - |
| Love Me Do (The Beatles) | no | pass | **FLAG** | **FLAG** | pass | ? | - | **FLAG** | tempo, plausibility |
| Twist and Shout (The Beatles) | yes | pass | pass | pass | pass | ? | - | pass | - |
| Seven Nation Army (The White Stripes) | no | no ref | pass | pass | pass | ? | - | pass | - |
| Come As You Are (Nirvana) | no | no ref | pass | pass | pass | **FAIL** | - | **FAIL** | embed |
| Creep (Radiohead) | no | pass | pass | pass | pass | ? | - | pass | - |
| The House Of The Rising Sun (The Animals) | no | pass | pass | pass | pass | ? | - | pass | - |
| Wonderwall (Oasis) | yes | pass | pass | pass | **FLAG** | ? | - | **FLAG** | timing |
| Zombie (The Cranberries) | yes | pass | pass | pass | fixed | pass | - | pass | - |
| Good Riddance (Time of Your Life) (Green Day) | no | pass | pass | pass | **FLAG** | pass | - | **FLAG** | timing |
| Don't Look Back in Anger (Oasis) | yes | pass | pass | pass | **FLAG** | pass | - | **FLAG** | timing |
| Have You Ever Seen the Rain (Creedence Clearwater Re…) | yes | pass | pass | **FLAG** | pass | pass | - | **FLAG** | plausibility |
| Bad Moon Rising (Creedence Clearwater Re…) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Free Fallin' (Tom Petty) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Island in the Sun (Weezer) | yes | **FLAG** | pass | pass | pass | pass | - | **FLAG** | chords |
| Take Me Home, Country Roads (John Denver) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Sweet Home Alabama (Lynyrd Skynyrd) | no | pass | pass | pass | pass | pass | - | pass | - |
| Riptide (Vance Joy) | no | pass | pass | pass | few | pass | - | pass | - |
| Three Little Birds (Bob Marley & The Wailers) | yes | pass | pass | **FLAG** | pass | pass | - | **FLAG** | plausibility |
| A Horse with No Name (America) | no | **FLAG** | pass | **FAIL** | **FLAG** | pass | - | **FAIL** | chords, plausibility, timing |
| Sweet Caroline (Neil Diamond) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Wagon Wheel (Old Crow Medicine Show) | yes | pass | pass | pass | fixed | pass | - | pass | - |
| Sit Down (James) | yes | pass | pass | **FLAG** | **FLAG** | pass | - | **FLAG** | plausibility, timing |
| Yellow (Coldplay) | yes | pass | pass | **FLAG** | pass | pass | - | **FLAG** | plausibility |
| What's Up? (4 Non Blondes) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Breakfast at Tiffany's (Deep Blue Something) | yes | pass | pass | pass | few | pass | - | pass | - |
| Budapest (George Ezra) | yes | pass | pass | **FLAG** | pass | pass | - | **FLAG** | plausibility |
| Lucky Man (The Verve) | yes | pass | pass | pass | fixed | pass | - | pass | - |
| Heart of Gold (Neil Young) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Take It Easy (Eagles) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Stuck in the Middle with You (Stealers Wheel) | yes | pass | pass | **FAIL** | pass | pass | - | **FAIL** | plausibility |
| I'm Yours (Jason Mraz) | yes | pass | pass | pass | few | pass | - | pass | - |
| Boulevard of Broken Dreams (Green Day) | yes | pass | pass | pass | pass | pass | - | pass | - |
| I Want to Hold Your Hand (The Beatles) | yes | **FLAG** | pass | pass | pass | pass | - | **FLAG** | chords |
| Save Tonight (Eagle-Eye Cherry) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Learning to Fly (Tom Petty) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Ho Hey (The Lumineers) | yes | pass | pass | **FAIL** | pass | pass | - | **FAIL** | plausibility |
| Wild World (Cat Stevens) | yes | pass | pass | pass | pass | pass | - | pass | - |
| Help! (The Beatles) | yes | pass | pass | pass | pass | pass | - | pass | - |
| I'm Gonna Be (500 Miles) (The Proclaimers) | yes | pass | pass | **FLAG** | pass | pass | - | **FLAG** | plausibility |
| Torn (Natalie Imbruglia) | yes | pass | pass | pass | fixed | pass | - | pass | - |
| Crazy Little Thing Called Love (Queen) | yes | **FLAG** | pass | pass | few | pass | - | **FLAG** | chords |

Shipped 35: 21 pass, 12 flag, 2 fail. Excluded 9: 5 pass, 2 flag, 2 fail.

Shipped songs that are not a pass, with the reasons the tool gives:

- **FAIL** Ho Hey (The Lumineers): plausibility: 44% of chord time sits in 3 single holds of 24+ beats (longest 33.79 beats of C) although the progression has 4 families; the chart probably merges alternating chords.
- **FAIL** Stuck in the Middle with You (Stealers Wheel): plausibility: 56% of chord time sits in 6 single holds of 24+ beats (longest 48.89 beats of D) although the progression has 5 families; the chart probably merges alternating chords. plausibility: Expected chord absent from the chart: Am.
- **FLAG** Budapest (George Ezra): plausibility: 19% of chord time sits in holds of 24+ beats (longest 31.78 beats of F).
- **FLAG** Crazy Little Thing Called Love (Queen): chords: Unexpected main chord: Dm 9%.
- **FLAG** Don't Look Back in Anger (Oasis): consistency: 3 of 133 repeated chord changes (2%) fall about a beat away from where the same change usually falls; first at 207.22s G>Am (+0.84 beat), 219.38s G>Am (+1.35 beat), 279.38s F>C (-0.99 beat).
- **FLAG** Have You Ever Seen the Rain (Creedence Clearwater Revival): plausibility: 32% of chord time sits in holds of 24+ beats (longest 24.32 beats of C). plausibility: Expected chords absent from the chart: Dm E.
- **FLAG** I Want to Hold Your Hand (The Beatles): chords: Unexpected main chord: Bm 9%.
- **FLAG** I'm Gonna Be (500 Miles) (The Proclaimers): plausibility: 12% of chord time sits in holds of 24+ beats (longest 28.4 beats of E). plausibility: Expected chords absent from the chart: C#m F#m.
- **FLAG** Island in the Sun (Weezer): chords: Only 78% of chord time is in the expected families (G C D Em). chords: Unexpected main chord: Am 21%.
- **FLAG** Sit Down (James): plausibility: 30% of chord time sits in holds of 24+ beats (longest 29.08 beats of E). consistency: 5 of 60 repeated chord changes (8%) fall about a beat away from where the same change usually falls; first at 80.71s E>A (+0.78 beat), 149.35s E>A (+0.93 beat), 150.37s A>E (-0.86 beat), 156.97s E>A (+0.89 beat).
- **FLAG** Three Little Birds (Bob Marley & The Wailers): plausibility: 11% of chord time sits in holds of 24+ beats (longest 24.09 beats of A).
- **FLAG** Wild Thing (The Troggs): plausibility: 28% of chord time sits in holds of 24+ beats (longest 38.44 beats of A).
- **FLAG** Wonderwall (Oasis): consistency: 5 of 115 repeated chord changes (4%) fall about a beat away from where the same change usually falls (meter assumed, so bar positions are indicative only); first at 31.86s A>F#m (-0.78 beat), 59.16s A>F#m (-1.19 beat), 97.9s F#m>A (+0.89 beat), 137.93s F#m>A (-1.14 beat).
- **FLAG** Yellow (Coldplay): plausibility: 15% of chord time sits in holds of 24+ beats (longest 31.96 beats of B).

## Validation

How the verdicts line up with the founder's labels. The labelled negatives are the nine exclusions in `catalogue.json`, plus Zombie's timing report.

| Recording | Founder label | What the tool says | Caught for the right reason? |
|---|---|---|---|
| A Horse with No Name | Chart merges its two alternating chords | **FAIL** on plausibility: 36% of chord time in 5 holds of 24+ beats, longest 52.3 beats of Em, with Em and D expected. Also a chords flag (F#m 8% unexpected) and 2 isolated timing deviants. | Yes. This is the designed catch. |
| Zombie | Repeated changes sometimes a beat off | Raw pack chart: timing flag, 2 isolated deviants (133.9 s Em>C, +1.24 beats, Em held 5.4 beats then C only 2.7; 254.2 s C>Em, −0.86 beat). The exporter's auto-timing moved 4 changes, 2 by a whole beat (these two) and 2 by small snaps. The shipped timeline has 0 deviants, so the song passes and is marked `fixed`. | Yes, on the raw chart. Not out-of-sample: the thresholds were set after looking at Zombie. The two snaps (about 0.3 to 0.4 beat) are below this check's noise floor. |
| Riptide | More a ukulele song | Pass on everything (chord cover 97% of the expected A#m G# C#). | No. Instrument stage only, and only if the tagger has a ukulele tag that separates it from guitar. |
| Creep | Barre chords, picked verse | Pass. The chart has the teaching chords G B C Cm (cover 94%). | No. Difficulty is the exporter's level logic; picking is invisible here. |
| The House of the Rising Sun | Arpeggiated picking | Pass. | No. Playing style. |
| Seven Nation Army | Riff song | Pass; no chord reference. | No. Playing style. |
| Come as You Are | Riff song | **FAIL** on embed (age-restricted, recorded 24 October). | Right outcome, wrong reason. The riff is not seen. |
| Good Riddance | Picked, not strummed | Flag on timing: 26% of repeated changes sit in two stretches a beat off, and 3 isolated deviants. | No. It is a real property of that chart (the old bar-position spread of 0 to 3 in `STRUMALONG_APP.md`) but unrelated to picking. |
| Sweet Home Alabama | Picked riff | Pass. | No. Playing style. |
| Love Me Do | Harmonica-led | Flag on tempo (grid spacing 152 BPM against pulse 143.6) and plausibility (15% of chord time in long holds). | No. A harmonica tag would catch it, untested. |

Summary:

- The two chart-level problems the founder named are caught by the non-instrument checks: A Horse with No Name (fail) and Zombie (found on the raw chart; fixed by the exporter).
- Of the seven instrument or playing-style negatives (Riptide, Creep, House, Seven Nation Army, Good Riddance, Sweet Home Alabama, Love Me Do), **none is caught for its real reason** without the instrument stage. Two are flagged by accident (Good Riddance, Love Me Do), five pass, and Come as You Are fails on an embed fact. This is expected: chords, tempo, plausibility and timing do not describe what the guitar is playing. Even the instrument stage is untested on picked-versus-strummed.
- There are no founder-labelled *good* songs, so **precision is unknown**. Of 35 shipped songs, 21 pass, 12 flag and 2 fail. Nobody has listened to the flagged or failed ones. In particular, the rule that catches A Horse also fails Ho Hey (C held 24 to 34 beats, three times, with C, F, Am and G expected) and Stuck in the Middle with You (D held up to 49 beats). These may be the same failure or real vamps and intros. A short listen to those two and to Sit Down (flag) would show whether the plausibility gate is right.
- The plausibility and timing thresholds were chosen after seeing A Horse (5 long holds, 52 beats, 36%) and Zombie (2 deviants of 87). They fit those two cases; they are not an independent test. A single stray deviant is deliberately not flagged. A threshold of 1 would flag three more shipped songs (Twist and Shout, Budapest, Take It Easy).

### Cross-check of the exporter's auto-timing

Measured with this tool's own offsets on the raw charts. Across the 19 songs the exporter changed, none of its moves made a change worse. Eight of its whole-beat moves fix a change that this tool also finds about a beat off in the raw chart (Zombie 2, Wagon Wheel 2, and one each in Don't Look Back in Anger, Lucky Man, Heart of Gold and Torn); the whole-beat move in I'm Yours is in a group too small to measure. The rest are snaps of at most about 0.6 beat. Free Fallin' has 9 and Learning to Fly 15 such snaps, none over about 0.4 beat, on changes that were already within the grid's noise of their group, so they are harmless but unneeded.

## Limitations

- Everything is relative to automatic charts and estimated grids. A song can pass every check and still be wrong.
- The chord check is only as good as the expected lists. Several are medium or low confidence and none is a timed transcription.
- The consistency test needs repetition. Sequences played once, and songs with few repeats (Riptide, Breakfast at Tiffany's, I'm Yours, Crazy Little Thing Called Love), get `few`.
- Wonderwall's meter is assumed (the beat count varies), so its bar positions are indicative only; it cannot hard-fail on timing.
- The report was moved out of the deployed `strumalong/` root on 25 October; it now lives at `docs/STRUMALONG_CATALOGUE_CHECKS.json`.
- The report depends on the exporter's state when it was generated. The song index hash is recorded in `generated_from`.
