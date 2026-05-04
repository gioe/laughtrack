-- TASK-1891: Model Encore Comedy as Eventbrite production-company coverage.
--
-- Encore Comedy operates an Eventbrite organizer (id 72313162423) with ~68 live
-- future events spanning VA, MD, KY, DC, NC, PA, and other states. The previous
-- representation — six SeatEngine state-bucket clubs (639–644 with external_ids
-- 644–649 on each respective scraping_sources row) returned zero events and
-- has been hidden (visible=false) since onboarding.
--
-- Modeling Encore as a row in `production_companies` lets ScrapingService route
-- through the new EventbriteScraper organizer mode (commit b031abdc), which
-- groups the organizer feed by event venue and upserts one `clubs` row per
-- distinct venue via ClubHandler.upsert_for_eventbrite_venue. Each resulting
-- Show is tagged with production_company_id so the Encore brand is preserved
-- without forcing every event under a single fake aggregator club.
--
-- show_name_keywords is intentionally empty — the organizer feed is curated by
-- Encore directly, so every event in it is theirs and no name-based filtering
-- is needed. (Compare: production_companies id=1 'Laff House' uses keywords
-- because it scrapes a multi-tenant venue page that mixes Laff House shows
-- with non-comedy events.)
--
-- No production_company_venues row is added: the new orchestrator path in
-- ScrapingService._scrape_production_companies (commit b031abdc) detects the
-- empty mapping and synthesizes an in-memory Club proxy from the scraping_url,
-- so the venue mapping is computed per-event from the live API response rather
-- than seeded as a single primary venue.

INSERT INTO production_companies (
    name,
    slug,
    scraping_url,
    website,
    visible,
    show_name_keywords
)
VALUES (
    'Encore Comedy',
    'encore-comedy',
    'https://www.eventbrite.com/o/encore-comedy/72313162423/',
    'https://encorecomedyshows.com/home/',
    TRUE,
    ARRAY[]::text[]
)
ON CONFLICT (name) DO NOTHING;

-- Idempotent guard: ensure the legacy SeatEngine state-bucket clubs stay
-- hidden so the new per-venue Encore shows (upserted via organizer mode) don't
-- coexist with a stale visible state-bucket version. Already true in prod and
-- staging at the time this migration was authored; the UPDATE is a no-op
-- there. New environments running the migration from scratch get the same
-- end-state without an out-of-band manual step.
UPDATE clubs
SET visible = FALSE
WHERE id IN (639, 640, 641, 642, 643, 644)
  AND name LIKE 'Encore Comedy - %'
  AND visible = TRUE;
