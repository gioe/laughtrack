-- TASK-2009: Switch The Lounge at World Stage (club 1353) from the
-- DataDome-blocked Etix venue page to a public-page fallback that hits the
-- venue's Ciright booking-tool calendar API directly.
--
-- The venue rebranded — worldcafelive.org now redirects to worldstage.live.
-- Their /shows page is rendered from a public POST endpoint at
--   https://www.myciright.com/Ciright/api/worldcafelive/m3203760
-- which is unauthenticated, returns structured JSON for every confirmed
-- booking, and lives on a host that is not behind DataDome (verified live
-- via plain curl on 2026-05-07: 35 confirmed Lounge events through
-- 7/30/2026, status=true, no captcha, no cookies needed).
--
-- The new `world_stage` scraper filters the response to roomId=3131060
-- (The Lounge); Main Hall (3131059) and XPN Studios (3251418) are left out
-- of this venue's ingest because club 1353 is the Lounge specifically.
-- Other rooms can be onboarded later by adding a scraping_sources row that
-- points at the same scraper with a different `room_ids` metadata value.
--
-- The original etix source row is disabled rather than deleted so the
-- previous configuration is preserved for audit and easy rollback.

-- Disable the legacy Etix source so it is no longer chosen by the
-- multi-source scrape loop.
UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 1353
  AND platform = 'etix'::"ScrapingPlatform";

-- Insert the new custom World Stage source at priority 0 if no row already
-- exists at that slot. Done as INSERT ... WHERE NOT EXISTS so a manual
-- pre-stage of this row before the migration runs does not error on the
-- (club_id, platform, priority) unique constraint.
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
SELECT
    1353,
    'custom'::"ScrapingPlatform",
    'world_stage',
    'https://worldstage.live/shows',
    0,
    TRUE,
    jsonb_build_object(
        'subscription_id', 8990189,
        'vertical_id', 2851,
        'type_id', 1662515,
        'app_id', 2949,
        'status_id', 1851385,
        'room_ids', jsonb_build_array(3131060),
        'lookahead_days', 120,
        'api_url', 'https://www.myciright.com/Ciright/api/worldcafelive/m3203760',
        'task_2009_audit', jsonb_build_object(
            'rebrand', 'worldcafelive.org -> worldstage.live (https://worldstage.live/shows)',
            'fallback_reason', 'etix venue 26727 returns DataDome iframe; Ciright API on myciright.com is unprotected and exposes the same calendar',
            'verified_live', '2026-05-07 — 33+ confirmed Lounge events fetched + transformed end-to-end',
            'rooms_known', jsonb_build_object(
                'lounge_id', 3131060,
                'main_hall_id', 3131059,
                'xpn_studios_id', 3251418
            )
        )
    ),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM scraping_sources
    WHERE club_id = 1353
      AND platform = 'custom'::"ScrapingPlatform"
      AND priority = 0
);

-- If the row already existed (manual pre-stage or re-run), update it in place.
UPDATE scraping_sources
SET scraper_key = 'world_stage',
    source_url = 'https://worldstage.live/shows',
    enabled = TRUE,
    metadata = jsonb_build_object(
        'subscription_id', 8990189,
        'vertical_id', 2851,
        'type_id', 1662515,
        'app_id', 2949,
        'status_id', 1851385,
        'room_ids', jsonb_build_array(3131060),
        'lookahead_days', 120,
        'api_url', 'https://www.myciright.com/Ciright/api/worldcafelive/m3203760',
        'task_2009_audit', jsonb_build_object(
            'rebrand', 'worldcafelive.org -> worldstage.live (https://worldstage.live/shows)',
            'fallback_reason', 'etix venue 26727 returns DataDome iframe; Ciright API on myciright.com is unprotected and exposes the same calendar',
            'verified_live', '2026-05-07 — 33+ confirmed Lounge events fetched + transformed end-to-end',
            'rooms_known', jsonb_build_object(
                'lounge_id', 3131060,
                'main_hall_id', 3131059,
                'xpn_studios_id', 3251418
            )
        )
    ),
    updated_at = NOW()
WHERE club_id = 1353
  AND platform = 'custom'::"ScrapingPlatform"
  AND priority = 0;

-- Update the club's website to the rebranded domain so detail-page links and
-- attribution surface the current venue identity.
UPDATE clubs
SET website = 'https://worldstage.live/'
WHERE id = 1353
  AND website = 'https://worldcafelive.org';
