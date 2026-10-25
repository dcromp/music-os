# Strum Along catalogue checks

Date: 25 October 2026. Tool: `experiments/analysis/strumalong/catalogue_checks.js`. Report: `docs/STRUMALONG_CATALOGUE_CHECKS.json`. Tests: `experiments/analysis/strumalong/catalogue_checks.test.js` and `test_instrument_stage.py`. No lyrics appear in any input or output.

Founder feedback on 25 October 2026: "The idea of a curated list is that we can automate basic checks like chords and instruments." Riptide "is more a ukulele song", and Zombie "has some chord mis timings ... a chord is 1 beat before going into the 3 beats of a different chord, but every other time that sequence is played the timing is correct". This tool is that automation. It gives every candidate recording in the packs listed in `strumalong/data/catalogue.json` a verdict of **pass**, **flag** or **fail**, each with reasons. Excluded recordings are checked too. They are the founder's labelled negatives, so they show what the checks can and cannot catch.

A verdict means "no automated check objected", not "verified". The charts are automatic CREMA drafts and the beat grids are estimated. The checker reads no audio itself: the instrument stage and the hold check read numbers that local Python tools computed from the audio beforehand (Demucs stems, YAMNet tags, strum features, hold homogeneity). Nobody has listened to the flagged songs. Every verdict lists what was *not* checked (`not_checked`).

## Run

```
node experiments/analysis/strumalong/catalogue_checks.js            # text table, writes docs/STRUMALONG_CATALOGUE_CHECKS.json
node experiments/analysis/strumalong/catalogue_checks.js --json     # full report on stdout
node experiments/analysis/strumalong/catalogue_checks.js --markdown # summary table in markdown (the snapshot below)
node experiments/analysis/strumalong/catalogue_checks.test.js       # tests (plain node, node:assert)
```

The audio evidence the checker reads is made beforehand by local tools, offline, into gitignored files (section 6 and the hold check in section 3):

```
.venv-demucs/bin/python experiments/analysis/strumalong/stems_6s.py          # Demucs guitar stems + stem statistics
.venv-crema/bin/python  experiments/analysis/strumalong/yamnet_tags.py       # YAMNet tags -> strumalong-instrument-tags.json
.venv-crema/bin/python  experiments/analysis/strumalong/strum_features.py    # on-beat restrike -> same file, `strum` blocks
.venv-crema/bin/python  experiments/analysis/strumalong/hold_homogeneity.py  # audio inside long holds -> strumalong-hold-checks.json
.venv-crema/bin/python  -m unittest discover -s experiments/analysis/strumalong -p 'test_instrument_stage.py'
```

Other flags: `--no-write`, `--out <path>`, `--check` (exit 1 when the report on disk is stale; the report has no timestamp, so a rerun on unchanged inputs is byte-identical) and `--strict` (also exit 1 when a shipped song is flagged).

**Exit code.** Non-zero when a *shipped* song fails a hard gate. "Shipped" means the recording is in the catalogue and not excluded. Excluded songs may fail without stopping the run. A flag alone never stops it unless `--strict` is given.

The tool is read-only on every input: the frozen packs, `experiments/review/*.json`, the exported `strumalong/songs/*.json`, and the fixtures. It writes only the report. It does not read audio; the gitignored instrument tags and hold checks are read when present.

## Verdicts

