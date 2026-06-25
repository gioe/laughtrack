-- Switch Improv Asylum (club 141) from the generic Tixr scraper to the
-- venue-specific Pixl Calendar scraper. The calendar API is linked from the
-- public venue site and returns complete title/date/ticket URL/sales data,
-- avoiding the DataDome-blocked Tixr group and event pages.
UPDATE scraping_sources
SET platform = 'custom',
    scraper_key = 'improv_asylum',
    source_url = 'https://calendar.improvasylum.com/api/events/improv-asylum',
    updated_at = NOW()
WHERE club_id = 141
  AND platform = 'tixr'
  AND scraper_key = 'tixr'
  AND source_url = 'https://www.tixr.com/groups/improvasylum'
  AND enabled = true;
