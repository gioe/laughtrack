-- Hide duplicate tour_dates stub for Wiseguys Comedy Club in Salt Lake City (club 2416).
--
-- Club 2416 was auto-created from comedian tour-page discovery as
-- "Wiseguys Comedy Club" in Salt Lake City, UT. Its tour_dates evidence came
-- from a D.L. Hughley tour listing, and the official Wiseguys page lists the
-- same shows under the existing canonical Salt Lake City venue.
--
-- Canonical club 390 already has enabled source 644:
--   platform='seatengine', scraper_key='seatengine',
--   source_url='https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom',
--   seatengine_id=361
--
-- Verification on 2026-05-13:
--   * club 2416 has 0 shows and no dependent tagged/subscription/email/
--     production-company rows
--   * make scrape-club CLUB="Wiseguys Comedy Club - Salt Lake City" scraped
--     115 SeatEngine shows
--   * the canonical scrape includes DL Hughley shows on 2026-06-27/28 UTC
--   * club_aliases had no existing Salt Lake City alias for
--     "Wiseguys Comedy Club"

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 390
          AND c.name = 'Wiseguys Comedy Club - Salt Lake City'
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
        RAISE EXCEPTION 'Cannot hide duplicate club 2416: canonical Wiseguys Salt Lake City source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2416
          AND c.name = 'Wiseguys Comedy Club'
          AND c.city = 'Salt Lake City'
          AND c.state = 'UT'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1424
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2416: expected tour_dates stub is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2416
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2416
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2416
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2416
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2416
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate club 2416: dependent rows exist';
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
    390,
    'Wiseguys Comedy Club',
    'wiseguys comedy club',
    'Salt Lake City',
    'UT',
    'salt lake city',
    'ut',
    '20260513225500: duplicate tour_dates stub 2416',
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
SET name = 'Wiseguys Comedy Club (duplicate of club 390)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2416
  AND name = 'Wiseguys Comedy Club'
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
    ),
    updated_at = NOW()
WHERE id = 1424
  AND club_id = 2416
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