- The song verdict is the worst status among the checks that ran: fail > flag > pass.
- `unknown` (embed), `not run` and `not measured` (instrument parts) and `no reference` (chords) never lower a verdict. They are listed in `not_checked`, and in the tables as `?`, `-` and `no ref`.
- `few` in the Timing column means too few repeated changes to judge. `fixed` means the raw chart had mistimed repeated changes and the exporter's auto-timing removed them.
- Songs with an exported `songs/<id>.json` are judged on **what ships** (display corrections and the exporter's timing fixes included). Others are judged on the pack's raw CREMA chart on the pack's beat grid. The report says which (`view_source`).

## Inputs

| Check | Reads |
|---|---|
| Chords | `experiments/analysis/strumalong/expected-chords.json` (v1) and `expected-chords-v2.json` (v2). For the first ten: `catalogue/first-ten-review.json` (teaching chord set at the teaching capo, converted to sounding chords) plus, when present, `experiments/generated/accompaniment-review-20261018/online-reviewed-v2.json` (sounding palettes of the usable teaching sources, as *accepted extras*). Seven Nation Army and Come as You Are have no reference. |
| Tempo | `experiments/fixtures/rhythm-first-ten.json`, `rhythm-strumalong-additions-v1.json`, `-v2.json` (prior ranges), and the pack's `rhythm.json` (pulse, beat times). |
| Plausibility | The chart and beat grid, plus the expected chords for the "progression has several families" test, and `experiments/generated/strumalong-hold-checks.json` (hold homogeneity, `hold_homogeneity.py`) if it exists. |
| Timing | The exported song (`chords`, `beats`, `rhythm`, per-chord `b`, `a`, `c`, `t`, and `chart.corrections` of kind `timing`), or the pack chart and grid. |
| Embed | `experiments/fixtures/strumalong-additions-candidates-v1.json` and `-v2.json` (per-entry `embed` and the fixture-level `checked` text), the exported `songs/index.json` card (`playable_embed`), and one fact recorded in git history. |
| Instrument | `experiments/generated/strumalong-instrument-tags.json`, if it exists: YAMNet tags (`yamnet_tags.py`), Demucs stem shares (`stems_6s.py`) and strum features (`strum_features.py`). |

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
- **merge signature** (`merge_signature`), all of: at least two expected families, at least 25% of chord time in long holds, at least 3 separate long holds (one break or solo is legitimate), and a hold of 32 beats or more (eight bars of 4/4). This is the A Horse with No Name chart: Em for up to 52 beats where the song alternates every bar. The same shape is also what a real vamp or a long intro looks like, so **on its own it only flags**.
- **fail** needs the merge signature **and** audio evidence from the hold check (`experiments/generated/strumalong-hold-checks.json`, written by `hold_homogeneity.py`; its docstring has the method). The hold check takes each bar inside a long hold and asks whether another of the song's main chords fits the bar's chroma better than the held chord, by more than 0.10 Pearson r. The song fails when that happens in at least 25% of the bars inside the chart's own long holds (24+ beats), counted over at least 12 bars.
- Each long hold is matched to the hold-check hold that starts within 1 s of it. If the file is missing, was made from the other chart (pack instead of exported, or the reverse), or any long hold has no match, the evidence counts as absent. The song then only flags, and `not_checked` lists `plausibility: hold homogeneity (no matching hold check)`.
- **flag** in three cases:
  - the progression has two or more families (expected, or the chart's own main families when there is no reference) and 10% or more of chord time is in long holds;
  - any hold lasts 32 beats or more;
  - N+X is at least 20% of the recording (fail at 50%).
- `hold_evidence` appears for every song that has long holds in the file. Its status is `measured`, `no long holds` or `mismatch`, with the matched holds and their missed bars. It changes a song's status only when the song has the merge signature.

Calibration on 25 October 2026, as missed bars over bars inside the chart's 24+ beat holds:

- A Horse with No Name: 17 of 45 (0.38), so it **fails**. Its whole-file fraction stays between 0.38 and 0.40 at hold-check margins of 0.05 to 0.20.
- Ho Hey 1 of 22 (0.05) and Stuck in the Middle with You 1 of 55 (0.02): these vamps now **flag** instead of failing.
- No other recording has the merge signature, so no other status changed.
- Highest fractions among the rest, whose status does not move: Sweet Caroline 4 of 6, Take It Easy 3 of 6, Love Me Do 4 of 12, Torn 2 of 6, Three Little Birds 2 of 6, Wild Thing 4 of 17. Six bars is too few to mean anything. Wild Thing (0.24 over 17 bars) would be the first shipped song at risk if its chart ever grew the signature.

Can tell: charts that merge alternating chords into long holds, when the audio inside the holds disagrees with the chart. Charts that are mostly N or X.

Cannot tell:

- A chart that merged chords into *short* wrong holds.
- A real long hold from a merged one when the hold check is missing or stale.
- Chords whose pitch classes nearly coincide (G6 and Em7, or Em7 and D6add9 with open strings ringing). The hold check's `claim` mode can call a coloured chord a missed change.

The 25% line rests on one failing song and two vamps that pass. Nobody has listened to any of them bar by bar.

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

### 6. Instrument: guitar-led and strummed

Three local tools write the evidence. All their outputs are gitignored, and both models are the founder-approved copies under `experiments/candidate-assets/` (their SHA-256 values are in the file).

1. `experiments/analysis/strumalong/stems_6s.py` (`.venv-demucs`) separates the pack audio with Demucs htdemucs_6s. It writes `experiments/generated/strumalong-stems/<id>/guitar16k.wav` (the guitar stem, mono 16 kHz) and `stats.json` (stem energies and shares).
2. `experiments/analysis/strumalong/yamnet_tags.py` (`.venv-crema`) runs YAMNet on the full mix and on the guitar stem. It writes the tags file `experiments/generated/strumalong-instrument-tags.json` and copies the stem statistics into it.
3. `experiments/analysis/strumalong/strum_features.py` (`.venv-crema`, about 15 s for all 44 recordings) measures how the guitar stem is played and merges a `strum` block per recording into the same file.

Run 1 first; 2 and 3 can run in either order, because each keeps the fields the other wrote. Without the tags file every song shows `not run` and its verdict does not change.

The check has two parts. Each part is pass, flag, fail, `not run` or `not measured`, and the check's status is the worse of the two.

**Guitar-led.** The main signal is `stems.guitar_share_of_harmonic`: the Demucs guitar stem's energy divided by guitar + piano + other. YAMNet's `scores` corroborate it.

- **fail** when two independent models agree:
  - share under 0.10 (the guitar stem is nearly empty) and YAMNet's best guitar tag under 0.25; or
  - share under 0.33 and a non-guitar tag of at least 0.30 leads the best guitar tag by 0.15 or more.
- **flag** when any one of these holds:
  - share under 0.33;
  - YAMNet's best guitar tag under 0.25;
  - a non-guitar tag of at least 0.30 sits at or above the best guitar tag.
- YAMNet alone never fails. Nor does a low share that YAMNet contradicts, because a separation failure would look the same.
- Where the cuts sit in the data:
  - Riptide 0.04 (below 0.10);
  - Love Me Do 0.14, Sweet Caroline 0.17 and Three Little Birds 0.22 (below 0.33);
  - the next recording, Wagon Wheel, at 0.59.
- Because both cuts fall in these gaps, any cut from 0.05 to 0.13, or from 0.22 to 0.58, gives the same verdicts. The YAMNet thresholds (0.25, 0.30, 0.15) are the ones set before the batch ran. They now only corroborate the share.

**Strummed.** The signal is `strum.restrike_onbeat`, which asks whether the guitar re-strikes the whole chord on the beat. A down-strum re-excites every string, so nearly all sounding partials get louder at once. A picked note or a riff excites one string while the others keep decaying.

- How it is measured:
  - On every guitar-stem attack within 60 ms of a beat of the pack's grid, compare 2048-point spectra about 72 ms after and before the attack.
  - Take the 120 to 2000 Hz partial peaks within 30 dB of the loudest, and count the share that got louder.
  - The song value is the mean over on-beat attacks, with its standard error (`restrike_onbeat_se`, typically 0.01).
  - Up-strums and off-beat attacks look like picking in every song, so only on-beat attacks are used.
  - The `strum_features.py` docstring has every constant.
- **flag** when `restrike_onbeat` is under 0.64 and there are at least 50 on-beat attacks. 0.64 is the highest founder-labelled picked or riff song (Creep 0.630) plus one standard error.
- It **never fails**. The labelled picked and riff songs score 0.583 to 0.630, and dense or distorted strummed songs score 0.627 to 0.655: they overlap within about two standard errors.
- **not measured**, listed in `not_checked`, in two cases:
  - the guitar-led part fails, because then the stem holds only bleed from other instruments;
  - there are fewer than 50 on-beat attacks.
- `single_onbeat` is reported but does not gate. It is the share of on-beat attacks that renew only one tone of the chart's chord; high means picked. It depends on the CREMA chart being right, and adding it did not improve the leave-one-out result.
- YAMNet's Strum class is ignored. It scored the picked House of the Rising Sun above the strummed Zombie.

**Staleness.** The part flags when the tags' `audio_sha256` differs from the pack's audio, and when `strum.audio_sha256` (the audio the stem was separated from) differs.

Schema `strumalong-instrument-tags-1`, extended. The checker reads `model`, `recordings.<id>.audio_sha256`, `.scores`, `.stems.guitar_share_of_harmonic` and `.strum.{restrike_onbeat, restrike_onbeat_se, onbeat_attacks, single_onbeat, audio_sha256, version}`. Every other field is evidence for people.

```json
{ "schema": "strumalong-instrument-tags-1",
  "model": { "name": "yamnet", "version": "1", "sha256": "<tarball sha256>",
             "aggregation": "<one line: which statistic of which source scores holds>",
             "stem_model": { "name": "htdemucs_6s", "weights_sha256": "..." } },
  "provenance": { "saved_model_pb_sha256": "...", "scores_from": "max", "scores_stat": "top5", "strum_in_scores": false,
                  "aggregation_detail": "...", "guitar_classes": ["..."], "tool": "..." },
  "strum_features": { "tool": "experiments/analysis/strumalong/strum_features.py", "version": "strum-features-1",
                      "definition": "...", "params": { "hop": 128, "n_fft": 2048, "beat_tolerance_seconds": 0.06, "...": 0 } },
  "recordings": {
    "<recording_id>": {
      "audio_sha256": "<sha256 of the pack's prepared audio, checked against the pack when present>",
      "model": "<optional per-recording override>",
      "pack": "...", "excluded": false, "excluded_reason": "<excluded only>",
      "scores": { "guitar": 0.0, "acoustic_guitar": 0.0, "electric_guitar": 0.0, "steel_guitar": 0.0, "ukulele": 0.0, "piano": 0.0,
                  "harmonica": 0.0, "banjo": 0.0, "mandolin": 0.0, "accordion": 0.0, "organ": 0.0, "keyboard": 0.0,
                  "synthesizer": 0.0, "violin": 0.0, "harp": 0.0, "electric_piano": 0.0, "brass": 0.0, "trumpet": 0.0,
                  "plucked_string": 0.0, "sitar": 0.0 },
      "scores_aggregation": "max/top5",
      "full_mix":    { "frames": 0, "classes": { "<tag>": { "mean": 0.0, "p90": 0.0, "top5_frac": 0.0 } },
                       "top_classes": [ { "name": "...", "mean": 0.0, "top5_frac": 0.0 } ],
                       "any_guitar_top5_frac": 0.0, "strum_given_guitar": { "value": 0.0, "frames": 0 } },
      "guitar_stem": { "<same shape as full_mix, YAMNet run on the Demucs guitar stem; absent without a stem>" },
      "stems": { "energy_share": { "drums": 0.0, "bass": 0.0, "other": 0.0, "vocals": 0.0, "guitar": 0.0, "piano": 0.0 },
                 "rms_dbfs": { "...": 0.0 }, "guitar_share_of_harmonic": 0.0, "guitar_active_fraction": 0.0,
                 "guitar_low_band_ratio": 0.0, "guitar_low_band_db": 0.0, "guitar_centroid_hz": 0.0,
                 "model": "htdemucs_6s", "weights_sha256": "...", "stats_file": "experiments/generated/strumalong-stems/<id>/stats.json" },
      "strum": { "restrike_onbeat": 0.0, "restrike_onbeat_se": 0.0, "onbeat_attacks": 0, "single_onbeat": 0.0,
                 "single_onbeat_attacks": 0, "restrike_all": 0.0, "attacks": 0, "attacks_per_beat": 0.0, "beats": 0,
                 "stem_active_fraction": 0.0, "audio_sha256": "<audio the stem was separated from>", "stem_sha256": "...",
                 "chart_sha256": "<the pack primary.json single_onbeat used>", "version": "strum-features-1" } } } }
```

- `scores`: numbers in [0, 1], one statistic of one source per tag, named in `model.aggregation`. The default `max/top5` takes, per tag, the larger of the full-mix and guitar-stem value. The statistic is the fraction of YAMNet frames (0.96 s windows, 0.48 s hop) in which the class is among the five highest. It is a frame fraction, not a probability. YAMNet's raw probabilities are tiny for every instrument in a dense mix (guitar 90th percentile 0.02 to 0.06), so no probability threshold works on them.
- `full_mix` and `guitar_stem` give per class (looked up by display name): `mean`, `p90` and `top5_frac`. `strum_given_guitar` is the mean Strum score over frames with a guitar class in the top five.
- `stems`:
  - energy is the mean square of the mono stem at 44.1 kHz;
  - `guitar_share_of_harmonic` is guitar / (guitar + piano + other);
  - `guitar_active_fraction` is the share of 46 ms frames in which the guitar stem is at least 3% of the mix's energy;
  - `guitar_low_band_ratio` is 70-250 Hz energy over 250-4000 Hz energy on those frames.
  - `strum_features.py` fills `stems` from `stats.json` only when `yamnet_tags.py` has not written it.
- `strum`: see above. `restrike_all` (every attack, not only on-beat ones) and `attacks_per_beat` are context. Dense 16th-note strumming lowers `restrike_onbeat`: Spearman −0.69 with attacks per beat among the strummed songs.

A bare map from recording id to `{model, scores, ...}` is accepted too.

Can tell:

- that a recording's harmonic bed is not mainly guitar (ukulele, harmonica, keys or horns leading);
- that the guitar on the beat does not re-strike the chord the way a strum does.

Cannot tell (see Validation): a picked verse inside a strummed song; picking under heavy string or organ bleed; whether a low score is picking or dense distorted strumming; an instrument Demucs files under "guitar" (a ukulele that leaks into the guitar stem would pass the share).

## Thresholds

All thresholds live in `T` in the script and are printed into the report under `thresholds`; that copy is authoritative.

| Check | Threshold |
|---|---|
| Main family | at least 4% of chord time |
| Chords | cover fail under 50%, flag under 80%; missing under 1%; first 3 expected are core; unexpected main flags at 8% |
| Tempo | edge pin 1.5%; fail more than 10% outside range; half/double window 8%; median hold at least 12 or at most 1 beat; grid spacing gap 4%; spacing variation 8% |
| Plausibility | long hold 24 beats; flag at 10% of chord time or a 32-beat hold; merge signature at 25% and 3 long holds and a 32-beat hold with 2+ expected families (flag); fail = signature and hold check missing 25%+ of 12+ bars (holds matched within 1 s); N+X flag 20%, fail 50% |
| Timing | group of 4+ changes, 60% within 0.5 beat; deviant 0.75 to 1.5 beats; shift of 3+; flag at 2 isolated deviants or 10% unfollowed shift; fail under 80%; auto-timing worse by 0.25 beat twice, or 10% of changes moved |
| Instrument | guitar-led: share fail under 0.10 with YAMNet guitar under 0.25, or under 0.33 with a non-guitar tag 0.30+ and 0.15 ahead; share flag under 0.33; YAMNet flags at guitar under 0.25 or a 0.30+ tag at or above guitar. Strummed: flag restrike_onbeat under 0.64 with 50+ on-beat attacks; never fails |

## Report schema

`strumalong-catalogue-checks-1`: `generated_from`, `thresholds`, `summary`, `unmatched_exclusions` (an excluded id that names no recording in any available pack), and `songs`. Each song has `recording_id`, `title`, `artist`, `pack`, `shipped`, `excluded_reason` (excluded only), `exported`, `view_source`, `chart_sha256`, `exported_sha256`, `checks` (`chords`, `tempo`, `plausibility`, `consistency`, `embed`, `instrument`, each with a `status`, `reasons` and its measurements), `verdict`, `reasons`, `notes` and `not_checked`. `plausibility` adds `merge_signature` and `hold_evidence` (`status`, `bars`, `missed_bars`, `missed_change_fraction`, matched `holds`). `instrument` adds `guitar_led` (`status`, `guitar_share_of_harmonic`, `yamnet_best_guitar`, `yamnet_lead_other`) and `strummed` (`status`, `restrike_onbeat`, `restrike_onbeat_se`, `onbeat_attacks`, `single_onbeat`, `version`). `generated_from` records the SHA-256 of the instrument tags and hold-check files it read (`instrument_tags`, `hold_checks`).

## Snapshot, 25 October 2026

Generated from the checkout at the time, with the exporter's auto-timing, the instrument tags (YAMNet, Demucs stems, strum features) and the hold checks present. Refresh with `--markdown`. The `songs_index_sha256` in the report says which export it saw; `instrument_tags` and `hold_checks` say which evidence files.

| Song | Ships | Chords | Tempo | Plausibility | Timing | Embed | Instrument | Verdict | Flagged by |
|---|---|---|---|---|---|---|---|---|---|
| Wild Thing (The Troggs) | yes | pass | pass | **FLAG** | pass | ? | pass | **FLAG** | plausibility |
| Knockin' on Heaven's Door (Bob Dylan) | yes | pass | pass | pass | pass | ? | pass | pass | - |
| Brown Eyed Girl (Van Morrison) | yes | pass | pass | pass | pass | ? | pass | pass | - |
| Love Me Do (The Beatles) | no | pass | **FLAG** | **FLAG** | pass | ? | **FLAG** | **FLAG** | tempo, plausibility, instrument |
| Twist and Shout (The Beatles) | yes | pass | pass | pass | pass | ? | pass | pass | - |
| Seven Nation Army (The White Stripes) | no | no ref | pass | pass | pass | ? | **FLAG** | **FLAG** | instrument |
| Come As You Are (Nirvana) | no | no ref | pass | pass | pass | **FAIL** | **FLAG** | **FAIL** | embed, instrument |
| Creep (Radiohead) | no | pass | pass | pass | pass | ? | **FLAG** | **FLAG** | instrument |
| The House Of The Rising Sun (The Animals) | no | pass | pass | pass | pass | ? | **FLAG** | **FLAG** | instrument |
| Wonderwall (Oasis) | yes | pass | pass | pass | **FLAG** | ? | pass | **FLAG** | timing |
| Zombie (The Cranberries) | yes | pass | pass | pass | fixed | pass | pass | pass | - |
| Good Riddance (Time of Your Life) (Green Day) | no | pass | pass | pass | **FLAG** | pass | **FLAG** | **FLAG** | timing, instrument |
| Don't Look Back in Anger (Oasis) | yes | pass | pass | pass | **FLAG** | pass | **FLAG** | **FLAG** | timing, instrument |
| Have You Ever Seen the Rain (Creedence Clearwater Re…) | yes | pass | pass | **FLAG** | pass | pass | pass | **FLAG** | plausibility |
| Bad Moon Rising (Creedence Clearwater Re…) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Free Fallin' (Tom Petty) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Island in the Sun (Weezer) | yes | **FLAG** | pass | pass | pass | pass | pass | **FLAG** | chords |
| Take Me Home, Country Roads (John Denver) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Sweet Home Alabama (Lynyrd Skynyrd) | no | pass | pass | pass | pass | pass | **FLAG** | **FLAG** | instrument |
| Riptide (Vance Joy) | no | pass | pass | pass | few | pass | **FAIL** | **FAIL** | instrument |
| Three Little Birds (Bob Marley & The Wailers) | yes | pass | pass | **FLAG** | pass | pass | **FLAG** | **FLAG** | plausibility, instrument |
| A Horse with No Name (America) | no | **FLAG** | pass | **FAIL** | **FLAG** | pass | pass | **FAIL** | chords, plausibility, timing |
| Sweet Caroline (Neil Diamond) | yes | pass | pass | pass | pass | pass | **FLAG** | **FLAG** | instrument |
| Wagon Wheel (Old Crow Medicine Show) | yes | pass | pass | pass | fixed | pass | pass | pass | - |
| Sit Down (James) | yes | pass | pass | **FLAG** | **FLAG** | pass | **FLAG** | **FLAG** | plausibility, timing, instrument |
| Yellow (Coldplay) | yes | pass | pass | **FLAG** | pass | pass | **FLAG** | **FLAG** | plausibility, instrument |
| What's Up? (4 Non Blondes) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Breakfast at Tiffany's (Deep Blue Something) | yes | pass | pass | pass | few | pass | pass | pass | - |
| Budapest (George Ezra) | yes | pass | pass | **FLAG** | pass | pass | pass | **FLAG** | plausibility |
| Lucky Man (The Verve) | yes | pass | pass | pass | fixed | pass | **FLAG** | **FLAG** | instrument |
| Heart of Gold (Neil Young) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Take It Easy (Eagles) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Stuck in the Middle with You (Stealers Wheel) | yes | pass | pass | **FLAG** | pass | pass | pass | **FLAG** | plausibility |
| I'm Yours (Jason Mraz) | yes | pass | pass | pass | few | pass | pass | pass | - |
| Boulevard of Broken Dreams (Green Day) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| I Want to Hold Your Hand (The Beatles) | yes | **FLAG** | pass | pass | pass | pass | pass | **FLAG** | chords |
| Save Tonight (Eagle-Eye Cherry) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Learning to Fly (Tom Petty) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Ho Hey (The Lumineers) | yes | pass | pass | **FLAG** | pass | pass | pass | **FLAG** | plausibility |
| Wild World (Cat Stevens) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| Help! (The Beatles) | yes | pass | pass | pass | pass | pass | pass | pass | - |
| I'm Gonna Be (500 Miles) (The Proclaimers) | yes | pass | pass | **FLAG** | pass | pass | pass | **FLAG** | plausibility |
| Torn (Natalie Imbruglia) | yes | pass | pass | pass | fixed | pass | pass | pass | - |
| Crazy Little Thing Called Love (Queen) | yes | **FLAG** | pass | pass | few | pass | pass | **FLAG** | chords |

Shipped 35: 19 pass, 16 flag, 0 fail. Excluded 9: 0 pass, 6 flag, 3 fail.

Shipped songs that are not a pass, with the reasons the tool gives:

- **FLAG** Budapest (George Ezra): plausibility: 19% of chord time sits in holds of 24+ beats (longest 31.78 beats of F).
- **FLAG** Crazy Little Thing Called Love (Queen): chords: Unexpected main chord: Dm 9%.
- **FLAG** Don't Look Back in Anger (Oasis): consistency: 3 of 133 repeated chord changes (2%) fall about a beat away from where the same change usually falls; first at 207.22s G>Am (+0.84 beat), 219.38s G>Am (+1.35 beat), 279.38s F>C (-0.99 beat). instrument: strummed: On-beat guitar attacks re-strike only 63% of the sounding partials (restrike_onbeat 0.631 ± 0.005, flag under 0.64; the founder-labelled picked and riff songs score 0.58 to 0.63). The recorded guitar may be picked or a riff, or this is dense or distorted strumming (a known false alarm). Listen.
- **FLAG** Have You Ever Seen the Rain (Creedence Clearwater Revival): plausibility: 32% of chord time sits in holds of 24+ beats (longest 24.32 beats of C). plausibility: Expected chords absent from the chart: Dm E.
- **FLAG** Ho Hey (The Lumineers): plausibility: 44% of chord time sits in 3 single holds of 24+ beats (longest 33.79 beats of C) although the progression has 4 families; the chart may merge alternating chords, but the audio inside them mostly stays on the held chord (1 of 22 bars fit another chord better, under 25%), so they may be real vamps or breaks.
- **FLAG** I Want to Hold Your Hand (The Beatles): chords: Unexpected main chord: Bm 9%.
- **FLAG** I'm Gonna Be (500 Miles) (The Proclaimers): plausibility: 12% of chord time sits in holds of 24+ beats (longest 28.4 beats of E). plausibility: Expected chords absent from the chart: C#m F#m.
- **FLAG** Island in the Sun (Weezer): chords: Only 78% of chord time is in the expected families (G C D Em). chords: Unexpected main chord: Am 21%.
- **FLAG** Lucky Man (The Verve): instrument: strummed: On-beat guitar attacks re-strike only 63% of the sounding partials (restrike_onbeat 0.627 ± 0.007, flag under 0.64; the founder-labelled picked and riff songs score 0.58 to 0.63). The recorded guitar may be picked or a riff, or this is dense or distorted strumming (a known false alarm). Listen.
- **FLAG** Sit Down (James): plausibility: 30% of chord time sits in holds of 24+ beats (longest 29.08 beats of E). consistency: 5 of 60 repeated chord changes (8%) fall about a beat away from where the same change usually falls; first at 80.71s E>A (+0.78 beat), 149.35s E>A (+0.93 beat), 150.37s A>E (-0.86 beat), 156.97s E>A (+0.89 beat). instrument: strummed: On-beat guitar attacks re-strike only 59% of the sounding partials (restrike_onbeat 0.592 ± 0.008, flag under 0.64; the founder-labelled picked and riff songs score 0.58 to 0.63). The recorded guitar may be picked or a riff, or this is dense or distorted strumming (a known false alarm). Listen.
- **FLAG** Stuck in the Middle with You (Stealers Wheel): plausibility: 56% of chord time sits in 6 single holds of 24+ beats (longest 48.89 beats of D) although the progression has 5 families; the chart may merge alternating chords, but the audio inside them mostly stays on the held chord (1 of 55 bars fit another chord better, under 25%), so they may be real vamps or breaks. plausibility: Expected chord absent from the chart: Am.
- **FLAG** Sweet Caroline (Neil Diamond): instrument: guitar-led: Guitar carries only 17% of the harmonic accompaniment (Demucs guitar / (guitar + piano + other)); another instrument may lead. Listen.
- **FLAG** Three Little Birds (Bob Marley & The Wailers): plausibility: 11% of chord time sits in holds of 24+ beats (longest 24.09 beats of A). instrument: guitar-led: Guitar carries only 22% of the harmonic accompaniment (Demucs guitar / (guitar + piano + other)); another instrument may lead. Listen.
- **FLAG** Wild Thing (The Troggs): plausibility: 28% of chord time sits in holds of 24+ beats (longest 38.44 beats of A).
- **FLAG** Wonderwall (Oasis): consistency: 5 of 115 repeated chord changes (4%) fall about a beat away from where the same change usually falls (meter assumed, so bar positions are indicative only); first at 31.86s A>F#m (-0.78 beat), 59.16s A>F#m (-1.19 beat), 97.9s F#m>A (+0.89 beat), 137.93s F#m>A (-1.14 beat).
- **FLAG** Yellow (Coldplay): plausibility: 15% of chord time sits in holds of 24+ beats (longest 31.96 beats of B). instrument: strummed: On-beat guitar attacks re-strike only 63% of the sounding partials (restrike_onbeat 0.634 ± 0.007, flag under 0.64; the founder-labelled picked and riff songs score 0.58 to 0.63). The recorded guitar may be picked or a riff, or this is dense or distorted strumming (a known false alarm). Listen.

## Validation

How the verdicts line up with the founder's labels. The labelled negatives are the nine exclusions in `catalogue.json`, plus Zombie's timing report.

| Recording | Founder label | What the tool says | Caught for the right reason? |
|---|---|---|---|
| A Horse with No Name | Chart merges its two alternating chords | **FAIL** on plausibility: the merge signature (36% of chord time in 5 holds of 24+ beats, longest 52.3 beats of Em, with Em and D expected) and the hold check (17 of 45 bars inside those holds fit D better than Em). Also a chords flag (F#m 8% unexpected) and 2 isolated timing deviants. The instrument stage passes it: guitar share 0.94, restrike 0.703. | Yes. This is the designed catch, and the strummed guitar is recognised as strummed. |
| Zombie | Repeated changes sometimes a beat off | **Raw pack chart:** timing flag with 2 isolated deviants: 133.9 s Em>C, +1.24 beats (Em held 5.4 beats, then C only 2.7); 254.2 s C>Em, −0.86 beat. **Exporter:** its auto-timing moved 4 changes, 2 of them by a whole beat (these two) and 2 by small snaps. **Shipped:** the timeline has 0 deviants, so the song passes and is marked `fixed`. | Yes, on the raw chart. Not out-of-sample: the thresholds were set after looking at Zombie. The two snaps (about 0.3 to 0.4 beat) are below this check's noise floor. |
| Riptide | More a ukulele song | **FAIL** on instrument (guitar-led): the Demucs guitar stem is nearly empty (share 0.04) and YAMNet hears no guitar (0.06). | Yes. |
| Love Me Do | Harmonica-led | **FLAG** on instrument (guitar share 0.14), also on tempo and plausibility. Not a fail: YAMNet still hears guitar (0.25) about as often as harmonica (0.28, under the 0.30 corroboration level). | Yes, as a flag. Sweet Caroline (0.17) is too close for a fail. |
| Creep | Barre chords, picked verse | **FLAG** on strummed: restrike 0.630, inside the picked range. A 20 s timeline shows the clean verse scoring strum-like (0.72 in the first 40 s). The distorted chorus (0.60 to 0.63) is what pulls the song down. | Right outcome, partly the wrong reason. |
| The House of the Rising Sun | Arpeggiated picking | **FLAG** on strummed: 0.625. The arpeggiated opening scores 0.52 to 0.57; later stretches with organ bleed score 0.61 to 0.78. | Yes, mostly. |
| Seven Nation Army | Riff song | **FLAG** on strummed: 0.615. No chord reference. | Yes, as a flag. |
| Come as You Are | Riff song | **FAIL** on embed (age-restricted, recorded 24 October) and **FLAG** on strummed (0.627). | The flag is for the right reason. |
| Good Riddance | Picked, not strummed | **FLAG** on strummed: 0.623. The picked intro and verse score 0.55; the middle section with strings scores 0.64 to 0.71. Also a timing flag (a property of the chart, unrelated to picking). | Yes, mostly. |
| Sweet Home Alabama | Picked riff | **FLAG** on strummed: 0.583, the lowest of all 44. Its half-beat attacks score 0.78, so this is either a riff accented off the beat or a grid half a beat out. | Yes, as a flag. |

Summary:

- **Chart problems.** The two the founder named are caught by the non-instrument checks: A Horse with No Name (fail) and Zombie (found on the raw chart, fixed by the exporter).
- **Plausibility now needs two signals to fail.** The chart signature alone used to fail Ho Hey and Stuck in the Middle with You. Now a fail needs the signature and the hold check together, so those two only flag: the hold check finds their audio staying on the held chord (1 of 22 and 1 of 55 bars).
- **Instrument and technique negatives.** With the instrument stage, all 8 are caught: Riptide fails, and the other 7 flag. Without it, none was caught for its real reason. These are in-sample numbers; the leave-one-out figures are below.
- **Precision is unknown.** There are no founder-confirmed *good* songs apart from A Horse with No Name's guitar. Of the 35 shipped songs, 19 pass, 16 flag and none fails. Six of the flags come from the instrument stage, and four of those six were already flagged by another check (Sit Down, Yellow, Three Little Birds, Don't Look Back in Anger).
- **Plausibility and timing thresholds are fitted.** They were chosen after seeing A Horse (5 long holds, 52 beats, 36%) and Zombie (2 deviants of 87), so they are not an independent test. A single stray deviant is deliberately not flagged. A threshold of 1 would flag three more shipped songs (Twist and Shout, Budapest, Take It Easy).

### Instrument stage: how it was chosen, and leave-one-out

Two approaches were tried on 25 October 2026. Both ran offline on the existing Demucs stems; scratch code, nothing downloaded.

| | A: signal features on the guitar stem (chosen) | B: YAMNet embeddings of the guitar stem |
|---|---|---|
| Measures | Technique: on-beat restrike. Instrument: Demucs guitar share. | How far the mean stem embedding sits from the catalogue's centroid (top 5 principal components) |
| Leave-one-out on the labels | Technique: 5 of 6 negatives caught, 3 of 36 positives flagged, with the cut refit in every fold. A nested LOO that re-selects 1 or 2 of 10 candidate features picked restrike_onbeat in 44 of 44 folds. | AUC 0.84: 6 of 8 negatives caught, 8 of 36 positives flagged. Misses Creep (23 positives score higher) and House. Supervised models on the embeddings were at chance under leave-one-type-out. |
| Explainable | Yes: one physical number per question | No: an atypicality score. It flags the picked Good Riddance and the strummed Ho Hey for the same reason (an exposed solo acoustic). |
| Runtime and drift | 15 s for 44 recordings, no model | 17 s for embeddings plus 4.5 min calibration. The centroid moves as songs are added. |

Kept from B: its finding that the plain guitar-share scalar separates the two instrument negatives as well as any embedding. Not kept: the embedding score itself.

Checks by the integrator:

- **Reproduction.** A's extraction was re-run on six recordings in a fresh directory and gave identical values. The repo's `strum_features.py` reproduces A's 44 values to within 5e-5.
- **Independent recomputation.** B's one-class score, recomputed from its cache with a separate implementation, gave the same ranking (values within 0.2).
- **Confounds.** `restrike_onbeat` falls with strumming density (Spearman −0.69 with attacks per beat among the strummed songs) and with YAMNet's electric-guitar tag on the stem (−0.41). With either regressed out on the positives, the AUC is still 0.93. So the feature is not just a density or timbre proxy, but dense and distorted strumming do pull it down.
- **Timelines.** The 20 s window values quoted in the table above come from these runs.

Leave-one-out with the rules as shipped:

- **Technique.** The cut is the highest training negative plus 0.01, refit in every fold. That catches 6 of 6 negatives (Creep by 0.007) and flags 4 of 36 positives: Sit Down, Lucky Man, Don't Look Back in Anger and Yellow.
  - Without the 0.01 margin: 5 of 6 negatives and 2 of 36 positives.
  - With 0.02: 6 of 6 and 7 of 36.
  - A's balanced-accuracy cut: 5 of 6 and 3 of 36.
- **Guitar-led.**
  - The fixed 0.33 cut catches 2 of 2 negatives and flags 2 of 36 positives. It was placed in the empty stretch 0.22 to 0.59 *after* seeing the data, so this is in-sample.
  - Refitting the cut in each fold, as the midpoint between the highest instrument negative and the lowest positive, catches only Riptide and flags Sweet Caroline. With two negatives the cut is not determined.
- **Both parts.** In-sample: 8 of 8 negatives (1 fail, 7 flags) and 6 of 36 positives flagged. No shipped song fails.
- **Selection bias.** Approach A tried about 60 feature variants on the same 6 technique negatives, and "on-beat attacks only" was found after looking at the labels. The nested LOO covers only the final 10 candidates. Expect a new picked or riff song to be caught less reliably than 6 of 6 suggests.
- **Ground truth.**
  - The 8 negatives come in 4 types: ukulele 1, harmonica 1, picked 3, riff 3.
  - The 36 positives are weak. The founder has played some of the 35 shipped songs and said the list is better, but none is individually confirmed.
  - The only confirmed strummed positive is A Horse with No Name, whose exclusion is about its chart.
  - One relabel moves every count above.

Per recording (25 October 2026), sorted by `restrike_onbeat`:

- *Guitar share* is the Demucs guitar / (guitar + piano + other). *YAMNet guitar* is the best guitar tag (top-5 frame fraction).
- *single_onbeat* is evidence only.
- *Hold missed bars* counts bars inside the chart's 24+ beat holds that fit another chord better.
- Riptide's restrike is shown but not used: its stem is bleed.

| Recording | Label | Guitar share | YAMNet guitar | restrike_onbeat ± SE | single_onbeat | Attacks / beat | Guitar-led / strummed | Merge signature | Hold missed bars | Instrument |
|---|---|---|---|---|---|---|---|---|---|---|
| Sweet Home Alabama | NEG picked riff | 1.00 | 0.92 | 0.583 ± 0.011 | 0.15 | 2.6 | pass / flag | - | - | **FLAG** |
| Sit Down | shipped (weak pos) | 0.98 | 0.44 | 0.592 ± 0.008 | 0.08 | 3.0 | pass / flag | - | 4/37 | **FLAG** |
| Seven Nation Army | NEG riff | 1.00 | 0.39 | 0.615 ± 0.017 | 0.09 | 0.9 | pass / flag | - | - | **FLAG** |
| Good Riddance (Time of Your Life) | NEG picked | 0.99 | 0.98 | 0.623 ± 0.010 | 0.07 | 2.7 | pass / flag | - | - | **FLAG** |
| The House Of The Rising Sun | NEG picked arpeggio | 0.90 | 0.93 | 0.625 ± 0.010 | 0.06 | 3.4 | pass / flag | - | - | **FLAG** |
| Come As You Are | NEG riff | 1.00 | 0.55 | 0.627 ± 0.013 | 0.09 | 1.9 | pass / flag | - | - | **FLAG** |
| Lucky Man | shipped (weak pos) | 0.83 | 0.61 | 0.627 ± 0.006 | 0.04 | 4.6 | pass / flag | - | - | **FLAG** |
| Creep | NEG picked verse | 1.00 | 0.58 | 0.629 ± 0.011 | 0.14 | 3.3 | pass / flag | - | - | **FLAG** |
| Don't Look Back in Anger | shipped (weak pos) | 1.00 | 0.59 | 0.631 ± 0.005 | 0.02 | 6.6 | pass / flag | - | - | **FLAG** |
| Yellow | shipped (weak pos) | 1.00 | 0.93 | 0.634 ± 0.006 | 0.07 | 3.1 | pass / flag | - | 0/13 | **FLAG** |
| Learning to Fly | shipped (weak pos) | 0.68 | 0.41 | 0.643 ± 0.008 | 0.03 | 2.2 | pass / pass | - | - | pass |
| Zombie | shipped (weak pos) | 1.00 | 0.64 | 0.644 ± 0.007 | 0.06 | 5.2 | pass / pass | - | - | pass |
| Breakfast at Tiffany's | shipped (weak pos) | 1.00 | 0.84 | 0.647 ± 0.008 | 0.03 | 2.6 | pass / pass | - | - | pass |
| Wonderwall | shipped (weak pos) | 0.98 | 0.56 | 0.650 ± 0.008 | 0.04 | 3.7 | pass / pass | - | - | pass |
| Boulevard of Broken Dreams | shipped (weak pos) | 0.99 | 0.69 | 0.655 ± 0.007 | 0.02 | 3.8 | pass / pass | - | - | pass |
| Wild Thing | shipped (weak pos) | 0.72 | 0.69 | 0.663 ± 0.011 | 0.01 | 1.7 | pass / pass | - | 4/17 | pass |
| Riptide | NEG ukulele-led | 0.04 | 0.06 | 0.664 ± 0.029 | 0.08 | 1.6 | fail / not measured | - | - | **FAIL** |
| Budapest | shipped (weak pos) | 1.00 | 0.67 | 0.666 ± 0.010 | 0.09 | 1.8 | pass / pass | - | 0/19 | pass |
| What's Up? | shipped (weak pos) | 0.95 | 0.76 | 0.667 ± 0.006 | 0.03 | 1.9 | pass / pass | - | - | pass |
| Free Fallin' | shipped (weak pos) | 0.93 | 0.30 | 0.667 ± 0.010 | 0.05 | 2.8 | pass / pass | - | - | pass |
| Knockin' on Heaven's Door | shipped (weak pos) | 1.00 | 0.73 | 0.681 ± 0.011 | 0.05 | 3.8 | pass / pass | - | - | pass |
| Torn | shipped (weak pos) | 0.99 | 0.43 | 0.684 ± 0.008 | 0.05 | 3.4 | pass / pass | - | 2/6 | pass |
| Love Me Do | NEG harmonica-led | 0.14 | 0.25 | 0.695 ± 0.012 | 0.08 | 1.4 | flag / pass | - | 4/12 | **FLAG** |
| Save Tonight | shipped (weak pos) | 1.00 | 0.83 | 0.695 ± 0.009 | 0.02 | 2.2 | pass / pass | - | - | pass |
| A Horse with No Name | POS strummed (chart problem) | 0.94 | 0.86 | 0.703 ± 0.010 | 0.04 | 1.8 | pass / pass | yes | 17/45 | pass |
| Have You Ever Seen the Rain | shipped (weak pos) | 0.94 | 0.71 | 0.704 ± 0.008 | 0.01 | 2.5 | pass / pass | - | 0/24 | pass |
| Island in the Sun | shipped (weak pos) | 1.00 | 0.90 | 0.715 ± 0.008 | 0.03 | 1.8 | pass / pass | - | - | pass |
| Take Me Home, Country Roads | shipped (weak pos) | 0.97 | 0.88 | 0.715 ± 0.009 | 0.05 | 3.5 | pass / pass | - | - | pass |
| I Want to Hold Your Hand | shipped (weak pos) | 0.91 | 0.53 | 0.716 ± 0.014 | 0.07 | 1.5 | pass / pass | - | - | pass |
| Brown Eyed Girl | shipped (weak pos) | 0.99 | 0.79 | 0.719 ± 0.011 | 0.05 | 1.3 | pass / pass | - | - | pass |
| Take It Easy | shipped (weak pos) | 0.95 | 0.79 | 0.721 ± 0.009 | 0.06 | 1.8 | pass / pass | - | 3/6 | pass |
| Wild World | shipped (weak pos) | 0.86 | 0.73 | 0.724 ± 0.016 | 0.07 | 2.6 | pass / pass | - | - | pass |
| Crazy Little Thing Called Love | shipped (weak pos) | 1.00 | 0.53 | 0.725 ± 0.013 | 0.13 | 1.2 | pass / pass | - | 0/6 | pass |
| Help! | shipped (weak pos) | 1.00 | 0.66 | 0.748 ± 0.013 | 0.07 | 2.6 | pass / pass | - | - | pass |
| Heart of Gold | shipped (weak pos) | 0.88 | 0.79 | 0.752 ± 0.011 | 0.02 | 2.5 | pass / pass | - | - | pass |
| Twist and Shout | shipped (weak pos) | 0.72 | 0.46 | 0.763 ± 0.024 | 0.04 | 0.9 | pass / pass | - | 0/6 | pass |
| Three Little Birds | shipped (weak pos) | 0.21 | 0.30 | 0.767 ± 0.021 | 0.05 | 2.6 | flag / pass | - | 2/6 | **FLAG** |
| Bad Moon Rising | shipped (weak pos) | 1.00 | 0.90 | 0.773 ± 0.011 | 0.01 | 2.6 | pass / pass | - | - | pass |
| I'm Yours | shipped (weak pos) | 0.61 | 0.37 | 0.782 ± 0.026 | 0.15 | 1.5 | pass / pass | - | - | pass |
| Wagon Wheel | shipped (weak pos) | 0.59 | 0.70 | 0.807 ± 0.008 | 0.04 | 1.3 | pass / pass | - | - | pass |
| Stuck in the Middle with You | shipped (weak pos) | 0.99 | 0.62 | 0.810 ± 0.010 | 0.02 | 1.5 | pass / pass | yes | 1/55 | pass |
| Sweet Caroline | shipped (weak pos) | 0.17 | 0.42 | 0.841 ± 0.012 | 0.06 | 1.0 | flag / pass | - | 4/6 | **FLAG** |
| Ho Hey | shipped (weak pos) | 0.98 | 0.84 | 0.855 ± 0.016 | 0.02 | 1.5 | pass / pass | yes | 1/22 | pass |
| I'm Gonna Be (500 Miles) | shipped (weak pos) | 0.99 | 0.92 | 0.918 ± 0.007 | 0.02 | 1.0 | pass / pass | - | 1/13 | pass |

Shipped songs the instrument stage flags (recommendations for the lead):

- **Sit Down (James).** Listen.
  - Restrike 0.592 is the second lowest of all 44, below five of the six labelled picked or riff songs.
  - It is low in most 20 s windows (0.55 to 0.66) and on the half-beats (0.63), so it is not a beat-phase error.
  - It is also flagged on plausibility and timing. This is the most credible real problem.
- **Lucky Man (The Verve).** Probable false alarm; keep unless a listen says otherwise.
  - Restrike 0.627.
  - It is dense strumming (4.6 attacks per beat) under strings, and single_onbeat 0.04 looks strummed.
- **Don't Look Back in Anger (Oasis).** Probable false alarm.
  - Restrike 0.631.
  - It has the densest strumming of all (6.6 attacks per beat), single_onbeat 0.02, and is already flagged on timing.
- **Yellow (Coldplay).** Probable false alarm.
  - Restrike 0.634.
  - It is distorted electric strumming (YAMNet electric-guitar tag 0.56 on the stem) and is already flagged on plausibility.
- **Sweet Caroline (Neil Diamond).** Listen.
  - Guitar share 0.17. The guitar that is there is strummed (restrike 0.841), but horns, strings and piano carry most of the harmonic bed.
  - Plausibly not guitar-led.
- **Three Little Birds (Bob Marley & The Wailers).** Listen.
  - Guitar share 0.22. The guitar stem is active in only 14% of frames: an off-beat skank under keys.
  - Plausibly not guitar-led.

What the instrument stage cannot detect:

- **A picked section inside a strummed song.** The score is a song average. Creep's picked verse scores strum-like.
- **Picking under heavy bleed.** Strings, organ or other instruments leaking into the Demucs guitar stem raise the score. Good Riddance's string section and House's organ do this.
- **Dense or distorted strumming versus picking.** 16th-note or distorted strumming lowers the score into the picked range (Don't Look Back in Anger, Lucky Man, Yellow, Zombie, Wonderwall). That is why technique only flags.
- **A wrong beat grid.** On-beat attacks come from the pack grid. A grid half a beat out reads up-strums as down-strums, which may explain Sweet Home Alabama and Learning to Fly.
- **An instrument Demucs files as guitar.** A ukulele or mandolin that leaks into the guitar stem passes the share, and YAMNet's Ukulele tag is weak (Riptide 0.11).
- **The parts YAMNet corroborates.** The thresholds 0.25, 0.30 and 0.15 were never fitted, so they only corroborate the share. No labelled song depends on them except Riptide's "no guitar".
- **Strum pattern, rhythm or difficulty.** The stage says nothing about these.

### Cross-check of the exporter's auto-timing

Measured with this tool's own offsets on the raw charts. Across the 19 songs the exporter changed, none of its moves made a change worse. Eight of its whole-beat moves fix a change that this tool also finds about a beat off in the raw chart (Zombie 2, Wagon Wheel 2, and one each in Don't Look Back in Anger, Lucky Man, Heart of Gold and Torn); the whole-beat move in I'm Yours is in a group too small to measure. The rest are snaps of at most about 0.6 beat. Free Fallin' has 9 and Learning to Fly 15 such snaps, none over about 0.4 beat, on changes that were already within the grid's noise of their group, so they are harmless but unneeded.

## Limitations

- Everything is relative to automatic charts and estimated grids. A song can pass every check and still be wrong.
- The chord check is only as good as the expected lists. Several are medium or low confidence and none is a timed transcription.
- The consistency test needs repetition. Sequences played once, and songs with few repeats (Riptide, Breakfast at Tiffany's, I'm Yours, Crazy Little Thing Called Love), get `few`.
- Wonderwall's meter is assumed (the beat count varies), so its bar positions are indicative only; it cannot hard-fail on timing.
- The report was moved out of the deployed `strumalong/` root on 25 October; it now lives at `docs/STRUMALONG_CATALOGUE_CHECKS.json`.
- The report depends on the exporter's state when it was generated. The song index hash is recorded in `generated_from`.
- The instrument stage and the hold check depend on gitignored files computed from the audio. On a checkout without them the instrument check is `not run` and the merge signature only flags. Re-run `stems_6s.py`, `yamnet_tags.py`, `strum_features.py` and `hold_homogeneity.py` after a pack's audio or chart changes; stale audio hashes flag, and stale holds are treated as missing evidence.
- The instrument thresholds were calibrated on 44 recordings with 8 labelled negatives and weak positives (see Validation). Treat an instrument flag as a request to listen, not as a finding.
