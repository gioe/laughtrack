-- TASK-4075: three NULL backfills and one independently verified Las Vegas correction.
-- Evidence: apps/scraper/docs/audits/2026-09-30-remaining-venue-timezones/.
-- No show timestamps, identity metadata or related records change.
DO $repair$
DECLARE target record; actual record;
BEGIN
 FOR target IN SELECT * FROM jsonb_to_recordset($targets$[{"id":22761,"name":"Cork It Gainesville (located inside of Main Street Market)","address":"118 Main St","zip_code":"30506","visible":true,"timezone":null,"new_timezone":"America/New_York"},{"id":45259,"name":"Pinfish Entertainment","address":"91214 Overseas Highway","zip_code":"33070","visible":true,"timezone":null,"new_timezone":"America/New_York"},{"id":56972,"name":"Spymaker Axe Throwing","address":"1235 S Center Rd.","zip_code":"48509","visible":true,"timezone":null,"new_timezone":"America/Detroit"},{"id":4552,"name":"The Empire Strips Back Theater","address":"3700 W Flamingo Rd, Las Vegas, NV","zip_code":"89103","visible":true,"timezone":"America/Vancouver","new_timezone":"America/Los_Angeles"}]$targets$::jsonb)
 AS x(id integer,name text,address text,zip_code text,visible boolean,timezone text,new_timezone text)
 ORDER BY id LOOP
  SELECT * INTO actual FROM clubs WHERE id=target.id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'TASK-4075 missing venue %',target.id; END IF;
  IF actual.name IS DISTINCT FROM target.name OR actual.address IS DISTINCT FROM target.address
   OR actual.zip_code IS DISTINCT FROM target.zip_code OR actual.visible IS DISTINCT FROM target.visible
  THEN RAISE EXCEPTION 'TASK-4075 identity drift %',target.id; END IF;
  IF actual.timezone IS NOT DISTINCT FROM target.new_timezone THEN CONTINUE; END IF;
  IF actual.timezone IS DISTINCT FROM target.timezone THEN
   RAISE EXCEPTION 'TASK-4075 timezone drift %',target.id;
  END IF;
  UPDATE clubs SET timezone=target.new_timezone WHERE id=target.id;
 END LOOP;
END
$repair$;
