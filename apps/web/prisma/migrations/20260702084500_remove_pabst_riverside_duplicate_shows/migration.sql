-- Remove duplicate Live Nation artifacts moved from the closed Riverside
-- Theatre - WI row. These overlap existing Pabst Theater Group Riverside rows
-- with fuller titles and venue-owned purchase URLs.

DO $$
DECLARE
    duplicate_count integer;
BEGIN
    SELECT count(*)
    INTO duplicate_count
    FROM shows
    WHERE id IN (3508706, 3399256, 3508708)
      AND club_id = 9123
      AND show_page_url ILIKE 'https://www.ticketmaster.com/event/%';

    IF duplicate_count <> 3 THEN
        RAISE EXCEPTION 'Expected 3 migrated Pabst Riverside duplicate shows, found %', duplicate_count;
    END IF;
END $$;

DELETE FROM shows
WHERE id IN (3508706, 3399256, 3508708)
  AND club_id = 9123
  AND show_page_url ILIKE 'https://www.ticketmaster.com/event/%';

UPDATE clubs c
SET total_shows = counts.show_count
FROM (
    SELECT club_id, count(*)::integer AS show_count
    FROM shows
    WHERE club_id = 9123
    GROUP BY club_id
) counts
WHERE c.id = counts.club_id;
