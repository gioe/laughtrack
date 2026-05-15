-- Onboard North Charleston Performing Arts Center (club 2498) from temporary
-- tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-north-charleston-north-charleston-performing-arts-center-9-10-2026/production/7024264
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by North Charleston Performing Arts
--     Center/PAC name or northcharlestoncoliseumpac.com source/domain in SC.
--   * Official site https://www.northcharlestoncoliseumpac.com/events lists
--     Performing Arts Center events and Ticketmaster buy links, including
--     Morgan Jay on June 20, 2026.
--   * Official ticket information says online tickets are sold at
--     Ticketmaster.com, with some show-specific AXS exceptions.
--   * Ticketmaster Discovery venue search returns KovZpZAEkAnA for North
--     Charleston Performing Arts Center, North Charleston, SC.
--   * Ticketmaster events API returned 11 upcoming venue events, including
--     comedy-classified events for Morgan Jay, Nikki Glaser, Nurse John, and
--     Steve Martin & Martin Short.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAEkAnA
--     produced 4 transformed comedy shows, including the source Nurse John
--     event on September 10, 2026.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2498
          AND c.name = 'North Charleston Performing Arts Center'
          AND c.city = 'North Charleston'
          AND c.state = 'SC'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard North Charleston Performing Arts Center: expected active tour_dates stub club 2498 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAEkAnA'
          AND club_id <> 2498
    ) THEN
        RAISE EXCEPTION 'Cannot onboard North Charleston Performing Arts Center: Ticketmaster venue KovZpZAEkAnA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.northcharlestoncoliseumpac.com',
    address = '5001 Coliseum Drive',
    zip_code = '29418',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2498
  AND name = 'North Charleston Performing Arts Center'
  AND city = 'North Charleston'
  AND state = 'SC'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAEkAnA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2498
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
    2498,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAEkAnA',
    'https://www.ticketmaster.com/north-charleston-performing-arts-center-tickets-north-charleston/venue/369120',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.northcharlestoncoliseumpac.com',
            'official_calendar', 'https://www.northcharlestoncoliseumpac.com/events',
            'ticketmaster_venue_id', 'KovZpZAEkAnA',
            'ticketmaster_public_venue_id', '369120',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-north-charleston-south-carolina-09-10-2026/event/2D0064A6D7D18B84',
            'verification', 'Ticketmaster Discovery API returned 11 total venue events; existing live_nation scraper transformed 4 comedy shows.'
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
                2498,
                'North Charleston PAC',
                'north charleston pac',
                'North Charleston',
                'SC',
                'north charleston',
                'sc',
                '20260515143000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2498,
                'NCPAC',
                'ncpac',
                'North Charleston',
                'SC',
                'north charleston',
                'sc',
                '20260515143000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2498,
                'North Charleston Coliseum & Performing Arts Center',
                'north charleston coliseum performing arts center',
                'North Charleston',
                'SC',
                'north charleston',
                'sc',
                '20260515143000: Ticketmaster venue onboarding',
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
