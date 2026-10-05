# TASK-4105: iO Theater bounded stale-performance cleanup

Fresh inspection on October 5, 2026 revalidated all 42 IDs from TASK-4063.
The native scraper HTTP stack returned 80 Crowdwork listings; its Playwright
browser retrieved all 13 affected event pages. The complete sanitized feed,
page dates and descriptions, database identities, and per-ID decisions are
hash-locked by manifest.json. Raw HTML and credentials are not committed.

29 future performances remain absent from both the complete feed and their
public pages: 18 Orbit occurrences, 10 individual omitted dates, and the old
This Year in Music date. This establishes delisting/schedule changes, not an
assertion that the venue explicitly canceled them. The This Year in Music
replacement, row 1044696 on December 11, remains present in source and storage.

13 IDs are held:

- 1863553, 480646 and 3736581 are now past. Retain historical rows; 3736581
  also remains the explicit missing People Being Funny replacement hold.
- 480692, Flex Improv: the description still lists 11/05 at 7:30pm even though
  the feed and date selector omit it. The conflict is unresolved.
- 3736583–3736585, 3767701 and 4880163: five more People Being Funny source-listed
  earlier-time replacements are now missing from storage. Retain these rows
  under the same replacement-preservation rule and TASK-4106 identity work.
- 2084643, 3013099, 4282370 and 5600935: the original Mystery Movie Club IDs now
  contain Battleprov. Their URL/title/freshness changed; never delete by ID alone.

The runtime reconciliation cap remains 10. No scraper runtime logic or source
configuration changes are part of this task. TASK-4106 owns simultaneous-event
identity repair. All 13 held IDs have explicit reasons in decisions.json.

Offline evidence verification (from apps/scraper):

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-io-stale-cleanup/replay.py
```

## Transaction and recovery

`cleanup.py` is a one-shot audited repair, not an automatic migration. Its default
mode rolls the transaction back. It refuses expired evidence (24 hours), missing
or changed IDs, refreshed rows, newly past performances, changed ticket/tag rows,
a missing/moved replacement, or saved/notification/discovery references. It locks
venue rows and their dependents before exporting and deleting. A second application
refuses because the exact 29-row cohort no longer exists.

The rollback validation removed exactly 29 rows inside the transaction, then
rolled back. It checked all retained show and dependent rows byte-for-value,
including the held IDs and replacement 1044696. The 29 tickets, 136 lineup links,
and 71 tags belong only to the stale cohort and cascade with it. All 143 click
records survive with attribution unchanged except their nullable show_id link.
The club count is refreshed in the same transaction. Runtime cap remains 10.

From apps/scraper (use a new absolute export filename for each invocation):

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-io-stale-cleanup/cleanup.py \
  --export /private/tmp/task4105-rollback-dry.json
# Add --apply only for the reviewed cohort, while the source evidence is fresh.
```

Recovery exports are created exclusively with mode 0600, flushed to disk before
DELETE, and never committed: they include complete show, ticket, lineup and tag
rows plus original click linkage, which can contain user identifiers. The apply
export is `/private/tmp/task4105-rollback-applied.json`. Retain it for recovery.
To restore, first inspect current IDs/venue-date-room collisions, then within one
transaction insert exported shows, tickets, lineup_items and tagged_shows in that
order using their original IDs; restore exported clicks' show_id only where it
is still NULL and the remaining attribution fields match the export. Never
upsert over newly created or changed rows. Refresh club 182 total_shows and
verify every restored/dependent ID before committing. Abort on any collision
and reconcile it explicitly. Rollback-only exports need no restoration.

Validation: the evidence replay and all 22 focused reconciliation/Crowdwork tests
pass. The full suite cannot collect because tzdata is missing in the shared
virtualenv; three unchanged-baseline prechecks reproduced it with no divergence.

## Applied result

Applied October 5 at 18:55 UTC. `result.json` records the exact 29 deleted IDs,
13 held IDs, dependency counts and preservation assertions. Club inventory
changed from 1,863 to 1,834 shows. All retained shows and their dependent rows
were unchanged within the transaction, including replacement 1044696. All 143
clicks survived with original attribution and NULL show_id. A separate read-only
post-commit connection confirmed the deleted IDs are absent, all 13 holds remain,
the club count matches, and the exported click attribution still matches.
