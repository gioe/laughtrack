# Ticketmaster national comedy discovery — status + follow-up

_Last updated 2026-06-13 after implementing + running national discovery against prod._

## What's DONE (shipped to the working tree + run against prod once)

1. **Date-window sharding** in `ticketmaster_national/scraper.py` — `_fetch_national_comedy_events`
   now slices the 180-day horizon into 10-day windows (`_fetch_window`), each staying under the
   Discovery API's `DIS1035` deep-paging cap (`(page*size) < 1000`), unioned + deduped by event id.
   Reaches the full ~10,951-event catalog (vs ~1,200 single-query). MSG, Radio City, Barclays,
   TD Garden, United Center now surface. 14/14 unit tests pass.
2. **Per-club timeout override** — `_PER_SCRAPER_TIMEOUT_OVERRIDES["ticketmaster_national"] = 1800`
   in `core/services/scraping/__init__.py`. The national scraper is one "club" doing ~1k venue
   upserts; the 180s default killed it mid-upsert (executor torn down → "cannot schedule new
   futures after shutdown"). 1800s lets it complete.
3. **Image sourcing decoupled from the scrape path** — removed the inline
   `source_images_for_new_comedians` call from `show/handler.py`. A national scrape creates
   thousands of new comedians; the inline per-comedian 5s Wikidata/TMDb/CDN throttle made a run
   take hours. Image sourcing is now solely the standalone `scripts.core.source_comedian_images`
   job's responsibility (backfills `has_image=false`), mirroring the separated popularity pipeline.

### Prod run result (2026-06-13)
- Catalog 518 → **1,344 clubs** (1,335 visible); **825 new national venues**, **6,524 national shows**.
- MSG / Radio City / TD Garden / United Center / UBS Arena / Bridgestone all live **with shows**.
- **97.1% null price** on national shows (the TASK-2827 problem; accepted for this run).
- Trigger club id **4036** ("Ticketmaster National (platform trigger)", `visible=false`) drives the
  scraper. **Its scraping_sources row is now `enabled=false`** so the nightly GHA scrape does NOT
  run national discovery. Re-enable deliberately to run again.

## The OPEN follow-up: upsert idempotency bug (the ~143-venue gap)

The run logged **158 errors**, all from `ClubHandler.upsert_for_ticketmaster_venue` →
`ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE` (`sql/club_queries.py`). The `scraping_sources`
INSERT only declares `ON CONFLICT (club_id, platform, priority)`, but the table has two more
partial unique indexes (both `WHERE enabled = true`):

- `scraping_sources_ticketmaster_id_unique` — `(ticketmaster_id) WHERE platform='ticketmaster' AND enabled AND ticketmaster_id IS NOT NULL`
- `scraping_sources_club_priority_enabled_unique` — `(club_id, priority) WHERE enabled`

When a national-discovered venue maps to a club / ticketmaster_id that **already has an enabled
source** (the ~48 overlap venues already configured under `live_nation`/`ticketmaster_comedy`, plus
name-collisions with existing clubs that have an enabled priority-0 source), the INSERT violates one
of those indexes — which is NOT the declared conflict target — so the whole statement rolls back. The
final `SELECT ... WHERE EXISTS (SELECT 1 FROM upserted_source)` then returns no club, and the
handler skips the venue **and its shows**. Net: ~143 venues short of the projected ~968 (incl.
Barclays Center, which landed with 0 shows). These are all venues that already exist / are already
scrape-able — so nothing is lost from the platform, but they don't get national shows attached.

### Validated fix design (needs a DB-backed test before shipping)
Keep the source INSERT but guard it so it only runs when it won't violate the two partial indexes,
and return the club unconditionally:

```sql
upserted_source AS (
    INSERT INTO scraping_sources (club_id, platform, scraper_key, ticketmaster_id, source_url, priority, enabled, metadata)
    SELECT id, 'ticketmaster', 'live_nation', %s, 'https://www.ticketmaster.com', 0, TRUE, '{}'::jsonb
    FROM upserted_club
    WHERE NOT EXISTS (   -- ticketmaster_id_unique
        SELECT 1 FROM scraping_sources s2
        WHERE s2.platform = 'ticketmaster' AND s2.enabled AND s2.ticketmaster_id = %s
    )
    AND NOT EXISTS (     -- club_priority_enabled_unique
        SELECT 1 FROM scraping_sources s3
        WHERE s3.club_id = (SELECT id FROM upserted_club) AND s3.priority = 0 AND s3.enabled
    )
    ON CONFLICT (club_id, platform, priority) DO UPDATE SET ...  -- unchanged (preserves TASK-1968/1978 re-enable carve-out for the disabled-source case)
    RETURNING club_id
)
SELECT uc.*, '[]'::json AS scraping_sources
FROM upserted_club uc           -- return the club unconditionally (was: WHERE EXISTS upserted_source)
```

Why it's safe: the guards only skip the source INSERT when an **enabled** source already occupies the
unique slot (exactly when a duplicate must not be created); the disabled-source re-enable path still
flows through `ON CONFLICT (club_id, platform, priority) DO UPDATE`. **Caveat:** this is shared SQL
the live venue-specific TM scrapers (`live_nation`, `ticketmaster_comedy`) also use, so it needs a
DB-backed test covering: new venue, overlap-by-tm_id, name-collision-with-enabled-priority-0, and the
disabled-source re-enable carve-out — before shipping.

### To complete coverage after the fix
Re-run `python -m scripts.core.scrape_shows --club-id 4036` (re-enable the source first) to capture
the missing ~143 venues incl. Barclays. Idempotent given the fix.

## Gating before any production (nightly) activation
- Resolve / accept the 97% null-price reality (TASK-2827 / TASK-2098).
- Decide whether national discovery should run nightly (catalog grows ~3×, includes non-comedy-club
  venues — Vegas residencies, Broadway houses, arenas — since the API's `classificationName=Comedy`
  is coarse). A comedy-quality filter on the national path was discussed as an alternative.

## Note
`tusk task-insert` was broken (is_deferred column, tusk#1096) when this was written, so this lives as
a repo note instead of a tusk task. File it once tusk#1096 lands.
