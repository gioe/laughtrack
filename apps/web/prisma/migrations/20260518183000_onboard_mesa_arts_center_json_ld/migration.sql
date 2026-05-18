-- Onboard Mesa Arts Center (club 2574) from temporary tour_dates discovery
-- to the existing generic JSON-LD detail-page scraper.
--
-- Verification on 2026-05-18:
--   * No existing active canonical duplicate found by Mesa Arts Center name,
--     mesaartscenter.com domain, or source URL.
--   * Official site https://www.mesaartscenter.com lists Mesa Arts Center at
--     1 East Main Street, Mesa, AZ 85201.
--   * The Theater-Comedy listing links official show detail pages under
--     /show-details/, and those detail pages expose schema.org TheaterEvent
--     JSON-LD with names, dates, official show URLs, and starting prices.
--   * A read-only JsonLdScraper smoke run against the configured listing
--     produced 22 shows, including:
--       - Leslie Jones: I'm Hot Tour, 2026-09-19
--       - Patton Oswalt, 2026-10-03
--       - Eddie B., 2026-10-17
--   * Ticketmaster venue KovZpZAdE11A exists, but its Discovery API comedy
--     results only returned Davide De Pierro and missed the tour_dates
--     evidence event, so the official JSON-LD source is more complete.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2574
          AND c.name = 'Mesa Arts Center'
          AND c.city = 'Mesa'
          AND c.state = 'AZ'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1582
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mesa Arts Center: expected active tour_dates stub club 2574/source 1582 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE club_id <> 2574
          AND enabled = TRUE
          AND lower(source_url) = 'https://www.mesaartscenter.com/performances/filtered/category/theater-comedy'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mesa Arts Center: Theater-Comedy JSON-LD source URL is already assigned to another enabled source';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.mesaartscenter.com',
    address = '1 East Main Street',
    zip_code = '85201',
    country = 'US',
    timezone = 'America/Phoenix'
WHERE id = 2574
  AND name = 'Mesa Arts Center'
  AND city = 'Mesa'
  AND state = 'AZ'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'json_ld',
            'replacement_source_url', 'https://www.mesaartscenter.com/performances/filtered/category/Theater-Comedy',
            'rationale', 'Temporary tour_dates source replaced after verified generic JSON-LD scrape produced comedy-relevant shows from the official Mesa Arts Center listing.'
        )
    ),
    updated_at = NOW()
WHERE id = 1582
  AND club_id = 2574
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

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
    2574,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.mesaartscenter.com/performances/filtered/category/Theater-Comedy',
    0,
    TRUE,
    jsonb_build_object(
        'detail_fetch', jsonb_build_object(
            'url_path_prefix', '/show-details/',
            'set_same_as_to_detail_url', TRUE,
            'max_pages', 1
        ),
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-18',
            'official_site', 'https://www.mesaartscenter.com',
            'official_calendar', 'https://www.mesaartscenter.com/performances/filtered/category/Theater-Comedy',
            'ticketing_domain', 'https://boxoffice.mesaartscenter.com',
            'sample_events', jsonb_build_array(
                'Leslie Jones: I''m Hot Tour',
                'Patton Oswalt',
                'Eddie B.'
            ),
            'verification', 'Read-only JsonLdScraper smoke run returned 22 shows from official detail-page JSON-LD. Ticketmaster venue KovZpZAdE11A exists but missed the tour_dates evidence event in comedy-filtered Discovery API results.',
            'known_limitation', 'Mesa detail-page JSON-LD startDate is date-only; offer availability timestamps include show times but the generic transformer currently stores date-only show datetimes for this source.'
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
