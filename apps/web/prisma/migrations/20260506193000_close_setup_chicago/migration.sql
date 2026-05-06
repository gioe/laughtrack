-- Close The Setup Chicago (club 660).
--
-- Official Setup Comedy currently lists San Francisco, Los Angeles, Seattle,
-- and Vancouver as locations. Chicago is no longer listed, its configured
-- Stagetime CSV source is header-only, and the club has no historical show
-- rows in LaughTrack. Keep chain_id for historical lineage, but hide/close the
-- club and disable its stale source so it no longer appears as an active
-- location or runs in nightly scraping.
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = COALESCE(closed_at, '2026-05-06T19:30:00+00:00'::timestamptz)
WHERE id = 660
  AND name = 'The Setup Chicago'
  AND status <> 'closed';

UPDATE scraping_sources
SET enabled = false,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_setup_chicago_closure',
        jsonb_build_object(
            'kind', 'closed_location_removed_from_official_chain',
            'verified_at', '2026-05-06',
            'reason', 'Official Setup Comedy locations are SF, LA, Seattle, and Vancouver; Chicago source is header-only.'
        )
    ),
    updated_at = NOW()
WHERE id = 138
  AND club_id = 660
  AND platform = 'stagetime'::"ScrapingPlatform"
  AND scraper_key = 'setup';
