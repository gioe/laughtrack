-- Hide duplicate tour_dates stub for Improv Comedy Club - Houston (club 2529).
--
-- Club 2529 was auto-created from comedian tour-page discovery as
-- "Improv Comedy Club - Houston" in Houston, TX. Its tour_dates evidence URL is
-- a Vivid Seats page for Shuler King at "Improv Comedy Club - Houston", which
-- duplicates canonical club 40, "Houston Improv". The canonical club already
-- has enabled source 376:
--   platform='custom', scraper_key='improv',
--   source_url='improvtx.com/houston/calendar/'
--
-- Verification on 2026-05-15:
--   * club 2529 has 0 shows and no dependent tagged/subscription/email rows
--   * make scrape-club CLUB="Houston Improv" scraped 149 Improv shows
--   * club_aliases had no existing Houston Improv aliases for this duplicate name

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 40
          AND c.name = 'Houston Improv'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 1
          AND ss.id = 376
          AND ss.platform = 'custom'::"ScrapingPlatform"
          AND ss.scraper_key = 'improv'
          AND ss.source_url = 'improvtx.com/houston/calendar/'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2529: canonical Houston Improv source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2529
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2529
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2529
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2529
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2529
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2529: dependent rows exist';
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
                40,
                'Improv Comedy Club - Houston',
                'improv comedy club houston',
                'Houston',
                'TX',
                'houston',
                'tx',
                '20260516094500: duplicate tour_dates stub 2529',
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
SET name = 'Improv Comedy Club - Houston (duplicate of club 40)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2529
  AND name = 'Improv Comedy Club - Houston'
  AND city = 'Houston'
  AND state = 'TX'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_40',
        'canonical_club_id', 40,
        'canonical_source_id', 376,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE club_id = 2529
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
