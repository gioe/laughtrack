# TASK-4134 — Heavy Hitters Tour identity review

On October 8, 2026 UTC, comedian **1936878**, UUID
`aa1d65a5844b25bda5016b1c8868c08b`, remained visible and canonical under
**Heavy Hitters Tour**. A complete query of its lineup associations returned
exactly four shows, all at Greenville Comedy Zone (club 73). Each listed only
this tour label as a performer.

The native scraper HTTP stack returned HTTP 200 for all four official pages.
Each describes a multi-comic tour featuring **Darren Brand, Marvin Hunter,
Burpie, and GiGi LeFlair**, rather than a person named Heavy Hitters Tour.
[association-review.json](association-review.json) records timestamps, source
URLs, response hashes, bounded excerpts, and every association decision.

| Show | Official page | Stored UTC start | Decision |
| --- | --- | --- | --- |
| 5775541 | [384861](https://greenvillecomedyzone.com/shows/384861) | 2027-04-09 23:00 | Detach tour-label association; retain show and tickets |
| 5775542 | [384862](https://greenvillecomedyzone.com/shows/384862) | 2027-04-10 01:00 | Detach tour-label association; retain show and tickets |
| 5775543 | [384863](https://greenvillecomedyzone.com/shows/384863) | 2027-04-10 22:00 | Detach tour-label association; retain show and tickets |
| 5775544 | [384864](https://greenvillecomedyzone.com/shows/384864) | 2027-04-11 01:00 | Detach tour-label association; retain show and tickets |

The source requests used the stored HTTP URLs; links above use HTTPS. The
current SeatEngine source is 32, venue 464. A separate Ticketmaster source
6262 also belongs to the club and must remain unchanged.

## Approved disposition

Hide the exact reviewed canonical identity using block reason
`task_4134_tour_label` and detach its four reviewed lineup rows. Preserve the
comedian row, all historical references, complete shows, tickets, sources,
clubs, and any unrelated performers. Do not manufacture aliases or add
performers by guessing their database identities from the billing.

The existing persistence filter excludes exact normalized names belonging to
hidden comedian rows before lineup updates. It supplies repeat-ingestion
protection without a broad Heavy Hitters substring exclusion or a new global
deny-list entry. Regression coverage must exercise this filter through lineup
persistence, including legitimate performers and similarly named controls.

The production operation must guard complete before-images and the exact
association cohort, save private recovery artifacts before writes, compare all
protected rows after writes, and refuse rollback if the affected after-state
has drifted. Execution and verification are recorded separately after apply.
