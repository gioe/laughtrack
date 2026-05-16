-- Onboard Andrew J Brady Music Center (club 2512) from temporary
-- tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-cincinnati-andrew-j-brady-music-center-10-24-2026--theater-comedy/production/7024686
--
-- Verification on 2026-05-15:
--   * No existing active canonical duplicate found by Brady name/domain, or
--     by Ticketmaster Discovery venue ID.
--   * https://bradymusiccenter.com is the official site and lists the venue
--     address as 25 Race Street, Cincinnati, OH 45202.
--   * The official box office page names Ticketmaster.com and the venue box
--     office as the only authorized ticket sellers.
--   * Ticketmaster Discovery venue search returns KovZ917APg3 / public venue
--     181165 for The Andrew J Brady Music Center, Cincinnati, OH.
--   * Discovery API returned 22 upcoming venue events, including Nurse John:
--     Against Medical Advice Tour on October 24, 2026.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZ917APg3
--     produced 1 transformed comedy show: Nurse John.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2512
          AND c.name = 'Andrew J Brady Music Center'
          AND c.city = 'Cincinnati'
          AND c.state = 'OH'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1520
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Andrew J Brady Music Center club 2512: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2512
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2512
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2512
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2512
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2512
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Andrew J Brady Music Center club 2512: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZ917APg3'
          AND club_id <> 2512
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Andrew J Brady Music Center: Ticketmaster venue KovZ917APg3 is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    name = 'The Andrew J Brady Music Center',
    address = '25 Race Street',
    website = 'https://bradymusiccenter.com',
    zip_code = '45202',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2512
  AND name = 'Andrew J Brady Music Center'
  AND city = 'Cincinnati'
  AND state = 'OH'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZ917APg3',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1520
  AND club_id = 2512
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
    2512,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZ917APg3',
    'https://www.ticketmaster.com/the-andrew-j-brady-music-center-tickets-cincinnati/venue/181165',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://bradymusiccenter.com',
            'official_calendar_url', 'https://bradymusiccenter.com',
            'ticket_information_url', 'https://bradymusiccenter.com/venue-info/box-office',
            'ticketmaster_venue_id', 'KovZ917APg3',
            'ticketmaster_public_venue_id', '181165',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-cincinnati-ohio-10-24-2026/event/160064A4A4C47C56',
            'verification', 'Ticketmaster Discovery API returned 22 total venue events; existing live_nation scraper transformed 1 comedy show.'
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
                2512,
                'Andrew J Brady Music Center',
                'andrew j brady music center',
                'Cincinnati',
                'OH',
                'cincinnati',
                'oh',
                '20260515213000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2512,
                'The Andrew J Brady Music Center',
                'the andrew j brady music center',
                'Cincinnati',
                'OH',
                'cincinnati',
                'oh',
                '20260515213000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2512,
                'Brady Music Center',
                'brady music center',
                'Cincinnati',
                'OH',
                'cincinnati',
                'oh',
                '20260515213000: Ticketmaster venue onboarding',
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
