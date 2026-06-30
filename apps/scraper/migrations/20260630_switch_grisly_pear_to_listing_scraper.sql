-- TASK-3517: The Grisly Pear calendar page's JSON-LD only exposes stale/current
-- rows, while the server-rendered event anchors include the upcoming month.
-- Switch both venues to the venue-specific listing scraper that parses those
-- anchors and assigns rows to Midtown vs Greenwich Village by title.

UPDATE scraping_sources
SET
    scraper_key = 'grisly_pear',
    source_url = 'https://www.grislypearstandup.com/calendar',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3517_switched_to_listing_scraper_at', '2026-06-30'
    ),
    updated_at = NOW()
WHERE club_id IN (6, 7)
  AND scraper_key = 'json_ld';

