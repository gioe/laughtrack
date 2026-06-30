# Comedian Home City And Club Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist each comedian's inferred home city and home club, defined as the city and club where they have appeared most often.

**Architecture:** Store denormalized nullable fields on `comedians`, recomputed from canonical `lineup_items -> shows -> clubs` history. The recompute should run after lineup persistence, next to existing show-count and popularity refreshes, because a newly inserted comedian has no stable home signal until lineups have been written.

**Tech Stack:** PostgreSQL, Prisma schema/migrations in `apps/web`, Python scraper handlers and SQL query constants in `apps/scraper`.

---

## Files

- Modify: `/Users/mattgioe/Desktop/projects/laughtrack/apps/web/prisma/schema.prisma`
- Create: `/Users/mattgioe/Desktop/projects/laughtrack/apps/web/prisma/migrations/<timestamp>_add_comedian_home_location/migration.sql`
- Modify: `/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/sql/comedian_queries.py`
- Modify: `/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/src/laughtrack/core/entities/comedian/model.py`
- Modify: `/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/src/laughtrack/core/entities/comedian/handler.py`
- Modify: `/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/src/laughtrack/core/entities/show/handler.py`
- Add tests near existing comedian SQL/handler tests under `/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/tests/`

## Decision: Write Lifecycle

Do not write home city/home club in `ComedianHandler.insert_comedians`. That path creates name-only stubs before lineup rows exist, and `ON CONFLICT DO NOTHING` intentionally avoids overwriting established comedian data.

Write these fields after `LineupHandler.batch_update_lineups()` in `ShowHandler.update_show_lineups()`, using the same affected comedian UUID set already passed to `update_comedian_popularity()`. Also call the same recompute from full popularity/backfill flows so historical corrections, stale lineup deletes, and migration backfills converge.

Use all historical shows by default, not only upcoming/recent shows. If product later wants "current home market", add a second recency-weighted field rather than changing the meaning of `home_*`.

Tie-breakers should be deterministic:
- Most appearances wins.
- Then most recent appearance wins.
- Then lowest `club_id` for home club.
- For city, group on normalized `clubs.city/state/country`; then choose most appearances, most recent appearance, lexicographic city/state/country.

## Task 1: Schema And Migration

- [ ] Add nullable fields to `Comedian` in Prisma:

```prisma
homeCity        String? @map("home_city")
homeState       String? @map("home_state")
homeCountry     String? @map("home_country")
homeClubId      Int?    @map("home_club_id")
homeClub        Club?   @relation("ComedianHomeClub", fields: [homeClubId], references: [id], onDelete: SetNull)
homeClubUpdatedAt DateTime? @map("home_club_updated_at") @db.Timestamptz
```

- [ ] Add the inverse relation on `Club`:

```prisma
homeComedians Comedian[] @relation("ComedianHomeClub")
```

- [ ] Add an index on `homeClubId`:

```prisma
@@index([homeClubId])
```

- [ ] Create a manual Prisma migration under `apps/web/prisma/migrations/<timestamp>_add_comedian_home_location/migration.sql`:

```sql
ALTER TABLE comedians
    ADD COLUMN IF NOT EXISTS home_city text,
    ADD COLUMN IF NOT EXISTS home_state text,
    ADD COLUMN IF NOT EXISTS home_country text,
    ADD COLUMN IF NOT EXISTS home_club_id integer,
    ADD COLUMN IF NOT EXISTS home_club_updated_at timestamptz;

ALTER TABLE comedians
    ADD CONSTRAINT comedians_home_club_id_fkey
    FOREIGN KEY (home_club_id)
    REFERENCES clubs(id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS comedians_home_club_id_idx
    ON comedians(home_club_id);
```

