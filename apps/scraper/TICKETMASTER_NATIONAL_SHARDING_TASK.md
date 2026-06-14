# Ticketmaster national comedy discovery — shipped

_Implemented + run against prod 2026-06-13/14. National discovery now reaches the
full US comedy catalog (incl. arenas/theatres like MSG) instead of the dormant
scraper's truncated ~1k events._

## What shipped

1. **Date-window sharding** (`ticketmaster_national/scraper.py`,
   `_fetch_national_comedy_events` / `_fetch_window`) — slices the 180-day
   horizon into 10-day windows, each under the Discovery API's `DIS1035`
   deep-paging cap (`(page*size) < 1000`), unioned + deduped by event id.
   Reaches the full ~10.8k-event catalog vs ~1.2k for a single query.

2. **Per-club timeout override** = 3600s for `ticketmaster_national`
   (`core/services/scraping/__init__.py`). One "club" fetches nationally,
   upserts ~1k venues, AND persists ~10k shows — the whole pass is ~30 min, far
   beyond the 180s default.

3. **Image sourcing decoupled** — removed the inline
   `source_images_for_new_comedians` call from `show/handler.py`. A national
   scrape creates thousands of comedians; the inline 5s/comedian Wikidata/TMDb/
   CDN throttle made runs take hours. Backfill is now solely the standalone
   `scripts.core.source_comedian_images` job (`has_image=false`), mirroring the
   separated popularity pipeline.

4. **Upsert idempotency fix** (`UPSERT_CLUB_BY_TICKETMASTER_VENUE` in
   `sql/club_queries.py` + handler param). The `scraping_sources` INSERT only
   declared `ON CONFLICT (club_id, platform, priority)`, but the table has two
   more partial unique indexes (`ticketmaster_id_unique`,
   `club_priority_enabled_unique`, both `WHERE enabled`). An already-configured
   venue violated a constraint NOT covered by the conflict target, aborting the
   whole statement so the club was never returned and the venue + its shows were
   dropped (158 errors / ~143-venue gap on the first run). Fix: guard the source
   INSERT with `NOT EXISTS` on those two indexes and return the club
   unconditionally; the disabled-source re-enable carve-out (TASK-1968/1978)
   still flows through `ON CONFLICT`. Validated against the real prod schema in a
   rolled-back transaction (existing-name+tmid, new-name+existing-tmid, happy
   path) + unit tests.

5. **Chunked self-persistence** (`_persist_in_chunks`). A national result is
   ~10k shows — more than the per-club pipeline's single `insert_club_result`
   can write within `_DB_WRITE_TIMEOUT` (300s; first attempt lost ~9k shows).
   The scraper now persists its own shows in 1000-show chunks via
   `ShowService.insert_shows` and returns `[]` so the pipeline doesn't
   re-persist. Each chunk commits independently → durable partial progress.

6. **Non-comedy filter in the national path** (`_process_events`). The Discovery
   API's `classificationName=Comedy` is loose — it also returns multi-genre
   events (music festivals with one comedy act on the bill) whose own
   classification is Music/Sports. The venue-specific TM scrapers drop these via
   `TicketmasterEventTransformer._is_comedy_event`, but the national scraper
   calls `create_show` directly and bypassed that gate, so it persisted music
   events and turned every attraction on the bill into a "comedian" (Bruce
   Springsteen, Foo Fighters, …). `_process_events` now applies the same
   `_is_comedy_event` gate before grouping/creating.
   - **One-time cleanup** (2026-06-14): removed the contamination already in
     prod. Identified PURE musicians — acts that appear in hard non-comedy
     (Music/Sports/Film) events and NEVER in any comedy event (so real comedians
     TM mistags as Music, e.g. Brad Williams / Josh Wolf, are protected). Deleted
     157 bogus musician "comedian" rows + 6 all-musician shows. Backed up to
     `scripts/tmp_cleanup_backup.json` first (reversible).

## Final prod result (2026-06-14)
- Catalog 518 → **1,344 clubs**; **841 new national venues, 0 with zero shows**
  (every discovered venue has shows). Venues that matched existing clubs by name
  (Barclays → club 2464, Addison Improv → 29, …) had shows attached there.
- **~8.8k national shows** (the deduped total; 10.8k was the pre-dedup produced
  count). MSG / Radio City / Barclays / TD Garden / United Center all live with
  shows.
- Run: ~29 min, 0 upsert errors, 0 chunk-persist failures.
- Trigger = hidden club **4036**, `scraping_sources.enabled = FALSE` → the
  national *discovery* job does NOT run in the nightly GHA scrape. Re-enable
  deliberately to find new venues.
- **Discovered venue sources switched `live_nation` → `ticketmaster_comedy`**
  (all 827, post-run). These per-venue sources stay `enabled`, so each venue
  self-refreshes its comedy listings nightly — independent of the disabled
  discovery trigger. `ticketmaster_comedy` (FocusedTicketmasterComedyScraper)
  adds `classificationName=Comedy` at the API level + add-on filtering on top of
  the transformer's `_is_comedy_event`, so multi-purpose rooms (MSG, arenas,
  theatres) can't pull concerts/sports — not even the untagged-event edge case
  that bare `live_nation` allows. Safe for the pure comedy clubs too: every one
  of these venues was discovered via `classificationName=Comedy`, so the comedy
  filter captures the same set they were created from. Reversible
  (`UPDATE scraping_sources SET scraper_key='live_nation' WHERE club_id>4036`).

## Known / deferred
- **~97% null price** on national shows — the Discovery API doesn't expose
  `priceRanges` for comedy (TASK-2098 / TASK-2827). Accept or pair with a price
  backfill before any nightly activation.
- `scrape_async` returns `[]` (persists itself), so the per-club run metric
  reports 0 shows for the trigger club. Cosmetic; only matters if activated
  nightly and someone reads that one club's metric.
- Nightly activation also means catalog churn (~3× venues incl. non-comedy-club
  rooms — Vegas residencies, Broadway, arenas — since `classificationName=Comedy`
  is coarse). A comedy-quality filter on the national path is the alternative if
  it's ever activated.

## Note
`tusk task-insert` was broken (is_deferred, tusk#1096) when this work was done,
so this is a repo note rather than a tusk task.
