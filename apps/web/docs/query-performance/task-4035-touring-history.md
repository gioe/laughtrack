# Touring history reuse — TASK-4035

Discover reuses only historical appearance totals and market coverage. Current
upcoming shows, available purchase links, visibility, restricted-content tags,
canonical performer metadata, popularity, home location/freshness, run counts,
classification and public show hydration remain live on every provider invocation.
The baseline SQL remains available as the fallback and equivalence oracle.

## Freshness and resource limits

`touringHistoryCache.ts` is an in-process LRU, not a durable/shared cache. Each
process can retain 64 market entries and 50,000 aggregate rows total, including
one coverage row per market, with at most eight snapshot loads in flight.
Snapshots expire five minutes **from load start**, not completion. A new process
or deployment starts empty. There is no prewarming or background timer.

Keys include classification version (currently 1), requested ZIP, radius (missing
and zero are equivalent), and the sorted unique **actual capped ZIP set** from
`resolveNearbyZips`. Different radii/centers remain isolated even if their ZIP sets
happen to match. Horizon and output limit are deliberately absent: neither changes
historical evidence. Bump the default version when changing history semantics.

A snapshot applies only at or after its original request clock and through the
next visible local show's date. Immediately after that timestamp, refresh history
because SQL uses strict `show.date < now`. This transition considers all local
shows, including sold-out/no-lineup shows, because they contribute to coverage.
Earlier request clocks force a reload. Concurrent requests for the same key share
a load only when the resulting snapshot is valid for each request's clock.

Historical backfills, deletions, changed show dates, venue geography/visibility,
alias remaps and restricted-tag edits can change historical counts within the
five-minute window. This is deliberately bounded staleness: counts are identical
to the original query at snapshot time, not guaranteed identical immediately after
historical mutations. Current hidden/restricted performers and unavailable tickets
are still excluded by fresh SQL. Home-location timestamps are never cached.
There is no new deny-list policy; existing canonical/visibility/tag predicates are
preserved in both query paths.

Expiry never serves stale evidence. Load rejection, expired/oversized results,
invalid clocks or capacity pressure return no snapshot and use the original
combined query. Failures are not stored. Clearing discards entries and prevents
older loads from repopulating them; in-flight slots remain counted until actual
settlement. This is a cache-load cap, not a database-wide concurrency cap: fallback
queries remain subject to the existing optional-provider runner's outer limits.
There is no SQL cancellation. A slow miss can exceed Discover's existing optional
provider deadline; after successful completion its snapshot can help later requests.
No schema migration or API/native payload change is required.

## Read-only production measurements

Measured September 22, 2026 using a read-only repeatable-read transaction and the
actual query builders, request clock `2026-09-22T20:00:00Z`, 90-day horizon and
25-mile radius. New York ZIP 10001 resolves to the existing 500-ZIP cap; Missoula
59801 resolves to 18 ZIPs. NYC had 20,415 historical shows and 2,141 historical
canonical performers; Missoula had zero historical coverage. Final query rows were
1,567 and 4 respectively. Full ordered result hashes match baseline and cached
SQL in both markets, including all evidence fields.

`task-4035-evidence.json` records all four EXPLAIN runs per shape, final full plans,
result hashes and a second interleaved wall-time experiment. Values below are
PostgreSQL execution milliseconds from `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`.

| Market | Original query, four runs | History snapshot build | Cached live query |
| --- | --- | --- | --- |
| NYC | 715.144, 680.937, 773.728, 679.945 | 521.196, 557.619, 532.172, 523.111 | 193.263, 167.694, 156.855, 161.560 |
| Missoula | 2.492, 2.297, 2.501, 2.362 | 2.261, 1.971, 1.869, 2.047 | 1.273, 23.758, 111.661, 1.282 |

NYC hits eliminate the historical scan and reduced measured SQL time substantially.
Top-level shared buffer accesses fell from about 71,770 to 37,680 per query (47%).
Missoula fell from 1,483 to 553 accesses (63%), but two large execution-time outliers
mean this sample does **not** establish a consistent sparse-market latency gain.
The NYC snapshot build itself used 34,924 shared block accesses. A miss executes
snapshot plus live queries, approximately the same total DB work as the original
query, and adds a round trip. Show hydration is unchanged and excluded here.

A second experiment interleaved original, snapshot+live (miss), and live (hit)
queries four times per market, using ordinary SELECTs rather than EXPLAIN.
Measured client wall times, including result transfer but excluding JS cache lookup,
classification, hydration and the HTTP/native stack:

| Market | Original wall ms | Miss wall ms, both queries | Hit wall ms |
| --- | --- | --- | --- |
| NYC | 629, 519, 382, 442 | 458, 461, 462, 436 | 200, 214, 187, 205 |
| Missoula | 24, 26, 25, 23 | 45, 41, 43, 45 | 20, 22, 22, 22 |

Sparse misses cost an extra round trip for little available DB work; dense hits
provide the main benefit. These are cache-path comparisons, not controlled cold
storage-cache tests. Buffers warmed across runs, no server caches were flushed,
and load/transfer/planner variation is present. They do not measure first iOS
launch or claim that a new serverless process gets a cache-hit benefit.

## Reproduction and verification

`task-4035-queries.json` captures the original and snapshot SQL/parameters for both
markets. Run them with a parameter-aware PostgreSQL driver in one read-only,
repeatable-read transaction. Convert the snapshot row to `TouringHistorySnapshot`
(`asOf` is the request clock), then pass it as `history` to
`buildTouringScarcityQuery` for the hit shape. JSON timestamps retain their timezone;
PostgreSQL casts them back to timestamptz. Compare full ordered rows and record
EXPLAIN plans/buffers separately from ordinary-query wall times. Update the request
clock and markets for new measurements. Do not mix controlled cold-cache claims
with warmed observations.

Regression coverage:

- Cache reuse, equivalent ZIP sets, market/radius/version isolation, TTL from load
  start, clock rollback, exact show/history transition, LRU/row/in-flight bounds,
  concurrent reuse, failures and clearing during a load.
- Real PostgreSQL-compatible fixture equality between original and cached SQL,
  canonical alias evidence, historical coverage and timestamps; live ticket,
  visibility, restriction, sold-out-title and home-location changes.
- Provider failure fallback, repeated-provider historical scan reuse, and existing
  classifier, public hydration, candidate pool and performer diversity checks.

Run:

```sh
cd apps/web
npx vitest run lib/data/home/getTouringScarcityRails.test.ts lib/data/home/touringHistoryCache.test.ts lib/data/home/homeShowCandidatePools.test.ts
npm run type-check
```

Rollback removes the provider's history-cache lookup and passes no `history` to
`buildTouringScarcityQuery`. The original combined SQL already supports that path.
