# Prisma Schema Domain Reference

Documents the purpose and usage of each model in `schema.prisma`.

## Core Entities

### Chain
A comedy club chain/brand (e.g., Improv, Helium, Funny Bone). Groups multiple Club locations under one parent brand. Has a unique name, slug, and optional brand-level website.

### Club
Comedy club venue. Has shows, tags, email subscriptions, and processed emails. Optionally belongs to a Chain via chainId FK.

### ClubAlias
Verified alternate venue names that resolve to one canonical Club before scraper discovery inserts a new club row. Aliases are global across ingestion sources and are scoped by normalized alias name, city, and state so the same venue nickname in a different market does not collide.

### Comedian
Individual comedian. Has social media stats, popularity, alternate names (aliases), favorites, and lineup appearances.

### ComedianPodcastAppearance
Episode-level evidence that a comedian appeared on a podcast episode. Rows are source-scoped by `source` and `sourceEpisodeId` and should only describe an appearance on a specific episode.

Legacy compatibility table for the first podcast ingestion path. New PodcastIndex-backed discovery should write canonical episode rows to `PodcastEpisode`, accepted graph edges to `EpisodeAppearance`, and review decisions to `EpisodeAppearanceReview`. Keep this table available for existing UI/data callers until those reads are migrated; do not use it as the source of podcast identity.

### ComedianPodcastIdentityLink
Reviewed source identity links between a comedian and an external podcast feed. For Podcast Index, `source = "podcast_index"` and `sourceFeedId` stores the feed identity returned by the provider. `reviewStatus` has three meanings: `verified` feeds are trusted for future backfills, `ambiguous` feeds require more review before they can be promoted by identity alone, and `rejected` feeds are known false positives that must be suppressed before writing episode appearance rows. This table is deliberately separate from `ComedianPodcastAppearance` so a reviewed feed relationship is not conflated with an episode appearance.

Legacy compatibility table for source feed links. New PodcastIndex-backed discovery should prefer `Podcast`, `ComedianPodcast`, and `PodcastCandidateReview` so candidate decisions can point at canonical podcast rows and preserve accepted/rejected review history. Keep this table for existing callers until the source identity workflow is moved onto the normalized graph.

### Podcast
Canonical podcast/feed identity. A row is source-scoped by `source` and `sourcePodcastId`, preserving PodcastIndex feed ids, feed URLs, external ids, provider payloads, and discovery evidence without tying identity to any one comedian.

### PodcastEpisode
Canonical episode identity under a podcast. A row is unique by `source` and `sourceEpisodeId` so the same episode is stored once even when multiple comedians appear on it.

### ComedianPodcast
Reviewed comedian-to-podcast association such as host, cohost, owner, producer, network, or other. This table represents podcast ownership/hosting relationships only; it does not imply a guest appearance on every episode. Episode-level participation belongs in `EpisodeAppearance`.

### PodcastCandidateReview
Review queue and audit log for candidate comedian-to-podcast associations. Accepted and rejected candidates remain stored with source ids, confidence, evidence, review status, reviewer, and optional canonical podcast linkage.

### EpisodeAppearance
Accepted or pending graph edge connecting a comedian to a specific podcast episode. This is the normalized replacement for new episode appearance writes and is separate from `ComedianPodcast`, so hosts are not automatically treated as episode guests.

### EpisodeAppearanceReview
Review queue and audit log for candidate episode appearances. Stores accepted and rejected candidates with source episode ids, confidence, evidence, review status, reviewer, role, and optional canonical episode linkage.

### Show
A comedy show at a club on a date. Has lineup items, tickets, and tags.

### Ticket
A ticket option for a show (price, purchase URL, type, sold-out flag).

### LineupItem
Join table linking a Comedian to a Show.

## User & Auth

### User
NextAuth user record (email, name, image).

### UserProfile
Extended user profile (role, zip code, notification preferences, favorite comedians).

### AdminActionAudit
Durable audit trail for admin mutations. Each row records the actor profile when available, action name, entity type/id, optional reason, before/after JSON snapshots, and creation timestamp. Actor deletion preserves audit rows by nulling the actor reference.

### Account
OAuth account linked to a User (provider, tokens).

### RefreshToken
Long-lived refresh tokens issued to native clients (iOS). Supports rotation and revocation so an exfiltrated access token cannot be used to mint new sessions indefinitely.

**Fields:**
- `id` — primary key (cuid)
- `token` — opaque 64-char hex string (unique); the value handed to the client
- `userId` — FK to `User` (cascade on delete)
- `expiresAt` — when the token stops being accepted (30 days after issue)
- `revokedAt` — when the token was invalidated (nullable; set on rotation or sign-out)
- `createdAt` — when the token was issued

**Usage:** Issued alongside a short-lived access JWT by `POST /api/v1/auth/token`. Consumed by `POST /api/v1/auth/refresh` — the submitted token is atomically marked `revoked_at=NOW()` and a new access+refresh pair is returned. `POST /api/v1/auth/signout` revokes every active token for the caller.

### VerificationToken
Email verification tokens for NextAuth.

### FavoriteComedian
User's favorited comedians (join table: UserProfile ↔ Comedian).

## Tagging

### Tag
A tag with type, name, slug, and visibility. Can be applied to clubs, shows, or comedians.

### TaggedClub
Join table: Club ↔ Tag.

### TaggedShow
Join table: Show ↔ Tag.

### TaggedComedian
Join table: Comedian ↔ Tag.

## Email Ingestion

### EmailSubscription
Tracks newsletter email subscriptions per club. One subscription per club (`clubId` unique).

**Fields:**
- `clubId` — FK to Club (unique; one subscription per club)
- `senderDomain` — email domain to expect newsletters from (e.g. `"thecomedystore.com"`)
- `subscribed` — whether the subscription is active (default `true`)
- `lastReceived` — timestamp of the last successfully received email (nullable)
- `createdAt` — when the subscription was created

**Usage:** Ingestion pipeline checks `subscribed` before processing emails from a given sender domain. `lastReceived` is updated each time an email from this club is successfully processed.

### ProcessedEmail
Deduplication log for ingested newsletter emails. Prevents re-ingesting the same message.

**Fields:**
- `messageId` — unique email Message-ID header value (unique index)
- `clubId` — FK to Club
- `receivedAt` — timestamp from the email headers
- `processedAt` — when the scraper processed the email (default `now()`)

**Usage:** Before processing any email, check whether `messageId` already exists in this table. If so, skip. After processing, insert a new row to mark the email as done.
