-- Onboard Ovens Auditorium (club 2499) from temporary tour_dates discovery to
-- the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-charlotte-ovens-auditorium-9-11-2026/production/7024262
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by Ovens/Ovens Auditorium name or
--     boplex/ovensauditorium source/domain in Charlotte, NC.
--   * Official BOplex venue page identifies Ovens Auditorium as an active
--     Charlotte performance venue and links to upcoming events.
--   * The official venue page notes detailed seat selection is available on
--     ticketmaster.com; the Ticketmaster venue page lists 30 upcoming events,
--     including the source Nurse John event on September 11, 2026.
--   * Ticketmaster Discovery venue search returns KovZpZAEkA6A for Ovens
--     Auditorium, Charlotte, NC.
--   * Ticketmaster events API returned 30 upcoming venue events, including
--     comedy-classified events for George Lopez, John Mulaney, Nikki Glaser,
--     Nurse John, and Mojo Brookzz.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAEkA6A
--     produced 8 transformed shows, including the source Nurse John event.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2499
          AND c.name = 'Ovens Auditorium'
          AND c.city = 'Charlotte'
          AND c.state = 'NC'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Ovens Auditorium: expected active tour_dates stub club 2499 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAEkA6A'
          AND club_id <> 2499
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Ovens Auditorium: Ticketmaster venue KovZpZAEkA6A is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.boplex.com/our-venues/ovens-auditorium',
    address = '2700 East Independence Blvd',
    zip_code = '28205',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2499
  AND name = 'Ovens Auditorium'
  AND city = 'Charlotte'
  AND state = 'NC'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAEkA6A',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2499
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
    2499,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAEkA6A',
    'https://www.ticketmaster.com/ovens-auditorium-tickets-charlotte/venue/368656',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.boplex.com/our-venues/ovens-auditorium',
            'official_calendar', 'https://www.boplex.com/events',
            'ticketmaster_venue_id', 'KovZpZAEkA6A',
            'ticketmaster_public_venue_id', '368656',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-charlotte-north-carolina-09-11-2026/event/2D00649ED1BDF990',
            'verification', 'Ticketmaster Discovery API returned 30 total venue events; existing live_nation scraper transformed 8 shows.'
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
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();
