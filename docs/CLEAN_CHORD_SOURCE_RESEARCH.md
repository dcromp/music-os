# A clean source for Strum Along's chord timings

**Researched 27 October 2026.** This is product research from public primary sources.

> **Not legal advice.** Nothing here replaces advice from a Norwegian lawyer or a decision by YouTube's policy team.
>
> - Claims we could not confirm from a primary source are marked **UNCONFIRMED**.
> - Our own reasoning is marked **(inference)**.
> - Every citation gives the date shown on the page, or "acc." (accessed 2026-10-27) when the page shows none.
> - We downloaded no media, contacted no one and submitted no forms.

This note follows [YOUTUBE_CHORDIFY_TOS_RESEARCH.md](YOUTUBE_CHORDIFY_TOS_RESEARCH.md), which covers the YouTube rules, how Chordify works and how Strum Along's playback already complies. Read that first; this note does not repeat it. It also builds on [SONG_ACCESS_FEASIBILITY.md](SONG_ACCESS_FEASIBILITY.md).

## Executive summary

**Is there a clean way? Yes, but not by downloading audio from YouTube.** The clean route is to build each chart without ever copying YouTube's audio, and to time it against the embed's own clock:
- A person, at first the founder, taps the beat and bar grid along to the official player.
- The chords come from the player's own guitar, picked up by the microphone while they wear headphones, or are entered by hand.

A paid catalogue will also need publisher licences to display the chord arrangements, whatever the timing source.

- **EU/EEA copyright law does not rescue the yt-dlp workflow.** We checked four points:
  - **Norway has no text-and-data-mining (TDM) exception yet.** The directive's EEA incorporation is still pending, and the bill that would add one (Prop. 41 LS (2025–2026), proposed § 50 e) is still in committee.
  - **Even the EU rule would not fit.** Art. 4 of directive 2019/790 needs *lawful access* and no rights-holder opt-out. Deleting the audio is not the test; the article lets copies be *kept* as long as needed.
  - **The labels have opted out:** UMG (all TDM), WMG (machine-learning uses) and Sony (listed by the music-industry body IFPI).
  - **Contracts can override Art. 4.** It is not among the exceptions protected from contracts by Art. 7(1). YouTube's developer contract is under California law and has no "as permitted by law" carve-out.
  - **Downloading may itself be circumvention.** German courts held, finally in October 2025, that youtube-dl helps users get around YouTube's technical protection measures.
- **No public way to get YouTube's written approval exists.** No page describes how to request the "prior written approval" in Developer Policy III.E.1. The only channel is the free text of the API compliance audit form. YouTube's Terms also need consent from "the respective rights holders". This route is unlikely and slow.
- **Analysing the audio while it plays is blocked.**
  - **Technically:** the embed is a cross-origin iframe, so the page can't reach its media element. The Web Audio spec says such a source "MUST output silence". iOS Safari can't capture tab or system audio.
  - **By policy:** III.I.7 forbids isolating the audio.
