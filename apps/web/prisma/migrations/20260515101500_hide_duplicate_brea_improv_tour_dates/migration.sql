-- Hide duplicate tour_dates stub for Improv Comedy Club - Brea (club 2496).
--
-- Club 2496 was auto-created from comedian tour-page discovery as
-- "Improv Comedy Club - Brea" in Brea, CA. Its tour_dates evidence URL is a
-- Vivid Seats page for Nurse John at "Brea Improv Comedy Club - Brea", which
-- duplicates canonical club 30, "Brea Improv". The canonical club already has
-- enabled source 346:
--   platform='custom', scraper_key='improv',
--   source_url='improv.com/brea/'
--
-- Verification on 2026-05-15:
--   * club 2496 has 0 shows and no dependent tagged/subscription/email rows
--   * make scrape-club CLUB="Brea Improv" scraped 19 Improv shows
--   * club_aliases had no existing Brea aliases for this duplicate name

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 30
          AND c.name = 'Brea Improv'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 1
          AND ss.id = 346
          AND ss.platform = 'custom'::"ScrapingPlatform"
          AND ss.scraper_key = 'improv'
          AND ss.source_url = 'improv.com/brea/'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2496: canonical Brea Improv source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2496
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2496
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2496
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2496
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2496
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2496: dependent rows exist';
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
                30,
                'Improv Comedy Club - Brea',
                'improv comedy club brea',
                'Brea',
                'CA',
                'brea',
                'ca',
                '20260515101500: duplicate tour_dates stub 2496',
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
SET name = 'Improv Comedy Club - Brea (duplicate of club 30)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2496
  AND name = 'Improv Comedy Club - Brea'
  AND city = 'Brea'
  AND state = 'CA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_30',
        'canonical_club_id', 30,
        'canonical_source_id', 346,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    )
WHERE club_id = 2496
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
