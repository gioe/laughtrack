-- TASK-4070: quarantine a multi-location promoter misidentified as Laugh Tour.
-- Preserve all historical references and source identity; never denylist Laugh Tour.
-- Only captured field transitions are allowed; source updated_at is trigger-maintained.
-- Operator rollback restores the known-bad preimage; use deliberately.
DO $task4070rollback$
DECLARE c clubs%ROWTYPE; s scraping_sources%ROWTYPE;
BEGIN
    PERFORM set_config('TimeZone','UTC',true);
    LOCK TABLE clubs, scraping_sources IN SHARE ROW EXCLUSIVE MODE;
    SELECT * INTO c FROM clubs WHERE id=855 FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT * INTO STRICT s FROM scraping_sources WHERE id=294 FOR UPDATE;
    IF NOT (to_jsonb(c) @> '{"id":855,"name":"Laugh Tonight Comedy","country":"US","timezone":"America/New_York","zip_code":"","status":"active","closed_at":null}'::jsonb)
       OR EXISTS (SELECT 1 FROM scraping_sources WHERE club_id=855 AND id<>294 AND enabled) THEN
        RAISE EXCEPTION 'TASK-4070 identity/source-owner guard failed';
    END IF;
    IF (SELECT jsonb_object_agg(k,to_jsonb(c)->k) FROM unnest(ARRAY['address','city','state','latitude','longitude','google_place_id','visible','club_type','has_image','website','description']) k) = '{"address":"Inside Dorrian''s Restaurant Outside Newport Mall, 555 Washington Blvd, Jersey City, NJ 07310, USA","city":"Jersey City","state":"NJ","latitude":40.7280954,"longitude":-74.034928,"google_place_id":"ChIJ369ARGdXwokRVCaKcxyCCBw","visible":true,"club_type":"club","has_image":true,"website":"http://www.laughtonightcomedy.com","description":"<p>Laugh Tonight Comedy </p><p>Cornerstone Center For The Arts</p><p>520 E Main Street</p><p>Muncie IN 47305</p>\n\nUpdated by TASK-3029: city/state components parsed from Google Places-backed address"}'::jsonb AND (to_jsonb(s)-'updated_at') = ('{"id":294,"club_id":855,"platform":"seatengine","scraper_key":"seatengine","source_url":"http://www.laughtonightcomedy.com","priority":0,"enabled":true,"metadata":{"task_1984_canonical_pointer":{"kind":"same_venue_dupe_canonical","pattern":"C","platform":"seatengine","rationale":"This row is the canonical for the same-venue duplicate-club pair resolved by TASK-1984. The duplicate club 449 (''Laugh Tonight Comedy @ Laugh Factory'') was hidden and its scraping_source 279 had its seatengine typed id cleared.","dupe_club_id":449,"typed_id_kept":424,"dupe_source_id":279}},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T23:21:47.875641+00:00","seatengine_id":424,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb-'updated_at') THEN RETURN; END IF;
    IF NOT ((SELECT jsonb_object_agg(k,to_jsonb(c)->k) FROM unnest(ARRAY['address','city','state','latitude','longitude','google_place_id','visible','club_type','has_image','website','description']) k) = '{"address":"","city":null,"state":null,"latitude":null,"longitude":null,"google_place_id":null,"visible":false,"club_type":"producer","has_image":false,"website":"https://www.laughtonightcomedy.com","description":"Laugh Tonight Comedy is a multi-location comedy promoter. SeatEngine account 424 includes events in Muncie and Chicago. No single physical venue address is verified. Source quarantined pending event-level venue routing (TASK-4070; TASK-4109)."}'::jsonb AND (to_jsonb(s)-'updated_at') = ('{"id":294,"club_id":855,"platform":"seatengine","scraper_key":"seatengine","source_url":"http://www.laughtonightcomedy.com","priority":0,"enabled":false,"metadata":{"task_1984_canonical_pointer":{"kind":"same_venue_dupe_canonical","pattern":"C","platform":"seatengine","rationale":"This row is the canonical for the same-venue duplicate-club pair resolved by TASK-1984. The duplicate club 449 (''Laugh Tonight Comedy @ Laugh Factory'') was hidden and its scraping_source 279 had its seatengine typed id cleared.","dupe_club_id":449,"typed_id_kept":424,"dupe_source_id":279},"task_4070_disposition":{"reason":"multi_location_promoter_wrong_physical_identity","routing_task":"TASK-4109","before_club_fields":{"address":"Inside Dorrian''s Restaurant Outside Newport Mall, 555 Washington Blvd, Jersey City, NJ 07310, USA","city":"Jersey City","state":"NJ","latitude":40.7280954,"longitude":-74.034928,"google_place_id":"ChIJ369ARGdXwokRVCaKcxyCCBw","visible":true,"club_type":"club","has_image":true,"website":"http://www.laughtonightcomedy.com","description":"<p>Laugh Tonight Comedy </p><p>Cornerstone Center For The Arts</p><p>520 E Main Street</p><p>Muncie IN 47305</p>\n\nUpdated by TASK-3029: city/state components parsed from Google Places-backed address"},"before_source":{"id":294,"club_id":855,"platform":"seatengine","scraper_key":"seatengine","source_url":"http://www.laughtonightcomedy.com","priority":0,"enabled":true,"metadata":{"task_1984_canonical_pointer":{"kind":"same_venue_dupe_canonical","pattern":"C","platform":"seatengine","rationale":"This row is the canonical for the same-venue duplicate-club pair resolved by TASK-1984. The duplicate club 449 (''Laugh Tonight Comedy @ Laugh Factory'') was hidden and its scraping_source 279 had its seatengine typed id cleared.","dupe_club_id":449,"typed_id_kept":424,"dupe_source_id":279}},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T23:21:47.875641+00:00","seatengine_id":424,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}}},"created_at":"2026-04-21T19:57:12.315022+00:00","updated_at":"2026-05-06T23:21:47.875641+00:00","seatengine_id":424,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb-'updated_at')) THEN
        RAISE EXCEPTION 'TASK-4070 snapshot guard failed; re-audit before changing data';
    END IF;
    UPDATE clubs SET address = 'Inside Dorrian''s Restaurant Outside Newport Mall, 555 Washington Blvd, Jersey City, NJ 07310, USA',
        city = 'Jersey City',
        state = 'NJ',
        latitude = 40.7280954,
        longitude = -74.034928,
        google_place_id = 'ChIJ369ARGdXwokRVCaKcxyCCBw',
        visible = TRUE,
        club_type = 'club',
        has_image = TRUE,
        website = 'http://www.laughtonightcomedy.com',
        description = '<p>Laugh Tonight Comedy </p><p>Cornerstone Center For The Arts</p><p>520 E Main Street</p><p>Muncie IN 47305</p>

Updated by TASK-3029: city/state components parsed from Google Places-backed address' WHERE id=855;
    UPDATE scraping_sources SET enabled=TRUE, metadata='{"task_1984_canonical_pointer":{"kind":"same_venue_dupe_canonical","pattern":"C","platform":"seatengine","rationale":"This row is the canonical for the same-venue duplicate-club pair resolved by TASK-1984. The duplicate club 449 (''Laugh Tonight Comedy @ Laugh Factory'') was hidden and its scraping_source 279 had its seatengine typed id cleared.","dupe_club_id":449,"typed_id_kept":424,"dupe_source_id":279}}'::jsonb WHERE id=294;
END;
$task4070rollback$;
