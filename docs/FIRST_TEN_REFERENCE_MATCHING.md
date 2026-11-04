# First-ten recording/reference matching

Checked 13 October 2026 in the canonical `Documents/music-os` checkout. The bounded check completed: all five cached recording identities pass, and all nine official annotation files match the earlier SHA-256 pins. **None of the five pairs establishes the corpus master and time origin, so no timing or chord accuracy is scored.** This is a data-pairing gap; David does not need to transcribe anything.

| Song | Reference audio named by the source | Cached project edition | Result |
| --- | --- | --- | --- |
| Love Me Do | *Please Please Me*, CDP 7 46435 2 | *Please Please Me*, 2009 remaster | Album/take metadata is useful; master/origin unverified |
| Twist And Shout | *Please Please Me*, CDP 7 46435 2 | *Please Please Me*, 2009 remaster | Named editions differ; master/origin unverified |
| Brown Eyed Girl | *Bang Masters*, Epic 1991 CD | *Blowin’ Your Mind!* | Compilation/album may reuse a performance; no independent timing mapping |
| Come As You Are | *Nevermind*, CD edition unspecified | *Nevermind* | Album matches, but no master checksum or CD-origin proof |
| The House Of The Rising Sun | *The Best of the Animals*, ABKCO 1966 CD | *Most of the Animals*, Parlophone UK | Animals identity is preserved; compilation/master/origin unverified |

The project editions come from the saved recording-selection and preparation metadata. They are not newly verified release descriptions. One fresh YouTube page returned only its title; the other four requests failed or were rate-limited, so the check stopped without repeated attempts or new media imports.

## What the sources establish

The [Isophonics reference description](https://isophonics.net/content/reference-annotations.html) names the CD, defines chord/beat formats and distinguishes repeatedly checked Beatles chords from moderate-confidence beat annotations. Its [Beatles index](https://isophonics.net/content/reference-annotations-beatles.html) identifies version 1.2. Two newly downloaded complete RDF documents point to local WAV filenames and timeline nodes. They contain no asserted audio checksum, fingerprint, sample rate or transform to our files; hexadecimal node suffixes are not audio hashes. Full Beatles annotations remain in ignored local storage because the inspected pages/documents did not state their licence.

The [Rock Corpus source list](https://rockcorpus.midside.com/timing_data/audio_sources.txt) names the three CD releases. Its [timing documentation](https://rockcorpus.midside.com/timing_data.html) makes time zero relative to each original CD file, including initial silence. Bar locations were tapped and refined; within-bar chord times use interpolation. The [official portal](https://rockcorpus.midside.com/) licenses posted corpus data/scripts under CC BY 4.0 with attribution to Trevor de Clercq and David Temperley. This is not a licence to external commercial recordings.

All five original AAC files and player WAVs match their preparation hashes. The AAC streams start at zero, and the importer decodes/downmixes/resamples without an explicit seek, trim or padding operation. The player uses zero within that prepared file. These facts establish internal pairing, not a correspondence to corpus CD zero. Similar duration, title/artist, annotation endpoints and model agreement cannot supply that correspondence.

## Next automatic work

1. Build a compatibility manifest that keeps unverified recording/reference pairs out of scoring denominators and records reference-origin/transform evidence explicitly.
2. Seek a permitted, checksum-paired corpus audio source or a locally identified rip; prioritize *Come As You Are*, then *House*. More release metadata can refine candidates but cannot prove time zero.
3. If canonical audio is available, freeze audio-only offset/drift estimation using separated windows and check the mapping on reserved windows before scoring. Pin both inputs and the transform. A verified remaster transfer is a mapped same-performance comparison, not an identical-master claim.
4. If no canonical pair can be acquired in a bounded check, continue algorithm selection on already paired publisher audio/annotations. Retain first-ten files for normal practice/usefulness feedback, with their unreviewed status.

No founder transcription, algorithm retuning, gold-selected offset/scaling or player changes were introduced. Compact source hashes, acquisition outcomes, waveform/codec checks and per-song evidence are in [the JSON report](FIRST_TEN_REFERENCE_MATCHING.json). Full source files are local in `experiments/candidate-assets/first-ten-reference-matching-20261013/`.
