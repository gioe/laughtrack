# TASK-4044 venue postal audit — September 24, 2026

Snapshot fixed at 2026-09-24T16:11:51.886455Z. Shows counted strictly after that instant; all counts concern visible venues. Sources and unchanged address guards are recorded per venue in sources.json.

| Measure | Before | After |
|---|---:|---:|
| Visible venues missing ZIP | 64 | 16 |
| Missing-ZIP venues with upcoming shows | 56 | 12 |
| Upcoming shows at missing-ZIP venues | 3,282 | 374 |

48 source-verified US venues received postal codes, including 44 with 2,908 upcoming shows. These shows now satisfy the postal portion of nearby discovery; this is not a claim that all satisfy lineup or other display requirements. No show, identity, address, visibility, or other metadata changed.

## Verification and application

The migration matches ID, exact name, address, country (including nullness), visibility, and a missing/blank ZIP. Existing ZIPs are never replaced. Local PostgreSQL validation replayed the 64-row production-shaped snapshot: 48 updates, then zero; nine guard scenarios and all three missing representations passed. See validate_migration.py and migration-validation.json.

The exact migration was then executed against production in a rolled-back transaction and applied in a separate committed transaction: both affected exactly 48 rows, and each immediate repeat affected zero. production-rollback.json and production-apply.json record results. A separate connection independently confirmed the after counts. The migration remains safe for later Prisma deployment; it will be a no-op for already-filled rows. No unrelated pending migrations were applied.

zip-pools.json uses the installed zipcodes package and the same 25-mile radius/500-result cap as the production helper. All 48 venues match an exact ZIP search and a nearby-origin pool. Two origins, 94102 and 01923, are omitted from their own radius pools because the package calculates NaN for self-distance. Nearby origins still include them. TASK-4072 tracks ensuring the searched ZIP is retained; that bug was not changed here.

## Metadata behavior

No evidence was found that these update paths erased populated ZIPs. The reproduced defect was that five name-conflict paths never refilled missing postal data, while Ticketmaster source-ID updates mishandled whitespace. Six paths now fill missing ZIPs without replacing populated values. Before the fix, 20 of 96 regression cases failed; afterward 96 passed, plus 118 existing club tests. All 96 complete-query cases also passed on temporary PostgreSQL; the full scraper commit gate passed.

## Deferred cases and follow-ups

All 16 exclusions retain their missing ZIP. Three are non-US records (1060 Netherlands, 1061 Spain, 11599 Canada); US numeric ZIP matching must not guess international postal codes. The other 13 require identity, location, routing, or stronger source evidence:

- TASK-4065: organizer/multiple-location review for Yardbird613, Alameda447, Lets Comedy469, Comedy Shoppe327, Pagliacci8701, Big Pine573; AC Jokes412 is additionally included for routing review, though its named flagship ZIP was verified and filled.
- TASK-4066: Carry On600, Phoenix cocktail experience attached to New Rochelle address.
- TASK-4067: Whiplash1347, Atlanta official domain attached to Brooklyn address.
- TASK-4068: Rozzie10970, official street differs from stored street.
- TASK-4069: District Dome554, official host ZIP differs from stored address ZIP.
- TASK-4070: Laugh Tonight855, identity/address mismatch with Laugh Tour.
- TASK-4071: Deaf Puppy551 and Nest8713, authoritative postal evidence still unresolved.

Each follow-up carries source URLs and acceptance criteria. Sources also preserve nonblocking postal-city/street-direction differences (Stardome and Alley Stage). Leading zeros remain strings.
