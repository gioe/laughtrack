-- Point St. Marks Comedy Club at its venue-owned calendar page.
--
-- The homepage exposes only a subset of upcoming cards. The /calendar page
-- exposes complete Webflow cards with title, date/time, and Tixr ticket URLs,
-- allowing the generic Tixr scraper's public-card fallback to avoid blocked
-- Tixr/DataDome event-detail pages.
UPDATE scraping_sources
SET
    source_url = 'https://www.stmarkscomedyclub.com/calendar',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'public_card_fallback', true,
        'fallback_reason', 'Venue-owned Webflow calendar exposes title/date/time/ticket URL; Tixr detail pages are DataDome-blocked in automation.',
        'audited_at', '2026-05-08'
    )
WHERE club_id = 16
  AND platform = 'tixr'::"ScrapingPlatform"
  AND scraper_key = 'tixr'
  AND enabled = true;
