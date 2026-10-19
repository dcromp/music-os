# Sources for a curated YouTube guitar pilot

**Checked 19 October 2026.** Research for [Establish feasible sources for the curated YouTube pilot](https://github.com/dcromp/music-os/issues/20), within [Find the route to a curated YouTube guitar play-along pilot](https://github.com/dcromp/music-os/issues/19). Public documentation was reopened; no supplier was contacted, account opened or music downloaded.

## Question and result

What can supply official video playback, matching analysis inputs or timed chord data, and teaching arrangements for a free private pilot of 10–20 popular rock/pop songs, with a possible low-price product later?

**There are documented components and supplier leads, but no verified end-to-end content package or price.** Official embedding supports playback. Analysis audio and reusable teaching/data content need their own evidenced basis. A viable specification can keep these sources separate and choose among the options below. This finding neither clears a catalogue nor replaces the popular-song goal with original exercises.

## Established playback facts

YouTube permits showing videos through its embedded player; that permission does not grant unrestricted reuse of the content. The applicable regional terms still matter. [YouTube Terms, Permissions/Reservation](https://www.youtube.com/t/terms)

The developer policies allow selling a compliant API client, prohibit charging for embedded viewing, and restrict downloading/caching YouTube audiovisual content without prior written approval. They prohibit separating audio/video, blocking ads or player functionality, and hidden background playback. Independently obtained data must be distinguished from YouTube data. Our proposed implication: offer our arrangements, practice patterns and learning path beside the visible official player; review the actual subscription boundary before charging. Normal product login can be allowed, so a private invitation is not automatically prohibited. The client also needs the required terms/privacy disclosures. [Policies III.A, III.E.1/4, III.F.3, III.G, III.I](https://developers.google.com/youtube/terms/developer-policies)

The IFrame API provides playback state, elapsed seconds, seeking and available playback rates. Seeking can land at a preceding keyframe; exact musical loops are not guaranteed. Errors identify missing/private videos, disabled embedding and missing client identification (153). These are technical integration/availability requirements, not an analysis-audio interface. [IFrame API](https://developers.google.com/youtube/iframe_api_reference)

## Candidate input and teaching routes

These are **options to decide**, not grants obtained:

| Route beside official playback | What it enables | What remains unresolved |
|---|---|---|
| Independently authored chord/timing annotations and practice arrangement | A small catalogue could be prepared without extracting a YouTube audio file. Suggested strumming can be authored as an exercise rather than copied from a teacher. | Record how annotations are created and the basis for displaying/adapting this particular composition/arrangement. Independent authoring alone does not settle every use. Manual preparation effort is unmeasured. |
| Separately permitted recording supplied by an authorised source | Run the existing automatic analysis once, retain drafts separately, then review. The analysis input need not be served to learners. | Terms must address acquisition, retention, machine processing, relevant third-party processors and downstream derived data. Confirm the source controls the required rights and supplies the same performance/edit as the video. No matching master or quote has been obtained. |
| Licensed teaching/chord data, with timing commissioned or supplied separately | Reduce transcription work; possibly obtain permitted arrangements and adaptations. | Verify repertoire, export/display rights, simplification/transposition, exact recording timelines and data retention. Buying ordinary sheet music or using a retail API does not establish these product rights. |

Composition and recording are distinct rights categories, commonly owned/licensed separately; the US Copyright Office explains that distinction but does not determine Norwegian or worldwide clearance. [Copyright Office](https://www.copyright.gov/register/pa-sr.html) For Norway, TONO documents online/app licensing and distinguishes composition from recording permissions. Its published mobile-app tariff is not a quote for this browser/embed design, and its audiovisual categories do not decide whether our precise timed display requires additional permission. Specify the use and territories for targeted review rather than importing a generic tariff. [TONO Online](https://en.tono.no/kunder/online/)

Concrete supplier/data leads:

- **Hal Leonard Connect** explicitly invites rights/content requests for products or platforms and describes a retail catalogue API. That makes it a relevant enquiry route; the retail sale/delivery workflow does not itself promise machine-readable chords, timestamps, master-analysis rights or subscription redistribution. Repertoire coverage and custom fees are unpublished on the reviewed page. [Hal Leonard Connect](https://connect.halleonard.com/)
- **Hooktheory** documents next-chord probabilities and songs containing a progression, not a complete recording-specific timing feed. Its terms restrict scraping, mining and redistribution without express authorisation. A data licence/API agreement would need to cover the intended use; public browsing is not that grant. [API](https://www.hooktheory.com/api/trends/docs), [terms](https://api.hooktheory.com/terms)
- **Songle** documents chord/beat annotations and correction tools, but its current help says new YouTube URLs cannot be registered. Existing coverage, permissible reuse and service reliability would require verification; it is not established as this pilot's catalogue supplier. [Songle help](https://docs.songle.jp/en/help/)
- **Chordify** confirms embedded YouTube playback and restricts automated collection and non-personal reuse. Its terms disclose neither our required sourcing arrangement nor a per-video payment. Do not treat it as a data licence or infer its private agreements. [Chordify terms](https://chordify.net/pages/terms-and-conditions/)

## Recording identity and acceptance

Project requirement: bind each arrangement to the exact YouTube video ID/channel, performance/edit, observed duration, annotation revision and source/permission record. Separately acquired audio needs its own recording ID/hash and documented mapping to that video. Titles, keys, covers, remasters and similar lengths do not establish equal timelines. Replacing an unavailable video requires a new timing check; never stretch old timestamps to a new duration. Keep source facts, automatic predictions, teaching simplification and reviewed timing separate.

## Costs and decisions still open

The current Data API table gives 100 daily search calls and 10,000 daily units for other endpoints (with separate upload allocation); `videos.list` costs one unit. These are request limits, **not royalties or a per-play music price**. The reviewed embed/API pages publish no per-view licence tariff for this design. [Quota calculator](https://developers.google.com/youtube/data/determine_quota_cost)

Budget **catalogue preparation** separately: permissions/agreements, any source/data purchase, one-time analysis, arrangement/timing review, corrections and device QA. Human minutes remain unmeasured. Budget **recurring service** separately: any negotiated royalties/minimums, data subscriptions, availability/replacement maintenance, hosting, support, and later payment/platform/tax costs. No supplier fee is assumed zero; no low subscription price is proven viable.

The next product decisions are the initial territories/audience, an acceptable source route for each selected recording, the permitted teaching/display scope, and tolerable preparation cost. Supplier terms may remain an explicit pre-pilot verification dependency when the specification is handed off. Free/private testing alone does not establish an exemption in this research.

The earlier [song-access comparison](SONG_ACCESS_FEASIBILITY.md) remains background. The [original-exercise route](ORIGINAL_EXERCISE_ROUTE.md) concerns a separate alternative; selecting it would change this map's confirmed popular-song destination. Existing research caches prove technical experiments, not a permission or production source.
