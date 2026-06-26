-- Onboard Stella's Pinball Arcade & Lounge (Greeley, CO) via the existing json_ld scraper - TASK-3426.
--
-- Stella's (stellaspinball.com) is a token-operated pinball arcade + full bar + Boss Burgers
-- ghost kitchen at 802 9th St, Greeley, CO 80631 that ALSO runs a weekly stand-up comedy
-- series ("Stand-Up Underground", every Thursday at 8pm, in coordination with the adjacent
-- Moxi Theater). Confirmed comedy 2026-06-26 from the live page JSON-LD: e.g. "David Testroet
-- – Underground Comedy Showcase" (2026-06-18), "Max Meisel – Underground Comedy Showcase"
-- (2026-07-16), "John Caparulo" (2026-07-09), "Kim Congdon & Dulce Mac" (2026-07-23).
--
-- Datasource: the venue's OWN comedy page, https://stellaspinball.com/comedy, server-renders
-- one schema.org Event JSON-LD block per upcoming show (name + startDate w/ -06:00 offset +
-- doorTime + location + performer + offers.url Tixr ticket link). Tickets check out on Tixr
-- (tixr.com/e/{id}), but the venue-owned comedy page itself carries the structured Event data,
-- so the generic json_ld scraper reads it with a plain static fetch — no Tixr detail-page
-- enrichment (which DataDome-blocks) and no new code. The Event blocks have no top-level "url";
-- JsonLdEvent._validate_required_fields falls back to offers.url (the Tixr link), so they parse.
--
-- This page is the venue's COMEDY-ONLY stage page, so NO comedy_filter is needed (the
-- mixed-use concert/trivia/car-show listings live on the separate Bandwagon Presents venue
-- page, which is intentionally NOT the source_url here).
--
-- Fixed venue (the club is its own room) -> visible=TRUE.
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.
-- Verified 2026-06-26: make scrape-club-id ID=11312 -> "Scraped 10 shows".

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, latitude, longitude, visible, status
)
SELECT
    'Stella''s Pinball Arcade & Lounge', '802 9th St, Greeley, CO 80631, USA',
    'https://www.stellaspinball.com/',
    'Greeley', 'CO', '80631', 'America/Denver', 'US', 'club',
    'ChIJzYeCsz6jbocRa3lHBw4wyMQ', 40.4205, -104.7085, TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJzYeCsz6jbocRa3lHBw4wyMQ'
       OR name = 'Stella''s Pinball Arcade & Lounge'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://stellaspinball.com/comedy',
    TRUE,
    0,
    '{
        "onboarded_via": "TASK-3426: Stella''s Pinball Arcade & Lounge (Greeley, CO) is a pinball arcade + bar running a weekly Thursday stand-up series. Its own /comedy page server-renders schema.org Event JSON-LD per show (offers.url = Tixr ticket link); the generic json_ld scraper reads it statically. Comedy-only page, so no comedy_filter. Verified 2026-06-26: 10 shows."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJzYeCsz6jbocRa3lHBw4wyMQ' OR c.name = 'Stella''s Pinball Arcade & Lounge')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
