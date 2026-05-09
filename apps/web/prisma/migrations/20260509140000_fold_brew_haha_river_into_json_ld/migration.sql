-- Fold the bespoke brew_haha_river scraper into the shared json_ld scraper
-- via a new location_name_filter metadata key.
--
-- Comedy Craft Beer (comedycraftbeer.com/calendar) embeds JSON-LD for ALL
-- of its venues on a single page; the prior BrewHaHaRiverExtractor narrowed
-- results by location.name == "River: A Waterfront Restaurant and Bar".
-- The shared json_ld scraper now honors this filter via metadata, so the
-- per-venue subclass is no longer needed (TASK-2068).
UPDATE scraping_sources
SET
    scraper_key = 'json_ld',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'location_name_filter', 'River: A Waterfront Restaurant and Bar',
        'audited_at', '2026-05-09'
    )
-- enabled flag is intentionally NOT in the WHERE clause: the venue folder is
-- deleted in the same change set, so any row still pointing at scraper_key
-- 'brew_haha_river' (enabled or not) must be migrated to avoid an orphaned key.
WHERE club_id = 1350
  AND platform = 'custom'::"ScrapingPlatform"
  AND scraper_key = 'brew_haha_river';
