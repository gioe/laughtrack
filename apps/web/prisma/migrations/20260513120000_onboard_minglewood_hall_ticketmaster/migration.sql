-- Onboard Minglewood Hall (club 2359) from temporary tour_dates discovery
-- to the existing generic Ticketmaster scraper.
--
-- Verification on 2026-05-13:
--   Official site: https://minglewoodhallmemphis.com/
--   Events page lists "Get Tickets" links to ticketmaster.com.
--   Ticketmaster Discovery venue: KovZpaCWke / venue page 341876.
--   Existing live_nation scraper fetched 15 future events and transformed
--   2 comedy-eligible shows, including Henry Cho: The Empty Nest Tour.

UPDATE clubs
SET
    website = 'https://minglewoodhallmemphis.com/',
    address = '1555 Madison Avenue',
    city = 'Memphis',
    state = 'TN',
    zip_code = '38104',
    country = 'US',
    timezone = 'America/Chicago'
WHERE id = 2359;

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-13',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpaCWke',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy-eligible shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2359
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    ticketmaster_id,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2359,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpaCWke',
    'https://www.ticketmaster.com/minglewood-hall-tickets-memphis/venue/341876',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-13',
            'official_site', 'https://minglewoodhallmemphis.com/',
            'ticketmaster_venue_id', 'KovZpaCWke',
            'ticketmaster_public_venue_id', '341876',
            'verification', 'Ticketmaster Discovery API returned 19 total venue events; existing live_nation scraper fetched 15 future events and transformed 2 comedy-eligible shows.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    ticketmaster_id = EXCLUDED.ticketmaster_id,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
