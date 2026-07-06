-- TASK-3563 follow-up: Comedy Explosion's Wix domain regressed after the
-- initial onboarding validation. The live post-migration make scrape-club run
-- returned zero shows because the domain now serves Wix ConnectYourDomain error
-- pages and the Wix access-token endpoint returns HTTP 404.

UPDATE scraping_sources s
SET enabled = FALSE,
    updated_at = NOW()
FROM clubs c
WHERE s.club_id = c.id
  AND c.google_place_id = 'ChIJoTL1eJ_7xokRxKP67A-9Aw0'
  AND s.platform = 'wix_events'::"ScrapingPlatform"
  AND s.source_url = 'https://thecomedyexplosion.com/';

UPDATE clubs
SET visible = FALSE,
    status = 'closed',
    closed_at = COALESCE(closed_at, NOW())
WHERE google_place_id = 'ChIJoTL1eJ_7xokRxKP67A-9Aw0'
  AND name = 'Comedy Explosion';

INSERT INTO venue_deny_list (
    google_place_id, name, reason, google_primary_type, evidence, added_by, denied_at
)
VALUES (
    'ChIJoTL1eJ_7xokRxKP67A-9Aw0',
    'Comedy Explosion',
    'Discovered Wix domain now serves Wix ConnectYourDomain error pages and the Wix access-token endpoint returns HTTP 404, so there is no safe public source to scrape.',
    'comedy_club',
    '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "stale_site_no_calendar", "post_migration_scrape": "zero_shows"}'::jsonb,
    'TASK-3563',
    NOW()
)
ON CONFLICT (google_place_id) DO UPDATE
SET reason = EXCLUDED.reason,
    google_primary_type = EXCLUDED.google_primary_type,
    evidence = EXCLUDED.evidence,
    added_by = EXCLUDED.added_by,
    denied_at = EXCLUDED.denied_at;
