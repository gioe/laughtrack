-- Remove duplicate Elmwood Commons Playhouse Theater (club 525)
-- This is a duplicate of club 105 ("Elmwood Commons Theater") which is already
-- visible and working with seatengine_id=447 (4 upcoming shows).
-- Club 525 used stale seatengine_id=501 (returning 0 shows) and was already hidden.
-- Safe to delete: club had visible=false, 0 shows, and 0 associated records.
DELETE FROM "clubs" WHERE id = 525;

-- Backfill location details for the real venue (club 105)
UPDATE "clubs"
SET city = 'Kenmore', state = 'NY', zip_code = '14217', address = '3200 Elmwood Ave'
WHERE id = 105 AND city IS NULL;
