-- Onboard Soboba Casino Resort (club 2413) from temporary tour_dates discovery
-- to a venue-specific scraper for the official entertainment calendar.
--
-- Verification on 2026-05-13:
--   Official site: https://soboba.com
--   Calendar: https://soboba.com/entertainment/calendar
--   The scraper Playwright stack fetched the calendar successfully and found
--   future comedy events including D.L. Hughley, Frankie Quiñones, and Steve
--   Treviño. Event detail pages link to Yapsody purchase URLs such as:
--     https://sobobacasino.yapsody.com/event/index/868865/dl-hughley
--
-- Keep the existing tour_dates source enabled as a fallback, but demote it so
-- the verified venue-owned calendar scraper is tried first.

UPDATE clubs
SET
    website = 'https://soboba.com',
    address = '22777 Soboba Rd',
    city = 'San Jacinto',
    state = 'CA',
    zip_code = '92583',
    country = 'US',
    timezone = 'America/Los_Angeles',
    updated_at = NOW()
WHERE id = 2413
  AND name = 'SCR Event Center at Soboba Casino Resort - Complex';

UPDATE scraping_sources
SET
    priority = 1,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_demoted', jsonb_build_object(
            'verified_at', '2026-05-13',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'soboba_casino_resort',
            'rationale', 'Venue-owned Soboba calendar scraper added; tour_dates kept enabled as fallback until production scrape history confirms replacement output.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2413
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2413,
    'custom'::"ScrapingPlatform",
    'soboba_casino_resort',
    'https://soboba.com/entertainment/calendar',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-13',
            'official_site', 'https://soboba.com',
            'ticketing_platform', 'yapsody',
            'sample_ticket_urls', jsonb_build_array(
                'https://sobobacasino.yapsody.com/event/index/868865/dl-hughley',
                'https://sobobacasino.yapsody.com/event/index/865983/frankie-quinones',
                'https://sobobacasino.yapsody.com/event/index/865291/steve-trevino'
            ),
            'verification', 'Scraper Playwright stack fetched the Soboba calendar and detail pages; listing cards provide dates/times/rooms and detail pages provide Yapsody ticket links.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
