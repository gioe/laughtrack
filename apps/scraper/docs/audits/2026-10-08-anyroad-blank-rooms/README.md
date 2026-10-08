# TASK-4135 — Rozzie legacy blank-room occurrences

Reviewed October 8, 2026 UTC using the production rows, native AnyRoad list API,
and booking-page identity, location, timezone and availability data. The scraper's
own HTTP stack fetched 44 experiences and validated all 44 calendars without
routing errors. A separate full, read-only scraper replay produced 137 shows with
no error. No scrape results were persisted during source review.

## Per-row disposition

All local times below use America/New_York. Native booking URLs, IDs, precise
timestamps, page hashes and date slots are recorded in
[source-review.json](source-review.json).

| Legacy show | Native experience | Decision | Retained show / verified occurrence |
| --- | --- | --- | --- |
| 3789152 | 88719 | Merge 09:00 placeholder; correct retained time | 3179527 — Oct 17, 20:30, Corinth Street |
| 3789159 | 133266 | Merge 09:00 placeholder | 3179503 — Oct 24, 20:30, Corinth Street |
| 3789169 | 102243 | Merge 09:00 placeholder; correct physical venue | 3179545 — Nov 5, 20:00, The Substation |
| 3789163 | 141813 | Merge 09:00 placeholder | 3179540 — Nov 7, 20:30, Corinth Street |
| 3789176 | 127816 | Hold; insufficient occurrence evidence | Preserve this row and 3179550 |
| 3789171 | 137902 | Merge 09:00 placeholder; correct physical venue | 3179547 — Nov 23, 20:00, The Substation |
| 3558371 | 79259 | Fill verified room; retain date and ID | June 26, 2027, 18:00, Corinth Street |
| 3789139 | 79259 | Fill verified room; retain date and ID | July 3, 2027, 18:00, Corinth Street |

The two 2027 ComedySportz rows are real native calendar occurrences with correct
times. They do not share the 09:00 defect. Level 2A is absent from the current
list; its direct booking page still identifies experience 127816 but returns an
empty availability map. Its current Substation location alone cannot prove the
stored November 15 occurrence, so neither existing Level 2A row is changed.

Fresh evidence supersedes the October 6 location/time observations for the
specific upcoming occurrences above: list and detail now agree that Level 1B
and Level 3B are at The Substation, and Mainstage now starts at 20:30. Historical
Level 1B show 3179544 and every other unreviewed row remain untouched.

## Repair boundaries

Retain the existing canonical show IDs; preserve distinct ticket offers and all
user-linked relationships. Coalesce an overlapping child row only if all business
fields are identical; otherwise refuse the operation for review. Correct producer
ownership to existing producer 50 on the seven retained shows. Preserve source
6820, plugin metadata, source 12257, both physical club identities and routing.

Execution requires an exact reviewed before-image, collision checks across both
physical venues, private recovery snapshots, post-write preservation assertions,
and rollback that refuses changed after-state. The current routed scraper already
holds unavailable detail calendars instead of importing placeholder list times;
no broader fallback or runtime filter change is proposed.
