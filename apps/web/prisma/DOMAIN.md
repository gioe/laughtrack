# Prisma Schema Domain Reference

Documents the purpose and usage of each model in `schema.prisma`.

## Core Entities

### Chain
A comedy club chain/brand (e.g., Improv, Helium, Funny Bone). Groups multiple Club locations under one parent brand. Has a unique name, slug, and optional brand-level website.

### Club
Comedy club venue. Has shows, tags, email subscriptions, and processed emails. Optionally belongs to a Chain via chainId FK. `clubType` is the accepted venue taxonomy: `club` for comedy-first fixed venues, `venue` for mixed-purpose physical hosts with real comedy programming, `festival` for seasonal comedy festivals, `producer` for organizer identities that are not public physical venues, `secret_location` for intentionally undisclosed venue placeholders, and `non_comedy` for hidden discovery placeholders that prevent re-inserting reviewed non-comedy venues. Only `festival` has scraper scheduling semantics today; all other values are classification metadata unless a caller explicitly opts into them. `googlePlaceId` caches the resolved Google Places identifier (text-searched by name + city/state) so the venue can be re-queried without re-resolving; `googlePlaceAttribution` stores the Google Places photo's required author attributions as a JSON array of `{displayName, uri, photoUri}` when a club image is sourced from Places rather than the club website. Both are populated server-side by the scraper's `source_club_images` job — `GOOGLE_PLACES_API_KEY` is read only in the scraper and is never exposed to the web client.

### ClubDiscoveryProfile
Derived club-level programming summary used for discovery and filtering. One row per Club stores the dominant `primaryShowType`, raw `showTypeCounts`, comedy and non-comedy classified show counts, whether the club has mixed programming, a 0–1 confidence score, and `computedAt`. This table is derived from `shows.showType`; do not treat it as manually-authored venue identity. `clubs.clubType` remains the operational venue/entity taxonomy, while ClubDiscoveryProfile describes the current show mix for user-facing discovery.

### VenueDenyList
Reviewed venue discovery rejection keyed by Google Places id. `reason` remains the human-readable audit note, while `googlePrimaryType` stores Google's structured primary type when known and `evidence` stores machine-readable triage details such as legacy reason text, matched club id/type, calendar evidence, or source workflow. `discover-nearby` uses this table to classify denied venues and preserve non-comedy evidence instead of resurfacing them as generic new club candidates.

### ScrapingSource comedy ingestion policy
Each source independently owns `comedyPolicy` (`unreviewed`, `comedy_only`, or `mixed`) and `comedyGateMode` (`off`, `shadow`, or `enforce`). Policy describes reviewed feed trust, not venue directory eligibility. Sibling feeds at one club can differ. These fields never inherit chain or SourceTarget metadata. `Club.clubType`, visibility, source `enabled`, and platform identity do not imply comedy trust.

The additive migration initializes every existing source to `unreviewed` / `off`; new sources have those same defaults. This task only supplies configuration: no ingestion filter is activated. Future gates interpret `off` as bypass, `shadow` as evaluate without changing ingestion, and `enforce` as applying their decisions. The scraper loader tolerates missing policy columns during code-before-DDL deployment.

`comedyReviewedBy` identifies the reviewing operator or process, `comedyReviewEvidence` is a JSON object holding review reasons and supporting evidence, and `comedyReviewedAt` is database-generated. Non-default inserts and policy, mode, reviewer, or evidence changes require a nonempty reviewer and evidence object. The database owns `comedyPolicyVersion`: inserts start at 1 and each such change increments it; no-op and unrelated updates preserve it. Direct assignments cannot reset versions or forge timestamps. The fields describe the latest review, not a complete revision history.

Any later cached or staged classification must retain `(source_id, comedy_policy_version)` and check both against the current source before reuse or publication. A mismatched version invalidates the decision and requires re-evaluation; a version match alone is not affirmative comedy evidence. Classifier and staging integration belongs to TASK-4153/4154. The scraper `save_source_comedy_policy` helper uses the expected revision to reject stale concurrent writes and runs inside the caller's transaction.

