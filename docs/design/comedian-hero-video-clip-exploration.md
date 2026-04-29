# Comedian Hero Video Clip Exploration

Date: 2026-04-29
Status: Deferred, decision captured
Scope: `apps/web`

## Context

The current comedian detail hero is optimized around a full-bleed headshot, social proof, a primary show/notification CTA, bio, and social links. There is no existing clip URL or clip metadata field on the `Comedian` Prisma model or `ComedianDTO`; current social data stores platform handles and follower counts only.

The Spotify-like product move behind this task is valid: let a user sample the performer immediately. For LaughTrack, the first implementation should avoid building a full video ingestion product before proving that clips improve detail-page engagement.

## Sourcing Decision

Use manually curated YouTube embeds as the first source, stored per comedian as a single canonical clip URL or video ID. Do not use Instagram Reels as the first implementation path, and do not self-host clips until the product has explicit rights, moderation, transcoding, and CDN requirements.

Recommended source priority:

- Primary: YouTube video or Short from the comedian's own channel, label/publisher channel, club channel, or another rights-cleared source.
- Later: self-hosted short clips only after a rights and media pipeline exists.
- Avoid for MVP: Instagram Reels as primary embeds because Meta oEmbed access is API/review-gated and less predictable for a lightweight detail-page feature.

Why YouTube first:

- The existing data model already tracks `youtube_account`, so YouTube is the closest match to current comedian social metadata.
- YouTube supports standard iframe embeds and explicit player parameters, including `autoplay`, `controls`, `start`, `end`, and `playsinline`.
- YouTube embeds avoid first-party storage, transcoding, and CDN work while the product validates whether clips belong on the comedian page.

Implementation implication:

- Add a small future schema surface such as `comedian_clips` or a nullable `featuredClip` relation rather than overloading `youtubeAccount`. A clip is content, not an account handle.
- Store source platform, source URL/video ID, title, thumbnail URL if available, duration if known, and curation status.

Sources:

- YouTube embedded player parameters: https://developers.google.com/youtube/player_parameters
- Current app model checked in `apps/web/prisma/schema.prisma` and `apps/web/objects/class/comedian/comedian.interface.ts`

## Licensing Decision

Only feature clips that are explicitly rights-cleared for LaughTrack use. For MVP, that means one of:

- The comedian or their representative submitted/approved the exact clip URL for use on their LaughTrack profile.
- The clip is from the comedian's own official YouTube channel and the comedian has opted into profile enrichment.
- The clip is from a venue, label, publisher, or podcast channel where LaughTrack has written permission or a documented partnership allowing profile-page embeds.

Do not automatically scrape and feature arbitrary YouTube Shorts, Instagram Reels, TikToks, or fan uploads based only on matching a comedian name. Name matching is too error-prone, and public availability is not the same as product permission to make that clip the primary content moment on a commercial detail page.

YouTube's terms allow viewing through the embeddable player, but the same terms distinguish platform-enabled playback from independent use of the underlying content. The product should therefore treat YouTube as the playback mechanism, not as a blanket content-rights solution.

Implementation implication:

- Add moderation fields before launch: `approvedBy`, `approvedAt`, `rightsSource`, and `status`.
- Keep the feature behind a curation workflow rather than automatic scraper enrichment.
- Use platform embeds for playback. Do not download, crop, transcode, or re-host third-party clips without a separate rights path.

Sources:

- YouTube Terms of Service, permissions and restrictions: https://www.youtube.com/t/terms
- YouTube Help on commercial uses of embedded players: https://support.google.com/youtube/answer/71011

## Autoplay And Sound Decision

Do not autoplay comedian clips with sound. The default interaction should be click-to-play with sound controlled by the user.

Accepted behavior:

- Default state: show a still thumbnail or paused embed with a clear play affordance.
- User action: tapping/clicking the clip starts playback with sound according to the embedded provider's controls.
- Optional later enhancement: muted inline preview on capable browsers, only when it does not add layout shift, data overuse, or cross-origin player complexity.

Rejected behavior:

- Sound-on autoplay on page load.
- Hidden or control-less playback that makes it unclear where audio is coming from.
- Treating muted autoplay as required for MVP.

Why:

- Chrome allows muted autoplay, but autoplay with sound depends on prior user interaction, site engagement, installation state, or iframe permission delegation. That makes sound-on autoplay inconsistent and inappropriate as the primary behavior.
- A comedian clip is a sample moment, not background video. A deliberate play action creates a clearer product contract and avoids surprising users on mobile or in public contexts.
- YouTube supports `autoplay` and `playsinline`, but the app does not need IFrame API complexity until it has measured demand for richer playback controls.

Implementation implication:

- MVP can render a YouTube iframe only after the user clicks the thumbnail, reducing initial third-party load and avoiding unwanted playback.
- If a muted preview is added later, include `muted`, `playsinline`, and visible controls/unmute affordance where the provider permits it.

Sources:

- Chrome autoplay policy: https://developer.chrome.com/blog/autoplay/
- Chrome muted mobile autoplay behavior: https://developer.chrome.com/blog/autoplay-2/
- YouTube embedded player parameters: https://developers.google.com/youtube/player_parameters

## Hero Placement Decision

Place the clip below the comedian name/stat block and before the long bio/social row when a curated clip exists. Do not replace the full-bleed hero photo, and do not place the video as a decorative overlay on top of the headshot.

Recommended layout:

- Desktop: keep the current full-bleed image hero, with identity/CTA content on the readable side. Add a compact clip module below the name/stat area, constrained to a stable aspect-ratio box.
- Mobile: show the name, stat, primary CTA, then the clip module before the full bio. This keeps the show/notification action reachable without forcing a video iframe above the fold on every profile.
- No clip available: render the current hero unchanged.

Why:

- Replacing the headshot makes comedian identity dependent on clip availability and would produce inconsistent profile quality across the catalog.
- Overlaying video on the hero image risks text/control collisions, poor contrast, and unpredictable embed controls inside an already dense hero.
- A below-name placement gives the clip high prominence while preserving the existing hero's strongest job: immediate recognition of the comedian and a clear next-show action.

Implementation implication:

- Build this as an optional `FeaturedComedianClip` component owned by the comedian detail header area.
- Reserve stable dimensions with `aspect-video` for landscape clips and a bounded portrait mode if Shorts become common.
- Lazy-load the iframe after user intent where possible, using a thumbnail/button shell first.
- Keep "See next show" or "Notify me about shows" as the primary CTA. The clip is a sampling moment, not the conversion target.

## Open Follow-Up Work

This task answers the product questions but does not ship the feature. A future implementation task should cover:

- Schema and migration for curated featured clips.
- Admin or operational curation workflow.
- YouTube thumbnail/embed helper and provider validation.
- Comedian detail UI component and responsive visual QA.
- Analytics to compare clip engagement against show CTA engagement.
