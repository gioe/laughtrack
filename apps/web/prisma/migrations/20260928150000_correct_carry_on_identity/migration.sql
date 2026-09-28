-- TASK-4066: repair Carry On identity and quarantine non-comedy inventory.
-- The prior Google place is Marshalls & HomeGoods in New Rochelle, not Carry On.
-- Source updated_at is trigger-maintained: guards ignore it, preimages retain it.
-- Keep every show, ticket, lineup, source ID and historical reference intact.
-- Preserve the disabled source with a disposition stamp: SeatEngine discovery
-- otherwise re-enables it. Only the verified Phoenix place is deny-listed.
-- One atomic DO statement; deliberately no BEGIN/COMMIT so rollback-only testing works.
DO $task4066$
DECLARE
    c clubs%ROWTYPE;
    s scraping_sources%ROWTYPE;
    marker jsonb;
    applied_at timestamptz := transaction_timestamp();
BEGIN
    -- Normalize timestamp JSON against the captured UTC preimage.
    PERFORM set_config('TimeZone', 'UTC', true);
    -- Prevent concurrent source insertion / identity edits during the guarded change.
    LOCK TABLE clubs, scraping_sources, venue_deny_list IN SHARE ROW EXCLUSIVE MODE;
    SELECT * INTO STRICT c FROM clubs WHERE id = 600 FOR UPDATE;
    SELECT * INTO STRICT s FROM scraping_sources WHERE id = 336 FOR UPDATE;
    IF NOT (to_jsonb(c) @> '{"id":600,"name":"Carry On","website":"https://www.carryonphx.com","country":"US","status":"active","closed_at":null,"google_place_attribution":null,"hours":null}'::jsonb)
       OR EXISTS (SELECT 1 FROM clubs WHERE id <> 600 AND google_place_id = 'ChIJZTvexEQTK4cRhKU-6MI20DU')
       OR EXISTS (SELECT 1 FROM scraping_sources WHERE club_id = 600 AND id <> 336 AND enabled) THEN
        RAISE EXCEPTION 'TASK-4066 identity, place collision, or enabled-source guard failed';
    END IF;
    marker := s.metadata->'task_4066_disposition';
    IF marker IS NOT NULL THEN
    IF (SELECT jsonb_object_agg(k, to_jsonb(c)->k) FROM unnest(ARRAY['address', 'city', 'state', 'zip_code', 'timezone', 'latitude', 'longitude', 'google_place_id', 'visible', 'club_type', 'description']) k) IS DISTINCT FROM '{"address":"2 N Central Ave #101, Phoenix, AZ 85004, USA","city":"Phoenix","state":"AZ","zip_code":"85004","timezone":"America/Phoenix","latitude":33.4486014,"longitude":-112.0749021,"google_place_id":"ChIJZTvexEQTK4cRhKU-6MI20DU","visible":false,"club_type":"non_comedy","description":"Immersive airline-themed cocktail experience in Phoenix, Arizona; not a comedy venue. Identity verified against the official website and Google Places by TASK-4066."}'::jsonb
       OR (to_jsonb(s) - ARRAY['metadata','enabled','updated_at']) IS DISTINCT FROM
          ('{"id":336,"club_id":600,"platform":"seatengine","scraper_key":"seatengine","source_url":"https://www.carryonphx.com","priority":0,"enabled":true,"metadata":{},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T21:52:53.876643+00:00","seatengine_id":584,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb - ARRAY['metadata','enabled','updated_at'])
       OR s.enabled IS DISTINCT FROM FALSE
       OR (s.metadata - 'task_4066_disposition') IS DISTINCT FROM '{}'::jsonb
       OR marker->'before_club_fields' IS DISTINCT FROM '{"address":"200 Petersville Rd, New Rochelle, NY 10801, USA","city":"New Rochelle","state":"NY","zip_code":"","timezone":"America/New_York","latitude":40.9229986,"longitude":-73.7726003,"google_place_id":"ChIJG0Jn64qNwokRGYoxmO3p3Xk","visible":true,"club_type":"club","description":"Updated by TASK-3029: city/state components parsed from Google Places-backed address"}'::jsonb
       OR ((marker->'before_source') - 'updated_at') IS DISTINCT FROM '{"id":336,"club_id":600,"platform":"seatengine","scraper_key":"seatengine","source_url":"https://www.carryonphx.com","priority":0,"enabled":true,"metadata":{},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T21:52:53.876643+00:00","seatengine_id":584,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb - 'updated_at'
       OR NOT EXISTS (SELECT 1 FROM venue_deny_list d
           WHERE d.google_place_id = 'ChIJZTvexEQTK4cRhKU-6MI20DU'
           AND (to_jsonb(d) - 'denied_at') = '{"google_place_id":"ChIJZTvexEQTK4cRhKU-6MI20DU","name":"Carry On","reason":"Verified immersive cocktail experience, not comedy programming. Official Carry On website and Google Places identify 2 N Central Ave #101, Phoenix, AZ 85004. TASK-4066.","added_by":"TASK-4066","google_primary_type":"cocktail_bar","evidence":{"task":"TASK-4066","club_id":600,"source_id":336,"seatengine_id":584,"official_url":"https://www.carryonphx.com/","incorrect_place_id":"ChIJG0Jn64qNwokRGYoxmO3p3Xk","incorrect_place_identity":"Marshalls & HomeGoods","inventory":"Cocktail experience sessions; no comedy programming","verified_date":"2026-09-28"}}'::jsonb
           AND to_jsonb(d.denied_at) = marker->'applied_at') THEN
        RAISE EXCEPTION 'TASK-4066 complete after-state guard failed; refusing partial replay or rollback';
    END IF;
        RETURN;
    END IF;
    IF (SELECT jsonb_object_agg(k, to_jsonb(c)->k) FROM unnest(ARRAY['address', 'city', 'state', 'zip_code', 'timezone', 'latitude', 'longitude', 'google_place_id', 'visible', 'club_type', 'description']) k) IS DISTINCT FROM '{"address":"200 Petersville Rd, New Rochelle, NY 10801, USA","city":"New Rochelle","state":"NY","zip_code":"","timezone":"America/New_York","latitude":40.9229986,"longitude":-73.7726003,"google_place_id":"ChIJG0Jn64qNwokRGYoxmO3p3Xk","visible":true,"club_type":"club","description":"Updated by TASK-3029: city/state components parsed from Google Places-backed address"}'::jsonb
       OR (to_jsonb(s) - 'updated_at') IS DISTINCT FROM '{"id":336,"club_id":600,"platform":"seatengine","scraper_key":"seatengine","source_url":"https://www.carryonphx.com","priority":0,"enabled":true,"metadata":{},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T21:52:53.876643+00:00","seatengine_id":584,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb - 'updated_at'
       OR EXISTS (SELECT 1 FROM venue_deny_list WHERE google_place_id = 'ChIJZTvexEQTK4cRhKU-6MI20DU') THEN
        RAISE EXCEPTION 'TASK-4066 original snapshot guard failed; re-audit before applying';
    END IF;
    UPDATE clubs SET
        address = '2 N Central Ave #101, Phoenix, AZ 85004, USA',
        city = 'Phoenix',
        state = 'AZ',
        zip_code = '85004',
        timezone = 'America/Phoenix',
        latitude = 33.4486014,
        longitude = -112.0749021,
        google_place_id = 'ChIJZTvexEQTK4cRhKU-6MI20DU',
        visible = FALSE,
        club_type = 'non_comedy',
        description = 'Immersive airline-themed cocktail experience in Phoenix, Arizona; not a comedy venue. Identity verified against the official website and Google Places by TASK-4066.'
    WHERE id = 600;
    UPDATE scraping_sources
       SET enabled = FALSE,
           updated_at = applied_at,
           metadata = metadata || jsonb_build_object('task_4066_disposition',
               jsonb_build_object('reason', 'verified_non_comedy_cocktail_experience',
                   'before_club_fields', '{"address":"200 Petersville Rd, New Rochelle, NY 10801, USA","city":"New Rochelle","state":"NY","zip_code":"","timezone":"America/New_York","latitude":40.9229986,"longitude":-73.7726003,"google_place_id":"ChIJG0Jn64qNwokRGYoxmO3p3Xk","visible":true,"club_type":"club","description":"Updated by TASK-3029: city/state components parsed from Google Places-backed address"}'::jsonb,
                   'before_source', to_jsonb(s), 'applied_at', applied_at))
     WHERE id = 336;
    INSERT INTO venue_deny_list (google_place_id, name, reason, added_by, google_primary_type, evidence, denied_at)
    VALUES ('ChIJZTvexEQTK4cRhKU-6MI20DU', 'Carry On', 'Verified immersive cocktail experience, not comedy programming. Official Carry On website and Google Places identify 2 N Central Ave #101, Phoenix, AZ 85004. TASK-4066.', 'TASK-4066', 'cocktail_bar', '{"task":"TASK-4066","club_id":600,"source_id":336,"seatengine_id":584,"official_url":"https://www.carryonphx.com/","incorrect_place_id":"ChIJG0Jn64qNwokRGYoxmO3p3Xk","incorrect_place_identity":"Marshalls & HomeGoods","inventory":"Cocktail experience sessions; no comedy programming","verified_date":"2026-09-28"}'::jsonb, applied_at);
END;
$task4066$;