Operational rollback sets `comedyGateMode` back to `off` with reviewer/evidence; it advances the revision and preserves source ID, owner, enabled status, and fetch configuration. Do not drop the new columns or reset the version to roll back enforcement. Migration validation executes the real SQL against isolated PostgreSQL, optionally seeded with the production identity/configuration projection through `SOURCE_POLICY_SNAPSHOT`.

### ComedyEventCandidate / ComedyEventDecision / ComedyEventPublication
Source-scoped staging separates candidate identity from public show identity. A candidate is unique by `(source_id, event_key)` and retains its venue and first/last observation times. The event key is native: plus the source performance ID when available. Otherwise fallback: prefixes the SHA-256 of the sanitized event URL, occurrence date normalized to UTC, whitespace-normalized room, and club ID. Legacy naive dates are interpreted as UTC, matching Show identity semantics. Missing both native identity and URL fails staging. Without native identity a reschedule produces a new candidate; no URL-only recurring-event identity is assumed. Different sources retain independent candidates even when they publish to the same show.

Decisions retain normalized payload, SHA-256 payload fingerprint, resolved identity fingerprint, policy and classifier revisions, rollout mode and full decision evidence. Repeated unchanged deliveries reuse a decision; changed evidence creates another revision. The application appends decisions and never rewrites old evidence. There is no mutable latest-decision pointer. Each staging upsert atomically increments a candidate observation generation; publication requires the exact staged generation. A newer staged delivery invalidates older publication tokens even under the same policy. An unchanged payload can reuse its immutable revision with a fresh generation, allowing legitimate reversions. Generations order database staging, not upstream fetch times. The publication join records a verified candidate/decision/show association; deleting a show removes only its publication links, retaining candidates and decision history. Sources and venues with retained candidates cannot be deleted without an explicit retention decision.

Staging runs in its own transaction before public persistence. Publication rechecks the source revision under a shared source-row lock and locks candidate rows through the public writer; policy updates cannot pass that fence concurrently. Existing show/related-entity writers have separate transactions: this is a policy fence, not an atomic replacement of the legacy persistence pipeline. Failed publication can leave accepted staging evidence for retry. Enforced review/rejection does not create or update public show, comedian or lineup records. Existing rejected show rows are preserved for the later inventory-cleanup workflow.

Off mode preserves legacy ingestion and does not access staging tables; pre-DDL source loading defaults missing policy fields to unreviewed/off. Shadow mode records decisions without filtering on the classification. If staging fails, shadow publication proceeds only when a new source-row fence proves the source is still enabled with the same revision and shadow mode. Source resolution or publication-lock failure withholds managed events; a stale generation also withholds publication. Failures always make reconciliation unsafe.

Covered boundaries are the normal BaseScraper/service result flow into ShowHandler, Ticketmaster national early chunk persistence, direct ShowHandler.insert_shows calls, and the public ShowHandler.update_show_lineups entry point. Screening runs before show identity reconciliation and before comedian/lineup persistence; internal screened helpers are used within the held fence to avoid screening twice. Scrape source identity and raw performer observations travel with events, including organizer/aggregate events routed to another venue. Managed source ambiguity is withheld. Unmanaged tour_dates deliveries and manual imports with neither source identity nor scraper attribution retain legacy off behavior. Raw SQL/operator writes remain outside the classifier boundary but are guarded independently by durable curation triggers. In-memory construction does not grant publication permission.

Stale-show cleanup and explicit provider cancellation messages are conservatively suppressed by the source/ownership guard for shadow/enforced sources, screened omissions, pending review, staging failures, unknown source ownership, source-target/organizer ambiguity, and venues with multiple configured sources. Any recorded publication ownership at a venue also disables stale-show cleanup and provider cancellations, including attempts by an off-mode sibling feed. A missing row in filtered output is never treated as cancellation. Existing inventory is retained for later reviewed cleanup.

