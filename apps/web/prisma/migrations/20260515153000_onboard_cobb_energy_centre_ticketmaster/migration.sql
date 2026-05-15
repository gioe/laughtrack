-- Onboard Cobb Energy Performing Arts Centre (club 2500) from temporary
-- tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Gary Owen tour-page evidence:
--   https://link.seated.com/9dcc9b9b-45d7-42fe-92a8-e33ecefdc1a5
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by Cobb Energy name, domain,
--     public Ticketmaster venue URL, or Ticketmaster Discovery venue ID.
--   * Official Cobb Energy Centre events page lists upcoming venue events and
--     uses ticketmaster.com buy links.
--   * Ticketmaster venue page lists 57 upcoming events, including Gary Owen on
--     September 26, 2026.
--   * Ticketmaster Discovery venue search returns KovZpa3j7e for Cobb Energy
--     Performing Arts Centre, Atlanta, GA.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpa3j7e
--     produced 18 transformed shows, including the source Gary Owen event.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2500
          AND c.name = 'Cobb Energy Performing Arts Centre'
          AND c.city = 'Atlanta'
          AND c.state = 'GA'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Cobb Energy Performing Arts Centre: expected active tour_dates stub club 2500 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpa3j7e'
          AND club_id <> 2500
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Cobb Energy Performing Arts Centre: Ticketmaster venue KovZpa3j7e is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.cobbenergycentre.com',
    address = '2800 Cobb Galleria Parkway',
    zip_code = '30339',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2500
  AND name = 'Cobb Energy Performing Arts Centre'
  AND city = 'Atlanta'
  AND state = 'GA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpa3j7e',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2500
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
    2500,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpa3j7e',
    'https://www.ticketmaster.com/cobb-energy-performing-arts-centre-tickets-atlanta/venue/115457',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.cobbenergycentre.com',
            'official_calendar', 'https://www.cobbenergycentre.com/events-tickets/events',
            'ticketmaster_venue_id', 'KovZpa3j7e',
            'ticketmaster_public_venue_id', '115457',
            'sample_event_detail', 'https://www.ticketmaster.com/gary-owen-no-hard-feelings-tour-atlanta-georgia-09-26-2026/event/0E006481E223FC96',
            'verification', 'Ticketmaster Discovery API returned 57 total venue events; existing live_nation scraper transformed 18 shows.'
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
