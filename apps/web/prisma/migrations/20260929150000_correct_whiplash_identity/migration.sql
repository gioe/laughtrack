-- TASK-4067: reviewed Whiplash location correction; no source/show/reference edits.
-- Evidence: apps/scraper/docs/audits/2026-09-29-whiplash/identity.md
-- Coordinates are the verified Ponce City Market Service Building address point.
-- No Whiplash business place ID was found; do not substitute the building ID.
DO $task4067$
DECLARE
    current_club jsonb;
    reviewed_state jsonb;
BEGIN
    SELECT to_jsonb(c) INTO current_club FROM clubs c WHERE id = 1347 FOR UPDATE;
    IF current_club IS NULL THEN
        RETURN; -- Other environments may not contain this production venue.
    END IF;
    IF current_club->>'name' IS DISTINCT FROM 'Whiplash Comedy'
       OR current_club->>'website' IS DISTINCT FROM 'https://whiplashcomedy.com/' THEN
        RAISE EXCEPTION 'TASK-4067: club identity changed; review required';
    END IF;
    -- Lock the existing source while validating ownership; do not change it.
    PERFORM 1 FROM scraping_sources
    WHERE id = 591 AND club_id = 1347 AND platform = 'seatengine'
      AND seatengine_id = 650 AND source_url = 'https://whiplashcomedy.com/'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'TASK-4067: expected SeatEngine source ownership changed';
    END IF;
    SELECT jsonb_object_agg(k, current_club->k) INTO reviewed_state
    FROM jsonb_object_keys('{"address": "650 North Avenue NE, Suite S210, Atlanta, GA 30308, USA", "city": "Atlanta", "state": "GA", "zip_code": "30308", "latitude": 33.7713365, "longitude": -84.3667376, "google_place_id": null, "google_place_attribution": [], "description": "Whiplash Comedy at Ponce City Market in Atlanta."}'::jsonb) AS keys(k);
    IF reviewed_state = '{"address": "650 North Avenue NE, Suite S210, Atlanta, GA 30308, USA", "city": "Atlanta", "state": "GA", "zip_code": "30308", "latitude": 33.7713365, "longitude": -84.3667376, "google_place_id": null, "google_place_attribution": [], "description": "Whiplash Comedy at Ponce City Market in Atlanta."}'::jsonb THEN
        RETURN; -- Exact reviewed state: replay is a no-op.
    END IF;
    IF reviewed_state IS DISTINCT FROM '{"address": "702 Union St, Brooklyn, NY 11215, USA", "city": "Brooklyn", "state": "NY", "zip_code": "", "latitude": 40.6760744, "longitude": -73.98008229999999, "google_place_id": "ChIJ43tYfapbwokRnkJq38aBk_M", "google_place_attribution": [{"uri": "https://maps.google.com/maps/contrib/100961615764141736810", "photoUri": "https://lh3.googleusercontent.com/a-/ALV-UjWQ6YRLsgvPUoPGhwKEq81iBgHR71sZ1d9GOFJi-ETgKfdaW1t6=s100-p-k-no-mo", "displayName": "Union Hall"}], "description": "Updated by TASK-3029: city/state components parsed from Google Places-backed address"}'::jsonb
       OR current_club->>'has_image' IS DISTINCT FROM 'false'
       OR EXISTS (SELECT 1 FROM club_image_assets WHERE club_id = 1347) THEN
        RAISE EXCEPTION 'TASK-4067: reviewed before-image changed; refusing to overwrite';
    END IF;
    UPDATE clubs SET
        address = '650 North Avenue NE, Suite S210, Atlanta, GA 30308, USA',
        city = 'Atlanta',
        state = 'GA',
        zip_code = '30308',
        latitude = 33.7713365,
        longitude = -84.3667376,
        google_place_id = NULL,
        google_place_attribution = '[]'::jsonb,
        description = 'Whiplash Comedy at Ponce City Market in Atlanta.'
    WHERE id = 1347;
END
$task4067$;
