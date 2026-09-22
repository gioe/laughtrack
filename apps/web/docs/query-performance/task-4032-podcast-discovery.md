# Discover podcast candidate query — TASK-4032

Measured 2026-09-22. Add a B-tree on `podcast_episodes.release_date`.
The existing `(podcast_id, release_date)` index remains useful for per-podcast
queries but scans too much index data for Discover's global date window.
The application SQL and ranking code are unchanged: eligibility, personalization,
canonical identity, deny lists, date bounds, candidate limit and diversity remain intact.

## Measurements

Exact query from `buildPodcastEpisodeDiscoveryQuery`, with cutoff
`2026-08-23T15:00:00Z`, now `2026-09-22T15:00:00Z`, candidate limit 200.
Anonymous and personalized SQL shapes were tested separately. The profile was
selected by highest combined favorite count (11 comedian favorites, zero podcast
favorites); its identity is redacted. Tests additionally cover podcast favorites.
Times below are PostgreSQL execution times from `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`.

| Dataset / shape | Before (ms, execution order) | After (ms, execution order) |
| --- | --- | --- |
| Production anonymous | 2985.104, 67.606, 62.245, 63.610 | See post-deployment verification |
| Production personalized | 64.891, 59.409, 58.623, 60.301 | See post-deployment verification |
| Temporary copy anonymous | 116.400, 45.247, 48.977, 562.433, 449.955 | 30.713, 26.689, 27.792, 27.186, 27.588 |
| Temporary copy personalized | 54.899, 52.040, 45.711, 46.413, 46.512 | 28.720, 28.240, 28.390, 27.358, 30.486 |

The first production anonymous run was read-heavy (5,417 shared blocks read),
not a controlled cold-cache experiment. Its episode index scan dominated at
2,883 ms. Subsequent runs benefited from warmed buffers. No cache was flushed,
and no independent cold personalized run was obtained. These are SQL timings,
not HTTP or iOS launch timings; concurrent Discover providers must not be summed.

The experiment copied all 612,443 episode rows/columns into a session-local temp
table, retained equivalent primary-key and podcast/date indexes, and queried the
real related tables in one repeatable-read snapshot. It then added only the date
index. Five runs of each shape and full ordered result hashes were captured before
and after. Both shapes returned exactly the same 200 rows and full values.
Other episode indexes were omitted because they do not serve this query; an
initial attempt to clone every index exceeded the 180-second copy timeout and
rolled back. The successful copy/setup took 43.36 seconds.

The conservative comparison uses the fastest before run, avoiding the noisy
anonymous outliers: 45.247 ms versus 26.689 ms (41% lower), and 45.711 ms versus
27.358 ms (40% lower). All after runs stayed below 31 ms. Temp tables have local
buffers and cannot use parallel scans, so these measurements isolate the index
benefit but are not predictions of production latency. Cache state, table layout,
concurrent load and planner statistics differ from production.

The representative before plan uses a bitmap scan of the podcast/date index;
after uses `benchmark_release_date_idx`. The final anonymous episode heap scan
falls from 152.547 ms / 2,979 local reads to 0.876 ms / zero local reads. The final
personalized scan falls from 18.797 ms to 0.912 ms. Both select 981 recent episodes.
See `task-4032-evidence.json` for timings, ordered result hashes and full
representative before/after plans (including buffers). No result payloads or
profile identifiers are committed.

## Cost and rollout

The trial index occupied 11,485,184 bytes (10.95 MiB), about 1.31% of the
877,117,440-byte episode heap, excluding TOAST and other indexes. The temporary
nonconcurrent build took 0.408 seconds; this is not an estimate for a concurrent
production build. Each inserted/deleted episode and release-date update must
maintain one additional B-tree, with additional WAL, vacuum and storage work.
No covering payload columns or rolling-date partial predicate are added.

Migration `20260922160000_podcast_episode_release_date_index` uses a single
`CREATE INDEX CONCURRENTLY` statement, without `BEGIN`/`COMMIT` or bundled `SET`
statements. The repo pins Prisma 6.5.0, whose PostgreSQL migrations are not wrapped
in transactions unless explicitly requested ([Prisma documentation](https://www.prisma.io/blog/prisma-migrate-dx-primitives)).
Do not apply Prisma 8 transaction semantics to this pinned migration runner.
Concurrent construction permits normal writes but requires two scans and can wait
for old transactions; a failed build can leave an invalid index
([PostgreSQL documentation](https://www.postgresql.org/docs/current/sql-createindex.html)).

Deploy through the existing pinned Prisma migration pipeline, using `DIRECT_URL`.
Do not run `migrate dev`, upgrade Prisma, or blindly apply unrelated pending migrations.
Inspect `pg_stat_progress_create_index` and old transactions if construction stalls.
After deployment, verify:

```sql
SELECT i.indisvalid, i.indisready, pg_size_pretty(pg_relation_size(i.indexrelid))
FROM pg_index i
WHERE i.indexrelid = to_regclass('public.podcast_episodes_release_date_idx');
```

Both flags must be true. Repeat the captured query shapes with current dates and
representative profiles; confirm the new index appears in actual plans and compare
warm runs separately from any read-heavy first run. Observe endpoint timings as a
separate measure. Do not assert production improvement solely from the temp trial.

If construction fails, inspect the index validity before retrying. Drop an invalid
artifact with `DROP INDEX CONCURRENTLY public.podcast_episodes_release_date_idx`
(outside a transaction), then use the pinned Prisma `migrate resolve --rolled-back`
for this failed migration and retry deployment. No `IF NOT EXISTS` is used because
it could silently preserve an invalid index.

Rollback: a new compensating migration drops this index concurrently and removes
`@@index([releaseDate])` from the schema. Keep applied migration history intact.
The original podcast/date index and application behavior remain available.

## Reproduction and correctness

`task-4032-queries.json` captures both Prisma SQL texts and parameter arrays;
replace the `benchmark-profile` placeholder with a representative profile ID
locally. Use a parameter-aware PostgreSQL driver; do not interpolate identities
into shell commands or publish them in EXPLAIN artifacts. Use a read-only
repeatable-read transaction for production baselines. For the isolated experiment,
copy episode rows to a temporary table, create the two baseline indexes, ANALYZE,
run five EXPLAINs and hash the full ordered result, create the release-date index,
and repeat in the same snapshot. Roll back to remove temporary objects.

Regression tests exercise both SQL shapes against PGlite, including accepted
appearances, visibility, canonical parents, active/restored podcast denies,
normalized comedian denies, inclusive date bounds, null/out-of-window dates,
profile-scoped favorites, ordering/limit, latest active artwork, and the existing
ranking/deduplication/diversity behavior.
