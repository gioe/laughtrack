-- Annotate Laugh Factory Covina's Tixr source with the TASK-2103 audit.
-- Mirrors the TASK-2011 / Rose City Comedy precedent: the source_url stays
-- pointed at the Tixr group page (the venue's own site
-- laughfactory.com/covina hard-redirects to it), enabled stays true so
-- nightly health signals keep flowing, and the blocker is captured in
-- metadata for triage continuity.
--
-- Evidence (2026-05-09 production scraper run, GitHub Actions runner):
--   * https://www.tixr.com/groups/laughfactorycovina returns 403 with
--     `datadome_cookie` interstitial through curl_cffi / TixrClient
--   * Playwright fallback hits an interactive DataDome CAPTCHA; CAPSOLVER
--     is not configured for the `tixr` scraper key, so the rescue returns
--     the challenge HTML unchanged and TixrExtractor extracts zero URLs
--   * https://www.laughfactory.com/covina (the venue-owned URL) issues a
--     302 to the Tixr group page above, which is itself DataDome-blocked
--   * The page is fully populated with future events when viewed in a
--     headed Chromium (10+ events visible 2026-05-09 PT), so this is a
--     fetch-stack issue, not upstream-empty / platform migration
--
-- The Improv Asylum (club_id=141) Pixl Calendar workaround does not apply:
-- Covina has no separate calendar.* host exposing a public events API.

UPDATE scraping_sources ss
SET metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
    'task_2103_audit', jsonb_build_object(
        'status', 'blocked',
        'audited_at', '2026-05-09',
        'fetch_stack', 'TixrClient curl_cffi + PlaywrightBrowser fallback (CAPSOLVER unset for `tixr` key)',
        'last_successful_scrape', '2026-04-20',
        'evidence_run_id', 25594302267,
        'evidence_log_lines', jsonb_build_array(
            'Tixr group-page DataDome interstitial detected (type=datadome_cookie, status=403)',
            '[PlaywrightBrowser] DataDome interactive CAPTCHA detected but CAPSOLVER_API_KEY is unset',
            'page fetch succeeded (html_len=1489) but no Tixr URLs were extracted'
        ),
        'tixr_pages_checked', jsonb_build_array(
            'https://www.tixr.com/groups/laughfactorycovina'
        ),
        'venue_owned_pages_checked', jsonb_build_array(
            'https://www.laughfactory.com/covina'
        ),
        'venue_owned_outcome', '302 redirect to https://www.tixr.com/groups/laughfactorycovina (also DataDome-blocked)',
        'live_browser_state', '10+ future events visible in headed Chromium (e.g. event ids 189028, 189088, 189090, 188798, 187607, 187368, 181041, 179762, 179258)',
        'pixl_fallback_eligible', false,
        'pixl_fallback_reason', 'No public calendar.* host comparable to calendar.improvasylum.com',
        'blocker', 'DataDome CAPTCHA on both curl_cffi and Playwright paths; no CAPSOLVER integration on `tixr` and no venue-owned API to bypass it',
        'fallback_decision', 'Keep enabled; rely on follow-up to add Tixr API or solver mitigation that benefits all DataDome-blocked Tixr group pages'
    )
)
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 171
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;
