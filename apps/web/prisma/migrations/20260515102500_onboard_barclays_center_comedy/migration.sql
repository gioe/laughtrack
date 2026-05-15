-- Onboard Barclays Center (club 2464) from temporary tour_dates discovery /
-- disposition state to a focused venue-owned comedy category scraper.
--
-- Discovered from tour_dates evidence for Michael Blackson / Nick Cannon
-- Presents Wild N Out Live No Filter on June 28, 2026.
--
-- Verification on 2026-05-15:
--   * Official site https://www.barclayscenter.com has a dedicated comedy
--     category at https://www.barclayscenter.com/events/category/comedy.
--   * The category page links to the official event detail page:
--     https://www.barclayscenter.com/events/detail/nick-cannon-wild-n-out-live-no-filter-2026
--     and Ticketmaster purchase URL:
--     https://www.ticketmaster.com/event/3000648FD9FB7F6A.
--   * Migration 20260515102000_disposition_barclays_center_tour_dates already
--     disabled source 1472 as unsafe generic Ticketmaster inventory; this
--     migration intentionally accepts that disposition state and replaces it
--     with the focused custom source.
--   * Ticketmaster Discovery venue id KovZ917AtP3 is valid but venue-wide
--     ingestion is unsafe here: it returned 110 total upcoming venue events,
--     and a read-only live_nation run transformed 36 shows including Barclays
--     Center Tours and sports-related tours. The generic live_nation source is
--     therefore intentionally not enabled for this arena.

DO $$
DECLARE
    matching_clubs integer;
BEGIN
    SELECT COUNT(*)
    INTO matching_clubs
    FROM clubs
    WHERE id = 2464
      AND name = 'Barclays Center'
      AND city = 'Brooklyn'
      AND state = 'NY'
      AND visible = TRUE
      AND status = 'active';

    IF matching_clubs <> 1 THEN
        RAISE EXCEPTION 'Cannot onboard Barclays Center: expected exactly one matching club row, found %', matching_clubs;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2464
          AND c.name = 'Barclays Center'
          AND c.city = 'Brooklyn'
          AND c.state = 'NY'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1472
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND (
              ss.enabled = TRUE
              OR (
                  ss.enabled = FALSE
                  AND ss.source_url = 'https://www.barclayscenter.com/events/category/comedy'
                  AND ss.metadata->>'task_tour_date_onboarding_disposition' = 'needs_focused_carbonhouse_comedy_scraper'
              )
          )
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Barclays Center: expected tour_dates stub/disposition source 1472 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZ917AtP3'
          AND club_id <> 2464
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Barclays Center: Ticketmaster venue KovZ917AtP3 is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.barclayscenter.com',
    address = '620 Atlantic Ave',
    zip_code = '11217',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2464
  AND name = 'Barclays Center'
  AND city = 'Brooklyn'
  AND state = 'NY'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'barclays_center',
            'replacement_source_url', 'https://www.barclayscenter.com/events/category/comedy',
            'rationale', 'Temporary tour_dates source replaced after verified venue-owned comedy category scraper avoided non-comedy arena events.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2464
  AND id = 1472
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
    2464,
    'custom'::"ScrapingPlatform",
    'barclays_center',
    'https://www.barclayscenter.com/events/category/comedy',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.barclayscenter.com',
            'official_category', 'https://www.barclayscenter.com/events/category/comedy',
            'sample_event_detail', 'https://www.barclayscenter.com/events/detail/nick-cannon-wild-n-out-live-no-filter-2026',
            'sample_ticket_url', 'https://www.ticketmaster.com/event/3000648FD9FB7F6A',
            'rejected_generic_source', jsonb_build_object(
                'platform', 'ticketmaster',
                'scraper_key', 'live_nation',
                'ticketmaster_venue_id', 'KovZ917AtP3',
                'reason', 'Venue-wide Ticketmaster source returned 110 total events and transformed non-comedy Barclays Center Tours / sports-related tours.'
            )
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
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
                2464,
                'Barclays Center',
                'barclays center',
                'Brooklyn',
                'NY',
                'brooklyn',
                'ny',
                '20260515102500: focused Barclays comedy category onboarding',
                TRUE
            ),
            (
                2464,
                'Barclays Center Brooklyn',
                'barclays center brooklyn',
                'Brooklyn',
                'NY',
                'brooklyn',
                'ny',
                '20260515102500: focused Barclays comedy category onboarding',
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
    END IF;
END $$;
