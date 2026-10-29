# Strum Along song research: strumming-first additions

Date: 25 October 2026. Decision by the lead's delegate, drawing on three
research passes: popularity lists, teacher song lists, and beginner-course
pedagogy. This document selects the songs. The recordings (uploads) are chosen
in a later step, and the metadata goes in `strumalong/data/additions-v2.json`
(see [STRUMALONG_APP.md](STRUMALONG_APP.md)). No lyrics are reproduced here.

## Founder requirements (25 October 2026)

Summary of the founder's feedback:

- Focus on **strumming** songs. There are enough pop and rock songs that the
  app need not teach finger patterns.
- Creep and Good Riddance feel like finger-picking songs. Riff songs don't fit
  either, and Love Me Do "isn't even a guitar song".
- The app should be **progressive in difficulty**. Creep needs barre chords
  (B, Cm) and should not sit among the early songs.
- On Good Riddance the bar lines fell oddly, in the middle of chords.
- A quick sweep of top pop and rock songs, filtered by these requirements,
  should produce a decent list.

The filter applied to every pick:

1. The defining guitar part of the studio recording is **strummed chords** for
   most of the song. Fingerpicked or arpeggiated, riff-driven, piano- or
   synth-led and harmonica-led songs are rejected.
2. A widely known rock or pop hit, with at least one popularity source.
3. Playable with open shapes at capo ≤ 7 for Levels 1–3. Songs needing F or Bm
   go to Level 4, and full barres to Level 5.
4. Steady tempo in 4/4, or a clearly strummed 6/8 or 3/4. No tempo changes,
   no key changes and no frequent odd bars.
5. A single well-known studio recording exists.

