# Song Chords reference: provenance and prototype use

Received from the founder in this chat on 29 October 2026. The supplied text refers to pages 46–55, but no book title, author or edition was supplied. `SONG_CHORDS_USER_REFERENCE.md` preserves the complete pasted text unchanged, including all 15 rows and 12 chord columns. It is source material, not independently verified song analysis.

## How the prototype uses it

The Foundation helper on `codex/band-member-prototype` uses all major-key rows, including enharmonic and double-flat spellings. It groups the columns into Basic, Rock / blues and More colour; uses conventional lowercase ii, iii, vi and iv for minor qualities; offers original illustrative progressions; and allows one chord per bar with a synthesized triad preview. It does not claim those progressions reproduce the named songs.

Changing the section key transposes its guide by column/degree. It does not transpose recorded audio. Chord suggestions, minor-mode teaching and changes of key are distinct: this revision implements major-key guides, while retaining all minor-mode and other material in the saved source for later work.

## Interpretation notes (original text remains unchanged)

- The six basic chords are a starter subset, not all diatonic triads: major also includes diminished vii°.
- A-minor's diatonic supertonic is B diminished, not B♭ major. B♭ is an additional borrowed ♭II colour; it should not be presented as a natural-minor diatonic chord.
- The supplied `I–IV–♭VII (C–B♭–F)` line contains an internal ordering mismatch: C–B♭–F corresponds to I–♭VII–IV. This is a notation correction, not verification of the named recording.
- Major II and III can function as secondary dominants (V/V and V/vi) in context; being major alone does not establish that function. Minor iv is modal borrowing, not a secondary dominant.
- Descriptions such as “tender” or “harder” are listening suggestions rather than guaranteed effects. Chord extensions and melody notes need to be considered together; the helper does not teach that any extension is always interchangeable.
- Named-song examples and the unnamed book's page references have not been independently checked.

## Theory sources checked

- [University of Puget Sound, Diatonic Chords in Minor](https://musictheory.pugetsound.edu/mt21c/DiatonicChordsInMinor.html): minor-scale variants and B diminished in A minor.
- [Open Music Theory, Modal mixture](https://github.com/openmusictheory/openmusictheory.github.io/blob/master/modalMixture.md): borrowing from parallel keys and Roman-numeral quality/accidental conventions.
- [University of Puget Sound, Mode Mixture](https://musictheory.pugetsound.edu/mt21c/ModeMixtureSection.html): parallel-minor borrowing in a major-key passage.
- [University of Puget Sound, Tonicization](https://musictheory.pugetsound.edu/mt21c/Tonicization.html): applied dominants and the distinction between chord root and function.
