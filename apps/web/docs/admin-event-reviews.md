# Admin event review

Open `/admin/event-reviews` from **Event Review** in the admin navigation. Only authenticated administrators can read the queue or submit decisions; the server derives the reviewer from the current database profile.

The queue contains staged source-owned candidates, not the offline shows-search audit corpus. Search by event or venue, filter by source, mode or review state, and select one occurrence. Identical venue/source/title entries are grouped within each 50-occurrence page for navigation only. Reviewing one never grants authority to other occurrences or to an entire venue.

Read the description, collected evidence, rule reasons and observed lineage before choosing **Approve as comedy**, **Reject from ingestion**, or **Defer — keep on hold**. A parent identity is not standalone proof of comedy. Enter a reason, preview the exact occurrence, and confirm. Source content is rendered as text; links allow only HTTP(S).

## Applying a review

The web app writes an attributed pending request to `comedy_admin_review_requests`. An independent `Apply admin event reviews` workflow runs at minutes 7, 22, 37 and 52, or via manual dispatch. GitHub scheduling can be delayed. Each run processes at most 100 requests. This worker is separate from scraping and makes no model calls.

The worker uses the existing Python `ReviewStore` to validate live comedian/deny-list evidence and source policy, prepare a preview, and atomically apply it. The operator's exact observation generation, decision, identity fingerprint, policy version, gate mode and review version must still match. Changing evidence, source settings, another review, or a revoked admin role makes the request stale and visible in the page. Inspect refreshed evidence and submit a new decision. Network retries retain the same request ID and are idempotent. Transient worker/DB errors roll back the entire operation, leaving the request pending for retry. The request row is locked with SKIP LOCKED for concurrent workers.

Applied reviews appear in the existing append-only review history. They do not publish or remove public shows immediately, change source trust, enable enforcement, or unblock performers. The ingestion gate consumes the scoped decision on the next scrape. Human reject/defer and stale-review holds also affect shadow ingestion; automated shadow flags alone do not withhold. Off-mode observations and disabled sources are read-only in this UI. Historical publication links are not a claim that the event is currently public or withheld. Stored-inventory cleanup remains TASK-4159 and enforcement qualification remains TASK-4160.

## Deployment and operations

Deploy the Prisma migration `20261012000000_add_comedy_admin_reviews` before using the page/worker, with the project's pinned Prisma migrate deploy command and normal Neon configuration. The independent workflow uses the existing scraper DB secrets and shared Python setup action. No new service or OpenAI credentials are needed. Do not switch sources into enforcement merely to populate the page.

Run the worker manually from `apps/scraper` with `python -m scripts.core.process_comedy_admin_reviews --limit 100`. This applies pending decisions; it is not a dry run. To pause processing, disable the independent GitHub workflow. Pending requests remain visible and can be processed later; existing applied review history remains authoritative until invalidated. A classifier/identity interpretation change may stale old observations until a fresh source observation is collected.

Local verification uses PGlite (real migrations and admin SQL), mocked route auth boundaries, React interaction tests, and worker transaction tests plus the existing review/gate regression suite. Do not validate by approving real production events as test data.
