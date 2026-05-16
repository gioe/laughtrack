-- Hide duplicate tour_dates stub for Funny Bone - Richmond (club 2556).
--
-- Club 2556 was auto-created from comedian tour-page discovery as
-- "Funny Bone - Richmond" in Richmond, VA. Its tour_dates evidence URL is a
-- Vivid Seats page for Kountry Wayne at "Funny Bone - Richmond", which
-- duplicates canonical club 1034, "Richmond Funny Bone". The canonical club
-- already has enabled source 108:
--   platform='ticketmaster', scraper_key='live_nation',
--   source_url='https://www.ticketmaster.com/venue/Z7r9jZadVa',
--   ticketmaster_id='Z7r9jZadVa'
--
-- Verification on 2026-05-16:
--   * club 2556 has 0 shows and no dependent tagged/subscription/email/
--     production-company rows
--   * the Ticketmaster Discovery API returned upcoming events for venue
--     Z7r9jZadVa
--   * make scrape-club CLUB="Richmond Funny Bone" fetched 68 Ticketmaster
--     events, transformed 59 comedy shows, and persisted 59 valid shows
--   * club_aliases had no existing Richmond Funny Bone aliases

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 1034
          AND c.name = 'Richmond Funny Bone'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 3
          AND ss.id = 108
          AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
          AND ss.scraper_key = 'live_nation'
          AND ss.source_url = 'https://www.ticketmaster.com/venue/Z7r9jZadVa'
          AND ss.ticketmaster_id = 'Z7r9jZadVa'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2556: canonical Richmond Funny Bone source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2556
          AND c.name = 'Funny Bone - Richmond'
          AND c.city = 'Richmond'
          AND c.state = 'VA'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1564
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2556: duplicate tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2556
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2556
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2556
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2556
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2556
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2556: dependent rows exist';
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
                1034,
                'Funny Bone - Richmond',
                'funny bone richmond',
                'Richmond',
                'VA',
                'richmond',
                'va',
                '20260516104500: duplicate tour_dates stub 2556',
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
SET name = 'Funny Bone - Richmond (duplicate of club 1034)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2556
  AND name = 'Funny Bone - Richmond'
  AND city = 'Richmond'
  AND state = 'VA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_1034',
        'canonical_club_id', 1034,
        'canonical_source_id', 108,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-16'
    )
WHERE id = 1564
  AND club_id = 2556
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
