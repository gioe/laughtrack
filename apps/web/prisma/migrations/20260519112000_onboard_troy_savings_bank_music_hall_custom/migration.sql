-- Onboard Troy Savings Bank Music Hall (club 2579) from temporary tour_dates
-- discovery to the venue's official server-rendered comedy events page.
--
-- Verification on 2026-05-19:
--   Official site: https://www.troymusichall.org/
--   Comedy listing: https://www.troymusichall.org/events/?searchType=7
--   The scraper HTTP stack fetched the page and found five comedy events:
--   Late Nite Catechism, ILANA GLAZER LIVE!, Please Don't Destroy: LIVE,
--   Leslie Jones: I'm Hot Tour, and Whose Live Anyway?.
--
-- Keep the existing tour_dates source enabled as a fallback until the official
-- source has successful persisted scrape history.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2579
          AND name = 'Troy Savings Bank Music Hall'
          AND city = 'Troy'
          AND state = 'NY'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Troy Savings Bank Music Hall: club 2579 is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE club_id = 2579
          AND platform = 'tour_dates'::"ScrapingPlatform"
          AND scraper_key = 'tour_dates'
          AND enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Troy Savings Bank Music Hall: expected enabled tour_dates source is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.troymusichall.org/',
    address = '30 Second Street',
    zip_code = '12180',
    timezone = 'America/New_York'
WHERE id = 2579
  AND name = 'Troy Savings Bank Music Hall'
  AND city = 'Troy'
  AND state = 'NY';

UPDATE scraping_sources
SET priority = 1,
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_dates_preserved_as_fallback', TRUE,
        'fallback_after_source', 'custom',
        'onboarded_platform', 'custom',
        'onboarded_scraper_key', 'troy_savings_bank_music_hall',
        'verified_at', '2026-05-19',
        'rationale', 'Venue-owned Troy Savings Bank Music Hall comedy listing scraper added; tour_dates kept enabled as fallback until production scrape history confirms replacement output.'
    ),
    updated_at = NOW()
WHERE club_id = 2579
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND priority = 0;

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2579,
    'custom'::"ScrapingPlatform",
    'troy_savings_bank_music_hall',
    'https://www.troymusichall.org/events/?searchType=7',
    TRUE,
    0,
    jsonb_build_object(
        'official_site', 'https://www.troymusichall.org/',
        'official_events_url', 'https://www.troymusichall.org/events/?searchType=7',
        'ticketing_platform', 'cart.troymusichall.org',
        'verified_at', '2026-05-19',
        'verified_event_count', 5,
        'verified_sample_event', 'Leslie Jones: I''m Hot Tour',
        'verified_sample_event_date', '2026-10-10',
        'verified_sample_ticket_url', 'https://cart.troymusichall.org/33985/leslie-jones-im-hot-tour',
        'verification', 'Scraper HTTP stack fetched the official server-rendered comedy list; cards provide title, local date/time, detail URL, and cart ticket URL.'
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
