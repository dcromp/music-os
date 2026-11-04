# Ten-recording timing, rhythm and setup checkpoint

Checked 16 October 2026. The automated diagnostic pass now covers all ten exact
recordings. It completes the first-four follow-up and remaining-six screening;
it does not accept physical chord times, recorded guitar strumming or whole
arrangements. The [compact results](CATALOGUE_TIMING_RHYTHM_CHECK.json) pin full
local reports, exact audio identities, policies and denominators.

| Recording | Concrete finding | Next recording-specific check |
|---|---|---|
| Wild Thing | Long native A regions have repeated full-mix transients and low-energy centers near 44.426 and 109.343 s. | Locate the contrasting G/A figure and paired guitar contacts; a harmonic hold need not mean continuous sound. |
| Love Me Do | Long C regions have recurring low-energy centers near 27.167, 48.524, 82.930 and 123.385 s; common D spans are saved as contrast search windows. | Check deliberate guitar damp versus skipped/ringing contact and swing. Full-mix energy minima are search landmarks, not accepted mute times. |
| Knockin' on Heaven's Door | Am/C hold inventories retain repeated full-mix attacks; the extra BTC Am fragment near 82.508–83.065 s remains unresolved. | Check alternating responses and existing provisional G edits without treating filtered runs as repeat counts. |
| Twist and Shout | Native A holds contain 31/24 BTC versus 31/26 CREMA transient candidates; the second ending still differs by 0.899 s. | Check the actual ending and guitar contacts; these are not stroke counts. Keep all-down eighth practice separate from the recorded pattern. |
| Brown Eyed Girl | G/C/D/Em at shift zero ranks first globally and in every active window in both acoustic methods. | Check Em, ringing ties and actual contacts; another teaching arrangement's tempo is not the selected recording's reference. |
| Seven Nation Army | No triad palette imposed. NNLS activity favours E/B/C, while simple spectral activity favours E/C#/F. | Check riff notes/articulation and explicitly choose a standard-tuning adaptation or original Open A/slide exercise. |
| Come As You Are | No triad palette imposed; native sounding labels and pitch-class activity remain descriptive. | Check the riff and D-standard setup. With no capo, conventional shape roots are two semitones above sounding roots. |
| Creep | G/B/C/Cm at shift zero ranks first globally in both methods; small local spectral alternatives remain visible. | Preserve B major/C minor, check verse picking and fuller sections, and retain local ambiguity. |
| House of the Rising Sun | Am/C/D/F/E/Dm at shift zero ranks first in every active acoustic window; common late Dm holds are saved. | Check the 6/8 pulse convention, picked/raked contacts and Am/Dm outro changes before numbering bars. |
| Wonderwall | Capo-2 shapes rank first at the expected +2 sounding shift globally and in all fixed samples in both methods. One tail NNLS window differs. | Preserve familiar shared-finger grips; check exact sections, contacts and local meter. The inspected teacher text does not establish 4/4-to-2/4 changes. |

The remaining-six [source review](../catalogue/remaining-six-teaching-review.json)
records ten primary teacher URLs checked on 16 October. It distinguishes
teacher adaptations from the selected recording. No full chart, lyrics, tabs
or pattern transcription was copied. All twelve pitch shifts remain visible
for the four harmonic cases; riff recordings have no imposed shift winner.
The [six-song pitch summary](REMAINING_SIX_PITCH_CHECK.json) retains local
ambiguities and descriptive model membership, which is not an accuracy score.

## Timing and rhythm results

The all-ten native inventory has **1,246 BTC changes, 989 CREMA changes and 796
compatible directed pairs**. It retains 745 candidate replay windows, selects
at most twelve per recording (120 total), and preserves forty fixed samples.
These are review workload figures. Between-model agreement cannot expose
shared errors; the earlier synthetic shared-clock control remains applicable.

The audio pass measures centered 512-sample RMS and log spectral flux at a
128-sample hop (about 5.8 ms), without shifting chart events. Every native
boundary, selected timing window and source-guided harmonic target gets
descriptive transient/energy context. Distances to a nearby transient do not
verify a harmonic change: drums, vocals and other instruments can cause it.
Cached guided pulses retain their existing identities and unverified phase.

Six procedural attack controls and two energy controls ran before interpreting
the recordings. The fixed attack detector is **not suitable for automatic
strumming transcription**: quarter attacks match 8/8 but produce 20 extras
(F1 0.444); eighth attacks score 0.727, swung pairs 0.667, and soft attacks
0.056 at 40 ms tolerance. Same-harmony beating produces false transients. The
sharp-quarter matched clock error is at most 3.1 ms, which does not excuse
the extras or establish real-recording precision. A +100 ms clock control
fails the passing tolerance. No thresholds were retuned to these outcomes.

In the energy controls, a chord allowed to ring across a skipped contact has
after/before RMS 0.986, versus 0.000 for an explicit three-millisecond damp.
This validates the distinction in the synthesized example. Full-band energy
cannot identify a guitar mute uniquely, so the real-song low-energy points
remain search cues. Stroke direction, swing ratio, guitar-only attack count,
formal section extent and downbeats are not inferred.

## Saved content and verification

Ten separate revision-checked developer drafts now have source/setup/rhythm
notes and **19 provisional search or fixed-coverage replay windows**. The two
earlier Dylan label proposals remain at native BTC bounds. The [versioned
editorial backup](../catalogue/first-ten-curation-proposals-v1.json) preserves
these project-authored proposals. Batch note entry created no review timer
sessions; human correction effort remains unmeasured. Raw charts and the
ordinary learner's charts, practice progress and feedback identity are intact.

The final suite discovers **436 Python tests: 416 pass and 20 optional checks
skip**. This continuation adds 30 focused regressions covering exact inputs,
setup-aware scoring, riff handling, clock/energy controls, stale chart targets,
private-file aliases and concurrent-input aborts. All 39 frozen workflow pins
pass. All 45 reviewer and 48 learner assets match served bytes. The existing
124 JavaScript checks passed earlier on 16 October; no JavaScript changed.
Independent audits reproduced native counts and remaining-six acoustic scores.

The final runs took 0.198 s for native changes, 8.757 s for the six-song acoustic
follow-up and 3.076 s for all-ten audio diagnostics. These are compute runtimes,
not musical review effort. Full reports, evidence and media remain ignored on
this Mac. No neural recognizer was rerun and no learner arrangement promoted.

## Reproduce on this Mac

From the checkout, with the existing ignored caches/assets present, choose
unused output folders. Existing outputs are refused.

```sh
.venv-analysis/bin/python experiments/analysis/catalogue_change_check.py \
  --output experiments/generated/catalogue-change-replay
.venv-analysis/bin/python experiments/analysis/catalogue_remaining_pitch_check.py \
  --output experiments/generated/catalogue-pitch-replay
.venv-analysis/bin/python experiments/analysis/catalogue_audio_rhythm_check.py \
  --spec experiments/fixtures/catalogue-audio-rhythm-v1.json \
  --output experiments/generated/catalogue-rhythm-replay
```

The rhythm fixture pins the original all-ten native report. Use its default
timing-report input when replaying this exact check; a new timing report needs
a new explicitly pinned specification. Local practice remains on port 8070,
developer drafts on 8073. Restart commands are in the README.
