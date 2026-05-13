-- Hide duplicate tour_dates stub for Orlando Funny Bone (club 2369).
--
-- Club 2369 was auto-created from comedian tour-page discovery as
-- "Funny Bone Comedy Club" in Orlando, FL. It duplicates canonical club 1027,
-- "Orlando Funny Bone", which is already chain-backed and has enabled source 105:
--   platform='ticketmaster', scraper_key='live_nation',
--   ticketmaster_id='ZFr9jZaA61'
--
-- Verification on 2026-05-13:
--   * club 2369 has 0 shows and no dependent tagged/subscription/email rows
--   * Ticketmaster Discovery returned upcoming events for venue ZFr9jZaA61
--   * TicketmasterScraper fetched 47 API events and transformed 43 shows
--   * club_aliases had no existing Orlando aliases for "Funny Bone Comedy Club"
--     or "Funny Bone"

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 1027
          AND c.name = 'Orlando Funny Bone'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 3
          AND ss.id = 105
          AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
          AND ss.scraper_key = 'live_nation'
          AND ss.ticketmaster_id = 'ZFr9jZaA61'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2369: canonical Orlando Funny Bone source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2369
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2369
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2369
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2369
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2369
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2369: dependent rows exist';
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
            VALUES
                (
                    1027,
                    'Funny Bone Comedy Club',
                    'funny bone comedy club',
                    'Orlando',
                    'FL',
                    'orlando',
                    'fl',
                    '20260513143000: duplicate tour_dates stub 2369',
                    TRUE
                ),
                (
                    1027,
                    'Funny Bone',
                    'funny bone',
                    'Orlando',
                    'FL',
                    'orlando',
                    'fl',
                    '20260513143000: duplicate tour_dates stubs 2369/3012',
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
SET name = 'Funny Bone Comedy Club (duplicate of club 1027)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2369
  AND name = 'Funny Bone Comedy Club'
  AND city = 'Orlando'
  AND state = 'FL'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_1027',
        'canonical_club_id', 1027,
        'canonical_source_id', 105,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2369
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
