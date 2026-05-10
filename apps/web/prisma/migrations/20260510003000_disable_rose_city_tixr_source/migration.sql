-- [TASK-2104] Disable Rose City Comedy's DataDome-blocked Tixr source.
--
-- TASK-2011 recorded that the venue-owned Rose City pages expose only Tixr
-- links/posters and no machine-readable date/time, while the Tixr group,
-- event, and likely API paths return DataDome challenge HTML through the
-- scraper's fetch stack. Without residential proxy plus CAPTCHA solving,
-- this source cannot deterministically produce shows and has not produced new
-- inventory since 2026-04-07. Disable it so stale-scraper audits stop
-- treating this as an actionable live source.

UPDATE scraping_sources ss
SET
    enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2104_disposition', jsonb_build_object(
            'kind', 'disabled_datadome_blocked_tixr_source',
            'closed_reason', 'disabled_source_requires_residential_proxy_and_captcha_aware_tixr_path',
            'evidence_task', 2011,
            'evidence_date', '2026-05-08',
            'source_id', 438,
            'club_id', 1023,
            'last_new_show_date', '2026-04-07',
            'blocker', 'Tixr group, event, and likely API paths return DataDome challenge HTML through scraper PlaywrightBrowser and TixrClient/HttpClient paths',
            'rationale', 'Rose City Comedy venue-owned pages do not expose machine-readable event dates or times; keep the club visible but disable this non-deterministic Tixr source until a proxy and CAPTCHA-aware Tixr path exists.'
        )
    ),
    updated_at = NOW()
FROM clubs c
WHERE ss.id = 438
  AND ss.club_id = 1023
  AND ss.club_id = c.id
  AND c.name = 'Rose City Comedy'
  AND ss.platform = 'tixr'::"ScrapingPlatform"
  AND ss.scraper_key = 'tixr';
