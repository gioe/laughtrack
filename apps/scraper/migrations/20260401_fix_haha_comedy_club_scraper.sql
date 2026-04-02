-- TASK-868: Switch HAHA Comedy Club to the new haha_comedy_club scraper
-- Tixr's DataDome WAF blocks GitHub Actions IP ranges, causing 31/31 (100%)
-- HTTP 403 failures on per-event Tixr page fetches in the 2026-04-01 run.
-- The new haha_comedy_club scraper extracts all show data (name, date+time,
-- performer, ticket URL, availability) directly from the venue's calendar page
-- HTML (hahacomedyclub.com/calendar), which embeds JSON-LD Event blocks and
-- visible start-time elements. No Tixr page fetches required.

UPDATE clubs
SET scraper = 'haha_comedy_club'
WHERE name = 'HAHA Comedy Club';
