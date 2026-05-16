-- Onboard The Blue Note - MO (club 2538) from temporary tour_dates
-- discovery to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Shuler King tour-page evidence:
--   https://www.vividseats.com/shuler-king-tickets-columbia-the-blue-note---mo-10-9-2026/production/6774054
--
-- Verification on 2026-05-16:
--   * No existing active canonical duplicate found by Blue Note name, official
--     website domain, Ticketmaster source URL, or Ticketmaster Discovery venue id.
--   * https://thebluenote.com is the official venue site; rendered event cards
--     link Buy Tickets actions to ticketmaster.com.
--   * Ticketmaster Discovery venue search returns KovZpZAantEA / public venue
--     49791 for The Blue Note, Columbia, MO.
--   * Discovery API returned 38 upcoming venue events and 9 Comedy-classified
--     events including Ryan Niemiller, Shuler King, Chris Porter, and Drew Lynch.
--   * Read-only FocusedTicketmasterComedyScraper run with ticketmaster_id
--     KovZpZAantEA produced 7 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2538
          AND c.name = 'The Blue Note - MO'
          AND c.city = 'Columbia'
          AND c.state = 'MO'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1546
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard The Blue Note - MO club 2538: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2538
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2538
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2538
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2538
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2538
    ) THEN
        RAISE EXCEPTION 'Cannot onboard The Blue Note - MO club 2538: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAantEA'
          AND club_id <> 2538
    ) THEN
        RAISE EXCEPTION 'Cannot onboard The Blue Note - MO: Ticketmaster venue KovZpZAantEA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '17 N. 9th Street',
    website = 'https://thebluenote.com',
    zip_code = '65201',
    country = 'US',
    timezone = 'America/Chicago'
WHERE id = 2538
  AND name = 'The Blue Note - MO'
  AND city = 'Columbia'
  AND state = 'MO'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpZAantEA',
            'rationale', 'Temporary tour_dates source replaced after verified ticketmaster_comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1546
  AND club_id = 2538
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
    2538,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpZAantEA',
    'https://www.ticketmaster.com/the-blue-note-tickets-columbia/venue/49791',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-16',
            'official_site', 'https://thebluenote.com',
            'official_calendar_url', 'https://thebluenote.com',
            'ticketmaster_venue_id', 'KovZpZAantEA',
            'ticketmaster_public_venue_id', '49791',
            'sample_event_detail', 'https://www.ticketmaster.com/shuler-king-columbia-missouri-10-09-2026/event/060064699C5897F4',
            'verification', 'Ticketmaster Discovery API returned 38 total venue events and 9 Comedy-classified events; existing ticketmaster_comedy scraper transformed 7 comedy shows.'
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
