-- Hide duplicate tour_dates stub for Hollywood Improv (club 2523).
--
-- Club 2523 was auto-created from comedian tour-page discovery as
-- "Improv Comedy Club - Hollywood" in Los Angeles, CA. Its tour_dates evidence
-- URL is a Vivid Seats reseller page for Rafi Bastos at "Improv Comedy Club -
-- Hollywood", which duplicates canonical club 32, "Hollywood Improv". The
-- canonical club already has enabled source 381:
--   platform='custom', scraper_key='improv',
--   source_url='improv.com/hollywood/'
--
-- Verification on 2026-05-15:
--   * club 2523 has 0 shows and no dependent tagged/subscription/email rows
--   * make scrape-club CLUB="Hollywood Improv" scraped 12 Improv shows
--   * club_aliases had no existing Los Angeles/Hollywood Improv aliases

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 32
          AND c.name = 'Hollywood Improv'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 1
          AND ss.id = 381
          AND ss.platform = 'custom'::"ScrapingPlatform"
          AND ss.scraper_key = 'improv'
          AND ss.source_url = 'improv.com/hollywood/'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2523: canonical Hollywood Improv source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2523
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2523
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2523
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2523
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2523
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2523: dependent rows exist';
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
                32,
                'Improv Comedy Club - Hollywood',
                'improv comedy club hollywood',
                'Los Angeles',
                'CA',
                'los angeles',
                'ca',
                '20260515204500: duplicate tour_dates stub 2523',
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
SET name = 'Improv Comedy Club - Hollywood (duplicate of club 32)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2523
  AND name = 'Improv Comedy Club - Hollywood'
  AND city = 'Los Angeles'
  AND state = 'CA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_32',
        'canonical_club_id', 32,
        'canonical_source_id', 381,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    )
WHERE club_id = 2523
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
