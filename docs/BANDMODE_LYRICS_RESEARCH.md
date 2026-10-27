# Band mode research: lyric-writing craft and AI lyric tools

Issue: [#70](https://github.com/dcromp/music-os/issues/70) (part of
[#64](https://github.com/dcromp/music-os/issues/64)). Research by AI (Claude
Code). Sources checked on **27 October 2026**. This is a findings note, not a
product decision. No song lyrics are reproduced anywhere in it. Quotations from
books and articles are kept under 15 words, and everything else is paraphrase.

Band mode is planned as a guided, editable song builder for guitarists without
bandmates. One step is lyric writing, where the AI should help the writer
rather than write the song. This note covers the craft that a guided step could
teach, the checks an app could run, the tools that exist, and the legal and
quality risks.

## Sources and how reliable they are

| Source | Type | What it supports |
|---|---|---|
| Pat Pattison, *Songwriting: Writing the Lyrics* (Berklee on Coursera) — <https://www.coursera.org/learn/songwriting-lyrics> | First-party course outline | Point of view, song form, prosody, stable/unstable, rhyme types, stressed syllables, melody fit |
| Berklee Online, *Lyric Writing: Writing From the Title* (OSONG-221, Pattison and Kelly Riley) — <https://online.berklee.edu/courses/lyric-writing-writing-from-the-title> | First-party course outline | Title-led writing, rhythm and pitch of the title, verse development, contrasting sections |
| Pattison's own book and article list — <https://www.patpattison.com/quotes-books-articles> | Author's site | Book titles, publishers and years; article titles |
| N. Ketterer, "Pat Pattison: Writing Better Lyrics", *Sound On Sound*, March 2022 — <https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics> | Interview, specialist press | Prosody, sense-bound writing, stability tools, point of view |
| J. Summach, "The Structure, Function, and Genesis of the Prechorus", *Music Theory Online* 17.3, Oct 2011 — <https://www.mtosmt.org/issues/mto.11.17.3/mto.11.17.3.summach.html> | Peer-reviewed music theory | Pre-chorus role, verse–pre-chorus–chorus form, module lengths |
| Wikipedia, "Song structure" — <https://en.wikipedia.org/wiki/Song_structure> | Encyclopaedia (cites Everett, Watson, Davidson & Heartwood, Doll) | Section roles, 32-bar form |
| Datamuse API docs — <https://www.datamuse.com/api/> and a live test of `api.datamuse.com` | First-party docs and observed behaviour | Rhyme, sound-alike, syllable and pronunciation queries, limits |
| CMU Pronouncing Dictionary — <https://github.com/cmusphinx/cmudict> | First-party data and licence | Pronunciations with stress marks |
| MasterWriter — <https://masterwriter.com/songwriting/> | Vendor page | Rhyme and phrase dictionaries, its stance on the writer |
| US Copyright Office, AI report Part 2 and 2023 registration guidance — <https://www.copyright.gov/ai/> | Government | Copyrightability of AI output in the US |
| UK CDPA 1988 s9(3) — <https://www.legislation.gov.uk/ukpga/1988/48/section/9>; UK government Copyright and AI report (18 March 2026), summarised by Stephenson Harwood — <https://www.stephensonharwood.com/post/102mpke/uk-government-publishes-report-and-impact-assessment-on-copyright-and-artificial-intelligence-the-debate-continues/> | Statute; law-firm summary of a government report | UK position on computer-generated works |
| GEMA v OpenAI (Munich Regional Court, 11 Nov 2025) — <https://www.gema.de/en/w/landmark-ruling-gema-against-openai> | Claimant's statement | Lyrics memorised and output by a chatbot |
| Concord v Anthropic guardrails stipulation — <https://musicbusinessworldwide.com/universal-music-concord-music-abkco-welcome-court-approved-guardrails-in-anthropic-ai-dispute> | Trade press | Lyric-output guardrails agreed in a US case |
| Doshi & Hauser, *Science Advances* 10, eadn5290 (2024) — <https://pmc.ncbi.nlm.nih.gov/articles/PMC11244532> | Peer-reviewed | AI ideas lift weaker writers but make output more alike |
| Suvarna, Khandelwal & Peng, *PhonologyBench* (arXiv 2404.02456, 2024) — <https://arxiv.org/abs/2404.02456> | Preprint | LLMs lag humans at syllable counting and rhyme generation |
| Yoshida et al., *CoLyricist* (arXiv 2602.22606, Feb 2026) — <https://arxiv.org/abs/2602.22606> | Preprint, HCI | Lyricist workflow stages; AI support per stage |

Pattison's books (*Writing Better Lyrics*, 2nd ed., Writer's Digest Books,
2009; *Essential Guide to Lyric Form and Structure* and *Essential Guide to
Rhyming*, Berklee Press, both first published 1992 per
[his site](https://www.patpattison.com/quotes-books-articles)) were **not read
directly**. Their content is reported here through his own course outlines and
interviews. Treat the book-level detail as second-hand.

## 1. Established craft

### 1.1 What each section does

- **Verse.** Carries the story and the detail. Its words usually change each
  time while the melody mostly repeats
  ([Wikipedia, citing Davidson & Heartwood and Cope](https://en.wikipedia.org/wiki/Song_structure)).
  Pattison judges sections by the job they do: a verse drafted first may end up
  as verse two, or even become the chorus
  ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
  His book has a chapter on "verse development and power positions", and his
  title course has a lesson on verse development techniques
  ([course](https://online.berklee.edu/courses/lyric-writing-writing-from-the-title)).
- **Pre-chorus.** A section of its own whose job is to build momentum into the
  chorus. In the lyric, phrases get shorter and run together, and rhyme pushes
  forward. In the music, groove, dynamics, register or harmonic rhythm change.
  With a pre-chorus, the chorus becomes the goal of the whole song
  ([Summach 2011](https://www.mtosmt.org/issues/mto.11.17.3/mto.11.17.3.summach.html)).
  Summach dates the pre-chorus as a separate section to the mid-1960s.
- **Chorus.** Carries the hook or main idea. It changes little between repeats
  and is more intense than the verse
  ([Wikipedia, citing Watson and Everett](https://en.wikipedia.org/wiki/Song_structure)).
- **Bridge.** Breaks the pattern with new music and new words, often after the
  second chorus. In AABA songs, the B section is the bridge or "middle eight"
  ([Wikipedia](https://en.wikipedia.org/wiki/Song_structure)).

### 1.2 Hooks and titles

- Berklee teaches a whole lyric course that starts from the **title**: finding
  and developing it, setting its rhythm and pitch, building a rhythmic template
  from it, then placing it in sections for the most impact
  ([OSONG-221](https://online.berklee.edu/courses/lyric-writing-writing-from-the-title)).
- The chorus is where the hook lives
  ([Wikipedia](https://en.wikipedia.org/wiki/Song_structure)). Pattison has an
  article titled "Hook Placement and Focus"
  ([list](https://www.patpattison.com/quotes-books-articles)), which was not
  read.
- He says key lines land better when the listener gets space after them. He
  also says a specific title can say a familiar thing more vividly than a
  generic one ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
- **Not verified:** the common rule of thumb that the title goes in the first
  and/or last line of the chorus. It is widely repeated but I found no primary
  statement of it. Pattison's "power positions" chapter probably covers it, but
  I could not read it.

### 1.3 Rhyme types and schemes

- Pattison's rhyme families, from his course outline: **perfect, family,
  additive/subtractive, assonance and consonance**
  ([Coursera module 3](https://www.coursera.org/learn/songwriting-lyrics)). In
  plain terms:
  - *Perfect*: same stressed vowel and same sounds after it.
  - *Family*: same vowel, with final consonants from the same phonetic group.
    This definition comes from secondary write-ups; the book was not read.
  - *Additive/subtractive*: same vowel, with a consonant added or dropped after
    it ([iZotope](https://www.izotope.com/en/learn/5-types-of-rhymes-you-can-use-in-your-song)).
  - *Assonance*: only the vowel matches.
  - *Consonance*: only the final consonants match.
- Pattison ranks these by how settled they sound: perfect rhyme closes a line
  firmly, and more remote types leave it open. He uses remote types on purpose
  to add tension, and calls these "tools, not rules"
  ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics);
  his article "Tools, Not Rules" is on [his list](https://www.patpattison.com/quotes-books-articles)).
- **Schemes affect stability.** ABAB feels settled. ABBA, or a line left
  unrhymed, feels unsettled ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
  His course calls rhyme scheme "Sonic GPS": it tells the listener where they
  are in the section ([Coursera](https://www.coursera.org/learn/songwriting-lyrics)).

### 1.4 Prosody: fitting words to music and to meaning

- Pattison defines prosody as the fit between form and content. Every element
  should support what the lyric says
  ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
- **Stable and unstable** is his main lens. The tools are:
  - number of lines: even feels settled, odd does not
  - line length: matched lengths feel settled, shorter or longer lines do not
  - rhyme scheme (see 1.3)
  - where a phrase starts against the bar: starting after the downbeat changes
    the feel

  Sources: [Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics),
  [Coursera module 2](https://www.coursera.org/learn/songwriting-lyrics).
- **Stress and melody.** The course teaches stressed and unstressed syllables,
  one- versus multi-syllable words, and how the rhythm of the words fits the
  rhythm of the melody. Students then set their verse and chorus to music
  ([Coursera module 4](https://www.coursera.org/learn/songwriting-lyrics)). The
  practical rule is that naturally stressed syllables should fall on strong
  beats and long notes. That is my paraphrase of the course aim, not a quotation.
- **Lyric shape in the pre-chorus.** Units shorten and phrases run together to
  build momentum ([Summach](https://www.mtosmt.org/issues/mto.11.17.3/mto.11.17.3.summach.html)).
  This is prosody at the level of a whole section.

### 1.5 Point of view, and "show, don't tell"

- The course opens with point of view as a basic development tool, alongside
  song form and Pattison's "Boxes" method for developing one idea through the
  song ([Coursera module 1](https://www.coursera.org/learn/songwriting-lyrics)).
- He describes four stances: third person, second person, first person, and
  direct address (an "I" singing to a "you"). Direct address is the mainstay of
  pop, but it can get static when overused
  ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
  He has separate chapters and articles on second person as narrative and on
  dialogue ([list](https://www.patpattison.com/quotes-books-articles)).
- **Show, don't tell** is taught through **object writing**: short, timed,
  daily free-writing on one object using all the senses. The aim is specific
  sensory images that trigger the listener's own memories, so they feel inside
  the song rather than told about it
  ([Sound On Sound](https://www.soundonsound.com/techniques/pat-pattison-writing-better-lyrics)).
  It is chapter 1 of *Writing Better Lyrics*
  ([list](https://www.patpattison.com/quotes-books-articles)).

### 1.6 Common structures and section lengths

- **Verse–chorus** (with or without a pre-chorus and bridge) is the main pop and
  rock form. **AABA** (32-bar form, usually four 8-bar sections) is the older
  standard ([Wikipedia](https://en.wikipedia.org/wiki/Song_structure)).
  Variants such as ABAB and ABABCB (verse, chorus, verse, chorus, bridge,
  chorus) are also listed there.
- **Lengths.** Summach puts formal modules at roughly 8 to 24 bars. His
  examples include a 4-bar departure too short to count as a pre-chorus, an
  8-bar chorus, and a 16-bar span that splits into verse, pre-chorus and chorus
  ([Summach](https://www.mtosmt.org/issues/mto.11.17.3/mto.11.17.3.summach.html)).
- **Not verified:** corpus statistics on typical section lengths in
  guitar-led pop and rock. The de Clercq–Temperley rock corpus
  (<https://rockcorpus.midside.com/>) holds timed form annotations that could
  answer this, but I did not compute it. Treat "8 or 16 bars per section" as a
  rule of thumb, not a finding.

## 2. What could become guidance or checks in an app

Most of Pattison's framework can be checked mechanically, because it is about
counts, positions and sounds. Whether a line is *good* cannot be checked.

| Craft idea | Possible check or guide | Data needed | Confidence |
|---|---|---|---|
| Section roles (1.1) | A template per section with a one-line prompt for its job: verse = detail, pre-chorus = build, chorus = title and main idea, bridge = new angle | None | High: text guidance only |
| Title first (1.2) | Ask for a title before the lyric step. Show where it appears in the chorus. Flag a chorus without it | String match | High |
| Line count and length (1.4) | Show lines per section and syllables per line, and mark which lines differ from their partner | Syllable counts (CMU dictionary or Datamuse `md=s`) | High for dictionary words; lower for slang, names and dialect |
| Rhyme scheme (1.3) | Label line endings A/B/C and name the scheme; label each pair as perfect, additive/subtractive, assonance or consonance | Phonemes and stress from the CMU dictionary | Medium: needs a small classifier over the phonemes |
| Rhyme suggestions | Show perfect and near rhymes on request, filtered by syllable count | Datamuse `rel_rhy` / `rel_nry` / `sl`, or local CMU dictionary | High (see 3.1) |
| Stress vs bar (1.4) | Mark stressed syllables (CMU stress digits 1/2) against beats in the bar the user placed them on, and flag stressed syllables that fall on weak beats | Stress marks, plus the user's word-to-beat placement | Medium: needs a melody or rhythm grid to exist in Band mode; words with two possible stresses are ambiguous |
| Fit to section length (1.6) | Compare line count and syllables with the bars in that section of the chord progression | Bar counts already in Band mode's structure | Medium |
| Object writing / show, don't tell (1.5) | A timed sense-prompt exercise (sight, sound, smell, taste, touch, body, motion) before drafting | None | High as an exercise; judging "showing" is not checkable |
| Point of view (1.5) | Ask who is speaking to whom; flag pronoun drift between sections | Pronoun counts | Medium: drift is sometimes deliberate |

Example from the CMU dictionary, checked live: *guitar* is `G IH0 T AA1 R`,
with primary stress (1) on the second syllable; *heartbreak* is
`HH AA1 R T B R EY2 K`, with secondary stress (2) on *-break*
([cmudict.dict](https://github.com/cmusphinx/cmudict)). That is enough data to
count syllables, find stress and compare endings.

## 3. AI and lyric tools today

### 3.1 Rhyme and pronunciation data (deterministic, no generation)

- **CMU Pronouncing Dictionary.** About 135,000 entries (counted in the current
  `cmudict.dict`, 27 Oct 2026), a 39-phoneme ARPAbet set, and stress marked 0/1/2
  on vowels. Licence: BSD-style; the README says use for research or commercial
  purposes is "completely unrestricted", with acknowledgement requested
  ([repo](https://github.com/cmusphinx/cmudict)). Caveats: it is **American
  English** (so UK accents, where *r* after a vowel is dropped, will rhyme
  differently), and the maintainers expect errors and omissions.
- **Datamuse API** (it powers RhymeZone and OneLook). Its current page documents
  `sl` (sounds like), `md=s` (syllable count), `md=r` (pronunciation, with
  optional IPA) and the related-word relations
  ([docs](https://www.datamuse.com/api/)). `rel_rhy` (perfect rhyme) and
  `rel_nry` (near rhyme) are **missing from the current docs page but still
  worked** when I tested them on 27 Oct 2026. They are described in third-party
  wrappers ([Microsoft connector](https://learn.microsoft.com/connectors/datamuseip/)).
  Limits: free without a key "until January 1, 2027". After that the page says
  a key will be needed, with 100,000 requests a day per key. Note that the page
  gives two different dates (1 January and 1 February 2027). Public apps should
  credit Datamuse. Customer-facing apps are asked to describe their app and
  traffic. Query logs are kept for a day ([docs](https://www.datamuse.com/api/)).
  I found no explicit commercial terms on the current page.
- **MasterWriter.** A paid suite: rhyme dictionary (100,000+ entries, filters
  for perfect, close and wide rhymes, search by syllable), 33,000+ phrases,
  "Word Families", figures of speech, and a thesaurus. The current songwriting
  page mentions **no AI features** and lists no price, only a 90-day trial. It
  says the writer's mind and heart can't be replaced
  ([MasterWriter](https://masterwriter.com/songwriting/)). It is a
  reference-tool model: suggestions only, with the writer choosing.

### 3.2 Generative assistants

- **General LLM chat assistants** can brainstorm, suggest alternative lines,
  explain a technique, or critique a draft against a checklist. The
  weaknesses that matter are below (3.3).
- **Dedicated lyric assistants** such as LyricStudio describe themselves as
  line-suggestion and rhyme helpers where the user accepts, edits or ignores
  each suggestion. I found **only directory and review pages**, not first-party
  documentation, so the details are unverified
  ([example listing](https://getcoai.com/tool-detail/lyricstudio/164322/)).
- **Full-song generators** such as Suno write whole lyrics and audio. This is
  the opposite of "help, don't write". Their terms limit what you can do with
  the output: free-plan songs are for non-commercial use only and remain owned
  by Suno; paid plans grant commercial-use rights, but Suno does not describe
  that as ownership ([Suno help](https://help.suno.com/en/articles/2416769)).
- **Research systems built around writer control.** *CoLyricist* interviewed 10
  lyricists and found four stages: theme setting, ideation, drafting and melody
  fitting. It offers AI support tailored to each stage. In a 16-person study,
  novices valued melody fitting most, and experienced writers valued ideation
  ([arXiv 2602.22606](https://arxiv.org/abs/2602.22606); preprint, not peer
  reviewed). The stage model is close to the step-by-step flow Band mode
  imagines.

### 3.3 Quality concerns

- **Counting and rhyme are weak spots for LLMs.** PhonologyBench found models
  45% behind humans on syllable counting and 17% behind on generating rhyme
  words ([arXiv 2404.02456](https://arxiv.org/abs/2404.02456)). A plausible
  reason is that subword tokens do not line up with syllables. A deterministic
  dictionary is therefore more reliable for counts and rhymes than asking a
  model.
- **Sameness.** In a 500-person experiment, story ideas from an LLM made
  stories rated more creative, with the gain mostly among the least creative
  writers. But the AI-assisted stories were more alike, both to each other and
  to the AI's ideas ([Doshi & Hauser 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11244532)).
  This is evidence about stories, not lyrics, but the same risk applies:
  beginners get the most help and also drift towards the model's clichés.
- **Clichés and generic lines.** Pattison's emphasis on specific, sensory
  detail (1.5) runs directly against the generic phrasing models default to. I
  found no study that measures cliché rate in AI lyrics.

## 4. Rights in AI-written lyrics

- **United States.** Copyright needs a human author. The Copyright Office's
  Part 2 report (29 Jan 2025) concludes that, with current tools, prompts alone
  do not give enough control to make the user the author. Human selection,
  arrangement or creative changes to AI output can be protected
  ([USCO AI page](https://www.copyright.gov/ai/);
  [Copyright Alliance summary](https://copyrightalliance.org/ai-report-part-2-copyrightability/)).
  The 2023 registration guidance says AI material that is more than
  de minimis should be **excluded and disclosed** when registering
  ([guidance PDF](https://www.copyright.gov/ai/ai_policy_guidance.pdf)).
  Practical effect: the parts the writer writes are theirs; lines the AI wrote
  verbatim may not be protected.
- **United Kingdom.** CDPA s9(3) still treats a computer-generated work (one
  with no human author) as authored by the person who made the arrangements
  for it ([legislation.gov.uk](https://www.legislation.gov.uk/ukpga/1988/48/section/9)).
  The government's Copyright and AI report (18 March 2026) proposes removing
  that protection, sets no timetable, and leaves AI-*assisted* works unchanged
  ([Stephenson Harwood summary](https://www.stephensonharwood.com/post/102mpke/uk-government-publishes-report-and-impact-assessment-on-copyright-and-artificial-intelligence-the-debate-continues/)).
  I did not read the gov.uk report itself.
- **Tool terms come on top of the law**, as the Suno example shows (3.2).
- A writer-led flow, where the user writes and the AI suggests or critiques,
  keeps the lyric clearly human-authored in both countries. A flow where the AI
  drafts and the user picks is the case the US guidance treats as weakest.
  This is a reading of the sources, not legal advice.

## 5. Not reproducing existing lyrics

- **Memorisation is real and has been ruled on.** The Munich Regional Court
  held on 11 Nov 2025 that ChatGPT models contained copies of nine songs'
  lyrics and output them in response to simple prompts. It found infringement
  and held that the text-and-data-mining exception does not cover storing and
  outputting lyrics ([GEMA](https://www.gema.de/en/w/landmark-ruling-gema-against-openai);
  [Bird & Bird](https://cm.twobirds.com/en/insights/2025/landmark-ruling-of-the-munich-regional-court-(gema-v-openai)-on-copyright-and-ai-training)).
  It is a first-instance judgment, and I did not verify whether it was appealed.
- **Vendors have lyric guardrails.** In *Concord v Anthropic* (N.D. Cal.), a
  court-approved stipulation in late Dec 2024 / Jan 2025 requires Anthropic to
  keep its existing guardrails against reproducing the publishers' lyrics,
  extend them to future models, and respond to reported failures. The
  technical details are redacted, and the training dispute continued
  ([MBW](https://musicbusinessworldwide.com/universal-music-concord-music-abkco-welcome-court-approved-guardrails-in-anthropic-ai-dispute);
  [Bloomberg Law](https://news.bloomberglaw.com/ip-law/anthropic-agrees-to-enforce-copyright-guardrails-on-new-ai-tools)).
  I did not check later developments in the case. (Disclosure: this note was
  written with an Anthropic model.)
- **What an app can add on its own side** (my synthesis; none of these
  techniques comes from the sources above):
  - Do not ask the model for "lines like [named song]". Prompt for techniques,
    and give the user's own draft as context.
  - Keep AI suggestions short (single lines or words), so a long memorised
    passage is less likely.
  - Store which text the user wrote and which suggestions they accepted.
  - Do not ship a corpus of existing lyrics as examples. Craft guidance can be
    taught with invented examples.

  A matching-based filter against a lyrics database would need a licensed
  lyrics corpus. I found no public, licensable source for that.

## 6. What this means for Band mode

Options, not decisions.

**Craft that can become guided steps**

1. *Idea and point of view*: who is speaking to whom, and what happens
   (Pattison module 1).
2. *Title first*: write and say the title aloud. Later, place it in the chorus
   (Berklee OSONG-221).
3. *Object writing warm-up*: a short sense-prompt exercise before drafting.
4. *Section-by-section drafting*, each with a one-line job description:
   verse detail, pre-chorus build, chorus title and main idea, bridge new
   angle.
5. *Shape and stability*: line counts, lengths and rhyme scheme, explained as
   choices ("this feels settled or unsettled"), not as errors. This matches
   Pattison's "tools, not rules".
6. *Fit to the music*: compare syllables and stresses with the bars and beats
   of the section's chord progression.

**Checks and tools: possible now**

- Syllable counts per line, rhyme-scheme labels, rhyme-type labels and stress
  marks, from the CMU dictionary (free, commercially usable, about 135k words;
  American pronunciation).
- Rhyme and near-rhyme suggestions, through Datamuse or locally from the CMU
  dictionary.
- Section templates and title presence or placement checks (pure text logic).
- An LLM in a **coach** role: questions, technique explanations, and critique
  of the user's own draft against the checklist above, with no whole-song
  drafting.

**Possible with caveats**

- Datamuse in production: needs an API key from early 2027, the rhyme
  parameters are now undocumented, and commercial terms are unclear. A local
  CMU dictionary avoids all three.
- LLM line suggestions: weak at counting and rhyme (so pair them with the
  deterministic checker), tend to cliché and sameness, carry a memorisation
  risk (keep suggestions short, never prompt with named songs), and weaken
  copyright in any text accepted verbatim.
- UK pronunciation: rhymes and syllables follow US English unless a UK lexicon
  is added. None was assessed here.
- Stress-on-beat checks: only possible once Band mode places words on beats.
  Words with variable stress need the user to confirm.

**Research-grade**

- Automatic melody fitting (setting a lyric line to a generated or sung
  melody): CoLyricist shows demand, but it is a preprint, not a component you
  can use.
- Judging quality: "show, don't tell", originality, and whether a line is
  clichéd. No validated metric was found.
- Detecting reproduced lyrics by matching against a licensed lyrics corpus.

## What I could not verify

- The text of Pattison's books, including the "power positions" chapter, the
  "Hook Placement and Focus" article, and his exact definition of family rhyme.
- A Berklee Online blog post by Pattison on stable/unstable prosody
  (`online.berklee.edu/takenote/?p=18154`), which returned HTTP 503.
- Open Music Theory's verse–chorus chapter (HTTP 403).
- The rule that the title goes in the first or last line of the chorus.
- Corpus figures for typical section lengths in guitar-led pop and rock.
- First-party LyricStudio documentation, and current MasterWriter pricing.
- Datamuse's commercial terms after the 2027 key change.
- Whether GEMA v OpenAI was appealed; later rulings in Concord v Anthropic; the
  gov.uk report text itself (only a law-firm summary was read).
- Any EU AI Act transparency duties for AI-suggested text (out of scope here).
