# Independent podcast discovery

Web, iOS and Android render a public five-episode “Hear a new comedian” rail after
the first three Discover sections (or earlier when fewer sections exist). The
web client starts its request when the section approaches the viewport; native
clients start independently after the main feed is available. Artwork loads with
the cards and audio starts only when the user presses Play.

`GET /api/v1/home/podcast-discovery` reads one durable snapshot row. Missing,
invalidated, and older-than-24-hour snapshots return an empty selection. It never
invokes the recommendation generator. HTTP caches must revalidate; matching
ETags return 304. Errors are not cacheable. Clients omit unavailable selections.
The snapshot contains no account identifiers or personalized favorite flags.

`GET` or `POST /api/cron/podcast-discovery`, authenticated with `CRON_SECRET`,
refreshes the snapshot using the existing public episode ranking and diversity
rules. Vercel schedules this at minute 15 every hour. A failed generation leaves
the previous snapshot intact. An empty successful generation publishes empty.
A revision comparison prevents an overlapping job or moderation race from
republishing an obsolete selection.

Database triggers invalidate changes to visibility, canonical comedian identity,
deny lists, reviewed appearances, podcast feed identity and episode deletion,
including writes made by the scraper. No-op identity/review writes do not evict.
Invalidation is intentionally fail-closed until the next successful scheduled
refresh; it does not start a new query on a visitor's request. Already mounted
cards are replaced on the client's next refresh, not by live push.

Updated native clients pass `deferPodcasts=true` on the main feed, which skips
both podcast providers entirely. Older clients retain the existing response
behavior. iOS legacy category screens retain their existing feed path. Public
snapshot state is separate from personalized/persisted main-feed caches.

## Rollout

Deploy the Prisma migration and web/API changes before releasing native clients.
The configured Vercel plan must support hourly cron invocations. Use the existing
secret configuration; no new credentials or storage service are required.
After deployment, invoke the authenticated refresh endpoint once to seed the
snapshot, then verify `published: true`, a nonempty public response (where eligible
episodes exist), and the hourly job. Do not apply unrelated pending migrations
just to seed this feature. Before seeding, clients safely omit the empty rail.

For rollback, remove the rail mounts and restore native feed requests without
`deferPodcasts`; the new API and table can remain while released clients use them.

## Verification

Focused tests cover snapshot misses, failed generation, revision races,
moderation triggers on real PostgreSQL semantics (PGlite), conditional caching,
cron auth, client cancellation and separate detail/profile/play actions. A feed
test installs permanently pending podcast providers and proves a deferred feed
completes without invoking either. Native tests cover independent state and
superseded/empty/failed responses. Browser fixtures stall the podcast response
while asserting primary content remains available, and verify no audio request
occurs until Play at 390px and 1440px.

These establish dependency isolation, not a measured production latency claim.
After rollout compare the existing `feed_total` and native first-content metrics
against the previous release, and verify podcast providers report `skipped` for
deferred requests. Measure the separate snapshot endpoint and cron success rate
independently. No production latency percentile has been measured locally.
