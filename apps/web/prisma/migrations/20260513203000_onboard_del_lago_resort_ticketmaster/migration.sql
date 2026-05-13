-- Onboard Del Lago Resort & Casino (club 2415) from tour_dates to Ticketmaster.
--
-- Discovered from D.L. Hughley tour-page evidence:
--   https://concerts50.com/buy/d-l-hughley-in-waterloo-tickets-jun-19-2026
--
-- Verification on 2026-05-13:
--   * No existing canonical duplicate found by name/domain in Waterloo, NY
--   * Official page https://dellagoresort.com/entertainment/ lists Ticketmaster buy links
--   * Ticketmaster Discovery venue search returns KovZ917A2-0 for del Lago Resort & Casino
--   * Ticketmaster events API for KovZ917A2-0 returns comedy events, including
--     Ali Siddiq, DL Hughley, Aries Spears, and Harriet
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZ917A2-0 produced 4 comedy shows

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2415
          AND c.name = 'Del Lago Resort & Casino'
          AND c.city = 'Waterloo'
          AND c.state = 'NY'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Del Lago Resort & Casino: expected active tour_dates stub club 2415 is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://dellagoresort.com',
    address = '1133 State Route 414, Waterloo, NY 13165',
    zip_code = '13165',
    timezone = 'America/New_York'
WHERE id = 2415
  AND name = 'Del Lago Resort & Casino'
  AND city = 'Waterloo'
  AND state = 'NY'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'replaced_by_ticketmaster',
        'replacement_platform', 'ticketmaster',
        'replacement_scraper_key', 'live_nation',
        'replacement_ticketmaster_id', 'KovZ917A2-0',
        'disabled_reason', 'ticketmaster_source_verified',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2415
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
    metadata
)
VALUES (
    2415,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZ917A2-0',
    'https://www.ticketmaster.com/del-lago-resort-casino-tickets-waterloo/venue/1436',
    0,
    TRUE,
    jsonb_build_object(
        'source', 'tour_date_club_onboarding',
        'verified_at', '2026-05-13',
        'official_url', 'https://dellagoresort.com/entertainment/',
        'verification', 'Ticketmaster Discovery API venue KovZ917A2-0 returned 4 comedy shows via TicketmasterScraper'
    )
)
ON CONFLICT (club_id, platform, priority)
DO UPDATE SET
    scraper_key = EXCLUDED.scraper_key,
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
                2415,
                'Del Lago Resort Casino',
                'del lago resort casino',
                'Waterloo',
                'NY',
                'waterloo',
                'ny',
                '20260513203000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2415,
                'The Vine at Del Lago Resort',
                'the vine at del lago resort',
                'Waterloo',
                'NY',
                'waterloo',
                'ny',
                '20260513203000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2415,
                'The Vine Theater at Del Lago Resort & Casino',
                'the vine theater at del lago resort casino',
                'Waterloo',
                'NY',
                'waterloo',
                'ny',
                '20260513203000: Ticketmaster venue onboarding',
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