- **No licensed chord-timing source covers mainstream songs for us today.**
  - **Songle** (run by AIST, Japan's national research institute) is the only one keyed to YouTube URLs. Commercial use needs AIST's agreement first.
  - **Chordify and Songsterr** have YouTube-synced data but no published third-party licence.
  - **Hooktheory and Ultimate Guitar** have no timings for third parties (Hooktheory's are capped excerpts) and restrictive terms.
  - **McGill Billboard** is free (CC0) with expert timings, but aligned to McGill's own copies of the recordings.
- **Licensed audio exists only under bespoke enterprise deals.** Store downloads are personal-use only, and Apple expressly bans "analysis". Creative Commons and artist-direct music is clean, but not familiar rock or pop.
- **Recommendation:** adopt **people tapping along to the embed, with chords heard by ear or from the player's own guitar** for the 10–40 song pilot. Rebuild the 43 current charts this way before anyone but the founder uses them. For a paid product:
  - add publisher print and digital licences (for example Hal Leonard or Muse Group, or deals with each publisher);
  - optionally, a private "analyse your own file on your phone" feature;
  - optionally, a Songle or YouTube enquiry if the founder chooses.

## 1. EU and EEA copyright law

### 1.1 Directive 2019/790, the digital single market (DSM) directive

Source: [EUR-Lex ELI 2019/790](https://eur-lex.europa.eu/eli/dir/2019/790/oj), of 17 April 2019. EUR-Lex blocked automated reading, so we read the identical text through the [EU Publications Office copy](http://publications.europa.eu/resource/celex/32019L0790) (acc.).

- **Art. 2(2), what TDM means:** "any automated analytical technique aimed at analysing text and data in digital form in order to generate information". Automatic chord or beat extraction plausibly fits (inference).
- **Art. 4(1), the commercial TDM exception:** covers "reproductions and extractions of lawfully accessible works and other subject matter for the purposes of text and data mining". Lawful access is a precondition.
- **Art. 4(2), keeping copies:** copies "may be retained for as long as is necessary for the purposes of text and data mining". The exception lets you *keep* copies. "We don't keep the audio" is therefore not what makes it apply. The tests are lawful access and no opt-out.
- **Art. 4(3), the opt-out:** the exception applies only if use "has not been expressly reserved by their rightholders in an appropriate manner, such as machine-readable means in the case of content made publicly available online".
- **Recital 18 says how an opt-out can be made:**
  - for content online, machine-readable means "including metadata and terms and conditions of a website or a service";
  - otherwise "contractual agreements or a unilateral declaration".
  - It also says rights holders may "apply measures to ensure that their reservations … are respected".
- **Art. 7(1), override by contract:** "Any contractual provision contrary to the exceptions provided for in Articles 3, 5 and 6 shall be unenforceable." **Art. 4 is not on the list, so a contract or terms of service can override the commercial TDM exception.**
- **Art. 7(2):** applies the first, third and fifth subparagraphs of Art. 6(4) of directive 2001/29 to Arts 3–6. Art. 6(4) obliges *rights holders* to make an exception usable. It does not let users break a protection measure themselves.

### 1.2 Directive 2001/29, the information society (InfoSoc) directive: temporary copies and protection measures

Source: [EUR-Lex ELI 2001/29](https://eur-lex.europa.eu/eli/dir/2001/29/oj), read through the Publications Office copy (acc.).

- **Art. 5(1), temporary copies.** All of these conditions must hold:
  - the copy is "transient or incidental";
  - it is "an integral and essential part of a technological process";
  - its sole purpose is a network transmission or "a lawful use";
  - it has "no independent economic significance".
- **How the EU Court of Justice (CJEU) has applied it:**
  - [*Infopaq*, C-5/08](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62008CJ0005) (16 July 2009). The conditions are cumulative (para 55). A copy is transient only if the process "deletes that act automatically, without human intervention".
  - [*FAPL/Murphy*, C-403/08 & C-429/08](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62008CJ0403) (4 October 2011), para 168. A use is lawful "where it is authorised by the right holder or where it is not restricted by the applicable legislation".
  - [*Stichting Brein v Filmspeler*, C-527/15](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62015CJ0527) (26 April 2017), ruling 2. Temporary copies made while streaming from an unauthorised source fail Art. 5(1) and (5).
  - [*PRCA v NLA*, C-360/13](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62013CJ0360) (5 June 2014). Screen and cache copies made "in the course of viewing a website" qualify.
- **What that means here (inference):** ordinary playback in the embed is covered. Saving a file with yt-dlp and running a separate analysis job on it is not transient, is not part of viewing, and is not a use the contract allows.
- **Art. 6(1)–(3), protection measures:** Member States must protect "effective technological measures". These include "an access control or protection process, such as encryption, scrambling or other transformation … or a copy control mechanism".
- **Art. 6(4), fourth subparagraph:** the duty to make exceptions usable does not apply to works "made available to the public on agreed contractual terms" on demand. That describes YouTube's service (inference).

### 1.3 Label and publisher opt-outs from TDM

- **IFPI's register:** [Reservations of Rights](https://www.ifpi.org/ifpi-priorities/reservations-of-rights/) (acc.) lists Art. 4 declarations by:
  - Sony Music Entertainment, Universal Music Group, Warner Music Group;
  - Merlin, Beggars, Concord and others.

  It says nothing specific about YouTube-hosted content.
- **Universal Music Group:** [UMG Reservation of Rights](https://www.universalmusic.com/umg-reservation-of-rights) (no date shown; acc.).
  - It is made by UMG "including Universal Music Publishing".
  - UMG "expressly reserves all rights … in relation to text and data mining … under Article 4".
  - It covers recordings and compositions, "for any purpose". It is not limited to AI training, so it reaches chord analysis.
  - It is a written web statement, not a machine-readable signal.
- **Warner Music Group:** [WMG Statement Regarding AI Technologies](https://www.wmg.com/wp-content/uploads/2024/07/WMG-Statement-Regarding-AI-Technologies.pdf) (PDF; the upload path shows July 2024; acc.).
  - It requires a licence for "ripping, scraping, crawling, mining … making extractions of" WMG works "as inputs for any machine learning or AI technologies".
  - It reserves all Art. 4 rights over compositions and lyrics too. That this includes Warner Chappell is our inference.
  - A chord-recognition model is machine learning, so it is arguably covered.
- **Sony Music:**
  - Its [Declaration of AI training opt out](https://www.sonymusic.com/sonymusic/declaration-of-ai-training-opt-out) blocked automated reading. The wording and the 16 May 2024 date are **UNCONFIRMED** from the page itself; IFPI lists it.
  - [sonymusic.com/robots.txt](https://www.sonymusic.com/robots.txt) (acc.) states that content-signal restrictions "ARE EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4", with `ai-train=no`. That covers sonymusic.com itself.
  - Sony Music Publishing's position is **UNCONFIRMED**.
- **No signal on the videos themselves:** we found no TDMRep or similar machine-readable opt-out attached to YouTube videos (absence **UNCONFIRMED**). Whether YouTube's own download ban counts as an Art. 4(3) opt-out, which Recital 18's "terms and conditions of … a service" would suggest, is untested.

### 1.4 The Hamburg youtube-dl / Uberspace case

The brief's "about 2021" date was wrong.
- **District court:** LG Hamburg ruled on **31 March 2023**. Uberspace, which hosted the youtube-dl website, was liable for aiding "Umgehung technischer Schutzmaßnahmen" (circumvention of technical protection measures). Sony, Universal and Warner were the claimants.
  - Sources: [GFF press release](https://freiheitsrechte.org/ueber-die-gff/presse/pressemitteilungen-der-gesellschaft-fur-freiheitsrechte/pm-uberspace-youtube-dl-berufung) (5 April 2023); [BVMI press release](https://www.musikindustrie.de/presse/presseinformationen/urteil-des-hanseatischen-oberlandesgerichts-host-provider-von-youtube-dl-haftet-als-teilnehmer-und-auf-schadensersatz) (26 November 2024).
  - The case number 310 O 316/21 comes only from secondary sources (**UNCONFIRMED**). The judgment text sits behind a CAPTCHA and we did not read it.
  - That the court called YouTube's "rolling cipher" an effective measure under § 95a of the German Copyright Act (UrhG) is consistent with these releases. The exact wording is **UNCONFIRMED**.
- **Appeal:** the Hanseatic Higher Regional Court (OLG Hamburg) dismissed the appeal "in vollem Umfang" (in full) (BVMI, 26 November 2024). The date of 21 November 2024 and case number 5 U 54/23 are **UNCONFIRMED** (secondary only).
- **Final:** the GFF case page ([Uberspace / youtube-dl](https://freiheitsrechte.org/uberspace-youtube-dl), acc.) says the Federal Court of Justice (BGH) rejected the complaint in October 2025. "Damit sind alle Rechtsmittel erschöpft" (all appeals are now exhausted). The BGH case number is **UNCONFIRMED**.
- **Contrast:** [GitHub reinstated youtube-dl](https://github.blog/news-insights/policy-news-and-insights/standing-up-for-developers-youtube-dl-is-back/) on 16 November 2020 under US law. That was a platform decision, not a court ruling, and German courts reached the opposite view.

### 1.5 Norway

- **EEA incorporation is still pending.** [EEA Joint Committee Decision No 333/2023](http://data.europa.eu/eli/dec/2024/1465/oj) of 8 December 2023 adds 2019/790 to the EEA Agreement's Annex XVII (published OJ L 2024/1465, 13 June 2024).
  - It enters into force only after Art. 103 notifications. Its footnote reads "Constitutional requirements indicated".
  - Norway's consent is part of the bill below, so the decision is almost certainly not yet in force (inference; the EFTA EEA-Lex status page blocked automated reading).
- **The bill:** [Prop. 41 LS (2025–2026)](https://www.regjeringen.no/no/dokumenter/prop.-41-ls-20252026/id3154279/) (Council of State, 27 March 2026). It proposes three new sections:
  - **§ 50 d:** defines TDM.
  - **§ 50 e, commercial TDM:**
    - needs a "lovlig tilgjengelig verk" (lawfully accessible work);
    - copies may be kept "så lenge det er nødvendig" (as long as necessary);
    - does not apply where the right is "på hensiktsmessig måte … forbeholdt" (reserved in an appropriate manner).
  - **§ 50 f, research TDM:** only this section says "Det kan ikke avtales innskrenkninger" (no restrictions can be agreed by contract). § 50 e has no such protection.
  - The ministry adds that using protection measures is itself "en hensiktsmessig måte å reservere seg" (an appropriate way to opt out).
- **Bill status:** [Stortinget case 200243](https://data.stortinget.no/eksport/sak?sakid=200243) (acc.) shows it as "til_behandling" (under consideration) in the Family and Culture Committee since 9 April 2026. **Norway has no TDM exception in force today.**
- **The current act:** [åndsverkloven, LOV-2018-06-15-40](https://lovdata.no/dokument/NL/lov/2018-06-15-40), as amended to LOV-2024-12-13-76 (acc.):
  - **§ 4, temporary copies:** implements Art. 5(1). It requires a sole purpose of "lovlig bruk" (lawful use) and no "selvstendig økonomisk betydning" (independent economic significance).
  - **§ 26, private copying:** applies only when not "i ervervsøyemed" (for commercial purposes) and not from an unlawful copy. Such copies "må ikke brukes i annet øyemed" (may not be used for any other purpose). Music may not be copied with "fremmed hjelp" (help from others).
  - **§ 99:** forbids circumventing "effektive tekniske beskyttelsessystemer" (effective technical protection measures) and distributing tools for it.
  - **§ 100:** makes rights holders enable listed exceptions, but excludes on-demand services provided on agreed terms.
  - Lovdata's consolidated text has no data-mining provision.

### 1.6 Can a copyright exception override YouTube's terms?

- **The consumer terms.** The [YouTube Terms of Service](https://www.youtube.com/t/terms) are served to Norwegian visitors in a version dated 5 January 2022 (acc.); the US English version is effective 15 December 2023.
  - For the EEA, the contracting party is Google Ireland and the governing law is "the laws of your country of residence".
  - The download ban carves out "(c) as permitted by applicable law", so Norwegian law decides. Today Norwegian law gives no exception that fits (§ 1.5).
- **The developer contract has no such carve-out.**
  - The [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) (updated 14 September 2026), §25.11, apply "the laws of California".
  - [Developer Policies III.E.1 and III.I.7](https://developers.google.com/youtube/terms/developer-policies) (updated 15 October 2026) forbid downloading, caching or storing copies, and isolating the audio, with no "applicable law" carve-out.
  - Strum Along accepts these by using the IFrame API.
  - Even a future § 50 e would not void them, since § 50 e (like Art. 4) is not protected against contract.

**What the founder argued, and what the law says:** "We're in the EEA and we don't keep the audio" fails on four counts. Norway has no TDM exception yet. Keeping copies isn't the test. The labels have opted out. And the developer contract applies whatever copyright allows.

## 2. Asking YouTube for permission

- **No route for III.E.1 itself.** The [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) (15 October 2026) say "prior written approval", but describe no way to request it for III.E.1.
  - The only "request that approval at this form" links are in III.F.1 (changing the look and feel) and the III.G.1 introduction (selling the API services, or ads on or around content).
  - Both point to [yt_api_form](https://support.google.com/youtube/contact/yt_api_form) (acc.).
- **The audit guide doesn't help.** [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) (15 October 2026) lists forms for audit and quota, appeals, periodic audits and changes of control. It does not mention policy exceptions.
  - The [Developer Policies Guide](https://developers.google.com/youtube/terms/developer-policies-guide) (14 September 2026) says to "apply for an API Compliance Audit" when unsure.
  - It lists "Using YouTube's API to separate or isolate video or audio components" as prohibited.
- **The audit form has no caching question.** Read only; nothing submitted. It asks for:
  - the organisation and its business model (a description of 100–5,000 characters);
  - the API client name (without "YouTube"), URL, privacy policy and terms of service;
  - a Google Cloud project number and the use-case category;
  - API volume and screenshots or a screencast;
  - any Google representative.

  There is no question about downloading or caching, and no field for policy exceptions. A request would have to go in free text. The end of the form was cut off when we read it (**UNCONFIRMED**).
- **Rights holders must agree too.** The [YouTube Terms](https://www.youtube.com/static?template=terms&hl=en&gl=US) (effective 15 December 2023) allow downloading only "with prior written permission from YouTube and, if applicable, the respective rights holders". YouTube's approval alone would not be enough for label-owned uploads (inference).
- **No partner programme route.** We found no page in the YouTube Partner Program, Content ID or YouTube Music partner material describing a III.E.1 route (**UNCONFIRMED**; not searched exhaustively).

**A specific request would need to contain** (founder's decision; not sent):
1. A statement that it asks for written approval under III.E.1, and whether it covers one-off server analysis or ongoing storage.
2. Who is asking: legal name, address, contact, the API client name, URL, privacy policy and terms, and the Google Cloud project number.
3. The use: a guitar-practice aid showing our own chord cues beside the unmodified embed. Playback, ads and controls are untouched.
4. Data handling:
   - audio fetched for each listed video, analysed, then deleted within a stated time;
   - only chord labels and timestamps kept;
   - no audio, stems or derived audio redistributed;
   - no offline or background play.
5. The exact list of video IDs and channels, with written consent from the rights holder or channel owner where applicable.
6. Commitments under III.I.7–8 (no separating the audio) and III.F.1 (no change to the player's look), plus monetisation and ad placement.
7. Screenshots, a demo or screencast, the expected API volume, and a request for a written reply.

**Assessment:** permission is possible in principle but has no published process. It would need label consent for most familiar songs. This is not a pilot-scale route (inference).

## 3. Clean alternatives that still pair with the embed

### 3.1 Analysing the audio while it plays: blocked

- **Policy:** III.I.7 forbids you to "separate, isolate, or modify the audio or video components" ([Developer Policies](https://developers.google.com/youtube/terms/developer-policies), 15 October 2026).
- **Cross-origin isolation:** the player is a cross-origin iframe on youtube.com, or youtube-nocookie.com in privacy-enhanced mode ([embed help](https://support.google.com/youtube/answer/171780), acc.).
  - The [HTML standard's cross-origin Window properties](https://html.spec.whatwg.org/multipage/nav-history-apis.html) (26 October 2026) do not include `document`, so the page cannot reach the player's `<video>`.
  - The [Web Audio API §1.22.4](https://webaudio.github.io/web-audio-api/#MediaElementAudioSourceOptions-security) (Editor's Draft, 27 October 2026) says a cross-origin MediaElementAudioSourceNode "MUST output silence".
  - The [IFrame API](https://developers.google.com/youtube/iframe_api_reference) (15 October 2026) exposes the iframe node only, with no audio.
- **Screen and system audio capture:** [MDN's compatibility data](https://github.com/mdn/browser-compat-data/blob/main/api/MediaDevices.json) (acc.) lists `getDisplayMedia` audio capture as unsupported on Safari for iOS. The iOS 27 `getDisplayMedia` entry is **UNCONFIRMED** against WebKit's notes.
- **Microphone pointed at the speaker:** technically possible, but low quality. It would arguably "isolate" the audio or use Content in a way the Service doesn't authorise. No text clears it (inference). **Don't use it.**

### 3.2 Licensed chord or timing data

| Supplier | What it offers | Terms | Cost signal | Rock/pop coverage | Match to a given YouTube upload |
|---|---|---|---|---|---|
| **Songle** (AIST) | Beats, chords and chorus in milliseconds, crowd-corrected; keyed to a song or video URL, including YouTube (`data-url`, `videoID`, `mode: yt-video`) ([widget docs](https://widget.songle.jp/docs/v1?lang=en), acc.) | [Terms](https://widget.songle.jp/docs/terms-of-use) (© 2014–2026), Art. 3: commercial use, "including free services run by a company", needs consulting AIST first; the player must be visible; Art. 1: the service may stop without notice | Not stated | Only songs someone has registered; Western rock/pop **UNCONFIRMED**; automatic analysis, so accuracy varies | **Best fit:** keyed to the upload's URL |
| **Chordify** | Per-beat chords aligned to the analysed YouTube video | Its terms' scope mentions "the Chordify API"; personal, non-commercial use. Read only via a search snapshot, because chordify.net blocked automated reading (**UNCONFIRMED** wording) | No public developer docs or B2B page found | Very broad | Would be excellent, but no licence is published. Its own audio sourcing is undisclosed (see [earlier note](YOUTUBE_CHORDIFY_TOS_RESEARCH.md)) |
| **Songsterr** (Guitar Tabs LLC) | Licensed tabs with a beat grid, synced to YouTube or the original audio | [Terms](https://www.songsterr.com/a/wa/terms) (10 June 2026): no commercial use "without express advance written permission"; no API mentioned; [help](https://www.songsterr.com/help) (acc.): "pay out almost half of our revenue as royalties" | Unknown | Strong | Good within Songsterr; no export route |
| **Hooktheory** | [Trends API](https://www.hooktheory.com/api/trends/docs) (acc.): next-chord probabilities and song lists, no timings. TheoryTab YouTube sync is capped at "30 seconds or 10% of the length" ([tabs help](https://hooktheory.com/support/tabs), acc.) | [Terms](https://www.hooktheory.com/terms) (October 2026 per fetch): no scraping or TDM unless "via a written data license or API terms" | Free API; data licence price unknown | Broad, but excerpts only | Partial: excerpt markers only |
| **Ultimate Guitar** (Muse Group) | Untimed chord and tab pages; [publisher licences](https://www.ultimate-guitar.com/article/blog/licensing) (undated) with "thousands of publishers" | [Terms](https://www.ultimate-guitar.com/about/tos.htm) (24 August 2026) §6.3: "personal, non-commercial use only"; §14: widgets not for commercial use | Unknown | Very strong | Poor (untimed) |
| **Hal Leonard** (Muse Group since [4 December 2023](https://mu.se/post/hal-leonard-joins-muse-group)) | [Hal Leonard Connect](https://connect.halleonard.com/) (acc.): "an API and SDK platform", "428,000+ digital titles", for "retailers, dealers and education resellers" ([announced](https://www.mu.se/posts/hal-leonard-connect) 6 August 2026) | Permission is case by case and quoted in writing (permissions FAQ, read via search snippet only) | Unknown | Very strong | Poor: notated bars, no recording timings (**UNCONFIRMED**) |
| **McGill Billboard** (DDMAL) | 740 Billboard Hot 100 songs with expert chords and timings in seconds; CC0 ([project page](https://ddmal.music.mcgill.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)) returned 404, so details come from the [mirdata loader](https://mirdata.readthedocs.io/en/latest/_modules/mirdata/datasets/billboard.html) and search summaries: **UNCONFIRMED**) | CC0, citation requested | Free | 1958–1991 US hits (**UNCONFIRMED** range) | Moderate: timed against McGill's own copies, so it needs an offset fit to each upload (§ 3.6) |
| **Chordonomicon** | 666k untimed chord sequences ([paper](https://arxiv.org/html/2410.22046v1)) | Scraped from Ultimate Guitar, which conflicts with its terms §6.2 and §6.4 | Free | Huge | None. **Not clean for commercial use** |

Also checked:
- [AcousticBrainz](https://acousticbrainz.org/) stopped collecting data in 2022 and has no chord timings.
- Musixmatch is lyrics only (plans page unreadable, **UNCONFIRMED**).
- [Music.AI / Moises](https://music.ai/docs/) needs input audio.

**Verdict:** no off-the-shelf licence covers familiar songs with YouTube-matched timings today. Songle comes closest, but only with AIST's prior agreement.

### 3.3 Licensed audio or stems for analysis

- **Catalogue suppliers:**
  - **7digital, now part of Songtradr's MassiveMusic.** [MassiveMusic catalogue analysis](https://massivemusic.com/services/metadata-services/audio-fingerprinting-catalog-analysis) (© 2025) offers analysis over 150M+ tracks, "subject to" the customer's own licensing. Its [AI datasets](https://massivemusic.com/services/training-content-data-for-ai-models/) are "approved by the rights holder". Whether major-label masters are included is **UNCONFIRMED**. This is an enterprise contract.
  - **Tuned Global.** [Its docs](https://docs.tunedglobal.com/overview) (undated) say the catalogue "cannot be used to train Machine Learning or AI models" without a separate agreement.
  - **[Feed.fm](https://www.feed.fm/license-music)** offers playback only.
- **Distributors** (for example [DistroKid's terms](https://distrokid.com/terms/), as of 24 September 2026): their licences run from artists to the distributor and its stores. They give a third-party app nothing (inference).
- **Label AI deals.** [UMG–Udio](https://tools.prnewswire.com/en-us/live/20813/release/20251029EN10848) (30 October 2025) describes a "walled garden". The WMG–Suno and Klay deals were reported only in trade press (**UNCONFIRMED**). These are bilateral deals; **we found no open programme for small analysis licensees**.
- **Store downloads are barred.**
  - [Apple Media Services Terms](https://www.apple.com/legal/internet-services/itunes/us/terms.html) (14 September 2026): "only for personal, noncommercial purposes". No use "to scrape, copy, or perform measurement, analysis, or monitoring of" Content.
  - [Qobuz](https://www.qobuz.com/us-en/legal/terms) (undated): "strictly private use", and no AI use without rights-holder authorisation.
  - [Bandcamp](https://bandcamp.com/terms_of_use) (7 May 2026): "solely for personal, non-commercial use".
- **Sound-alike re-recordings.**
  - KaraFun's tracks are "produced and licensed by Tency Music" ([KaraFun copyright](https://www.karafun.com/copyright.html), acc.).
  - Karaoke Version separates master use from publishing rights (its blog post of 4 August 2025; full URL not captured, **UNCONFIRMED**), and licenses uses beyond home and one-off live use ([self-licensing help](https://www.karaoke-version.com/help/self-licensing_33.html), acc.).
  - A deal plus publisher coverage could permit analysis. But **their timing never matches the YouTube upload**, because it is a different performance.
- **Cost signals:** enterprise and unpriced. One AI-dataset vendor is reported "starting at $10,000/year" (secondary, **UNCONFIRMED**).
- **Timing match:** high, with an offset, only when the licensed file is the same master as the upload (inference). Remasters and video edits need checking for each song.

### 3.4 Artist-authorised or original recordings

- **What Creative Commons allows:** CC BY and BY-SA permit commercial use and adaptations; NC and ND variants restrict them ([CC licence summary](https://creativecommons.org/share-your-work/cclicenses/), acc.).
- **CC doesn't override YouTube's terms.** [CC BY 4.0 §7(b)](https://creativecommons.org/licenses/by/4.0/legalcode.en) says other agreements are separate. A CC licence doesn't lift the YouTube Terms' download ban, so get the file from the artist or a host that permits downloads (inference from both texts).
- **Sources:**
  - [Jamendo API terms](https://devportal.jamendo.com/api_terms_of_use) (17 September 2013): free for non-commercial use; commercial use by contact. [Jamendo Licensing](https://licensing.jamendo.com/en) offers 283k+ tracks.
  - The [Free Music Archive](https://freemusicarchive.org/faq) is mostly CC.
  - A direct written licence from an artist or label, covering master and composition, is cleanest.
- **Fit:** clean, and the timing matches the artist's own upload of the same master. But **not familiar rock or pop**. It suits original exercises and partner artists, as [SONG_ACCESS_FEASIBILITY.md](SONG_ACCESS_FEASIBILITY.md) already suggests.

### 3.5 The user's own audio, analysed on their own device

- **Technically feasible in Safari.**
  - [`<input type="file" accept="audio/*">`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file) (MDN, 14 October 2026) and [`decodeAudioData`](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData) (MDN, 30 September 2026) are both widely supported.
  - [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/) (acc.) runs models in the browser with WASM or WebGPU backends.
  - [Safari 26](https://developer.apple.com/documentation/safari-release-notes/safari-26-release-notes) added WebGPU.
  - Threaded WASM needs cross-origin isolation headers, which GitHub Pages can't set (inference; **UNCONFIRMED**).
  - Whether our chord models (BTC, CREMA) run fast enough on an iPhone is unproven.
- **Apple Music is not a source.** The Apple Music API returns library metadata and `playParams` for playback only, not audio ([library song attributes](https://developer.apple.com/documentation/applemusicapi/librarysongs/attributes-data.dictionary), acc.).
- **Precedent:** Chordify Premium lets users upload MP3, MP4 or OGG files ([support page](https://support.chordify.net/hc/en-us/articles/360002164538-How-to-use-Premium-features)). We read this only via search index (**UNCONFIRMED** wording). Chordify analyses on its servers.
- **Legal limit:**
  - § 26 of the Norwegian act allows private, non-commercial copies that "må ikke brukes i annet øyemed" (may not be used for any other purpose) (§ 1.5). Directive 2001/29 Art. 5(2)(b) has an equivalent private-copying exception.
  - A store-bought file still carries the store's ban on "analysis" (§ 3.3). Whether a user's on-device analysis breaches Apple's terms is for the user and for counsel (inference).
  - **The result must stay with that user. It cannot feed the shared catalogue** (inference).
- **Timing match:** medium to high. The user's file may be a different master or edit, so it needs offset and drift alignment to the embed. A tapped anchor point (§ 3.6) would do.

### 3.6 People tapping along to the embed's own clock: no audio copy at all

- **What the player offers** ([IFrame Player API](https://developers.google.com/youtube/iframe_api_reference), 15 October 2026):
  - `getCurrentTime()`: "Returns the elapsed time in seconds since the video started playing".
  - `onStateChange`, `getPlaybackRate()`.
  - `seekTo()` goes "to the closest keyframe" unless that part is already buffered.
  - The precision of `getCurrentTime()` is not documented (**UNCONFIRMED**), so measure it on the device.
- **Storing our own timestamps.** "API Data" is data "provided to API Clients … through the YouTube API services" ([API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service), 14 September 2026).
  - Timestamps we author ourselves aren't API Data, so the 30-day refresh in III.E.4 doesn't plainly reach them (inference).
  - The video ID and any metadata fetched through the Data API are API Data.
  - III.E.4.h forbids presenting our data as a replacement for YouTube's; our chords are not YouTube data, so label them clearly.
- **Precedent:** Songle's crowd correction of beats and chords ([JST press release](https://www.jst.go.jp/pr/announce/20120829-3/index.html), 29 August 2012; [docs.songle.jp](https://docs.songle.jp/), acc.).
- **How it could work** (inference; a design proposal, not tested):
  1. **Beat and bar grid.** The founder, wearing headphones, taps each beat or downbeat on the phone while the visible embed plays. Taps are stamped with `performance.now()`. The embed clock is fitted to that: `t_video ≈ a·performance.now() + b`, sampled every animation frame during PLAYING and refitted after every state change or seek.
  2. **Chords, option one: by hand.** Enter the chord changes per bar on that grid, from ear and musical knowledge.
  3. **Chords, option two: from the player's own guitar.** The founder plays along on guitar while wearing headphones, and the microphone records *only their guitar*. Our existing chord models then run on that recording, which is the founder's own audio. No YouTube audio is captured, provided the headphones keep the speaker out of the mic.
  4. **Calibration.** Measure tap latency on each device against a click with known timing, then subtract the median. Take the median across several tappers, reject outliers about 80 ms out, and report the spread as a quality score.
  5. **Validate** against a self-published or synthetic video whose click times are known. This keeps the repo's rule that editorial drafts are not independent timing references (AGENTS.md).
- **Cost:** a few minutes per song per tapper, plus a few takes of guitar-along. That is human time, not fees.
- **Timing match:** the best of any route. The timings are measured on that exact upload's clock, so there is no offset problem. If the upload changes, re-tap or re-anchor it.

### 3.7 Displaying chord arrangements: a separate publisher licence

- **The licensed services hold publisher licences:**
  - **Ultimate Guitar:** [licences](https://www.ultimate-guitar.com/article/blog/licensing) with Sony/ATV, EMI, Hal Leonard and others, and the Harry Fox Agency.
  - **Songsterr:** its [help page](https://www.songsterr.com/help) says blocked songs have no "license with the artist's publisher".
  - **Yousician:** songs may be missing "due to licensing agreements with the publishers" ([Yousician support](https://support.yousician.com/hc/en-us/articles/360000758937-Why-can-t-I-find-a-popular-song-in-Yousician), acc.).
  - **JustinGuitar's** publisher payments are stated only by community moderators (**UNCONFIRMED**).
- **In Norway:** [TONO handles public performance and NCB handles mechanical rights](https://en.tono.no/faq-items/hva-er-forskjellen-pa-tono-og-ncb/) (undated). Neither mentions sheet music. Digital chord display is therefore likely licensed directly by publishers or their print agents (**UNCONFIRMED**).
- **Chord progressions alone:** in *Structured Asset Sales v Sheeran* (US 2nd Circuit, 1 November 2024), a commonplace progression with its harmonic rhythm was held not protectable. We read this only in summaries ([Loeb & Loeb](https://www.loeb.com/en/insights/publications/2024/11/structured-asset-sales-llc-v-sheeran), [Stanford Fair Use Project](https://fairuse.stanford.edu/case/structured-asset-sales-llc-v-sheeran)). It is US law, and the EU and Norwegian position is **UNCONFIRMED**.
- **What stays protected:** lyrics, which Strum Along already does not show, and specific arrangements.
- **Takeaway (inference):** the founder's private pilot carries little risk here. A paid product showing full song structure and chords should expect to need publisher licences whatever the timing source. This is a separate cost from the timing problem.

## 4. Recommendation

| Rank | Route | Clean against YouTube's terms | Clean on copyright | 10–40 song pilot | Paid product | Timing match |
|---|---|---|---|---|---|---|
| 1 | **Tap-along on the embed clock, chords by ear or from the player's own guitar** (§ 3.6) | Yes: no copy, only normal visible playback (inference) | Timing is ours; arrangement display needs publisher licences once paid | Days of founder time; no fees | Scales with crowd or contractor tapping; add publisher licences | Exact |
| 2 | **User's own file, analysed on their phone** (§ 3.5) | Yes: no YouTube involvement | Private use only; results not shared | Optional; engineering-heavy | A good Premium feature, private to each user | Medium–high, with an anchor |
| 3 | **Songle data with AIST's agreement** (§ 3.2) | Yes, if AIST agrees; its widget uses visible embeds | Publisher question unchanged | Needs an enquiry (founder's call); coverage uncertain | Depends on AIST's terms | Keyed to the upload |
| 4 | **McGill Billboard (CC0) as a seed, anchored by taps** (§ 3.2) | Yes: no copy | The data is CC0; publisher question unchanged | Only songs that overlap, from 1958–1991 | Limited coverage | Good once offset-fitted |
| 5 | **Licensed masters or sound-alikes under a contract** (§ 3.3) | Yes: no YouTube involvement | Clean if the contract covers analysis | Too costly for a pilot | Possible at scale | High (same master) or none (sound-alike) |
| 6 | **Written approval from YouTube plus rights holders** (§ 2) | Yes, once granted | Rights holders' consent needed anyway | No: no process, slow | Unlikely | Exact |
| 7 | **CC or artist-direct recordings** (§ 3.4) | Yes | Yes | Not familiar songs | For original or partner content | High for the artist's own upload |
| — | **Analysis during playback; yt-dlp; store downloads** | **No** | — | — | — | — |

**Adopt first: route 1.**

For the pilot:
1. Build a "tap the grid" mode into Strum Along's own player screen, plus a headphone guitar-along take that feeds the existing chord models.
2. Rebuild the 10–40 pilot charts this way.
3. Keep the yt-dlp-derived charts research-only, as the repo already treats them. Retire them before anyone other than the founder uses the app.
4. Deciding whether to delete the local caches is the founder's call. Deleting them stops the ongoing "store" problem under III.E.1 but doesn't undo the earlier copying.

Before charging:
1. Get publisher print and digital terms, for example from Hal Leonard or Muse Group, or from each publisher (§ 3.7).
2. Get a targeted review by a Norwegian lawyer of route 1 and of how arrangements are displayed.
3. Consider route 2 as a private Premium feature.
4. Consider a Songle or YouTube enquiry (routes 3 and 6) only if the founder decides to make contact.
