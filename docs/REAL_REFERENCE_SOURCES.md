# Independent references for the three imported recordings

Checked 10 October 2026. **No independently annotated timing reference has yet been verified against any of the three imported YouTube WAVs.** A usable, independently created candidate exists for the Animals recording, but its recording identity and time origin require listening checks before it can become evaluation gold.

## The Animals: a practical source candidate

The [de Clercq–Temperley Rock Corpus](https://rockcorpus.midside.com/) contains *House of the Rising Sun*. The authors made [two harmony analyses independently by ear](https://rockcorpus.midside.com/harmonic_analyses.html), without consulting each other or printed charts. They resolved meter/barline differences, while retaining substantive harmony disagreements. Treat the two analyses as alternate human references, not two unanimous votes for every chord.

Its [timing data](https://rockcorpus.midside.com/timing_data.html) contains human barline annotations: an initial tapping pass followed by listening/waveform refinement in Sonic Visualiser. These are reference barlines on the corpus audio. Chord changes inside a bar are interpolated by the supplied [conversion program](https://rockcorpus.midside.com/programs.html), so they should not all be described as separately marked physical chord onsets.

The project releases its annotations and programs under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), allowing adaptation and commercial use with attribution. This annotation licence does not establish permission for the associated commercial audio. Cite Trevor de Clercq and David Temperley (2011), [“A corpus analysis of rock harmony,” *Popular Music* 30(1), 47–70](https://rockcorpus.midside.com/2011_paper/declercq_temperley_2011.pdf), and identify any conversions or corrections.

Small source files are cached locally under the ignored `experiments/candidate-assets/rock-corpus/` directory. `provenance.json` records retrieval time, source URLs, size and SHA-256 for each unmodified file.

| Cached file | Primary source | Role |
|---|---|---|
| `house_of_the_rising_sun_dt.har` | [David Temperley analysis](https://rockcorpus.midside.com/harmonic_analyses/rs200_harmony/house_of_the_rising_sun_dt.har) | Ordered harmony and sections/repeats |
| `house_of_the_rising_sun_tdc.har` | [Trevor de Clercq analysis](https://rockcorpus.midside.com/harmonic_analyses/rs200_harmony/house_of_the_rising_sun_tdc.har) | Alternate ordered harmony and sections/repeats |
| `house_of_the_rising_sun.tim` | [Human barline times](https://rockcorpus.midside.com/timing_data/timing_data/house_of_the_rising_sun.tim) | 172 strictly increasing entries, bars 0–171 |
| `audio_sources.txt` | [Corpus audio source list](https://rockcorpus.midside.com/timing_data/audio_sources.txt) | The Animals, *The Best of the Animals*, ABKCO 1966, compact disc source |

The source intro is eight bars: Am–C–D–F–Am–E(7)–Am–E(7), in 6/8. Temperley marks E7 in the intro; de Clercq marks E. Their full structures provide a finite sequence through seven verse passages, including an instrumental verse, and an outro alternating Am/Dm. These are hypotheses about the corpus recording until checked against the imported video.

The corpus barline file starts at 0.313265306 seconds and ends at 262.942811791 seconds. The imported video `4-43lLKaqBQ` produces a **248.546394558-second** WAV, SHA-256 `7724e708da432a588e2faeb3aa025b7e37128c3a440b39077e0370e472c55035`. The reference endpoint exceeds the WAV duration by **14.396417233 seconds**. This discrepancy rules out directly scoring the unmodified reference on this WAV. It does not identify whether the cause is an edit, different performance speed, source silence, or another version.

Do not fit a timestamp scale from these two endpoints, infer an offset from detector outputs, or call a successful forced alignment proof of matching versions. Check the intro, verse/solo order and ending separately. A verified partial match may justify a reference only over its explicitly checked interval; it does not validate the whole song.

## Creep and Wonderwall

Neither title appears in the [Rock Corpus RS200 index](https://rockcorpus.midside.com/overview/rs200.txt). The [Isophonics catalogue](https://isophonics.net/datasets) provides useful other-artist references but no candidate for these imported recordings was found in the collections checked. The [McGill Billboard collection](https://ddmal.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)/) is another substantial source: CC0 harmony annotations, with human phrase-start times and interpolated internal chord boundaries. Its [CoCoPops sample index](https://raw.githubusercontent.com/Computational-Cognitive-Musicology-Lab/CoCoPops/main/Billboard/Billboard_Sample.tsv) has neither Creep nor Wonderwall, and its Animals entry is *San Franciscan Nights*, not *House of the Rising Sun*.

[Bello and Pickens (ISMIR 2005)](https://ismir2005.ismir.net/proceedings/1038.pdf) show a manually annotated Wonderwall structure in a figure. The paper is a research lead; the checked material supplies neither a downloadable chord-timing annotation nor proof of the exact audio version used. Do not digitise that figure and present it as timing gold for video `bx1Bh8ZvH84`.

Keep the existing [untimed chart candidates](../experiments/fixtures/untimed-charts/) and authored teacher references as harmony/arrangement evidence. They supply no independently checked timestamps. No exact timing dataset was located in this bounded search; that is a statement about the sources inspected, not proof that none exists.

## Bounded listening check for a first review pack

Prepare one short **review window**, initially the first 20–30 seconds of each cached WAV. These ranges are selection conveniences, not claims that an intro ends there. Preserve the parent audio hash, integer source sample range and clip hash. The founder can hear these without playing guitar.

1. Present the audio and candidate ordered chords with detector/aligner timings hidden. Mark the audible chord changes and uncertain labels in a first pass. Confirm how many chord changes are actually contained in the window before deciding on a finite sequence.
2. In a second pass, replay around each change and refine the mark. Define a boundary as the first audible attack belonging to the new harmony; record an uncertainty interval where arpeggios, overlap or anticipations make that unclear. Keep barlines and harmonic changes separate.
3. For House, compare the heard intro/order with both human source analyses. If the named corpus CD is acquired later, verify identifiable events near the beginning, middle and end before transferring its reference. Keep any checked time-origin transform and its evidence separate from model inference.
4. Save the human reference with reviewer identity, review date, audio/clip hashes, coverage, label convention, uncertainty and acceptance state. A second reviewer or repeat blind pass is needed before calling the marks independently checked. Never use agreement among the three audio detectors as gold.
5. Compare the frozen detector/aligner outputs only after saving the reference. Use these first familiar clips for development diagnostics; select fresh clips/recordings for holdout evaluation before tuning.

A practical first session is **three windows, roughly 60–90 seconds of audio in total**, with an explicit list of changes to check. Allow about 20–40 minutes for listening, mark refinement and resolving ambiguities; this is an effort estimate, not an algorithm accuracy claim. Expand to the planned ten excerpts only after the first packet establishes the reference process and reveals its actual review cost.
