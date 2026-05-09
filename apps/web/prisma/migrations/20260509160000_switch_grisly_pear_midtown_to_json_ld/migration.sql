-- Switch The Grisly Pear Midtown (club 7) from the NYCC-specific scraper to
-- shared json_ld with an explicit venue filter.
--
-- grislypearstandup.com/calendar embeds JSON-LD for both Grisly Pear venues on
-- one page. A bare json_ld source would scrape Greenwich Village and Midtown
-- together; this metadata keeps club 7 scoped to Midtown while removing the
-- accidental dependency on new_york_comedy_club's address-filter scraper.
UPDATE scraping_sources
SET
    scraper_key = 'json_ld',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'location_name_filter', 'The Grisly Pear Midtown',
        'audited_at', '2026-05-09'
    ),
    updated_at = NOW()
WHERE club_id = 7
  AND platform = 'custom'::"ScrapingPlatform"
  AND scraper_key = 'new_york_comedy_club';
