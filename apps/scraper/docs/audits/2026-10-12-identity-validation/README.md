# Comedian identity validation and shared review inbox

The admin inbox at `/admin/reviews` supports two independent review workflows:
comedian identity and existing podcast relationships. The shared queue, evidence
panel, navigation, history, conflict handling and undo are reusable. Show eligibility
and club management remain linked to their existing screens; they are not silently
assigned a universal approval state.

Ingestion stores uncertain identities and source context in candidate/evidence tables.
An extraction, a legacy canonical row or a title match does not validate an identity.
Only explicit administrator approval sets `identity_validated_at`. No existing profiles
are grandfathered. Existing historical lineup rows are preserved; new links and title
inference require a visible validated canonical identity. Identity review independently
lets the administrator select which observed appearances to add immediately.
Rejected candidates survive repeated ingestion. Existing hidden/denied names do not
create new queue entries. A rejected candidate does not hide a separately existing
profile; profile suppression remains an explicit management operation.

The PostgreSQL and browser checks cover pending/rejected/accepted transitions,
idempotent evidence, canonical linking, selected appearances, optimistic conflicts,
audit history, and guarded undo. Undo never removes pre-existing lineup links and
refuses conflicting later identity changes. Undoing a newly created identity hides
its profile and retains its history; the same reviewer can approve it again.

## Deployment order

1. Apply the additive Prisma migration `20261012210000_comedian_identity_review`.
2. Deploy the web inbox before updating the scraper worker to the new gate.
3. Apply the reviewed suppression migration. It affects only the five exact ID/UUID/name
   tuples in `before.json`, preserving six lineup links and their six shows.
4. Review staged candidates in the inbox. Periodic podcast discovery picks up newly
   approved profiles; approval itself does not make external discovery requests.

`rollback.sql` restores only still-untouched TASK-4173 suppressions. The original
profile flags are recorded in `before.json`. The data migration was tested forward,
replayed, rolled back and replayed inside a transaction; full show and lineup rows
were compared before and after.
