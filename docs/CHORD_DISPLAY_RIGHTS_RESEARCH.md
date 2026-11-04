# Can Strum Along show chord charts without a publisher licence?

**Researched 27 October 2026** from public primary sources. This follows issue [#56](https://github.com/dcromp/music-os/issues/56) and the two earlier notes, which are still on unmerged branches:
- `docs/YOUTUBE_CHORDIFY_TOS_RESEARCH.md` on `refs/heads/claude/research-youtube-tos-98a87a`
- `docs/CLEAN_CHORD_SOURCE_RESEARCH.md` on `refs/heads/claude/research-clean-chord-source-3600f4`

> **Not legal advice.** This is product research. It does not replace advice from a Norwegian music or IP lawyer.
>
> - **CONFIRMED**: read on the primary source.
> - **REPORTED**: seen only in a secondary source, so unconfirmed.
> - **NONE PUBLIC**: no public figure was found.
> - **(inference)**: our own reasoning.
> - Dates are those shown on each source. "acc." means accessed 2026-10-27, for pages that show no date.
> - We downloaded no media, contacted no one and submitted no forms.

**What the product shows:** chord names on a beat and bar grid, timed to the official YouTube embed, with section labels (Verse, Chorus), Strum Along's own suggested strum patterns, and **no lyrics**.

## Executive summary

- **Chords only: legally grey and untested. No court anywhere has ruled on a bare chord chart.**
  - **Generic harmony is not protected.** The US Copyright Office, the Second Circuit (*Sheeran*, 2024) and the English High Court (*Sheeran v Chokri*, 2022) all treat common progressions such as I–V–vi–IV as building blocks no one owns.
  - **A whole-song chart is different, but only for distinctive songs.** It copies the full sequence of chords, where they change, and the song's form. For a song with distinctive harmony, it could count as reproducing a protected "part" of the work under the EU test (*Infopaq* 2009; *Mio/konektra*, 4 Dec 2025: creative elements "reproduced in a recognisable manner").
  - **Norway and the UK go further.** Both expressly cover changed forms of a work: åndsverkloven § 3 ("i endret skikkelse … i annen teknikk") and the UK act (CDPA s 21(3)(b)), which makes a "transcription" of a musical work an adaptation.
  - **No exception fits.** Teaching and quotation exceptions do not cover a paid consumer app.
- **Industry practice treats chord charts as licensable.**
  - **Fender** signed deals with Sony/ATV, Warner Chappell, Kobalt and BMG to pay for "the use of their chords" (press release, 22 Oct 2019).
  - **Ultimate Guitar** says it licenses "thousands of publishers", plus the Harry Fox Agency (HFA).
  - **Songsterr** pays "almost half of our revenue as royalties". Yousician and Songsterr block songs where they lack a publisher licence.
  - **Chordify is the outlier.** It claims no chord licences, argued in 2014 that progressions aren't copyrightable, and runs a takedown process.
  - **Publishers have enforced against tab sites.** US publishers shut tab and lyric sites in 2005–07 with demand letters, not lawsuits.
- **Adding lyrics makes the answer clear: you need a licence.**
  - Lyrics are a separate literary work that is almost always original enough to be protected, and as few as 11 words can infringe (*Infopaq*).
  - Most publisher enforcement has been about lyrics. One lyrics-site operator faced a USD 6.6M default judgment (REPORTED).
  - Lyrics come from LyricFind or Musixmatch, or direct from publishers, under a deal separate from any chord deal.
- **Cost: almost no public prices exist.** Every route is quote-only. The only published numbers are:
  - Songsterr's royalty share, "almost half" of revenue, for full tab;
  - a Latvian collecting society tariff: 12% of revenue for music, plus 6% to the lyricist when lyrics are added, with at least EUR 17 per work.

  Our rough estimate for a 40–100 song catalogue at small scale is **low thousands to low tens of thousands of EUR a year, driven by minimum guarantees rather than revenue share**. Adding lyrics probably adds a separate minimum on top. This is **an estimate, not a quote** (§ 1.4).
- **Recommendation (inference):**
  - Keep the private and small free pilot chords-only.
  - Before charging, take the questions in § 5 to a Norwegian lawyer.
  - Approach publishers or an aggregator for a chords-only licence. Leave lyrics out until the chords deal is in place.

## 1. Cost evidence (read first)

### 1.1 Public tariffs and rate cards

| Item | What it says | Status |
|---|---|---|
| **AKKA/LAA (Latvia)** [online sheet-music and lyrics tariff](https://www.akka-laa.lv/storage/ckeditor/minimum_tariffs_sheet_music_online.pdf), 19 Oct 2020 | Online, with end-user revenue: **music alone 12% (composer)**; music with lyrics 6% composer + 6% lyricist; **minimum EUR 17 per work**. Without revenue: EUR 0.43 per line of music, EUR 0.43 per line of lyrics. | **CONFIRMED.** The only published collecting society tariff we found that prices music and lyrics display separately. It covers only that society's repertoire, so it is a benchmark, not a route. |
| **TONO (Norway)** [online tariffs](https://en.tono.no/customers/online/) (acc.) | Apps pay 12% of turnover, with minimums for streaming (5 øre per minute) and downloads (82 øre per song). | **CONFIRMED.** But these cover performing and communicating *audio*. Nothing on chords, sheet music or lyrics. If the official embed supplies the audio, YouTube licenses it (inference). A TONO price for chord display: **NONE PUBLIC**. |
| **NCB, Koda, STIM, Teosto, GEMA, PRS/MCPS** | No online tariff for displaying chords, sheet music or lyrics found. | **NONE PUBLIC.** The Swedish publishers' association says print rights usually sit with the publisher. Without permission you may not "lägga ut noter och sångtexter på hemsidor" (post sheet music and lyrics on websites) ([Musikförläggarna brochure](https://musikforlaggarna.se/wp-content/uploads/Upphovsratt-och-Noter.pdf), 2013). |
| **Kopinor (NO), Copydan (DK), Bonus (SE), PMLL (UK)** | Licences for copying in schools, churches and choirs, e.g. Kopinor's church agreement caps sheet music at "15 %, men maksimum 10 sider" ([Kopinor](https://kopinor.no/wp-content/uploads/2026/02/Sentralavtale-Norges-Kristne-Rad.pdf), 2026). | **CONFIRMED**, but none covers a commercial consumer app. |
| **IMPEL/IMPF Digital Licensing Handbook 2026** ([PDF](https://www.impforum.org/wp-content/uploads/2026/10/IMPEL-IMPF-Digital-Licensing-Handbook-2026.pdf), Oct 2026; linked from Musikkforleggerne) | Typical deals pay "the greater of x% of revenue or €y per stream", and "15–17% is pretty standard for music streaming". Karaoke costs more because it includes lyric rights. For start-ups, flat fees or minimum guarantees are the "least-worst option". | **CONFIRMED.** Lists Yousician and Fender Play as licensees, but says nothing about chord display. |
| **Hal Leonard permissions** (sl.halleonard.com) | A portal for case-by-case requests. | Portal **CONFIRMED**; fees **NONE PUBLIC**. Authors report lyric reprint fees of about USD 100–300 for small book print runs (REPORTED). That is not an app price. |
| **Musicnotes** [publisher page](https://apps.musicnotes.com/publishers/) (acc.) | Says it has paid "more than $100 million" in royalties. | Per-copy rate: **NONE PUBLIC**. |
| **HFA tab and lyric deals** (Ultimate Guitar, 2010; MXTabs, 2007) | Ultimate Guitar: [HFA press release](https://www.scoringnotes.com/wp-content/uploads/2023/12/HFAUltimateGuitar_20100406_Final.pdf), 6 Apr 2010, publishers opt in. MXTabs: an advertising revenue-share model (REPORTED). | Rates: **NONE PUBLIC**. |

### 1.2 Deal terms reported for comparable apps

| Service | Evidence | Status |
|---|---|---|
| **Songsterr** | "We have licenses with original music creators and pay out almost half of our revenue as royalties" ([help](https://www.songsterr.com/help), acc.). This covers full tab, which shows every note. | **CONFIRMED.** The only public revenue share from a tab or chord service. |
| **Ultimate Guitar / Muse Group** | Licences with "thousands of publishers" plus HFA ([licensing page](https://www.ultimate-guitar.com/article/blog/licensing), undated). | Terms **NONE PUBLIC** (the company is private). |
| **Fender (Fender Songs)** | Deals with Sony/ATV, Warner Chappell, Kobalt and BMG to pay for "the use of their chords"; LyricFind supplies lyrics separately (press release of 22 Oct 2019, read via [American Songwriter's reprint](https://americansongwriter.com/fender-launches-new-app-fender-songs-offers-immersive-playing-experience-with-apple-music/) because fender.com returned 403). | Deals **CONFIRMED** (reprinted release); terms **NONE PUBLIC**. |
| **Yousician** | Songs are unavailable "due to licensing agreements with the publishers" ([support](https://support.yousician.com/hc/en-us/articles/360000758937), acc.). | Terms **NONE PUBLIC**. |
| **JustinGuitar** | Forum moderators say songs are licensed "with all legal permissions and royalties paid". The Songs app is run by Musopia. | **REPORTED** only; terms **NONE PUBLIC**. |
| **Chordify** | Claims no chord licences (see § 3). | n/a |
| **LyricFind** (lyrics) | Pays rights holders in proportion to views; pricing by [enquiry form](https://www.lyricfind.com/products/lyric-display). | **Quote only.** |
| **Musixmatch** (lyrics) | A user quoted Musixmatch's terms in 2015: no data licence "for less than USD $25,000", and at least USD 1.40 per 1,000 views ([forum](https://redmine.audacious-media-player.org/issues/502), 14 Oct 2015). | **REPORTED**, 11 years old. Current pricing pages blocked automated reading. |

### 1.3 Is a chords-only licence cheaper than chords with lyrics?

- **No route publishes a chords-only price.** Hal Leonard, Muse Group, the major publishers, LyricFind and Musixmatch are all quote-only. **NONE PUBLIC.**
- **The rights are sold separately, though.**
  - Chords and arrangements are licensed by the composition's publisher. Lyrics are often licensed through an aggregator; Fender used publishers for chords and LyricFind for lyrics.
  - The Latvian tariff prices the lyrics as an extra 6% share on top of the music.
  - So a chords-only deal avoids the lyrics licence entirely, along with its minimums (inference).
- **Hal Leonard Connect is not a display licence.** [Announced 6 Aug 2026](https://www.mu.se/posts/hal-leonard-connect), it is an API and storefront for retailers *reselling* Hal Leonard sheet music. It does not license chord display in someone else's app (CONFIRMED).

### 1.4 Rough order of magnitude for 40–100 songs at small scale (ESTIMATE)

**There is no public figure for this.** Below is our own arithmetic from the few benchmarks above, for budgeting only:

- **Revenue share:** expect about 10–20% of the revenue the songs earn for chords only. That range comes from the Latvian 12% and IMPEL's 15–17%. Songsterr's "almost half" covers note-for-note tab, which is a heavier use, so treat it as an upper bound.
- **Minimums dominate at small scale.**
  - The Latvian floor of EUR 17 per work comes to EUR 680–1,700 for 40–100 songs. That tariff doesn't say how often the floor applies.
  - IMPEL says start-ups usually get flat fees or minimum guarantees. Publishers' minimums and advances are not public.
  - **Our estimate (inference): low thousands to low tens of thousands of EUR a year across the publishers involved, before legal fees.** The minimums would matter more than the percentage.
- **Lyrics would add a separate deal.** The only figure is the reported 2015 Musixmatch floor of USD 25,000 a year, which alone could exceed the chord costs above. Unconfirmed and dated.
- **Coverage risk:** one song can involve several publishers. A song is usable only once every share is cleared, and some rights holders refuse or restrict songs by country.

## 2. The law

### 2.1 Norway: åndsverkloven 2018

Sources: [LOV-2018-06-15-40](https://lovdata.no/dokument/NL/lov/2018-06-15-40), as amended to LOV-2024-12-13-76, in force 1 Jan 2025 (acc.); [Prop. 104 L (2016–2017) ch. 3](https://www.regjeringen.no/no/dokumenter/prop.-104-l-20162017/id2547943/?ch=3), 5 Apr 2017. All read on the primary source.

- **§ 2, what counts as a work:** a work must be "uttrykk for original og individuell skapende åndsinnsats" (an expression of original and individual creative effort). The list includes:
  - "(a) tekster av alle slag" (texts of all kinds), which covers lyrics;
  - "(d) musikkverk, med eller uten tekst" (musical works, with or without text).
- **§ 3, the exclusive rights:** making copies and making the work available to the public. These rights cover the work "i opprinnelig eller endret skikkelse … i annen litteratur- eller kunstart eller i annen teknikk" (in its original or a changed form … in another art form or technique).
  - **So Norway has an express right over changed forms, which EU law does not harmonise.**
  - Writing a song out as chord notation is a use "i endret skikkelse", *if* it carries over a protected element (inference).
- **§ 6, adaptations:** a person who adapts a work owns their version, but "kan ikke råde over det i strid med opphavsretten til originalverket" (may not use it against the copyright in the original).
  - Only a "nye og selvstendige verk" (new and independent work) escapes the original copyright.
  - A chord chart of a specific song is not a new, independent work (inference).
- **Prop. 104 L on the originality threshold:**
  - It adopts the EU test, "author's own intellectual creation", and cites Rt. 2007 s. 1329.
  - Protection reaches as far as the creative effort reaches, decided case by case.
  - TONO's consultation response called it a common misconception that adding new elements avoids infringing the original.
- **No exception fits a commercial app:**
  - **Quotation (§ 29):** allowed only "i den utstrekning formålet betinger" (to the extent the purpose requires).
  - **Teaching (§§ 43–47):** these provisions cover teaching institutions, anthologies and collective licences, not a paid consumer app (inference).
- **Case law:** we found **no Supreme Court (Høyesterett) judgment on copying melody, harmony or an arrangement.** Lower courts were not searched (Lovdata Pro needed).

### 2.2 EU: InfoSoc directive 2001/29 and the EU Court of Justice (CJEU)

- **Directive:** [2001/29](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32001L0029) (acc.).
  - **Art. 2:** reproduction "in whole or in part".
  - **Art. 3:** making available to the public.
  - **No general adaptation right.** That is left to national law and the Berne Convention (inference from the text).
  - **Art. 5(3)(a):** the teaching exception applies only "to the extent justified by the non-commercial purpose".
- **The originality test, all read on EUR-Lex:**
  - ***Infopaq*, C-5/08 (16 Jul 2009):** a part of a work is protected if it expresses "the author's own intellectual creation" (para 39). An 11-word extract can be enough (para 48).
  - ***Painer*, C-145/10 (1 Dec 2011):** the author's "free and creative choices".
  - ***SAS Institute*, C-406/10 (2 May 2012):** ideas and functionality are not protected (para 40).
  - ***Levola*, C-310/17 (13 Nov 2018):** the work must be "identifiable with sufficient precision and objectivity".
  - ***Cofemel*, C-683/17 (12 Sep 2019) and *Brompton*, C-833/18 (11 Jun 2020):** choices "dictated by technical considerations, rules or other constraints" are not creative.
- **Infringement: *Mio/konektra*, C-580/23 and C-795/23 (4 Dec 2025):** infringement requires that "creative elements of the protected work have been reproduced in a recognisable manner".
  - This is now the question for a chord chart. Does it recognisably reproduce the song's creative harmonic and structural choices?
  - The answer depends on the song (inference).
- ***Pelham*, C-476/17 (29 Jul 2019):** about sampling the *recording*, so of little relevance here. Its point that a quotation must enter into "dialogue" with the work also rules out quotation as a defence for a full play-along chart.

### 2.3 United States

- **What the statute and regulations say:**
  - **17 U.S.C. § 101:** a "musical arrangement" is a derivative work.
  - **37 C.F.R. § 202.1:** short phrases and common property cannot be registered.
- **What the Copyright Office says:** [Compendium (Third) ch. 800](https://www.copyright.gov/comp3/chap800/ch800-performing-arts.pdf) (version of 28 Jan 2021).
  - Musical authorship includes "melody, rhythm, harmony, and lyrics" (§ 802.3).
  - "Chord symbols based on standard chord progressions" are common property (§ 802.5(A)).
  - A chart consisting only of C–Am–Dm–G is "both standard and too short" (§ 802.6(C)(1)).
  - **Caveat:** these passages are about registering the chart-maker's own work, not about whether copying a song's chords infringes.
- **Cases, all read on the primary source:**
  - ***Skidmore v. Led Zeppelin*, 952 F.3d 1051 (9th Cir. en banc, No. 16-56057, 9 Mar 2020):** common musical elements "belong in the public domain".
  - ***Gray v. Hudson* (9th Cir., 10 Mar 2022):** an ostinato built entirely from commonplace elements is not protected, and the USD 2.8M verdict was vacated.
  - **[*Structured Asset Sales v. Sheeran*](https://www.govinfo.gov/content/pkg/USCOURTS-ca2-23-00905/pdf/USCOURTS-ca2-23-00905-0.pdf) (2d Cir., 1 Nov 2024):** the claim was about "Let's Get It On". Its four-chord progression and syncopated harmonic rhythm, taken together, are not original enough to protect. "Basic musical building blocks like notes, rhythms, and chords are generally not copyrightable."
    - The ruling concerns that specific *combination*. It does not hold that a whole song's harmony can never be protected.
- **Arrangements:** *Woods v. Bourne* (2d Cir. 1995) requires more than routine variations for an arrangement to be original (REPORTED).

### 2.4 United Kingdom

- **The statute** ([CDPA 1988](https://www.legislation.gov.uk/ukpga/1988/48/section/3), acc.):
  - **s 3(1):** a musical work excludes the words, and lyrics are a separate literary work.
  - **s 16(3):** restricted acts cover "the work as a whole or any substantial part of it".
  - **[s 21(3)(b)](https://www.legislation.gov.uk/ukpga/1988/48/section/21):** an adaptation of a musical work means "an arrangement or **transcription**" of it.
- **The cases:**
  - **[*Hyperion v Sawkins*](https://caselaw.nationalarchives.gov.uk/ewca/civ/2005/565) [2005] EWCA Civ 565 (19 May 2005):** music is not just "the actual notes in the score". Figured bass and performance directions counted.
  - **[*Brooker v Fisher*](https://caselaw.nationalarchives.gov.uk/ewca/civ/2008/287) [2008] EWCA Civ 287:** the organ part was "a distinctive and significant contribution to the overall composition". The House of Lords judgment of 2009 was not read.
  - **[*Sheeran v Chokri*](https://www.judiciary.uk/wp-content/uploads/2022/07/Sheeran-v-Chokri-judgment-060422.pdf) [2022] EWHC 827 (Ch) (6 Apr 2022):** applies *Infopaq* to "substantial part". I–V–vi–IV is "so commonplace in pop music" that it can't be said to be copied from any one song.

### 2.5 Applied to Strum Along's chart (inference)

1. **What the chart copies.** It captures the song's chord sequence, where the chords change, its form and its timing. It copies no melody, lyrics or recording.
   - Harmony is part of the musical work in all four legal systems.
   - Common progressions taken alone are not protected.
2. **Generic songs versus distinctive songs.**
   - **Generic harmony:** for a song built on a stock loop, the chart probably takes nothing protected.
   - **Distinctive harmony:** for a song with distinctive passing chords, modulations or structure, a full-song chart could be a recognisable reproduction of creative elements. In Norway and the UK it could also be a changed form or transcription.
   - Neither point has been tested in court.
3. **What doesn't change the answer.**
   - **Strum patterns:** they are the app's own, and generic ones are building blocks anyone may use. They neither cause nor cure infringement.
   - **Section labels and bar timestamps:** these are short words and facts.
   - **Syncing to the official embed:** this copies no recording. YouTube's own terms are covered in the earlier note.
4. **The risk is commercial as much as legal.** Publishers treat chord and tab display as licensable "print" use and have enforced against such sites before. At commercial scale, the realistic risk is a demand letter or a removal request, not a ruling.

## 3. Industry practice and disputes

| Service | What it licenses | Source |
|---|---|---|
| **Ultimate Guitar** | Tab, chords and lyrics from "thousands of publishers". The HFA deal covers "lyrics display, title search and tablature display". Its terms say user tabs are allowed only for "compositions that we have licensed" (§7.7a). | [Licensing page](https://www.ultimate-guitar.com/article/blog/licensing) (undated); HFA release (6 Apr 2010); [ToS](https://www.ultimate-guitar.com/about/tos.htm) (acc.). CONFIRMED. |
| **Songsterr** | Tab, licensed per publisher and blocked by country where unlicensed. | [Help](https://www.songsterr.com/help) (acc.). CONFIRMED. |
| **Fender Songs / Fender Play** | Chords from Sony/ATV, Warner Chappell, Kobalt and BMG; lyrics through LyricFind. | Press release of 22 Oct 2019 (reprint). Fender Play's own publisher list: not found. |
| **Yousician** | Publisher licences that vary by country. No press release names its deals. | [Support](https://support.yousician.com/hc/en-us/articles/360000758937) (acc.). CONFIRMED. |
| **JustinGuitar** | Says royalties are paid; the Songs app is run by Musopia. | Community forum. REPORTED. |
| **Chordify** | Its [terms](https://chordify.net/pages/terms-and-conditions/) claim no chord licences. §12 is a takedown process, and §8 limits lyrics to personal, non-commercial use. Lyrics via LyricFind (Jul 2023). It argued in 2014 that progressions are not copyrightable. | Terms CONFIRMED (acc.); the rest REPORTED. |

**Disputes:**
- **2005: tab site crackdown.** In December 2005 the US Music Publishers' Association (MPA), backed by the National Music Publishers' Association (NMPA), threatened tab and lyric sites ([The Register](https://www.theregister.com/2005/12/19/mpa_threatens_song_lyric_websites/), 19 Dec 2005; REPORTED). MXTabs went offline and later licensed through HFA and Musicnotes.
- **2007: the publishers' own records.** The MPA's [board minutes of 19 Apr 2007](https://www.mpa.org/wp-content/uploads/2011/12/meeting_minutes_28.pdf) record HFA starting to license guitar tabs with Musicnotes. The [minutes of 25 Oct 2007](https://www.mpa.org/wp-content/uploads/2011/12/meeting_minutes_31.pdf) record the NMPA asking for money toward "shutting down guitar tab websites". CONFIRMED.
- **OLGA (the On-line Guitar Archive):** an HFA complaint in 1998, then an NMPA and MPA letter in 2006 that removed about 34,000 tabs. REPORTED.
- **We found no court filing against any tab site.** They were all closed by demand letters or settled by licensing.
- **Lyrics enforcement:**
  - **LiveUniverse:** in the case brought by Peermusic, Warner/Chappell and Bug Music (C.D. Cal., filed 2009), the court ordered four lyrics sites shut ([NMPA](https://www.nmpa.org/?p=1117), 11 Aug 2010). A USD 6.6M default judgment followed in 2012 (REPORTED).
  - **50 lyric sites:** in November 2013 the NMPA sent takedown notices to 50 sites, including the chord and tab sites e-chords.com and guitaretab.com, but not Ultimate Guitar (REPORTED list).
  - **Rap Genius:** the NMPA and Rap Genius reached an [agreement](https://www.nmpa.org/nmpa-rap-genius-announce-agreement/) on 6 May 2014. CONFIRMED.
- **Nordic:** we found no Norwegian or Nordic enforcement against chord sites, and no licensed Norwegian chord site.
  - Musikkforleggerne, the Norwegian music publishers' association, advises on graphic rights but runs no licensing scheme (acc.).

## 4. Licensing routes

| Route | Covers chords only? | Covers lyrics? | Price |
|---|---|---|---|
| **Direct publisher deals** (Sony Music Publishing, UMPG, Warner Chappell, Kobalt, BMG, then the independents) | Yes, as Fender did in 2019 | Sometimes; often via an aggregator | Quote only |
| **Hal Leonard permissions** (Muse Group) | Case by case, for catalogue Hal Leonard administers | Lyric reprints | Quote only |
| **Hal Leonard Connect** (6 Aug 2026) | No: it is for retailers reselling sheet music | — | Not disclosed |
| **HFA** (owned by SESAC since 2015, REPORTED) | Historically tab and lyric display with publisher opt-in (Ultimate Guitar 2010) | Historically yes | Not disclosed. Whether it still offers this is unverified. |
| **LyricFind** | No chords product | Yes: static and time-synced | Quote only |
| **Musixmatch** | No chords mentioned | Yes | Quote only (2015 report: USD 25,000 a year minimum) |
| **TONO / NCB** | No: audio performance and mechanical rights | No | 12% of turnover, for audio the app plays itself |
| **Kopinor and the other copying societies** | No: copying within organisations | No | n/a |
| **Musikkforleggerne** | Advice and referrals only | Advice only | n/a |

Not checked: the print-licensing pages of Alfred/Peaksware, Wise Music and BMG.

## 5. For Strum Along

### 5.1 Risk ladder (inference)

| Step | What's shown | Legal position | Practical risk | Licence |
|---|---|---|---|---|
| 0 | Private use by the founder | Private use; not a public making available | Negligible | None |
| 1 | Small free group, chords only, stock-progression songs | Probably takes nothing protected | Low | None for now; keep a takedown process like Chordify's |
| 2 | Free or paid public app, chords only, full-song charts | Grey: depends on each song's harmony; untested | Medium: a demand letter or app-store complaint at scale | Publisher chord licences recommended before charging |
| 3 | Paid app, chords only, with publisher licences | Covered for the licensed share of each song | Low; some songs blocked | Direct or aggregated publisher deals (§ 4) |
| 4 | Chords plus a few lyric lines (titles, hooks) | Even 11 words can infringe (*Infopaq*) | High without a licence | A lyrics licence is needed |
| 5 | Chords plus full time-synced lyrics | Clear reproduction of the literary work | Very high without a licence; this is where publishers have sued | LyricFind, Musixmatch or a publisher licence, plus the chord deal |

**Practical steps (inference):**
- Prefer songs with simple harmony for the launch catalogue.
- Label charts as Strum Along's own simplified practice arrangement.
- Show no lyrics and no melody.
- Add a takedown contact and process.
- Record the publishers for each song now, so licence requests are quick later.

### 5.2 Questions for a Norwegian music or IP lawyer

1. Under åndsverkloven §§ 2, 3 and 6, does a timed chord chart (chords, harmonic rhythm, section form, no melody or lyrics) reproduce the musical work "i endret skikkelse"? Does the answer differ for stock progressions and distinctive harmony?
2. Is there Norwegian case law, at any court level, on harmony, arrangements or chord or tab sheets? How would *Mio/konektra* (C-580/23) apply in Norway?
3. For a free beta with a small closed group, is the risk different from a paid launch? Does Norwegian law treat a closed invite-only group as "allmennheten" (the public)?
4. Which law applies to users in the US and UK, and does the app need to block countries or songs?
5. In Norway, who grants graphic and print display rights: each publisher, its Norwegian sub-publisher, or anyone else? Can Musikkforleggerne point us to a collective route?
6. What should a chords-only licence say: scope (display, time-synced, simplified arrangement), territory, minimum guarantees, how the publisher shares in each song are split, and takedown duties?
7. If lyrics are added later, is a LyricFind or Musixmatch licence enough for synced display in Norway, the EU, the US and the UK? Does it cover display next to a YouTube embed?
8. How should the terms and the app describe charts ("Strum Along's own simplified arrangement") and the takedown process to reduce risk?
9. What exposure would the founder face personally before incorporating a company, and how would an AS (Norwegian limited company) change that?

## Gaps

- We read no judgment on a bare chord chart, because none was found. Lower Norwegian courts were not searched.
- The House of Lords *Fisher* judgment and the *Hadley*, *Coffey*, *Swirsky* and *Griffin* cases were not opened.
- US fair use was not analysed.
- The current terms of LyricFind, Musixmatch, HFA and the major publishers' print departments, and the Alfred, Wise and BMG print pages, could not be confirmed.
- Every price beyond the AKKA/LAA tariff and Songsterr's share is quote-only or our estimate.
