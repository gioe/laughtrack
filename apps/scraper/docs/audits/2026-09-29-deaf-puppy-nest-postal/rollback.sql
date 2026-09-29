-- Manual recovery only: restores the original missing values and removes these venues from ZIP discovery.
-- TASK-4071: operator rollback of independently verified postal values.
-- Evidence: apps/scraper/docs/audits/2026-09-29-deaf-puppy-nest-postal/evidence.md
-- Only zip_code is changed; preserve every other field and historical reference.
-- Source updated_at is trigger-maintained and not part of the ownership guard.
DO $task4071$
DECLARE current_club jsonb; current_source jsonb;
BEGIN
    PERFORM set_config('TimeZone','UTC',true);

    SELECT to_jsonb(c) INTO current_club FROM clubs c WHERE id=551 FOR UPDATE;
    IF current_club IS NOT NULL THEN
        IF NOT (current_club @> '{"id":551,"name":"Deaf Puppy Comedy Club","address":"127 N Main St, Manteca, CA 95336, USA","website":"Http://www.deafpuppyclub.com","city":"Manteca","state":"CA","country":"US","latitude":37.7980935,"longitude":-121.2168019,"google_place_id":"ChIJ56C9BrpBkIARwR05O3V4F3M"}'::jsonb) THEN
            RAISE EXCEPTION 'TASK-4071: club 551 identity changed; re-audit required';
        END IF;
        SELECT to_jsonb(ss)-'updated_at' INTO current_source
          FROM scraping_sources ss WHERE id=594 FOR UPDATE;
        IF current_source IS DISTINCT FROM '{"id":594,"club_id":551,"platform":"seatengine","scraper_key":"seatengine","source_url":"Http://www.deafpuppyclub.com","priority":0,"enabled":true,"metadata":{},"created_at":"2026-04-21T19:57:12.315022+00:00","seatengine_id":531,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb THEN
            RAISE EXCEPTION 'TASK-4071: club 551 source changed; re-audit required';
        END IF;
        IF current_club->'zip_code' IS NOT DISTINCT FROM '""'::jsonb THEN
            NULL; -- Already at exact original missing value.
        ELSIF current_club->>'zip_code' = '95336' THEN
            UPDATE clubs SET zip_code='' WHERE id=551;
        ELSE
            RAISE EXCEPTION 'TASK-4071: club 551 postal changed after repair; refuse rollback';
        END IF;
    END IF;

    SELECT to_jsonb(c) INTO current_club FROM clubs c WHERE id=8713 FOR UPDATE;
    IF current_club IS NOT NULL THEN
        IF NOT (current_club @> '{"id":8713,"name":"The Nest Theatre","address":"2643 N High St, Columbus, OH 43202, USA","website":"https://nesttheatre.com/","city":"Columbus","state":"OH","country":"US","latitude":40.016155999999995,"longitude":-83.0122253,"google_place_id":"ChIJe4VjWzaPOIgRjuXnR1D1PQA"}'::jsonb) THEN
            RAISE EXCEPTION 'TASK-4071: club 8713 identity changed; re-audit required';
        END IF;
        SELECT to_jsonb(ss)-'updated_at' INTO current_source
          FROM scraping_sources ss WHERE id=5863 FOR UPDATE;
        IF current_source IS DISTINCT FROM '{"id":5863,"club_id":8713,"platform":"custom","scraper_key":"vbo_tickets","source_url":"https://plugin.vbotickets.com/plugin/loadplugin?siteid=5D584EB6-2A49-4AFD-9430-259D26127F0B&page=ListEvents","priority":0,"enabled":true,"metadata":{"category_filter":"Live Shows"},"created_at":"2026-06-16T01:16:04.338331+00:00","seatengine_id":null,"eventbrite_id":null,"ticketmaster_id":null,"wix_event_id":null,"ovationtix_id":null,"squadup_id":null,"seatengine_v3_id":null,"source_target_id":null}'::jsonb THEN
            RAISE EXCEPTION 'TASK-4071: club 8713 source changed; re-audit required';
        END IF;
        IF current_club->'zip_code' IS NOT DISTINCT FROM 'null'::jsonb THEN
            NULL; -- Already at exact original missing value.
        ELSIF current_club->>'zip_code' = '43202' THEN
            UPDATE clubs SET zip_code=NULL WHERE id=8713;
        ELSE
            RAISE EXCEPTION 'TASK-4071: club 8713 postal changed after repair; refuse rollback';
        END IF;
    END IF;
END;
$task4071$;
