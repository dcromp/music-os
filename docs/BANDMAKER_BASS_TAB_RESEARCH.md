# Bandmaker: starter bass tabs that follow the rhythm chords

Research date: 3 November 2026. [Research #80](https://github.com/dcromp/music-os/issues/80), informing [prototype #73](https://github.com/dcromp/music-os/issues/73), part of [map #64](https://github.com/dcromp/music-os/issues/64).

## Recommendation

Add **original, short bass exercises with playable tablature**, derived from the actual chords selected in Rhythm. Start with roots and pulse, then root/fifth, explicit rests, octaves and chord tones. The selected key provides context; the current chord determines each bar's target notes. Show **chord name + chord-relative note role + note name + string/fret + timing**, with synchronized listening. These are design recommendations informed by first-party teaching, not a tested curriculum.

StudyBass is the strongest directly relevant starting resource: its teacher-authored lessons connect chord roots, fifths and octaves with bassline construction. Link to those lessons for fuller technique instruction. Do not import copyrighted song riffs or teaching-tab images. The exercises below are newly authored applications of common musical ideas; no source's tab or named-song line is reproduced.

## First-party references and implications

- [StudyBass: Roots to Chords](https://www.studybass.com/lessons/common-bass-patterns/roots-to-chords/) teaches identifying each chord's root and playing it as harmony changes, commonly on beat 1. **Application:** offer a root-only default before runs; G–C–D–G needs G, C, D, G targets, rather than repeating the key's tonic throughout.
- [StudyBass: Roots and Fifths](https://www.studybass.com/lessons/common-bass-patterns/roots-and-fifths/) explains this widely usable interval pair and movable fretboard relationships. **Application:** add one fifth after roots are comfortable. Qualify the rule: a diminished chord needs its diminished fifth, not an automatic perfect fifth.
- [StudyBass: Octaves](https://www.studybass.com/lessons/common-bass-patterns/octaves/) explains octave relationships, string/fret alternatives and controlling one sounding note at a time. **Application:** octaves give variety without a new pitch class; tab must reflect the available strings, not blindly apply a shape beyond the G string.
- [StudyBass: Chord Tones Are Primary](https://www.studybass.com/lessons/bass-chord-patterns/chord-tones-are-primary/) argues from the author's teaching practice for learning chord tones alongside scales. **Application:** explain bass-note choices against each chord. This is a teacher's rationale, not controlled evidence that this exact app sequence improves learning.
- [StudyBass: Rhythmic Notation](https://www.studybass.com/lessons/reading-music/rhythmic-notation/) distinguishes note onsets, durations and silence. [Yamaha: Reading Sheet Music and Tablature](https://hub.yamaha.com/guitars/bass/a-bassists-guide-to-reading-sheet-music-and-tablature/) emphasizes rhythm and note lengths alongside fret locations. **Application:** plain fret numbers are insufficient; add a beat grid, explicit holds/rests, and a matching audible demonstration. Rhythm-enriched tab can carry this information; it is not an intrinsic limitation of every tab format.
- [Fender bass owner's manual](https://www.fmicassets.com/Damroot/Original/10001/OM_leg_bass_2011_Owner%27s_Manual_For_Fender_Basses_English.pdf) specifies four-string E–A–D–G tuning, low to high. **Application:** label standard four-string bass clearly; do not silently present guitar or five-string fingering.
- [StudyBass: Fretting](https://www.studybass.com/lessons/bass-technique/fretting/) discusses relaxed technique, shifts instead of excessive stretches and closer fret spacing higher on the neck. [Open-string muting](https://www.studybass.com/lessons/bass-technique/open-string-muting/) shows why both hands matter for clean single notes. **Application:** low frets/open strings are an option, not a guarantee of easy playing. Suggest a position change when needed and let learners hear the difference between ringing and deliberately stopped notes.

Sources were read on their first-party pages; no course enrollment, learner trial or audio audition was performed. The cited public pages supply teaching references, not permission to redistribute their tabs, recordings or illustrations. StudyBass pages carry an all-rights-reserved notice. Attribution permission for the app's sampled instruments does not license unrelated teaching content. Link externally unless an explicit reusable licence or permission is established for a particular asset.

## What the app currently does

Source review: `strumalong/bandmaker-bass.js` at checkout `3aafbb2`; context also read in `docs/BANDMAKER_BEGINNER_LEARNING_RESEARCH.md`. No app files were edited for this research.

The four current patterns are generated musical pitches: one root per bar; roots on all four beats; root/fifth in half notes; and root/third/fifth/octave in quarters (root/fifth/octave/fifth for power chords). Roots are assigned to the lowest octave from E1 through D#2. Minor and diminished thirds and diminished fifths are handled; a B7 produces B–D#–F#–B, omitting its seventh. That is a valid subset, but not the full B7 arpeggio. These are useful compositional starting points, not bass fingering lessons.

There is currently no string/fret choice, no explicit rest pattern or isolated octave pattern, and no count-in in this file. The display shows note names and attack beats, not full durations. Playback gates each nominal note at 90% of its length, so a displayed four-beat hold is not literally sustained for all four beats. Physical muting, string crossings, shifts, and one-finger-per-fret feasibility are not represented. A future tab should agree with the exact sounding octave and playback duration, rather than attach any convenient fingering to the same note name.

## Original starter material

The following are six **authored exercises**, each applied to both four-bar loops. These are proposed teaching material, not transcriptions and not claims of stylistic authenticity. Start around 60 BPM, or slower if helpful; that tempo is an editorial starting point, not a research-derived threshold. Play one chord per 4/4 bar. Repeat a single bar before attempting the whole loop.

**Notation:** four lines run G (highest/thinnest) to E (lowest/thickest). A number is a fret and `0` means an open string. Each cell is exactly one quarter-note beat. `~` means continue holding the preceding note on that string, not a new attack; `-` means that string is silent for the cell. A column of four dashes is a full beat of rest. These explicit grid conventions supplement ordinary tab. Mute a previous string when a new note begins. The event list is the authoritative onset and duration specification: `note@beat/length[string:fret]`; lengths are in quarter-note beats. Octave labels are **sounding scientific pitches**, with open E1/A1/D2/G2, not octave-transposing written bass notation.

Do not confuse the two numbering systems: Roman I–IV–V–I describes chords relative to G major; bass roles 1–3–5 describe notes relative to the current chord. Thus C's root is bass role 1 while C is chord IV in G major. E minor's loop is i–iv–V7–i; D# in B7 is its major third and a common minor-key dominant tone, not an erroneous D natural. See [Puget Sound: Diatonic Chords in Minor](https://musictheory.pugetsound.edu/mt21c/DiatonicChordsInMinor.html), also cited in the prior research.

### 1. Land on the root

One attack at beat 1, held for four beats. Start here; change with the chord.

**G major: G–C–D–G**

- G: `G1@1/4[E:3]`
- C: `C2@1/4[A:3]`
- D: `D2@1/4[D:0]`
- G: `G1@1/4[E:3]`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - - - | 0 ~ ~ ~ | - - - -
A     - - - - | 3 ~ ~ ~ | - - - - | - - - -
E     3 ~ ~ ~ | - - - - | - - - - | 3 ~ ~ ~
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/4[E:0]`
- Am: `A1@1/4[A:0]`
- B7: `B1@1/4[A:2]`
- Em: `E1@1/4[E:0]`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - - - | - - - - | - - - -
A     - - - - | 0 ~ ~ ~ | 2 ~ ~ ~ | - - - -
E     0 ~ ~ ~ | - - - - | - - - - | 0 ~ ~ ~
```

### 2. Keep a steady pulse

Root on beats 1, 2, 3 and 4, one beat each. Re-pluck on each beat.

**G major: G–C–D–G**

- G: `G1@1/1[E:3], G1@2/1[E:3], G1@3/1[E:3], G1@4/1[E:3]`
- C: `C2@1/1[A:3], C2@2/1[A:3], C2@3/1[A:3], C2@4/1[A:3]`
- D: `D2@1/1[D:0], D2@2/1[D:0], D2@3/1[D:0], D2@4/1[D:0]`
- G: `G1@1/1[E:3], G1@2/1[E:3], G1@3/1[E:3], G1@4/1[E:3]`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - - - | 0 0 0 0 | - - - -
A     - - - - | 3 3 3 3 | - - - - | - - - -
E     3 3 3 3 | - - - - | - - - - | 3 3 3 3
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/1[E:0], E1@2/1[E:0], E1@3/1[E:0], E1@4/1[E:0]`
- Am: `A1@1/1[A:0], A1@2/1[A:0], A1@3/1[A:0], A1@4/1[A:0]`
- B7: `B1@1/1[A:2], B1@2/1[A:2], B1@3/1[A:2], B1@4/1[A:2]`
- Em: `E1@1/1[E:0], E1@2/1[E:0], E1@3/1[E:0], E1@4/1[E:0]`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - - - | - - - - | - - - -
A     - - - - | 0 0 0 0 | 2 2 2 2 | - - - -
E     0 0 0 0 | - - - - | - - - - | 0 0 0 0
```

### 3. Root then fifth

Root on beat 1 for two beats; fifth on beat 3 for two beats. Hear the chord remain supported.

**G major: G–C–D–G**

- G: `G1@1/2[E:3], D2@3/2[D:0]`
- C: `C2@1/2[A:3], G2@3/2[G:0]`
- D: `D2@1/2[D:0], A2@3/2[G:2]`
- G: `G1@1/2[E:3], D2@3/2[D:0]`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - 0 ~ | - - 2 ~ | - - - -
D     - - 0 ~ | - - - - | 0 ~ - - | - - 0 ~
A     - - - - | 3 ~ - - | - - - - | - - - -
E     3 ~ - - | - - - - | - - - - | 3 ~ - -
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/2[E:0], B1@3/2[A:2]`
- Am: `A1@1/2[A:0], E2@3/2[D:2]`
- B7: `B1@1/2[A:2], F#2@3/2[D:4]`
- Em: `E1@1/2[E:0], B1@3/2[A:2]`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - 2 ~ | - - 4 ~ | - - - -
A     - - 2 ~ | 0 ~ - - | 2 ~ - - | - - 2 ~
E     0 ~ - - | - - - - | - - - - | 0 ~ - -
```

### 4. Root then octave

Root on beat 1 for two beats; upper octave on beat 3 for two beats. Optional next step: string crossing and register changes.

**G major: G–C–D–G**

- G: `G1@1/2[E:3], G2@3/2[G:0]`
- C: `C2@1/2[A:3], C3@3/2[G:5]`
- D: `D2@1/2[D:0], D3@3/2[G:7]`
- G: `G1@1/2[E:3], G2@3/2[G:0]`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - 0 ~ | - - 5 ~ | - - 7 ~ | - - 0 ~
D     - - - - | - - - - | 0 ~ - - | - - - -
A     - - - - | 3 ~ - - | - - - - | - - - -
E     3 ~ - - | - - - - | - - - - | 3 ~ - -
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/2[E:0], E2@3/2[D:2]`
- Am: `A1@1/2[A:0], A2@3/2[G:2]`
- B7: `B1@1/2[A:2], B2@3/2[G:4]`
- Em: `E1@1/2[E:0], E2@3/2[D:2]`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - 2 ~ | - - 4 ~ | - - - -
D     - - 2 ~ | - - - - | - - - - | - - 2 ~
A     - - - - | 0 ~ - - | 2 ~ - - | - - - -
E     0 ~ - - | - - - - | - - - - | 0 ~ - -
```

### 5. Leave some space

Root on beat 1 for one beat; rest on beat 2; fifth on beat 3 for one beat; rest on beat 4. Stop the strings for the rests.

**G major: G–C–D–G**

- G: `G1@1/1[E:3], rest@2/1, D2@3/1[D:0], rest@4/1`
- C: `C2@1/1[A:3], rest@2/1, G2@3/1[G:0], rest@4/1`
- D: `D2@1/1[D:0], rest@2/1, A2@3/1[G:2], rest@4/1`
- G: `G1@1/1[E:3], rest@2/1, D2@3/1[D:0], rest@4/1`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - 0 - | - - 2 - | - - - -
D     - - 0 - | - - - - | 0 - - - | - - 0 -
A     - - - - | 3 - - - | - - - - | - - - -
E     3 - - - | - - - - | - - - - | 3 - - -
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/1[E:0], rest@2/1, B1@3/1[A:2], rest@4/1`
- Am: `A1@1/1[A:0], rest@2/1, E2@3/1[D:2], rest@4/1`
- B7: `B1@1/1[A:2], rest@2/1, F#2@3/1[D:4], rest@4/1`
- Em: `E1@1/1[E:0], rest@2/1, B1@3/1[A:2], rest@4/1`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - 2 - | - - 4 - | - - - -
A     - - 2 - | 0 - - - | 2 - - - | - - 2 -
E     0 - - - | - - - - | - - - - | 0 - - -
```

### 6. Outline the chord

Root, third, fifth, root on beats 1–4, one beat each. Returning to the low root keeps this exercise within frets 0–4.

**G major: G–C–D–G**

- G: `G1@1/1[E:3], B1@2/1[A:2], D2@3/1[D:0], G1@4/1[E:3]`
- C: `C2@1/1[A:3], E2@2/1[D:2], G2@3/1[G:0], C2@4/1[A:3]`
- D: `D2@1/1[D:0], F#2@2/1[D:4], A2@3/1[G:2], D2@4/1[D:0]`
- G: `G1@1/1[E:3], B1@2/1[A:2], D2@3/1[D:0], G1@4/1[E:3]`

```text
Chord G       | C       | D       | G
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - 0 - | - - 2 - | - - - -
D     - - 0 - | - 2 - - | 0 4 - 0 | - - 0 -
A     - 2 - - | 3 - - 3 | - - - - | - 2 - -
E     3 - - 3 | - - - - | - - - - | 3 - - 3
```

**E minor: Em–Am–B7–Em**

- Em: `E1@1/1[E:0], G1@2/1[E:3], B1@3/1[A:2], E1@4/1[E:0]`
- Am: `A1@1/1[A:0], C2@2/1[A:3], E2@3/1[D:2], A1@4/1[A:0]`
- B7: `B1@1/1[A:2], D#2@2/1[D:1], F#2@3/1[D:4], B1@4/1[A:2]`
- Em: `E1@1/1[E:0], G1@2/1[E:3], B1@3/1[A:2], E1@4/1[E:0]`

```text
Chord Em      | Am      | B7      | Em
Beat  1 2 3 4 | 1 2 3 4 | 1 2 3 4 | 1 2 3 4
G     - - - - | - - - - | - - - - | - - - -
D     - - - - | - - 2 - | - 1 4 - | - - - -
A     - - 2 - | 0 3 - 0 | 2 - - 2 | - - 2 -
E     0 3 - 0 | - - - - | - - - - | 0 3 - 0
```

## Fingering, range and transposition

Exercises 1, 2, 3, 5 and 6 use frets 0–4 only. Open strings reduce fretting demands but need active muting. Treat finger choices as suggestions based on the phrase and hand, not fixed properties of a pitch. In exercise 6, the B7 bar moves between A2, D1 and D4; allow a hand shift to D4 instead of requiring a static stretch. The same F#2 can be played on A-string fret 9, but that is a poor default for this low-position phrase.

Exercise 4 is deliberately optional: C3 at G5 and D3 at G7 require reaching higher positions. An alternative consistent octave shape uses G1 E3 → G2 D5, C2 A3 → C3 G5 and D2 A5 → D3 G7; this has movable shapes but more shifts. For an earlier-stage learner, replace the upper octave with the original root (exercise 1) or play exercise 3 instead. Do not silently lower D3 to D2 while still labelling it an upper octave.

For arbitrary keys, transpose musical pitch/role first, then choose playable string/fret positions. Moving every displayed fret by the semitone offset fails when an open note would move below fret zero, crosses the usable neck range, or makes transitions awkward. Standard four-string bass has no D1 below open E1; use D2 and disclose the octave change rather than invent a negative fret or assume drop D. Re-finger the entire phrase with a preference for a compact position and modest shifts, not just the lowest fret independently per note. Offer an open-string option and a movable-position option where both are useful. These are proposed heuristics, not a validated ergonomic algorithm.

Read actual chord quality after substitutions: major third = 4 semitones, minor third = 3; perfect fifth = 7, diminished fifth = 6; octave = 12. For a power chord, omit a third rather than imposing major/minor. For sevenths, later offer an explicitly labelled seventh variation; do not imply the root/third/fifth exercise covers every chord tone. Preserve enharmonic spelling from the harmony while calculating pitch separately.

## Suggested product increment and checks

1. Keep the four existing sound-pattern choices; add **Show playable tab** to roots, pulse and root/fifth first. Offer **Space and rests** and **Octaves** as additions; offer the low-root return from exercise 6 as a simpler alternative to the current ascending octave ending.
2. Show the chord progression above the tab with existing Roman degrees. Inside the tab show bass roles, note names, beats and duration together. Link each label to the relevant current chord; avoid presenting a key scale as a guaranteed bassline.
3. Provide one-bar loop, slow tempo and a one-bar count-in, followed by bass-only and bass-with-chords playback. Highlight the note/rest as it sounds; maintain stop/hold behavior when switching tabs. These controls are recommendations, not implemented features.
4. Allow a learner to hear and play one pattern, change only its rhythm, then compare. Test whether they can explain why the bass root changes under C even in a G-major song. A small observed beginner trial and a bass teacher's fingering review are still needed.

**Verification completed:** every displayed fret was checked against E1/A1/D2/G2 open-string MIDI values 28/33/38/43; fifths, thirds and octaves were checked arithmetically; each bar has exactly four beats; tab grids were generated from the same event definitions as the printed event lists. This is pitch/timing consistency checking, not audio audition, physical play-testing, or an evaluation of educational effectiveness. No learner success, iPhone readability or optimal fingering is claimed. No source tab, audio or copyrighted song excerpt was downloaded into the project.
