-- Onboard Citizens Live at The Wylie (club 2513) from temporary
-- tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-pittsburgh-citizens-live-at-the-wylie-11-5-2026--theater-comedy/production/7024688
--
-- Verification on 2026-05-16:
--   * No existing active canonical duplicate found by Citizens/Wylie name,
--     official website domain, Ticketmaster source URL, or Ticketmaster
--     Discovery venue id.
--   * https://www.citizensliveatthewylie.com is the official venue site;
--     footer identifies Live Nation ownership and every event Buy Tickets
--     link points to ticketmaster.com.
--   * Ticketmaster Discovery venue search returns KovZ917AYrv / public venue
--     181242 for Citizens Live at The Wylie, Pittsburgh, PA.
--   * Discovery API returned 23 upcoming venue events, including comedy events
--     for Chelsea Handler, Aries Spears, and Nurse John.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZ917AYrv
--     produced 3 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2513
          AND c.name = 'Citizens Live at The Wylie'
          AND c.city = 'Pittsburgh'
          AND c.state = 'PA'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1521
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Citizens Live at The Wylie club 2513: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2513
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2513
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2513
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2513
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2513
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Citizens Live at The Wylie club 2513: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZ917AYrv'
          AND club_id <> 2513
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Citizens Live at The Wylie: Ticketmaster venue KovZ917AYrv is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '1201 Wylie Ave',
    website = 'https://www.citizensliveatthewylie.com',
    zip_code = '15219',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2513
  AND name = 'Citizens Live at The Wylie'
  AND city = 'Pittsburgh'
  AND state = 'PA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZ917AYrv',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1521
  AND club_id = 2513
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
    2513,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZ917AYrv',
    'https://www.ticketmaster.com/citizens-live-at-the-wylie-tickets-pittsburgh/venue/181242',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-16',
            'official_site', 'https://www.citizensliveatthewylie.com',
            'official_calendar_url', 'https://www.citizensliveatthewylie.com',
            'ticketmaster_venue_id', 'KovZ917AYrv',
            'ticketmaster_public_venue_id', '181242',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-pittsburgh-pennsylvania-11-05-2026/event/160064ABAB998AD2',
            'verification', 'Ticketmaster Discovery API returned 23 total venue events; existing live_nation scraper transformed 3 comedy shows.'
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
                2513,
                'Citizens Live at The Wylie',
                'citizens live at the wylie',
                'Pittsburgh',
                'PA',
                'pittsburgh',
                'pa',
                '20260516090000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2513,
                'The Wylie',
                'the wylie',
                'Pittsburgh',
                'PA',
                'pittsburgh',
                'pa',
                '20260516090000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2513,
                'Citizens Live at Wylie',
                'citizens live at wylie',
                'Pittsburgh',
                'PA',
                'pittsburgh',
                'pa',
                '20260516090000: Ticketmaster venue onboarding',
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
