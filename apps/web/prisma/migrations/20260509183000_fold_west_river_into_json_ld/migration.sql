-- Fold West River Comedy Club into the shared json_ld scraper.
-- TicketTailor requires rendered HTML for both listing and event pages; the
-- detail_fetch metadata harvests event anchors from paginated listing pages.
UPDATE scraping_sources
SET
    scraper_key = 'json_ld',
    metadata = COALESCE(metadata, '{}'::jsonb) || '{
        "force_js_rendering": true,
        "detail_fetch": {
            "url_path_prefix": "/events/westrivercomedyclub/",
            "exclude_url_path_suffixes": ["/select-date"],
            "pagination": {
                "enabled": true,
                "max_pages": 10
            }
        }
    }'::jsonb,
    updated_at = NOW()
WHERE club_id = 1059
  AND scraper_key = 'west_river_comedy'
  AND enabled = TRUE;
