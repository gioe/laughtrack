-- Hide duplicate tour_dates stub for Wiseguys - The Showroom (club 2399).
--
-- Club 2399 was auto-created from comedian tour-page discovery as
-- "Wise Guys Conedy Club" in Salt Lake City, UT. Its tour_dates evidence URL
-- is https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom/e/andrew-schulz,
-- which duplicates canonical club 390, "Wiseguys - The Showroom". The
-- canonical club already has enabled source 644:
--   platform='seatengine', scraper_key='seatengine',
--   source_url='https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom',
--   seatengine_id=361
--
-- Verification on 2026-05-13:
--   * club 2399 has 0 shows and no dependent tagged/subscription/email rows
--   * make scrape-club CLUB="Wiseguys - The Showroom" scraped 115 SeatEngine shows
--   * club_aliases had no existing Utah Wiseguys aliases

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 390
          AND c.name = 'Wiseguys - The Showroom'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 10
          AND ss.id = 644
          AND ss.platform = 'seatengine'::"ScrapingPlatform"
          AND ss.scraper_key = 'seatengine'
          AND ss.source_url = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom'
          AND ss.seatengine_id = 361
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2399: canonical Wiseguys - The Showroom source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2399
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2399: dependent rows exist';
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
                390,
                'Wise Guys Conedy Club',
                'wise guys conedy club',
                'Salt Lake City',
                'UT',
                'salt lake city',
                'ut',
                '20260513172000: duplicate tour_dates stub 2399',
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
SET name = 'Wise Guys Conedy Club (duplicate of club 390)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2399
  AND name = 'Wise Guys Conedy Club'
  AND city = 'Salt Lake City'
  AND state = 'UT'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_390',
        'canonical_club_id', 390,
        'canonical_source_id', 644,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2399
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
