# Song access and launch economics

**Checked 12 October 2026.** This is a product feasibility comparison using public first-party terms, not a negotiated licence or a conclusion that the current ten-song cache can be shipped.

**Preferred route to scope first:** sell our learning paths, reviewed practice arrangements and progress tools; use the official YouTube player for available recordings, and obtain analysis audio separately under suitable permission. Start with original/artist-authorised music if popular-song permissions or prices are unsuitable. This is a recommendation, conditional on the selected content and implementation review.

## What YouTube and Chordify actually establish

YouTube permits selling an API client subject to its other terms. It prohibits charging users to watch embedded videos, downloading/caching audiovisual content without prior written approval, and separating its audio/video components. Independently sourced product data must be clearly distinguished from YouTube data. Therefore our subscription should buy our practice experience; embedded viewing must not itself be sold or paywalled. [Developer Policies, III.E.1, III.E.4.h, III.F.3 and III.G](https://developers.google.com/youtube/terms/developer-policies)

Chordify's public terms confirm that it uses YouTube API Services for embedded playback. They do not disclose its audio acquisition method, music agreements or per-video payments. They also restrict automated collection and commercial reuse of Chordify's service/content. Treat Chordify as evidence that customers buy this kind of product, not as an available data supplier or proof of our proposed sourcing economics. [Chordify terms, 2.1, 2.4, 2.8 and 9.2](https://chordify.net/pages/terms-and-conditions/)

## Three routes

| Route | Practical experience | Input and content dependency | Cost position today |
|---|---|---|---|
| Official embeds plus our own practice features | Familiar recordings with separate chord cards, suggested strumming, learning paths and progress. Retain the visible official player and its ads/controls. | Obtain the exact analysis recording from a separately permitted source, or permitted independently authored timing/chart data. Verify recording identity and player timing. Embedding supplies playback, not an analysis-audio licence. | No public per-video music tariff found in the reviewed API documentation. Analysis/content permission prices unresolved; processing and review can be measured once per permitted recording. |
| Rights-cleared originals/artist partnerships; user-supplied recordings | Local practice can support the full audio workflow, with analysis and repeat/speed features allowed by the chosen agreement. A user's own guitar performance is a useful input. | Artist agreement must cover the recording and relevant composition/content uses. A supplied file is not, by itself, evidence of permission to redistribute its audio or teaching arrangement. Keep private analysis and a shared catalogue distinct. | Original exercises have production/review costs. Partnerships may have negotiated fees or revenue shares; no quote obtained. Local analysis can reduce server expense, but does not settle content permissions. |
| Licensed popular-song catalogue | Controlled versions, stable availability and potentially downloadable practice, stems or part removal. | Negotiate the intended playback, analysis, storage, teaching/arrangement and territory uses; ask for stem/part-removal rights specifically if wanted. Determine which suppliers control each requested use. | Fees, minimum guarantees, royalties and available repertoire unknown. Do not assume a $4–$5 subscription supports them before receiving terms. |

The route descriptions are product proposals. YouTube grants other users access through enabled service features, while retaining rights not expressly granted; it does not grant a general right to reuse recordings elsewhere. Original or separately licensed inputs avoid making the analysis pipeline depend on extraction from an embed. [YouTube Terms, “Reservation” and “Licence to Other Users”](https://www.youtube.com/t/terms)

## Playback capabilities and limits

The official IFrame API exposes play/pause, elapsed time and seeking. Playback rates depend on the video: query available rates and observe the change event. Seeking may start at a nearby keyframe, so section repeats need actual device testing; do not promise precise musical loops from these methods alone. Removed/private videos and disabled embedding have explicit errors. The documented player is not a raw waveform or stems API. [IFrame Player API](https://developers.google.com/youtube/iframe_api_reference)

The public policy guide excludes offline downloads outside YouTube Premium, separated tracks, background playback, blocked ads and altered standard player functionality. Consequently “remove the guitar”, offline playback and a screen-off backing band belong to an independently authorised audio route; an ordinary embed is insufficient. Our practice features should retain value without YouTube playback. [YouTube policy guide](https://developers.google.com/youtube/terms/developer-policies-guide)

## Quota is not music licensing

The current Data API documentation allocates **100 `search.list` calls/day**, a separate **100 `videos.insert` calls/day**, and **10,000 units/day for other endpoints**. `videos.list` costs one unit per request. These are request quotas, not money or royalties per listen; the reviewed pages contain no public tariff authorising audio extraction or catalogue reuse. Older advice that every search costs 100 shared units is inconsistent with the current table. [Quota Calculator, updated 8 October 2026](https://developers.google.com/youtube/v3/determine_quota_cost)

A curated catalogue can select IDs once and make bounded availability checks instead of performing a search for every play. Estimate those Data API requests separately from IFrame playback and from our own hosting. Additional quota requires a compliance audit/request, not a published pay-per-video purchase. [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits)

## What the experiments prove, and the next decision

The local importer, saved charts and Mac player establish technical acquisition, analysis and practice-display behaviour. They do not establish commercial permission or a production audio source. Keep those research caches out of the proposed shipped catalogue until its route is resolved. Open research recordings also do not establish rights to the popular-song repertoire.

Continue algorithm work now. Before the paid pilot, prepare the selected route's concrete player/content design for targeted review, identify a small permitted launch catalogue, and obtain actual supplier terms where necessary. No founder transcription or vendor contact is required to complete the current technical milestone.

Measure two budgets: **catalogue creation** (permission, decoding/inference, arrangement review and corrections per recording) and **recurring service** (content fees, hosting/storage, support and payment/platform fees per active payer). Record correction minutes and analysis runtime now; leave unquoted rights fees explicitly unknown. Compare the eventual net subscription contribution against these costs before setting an unlimited catalogue promise.
