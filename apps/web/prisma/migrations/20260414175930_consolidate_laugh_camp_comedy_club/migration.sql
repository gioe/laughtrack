-- Consolidate duplicate Laugh Camp Comedy Club entries
-- Club 114 (seatengine_classic, ID 537) and club 576 (seatengine, ID 556) are the same venue
-- at 490 N Robert St, Saint Paul, MN. Keep club 114 (more complete metadata, longer history)
-- but upgrade it to the newer seatengine scraper with venue ID 556 (returns 52 shows vs 22).
-- Hide club 576 as the duplicate.

-- Upgrade club 114 to newer seatengine scraper and venue ID
UPDATE "clubs"
SET scraper = 'seatengine',
    seatengine_id = '556'
WHERE id = 114;

-- Hide the duplicate (club 576)
UPDATE "clubs"
SET visible = false
WHERE id = 576;
