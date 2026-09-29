-- TASK-4069: reviewed District Dome postal correction; no source/show/reference edits.
-- Evidence: apps/scraper/docs/audits/2026-09-29-district-dome/identity.md
-- Operator-provided ZIP 85050 takes precedence over conflicting Google ZIP 85054.
-- Retain the verified business map point; no show or source reassignment.
DO $task4069$
DECLARE
    current_club jsonb;
    reviewed_state jsonb;
BEGIN
    SELECT to_jsonb(c) INTO current_club FROM clubs c WHERE id = 554 FOR UPDATE;
    IF current_club IS NULL THEN
        RETURN; -- Other environments may not contain this production venue.
    END IF;
    IF current_club->>'name' IS DISTINCT FROM 'District Dome'
       OR current_club->>'google_place_id' IS DISTINCT FROM 'ChIJ_y7Ne-BwK4cR7wtdsKrbYgw'
       OR current_club->>'website' IS DISTINCT FROM 'https://www.districtdome.com' THEN
        RAISE EXCEPTION 'TASK-4069: club identity changed; review required';
    END IF;
    -- Lock the existing source while validating ownership; do not change it.
    PERFORM 1 FROM scraping_sources
    WHERE id = 87 AND club_id = 554 AND platform = 'seatengine'
      AND scraper_key = 'seatengine' AND seatengine_id = 534
      AND source_url = 'https://www.districtdome.com'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'TASK-4069: expected SeatEngine source ownership changed';
    END IF;
    SELECT jsonb_object_agg(k, current_club->k) INTO reviewed_state
    FROM jsonb_object_keys('{"address": "21001 N Tatum Blvd, Phoenix, AZ 85050, USA", "zip_code": "85050"}'::jsonb) AS keys(k);
    IF reviewed_state = '{"address": "21001 N Tatum Blvd, Phoenix, AZ 85050, USA", "zip_code": "85050"}'::jsonb THEN
        RETURN; -- Exact reviewed state: replay is a no-op.
    END IF;
    IF reviewed_state IS DISTINCT FROM '{"address": "21001 N Tatum Blvd, Phoenix, AZ 85054, USA", "zip_code": ""}'::jsonb THEN
        RAISE EXCEPTION 'TASK-4069: reviewed before-image changed; refusing to overwrite';
    END IF;
    UPDATE clubs SET
        address = '21001 N Tatum Blvd, Phoenix, AZ 85050, USA',
        zip_code = '85050'
    WHERE id = 554;
END
$task4069$;
