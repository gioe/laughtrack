-- Move The Stand NYC (club_id=5) onto the tixr_public_card scraper.
--
-- TASK-2044 split Tixr scraping into two keys: `tixr` for DataDome-sensitive
-- Tixr-hosted detail/group pages, and `tixr_public_card` for venue-owned
-- pages whose cards already carry title, date/time, and a Tixr ticket URL.
--
-- Audit on 2026-05-08 confirmed thestandnyc.com/shows exposes:
--   * title       — h2.showtitle a
--   * date/time   — encoded in the showtitle href slug
--                   /shows/show/<id>/<YYYY-MM-DD>-<HHMMSS>-...
--   * ticket URL  — a.btn-stand[href*="tixr.com"]
-- Sold-out cards replace the buy button with span.btn-outline-danger and
-- carry no Tixr URL; they are intentionally skipped (the Tixr API path
-- can't reach them either).
--
-- The page is Bootstrap-styled (not Webflow), so this commit ships
-- alongside a Stand-specific branch in TixrScraper._parse_public_calendar_events
-- that walks .show_row containers in addition to the existing Webflow
-- selectors used by Bloomington and St Marks.
UPDATE scraping_sources
SET
    scraper_key = 'tixr_public_card',
    source_url = 'https://thestandnyc.com/shows',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tixr_source_type', 'venue_public_card',
        'detail_fetch_required', false,
        'datadome_dependent', false,
        'audit_note', 'Bootstrap-style .show_row cards expose title/ISO-datetime/ticket URL; Tixr is only the ticket provider.',
        'audited_at', '2026-05-08'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE club_id = 5
  AND platform = 'tixr'::"ScrapingPlatform"
  AND scraper_key = 'tixr'
  AND enabled = true;
