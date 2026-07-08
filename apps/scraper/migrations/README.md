# Scraper SQL migrations

Plain `*.sql` files applied to the production Neon database by
`apps/scraper/bin/migrate`. This is a **separate migration system** from the
`apps/web` Prisma migrations, even though both write the **same** Neon database.
Read this before adding a file here.

## Two migration systems, one database

| | Prisma (`apps/web/prisma/migrations/`) | Scraper SQL (this directory) |
|---|---|---|
| **Owns** | Table/column/index **DDL** — the canonical relational schema | **Data fixes** (club onboarding, scraper-key switches, dedup/cleanup) and **scraper-only objects** (e.g. the `mv_scraper_health_*` materialized views) |
| **Applied by** | `prisma migrate deploy`, run in the Vercel **buildCommand on every merge to `main`** | `python bin/migrate`, run in the **nightly** `scraper-schedule.yml` "Apply pending scraper migrations" step (~21:00 UTC), and on demand via `make migrate` |
| **Ledger** | `_prisma_migrations` (checksum + name) | `migrations_log` (filename, `applied_at`) |

**Ownership rule:** Prisma owns table DDL; scraper SQL owns data and
scraper-only objects. Do **not** add or alter a table/column/index here — put
structural DDL in a Prisma migration so `prisma/schema.prisma` stays the single
source of truth for the relational schema. It is expected and fine for a scraper
migration to build objects **on top of** Prisma-owned tables — the
`scraper_health` materialized views read Prisma-owned `scraper_runs` /
`scraper_run_clubs` / `scraper_run_errors`.

## How `bin/migrate` applies files

`bin/migrate` (read it — it is ~200 lines):

1. Takes a Postgres advisory lock so concurrent invocations serialize.
2. Ensures the `migrations_log` table exists (`CREATE TABLE IF NOT EXISTS`).
3. Globs `*.sql`, sorts by **filename**, and applies only files whose name is
   **not already in `migrations_log`** (`get_pending`). Each file is executed in
   its own transaction and, on success, its filename is recorded — committed
   together. A file that fails rolls back and is **not** recorded, so the run
   exits non-zero (failing the nightly job loudly) and that file is retried in
   full on the next invocation.

So each migration file is applied **exactly once** and keyed by its filename.

## Idempotency is mandatory

Every migration here must be idempotent — guarded inserts
(`INSERT ... WHERE NOT EXISTS` / `ON CONFLICT DO NOTHING`), guarded updates, and
`... IF [NOT] EXISTS` for objects. This is convention **#186**. Why it matters
even though a logged file does not re-run:

- **Partial-failure retry.** A multi-statement file that fails partway rolls
  back *un-logged* and re-runs **in full** on the next nightly invocation, so its
  earlier statements execute a second time. A bare `INSERT`/`CREATE` would then
  error or duplicate; a guarded one no-ops.
- **The change may already exist by another path.** The same club/data may have
  been seeded by a Prisma migration, a manual `make migrate` of a prior draft, or
  a fresh-environment restore. A non-idempotent migration can **clobber later
  manual data changes** (convention #186) or collide with an existing unique
  index.
- **Fresh environments / log loss.** A guarded migration is safe to replay
  against a database that already has the data.

Dry-run against prod in a rolled-back transaction before merge when a migration
touches existing rows (see convention #275 for the dedup/close-duplicate case).

## Materialized-view changes: new DROP+recreate migration, never edit-in-place

The `mv_scraper_health_*` materialized views are defined in
`20260703_scraper_health_summary_materialized_views.sql` (later recreated by
`20260704_scraper_health_club_labels_stable_series.sql` and
`20260706174000_retune_consecutive_zero_health_alert.sql`). The scraper
`REFRESH`es them once at the end of each full run; the Grafana
`scraper-health-alerts.yaml` rules read from them.

Per the `scraper-health-alerts.yaml` header (read it — do not paraphrase from
memory): the view migration uses `CREATE MATERIALIZED VIEW IF NOT EXISTS`, so
**editing it in place and re-applying is a no-op** (the view already exists) and
a `REFRESH` does **not** pick up a definition change. **A window or semantic
change requires a NEW migration that `DROP`s and recreates the affected
view(s)** — never an edit to the existing migration or an in-place edit here.
Rule 5 (staleness) stays an inline live query and is unaffected.

## Filenames

- **New files** use a full `YYYYMMDDHHMMSS_<description>.sql` timestamp prefix
  (e.g. `20260707140000_onboard_quezadas_comedy_club_holdmyticket.sql`). The
  older `YYYYMMDD_` (date-only) files predate this convention; match the
  14-digit form for anything new so filename sort order is unambiguous within a
  day.
- **NEVER rename an applied file.** `migrations_log` keys on the exact filename,
  so a rename makes `bin/migrate` treat it as a new, unapplied migration and
  re-run it. If a migration is already on `main`/prod, it is immutable — write a
  new one instead.

## Deploy ordering

- **Prisma** (table DDL) applies on **merge** via the Vercel buildCommand, so
  schema changes land when the web app deploys.
- **Scraper SQL** (this directory) applies **nightly** at ~21:00 UTC before the
  scrape, so a data migration can lag the repo by up to ~24h until the nightly
  run (apply immediately with `make migrate` if you need it live sooner).
- A scraper migration that depends on a new column/table must not merge before
  the Prisma migration that adds it — the Prisma DDL lands on merge, the scraper
  SQL on the following nightly, so the dependency is normally satisfied, but
  don't rely on the reverse order.

See `apps/web/DEPLOYMENT.md` → **Running Migrations** for the Prisma side (the
pre-merge Neon-branch gate, P3009 recovery, and the fresh-environment seed).
