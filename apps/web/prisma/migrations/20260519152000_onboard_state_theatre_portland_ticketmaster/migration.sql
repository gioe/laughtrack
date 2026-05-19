-- Onboard State Theatre (club 2581) from temporary tour_dates discovery
-- to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Leslie Jones tour-page evidence:
--   https://concerts50.com/buy/leslie-jones-in-portland-tickets-nov-06-2026
--
-- Verification on 2026-05-19:
--   * No existing active canonical duplicate found by State Theatre name,
--     Portland location, official website domain, or Ticketmaster source URL.
--   * https://statetheatreportland.com is the official venue site; its event
--     listing links ticket actions to ticketmaster.com.
--   * Official contact page lists State Theatre at 609 Congress Street,
--     Portland, ME 04101.
--   * Ticketmaster public venue page is
--     https://www.ticketmaster.com/state-theatre-tickets-portland/venue/8505.
--   * Ticketmaster Discovery venue search returns KovZpa3mee for State
--     Theatre, Portland, ME.
--   * Discovery API returned 51 upcoming venue events and 12 comedy-classified
--     events.
--   * Read-only FocusedTicketmasterComedyScraper run with
--     ticketmaster_id=KovZpa3mee produced 11 transformed comedy shows,
--     including Leslie Jones on 2026-11-06.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2581
          AND c.name = 'State Theatre'
          AND c.city = 'Portland'
          AND c.state = 'ME'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
          AND ss.id = 1589
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard State Theatre club 2581: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2581
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2581
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2581
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2581
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2581
    ) THEN
        RAISE EXCEPTION 'Cannot onboard State Theatre club 2581: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpa3mee'
          AND club_id <> 2581
    ) THEN
        RAISE EXCEPTION 'Cannot onboard State Theatre: Ticketmaster venue KovZpa3mee is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '609 Congress Street',
    website = 'https://statetheatreportland.com',
    zip_code = '04101',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2581
  AND name = 'State Theatre'
  AND city = 'Portland'
  AND state = 'ME'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-19',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpa3mee',
            'rationale', 'Temporary tour_dates source replaced after verified focused Ticketmaster comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1589
  AND club_id = 2581
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;

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
    2581,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpa3mee',
    'https://www.ticketmaster.com/state-theatre-tickets-portland/venue/8505',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-19',
            'official_site', 'https://statetheatreportland.com',
            'official_calendar_url', 'https://statetheatreportland.com/events/',
            'ticketmaster_venue_id', 'KovZpa3mee',
            'ticketmaster_public_venue_id', '8505',
            'sample_event_detail', 'https://www.ticketmaster.com/leslie-jones-im-hot-tour-portland-maine-11-06-2026/event/01006486DE8A31C5',
            'verification', 'Ticketmaster Discovery API returned 51 total venue events and 12 comedy-classified events; existing ticketmaster_comedy scraper transformed 11 comedy shows.'
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
                2581,
                'State Theatre',
                'state theatre',
                'Portland',
                'ME',
                'portland',
                'me',
                '20260519152000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2581,
                'State Theatre Portland',
                'state theatre portland',
                'Portland',
                'ME',
                'portland',
                'me',
                '20260519152000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2581,
                'State Theatre Portland Maine',
                'state theatre portland maine',
                'Portland',
                'ME',
                'portland',
                'me',
                '20260519152000: Ticketmaster venue onboarding',
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
