-- Hide Stand Up Live Huntsville (club 503) — duplicate of Huntsville Levity Live (club 28)
-- Venue rebranded from Stand Up Live to Levity Live; already tracked as club 28 with live_nation scraper (58 total shows);
-- SeatEngine venue 479 returns 404 (v1 and v2); 0 total shows on this record
UPDATE "clubs"
SET visible = false
WHERE id = 503;
