# Production verification

The guarded dry run produced four target lineup rows before and zero after,
passed preservation assertions, and rolled back. Apply committed that same
change on October 8, 2026 UTC. A subsequent dry run returned
`already_applied: true`, with zero target rows before and after.

Only `visible`, `block_reason`, and `block_added_at` changed on comedian
1936878. The identity remains in the database, hidden with reason
`task_4134_tour_label`; its four exact reviewed lineup associations were removed.

Complete transactional before/after comparisons preserved four shows, eight
tickets, five tagged-show rows, 67 ticket-click rows, one club, and two scraping
sources. Fourteen other comedian-reference relationships were inspected; the
one existing podcast discovery-attempt record remains unchanged. The four
reviewed lineups contained no other performers. No aliases, replacement
performers, or global deny-list entries were created.

## Recovery

The executed script is archived at
`scripts/archive/disposition_heavy_hitters_tour_2026_10_08.py`.
Private files contain complete database rows and remain outside Git, mode 0600:

- `/private/tmp/task4134-identities.json` and
  `/private/tmp/task4134-associations.json`: reviewed inputs.
- `/private/tmp/task4134-disposition-backup.json`: original state;
  SHA-256 `cd963676facadd427e0c8619bb8e8f1af04f179649f6eef0eafda165d3ac50e9`.
- `/private/tmp/task4134-disposition-backup.json.after.json`: recovery inputs
  and exact before/after states;
  SHA-256 `403f70184ed8172147380a287d587a140190da097ab6b02c10b59cbdc549cb93`.

From `apps/scraper`, guarded rollback is:

```sh
.venv/bin/python3 scripts/archive/disposition_heavy_hitters_tour_2026_10_08.py \
  --rollback /private/tmp/task4134-disposition-backup.json.after.json
```

Rollback refuses changed after-state. It restores original identity metadata
and exact lineup rows; it was tested in temporary PostgreSQL tables, not run
against production after apply.

## Public behavior and regression coverage

Read-only production API verification confirmed performer detail returns 404,
search for Heavy Hitters Tour with `includeEmpty=true` returns zero results,
and all four show endpoints return 200 with the false performer absent.
Every other field of each show response, including both tickets, matches its
saved pre-cleanup response exactly. Initial repeated GETs returned the old
responses; fresh query variants verified current behavior. Private public API
responses are in `/private/tmp/task4134-public-before.json` and
`/private/tmp/task4134-public-fresh.json`; [verification.json](verification.json)
contains sanitized counts and timestamps.

All 12 focused tests passed with no skips against a local PostgreSQL test
database, using temporary tables and rollback. Coverage includes complete
preservation, repeat apply, serialized recovery rollback, private backup modes,
backup failure before writes, identity/canonical/role/cohort/source/show drift,
changed historical references, and unexpected incoming lineup foreign keys.
Repeated ingestion exercises the real hidden-name filter and lineup update
path for label-only and mixed lineups, preserving named performers, the close
name Heavy Hitters Tour Jr, and show/ticket fields.

No runtime filter change is required: the production hidden identity activates
the existing exact-name ingestion suppression immediately.
