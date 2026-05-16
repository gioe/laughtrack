-- Hide duplicate tour_dates stub for "Improv Comedy Club - DC" (club 2524).
--
-- Club 2524 was auto-created from comedian tour-page discovery as
-- "Improv Comedy Club - DC" in Washington, DC. Its tour_dates evidence URL is a
-- Vivid Seats page for Rafi Bastos at "Improv Comedy Club - DC", which
-- duplicates canonical club 102, "DC Improv". The official site
-- https://www.dcimprov.com links to the same SeatEngine Classic calendar:
-- https://dcimprov-com.seatengine.com/calendar
--
-- Verification on 2026-05-15:
--   * Duplicate club 2524 has 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * Canonical club 102 is visible, active, and has enabled source 432:
--     platform='seatengine', scraper_key='seatengine_classic',
--     source_url='dcimprov-com.seatengine.com/calendar', seatengine_id=290.
--   * make scrape-club CLUB="DC Improv" scraped 221 shows from the canonical
--     SeatEngine Classic source.
--   * club_aliases had no existing Washington DC Improv aliases.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 102
          AND c.name = 'DC Improv'
          AND c.city = 'Washington'
          AND c.state = 'DC'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 432
          AND ss.platform = 'seatengine'::"ScrapingPlatform"
          AND ss.scraper_key = 'seatengine_classic'
          AND ss.source_url = 'dcimprov-com.seatengine.com/calendar'
          AND ss.seatengine_id = 290
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2524: canonical DC Improv source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2524
          AND c.name = 'Improv Comedy Club - DC'
          AND c.city = 'Washington'
          AND c.state = 'DC'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1532
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2524: duplicate tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2524
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2524
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2524
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2524
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2524
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2524: dependent rows exist';
    END IF;
END $$;

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
    102,
    'Improv Comedy Club - DC',
    'improv comedy club dc',
    'Washington',
    'DC',
    'washington',
    'dc',
    '20260516093000: duplicate tour_dates stub 2524',
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

UPDATE clubs
SET name = 'Improv Comedy Club - DC (duplicate of club 102)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2524
  AND name = 'Improv Comedy Club - DC'
  AND city = 'Washington'
  AND state = 'DC'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_102',
        'canonical_club_id', 102,
        'canonical_source_id', 432,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    )
WHERE club_id = 2524
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
