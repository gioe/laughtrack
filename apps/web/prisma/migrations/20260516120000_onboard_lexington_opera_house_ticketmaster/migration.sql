-- Onboard Lexington Opera House (club 2570) from temporary tour_dates
-- discovery to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Leslie Jones tour-page evidence:
--   https://concerts50.com/buy/leslie-jones-in-lexington-tickets-sep-11-2026
--
-- Verification on 2026-05-16:
--   * No existing active canonical duplicate found by Lexington Opera House
--     name, official website domain, or Ticketmaster Discovery venue id.
--   * https://www.centralbankcenter.com/events/detail/leslie-jones-im-hot-tour/
--     is the official event page; it lists Lexington Opera House as the venue
--     and links Buy Tickets to ticketmaster.com.
--   * Ticketmaster Discovery venue search returns KovZpZAFkFtA / public
--     venue 180455 for Lexington Opera House, Lexington, KY.
--   * Discovery API returned 50 upcoming venue events and 6 Comedy-classified
--     events.
--   * Read-only FocusedTicketmasterComedyScraper run with ticketmaster_id
--     KovZpZAFkFtA produced 6 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2570
          AND c.name = 'Lexington Opera House'
          AND c.city = 'Lexington'
          AND c.state = 'KY'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1578
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Lexington Opera House club 2570: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2570
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2570
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2570
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2570
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2570
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Lexington Opera House club 2570: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAFkFtA'
          AND club_id <> 2570
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Lexington Opera House: Ticketmaster venue KovZpZAFkFtA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '401 W Short St',
    website = 'https://www.centralbankcenter.com/lexington-opera-house/',
    zip_code = '40507',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2570
  AND name = 'Lexington Opera House'
  AND city = 'Lexington'
  AND state = 'KY'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpZAFkFtA',
            'rationale', 'Temporary tour_dates source replaced after verified ticketmaster_comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1578
  AND club_id = 2570
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
    2570,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpZAFkFtA',
    'https://www.ticketmaster.com/lexington-opera-house-tickets-lexington/venue/180455',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-16',
            'official_site', 'https://www.centralbankcenter.com/lexington-opera-house/',
            'official_calendar_url', 'https://www.centralbankcenter.com/events/venue/lexington-opera-house',
            'ticketmaster_venue_id', 'KovZpZAFkFtA',
            'ticketmaster_public_venue_id', '180455',
            'sample_event_detail', 'https://www.ticketmaster.com/leslie-jones-im-hot-tour-lexington-kentucky-09-11-2026/event/16006487DD6DB111',
            'verification', 'Ticketmaster Discovery API returned 50 total venue events and 6 Comedy-classified events; existing ticketmaster_comedy scraper transformed 6 comedy shows.'
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
                2570,
                'Lexington Opera House',
                'lexington opera house',
                'Lexington',
                'KY',
                'lexington',
                'ky',
                '20260516120000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2570,
                'The Lexington Opera House',
                'the lexington opera house',
                'Lexington',
                'KY',
                'lexington',
                'ky',
                '20260516120000: Ticketmaster venue onboarding',
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
