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
