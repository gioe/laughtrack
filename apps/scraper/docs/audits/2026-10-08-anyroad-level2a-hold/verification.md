# Continued-hold verification

The task performed no production mutations. Fresh read-only, repeatable-read
snapshots around a non-persisted native scraper replay were exactly equal across
both venue cohorts: 141 shows, 141 tickets, 244 tags and 2,005 click events, plus
club, producer, mapping and source rows. Both held Level 2A rows and historical
Level 1B 3179544 also match the initial source-review snapshot exactly.

The three protected shows retain 3 tickets, 11 tags and 46 click events. No private
user rows are committed: the audit contains public show fields and aggregate
relationship counts/hash evidence only. Both Level 2A public detail endpoints and
historical Level 1B returned HTTP200 at their existing IDs and stored dates.

The full read-only native replay returned136 shows with no error and no Level2A
showcase candidate. This does not prove cancellation and did not persist results
or trigger cleanup. Continued hold here means no manual repair; it does not add a
new database flag or claim a new runtime retention mechanism.

66 existing focused tests passed, including real PostgreSQL checks preserving
3789176,3179550 and3179544 and the empty-authoritative-calendar test that refuses
to resurrect placeholder slots. No production code or tests required changes.
The full scraper gate failed collecting the pre-existing missing tzdata import;
all three clean-HEAD prechecks reproduced it without flakiness or divergence.

See [verification.json](verification.json) for snapshots, public responses,
counts, replay and test evidence, and [README.md](README.md) for the exact evidence
needed before revisiting the hold. No rollback is needed because no rows changed.
