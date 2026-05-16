-- Onboard Hollywood Casino Columbus (club 2561) from temporary
-- tour_dates discovery to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Leslie Jones tour-page evidence:
--   https://concerts50.com/buy/leslie-jones-in-columbus-tickets-jun-18-2026
--
-- Verification on 2026-05-16:
--   * No existing active canonical duplicate found by Hollywood Casino name,
--     official website domain, Ticketmaster source URL, or Ticketmaster
--     Discovery venue id.
--   * https://www.hollywoodcolumbus.com is the official venue site; its
--     entertainment page lists the same upcoming events and Buy Tickets links
--     resolve through ticketmaster.com.
--   * Ticketmaster Discovery venue search returns KovZpZAaJ17A / public venue
--     42054 for The Event Center at Hollywood Casino Columbus, Columbus, OH.
--   * Discovery API returned 10 upcoming venue events and 2 Comedy-classified
--     events: Demetri Martin and Leslie Jones.
--   * Read-only FocusedTicketmasterComedyScraper run with ticketmaster_id
--     KovZpZAaJ17A produced 2 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2561
          AND c.name = 'Hollywood Casino Columbus'
          AND c.city = 'Columbus'
          AND c.state = 'OH'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1569
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hollywood Casino Columbus club 2561: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2561
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2561
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2561
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2561
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2561
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hollywood Casino Columbus club 2561: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAaJ17A'
          AND club_id <> 2561
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hollywood Casino Columbus: Ticketmaster venue KovZpZAaJ17A is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '200 Georgesville Road',
    website = 'https://www.hollywoodcolumbus.com',
    zip_code = '43228',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2561
  AND name = 'Hollywood Casino Columbus'
  AND city = 'Columbus'
  AND state = 'OH'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpZAaJ17A',
            'rationale', 'Temporary tour_dates source replaced after verified ticketmaster_comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1569
  AND club_id = 2561
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
    2561,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpZAaJ17A',
    'https://www.ticketmaster.com/the-event-center-at-hollywood-casino-tickets-columbus/venue/42054',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-16',
            'official_site', 'https://www.hollywoodcolumbus.com',
            'official_calendar_url', 'https://www.hollywoodcolumbus.com/entertainment',
            'ticketmaster_venue_id', 'KovZpZAaJ17A',
            'ticketmaster_public_venue_id', '42054',
            'sample_event_detail', 'https://www.ticketmaster.com/leslie-jones-im-hot-tour-columbus-ohio-06-18-2026/event/05006487AB576F0E',
            'verification', 'Ticketmaster Discovery API returned 10 total venue events and 2 Comedy-classified events; existing ticketmaster_comedy scraper transformed 2 comedy shows.'
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
                2561,
                'Hollywood Casino Columbus',
                'hollywood casino columbus',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260516110000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2561,
                'The Event Center at Hollywood Casino Columbus',
                'the event center at hollywood casino columbus',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260516110000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2561,
                'Event Center at Hollywood Casino',
                'event center at hollywood casino',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260516110000: Ticketmaster venue onboarding',
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
