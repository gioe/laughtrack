-- The venue-specific `improv_asylum` scraper was removed in favor of the
-- generic Tixr scraper, which owns the Improv Asylum Pixl Calendar fallback.
-- A late-applied older migration repointed this source to the removed key.
UPDATE scraping_sources
SET platform = 'tixr',
    scraper_key = 'tixr',
    source_url = 'https://www.tixr.com/groups/improvasylum',
    updated_at = NOW()
WHERE club_id = 141
  AND platform = 'custom'
  AND scraper_key = 'improv_asylum'
  AND source_url = 'https://calendar.improvasylum.com/api/events/improv-asylum'
  AND enabled = true;
