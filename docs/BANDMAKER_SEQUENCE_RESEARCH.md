# Bandmaker sequence research

Ticket: [#99](https://github.com/dcromp/music-os/issues/99). Research only; no app code changed.
Checked on 10 November 2026 against `feelRecipes` and `POPULAR` in `strumalong/bandmaker.js` on `main`.

## Short answer

- The evidence for a single most-common four-chord loop is solid: **I–V–vi–IV (H2)**. Hooktheory's data ranks it first, and the root-frequency findings of the rock corpus studies agree with it.
- **H1 I–IV–V–I** and **H3 I–vi–IV–V** are reasonably supported. Keep the badge.
- **S2, S3, R1 and R5 are not supported by any count I could verify.** S3 and R1 are plausible; S2 and R5 look like teaching choices rather than popular ones.
- No corpus I could read gives clean counts for minor-key or power-chord sequences. Hooktheory's Trends tool is interactive and could not be queried from here. Treat minor and power badges as judgements until someone runs the Trends queries listed at the end.
- Suggested design: split the badge into **Popular** (counted in a corpus) and **Classic** (standard in theory or rock practice, no count). That lets the list stay honest.

## What the sources can and cannot say

| Source | What it is | What it supports | Limits |
|---|---|---|---|
| Temperley & de Clercq, [Statistical analysis of harmony and melody in rock music](https://www.midside.com/publications/temperley_declercq_2013.pdf), *Journal of New Music Research* 42(3), 2013. Corpus: [rockcorpus.midside.com](https://rockcorpus.midside.com/) | Hand-analysed Roman numerals for 200 songs from Rolling Stone's "500 Greatest Songs" list | "IV is the most common root after I, followed by V, then ♭VII, then VI." IV is the most common chord both just before and just after I. Rock shows a tendency toward temporal symmetry, so IV→V is not far more common than V→IV as in classical music. Rock minor-key profiles favour the lowered seventh, unlike classical minor. | Reports root and chord frequencies, not four-chord sequence counts. Biased toward songs critics ranked highly, not toward the most played. I read the full text (extracted from the PDF). |
| de Clercq & Temperley, [A corpus analysis of rock harmony](https://www.cambridge.org/core/journals/popular-music/article/corpus-analysis-of-rock-harmony/C5210A8EC985DDF170B53124F4464DA4), *Popular Music* 30(1), 2011 | The 100-song predecessor | Abstract only (paywalled): IV is the most common chord after I and especially common before the tonic. | I did not read the full text. |
| Hooktheory, [I analyzed the chords of 1300 popular songs](https://www.hooktheory.com/blog/i-analyzed-the-chords-of-1300-popular-songs-for-patterns-this-is-what-i-found/), [part 2](https://www.hooktheory.com/blog/music-theory-analysis-1300-songs-for-songwriting-part2/index.html) | Hand-analysed 1,300 songs, mainly from the Billboard 100, transposed to C | I–V–vi–IV is "the most popular four-chord progression that shows up in the database." IV→I appears as often as V→I. F (IV) and G (V) appear in more progressions than C (I). | The posts give the ranking but no percentages for progressions; the figures are in chart images. Undated, around 2013. |
| Hooktheory, [Common chord progressions](https://www.hooktheory.com/theorytab/common-chord-progressions) | A curated list on the TheoryTab database ("Search 82,484 songs") with tab counts per sequence | Counts below. The numerals come from the page's own `node=` links. | A hand-picked list, not a ranked census; "tabs" are user-made charts of a song or section, not songs. The counts are not stated to be exact-sequence or any-position. |
| Hooktheory, [Minor chord progressions](https://www.hooktheory.com/blog/minor-chord-progressions/) | Blog on minor-key trends in its database | Chord shares in minor progressions: i 14%, ♭VI 9%, ♭VII 9%, ♭III 6%, iv 5%, v 3%. V is the most common borrowed chord. iv rarely starts a sequence. Lists sequences with song examples. | Does not say what the percentages divide by. A [Hooktheory forum thread](https://forum.hooktheory.com/t/computing-chord-statistics-for-hooktheory-trends/112) says Trends converts minor songs to the relative major first, so minor counts need care. |
| Dong & Lai, [Music Chord Progression Analysis](https://hermandong.com/pdf/chord_progression_analysis_report.pdf) (student report, UCSD ECE 225) | N-gram counts on 11,380 Hooktheory songs (the open lead-sheet dataset) | Most common four-grams: C–G–Am–F, C–F–G–C, G–C–F–G, Cm–A♭–B♭–Cm and their cyclic permutations. | A course project, not peer reviewed; no counts given in text (figures only). Useful as a cross-check of H1 and H2, not as a primary source. |
| Everett, [Making sense of rock's tonal systems](https://www.mtosmt.org/issues/mto.04.10.4/mto.04.10.4.w_everett.php), *Music Theory Online* 10(4), 2004 | Music-theory taxonomy of rock harmony with song examples | ♭VII–IV–I as the "double-plagal" cadence (¶11). A triad-doubled minor-pentatonic system built from I, ♭III, IV, V, ♭VII, where chords are "not functionally related" (¶19–20). ♭VI–♭VII–I as an Aeolian cadence (¶12). | A taxonomy with examples, not a frequency count. |
| McGill Billboard corpus, Burgoyne (2011), [thesis](https://escholarship.mcgill.ca/downloads/000004056) | 1,000+ chord-annotated Billboard Hot 100 songs | Cited because it is the largest hand-annotated corpus. | I could not retrieve the text, so I cite **no** figure from it. A reader with the thesis should check the chord-transition chapter. |
| Biamonte, "Triadic modal and pentatonic patterns in rock music", *Music Theory Spectrum* 32(2), 2010 | Theory article | Reported by secondary sources to treat ♭VII–IV–I as double-plagal and ♭VI–♭VII–I as Aeolian. | Not read; not relied on. |

### Hooktheory sequence counts (from the Common chord progressions page)

Keys are Roman numerals relative to the major key, as encoded in the page's links.

| Sequence | Hooktheory label | Tabs |
|---|---|---|
| I–V–vi–IV | "The most popular progression" | 1,385 |
| I–vi–IV–V | "Those magic changes" | 542 |
| vi–V–IV–V | "Effective in all genres" | 377 |
| I–V–IV–V | "Timeless" | 376 |
| I–IV–vi–V | "Gaining popularity" | 350 |
| I–V–vi–iii | "Pachelbel's progression" | 200 |
| ♭VII–IV–I | "A mixolydian cadence" | 109 |

Hooktheory's own labels are marketing, not evidence. Only the counts and the ranking claim in the blog carry weight.

## Q1. What is most common?

1. **I–V–vi–IV** (and its rotations vi–IV–I–V, IV–I–V–vi, V–vi–IV–I). Top of Hooktheory's blog ranking and list, and the top four-gram in the cross-check report.
2. **I–IV–V–I** family (with rotations such as I–V–IV–I). Second in the cross-check report. Consistent with the corpus finding that IV and V are the most common roots after I, and that IV→I is as common as V→I.
3. **I–vi–IV–V**, the 1950s pattern, at 542 Hooktheory tabs.
4. Loops with ♭VII, ♭VI and ♭III in rock. ♭VII is the third most common root in the Rolling Stone corpus. The pentatonic-system chords (I, ♭III, IV, V, ♭VII) are standard rock practice per Everett.

For minor keys the best evidence is chord-level: ♭VI and ♭VII are each about 9% of chords, ahead of ♭III and iv. Sequence-level counts for minor keys were not retrievable.

## Q2. Are the current POPULAR marks justified?

| Id | Sequence | Verdict | Why |
|---|---|---|---|
| H1 | I–IV–V–I | **Keep** | IV and V are the next most common roots after I; IV→I is as common as V→I. Second four-gram family in the cross-check. Sourcing is secondary. |
| H2 | I–V–vi–IV | **Keep** | Strongest evidence: Hooktheory ranks it first (1,385 tabs; blog says most popular four-chord progression). |
| H3 | I–vi–IV–V | **Keep** | 542 Hooktheory tabs, second in that list. No scholarly count found. |
| S2 | i–iv–V7–i | **Remove the badge; keep the sequence** | A textbook minor cadence, but nothing I found shows it is popular. Rock minor favours ♭VII over the raised seventh, and the v/V chord is rare in minor-key chord shares (v 3%). Reasonable as "pull back home", labelled Classic. |
| S3 | i–♭VI–♭III–♭VII | **Provisional** | Built from the three most common non-tonic minor chords (♭VI, ♭VII, ♭III) but I have no count for the sequence. Keep the badge only if the Trends query below confirms it. |
| R1 | 1–♭3–4–1 | **Remove the badge; label Classic** | Roots I, ♭III, IV are the core of the pentatonic system (Everett ¶19–20), and the book gives I–♭III–IV as hard-rock formula. No count for this order. |
| R5 | 1–4–5–4 | **Remove the badge** | I found nothing on I–IV–V–IV specifically. The closest counted sequence is I–V–IV–V (376 tabs). |

**To add:** none of the existing unbadged sequences have a count that beats the above. H9 (I–♭VII–IV–I) and H10 (I–IV–V–♭VII) are rock-standard per Everett and the book but are Classic, not counted.

## Q3. Drafts

| Id | Sequence | Verdict | Why |
|---|---|---|---|
| S5 | i–♭VII–♭VI–♭VII | **Keep, no badge** | A legitimate Aeolian vamp. The chords are the second and third most common non-tonic minor chords. No source for this exact order, so describe it as a vamp, not a named progression. |
| S6 | i–♭VII–♭VI–V7 | **Keep; rename** | This is the Andalusian descent i–♭VII–♭VI–V. [Wikipedia](https://en.wikipedia.org/wiki/Andalusian_cadence) lists it with song examples ("Hit the Road Jack" is the example it says has this as its primary structure). Secondary source; check its cited books before putting a song name in the app. Badge: Classic. |
| S7 | i–iv–♭VII–♭III | **Keep; fix the description** | The roots fall by fifths (Em–Am–D–G), so "climbs toward ♭III" in the `why` text is wrong. It is a descending-fifths chain. No popularity evidence; no badge. |
| R5 | 1–4–5–4 | **Keep as a drill, no badge** | See Q2. |
| R6 | 1–♭7–♭6–♭7 | **Drop** | Same roots as S5 and the same idea as R2 (1–♭6–♭7–1). Redundant in the heavy list. |
| R7 | 1–5–♭6–4 | **Drop and replace with 1–5–6–4** | I found no source for mixing V and ♭VI in this order. The power-chord version of the most common loop (I–V–vi–IV) is better evidenced. Needs a 6th-degree power chord (C♯5 in E), which the current power array lacks. |

## Q4. Proposed additions

Numerals are in the book's vocabulary; every chord comes from its major-key table, its minor-key rules or its flat-degree columns (see `docs/reference/SONG_CHORDS_USER_REFERENCE.md`). Examples in G (major) and E (minor and power) match the current recipes. No song names are given except where a cited source supplies them.

### Major (key of G)

| Numerals | Chords | Plain-English name | Source |
|---|---|---|---|
| vi–IV–I–V | Em C G D | Same loop, different start | Rotation of H2; Dong & Lai count cyclic permutations together. The book says the six primary chords work in any order. |
| I–IV–vi–V | G C Em D | Lift to the fifth | Hooktheory list, 350 tabs ("Gaining popularity"). |
| I–V–IV–V | G D C D | Rock-and-roll rocker | Hooktheory list, 376 tabs ("Timeless"). Corpus finding that IV and V are the two most common roots. |
| I–V–vi–iii | G D Em Bm | Falling-thirds descent | Hooktheory list, 200 tabs (its label "Pachelbel's progression"). Lowest count; add last. |

### Minor (key of E)

| Numerals | Chords | Plain-English name | Source |
|---|---|---|---|
| i–♭VI–♭VII–i | Em C D Em | Climb home | Hooktheory minor blog (♭VI→♭VII→i, with song examples there); Everett ¶12 (♭VI–♭VII–I Aeolian cadence); the book's ♭VI–♭VII–I phrase ending. |
| i–v–iv–♭VII | Em Bm Am D | Step down by fifths | Hooktheory minor blog (i→v→iv→VII, song example there). Uses the book's natural-minor chords. |
| i–♭VI–iv–V | Em C Am B | Sad turn, then dominant | Hooktheory minor blog calls it the more common form of i→♭VI→iv→V. Needs a major V, which the book allows (harmonic minor). |
| ♭VI–i–♭VII–♭III | C Em D G | Start on the sixth | Hooktheory minor blog, with song example there. Starts off tonic, so it suits an "advanced" slot. |

Not proposed as new: i–♭VII–♭VI–V (already S6).

### Power (key of E)

| Roots | Chords | Plain-English name | Source |
|---|---|---|---|
| 1–5–6–4 | E5 B5 C♯5 A5 | The big pop loop, power-chord style | I–V–vi–IV roots (see Q2 H2). The corpus counts are by root, so they transfer to power chords. Needs C♯5. |
| 1–♭7–4–1 | E5 D5 A5 E5 | Double-plagal rock | Everett ¶11 (♭VII–IV–I); the book's I–♭VII–IV. Everett's song examples there include "The Last Time" and "I Can't Explain". |
| 1–♭3–4–5 | E5 G5 A5 B5 | Rock pentatonic climb | Everett ¶19–20; the book's hard-rock formula I–♭III–IV–V–♭VII. |
| 1–4–5–1 | E5 A5 B5 E5 | Three-chord rock | Same roots as H1 (see Q2). |

Caveat: corpora transcribe chord roots and often qualities, but no source I read counts power chords separately. Power-chord claims rest on the root.

## Caveats

- **Genre and era.** The Rolling Stone corpus is rock from the 1950s to 1990s, ranked by critics. Hooktheory is a user-contributed database, with pop, video game and electronic tabs. Neither is a census of what people listen to.
- **Contiguity.** Several sources count sequences without saying whether the four chords must be contiguous. Rotations of one loop are separate paths in Hooktheory.
- **Songs.** I verified song names only through the cited pages. Wikipedia and Hooktheory examples are secondary; double-check before showing any song in the app.
- **Unverified.** I could not retrieve counts from the McGill Billboard thesis, or from Hooktheory's interactive Trends tool.

## Suggested checks before changing the badge

Run these in [Hooktheory Trends](https://www.hooktheory.com/trends) (minor and major views, all tabs) and note the song counts:

1. i–♭VI–♭III–♭VII (S3), i–iv–V–i (S2), i–♭VII–♭VI–♭VII (S5).
2. 1–♭3–4–1 and 1–4–5–4 as major-key I–♭III–IV–I and I–IV–V–IV (R1, R5).
3. I–V–IV–V versus I–IV–V–IV, to see whether R5 is better changed.
4. In the McGill Billboard data, the four-chord n-gram counts for I–V–vi–IV, I–IV–V–I and I–vi–IV–V.

Then apply changes to `strumalong/bandmaker.js` in a separate ticket.
