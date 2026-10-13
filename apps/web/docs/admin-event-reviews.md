# Event eligibility in Review inbox

Open **Admin → Review inbox** and choose **Event eligibility**. Event screening uses the same queue, evidence, decision controls, and history as comedian identity and podcast relationship reviews. `/admin/event-reviews` redirects here and preserves its filters and selected occurrence.

Each occurrence is reviewed individually. Source ID, screening mode, status, and text filters narrow the queue. Cursor pagination keeps a stable upper boundary while browsing. A reason and confirmation are required for Approve event, Reject, or Defer. Submitted requests remain distinct from applied decisions; pending requests refresh automatically.

## Applying a review

The web app writes an attributed pending request to `comedy_admin_review_requests`. An independent `Apply admin event reviews` workflow runs at minutes 7, 22, 37 and 52, or via manual dispatch. GitHub scheduling can be delayed. Each run processes at most 100 requests. This worker is separate from scraping and makes no model calls.

The worker uses the existing Python `ReviewStore` to validate live comedian/deny-list evidence and source policy, prepare a preview, and atomically apply it. The operator's exact observation generation, decision, identity fingerprint, policy version, gate mode and review version must still match. Changing evidence, source settings, another review, or a revoked admin role makes the request stale and visible in the page. Inspect refreshed evidence and submit a new decision. Network retries retain the same request ID and are idempotent. Transient worker/DB errors roll back the entire operation, leaving the request pending for retry. The request row is locked with SKIP LOCKED for concurrent workers.

Applied reviews appear in the existing append-only review history. They do not publish or remove public shows immediately, change source trust, enable enforcement, or unblock performers. The ingestion gate consumes the scoped decision on the next scrape. Human reject/defer and stale-review holds also affect shadow ingestion; automated shadow flags alone do not withhold. Off-mode observations and disabled sources are read-only in this UI. Historical publication links are not a claim that the event is currently public or withheld. Stored-inventory cleanup remains TASK-4159 and enforcement qualification remains TASK-4160.

## Deployment and operations

Deploy the Prisma migration `20261012000000_add_comedy_admin_reviews` before using the page/worker, with the project's pinned Prisma migrate deploy command and normal Neon configuration. The independent workflow uses the existing scraper DB secrets and shared Python setup action. No new service or OpenAI credentials are needed. Do not switch sources into enforcement merely to populate the page.

Run the worker manually from `apps/scraper` with `python -m scripts.core.process_comedy_admin_reviews --limit 100`. This applies pending decisions; it is not a dry run. To pause processing, disable the independent GitHub workflow. Pending requests remain visible and can be processed later; existing applied review history remains authoritative until invalidated. A classifier/identity interpretation change may stale old observations until a fresh source observation is collected.

Local verification uses PGlite (real migrations and admin SQL), mocked route auth boundaries, React interaction tests, and worker transaction tests plus the existing review/gate regression suite. Do not validate by approving real production events as test data.
