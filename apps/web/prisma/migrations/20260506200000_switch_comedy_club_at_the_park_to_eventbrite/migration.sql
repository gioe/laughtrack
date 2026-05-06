-- TASK-1980: Comedy Club at The Park (club 520) migrated comedy ticketing
-- from SeatEngine (venue 496, no upcoming events) to Eventbrite. The Park's
-- Comedy Show Series page at https://www.thepark.com/event/comedy-show-series/
-- links its "GET YOUR TICKETS TODAY" button to Eventbrite event
-- 1988092650636 ("Showtime at The Park RVA"), an every-other-Friday recurring
-- series at venue 295432298 (organizer 63880101343). Live API check returned
-- 5 instances (May 16 - July 11, 2026), all category 105 / subcategory 5010.
--
-- Single-venue mode (source_url omits /o/) binds the comedy instances to
-- club 520 directly. Organizer mode would auto-create a duplicate
-- "The Park RVA" club because the per-venue dedupe in
-- EventbriteScraper._scrape_organizer_async keys on (name, city, state) and
-- clubs.name = "Comedy Club at The Park" does not match the Eventbrite
-- venue's "The Park RVA" name. It would also pull in The Park's
-- non-comedy events (e.g. "Bad Bunny Dance Party" at a sibling venue id);
-- the venue endpoint returns only events at venue 295432298, which holds
-- only the comedy series.
--
-- The existing SeatEngine source row (priority=0, enabled=false) is left
-- in place. It carries task_1950_disposition (stub_dormant) and
-- task_1954_hide (left_visible_live_site) metadata stamps, which the
-- disposition-aware UPSERT carve-out (TASK-1968 / TASK-1978) preserves
-- through future scraping_sources upserts of this row.

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    external_id,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    520,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    '295432298',
    'https://www.eventbrite.com',
    0,
    TRUE,
    jsonb_build_object(
        'task_1980_onboard', jsonb_build_object(
            'organizer_id', '63880101343',
            'venue_id', '295432298',
            'event_url', 'https://www.eventbrite.com/e/showtime-at-the-park-rva-tickets-1988092650636',
            'rationale', 'The Park migrated comedy from SeatEngine (empty) to Eventbrite. Single-venue mode (no /o/) pins shows to club 520 and avoids forking a per-venue Eventbrite club through organizer-mode (name,city,state) dedupe.'
        )
    )
WHERE NOT EXISTS (
    SELECT 1 FROM scraping_sources
    WHERE club_id = 520
      AND platform = 'eventbrite'::"ScrapingPlatform"
);
