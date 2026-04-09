-- Remove duplicate/junk Helium and Goodnights club entries
-- Club 224 (Helium & Elements Restaurant) is a duplicate of Club 132 (Helium & Elements Restaurant - Buffalo)
-- All 121 shows on club 224 are exact duplicates of shows already on club 132 (same date+room)
-- Clubs 209, 210, 226, 266 are duplicate "Store" entries with no shows
-- Club 318 (Helium) points at laketheatercafe.com — wrong venue entirely, no shows

-- Step 1: Delete club 224's show-dependent records (lineup_items, tickets) then shows
DELETE FROM lineup_items WHERE show_id IN (SELECT id FROM shows WHERE club_id = 224);
DELETE FROM tickets WHERE show_id IN (SELECT id FROM shows WHERE club_id = 224);
DELETE FROM shows WHERE club_id = 224;

-- Step 2: Delete other dependent records for all 6 clubs
DELETE FROM tagged_clubs WHERE club_id IN (209, 210, 224, 226, 266, 318);
DELETE FROM email_subscriptions WHERE club_id IN (209, 210, 224, 226, 266, 318);
DELETE FROM processed_emails WHERE club_id IN (209, 210, 224, 226, 266, 318);

-- Step 3: Delete the duplicate clubs
DELETE FROM clubs WHERE id IN (209, 210, 224, 226, 266, 318);
