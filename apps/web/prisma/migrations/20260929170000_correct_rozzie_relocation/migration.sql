-- TASK-4068: reviewed Rozzie relocation correction; no source/show/reference edits.
-- Evidence: apps/scraper/docs/audits/2026-09-29-rozzie/identity.md
-- Coordinates are the existing theater business listing, confirmed at Corinth Street.
DO $task4068$
DECLARE
    current_club jsonb;
    reviewed_state jsonb;
BEGIN
    SELECT to_jsonb(c) INTO current_club FROM clubs c WHERE id = 10970 FOR UPDATE;
    IF current_club IS NULL THEN
        RETURN; -- Other environments may not contain this production venue.
    END IF;
    IF current_club->>'name' IS DISTINCT FROM 'The Rozzie Square Theater'
       OR current_club->>'google_place_id' IS DISTINCT FROM 'ChIJRVOdn8x-44kRtXtU9mgi-jE'
       OR current_club->>'website' IS DISTINCT FROM 'http://www.rozziesquaretheater.com/' THEN
        RAISE EXCEPTION 'TASK-4068: club identity changed; review required';
    END IF;
    -- Lock the existing source while validating ownership; do not change it.
    PERFORM 1 FROM scraping_sources
    WHERE id = 6820 AND club_id = 10970 AND platform = 'custom'
      AND scraper_key = 'anyroad' AND metadata->>'plugin_id' = 'rozziesquaretheater'
      AND source_url = 'https://app.anyroad.com/i/plugin/rozziesquaretheater'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'TASK-4068: expected AnyRoad source ownership changed';
    END IF;
    SELECT jsonb_object_agg(k, current_club->k) INTO reviewed_state
    FROM jsonb_object_keys('{"address": "18 Corinth St, Roslindale, MA 02131", "zip_code": "02131", "latitude": 42.286516, "longitude": -71.13004409999999}'::jsonb) AS keys(k);
    IF reviewed_state = '{"address": "18 Corinth St, Roslindale, MA 02131", "zip_code": "02131", "latitude": 42.286516, "longitude": -71.13004409999999}'::jsonb THEN
        RETURN; -- Exact reviewed state: replay is a no-op.
    END IF;
    IF reviewed_state IS DISTINCT FROM '{"address": "5 Basile St, Roslindale, MA 02131", "zip_code": null, "latitude": 42.2869269, "longitude": -71.1272674}'::jsonb THEN
        RAISE EXCEPTION 'TASK-4068: reviewed before-image changed; refusing to overwrite';
    END IF;
    UPDATE clubs SET
        address = '18 Corinth St, Roslindale, MA 02131',
        zip_code = '02131',
        latitude = 42.286516,
        longitude = -71.13004409999999
    WHERE id = 10970;
END
$task4068$;
