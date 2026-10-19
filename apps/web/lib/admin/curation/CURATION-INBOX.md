# Unified Review Inbox

`/admin/reviews` is the admin entry point for intake, relationships, performer
validation, event eligibility and public visibility. Intake decisions are keyed by
curation identity and explicit entity/name/series scope. Parent and host pairs use
the same queue, evidence, reason, preview, action and attributed-history panel.

- Intake filters cover comedians, clubs, shows and podcasts, including searchable
  blocked history. Identifiers show exactly which identity or source-owned series
  is being reviewed. Existing name matches are comparison evidence, not implicit links.
- Performer approval still requires the existing evidence/name/match/appearance
  workflow. Its decisions now require a reason and confirmation. Blocking and
  restoration use the shared durable ledger.
- Parent proposals require same-performer evidence. Parent previews can explicitly
  replace an existing parent and explain host reconciliation holds. Host/cohost
  proposals retain multiple hosts; they never implicitly reject other candidates.
- Public hide/show is labeled separately. Restore returns an identity or pair to
  review; it never approves, publishes or restores other relationships.
- Every new decision is previewed. A sent request is saved in session storage with
  its exact body and request ID. Interrupted requests can be checked or retried;
  conflict recovery requires fresh state and a fresh preview. Pending work is
  labeled submitted, not applied. Reconciliation retries retain their original token.
- Mobile filters and queue collapse independently; previews receive focus and
  scroll into view. J skips outside editable/interactive controls without deciding.

Entity tabs link using `view`, `kind`, `recordId` and `endpointKind`. Direct ledger
links use `view` and `id`. Podcast host review and the old deny-list page redirect
into the Inbox; comedian parent/host controls no longer mutate from the entity tab.
Metadata and manual RSS entry remain in the entity editor.

## Verification and rollout

Run `npm test -- ui/pages/admin/reviews/CurationWorkspace.test.tsx` and
`npm run type-check`. The real SQL query contract is in
`lib/admin/curation/hostRelationships.test.ts`; API tests exercise admin guards.

Run `node bin/verify-curation-inbox.mjs` from `apps/web` for repeatable 1440px and
390px browser checks. It mounts the real components with a stateful isolated test
API and tests reject/rediscover/restore, establish/sever, keyboard skipping and
horizontal overflow. Screenshots are written to `/tmp/curation-inbox-*.png`.
This browser harness does not prove production migration readiness; database
policy contracts run separately against PGlite with the real migrations.

No schema or production data changes are part of TASK-4185. Production must first
complete the earlier curation migrations and explicit legacy reconciliation,
including the host preflight documented in `prisma/CURATION-HOST-RELATIONSHIPS.md`.
If that schema is unavailable, the Inbox read API returns a clear 503; it does not
fall back to unsafe per-source decision writes.
