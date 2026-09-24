# Coordinate backlog diagnosis — TASK-4046

Snapshot refreshed 2026-09-24. There were 913 venues missing at least one coordinate, 790 visible venues, and 686 visible venues with 3,479 upcoming shows. Of these, 788 are active physical club/venue rows; 685 have 3,460 upcoming shows. Two visible festival records are excluded from the physical-venue enrichment queue. See before.json.

The deployed selection was ORDER BY id LIMIT 30 over every missing-coordinate row. Its next batch contained 12 hidden venues; 883 rows were outside that batch. Failed lookups wrote no attempt state, so an unresolved first batch could repeat forever. A regression reproduced consecutive selections [1,1] instead of [1,2]. This proves the starvation mechanism, not a historical count of starved venues.

Two completed nightly runs (35933510357 and 35797636435) retained neither geocoding summaries nor provider errors. INFO summaries were suppressed by WARNING console output, and finalizer log files were not uploaded. Historical successful, failed, retried and never-attempted counts are therefore unknown, not zero. nightly-evidence.json records artifact checks and log hashes. TASK-4076 tracks per-run observability.

## Controlled provider comparison

Twelve high-inventory addresses were queried serially at 15-second intervals. All requests returned HTTP 200; no 403, 429, timeout or other provider error occurred. The existing query shape appended city/state/ZIP even when already present in the address: only 3/12 returned candidates. Removing duplicate components increased this to 9/12. Seven responses passed strict identity checks; empty results, differing coordinate pairs for one address, and conflicting locality evidence were not accepted. HTTP success is not proof of a correct match.

Example: 616 Lavaca St, Austin, TX 78701, Austin, TX, 78701, US returned no result; the deduplicated address returned the exact house and road in Austin. Another response to 99 MacDougal St included both Manhattan 10012 and Brooklyn 11233; only the matching postal address passed.

See provider-original-queries.json and provider-deduplicated-queries.json. Data © OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright.

## Repair

The shared enrichment now persists geocode_attempted_at, geocode_attempt_count and geocode_outcome. It selects active visible physical venues, prioritizes never-attempted and oldest eligible rows, and prioritizes upcoming inventory within equal attempt times. Misses cool down seven days; failures one day. Provider 403/429 stops the batch and pauses requests across runs for one day. A PostgreSQL advisory lock serializes workers, with at least 15 seconds between requests across successive runs.

Queries avoid duplicate address components. Results require finite in-range coordinates, house/road/postal/country agreement, agreement with supplied and parsed US city/state, and one matching coordinate pair. The US-only ZIP-centroid fallback was removed. Existing coordinate halves and concurrently changed venue identities are protected by update guards. Lookup failures are distinguished from database persistence failures.

The public provider's regular-job limit is four requests/minute, single-threaded, with cached results: https://operations.osmfoundation.org/policies/nominatim/. This task repairs the existing integration; NOMINATIM_SEARCH_URL allows changing providers without source edits. The manual backfill CLI now delegates to this path and defaults to a read-only candidate preview.

Schema validation covered all 2,812 club rows, rollback, and idempotent reapplication. The focused schema SQL was applied directly; other pending migrations were not deployed. Later Prisma deployment may reapply it safely. sql-validation.json and validate_coordinate_sql.py additionally exercise real PostgreSQL selection, locking, persistence and rollback. Both named regressions failed before the fix and pass afterward; the full scraper commit gate and Prisma schema validation pass.
