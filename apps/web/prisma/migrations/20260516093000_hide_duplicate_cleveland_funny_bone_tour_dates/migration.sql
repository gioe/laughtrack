-- Hide duplicate tour_dates stub for Funny Bone - Cleveland (club 2552).
--
-- Club 2552 was auto-created from comedian tour-page discovery as
-- "Funny Bone - Cleveland" in Cleveland, OH. Its tour_dates evidence URL is a
-- Vivid Seats page for Kountry Wayne at "Funny Bone - Cleveland", which
-- duplicates canonical club 1050, "Cleveland Funny Bone". The canonical club
-- already has enabled source 136:
--   platform='ticketmaster', scraper_key='live_nation',
--   source_url='https://www.ticketmaster.com/venue/Z7r9jZaAhN',
--   ticketmaster_id='Z7r9jZaAhN'
--
-- Verification on 2026-05-16:
--   * club 2552 has 0 shows and no dependent tagged/subscription/email rows
--   * make scrape-club CLUB="Cleveland Funny Bone" fetched 18 Ticketmaster
--     events, transformed 15 comedy shows, and persisted 15 valid shows
--   * club_aliases had no existing Cleveland Funny Bone aliases

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 1050
          AND c.name = 'Cleveland Funny Bone'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 3
          AND ss.id = 136
          AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
          AND ss.scraper_key = 'live_nation'
          AND ss.source_url = 'https://www.ticketmaster.com/venue/Z7r9jZaAhN'
          AND ss.ticketmaster_id = 'Z7r9jZaAhN'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2552: canonical Cleveland Funny Bone source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2552
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2552
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2552
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2552
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2552
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2552: dependent rows exist';
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
                1050,
                'Funny Bone - Cleveland',
                'funny bone cleveland',
                'Cleveland',
                'OH',
                'cleveland',
                'oh',
                '20260516093000: duplicate tour_dates stub 2552',
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
SET name = 'Funny Bone - Cleveland (duplicate of club 1050)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2552
  AND name = 'Funny Bone - Cleveland'
  AND city = 'Cleveland'
  AND state = 'OH'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_1050',
        'canonical_club_id', 1050,
        'canonical_source_id', 136,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-16'
    )
WHERE club_id = 2552
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
