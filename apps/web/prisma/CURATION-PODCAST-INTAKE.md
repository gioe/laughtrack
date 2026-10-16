# Podcast intake curation

Podcast rows can hold pending review metadata. They are not trusted publication:
`curation_podcast_allowed(id)` requires exactly one approved identity bound to
that row. Episodes cannot be inserted or refreshed without that approval.
Public podcast lists, details, artwork, favorites, home rails and comedian
appearances require approval as well as their existing eligibility checks.

Identity uses podcast ID, provider-scoped ID and normalized feed URL. Known
`itunes_collection_id` and `podcast_index_feed_id` external IDs are retained.
URL normalization lowercases scheme/host, removes the default port and fragment,
and represents an empty path as `/`. It preserves path case, query strings,
trailing slashes and HTTP versus HTTPS. Titles and host names never prove identity.
Conflicting keys hold writes; provider IDs are not reassigned to a different identity.

Old feed keys survive feed edits and deletion. Operators can attach a verified
redirect or alias with `curation_verify_podcast_feed(entity_id, url, actor, reason)`.
This requires an explicit verification reason and refuses another identity's feed.
An HTTP redirect alone is not proof; automated fetchers do not adopt landing pages
or arbitrary redirect targets as aliases. Review the feed ownership/content first.

The shared curation service supports approve, block and restore for podcasts.
Block suppresses existing public records and future episode writes while retaining
history and relationships. Restore returns to pending, never directly to approved.
It marks matching compatibility denials restored without deleting their history.
Deleting an active legacy denial does not clear the durable block. A host rejection
is independent; host approval never restores or approves a podcast. Legacy admin
clients must explicitly send `denyListed: true` to block or `false` to restore.
Manual RSS imports return `episodeIntakeHeld: true` until the podcast is approved.
The database still rechecks policy if a block races an episode refresh.

All writers use the shared intake lock before row locks. SQL triggers are the final
boundary for Python, Prisma, retries and maintenance imports. Lookup errors fail
closed. Cache versions use the existing `show_publication_revision` shared by
public entity pages; podcast decisions, compatibility blocks and verified aliases
increment it, so workers do not need an HTTP cache-invalidation callback.

## Rollout

Do not treat existing accepted host links as podcast approval. Reconcile explicit
podcast approvals before enabling this boundary; legacy records without evidence
remain pending. Existing duplicate feed rows require identity reconciliation and
are not silently merged. New metadata can be reviewed through the shared curation
API; the expanded inbox interface is tracked in TASK-4185.

Production currently has the earlier failed `20261015120000_club_curation_intake`
migration. Follow CURATION-SHOW-INTAKE.md recovery and legacy reconciliation before
`prisma migrate deploy`. This task does not resolve that failure or deploy schemas.

The migration contract can be run against a read-only production identity snapshot:
`CURATION_PODCAST_SNAPSHOT=/private/tmp/snapshot.json npm test -- lib/admin/curation/podcastIntake.test.ts`.
The snapshot format is `[{"snapshot":{"podcasts":[...],"denials":[...]}}]`;
no production data is committed. Ordinary CI uses synthetic boundary cases.
