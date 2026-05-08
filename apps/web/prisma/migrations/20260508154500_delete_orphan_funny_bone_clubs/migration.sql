-- TASK-2042: Delete two orphan Funny Bone club rows that duplicate canonical chain_id=3 venues.
-- Expected canonical replacements:
-- - 310  -> 1033 Virginia Beach Funny Bone
-- - 1037 -> 308  Funny Bone Columbus

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id IN (310, 1037)
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id IN (310, 1037)
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id IN (310, 1037)
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id IN (310, 1037)
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id IN (310, 1037)
    ) THEN
        RAISE EXCEPTION 'Cannot delete orphan Funny Bone clubs 310/1037: dependent rows still exist';
    END IF;
END $$;

DELETE FROM scraping_sources
WHERE club_id IN (310, 1037);

DELETE FROM clubs
WHERE id IN (310, 1037);