- [ ] Validate with the repo-pinned Prisma binary, not `npx`:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/web
node_modules/.bin/prisma validate
```

## Task 2: SQL Recompute Query

- [ ] Add `ComedianQueries.BATCH_UPDATE_COMEDIAN_HOME_LOCATION`.

Shape:
- Input: `comedian_uuids text[]`
- Compute `club_counts` from `lineup_items li JOIN shows s JOIN clubs cl`
- Filter to target comedian UUIDs and clubs with non-empty city for city selection.
- Rank club rows by `appearance_count DESC`, `last_seen_at DESC`, `club_id ASC`.
- Rank city rows by `appearance_count DESC`, `last_seen_at DESC`, `city ASC`, `state ASC`, `country ASC`.
- Update `comedians.home_*` and `home_club_id`, plus `home_club_updated_at = NOW()`.

Important: use lowercase SQL table names: `comedians`, `clubs`, `shows`, `lineup_items`.

## Task 3: Scraper Model Compatibility

- [ ] Add nullable fields to `Comedian` dataclass:

```python
home_city: Optional[str] = None
home_state: Optional[str] = None
home_country: Optional[str] = None
home_club_id: Optional[int] = None
```

- [ ] Read these fields in `Comedian.from_db_row`.

- [ ] Do not include these fields in `to_insert_tuple()` or `BATCH_ADD_COMEDIANS`; home location is derived, not ingestion input.

## Task 4: Handler Recompute Method

- [ ] Add `ComedianHandler.update_home_location(comedian_uuids: list[str]) -> None`.

Implementation notes:
- Return immediately on an empty list.
- Chunk at the same size as `_SHOW_COUNTS_REFRESH_CHUNK_SIZE` or introduce `_HOME_LOCATION_REFRESH_CHUNK_SIZE = 250`.
- Execute `BATCH_UPDATE_COMEDIAN_HOME_LOCATION` once per chunk.
- Log counts in the message string, not only context dicts.

## Task 5: Lifecycle Integration

- [ ] In `ShowHandler.update_show_lineups`, after `lineup_handler.batch_update_lineups(shows, db_lineups)` and before/near `update_comedian_popularity(comedian_uuids)`, call:

```python
self.comedian_handler.update_home_location(comedian_uuids)
```

- [ ] Optionally call it inside `ComedianHandler.update_comedian_popularity()` before fetching details, but avoid duplicate work if `update_show_lineups` already calls both in sequence. Preferred shape is a single broader method:

```python
self.comedian_handler.update_derived_show_metrics(comedian_uuids)
```

that refreshes show counts, home location, recency/popularity in one place. If that refactor is too broad, keep `update_home_location` as a separate call in `update_show_lineups` and in any existing full backfill CLI that invokes popularity for all comedians.

## Task 6: Backfill

- [ ] Add a one-time backfill path. Best option: have the migration add nullable columns only, then run a scraper-side recompute using the Python handler against all comedian UUIDs.

Command shape:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper
.venv/bin/python3 -c "from laughtrack.core.entities.comedian.handler import ComedianHandler; h=ComedianHandler(); h.update_home_location(h.get_all_comedian_uuids())"
```

- [ ] If this needs to run automatically in deployment, add an idempotent scraper migration or maintenance script rather than stuffing the full data backfill into the Prisma DDL migration. The aggregation may touch large tables and should be validated against prod-shaped data first.

## Task 7: Tests

- [ ] Add SQL shape tests asserting the recompute query references `lineup_items`, `shows`, `clubs`, lowercase `comedians`, and deterministic rank ordering.

- [ ] Add handler tests with mocked `execute_with_cursor` verifying empty input no-ops and large input chunks.

- [ ] Add an integration-style SQL test if the existing test harness supports temporary Postgres or SQLite-compatible query extraction. Minimum cases:
  - Comedian with 3 appearances at Club A and 2 at Club B gets Club A.
  - Comedian with tied club counts gets the club with the latest show.
  - Comedian with tied city counts gets deterministic city/state/country ordering.
  - Comedian with no lineups remains `NULL` for all home fields.

## Task 8: Product Surface Follow-Up

- [ ] Decide where to expose the fields: API DTOs, comedian detail page, search cards, admin views, or filters.

- [ ] Keep that as a separate UI/API task unless the current feature explicitly requires user-visible display. The schema and lifecycle work can ship independently and be verified from database rows.

## Verification

- Run scraper unit tests around comedian handler/query updates:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper
.venv/bin/python3 -m pytest tests/sql tests/core/entities -q
```

- Validate Prisma:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/web
node_modules/.bin/prisma validate
```

- Before merge, validate the migration and recompute query against prod-shaped data because this touches historical `lineup_items` and `shows`.
