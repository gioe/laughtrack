-- Onboard New Jersey Performing Arts Center - Prudential Hall (club 2489)
-- from temporary tour_dates discovery to the existing generic Ticketmaster
-- scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-newark-new-jersey-performing-arts-center---prudential-hall-9-24-2026/production/7024320
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by NJPAC/Prudential Hall name or
--     source/domain in Newark, NJ.
--   * Official site https://www.njpac.org/tickets-events/ lists comedy events
--     including Nurse John: Against Medical Advice Tour on September 24, 2026.
--   * Official address is 1 Center Street, Newark, NJ 07102.
--   * Ticketmaster Discovery venue search returns KovZpa6Vxe for New Jersey
--     Performing Arts Center, Newark, NJ.
--   * Ticketmaster events API returned 76 upcoming venue events, including
--     comedy events for Russell Peters, Dan Soder, Marc Maron, Nurse John,
--     Jamie Lissow, Mario Adrion, and Jon Bramnick.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpa6Vxe
--     produced 23 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2489
          AND c.name = 'New Jersey Performing Arts Center - Prudential Hall'
          AND c.city = 'Newark'
          AND c.state = 'NJ'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard NJPAC: expected active tour_dates stub club 2489 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpa6Vxe'
          AND club_id <> 2489
    ) THEN
        RAISE EXCEPTION 'Cannot onboard NJPAC: Ticketmaster venue KovZpa6Vxe is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.njpac.org',
    address = '1 Center Street',
    zip_code = '07102',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2489
  AND name = 'New Jersey Performing Arts Center - Prudential Hall'
  AND city = 'Newark'
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
            'replacement_ticketmaster_id', 'KovZpa6Vxe',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2489
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
    2489,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpa6Vxe',
    'https://www.ticketmaster.com/new-jersey-performing-arts-center-tickets-newark/venue/308',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.njpac.org',
            'official_calendar', 'https://www.njpac.org/tickets-events/',
            'ticketmaster_venue_id', 'KovZpa6Vxe',
            'ticketmaster_public_venue_id', '308',
            'sample_event_detail', 'https://www.livenation.com/event/k7vGF_1rqZHbv/nurse-john-against-medical-advice-tour',
            'verification', 'Ticketmaster Discovery API returned 76 total venue events; existing live_nation scraper transformed 23 comedy shows.'
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
                2489,
                'NJPAC',
                'njpac',
                'Newark',
                'NJ',
                'newark',
                'nj',
                '20260515141000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2489,
                'New Jersey Performing Arts Center',
                'new jersey performing arts center',
                'Newark',
                'NJ',
                'newark',
                'nj',
                '20260515141000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2489,
                'Prudential Hall at New Jersey Performing Arts Center',
                'prudential hall at new jersey performing arts center',
                'Newark',
                'NJ',
                'newark',
                'nj',
                '20260515141000: Ticketmaster venue onboarding',
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
