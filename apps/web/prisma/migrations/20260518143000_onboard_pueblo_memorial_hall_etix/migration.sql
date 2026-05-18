-- Onboard Pueblo Memorial Hall (club 2575) from tour_dates to the generic
-- Etix scraper using the venue-owned Rockhouse public event listing.
--
-- Verification on 2026-05-18:
--   * Official site: https://pueblomemorialhall.com/
--   * Official address/phone from the site footer.
--   * Etix venue id 21619 exists, but the Etix upcoming-events endpoint is
--     DataDome-blocked from the scraper egress path; Playwright fallback also
--     returned a DataDome bot-block page.
--   * The public venue page exposes the same Rockhouse event widget with Etix
--     ticket links. A live in-memory parser check extracted 14 upcoming events,
--     including Leslie Jones on 2026-10-02 and Steve Trevino on 2026-10-23.
--   * Club 2575 had no dependent rows in shows, tagged_clubs,
--     email_subscriptions, processed_emails, or production_company_venues.

DO $$
DECLARE
    expected_tour_source_id integer := 1583;
    bad_count integer;
BEGIN
    SELECT COUNT(*)
    INTO bad_count
    FROM clubs c
    LEFT JOIN scraping_sources ss
        ON ss.id = expected_tour_source_id
       AND ss.club_id = c.id
       AND ss.platform = 'tour_dates'::"ScrapingPlatform"
       AND ss.scraper_key = 'tour_dates'
       AND ss.enabled = TRUE
    WHERE c.id = 2575
      AND c.name = 'Pueblo Memorial Hall'
      AND c.city = 'Pueblo'
      AND c.state = 'CO'
      AND c.visible = TRUE
      AND c.status = 'active'
      AND ss.id IS NOT NULL;

    IF bad_count <> 1 THEN
        RAISE EXCEPTION 'Cannot onboard Pueblo Memorial Hall: expected club/source rows are missing or changed';
    END IF;
END $$;

UPDATE clubs
SET address = '1 City Hall Place, Pueblo, CO 81003',
    website = 'https://pueblomemorialhall.com/',
    zip_code = '81003',
    phone_number = '719-583-4961',
    timezone = 'America/Denver'
WHERE id = 2575
  AND name = 'Pueblo Memorial Hall'
  AND city = 'Pueblo'
  AND state = 'CO';

UPDATE scraping_sources
SET priority = 10,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'replaced_by_etix_rockhouse_public_source',
        'replacement_platform', 'etix',
        'replacement_source_url', 'https://pueblomemorialhall.com/',
        'verified_at', '2026-05-18'
    ),
    updated_at = NOW()
WHERE id = 1583
  AND club_id = 2575
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
VALUES (
    2575,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://pueblomemorialhall.com/',
    0,
    TRUE,
    jsonb_build_object(
        'verified_at', '2026-05-18',
        'official_site', 'https://pueblomemorialhall.com/',
        'ticketing_backend', 'etix',
        'etix_venue_id', '21619',
        'public_ticket_listing', 'https://pueblomemorialhall.com/',
        'source_note', 'Rockhouse public listing with Etix ticket links; upstream Etix venue API is DataDome-blocked'
    )
)
ON CONFLICT (club_id, platform, priority)
DO UPDATE SET
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