Retention is indefinite until a separately reviewed retention policy is introduced. No automatic purge, backfill, public suppression, or production policy activation occurs in this migration. Payloads are normalized event evidence rather than full provider HTML, request headers or credentials. Model enrichment and operator review are follow-up workflows.

### SourceTarget
Non-venue scraper trigger identity for platform, national, or aggregate feeds that should not appear as physical clubs. Use this when a source exists only to drive discovery or scraping and cannot truthfully provide a venue address. `scraping_sources` rows belong to exactly one owner: either `clubId` for venue-scoped scraping or `sourceTargetId` for non-venue scraping. Shows discovered through a source target must still be attributed to real `Club` rows where venue data is available; production attribution remains on `ProductionCompany`.

### ClubAlias
Verified alternate venue names that resolve to one canonical Club before scraper discovery inserts a new club row. Aliases are global across ingestion sources and are scoped by normalized alias name, city, and state so the same venue nickname in a different market does not collide.

### ClubImageAsset
Published image assets for a club from the admin club-image pipeline. Rows preserve the source image URL, Bunny storage paths for original/icon/hero variants, image metadata, and whether the row is the active public asset. `Club.hasImage` remains the migration-era public compatibility flag; URL builders still use the legacy name-keyed Bunny paths for existing club images while publishes can retain versioned asset history.

### Comedian
Individual comedian. Has social media stats, popularity, alternate names (aliases), favorites, lineup appearances, and optional canonical YouTube channel id for WebSub live notifications. `youtubeAccount` is the user-facing handle/account value; `youtubeChannelId` stores the canonical channel id used in `https://www.youtube.com/feeds/videos.xml?channel_id=...` topics.

### ComedianImageAsset
Published image assets for a comedian from the official-site image pipeline. Rows preserve the source image URL, Bunny storage paths for original/avatar/hero variants, image metadata, and whether the row is the active public asset. `Comedian.hasImage` remains the migration-era public compatibility flag; URL builders prefer the active stable asset paths when present and fall back to the legacy name-based PNG path while older assets are still in use.

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
`visible` is the publication-suppression flag, independent of `isCancelled`, comedy eligibility, venue visibility and curation disposition. Public discovery, detail, ticket redirects, saved-show feeds and promotional queries require visible, non-cancelled shows; admin evidence remains accessible. Suppression retains the show and its saved-show, ticket, lineup, notification and audit references. Explicit curation restoration does not set visibility or clear other holds.

Occurrence curation retains source-owned event keys, provider IDs and confirmed cross-source publication mappings. Series curation requires a separate source-owned series identity with explicit membership. Titles never define a global show ban. See [show intake](CURATION-SHOW-INTAKE.md).

A comedy show at a club on a date. Has lineup items, tickets, and tags. `showType` is the normalized programming classifier used to derive ClubDiscoveryProfile rows; `unknown` means classification was attempted without enough evidence, while null means unclassified legacy or not-yet-processed data. `firstDiscoveredAt` is set by the database default when a scraper inserts a new show and is preserved on later upserts; historical rows may be null so notification candidate queries can exclude pre-existing backlog.

### DiscoveryRailCatalog
Stable registry of Discover rail keys and their rendering metadata. Each row identifies the rail's label and content kind, whether it requires an authenticated viewer, the platforms that can render it, and the catalog version that introduced the definition. Platform policies may reference only cataloged keys, and catalog rows cannot be deleted while policy entries still use them.

### DiscoveryRailPlatformPolicy
Versioned Discover configuration for exactly one of `web`, `ios`, or `android`. Each platform owns an independent policy version, catalog version, and cycle cadence in hours. `updatedByProfileId` attributes the latest admin write when available; deleting that profile nulls the reference without deleting configuration. Updates to a policy and its entries must be applied atomically and increment `policyVersion`.

