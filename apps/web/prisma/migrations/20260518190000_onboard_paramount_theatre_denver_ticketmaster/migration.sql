-- Onboard Paramount Theatre (club 2576) from temporary tour_dates discovery
-- to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Bobby Lee tour-page evidence:
--   https://link.seated.com/fbeb56a6-21a6-43dc-b92a-3751bfacae53
--
-- Verification on 2026-05-18:
--   * No existing active canonical duplicate found by Paramount name,
--     Denver location, official website domain, or Ticketmaster source URL.
--   * https://www.paramountdenver.com is the official venue site; its Box
--     Office page says tickets are sold through ParamountDenver.com or
--     Ticketmaster.com.
--   * Ticketmaster public venue page is
--     https://www.ticketmaster.com/paramount-theatre-tickets-denver/venue/245776.
--   * Ticketmaster Discovery venue search returns KovZpZAFa1nA for Paramount
--     Theatre, 1621 Glenarm, Denver, CO.
--   * Discovery API returned 84 upcoming venue events and 33 comedy-classified
--     events.
--   * Read-only FocusedTicketmasterComedyScraper run with
--     ticketmaster_id=KovZpZAFa1nA produced 22 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2576
          AND c.name = 'Paramount Theatre'
          AND c.city = 'Denver'
          AND c.state = 'CO'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
          AND ss.id = 1584
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Paramount Theatre club 2576: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2576
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2576
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2576
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2576
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2576
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Paramount Theatre club 2576: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAFa1nA'
          AND club_id <> 2576
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Paramount Theatre: Ticketmaster venue KovZpZAFa1nA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '1621 Glenarm Pl',
    website = 'https://www.paramountdenver.com',
    zip_code = '80202',
    country = 'US',
    timezone = 'America/Denver'
WHERE id = 2576
  AND name = 'Paramount Theatre'
  AND city = 'Denver'
  AND state = 'CO'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpZAFa1nA',
            'rationale', 'Temporary tour_dates source replaced after verified focused Ticketmaster comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1584
  AND club_id = 2576
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
    2576,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpZAFa1nA',
    'https://www.ticketmaster.com/paramount-theatre-tickets-denver/venue/245776',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-18',
            'official_site', 'https://www.paramountdenver.com',
            'official_calendar_url', 'https://www.paramountdenver.com/event-calendar/',
            'ticketmaster_venue_id', 'KovZpZAFa1nA',
            'ticketmaster_public_venue_id', '245776',
            'sample_event_detail', 'https://www.ticketmaster.com/bobby-lee-the-finally-tour-2026-denver-colorado-09-19-2026/event/1E00646599CC878D',
            'verification', 'Ticketmaster Discovery API returned 84 total venue events and 33 comedy-classified events; existing ticketmaster_comedy scraper transformed 22 comedy shows.'
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
                2576,
                'Paramount Theatre',
                'paramount theatre',
                'Denver',
                'CO',
                'denver',
                'co',
                '20260518190000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2576,
                'Paramount Theater',
                'paramount theater',
                'Denver',
                'CO',
                'denver',
                'co',
                '20260518190000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2576,
                'Paramount Theatre Denver',
                'paramount theatre denver',
                'Denver',
                'CO',
                'denver',
                'co',
                '20260518190000: Ticketmaster venue onboarding',
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