The 13 songs that stay in the app were not re-proposed. The 7 dropped songs
are listed under [Rejections](#notable-rejections).

## Sources swept

**Popularity lists**
- Rolling Stone 500 (2004 top 100; 2021 guitar-band entries): <https://de.wikipedia.org/wiki/Die_500_besten_Songs_aller_Zeiten>, <https://en.wikipedia.org/wiki/Rolling_Stone%27s_500_Greatest_Songs_of_All_Time> (RS04, RS21)
- NME 500 (2014): <https://stereogum.com/1660091/nmes-500-greatest-songs-of-all-time/news> (NME)
- Ultimate Classic Rock top 100: <https://ultimateclassicrock.com/top-100-classic-rock-songs> (UCR)
- UK Official Charts most-streamed of all time: <https://www.officialcharts.com/chart-news/the-uks-official-most-streamed-songs-of-all-time__37837/> (OCS)
- Most-streamed on Spotify: <https://en.wikipedia.org/wiki/List_of_most-streamed_songs_on_Spotify> (SPO)
- UK and US best-selling singles: <https://en.wikipedia.org/wiki/List_of_best-selling_singles_in_the_United_Kingdom>, <https://en.wikipedia.org/wiki/List_of_best-selling_singles_in_the_United_States> (UKS, USS)
- PPL UK most-heard 75: <https://americansongwriter.com/britains-75-most-heard-song-list-topped-byprocul-harum/>, 21st-century list <https://www.ppluk.com/?p=3557> (PPL)
- Radio X Best of British (partial): <https://radiotoday.co.uk/2026/04/radio-x-listeners-name-greatest-500-british-songs-ever/> (RX)
- Wikipedia song pages, for chart peaks and certifications: [Budapest](https://en.wikipedia.org/wiki/Budapest_(song)), [What's Up?](https://en.wikipedia.org/wiki/What%27s_Up%3F_(4_Non_Blondes_song)), [Breakfast at Tiffany's](https://en.wikipedia.org/wiki/Breakfast_at_Tiffany%27s_(song)), [Lucky Man](https://en.wikipedia.org/wiki/Lucky_Man_(The_Verve_song)), [Stuck in the Middle with You](https://en.wikipedia.org/wiki/Stuck_in_the_Middle_with_You), [I'm Gonna Be (500 Miles)](https://en.wikipedia.org/wiki/I%27m_Gonna_Be_(500_Miles)), [Sit Down](https://en.wikipedia.org/wiki/Sit_Down_(James_song))

**Teacher and guitar-site song lists**
- Killer Guitar Rigs sing-alongs: <https://killerguitarrigs.com/best-sing-along-and-campfire-songs-on-guitar/> (KGR)
- Guitar Lobby easy acoustic and easy strumming: <https://www.guitarlobby.com/easy-acoustic-guitar-songs-for-beginners/> (GL), <https://www.guitarlobby.com/easy-strumming-songs/>
- Guitar Habits 50 acoustic: <https://www.guitarhabits.com/50-of-the-best-acoustic-guitar-songs-of-all-time/> (GH)
- Acoustic World 50 beginner: <https://acousticworld.net/50-best-acoustic-songs-for-beginners-with-chords-and-tabs/> (AW)
- Andy Guitar top 20 three-chord songs: <https://andyguitar.co.uk/videos/top-20-three-chord-songs> (AG)
- Applied Guitar Theory: <https://appliedguitartheory.com/lessons/easy-open-chord-guitar-songs/>, <https://appliedguitartheory.com/lessons/easy-songs-for-guitar/> (AGT)
- Guitar Chalk four-chord songs: <https://www.guitarchalk.com/four-chord-songs/> (GC)
- Good Guitarist: <https://goodguitarist.com/songs/>, <https://goodguitarist.com/top-guitar-songs-to-learn-2025> (GG)
- JustinGuitar songbook stage lists: <https://www.andertons.co.uk/justinguitar-beginners-songbook-2nd-edition-spiral-bound/>, <https://www.andertons.co.uk/justinguitar-beginners-songbook-volume-2/>, with lesson codes from <https://www.justinguitar.com/sitemap.xml> (JG)
- Hal Leonard First 50 Songs You Should Strum: <https://www.halleonard.com/product/148996/first-50-songs-you-should-strum-on-guitar> (HL50)
- Snippet-only: Ultimate Guitar most-viewed tabs (UGJ), Guitar World acoustic polls, MusicRadar acoustic list, Happy New Guitar Day (HNG)

**Chord sheets and tempo checks (one or more per chosen song)**
guitartabsexplorer.com, chordu.com, musictonic.com, goodguitarist.com,
laurenbateman.com, songnotes.net, andyguitar.co.uk, songbpm.com, and Ultimate
Guitar or Musicnotes data seen through search results. The per-song source is
named in the table notes below.

**Pedagogy**
JustinGuitar Grades 1–4 (<https://justinguitar.com/site-map-and-lesson-structure>,
<https://justinguitar.com/guitar-lessons/one-minute-changes-exercise-b1-110>),
the Andy Guitar beginner course (<https://www.andyguitar.co.uk/courses/absolute-beginner-guitar>),
Fender Play (<https://www.fender.com/play/guitar/skills>) and Hal Leonard
Method Book 1 (<https://halleonard.com/product/699010/hal-leonard-guitar-method-book-1>).

Ultimate Guitar, e-chords, Cifra Club and JustinGuitar song pages returned 403
to direct fetches, so their data is second-hand through search results.

## Level model

Shapes are what the player frets after any capo. The tiers and levels are the
lead decision already in `strumalong/tools/build-songs.js`.

| Tier | Shapes |
|---|---|
| T1 | A, D, E, Em, Am, plus A7, D7, E7, Am7, Em7, Asus2, Asus4, Dsus2, Dsus4, Esus4 |
| T2 | G, C, Dm, G7, C7, B7, Cadd9, Cmaj7, Fmaj7, Dm7, G/B, D/F#, C/G |
| T3 | F (including mini-F), Bm, Bm7, F#m |
| T4 | every other shape (B, Bb, Cm, C#m, G#m, Gm, F#, Eb …) |

| Level | Rule |
|---|---|
| 1 · First chords | all main shapes T1, at most 3 |
| 2 · Open chords | all ≤ T2, at most 4 (or all T1 with 4+) |
| 3 · More changes | all ≤ T2 with 5+ shapes, or quick changes, or an authored `needs_syncopation` |
| 4 · First barre (F / Bm) | any T3 main shape, no T4 |
| 5 · Barre chords | any T4 main shape |

Main shapes are Core shapes covering at least 4% of chord time.

### One change adopted: the quick-change rate line moves from 30 to 40 changes per minute

The pedagogy pass showed the 30-per-minute line sits on ordinary songs. One
chord per bar at 120 BPM is exactly 30 changes a minute. JustinGuitar's "30
changes a minute" target is a two-chord drill, not a strum-along pace. The
app's own data shows the problem:

- Bad Moon Rising (28.7), Riptide (29.0), Don't Look Back in Anger (29.8),
  Wild Thing (30.2) and Free Fallin' (30.7) all sit within one change a minute
  of the line.
- Wild Thing needed a manual `level_overrides` entry to stay at Level 1.
- New one-chord-per-bar songs would land at Level 3 for no musical reason:
  A Horse with No Name (~31/min at 123 BPM), What's Up? (~34/min at 135 BPM)
  and Sit Down (~32/min at 126 BPM).

**New rule:** quick = **≥ 40 changes per minute** (about one change every 1.5 s),
or median hold ≤ 2 beats at ≥ 120 BPM (unchanged). Effects on the songs that
stay, using their stored statistics:

| Song | Changes/min | Before | After |
|---|---|---|---|
| Wild Thing | 30.2 | L3, overridden to L1 | L1 (the override can be removed) |
| Free Fallin' | 30.7 | L3 | L2 |
| Brown Eyed Girl | 34.2 (median 4 beats at 152 BPM) | L3 | L2 |
| Wonderwall | 34.0 | L3 | L2, unless `needs_syncopation` is authored (recommended, so it stays L3) |
| Twist and Shout | 40.2 (median 2 beats at 123 BPM) | L3 | L3 |
| Island in the Sun | 51.4 | L3 | L3 |

**Clarification, no code change:** set `needs_syncopation` only when the song's
pattern needs anticipations, muted chucks or 16ths. That is step P4 of the
course ladder. The common D – D U – U D U pattern is taught in JustinGuitar
Grade 1 and should not count. On that basis, author the flag for Wonderwall
and I'm Yours.

**Considered, not adopted:**
- Letting G and C into Level 1. Strict Level 1 still reaches six songs, and
  starting with A, D and E follows the JustinGuitar and Andy Guitar order.
- Power chords as T2. No power-chord songs were chosen.
- Lowering the tier-ceiling cutoff to 2% of chord time, a second "with easy
  substitutions" level, a continuous difficulty score, and automatic capo
  selection. These are worth revisiting once the catalogue grows. Passing hard
  chords (for example Sweet Caroline's brief walkdown, or Riptide's 3.1% F)
  could get a UI flag later.

## Final selection: 24 new songs

The level is the expected level from the chord sheets at the stated capo. The
app computes its own level from the automatic chart. Tempo is the studio pulse
from the cited sources. All songs are in 4/4.

### Level 1 · First chords (5)

| Artist | Title | Year | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|
| Bob Marley & The Wailers | Three Little Birds | 1977 | A D E (0) | 74 | Three T1 shapes, slow, long holds. The record's guitar is an off-beat strummed chop; start with four downs per bar. JustinGuitar Stage 1. Sheet: musictonic (A major, 74 BPM, 4/4). | GL26, AW39 |
| America | A Horse with No Name | 1971 | Em, D6add9/F# (0) | 123 | Two shapes, one per bar; a strummed 12-string acoustic carries the record. Sheet: guitartabsexplorer (Em 022000, D6add9/F# 200200); songbpm 123. | GL34, GH38, AW11 |
| Neil Diamond | Sweet Caroline | 1969 | A D E (2) | ~127 | The record is in B; capo 2 gives A, D and E (Andy Guitar). Acoustic strum under horns. Passing F#m and a short Bm walkdown (about 4% of changes in chordu's chart). | KGR33, AG2 |
| Snow Patrol | Chasing Cars | 2006 | A E D (0) | 104 | Three T1 shapes, one per bar. Taught as "8ths all down" (Andy Guitar). The record's guitar pulses eighth-note downstrokes on two-note shapes. **Borderline** on requirement 1 (see Limitations). Sheet: guitartabsexplorer; chordu 104 BPM. | OCS136, AG4, AW23, KGR28, PPL 21st-century #1 |
| James | Sit Down | 1991 | A D E (7) | 126 | The record is in E (E, A, B per guitartabsexplorer; songbpm E major, 126). Capo 7 keeps it all T1. Andy Guitar teaches capo 2 with D, G and A (Level 2) as his lesson 2. Swung strum. | UK #2 1991, BPI Platinum (Wikipedia); not on the swept lists |

### Level 2 · Open chords (5)

| Artist | Title | Year | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|
| Coldplay | Yellow | 2000 | G D C Em (4) | 87 | The record is in B (guitartabsexplorer; songbpm 173, half time 87). Capo 4 shapes, as taught by Andy Guitar. Big strummed chords, one per bar. | OCS160, SPO14, GH36, AW15, UGJ |
| 4 Non Blondes | What's Up? | 1993 | G Am C (2) | 135 | The record is A, Bm, D (guitartabsexplorer). Capo 2 avoids the Bm (JustinGuitar Stage 3 trick). Strummed acoustic throughout, one chord per bar. | UK #2, US #14, BPI 2× Platinum (Wikipedia); JG1 Stage 3 |
| Deep Blue Something | Breakfast at Tiffany's | 1995 | D G A (0) | 114 | D, G and A with sus colours; a bright strummed acoustic (chordu: D major, capo 0, 113.85 BPM; Am is brief). | UK #1, US #5, BPI 2× Platinum (Wikipedia) |
| George Ezra | Budapest | 2014 | D G A (3) | 128 | The record is in F with F, Bb and C (Wikipedia: F major, 128 BPM; chordu alternative video). Capo 3 gives D, G and A without retuning; JustinGuitar instead tunes down a tone and plays G, C and D. | OCS54; UK #3, BPI 6× Platinum |
| The Verve | Lucky Man | 1997 | G D Asus4 Em (0) | 76 | A slow loop on strummed acoustic with strings (guitartabsexplorer: G, D, Asus4, Em in the bridge). | UK #7, BPI 2× Platinum (Wikipedia); HNG |

### Level 3 · More changes (6)

| Artist | Title | Year | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|
| Neil Young | Heart of Gold | 1972 | Em C D G (0) | 86 | Four open shapes, two chords per bar (about 40+ changes a minute), so expected L3; it may compute L2. Strummed acoustic with harmonica breaks; harmonica is not the main part. Sheet: Ultimate Guitar via search (Em7, D, Em, C, G, no capo); songbpm 86. | KGR7, GL6, GH4, AW9 |
| Eagles | Take It Easy | 1972 | G C D Em Am (0) | 138 | Five-plus open shapes; acoustic strum drives the record (Ultimate Guitar via search: key G, no capo; Good Guitarist 138). | GL69, AW7 |
| Stealers Wheel | Stuck in the Middle with You | 1972 | D G A C Am (0) | ~120 | Open shapes with a percussive slap strum (songnotes: D, 116 BPM; chord sites D, G, A, C, Am). Computes L2 if Am stays under 4%. | UK #8, US #6, BPI 2× Platinum (Wikipedia) |
| Jason Mraz | I'm Yours | 2008 | G D Em C (4) | 151 | Open loop, but the record's "island" strum with muted chucks is the skill: author `needs_syncopation`. Good Guitarist: 151 BPM, Late Beginner. | KGR40, GL40, AW47, USS |
| Green Day | Boulevard of Broken Dreams | 2004 | Em G D A C B7 (1) | 84 | The record is in F minor; capo 1 gives open shapes (Heartwood and Andy Guitar). Six shapes, strummed verse and driving chorus. songbpm 167 (half time 84). | KGR35 |
| The Beatles | I Want to Hold Your Hand | 1963 | G D Em B7 C Dm Am (0) | 130 | Seven open shapes with quick two-beat changes; driving rhythm-guitar strum (G major, about 130 BPM). | UKS18, USS, RS04-16, RS21-15 |

### Level 4 · First barre (F / Bm) (4)

| Artist | Title | Year | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|
| Eagle-Eye Cherry | Save Tonight | 1997 | Am F C G (0) | 120 | One-bar-per-chord loop where F is the only new shape. Strummed acoustic. Sheet: gitaartabs (capo 0); about 120 BPM. | GL65 |
| Tom Petty | Learning to Fly | 1991 | F C Am G (0) | 116 | The same F loop for the whole song (songnotes; Musicnotes key C, about 116 BPM). | GL51 |
| The Lumineers | Ho Hey | 2012 | C F Am G (0) | 80 | Slow, with F, plus a stomp-clap syncopated strum. Good Guitarist: 80 BPM, Late Beginner. | AW22 |
| Cat Stevens | Wild World | 1970 | Am D G C F Dm E (0) | ~76 | Seven open shapes plus one F; all-downstroke strum (songnotes; key A minor, about 74–76 BPM). | AW14 |

### Level 5 · Barre chords (4)

| Artist | Title | Year | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|
| The Beatles | Help! | 1965 | A C#m F#m D G Bm E (0) | ~96 | C#m (T4) every verse. Lennon's strummed 12-string acoustic is the backbone (A major, about 96 BPM). | RS04-29 |
| The Proclaimers | I'm Gonna Be (500 Miles) | 1988 | E A B C#m F#m (0) | ~134 | B and C#m are T4. A staccato strummed acoustic is the hook (E major, capo 0, 132–136 BPM). | UK #11 (1988) and #1 (2007), US #3, BPI 2× Platinum (Wikipedia); AGT |
| Natalie Imbruglia | Torn | 1997 | F Am Dm Bb C (0) | ~96 | Bb is in every verse cycle: a first A-shape barre. Strummed acoustic (Ultimate Guitar via search: key F, no capo; 92–96 BPM). Capo 5 (C, Em, Am, F) would make it Level 4. | PPL22 |
| Queen | Crazy Little Thing Called Love | 1979 | D G C A E Bb (0) | 154 | Swung rockabilly strum on acoustic. The Bb turnaround before each chorus is T4. It computes L4 if only F reaches 4%, or L3 if neither Bb nor F does. songbpm 77, double time 154. | KGR31, GH11, MR |

### Projected level counts

These assume the adopted 40-per-minute line and the `needs_syncopation` flag
on Wonderwall and I'm Yours.

| Level | Staying songs | New songs | Total |
|---|---|---|---|
| 1 | Wild Thing | 5 | 6 |
| 2 | Zombie, Country Roads, Knockin', Bad Moon Rising, Riptide, Free Fallin', Brown Eyed Girl | 5 | 12 |
| 3 | Wonderwall, Twist and Shout, Island in the Sun | 6 | 9 |
| 4 | Have You Ever Seen the Rain, Don't Look Back in Anger | 4 | 6 |
| 5 | — | 4 | 4 |

## Fallbacks (9)

Use these if a pick has no usable upload or fails chart review.

| Artist | Title | Shapes (capo) | Tempo | Expected level | Note |
|---|---|---|---|---|---|
| Darius Rucker (Old Crow Medicine Show, 2004) | Wagon Wheel | G D Em C (2) | ~150 | 2 | Country-pop crossover; fiddle on top. GL73, GC. |
| Johnny Cash | Ring of Fire | G C D (0) | ~105 | 2 | Boom-chick strum; horns carry the hook. KGR21, AG14, AW12, RS04-87. |
| Steve Miller Band | The Joker | D G A (3) | — | 2 | The record is in F. Capo 3 replaces the whole-step-down tuning. Slide lick on top. AG13. |
| Poison | Every Rose Has Its Thorn | D G A (4) | — | 2 | The record is a half step down (G, Cadd9, D shapes). Capo 4 matches it. Arpeggiated intro. GC, AW48. |
| Tom Petty | Mary Jane's Last Dance | Am G D (0) | — | 2 | Third Tom Petty song; harmonica intro. AGT9. |
| Tom Petty | I Won't Back Down | Em D G C (0) | 114 | 3 | Em, D, G inside 2 bars (~43/min). Good Guitarist. |
| Pink Floyd | Wish You Were Here | Em7 G A7sus4 C D Am (0) | ~122 | 3 | Picked 12-string intro and fills; verses strummed. KGR22, AGT4, UCR. |
| Counting Crows | Mr. Jones | Am F Dm G C (0) | — | 4 | Two strum patterns, verse and chorus. JustinGuitar Stage 6, AGT. |
| Oasis | Live Forever | G D Am C Em F (0) | ~88 | 4 | A third Oasis song. NME13, RX1. |

## Notable rejections

**Dropped from the app**

| Song | Reason |
|---|---|
| Radiohead, Creep | Arpeggiated verse, and B and Cm barres (Level 5 by shape). Not a beginner strum song. |
| The Animals, The House of the Rising Sun | Arpeggiated 6/8 picking; organ solo. |
| The White Stripes, Seven Nation Army | Riff song with no strummed chord part. |
| Nirvana, Come As You Are | Riff song. |
| The Beatles, Love Me Do | Harmonica-led; the guitar barely features. |
| Green Day, Good Riddance (Time of Your Life) | Flatpicked pattern, not strummed. The automatic chart also put bar lines mid-chord (see Limitations). |
| Lynyrd Skynyrd, Sweet Home Alabama | Picked riff. |

**Rejected candidates**

| Song | Reason |
|---|---|
| Eagles, Hotel California | Arpeggiated, with Bm and F# barres. |
| Led Zeppelin, Stairway to Heaven | Fingerpicked, and the tempo changes. |
| The Beatles, Blackbird | Fingerpicked. |
| Kansas, Dust in the Wind | Travis picking. |
| Nirvana, Smells Like Teen Spirit | Power-chord riff. |
| Guns N' Roses, Sweet Child O' Mine | Riff. |
| OutKast, Hey Ya! | A short bar in every chord cycle (frequent odd bars). |
| Ben E. King, Stand By Me | Bass- and strings-led; the guitar is subtle. |
| Fleetwood Mac, Dreams | Bass-led. |
| Bryan Adams, Summer of '69 | Pre-chorus and chorus are picked arpeggios. |
| Goo Goo Dolls, Iris | Alternate tuning; picked. |
| The Cranberries, Linger | Arpeggiated with strings. |
| The Killers, Mr. Brightside | Picked riff. |
| Arctic Monkeys, 505 | Organ and riff led. |
| Passenger, Let Her Go; Ed Sheeran, The A Team, Photograph, Perfect | Fingerpicked (Perfect is also 12/8). |
| Guns N' Roses, Patience | Whistled and picked intro; half-step-down tuning puts it at Level 4 even with a capo. |
| Train, Hey, Soul Sister | Ukulele-led. |
| Pulp, Common People | Synth-led build. |
| Semisonic, Closing Time; The Beatles, Let It Be, Hey Jude; John Lennon, Imagine | Piano-led. |
| Bob Marley, No Woman No Cry | Organ-led. |
| OneRepublic, Counting Stars; Avicii, Wake Me Up | Piano or synth-led. |
| Green Day, Wake Me Up When September Ends | Picked verses. |
| U2, With or Without You; I Still Haven't Found What I'm Looking For | Delay arpeggios. |
| Foo Fighters, Everlong | Drop-D power-chord riff. |
| Foo Fighters, Times Like These | 7/8 bars. |
| Don McLean, American Pie | 8½ minutes with a slow, free opening. |
| Wings, Mull of Kintyre | Key change for the bagpipe section. |
| Taylor Swift, Love Story | Key change near the end. |
| The Kingsmen, Louie Louie | 3+2 chord grouping; the metre is disputed. |
| Mumford & Sons, Little Lion Man, I Will Wait | Banjo-led, very fast. |
| Bob Dylan, Blowin' in the Wind | Folk with harmonica; Dylan is already in the app. |
| The Monkees, I'm a Believer | Organ and guitar riff hook. |
| Jimi Hendrix, Hey Joe; The Beatles, Get Back; CCR, Fortunate Son; AC/DC, You Shook Me All Night Long | Lead or riff carries the record. |
| George Ezra, Shotgun | The record's guitar part is unverified; F, Bb, Dm, C needs capo 3 or 5 to reach Level 4. |

## Limitations

- **Expected levels come from chord sheets.** The app computes levels from
  automatic charts at the configured capo, and they can differ:
  - Labels: A Horse with No Name's second chord could be read as D (L1),
    D/F# (L2), or Bm or F#m (L4). Pin it with a `level_overrides` entry if
    needed.
  - Passing chords near the 4% line: Sweet Caroline's F#m and Bm,
    Stuck in the Middle's Am, Crazy Little Thing Called Love's Bb and F.
  - Change rate near the line: Heart of Gold and Sit Down.
- **The new quick-change line is a recommendation.** Until it is applied in
  `build-songs.js`, several L1 and L2 picks will compute at L3.
- **Strum-versus-pick is judged by ear and teaching sources**, not by analysing
  the uploads. Chasing Cars is the most borderline pick: its main guitar is an
  eighth-note downstroke pulse on two-note shapes. Drop it if it feels picked
  in review; Level 1 still has five songs without it.
- **Tempos** are single-source or algorithmic (songbpm, chordu) and some are
  half or double time. Measure each upload with the repo's analysis.
- **Capos are chosen to match the recording's pitch.** The capo-7 Sit Down,
  capo-3 Budapest and capo-3 The Joker replace a teacher's alternative (capo 2,
  or retuning). Both routes are noted.
- **Bar lines.** The founder saw bar lines fall mid-chord on Good Riddance. That
  is a downbeat or phase error in the automatic chart, not a song-choice
  issue. Check each new import's on-bar change share and bar placement before
  it ships. Long-hold songs (Three Little Birds, Lucky Man) expose this most.
- **Uploads are not chosen here.** Pick them in a later step, preferring the
  single studio recording named in the table. Exclude any upload that turns
  out live, re-recorded, picked or riff-based in `catalogue.json`, with a
  reason.
- Popularity evidence is partial. Some lists showed only their top entries, and
  Sit Down's evidence is chart and certification data, not a list.

## v4 batch (28 October 2026): towards 100 songs

The founder wants the catalogue grown from 43 to about 100 songs: top rhythm-guitar (strummed) rock and pop hits. This batch applies the same filter as above (strummed chords for most of the studio recording; a widely known hit; steady 4/4 or a clearly strummed 6/8; no key or tempo changes; one well-known studio recording). It nominates 66 first picks and 10 fallbacks, so that about 57 survive the automated chord, instrument and strum checks. Nothing in `songs/index.json`, the catalogue `exclude` list, the rejections above, or candidates v1 to v3 (first picks and fallbacks) is re-proposed. Every row carries `genre` (`rock` or `pop`).

Files: `experiments/fixtures/strumalong-additions-candidates-v4.json` (uploads) and `strumalong/data/additions-v4.json` (metadata, `chart_check` pending). No lyrics are reproduced here.

### Sources used

**Top rock and pop lists**: the lists swept above (Rolling Stone 500, NME 500, Ultimate Classic Rock top 100, UK and US best-sellers, UK and Spotify most-streamed), screened against the catalogue for strummed hits not yet proposed. The chart peaks and certifications in the Popularity column are UK Official Charts and Billboard figures as recalled during research, spot-checked against Wikipedia song pages; they were not all re-fetched, so verify any that matter.

**Guitar-teacher strumming lists and lessons**: Andy Guitar (Have a Nice Day; When I Come Around), JustinGuitar and Guitar Lobby easy-strumming lists (as above), Totally Guitars lessons (You're Still the One, Peace Train, Bonfire Heart, Pink Houses), Lauren Bateman chord charts (End of the Line, Who'll Stop the Rain, Stick Season, Me and Julio, Redemption Song), Guitar Noise easy-song threads (The Drugs Don't Work, Why Does It Always Rain on Me?), Heartwood Guitar, Uberchord, School of Feedback, Richter Guitar and Guitar Player (the Only Wanna Be with You capo story).

**Chord sheets and theory**: Ultimate Guitar (search snippets and the pg.zachmanson.com mirror, since UG returns 403 to direct fetches), guitartabs.cc, Guitar Tabs Explorer, e-chords, chordu, Hooktheory TheoryTabs, Yousician, gitaartabs.nl, ukutabs, Alan W. Pollack's Beatles notes, and Musicnotes listings. The per-song source is in the metadata `sources`.

**Tempo and key**: SongBPM (<https://songbpm.com>) for 75 of the 94 songs first examined, plus GetSongBPM, Hooktheory and Musicnotes markings. These are algorithmic and sometimes half or double time.

**Uploads**: read-only yt-dlp searches (metadata only, no download), oEmbed and the embed-page playability check, at one YouTube request every ~2.5 s.

### Picks by level

Shapes are what the player frets at the stated capo; the level is the expected level from the chord sheets. Tempo is the studio pulse from the cited source (some are half or double time).

#### Level 1 · First chords (1)

| Artist | Title | Year | Genre | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|---|
| Hootie & the Blowfish | Hold My Hand | 1994 | pop | A D E (2) | ~86 (songbpm 171, half time) | Mostly A and D with E in the chorus; strummed acoustic and electric. Bm or F#m may appear briefly, which would make it L4. | US #10 (1995); Cracked Rear View, 21x Platinum |

#### Level 2 · Open chords (25)

| Artist | Title | Year | Genre | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|---|
| Creedence Clearwater Revival | Lookin' Out My Back Door | 1970 | rock | G Em C D (4) | ~120 (Hooktheory) | Chugging country-rock rhythm guitar on open shapes; record in B, so capo 4 G shapes. | US #2 (1970) |
| Traveling Wilburys | End of the Line | 1988 | rock | D A G (0) | ~167 (songbpm) | Acoustic train-beat strum on three open chords; the whole band strums. | UK #52, US Mainstream Rock #2 (1989); Traveling Wilburys Vol. 1, 3x Platinum |
| Neil Young | Rockin' in the Free World | 1989 | rock | Em D C G (0) | ~132 (songbpm) | Distorted electric chord strum on Em-D-C throughout; no riff hook. | US Mainstream Rock #2 (1989); Rolling Stone 500 (2004) #216 |
| Matchbox Twenty | 3AM | 1997 | rock | G Cadd9 D Em (1) | ~108 (songbpm) | Acoustic strum carries the song after a short picked intro; record in Ab, capo 1. | Yourself or Someone Like You, 12x Platinum album |
| Hootie & the Blowfish | Only Wanna Be with You | 1995 | pop | D G A Em (4) | ~103 (songbpm) | Capo-up jangly acoustic strum; record in F#. Mandolin colours it but the guitar strum leads. | US #6 (1995) |
| Pearl Jam | Last Kiss | 1999 | rock | G Em C D (0) | ~112 (songbpm) | Simple I-vi-IV-V strum with a shuffle feel. Some charts add a late Gm/A, which needs a listen. | US #2 (1999), Pearl Jam's highest-charting US single |
| John Mellencamp | Small Town | 1985 | rock | G Dsus2 Cadd9 Am (4) | ~123 (songbpm) | Driving acoustic strum on capo-4 open shapes; record in B. | US #6 (1985) |
| Sublime | What I Got | 1996 | rock | D G (0) | ~96 (songbpm) | Two-chord acoustic strum over a beat for the whole song. | US Modern Rock #1 (1996) |
| James | Laid | 1993 | rock | G C D (5) | fast; songbpm 116 | Frantic acoustic strum the whole way. Record in C; capo 5 swaps C, F and G for G, C and D shapes (open it is L4). | UK #25, US Modern Rock #3 (1993) |
| Jake Bugg | Lightning Bolt | 2012 | rock | D A G (2) | ~113 (Musicnotes) | Fast skiffle-style acoustic strum throughout; record in E, capo 2. | UK #26 (2012); Jake Bugg UK #1 album |
| The Rolling Stones | Dead Flowers | 1971 | rock | D G A (0) | ~125 | Country acoustic strum on three chords throughout. | Sticky Fingers (UK and US #1 album, 1971) |
| Status Quo | Rockin' All Over the World | 1977 | rock | G C D (5) | ~131 (songbpm) | Band chord strum; record in C, capo 5 gives G, C, D shapes (open it needs F, L4). A passing diminished chord is brief. | UK #3 (1977) |
| Taylor Swift | You Belong with Me | 2008 | pop | D A G Em (4) | ~130 (songbpm) | Steady acoustic eighths strum; record in F#, capo 4. Original Fearless recording, not the re-recording. Bridge Bm unconfirmed. | US #2 (2009) |
| Taylor Swift | We Are Never Ever Getting Back Together | 2012 | pop | Cadd9 G D Em (0) | ~86 (songbpm 172, double time) | Acoustic strum with muted chops on a simple loop; spoken bridge only. | US #1 (2012), UK #4 |
| Jimmy Buffett | Margaritaville | 1977 | pop | D A G (0) | ~124 (Hooktheory; songbpm 125) | Acoustic strum carries it; steel drums and harmonica are colour only. | US #8 (1977) |
| Sugar Ray | Every Morning | 1999 | pop | G D C (1) | ~110 (Hooktheory; songbpm 110) | Acoustic strum loop under a lead lick; record in Ab, capo 1. | US Airplay #1 (1999), UK #10 |
| The Lumineers | Stubborn Love | 2012 | pop | C Em G D (5) | ~115 (songbpm) | Acoustic strumming with cello and strings; capo 5. | The Lumineers (2012), multi-Platinum debut album |
| Shania Twain | You're Still the One | 1997 | pop | D G A Em (1) | ~68 | Slow acoustic strum; steel guitar fills on top. Record in Eb, capo 1. | US #2, UK #10 (1998) |
| Noah Kahan | Stick Season | 2022 | pop | G D Em C (2) | ~117 | Fast driving strum after a picked first verse; record in A, capo 2. Could compute L3 on pace. | UK #1 (2023), US #9 |
| Harry Chapin | Cat's in the Cradle | 1974 | pop | E D G A (1) | ~78 (songbpm) | Picked intro, strummed verses; Bm may appear. | US #1 (1974) |
| Barenaked Ladies | If I Had $1000000 | 1992 | pop | G D C Em (2) | ~ | Acoustic strumming leads; spoken and stop-time breakdowns may break the grid. | Canada top 40 (1992); signature song |
| Uncle Kracker | Follow Me | 2000 | pop | D G A Em (3) | 105 (songbpm) | Acoustic strum throughout; record in F, capo 3 gives D shapes (the common capo-1 chart needs B, L5). | US #5 (2001) |
| Taylor Swift | Mine | 2010 | pop | C G D Em (0) | ~121 (songbpm) | Acoustic strum with banjo colour; original Speak Now recording, not the re-recording. | US #3 (2010) |
| Oasis | Songbird | 2003 | rock | G Em7 (0) | ~135 (songbpm) | Acoustic strum through the whole song; irregular phrase lengths in the instrumental need a check. | UK #3 (2003) |
| Lifehouse | Hanging by a Moment | 2000 | rock | G D Em C (6) | ~124 (Hooktheory) | Driving distorted eighth-note chord strumming. The record is tuned down (drop D a half step lower); capo 6 in standard tuning matches its pitch. | US Billboard Hot 100 #1 song of 2001 (peak #2) |

#### Level 3 · More changes (11)

| Artist | Title | Year | Genre | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|---|
| Creedence Clearwater Revival | Who'll Stop the Rain | 1970 | rock | G C D Em Am (0) | ~120 | Acoustic strum drives the whole song. Charts that keep the Bm make it L4. | US #2 (1970, double A-side) |
| Stereophonics | Have a Nice Day | 2001 | rock | A G D E D/F# (2) | ~121 (songbpm) | Acoustic strum throughout; record in B, capo 2. Taught by Andy Guitar. | UK #5 (2001) |
| Counting Crows | Accidentally in Love | 2004 | pop | G Em C D A Am (0) | ~138 (Hooktheory; songbpm 138) | Bright band strum through six open shapes after a short intro hook. | Shrek 2 single; Oscar-nominated (2005); UK #28 |
| Phillip Phillips | Home | 2012 | pop | G C Em D D/F# (5) | ~121 (Hooktheory; songbpm 121) | Acoustic strum throughout; record in C, capo 5 (open shapes would need F). | US #6 (2012), 5x Platinum |
| Paul Simon | Me and Julio Down by the Schoolyard | 1972 | pop | A D E B7 G (0) | ~103 (getsongbpm; songbpm 105) | Percussive syncopated acoustic strum on open shapes; the strum is the skill. | US #22, UK #15 (1972) |
| MAGIC! | Rude | 2014 | pop | G C D Em (6) | ~144 (songbpm) | Off-beat reggae chord chops; record in Db, capo 6. Borderline: chops rather than a full strum, like Three Little Birds. | US #1 (2014), UK #1 |
| The Wallflowers | One Headlight | 1996 | rock | G C B7 Em D (7) | ~104-108 | Acoustic strum under organ and slide. Record key D or C across sources, so the capo is 7 or 5; check against the upload. | Two Grammys (1998); Bringing Down the Horse, 6x Platinum |
| Lisa Loeb | Stay (I Missed You) | 1994 | pop | G Em7 Am7 G/B Cadd9 (6) | ~161 (songbpm) | Acoustic strum throughout; wordy phrasing may give irregular bars. | US #1 (1994) |
| The Beautiful South | Rotterdam (Or Anywhere) | 1996 | pop | Fmaj7 C Am G E7 D (0) | ~108 (Hooktheory) | Strummed acoustic, but sources disagree on 4/4 versus 6/8. | UK #5 (1996) |
| Third Eye Blind | Jumper | 1998 | rock | Fmaj7 C G Am Dsus2 (0) | ~91 (songbpm) | Acoustic strum through most of the song; Fmaj7 rather than F. | Third Eye Blind (1997), 6x Platinum album; single 1998 |
| The Beatles | Eight Days a Week | 1964 | rock | G A7 C Em D (7) | ~138 | Acoustic and electric chord strumming; capo 7 avoids the Bm of the open D version (L4). | US #1 (1965) |

#### Level 4 · First barre (F / Bm) (23)

| Artist | Title | Year | Genre | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|---|
| Eagles | Peaceful Easy Feeling | 1972 | rock | E A B7 F#m Esus4 (0) | ~143 (songbpm) | Open acoustic strum throughout; F#m in the chorus. | US #22 (1972); Their Greatest Hits, 38x Platinum |
| Rod Stewart | Maggie May | 1971 | rock | D A G Em F#m (0) | ~129 (songbpm) | 12-string acoustic strum through the verses; picked intro and mandolin outro are short. | UK #1 and US #1 (1971); Rolling Stone 500 |
| Traveling Wilburys | Handle with Care | 1988 | rock | D C G Bm B7 (0) | ~115 (songbpm) | Whole-band acoustic strum; harmonica fills only. A full B in the bridge would make it L5. | UK #21, US Mainstream Rock #2 (1988) |
| Crowded House | Weather with You | 1992 | rock | Em7 A D G F C (0) | ~94 (songbpm) | Acoustic Em7-Asus4 strum figure throughout; the F is in the bridge only. | UK #7 (1992) |
| Fleetwood Mac | Go Your Own Way | 1976 | rock | D A G Bm (3) | ~136 (songbpm) | Driving strummed guitars; record in F, so capo 3 gives D shapes. Lead solo at the end. | US #10 (1977); Rumours; Rolling Stone 500 |
| Spin Doctors | Two Princes | 1991 | rock | D A Bm G (0) | ~104-108 (Musicnotes 108) | Funky, syncopated electric chord strum on a four-chord loop. | US #7, UK #3 (1993) |
| The Verve | The Drugs Don't Work | 1997 | rock | C Am Em F G (0) | ~78 | Laid-back acoustic strum with strings throughout. | UK #1 (1997) |
| Travis | Why Does It Always Rain on Me? | 1999 | rock | D Bm G Em7 A (2) | ~108 (songbpm) | Acoustic strum after a short cello intro; record in E, capo 2. | UK #10 (1999); The Man Who, UK #1 |
| Oasis | Stand by Me | 1997 | rock | G D C Em Am F (0) | ~86-88 (Musicnotes) | Acoustic and electric strummed wall in G throughout. | UK #2 (1997) |
| The Beatles | You've Got to Hide Your Love Away | 1965 | rock | G D F C Dsus4 (0) | ~ (6/8 waltz feel) | Lennon's strummed 12-string acoustic in a clear triple feel. | Help! (UK and US #1 album, 1965) |
| The Kooks | She Moves in Her Own Way | 2006 | rock | G C D Am Bm Em (0) | ~154 (songbpm 77, double time) | Bouncy acoustic strum, with short picked licks between sections. | UK #7 (2006) |
| Smash Mouth | All Star | 1999 | pop | D A Bm G (4) | ~104 (Hooktheory; songbpm 104) | Electric chord strum on a four-chord loop; record in F#, capo 4 (capo 2 gives L5 shapes). | US #4 (1999); Shrek |
| Del Amitri | Roll to Me | 1995 | pop | D G A Em Bm7 (4) | ~150 (songbpm 75, double time) | Jangly chord strum; 2:13 long. Key inferred from charts (F#), capo 4. | US #10 (1995), UK #22 |
| The Jam | That's Entertainment | 1980 | rock | G Em Am F (3) | ~ | Acoustic strum carries the whole track; record in Bb, capo 3. | UK #21 (1981, import single) |
| George Michael | Faith | 1987 | pop | A D G E Bm F#m (2) | ~96 (songbpm) | Syncopated acoustic strum is the record's hook after a free-time organ intro; record in B, capo 2. | US #1 (1987), UK #2 |
| Amy Macdonald | This Is the Life | 2007 | pop | Am F C Em (4) | ~95 | Acoustic strum is the core part; record in C#m, capo 4. | UK #28 (2007); a number one in several European countries |
| Sheryl Crow | Soak Up the Sun | 2002 | pop | D A G Em F (2) | ~120 (songbpm) | Acoustic strum with band; record in E, capo 2. Sheets disagree on some chords. | US #17 (2002), US Adult Top 40 #1 |
| The Mamas & the Papas | California Dreamin' | 1965 | pop | Am G F E7sus4 E7 C (4) | ~112 (songbpm) | 12-string acoustic strumming throughout after a short picked figure; flute solo. Record in C#m, capo 4. | US #4 (1966); Rolling Stone 500 |
| Cat Stevens | Peace Train | 1971 | pop | C G F Am (0) | ~80-83 (sheet music) | Driving acoustic strum with fast changes; Cat Stevens' Wild World is already in. | US #7 (1971) |
| Avril Lavigne | Complicated | 2002 | pop | Am F C G (5) | ~78 (Hooktheory) | Acoustic strumming leads, with electric layers; record in F, capo 5. | US #2, UK #3 (2002) |
| Alanis Morissette | Hand in My Pocket | 1995 | pop | G Em7 Cadd9 F C (0) | 92 (Wikipedia) | Jangly strum over a G drone; harmonica only in the solo. | Canada #1, US Airplay #15 (1995); Jagged Little Pill |
| Toad the Wet Sprocket | All I Want | 1991 | pop | Am C G Em F D (5) | ~124 (songbpm) | Jangly strum with electric arpeggio layers; record in C, capo 5 (no capo needs Bb, L5). | US #15 (1992) |
| James Blunt | Bonfire Heart | 2013 | pop | C Em Am G F (0) | ~117 (songbpm) | Acoustic strum throughout. | UK #4 (2013) |

#### Level 5 · Barre chords (6)

| Artist | Title | Year | Genre | Shapes (capo) | Tempo | Why it fits | Popularity |
|---|---|---|---|---|---|---|---|
| The Kinks | Lola | 1970 | rock | E A D C B C#m (0) | ~ | Strummed acoustic throughout; the intro C-D-E is a strummed chord figure. Bridge has B and C#m. | UK #2, US #9 (1970); Rolling Stone 500 |
| Oasis | Half the World Away | 1994 | rock | C Fmaj7 Am D E Fm (2) | ~116 | Acoustic strum with keys; the Fm is T4. Royle Family theme. | B-side of Whatever (UK #3, 1994); The Royle Family theme |
| The Beatles | She Loves You | 1963 | rock | G Em Bm D C Cm (0) | ~150 | Fast electric chord strum; Cm is T4. | UK #1 (1963), US #1 (1964); UK best-selling single of the 1960s |
| The Beatles | All My Loving | 1963 | rock | Em A7 D Bm G C#m F#7 (0) | ~155 | The defining part is Lennon's fast triplet rhythm strum; C#m and F#7 are T4. | With the Beatles (UK #1 album, 1963) |
| KT Tunstall | Suddenly I See | 2005 | pop | D G A Bm F#m Gm (0) | ~100 (songbpm) | Driving acoustic strum throughout; Gm is T4 and no capo removes it. | UK #12 (2005); The Devil Wears Prada |
| The Fratellis | Chelsea Dagger | 2006 | rock | G D C B E (0) | ~155 (songbpm) | Driving full-band chord strum; sheets disagree on the verse B and E. | UK #5 (2006) |

#### Counts

| Level | Rock | Pop | v4 picks | In the app now | If all picks pass |
|---|---|---|---|---|---|
| 1 | 0 | 1 | 1 | 11 | 12 |
| 2 | 13 | 12 | 25 | 14 | 39 |
| 3 | 5 | 6 | 11 | 6 | 17 |
| 4 | 12 | 11 | 23 | 7 | 30 |
| 5 | 5 | 1 | 6 | 5 | 11 |
| All | 35 | 31 | 66 | 43 | 109 |

Over half the picks (36 of 66) sit at Levels 2–3, as asked. Level 4 is also large: many hits use one F, Bm or F#m, and a passing barre chord under 4% of chord time will compute lower. Level 1 gets only one pick: the app already has 11 songs there, and few hits use only A, D, E, Em and Am.

### Fallbacks, in order

| # | Artist | Title | Genre | Shapes (capo) | Level | Why it is a fallback |
|---|---|---|---|---|---|---|
| 1 | Gin Blossoms | Hey Jealousy | rock | C D Em G (2) | 2 | Jangly strum, but a signature lead riff is the hook. |
| 2 | One Direction | Story of My Life | pop | Am F C G (3) | 4 | Picked acoustic verses, strummed choruses. |
| 3 | The Kooks | Naive | rock | Em C G D D/F# (4) | 3 | Staccato, muted chord picking in the verse; strummed chorus. |
| 4 | Catfish and the Bottlemen | Kathleen | rock | G Em Am D C (7) | 3 | Fast electric strum, but riff hooks; capo 7 keeps it open. |
| 5 | The Everly Brothers | Wake Up Little Susie | rock | D F G A (0) | 4 | Strummed chordal intro figure; stop bars may unsettle the bar grid. |
| 6 | Crowded House | Don't Dream It's Over | rock | D Bm G A Em (1) | 4 | Organ is prominent and the intro is picked; strummed verses. |
| 7 | Jack Johnson | Banana Pancakes | pop | G Am D7 C7 Bm Em (0) | 4 | Syncopated chord strum with riff fills; a third Jack Johnson song. |
| 8 | Primal Scream | Movin' on Up | rock | G D C Am (5) | 4 | Stones-style acoustic strum; chart sources conflict on capo and the Bb/Ab passing chords. |
| 9 | Ocean Colour Scene | The Day We Caught the Train | rock | Em D G C A B (0) | 5 | Strummed, but riff and lead lines and many chord colours; charts disagree on the key. |
| 10 | Green Day | When I Come Around | rock | G D Em C (0) | 2 | Palm-muted power-chord strum with a picked lead line; needs half-step-down tuning (capo gives L4). |

### Notable rejections

| Song | Reason |
|---|---|
| Mr. Big, To Be with You | The last chorus modulates from E to G. |
| Neil Diamond, Cracklin' Rosie | Key changes; players slide the capo up mid-song. |
| The Cranberries, Dreams | The chorus lead-out moves key, and the chiming effects part is only borderline strumming. |
| R.E.M., It's the End of the World as We Know It | A fast, arpeggiated jangle, not a strum. |
| The Doobie Brothers, Listen to the Music | A syncopated hammer-on chord riff, and the bridge is unclear. |
| Sheryl Crow, All I Wanna Do | A slide- and groove-led record with spoken verses. |
| Sam Fender, Seventeen Going Under | A lead-guitar riff defines it. |
| America, Sister Golden Hair | The slide-guitar intro riff is the hook. |
| The Rembrandts, I'll Be There for You | The 12-string jangle riff is the hook. |
| John Mellencamp, Pink Houses | A signature riff opens it, and the record may be in open G. |
| Bob Marley, Redemption Song | Built around a single-note bass riff between lines. |
| Of Monsters and Men, Little Talks | The horn riff is the hook. |
| Bruno Mars, The Lazy Song | A reggae skank with whistling; MAGIC!'s Rude was kept as the one off-beat chop song. |
| Shawn Mendes, Treat You Better; Ed Sheeran, Lego House; Simon & Garfunkel, Homeward Bound | Picked or hybrid picked-and-strummed parts. |
| Corinne Bailey Rae, Put Your Records On; The Lovin' Spoonful, Daydream | The guitar is light and not the lead part (strings or piano). |
| James Bay, Hold Back the River; Train, Drive By; Paolo Nutini, New Shoes | Riffy or palm-muted 16th parts, or the guitar part could not be confirmed. |
| Wheatus, Teenage Dirtbag | A picked verse and a power-chord chorus. |
| The Waterboys, Fisherman's Blues | Fiddle and mandolin lead the arrangement. |
| Oasis, Whatever | A 6:21 string-led record whose later section may move key. |
| Blur, Tender | 7:42 long, and the only upload found was unofficial. |
| Jack Johnson, Upside Down; Michelle Branch, Everywhere; Jack Johnson, Sitting, Waiting, Wishing | No Topic or album-length official upload was found (video edits or unofficial channels only). |
| Third Eye Blind, Semi-Charmed Life; Goo Goo Dolls, Slide; Snow Patrol, Run; Kings of Leon, Sex on Fire | Not researched further: picked riffs, alternate tunings or delay arpeggios on the record. |

### Uploads and doubts

- **Check method.** Every row passed oEmbed (200) and the embed-page playability check with a github.io Referer (so it is neither age-restricted nor embed-blocked), and is under 600 s. Unlike v3, the upload descriptions were not read: the installed yt-dlp (2025.08.11) cannot fetch full metadata for these videos ("not available on this app"), and a direct watch-page read was not used. Topic uploads are label deliveries of the studio recording; titles and durations were compared with the album track instead.
- **Non-Topic uploads (official artist or label channels).** Handle with Care and End of the Line (official visualizers), 3AM, Laid (one of several video versions), Small Town, You Belong with Me, Mine, You're Still the One (single edit), Home, Rude, Hanging by a Moment and Don't Dream It's Over (music videos), Stick Season, We Are Never Ever Getting Back Together and Complicated (lyric videos), Last Kiss and Me and Julio (official audio), What I Got (music video), and Stubborn Love. A music video can carry a different intro or edit, so check the grid on these first.
- **Versions rejected.** Taylor's Version re-recordings; the J. Frank Wilson original of Last Kiss; Topic commentary tracks (Taylor Swift), the "POP Mix" of Mine, "The Matrix Mix" of Complicated, the 2004 remix of You're Still the One, the 2022 Mix of Small Town, and the 1988 re-recording of Rockin' All Over the World.
- **Duration doubts.** All Star (230 s against a ~3:20 album track; the 204 s Topic copy is not embeddable), This Is the Life (188 s video against ~3:04), and 3AM (227 s video).
- **Strum doubts.** Rude (off-beat chops, like Three Little Birds), Me and Julio (percussive, syncopated), Stick Season (first verse picked), Cat's in the Cradle (picked intro), Faith (syncopated strum after a free-time organ intro), One Headlight (organ and slide on top), Lola (the intro is a strummed chord figure), Hanging by a Moment (distorted eighth-note strumming on a tuned-down record).
- **Chord or capo doubts.** Hold My Hand (Bm or F#m may appear, which would make it L4), Who'll Stop the Rain (Bm in some charts), Handle with Care (B or B7 in the bridge), One Headlight (record key D or C, so capo 7 or 5), Roll to Me (key inferred from charts), Soak Up the Sun (sheets disagree), Chelsea Dagger (the verse B is in one sheet only), and the Songbird instrumental bar counts.
- Expected levels are chord-sheet drafts; the app computes its own from the automatic chart.
