-- Onboard medium-likelihood comedy venues discovered via discover-comedy-venues
-- near ZIP 02101 - TASK-3152 (batch 3 of 45, venues 21-30).
--
-- Of venues 21-30, 1 qualifies; 9 dropped (see task notes):
--   - The Star Theatre (Kittery KCC): comedy is an external roving producer
--     (Scamps Comedy), 1 upcoming event org-wide — no venue-run series.
--   - The Strand Dover: wix_events-capable but 0 upcoming comedy (recheck later).
--   - Loft Nightclub (Oak Bluffs): closed/rebranded (Inkwell Beach Club), 0 comedy.
--   - Rochester Opera House: sporadic touring comedy + TicketSearch (no scraper).
--   - The Drake (Amherst): 1 comedy among ~50 music shows.
--   - The Parlor Room (Northampton): 0 comedy (songwriter room), Salesforce ticketing.
--   - Unicorn Holyoke: open-mic only, no events/calendar page on own site.
--   - Hawks and Reed (Greenfield): comedy series dead (last show 2024), 0 upcoming.
--   - Broad Brook Opera House: 0 upcoming comedy (thundertix music-only; recheck later).
--
-- 21. Academy of Music (Northampton) (274 Main Street, Northampton, MA 01060) —
--     historic theater that books A-list touring stand-up (Ilana Glazer, David
--     Cross, Gary Gulman, Paula Poundstone, Jordan Jensen, Ira Glass) among mostly
--     music/theater. Its calendar lives in the WordPress REST `aom_event` custom
--     post type with no schema.org Event JSON-LD, so a new venue-specific scraper
--     (scraper_key 'academy_of_music') was added in this task's scraper commit. The
--     source opts into comedy isolation via metadata.comedy_filter. Verified
--     2026-06-22: a real scrape kept 9/86 events (comedy) for the venue.

-- ---- Academy of Music (Northampton) (academy_of_music, comedy_filter) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Academy of Music (Northampton)', '274 Main Street', 'http://www.aomtheatre.com/',
    'Northampton', 'MA', '01060', 'America/New_York', 'US', 'club',
    'ChIJj1l-8UPX5okRPlMOkNK13qM', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJj1l-8UPX5okRPlMOkNK13qM'
       OR name = 'Academy of Music (Northampton)'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'academy_of_music',
    'https://aomtheatre.com/wp-json/wp/v2/aom_event?per_page=100',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJj1l-8UPX5okRPlMOkNK13qM' OR c.name = 'Academy of Music (Northampton)')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'academy_of_music'
  );