### DiscoveryRailPolicyEntry
Placement and rotation settings for one catalog rail on one platform. The composite `(platform, railKey)` identity prevents duplicate configuration, and every rail must be cataloged and support its selected platform. `position` is zero-based, contiguous across slots, and cannot mix a fixed rail with a rotation pool or two different pools. `rotationPool` is null for fixed rails or names the pool used for cycling; all members of one pool share a position and every pool has at least one enabled member. Fixed rails require weight 1, rotation weights are constrained to 1–100, and enabled fixed rails have unique positions per platform. Deleting a platform policy cascades to its entries, while deleting a referenced catalog rail is restricted.

### Ticket
A ticket option for a show (price, purchase URL, type, sold-out flag).

### LineupItem
Join table linking a Comedian to a Show.

## User & Auth

### User
NextAuth user record (email, name, image).

### UserProfile
Extended user profile (role, zip code, notification preferences, favorite comedians).

### UserPushToken
Active and revoked APNs device tokens for authenticated native clients. Rows are scoped to both `User` and `UserProfile`, store the platform (`ios`), normalized device token, registration timestamps, and inactive/revoked state. `POST /api/v1/me/push-tokens` upserts the caller's current token; `DELETE /api/v1/me/push-tokens` marks only the caller-owned token inactive without exposing token data across users.

### YouTubeLiveNotification
Deduplication and history table for YouTube live push notifications. One row records that a specific user was notified about a specific comedian/video pair via a notification channel. Uniqueness on `(userId, comedianId, youtubeVideoId, notificationType)` prevents duplicate sends when YouTube WebSub posts multiple updates for the same live video. Rows store the canonical YouTube channel id, video id, video title, watch URL, notification type, and send timestamp; user and comedian deletes cascade to their notification history.

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

### SavedShow
The `saved_shows` table stores a binary saved/unsaved relationship between a UserProfile and one Show. The composite `(profileId, showId)` key allows only one save per profile and show, while `createdAt` records when the show was saved. A row remains after the show's date passes and is deleted only by an explicit unsave or by the cascading deletion of its profile or show. It does not represent reminders, intent status, purchases, attendance, or social activity.

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


### ComedyModelCache / ComedyModelAttempt / ComedyModelBudgetMutex
Durable model fallback cache entries are keyed by the caller's digest of event evidence, source policy, resolved identity/block state, classifier, model, prompt and schema versions. Callers validate cached responses again; only successfully validated provider results are completed. The cache is separate from immutable event eligibility decisions and does not itself authorize publication.

Each provider attempt reserves an integer USD-micro upper bound before network I/O. A singleton database row serializes short reservation transactions across hosts and worker loops. Reservations enforce the supplied UTC-day request and charge limits, active lease count, and same-key single-flight. Every retry creates and charges another attempt. Completed calls charge actual cost; failure or expired ownership retains the conservative reservation. If reported actual cost exceeds its reservation, the excess is charged and the result is not cached. A hard spending bound therefore requires the caller to reserve a true maximum provider cost; unexpected provider overages are observable but cannot be undone after billing. All callers must use the same configured daily limits.

Owner tokens and lease deadlines prevent a late worker from populating the cache after losing ownership. Expired attempts remain in the spend ledger, but a new owner can reserve the key. Provider transport deadlines must be shorter than leases; lease expiry cannot cancel a still-running external request. No provider call occurs inside a database transaction. The cache and attempt ledger have no automatic purge in this task; manual retention must preserve current budget accounting. The additive migration activates no source policy or provider traffic.


### ComedyEventObservation / ComedyEventReview / ComedyReviewPreview / ComedyReviewOperation
An immutable observation maps every newly staged candidate generation to its exact reused or new decision. Queue reads join this mapping, never the largest decision ID: an A→B→A payload reversion can legitimately return an older decision. Legacy candidates have no guessed observation backfill and display awaiting_observation until their next scrape. The observation stores deterministic baseline identity evidence independently of model/human decision suffixes.

The review queue uses candidate-ID keyset pagination with a first-page ceiling, SQL filtering and a bounded page size. Filters cover source, venue, current observed decision/review state, lineup coverage and reasons. Concurrent changes may change filter membership; the ceiling prevents newly created candidates entering the same traversal. Queue identity evidence is observed, not a fresh per-row identity audit. Detail refreshes identity when a validator is supplied and labels stale_identity; preview and apply require live identity validation. Detail returns up to 100 review actions, observations and publication links with explicit truncation flags.

A preview records 1–100 explicitly selected candidate snapshots, actor, action, reason, confirmation digest and a 15-minute expiry. Its display shows event payload/evidence and state; the confirmation digest binds selection rather than a filter query. Applying checks actor and digest, source mode/revision, generation, decision, review version and current identity evidence under ordered source/candidate locks. Every selected action succeeds together or the transaction rolls back. Off or disabled sources cannot receive new review actions. Replaying the same idempotency key and preview returns the recorded result; conflicting reuse is refused.

Human approve/reject/defer actions append immutable history and increment the candidate review version, invalidating previously prepared publication tokens. Database triggers prohibit updates/deletes of observations, reviews, previews and operations. The latest action matches only its exact payload, policy revision and deterministic identity snapshot. Unchanged later scrapes retain it; changed evidence makes it stale and requires renewed review. No earlier matching action is resurrected after a later decision.

Approval is consumed on a subsequent normal scrape and publishes through existing validation and eligibility fences; the review operation never reconstructs public entities from stored payloads. Explicit rejection/defer withholds the selected event in both shadow and enforcement modes. Off mode retains legacy behavior. Neither rejection nor deferral deletes already published rows, blocks a venue, or changes source trust. Retention remains indefinite pending a separately reviewed retention policy; no production source activation or live DDL is part of isolated verification.


### ComedySourceSample / ComedySourceReport / ComedySourceTransition
Source quality monitoring keeps one latest baseline sample per source/event key. Repeated scrapes update freshness and evidence, not sample count. Baselines deliberately classify under unreviewed trust, before model or human overrides, so a comedy_only source cannot validate itself merely through its trust label. This ledger is separate from publication eligibility staging and can observe broadly ingested trusted off-mode feeds without changing their publication behavior. Source shared locks precede sample writes; monitor transitions acquire the source update lock first.

Immutable reports retain explicit denominator metrics, configuration, source policy snapshot, exact UTC window bounds, up to five negative example event keys/fingerprints/reasons, and the substantive full-evidence digest. Samples are reloaded under the source lock and metrics/recommendations recomputed before recording or applying; stale collected evidence is refused. Report identity excludes scrape generations and freshness timestamps. Repeated unchanged evidence/configuration reuses the report; no repeated operational alert or policy toggle is necessary. Enabled zero-sample sources remain visible as insufficient evidence. History endpoints return at most 100 reports and transitions with truncation flags.

Automatic action is disabled by default. Explicitly enabling monitor action authorizes only comedy_only → mixed/enforce, including enforcement activation if the trusted source was off/shadow; it never automatically upgrades source trust. The policy revision is checked under lock and the existing policy helper records monitor attribution/evidence while the policy trigger increments the revision. Transition history retains before/after policy state and the report that justified it. No source ownership, enabled flag, venue visibility or public inventory rows are modified.

Rollback is an explicit operator action requiring actor, reason, and the exact revision produced by the downgrade. A later policy edit blocks rollback. Rollback restores prior trust/mode with a fresh revision and records its link to the original downgrade. Its bad-content evidence digest remains suppressed independently of policy version or configuration changes, preventing immediate re-downgrade on identical evidence. Fresh substantive event evidence may trigger a new evaluation. Database triggers enforce append-only reports and transition history; no retention purge is introduced.

## Intake curation

See [CURATION.md](CURATION.md) for durable entity/relationship identities, decisions, and compatibility boundaries.
