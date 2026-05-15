-- Onboard Stifel Theatre - St. Louis (club 2509) from temporary tour_dates
-- discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-st-louis-stifel-theatre---st-louis-10-16-2026/production/7024404
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by Stifel Theatre name/domain in
--     St. Louis, MO, or by Ticketmaster Discovery venue ID.
--   * Official Stifel Theatre site lists the venue at 1400 Market Street,
--     St. Louis, MO 63103, and exposes the events calendar at
--     https://www.stifeltheatre.com/tickets/events.
--   * Ticketmaster venue search returns KovZpa3die for Stifel Theatre,
--     Saint Louis, MO, with public venue page 50474.
--   * Ticketmaster events API returned 14 upcoming venue events, including
--     Ali Wong, Nurse John, Leanne Morgan, and Je'Caryous Johnson comedy-
--     classified events.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpa3die
--     produced 3 transformed comedy shows: Ali Wong, Nurse John, and
--     Leanne Morgan.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2509
          AND c.name = 'Stifel Theatre - St. Louis'
          AND c.city = 'St. Louis'
          AND c.state = 'MO'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Stifel Theatre: expected active tour_dates stub club 2509 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpa3die'
          AND club_id <> 2509
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Stifel Theatre: Ticketmaster venue KovZpa3die is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.stifeltheatre.com',
    address = '1400 Market Street',
    zip_code = '63103',
    country = 'US',
    timezone = 'America/Chicago'
WHERE id = 2509
  AND name = 'Stifel Theatre - St. Louis'
  AND city = 'St. Louis'
  AND state = 'MO'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpa3die',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2509
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
    2509,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpa3die',
    'https://www.ticketmaster.com/stifel-theatre-tickets-saint-louis/venue/50474',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.stifeltheatre.com',
            'official_calendar', 'https://www.stifeltheatre.com/tickets/events',
            'ticketmaster_venue_id', 'KovZpa3die',
            'ticketmaster_public_venue_id', '50474',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-saint-louis-missouri-10-16-2026/event/060064A4D79750BB',
            'verification', 'Ticketmaster Discovery API returned 14 total venue events; existing live_nation scraper transformed 3 comedy shows.'
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
        VALUES (
            2509,
            'Stifel Theatre - St. Louis',
            'stifel theatre st louis',
            'St. Louis',
            'MO',
            'st louis',
            'mo',
            '20260515170000_onboard_stifel_theatre_ticketmaster',
            TRUE
        )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO UPDATE
        SET club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW();
    END IF;
END $$;
