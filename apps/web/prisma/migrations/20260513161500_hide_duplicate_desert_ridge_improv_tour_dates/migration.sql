-- Hide duplicate tour_dates stub for Desert Ridge Improv (club 2374).
--
-- Club 2374 was auto-created from comedian tour-page discovery as
-- "DESERT RIDGE IMPROV" in Phoenix, AZ. It duplicates canonical club 104,
-- "Desert Ridge Improv", which already has enabled source 610:
--   platform='seatengine', scraper_key='seatengine_classic',
--   source_url='desertridgeimprov.com/events'
--
-- Verification on 2026-05-13:
--   * club 2374 has 0 shows and no dependent tagged/subscription/email rows
--   * PlaywrightBrowser fetched the official site, tour-date show URL, and
--     events page, all with SeatEngine markers
--   * make scrape-club-id ID=104 scraped 67 shows and persisted 65 valid updates
--   * club_aliases had no existing Phoenix alias for "DESERT RIDGE IMPROV"

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 104
          AND c.name = 'Desert Ridge Improv'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 1
          AND ss.id = 610
          AND ss.platform = 'seatengine'::"ScrapingPlatform"
          AND ss.scraper_key = 'seatengine_classic'
          AND ss.source_url = 'desertridgeimprov.com/events'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2374: canonical Desert Ridge Improv source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2374
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2374
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2374
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2374
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2374
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2374: dependent rows exist';
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
        EXECUTE $alias_sql$
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
                104,
                'DESERT RIDGE IMPROV',
                'desert ridge improv',
                'Phoenix',
                'AZ',
                'phoenix',
                'az',
                '20260513161500: duplicate tour_dates stub 2374',
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
                updated_at = NOW()
        $alias_sql$;
    END IF;
END $$;

UPDATE clubs
SET name = 'DESERT RIDGE IMPROV (duplicate of club 104)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2374
  AND name = 'DESERT RIDGE IMPROV'
  AND city = 'Phoenix'
  AND state = 'AZ'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_104',
        'canonical_club_id', 104,
        'canonical_source_id', 610,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2374
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
