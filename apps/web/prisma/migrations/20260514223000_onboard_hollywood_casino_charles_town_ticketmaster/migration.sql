-- Onboard Hollywood Casino at Charles Town Races (club 2430) from
-- temporary tour_dates discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Gary Owen tour-page evidence:
--   https://link.seated.com/c59cefd2-ba8e-4220-af37-1e70dd5d9dd9
--
-- Verification on 2026-05-14:
--   * No existing canonical source found for Ticketmaster venue KovZpZAJ6knA
--     or public venue 172587.
--   * Official page https://www.hollywoodcasinocharlestown.com/entertainment
--     lists upcoming shows with ticketmaster.com buy links and says online
--     tickets are sold via Ticketmaster.
--   * Ticketmaster Discovery venue search returns KovZpZAJ6knA for
--     Hollywood Casino at Charles Town Races, Charles Town, WV.
--   * Ticketmaster events API returned 34 upcoming events, including comedy
--     events for Killers of Kill Tony, Dusty Slay, Ben Bankas, DL Hughley,
--     Margaret Cho, Brad Williams, Leslie Jones, and Kathleen Madigan.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAJ6knA
--     produced 10 transformed shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2430
          AND c.name = 'Hollywood Casino at Charles Town Races'
          AND c.city = 'Charles Town'
          AND c.state = 'WV'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hollywood Casino at Charles Town Races: expected active tour_dates stub club 2430 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAJ6knA'
          AND club_id <> 2430
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hollywood Casino at Charles Town Races: Ticketmaster venue KovZpZAJ6knA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.hollywoodcasinocharlestown.com',
    address = '750 Hollywood Drive',
    zip_code = '25414',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2430
  AND name = 'Hollywood Casino at Charles Town Races'
  AND city = 'Charles Town'
  AND state = 'WV'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-14',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAJ6knA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy-eligible shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2430
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
    2430,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAJ6knA',
    'https://www.ticketmaster.com/hollywood-casino-at-charles-town-races-tickets-charles-town/venue/172587',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-14',
            'official_site', 'https://www.hollywoodcasinocharlestown.com/entertainment',
            'ticketmaster_venue_id', 'KovZpZAJ6knA',
            'ticketmaster_public_venue_id', '172587',
            'verification', 'Ticketmaster Discovery API returned 34 total venue events; existing live_nation scraper transformed 10 shows.'
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
                2430,
                'Hollywood Casino Charles Town',
                'hollywood casino charles town',
                'Charles Town',
                'WV',
                'charles town',
                'wv',
                '20260514223000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2430,
                'The Event Center at Hollywood Casino',
                'the event center at hollywood casino',
                'Charles Town',
                'WV',
                'charles town',
                'wv',
                '20260514223000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2430,
                'Hollywood Casino at Charles Town',
                'hollywood casino at charles town',
                'Charles Town',
                'WV',
                'charles town',
                'wv',
                '20260514223000: Ticketmaster venue onboarding',
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
