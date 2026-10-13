# Shared Review inbox

Reviewable work uses `/admin/reviews`: a filterable queue, an evidence/detail panel, explicit decision controls, and attributed history. Comedian identities, podcast relationships, and event eligibility all use this screen and `/api/admin/reviews`. Event Review's old URL redirects with filters intact.

Register workflow capabilities in `lib/admin/reviewTypes.ts`: available states, default state, action labels, required reasons, identity fields, source filters, and whether decisions are queued. Map domain data into `ReviewItem` (evidence, matches, history, allowed actions, processing state, and explanatory notice). Keep domain validation and transitions in the service adapter; the UI never decides what a stored status means for publication.

Route list/detail/decision dispatch through `lib/admin/reviews.ts`. Preserve the domain's concurrency token and pagination semantics. Queued decisions use a stable request ID across retries and return a submitted notice; only reversible synchronous decisions return an undo ID. Include authenticated route tests, service state/conflict tests, and shared-screen interaction tests. New reviewable entities should extend this contract instead of creating a separate review page.

A reviewed entity and a particular review workflow are distinct: approving an identity does not approve its appearances, and submitting an event decision does not immediately publish a show. Club management remains a management screen until a concrete club review workflow is defined.
