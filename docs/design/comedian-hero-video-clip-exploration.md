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
