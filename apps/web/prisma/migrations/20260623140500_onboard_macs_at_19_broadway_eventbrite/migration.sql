-- Onboard Mac's at 19 Broadway (Fairfax, CA) via Eventbrite venue mode - TASK-3188.
--
-- The venue's own WordPress site describes Mac's as Fairfax's comedy/nightlife
-- venue and links comedy/ticket CTAs to Eventbrite organizer 68173536473. A live
-- scraper check on 2026-06-23 found Eventbrite venue 295371315 with 25 live
-- events; the Eventbrite category/DJ filters transformed those into 14 comedy
-- shows (category 105 / subcategory 5010), including 90 Seconds Comedy Time
-- Bomb, Naked Cat Comedy, Comedy Confessions After Dark, DJ Sandhu, and Girls
-- Night Laugh Out Loud. Venue mode keeps the source pinned to the physical venue
-- and avoids organizer fan-out while still letting the existing Eventbrite
-- filters drop music/DJ listings from the mixed-use calendar.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Mac''s at 19 Broadway',
    '19 Broadway',
    'https://www.macsat19broadway.com/',
    'Fairfax',
    'CA',
    '94930',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJ44vR_FWWhYARNIvh6gYMTUY',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ44vR_FWWhYARNIvh6gYMTUY'
       OR name = 'Mac''s at 19 Broadway'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '295371315',
    TRUE,
    0,
    jsonb_build_object(
        'organizer_id', '68173536473',
        'eventbrite_venue_id', '295371315',
        'onboarded_via', 'TASK-3188',
        'rationale', 'Single-venue Eventbrite mode pins the mixed-use Mac''s at 19 Broadway feed to the physical venue; Eventbrite category/DJ filters drop non-comedy music listings.'
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ44vR_FWWhYARNIvh6gYMTUY' OR c.name = 'Mac''s at 19 Broadway')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );
