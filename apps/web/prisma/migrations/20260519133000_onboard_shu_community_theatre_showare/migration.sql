-- Onboard SHU Community Theatre (club 2578) from a temporary tour_dates
-- source to the official accesso ShoWare live-performance feed. ShoWare is
-- represented as platform='custom' with scraper_key='showare' because the
-- current ScrapingPlatform enum has no dedicated ShoWare value.
--
-- Verification on 2026-05-19:
--   * Official site: https://www.shucommunitytheatre.org/
--   * Official all-events page: https://www.shucommunitytheatre.org/allevents
--   * Official ticketing host: https://shucommunitytheatre.showare.com/
--   * ShoWare performance endpoint:
--     https://shucommunitytheatre.showare.com/include/widgets/events/performancelist.asp?action=perf&listPageSize=100&listMaxSize=100&page=1
--   * Endpoint returned 39 performance rows, including comedy-relevant live
--     events: Manhattan Comedy Night, Comedy Bang! Bang!, David Nihill,
--     Colin Mochrie & Brad Sherwood, Leslie Jones, Maria Bamford, and
--     #IMOMSOHARD.
--   * Official all-events page also links movie ticketing to Veezi, so this
--     source_url intentionally points at the ShoWare live-performance host.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2578
          AND c.name = 'SHU Community Theatre'
          AND c.city = 'Fairfield'
          AND c.state = 'CT'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1586
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard SHU Community Theatre club 2578: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE scraper_key = 'showare'
          AND club_id <> 2578
          AND source_url = 'https://shucommunitytheatre.showare.com/default.asp'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard SHU Community Theatre: ShoWare source URL is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    website = 'https://www.shucommunitytheatre.org/',
    timezone = 'America/New_York'
WHERE id = 2578
  AND name = 'SHU Community Theatre'
  AND city = 'Fairfield'
  AND state = 'CT'
  AND visible = TRUE
  AND status = 'active';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2578,
    'custom'::"ScrapingPlatform",
    'showare',
    'https://shucommunitytheatre.showare.com/default.asp',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns', jsonb_build_array(
            'Comedy',
            'Leslie\s+Jones',
            'Maria\s+Bamford',
            'David\s+Nihill',
            'IMOMSOHARD',
            'Mochrie',
            'Sherwood'
        ),
        'exclude_title_patterns', jsonb_build_array(
            'screening',
            'movie',
            'film'
        ),
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-19',
            'official_site', 'https://www.shucommunitytheatre.org/',
            'official_calendar_url', 'https://www.shucommunitytheatre.org/allevents',
            'ticketing_platform', 'accesso_showare',
            'ticketing_host', 'https://shucommunitytheatre.showare.com/',
            'performance_endpoint', 'https://shucommunitytheatre.showare.com/include/widgets/events/performancelist.asp',
            'sample_detail_url', 'https://shucommunitytheatre.showare.com/eventperformances.asp?evt=386',
            'verified_performance_count', 39,
            'veezi_movie_links_present_on_official_calendar', TRUE,
            'verification', 'Generic ShoWare endpoint returned live-performance rows; source_url avoids Veezi movie links on the venue all-events page.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();

UPDATE scraping_sources
SET priority = 1,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_retained', jsonb_build_object(
            'verified_at', '2026-05-19',
            'replacement_platform', 'showare',
            'replacement_scraper_key', 'showare',
            'replacement_source_url', 'https://shucommunitytheatre.showare.com/default.asp',
            'rationale', 'Retained until the ShoWare source has produced a successful production scrape for SHU Community Theatre.'
        )
    ),
    updated_at = NOW()
WHERE id = 1586
  AND club_id = 2578
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
