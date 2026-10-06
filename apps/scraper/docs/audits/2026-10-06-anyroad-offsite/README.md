# TASK-4116: AnyRoad physical venue review

Reviewed 2026-10-06. Organizer club 10970, The Rozzie Square Theater, owns
AnyRoad source 6820 and plugin `rozziesquaretheater`. The source can advertise
performances at another physical venue without changing that ownership.

## Fresh authoritative evidence

The scraper's own HTTP stack successfully fetched all five API pages: 10, 10,
10, 7, then zero experiences. All 37 current experiences name either 18 or 18b
Corinth Street. This supersedes the September audit's upstream-fetch limitation;
it does not retroactively determine every historical performance location.

Three official booking pages were fetched independently and their native About
properties inspected:

| Experience | ID | Current advertised place | Current availability |
| --- | ---: | --- | --- |
| [Level 1A](https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/level-1-improv-showcase?lang=en-US) | 83409 | The Substation, Washington Street, Roslindale, MA | Empty; no future occurrence inferred |
| [Level 1B](https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/level-1b-showcase?lang=en-US) | 102243 | 18b Corinth Street, Boston, MA | November 5, 2026, 8pm America/New_York |
| [Level 3A](https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/level-3a-improv-showcase?lang=en-US) | 134116 | The Substation, Washington Street, Roslindale, MA | Empty; no future occurrence inferred |

The [Substation's official site](https://thesubstation.space/) identifies its
address as 4228 Washington Street, Boston, MA 02131. Existing physical club
61212 already represents this venue; no new club is needed. Its Eventbrite
source 12257 remains independent. The theater's official calendar and completed
TASK-4068 review establish 18/18b Corinth as its in-house site.

`source-review.json` records the native identities, locations, booking URLs,
page counts, and source hashes. Raw responses are private working evidence in
`/private/tmp/task4116-evidence/`; no full source-page prose is committed.

## Per-show decisions

All four rows initially belong to club 10970 with room text naming The
Substation at 4228 Washington Street. These are separate decisions:

| Show | Stored UTC instant | Decision and evidence |
| --- | --- | --- |
| 3179506, Level 1A | 2026-07-02 00:00Z | Move to existing Substation club 61212. Stored source location and the exact official experience page agree on the offsite venue. Preserve the historical instant and all references. |
| 3558318, Level 3A | 2026-07-07 00:00Z | Same source-backed move to 61212; do not infer any new occurrence from its empty calendar. |
| 3179544, Level 1B | 2026-08-21 00:00Z | Retain unchanged pending historical evidence. The current recurring page moved to Corinth and cannot establish where the August occurrence happened. |
| 3179545, Level 1B | 2026-11-06 01:00Z | Retain club 10970 and correct stale room to `18b Corinth Street, Boston, MA`. Current feed and detail page independently agree on venue and November 5 8pm occurrence. |

The first two decisions combine the recorded occurrence-level source location
with the still-consistent official experience location. The current pages no
longer list those historical dates; the repair does not claim a fresh historical
calendar lookup. The third decision deliberately avoids applying current
recurring-location text to an ambiguous past occurrence.

## Blank locations and preservation

The organizer's 144 stored shows include forty with blank room text, eight
upcoming at review time. Blank text does not establish a new venue and does not
justify moving these rows. All forty are preserved. Other stored home variants
match the verified Corinth identity; they are not separate venue records.

Routing is opt-in metadata on the organizer source. Exact reviewed location
aliases resolve to pinned existing physical identities; future experience IDs
may use the same verified venue. Blank locations preserve the home fallback
while exposing uncertainty. Unknown or conflicting explicit locations must not
silently inherit the theater or create a venue. Incomplete evidence must not
authorize stale-show reconciliation.

The guarded repair preserves show IDs, UTC instants, booking URLs, tickets,
lineups and every user-linked child row. Destination inventory and source
ownership remain intact. A private backup, collision checks, repeat validation,
and guarded rollback are required before production mutation. Execution and
public/ingestion verification are recorded separately after application.
