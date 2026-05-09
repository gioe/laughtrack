-- TASK-2101: Palm Beach Improv's Kravis source is currently upstream-empty.
--
-- Live checks on 2026-05-09 found:
-- - https://www.kravis.org/performance-calendar/improv/ renders Kravis' "page
--   does not exist" content.
-- - The Kravis month API returned center-wide performances for May 2026 through
--   Apr 2027, but no Palm Beach Improv comedy-series shows. The only
--   candidate under the existing pre-filter was a non-Improv Persson Hall
--   performance ("A MID SUMMER NIGHT'S DREAM").
--
-- Disable the custom source and stamp metadata rather than broadening the
-- candidate filter into unrelated Kravis programming.
UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2101_disposition',
        jsonb_build_object(
            'kind', 'upstream_empty',
            'checked_at', '2026-05-09',
            'source_url_status', 'kravis_improv_page_404',
            'months_checked', '2026-05 through 2027-04',
            'rationale', 'Kravis currently exposes no Palm Beach Improv comedy-series events; the only live pre-filter candidate is a non-Improv Persson Hall event.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 379
  AND platform = 'custom'::"ScrapingPlatform"
  AND scraper_key = 'palm_beach_improv'
  AND priority = 0;
