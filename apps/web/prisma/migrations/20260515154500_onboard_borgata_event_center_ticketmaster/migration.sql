-- Onboard Borgata Casino Event Center (club 2501) from temporary
-- tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-atlantic-city-borgata-casino-event-center-9-18-2026/production/7024354
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by Borgata Event Center name,
--     Ticketmaster public venue URL, or Ticketmaster Discovery venue ID.
--   * Borgata's official Event Center page confirms the venue address and
--     names Ticketmaster as a sanctioned ticketing source.
--   * Ticketmaster venue search returns KovZpapVCe for Borgata Event Center,
--     Atlantic City, NJ.
--   * Ticketmaster events API returned 20 upcoming venue events, including
--     Nurse John: Against Medical Advice Tour on September 18, 2026.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpapVCe
--     produced 6 transformed comedy shows, including the source Nurse John
--     event.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2501
          AND c.name = 'Borgata Casino Event Center'
          AND c.city = 'Atlantic City'
          AND c.state = 'NJ'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Borgata Casino Event Center: expected active tour_dates stub club 2501 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpapVCe'
          AND club_id <> 2501
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Borgata Casino Event Center: Ticketmaster venue KovZpapVCe is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://borgata.mgmresorts.com',
    address = 'One Borgata Way',
    zip_code = '08401',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2501
  AND name = 'Borgata Casino Event Center'
  AND city = 'Atlantic City'
  AND state = 'NJ'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpapVCe',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2501
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
    2501,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpapVCe',
    'https://www.ticketmaster.com/borgata-event-center-tickets-atlantic-city/venue/16907',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://borgata.mgmresorts.com',
            'official_calendar', 'https://borgata.mgmresorts.com/shows/venues/event-center',
            'ticketmaster_venue_id', 'KovZpapVCe',
            'ticketmaster_public_venue_id', '16907',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-atlantic-city-new-jersey-09-18-2026/event/020064A7BCFD07FA',
            'verification', 'Ticketmaster Discovery API returned 20 total venue events; existing live_nation scraper transformed 6 comedy shows.'
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

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
        INSERT INTO club_aliases (
            club_id,
            alias_name,
            normalized_alias_name,
            city,
            state,
            normalized_city,
            normalized_state,
            source,
            verified
        )
        VALUES
            (
                2501,
                'Borgata Event Center',
                'borgata event center',
                'Atlantic City',
                'NJ',
                'atlantic city',
                'nj',
                '20260515154500: Ticketmaster venue onboarding',
                TRUE
            )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
        DO UPDATE SET
            club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW();
    END IF;
END $$;
