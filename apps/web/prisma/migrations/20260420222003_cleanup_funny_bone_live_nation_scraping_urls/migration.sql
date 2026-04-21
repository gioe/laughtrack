-- Replace the stale etix.com scraping_url on the 9 Funny Bones that run on
-- scraper='live_nation' (TicketmasterScraper). The chain migration
-- 20260420161847_migrate_funny_bone_chain_to_ticketmaster moved these venues
-- to Ticketmaster but left the pre-existing etix.com scraping_url in place.
--
-- TicketmasterScraper overrides discover_urls() to return an app.ticketmaster.com
-- endpoint computed from club.ticketmaster_id and never reads scraping_url, so
-- the stale etix URL has no functional effect — but it's misleading when
-- auditing the clubs table and caused confusion during TASK-1691 triage.
--
-- The scraping_url column is NOT NULL, so we replace with the public
-- Ticketmaster venue page URL (which mirrors the actual API target). Guards
-- on scraper, ticketmaster_id, and the LIKE clause make this idempotent and
-- scope-safe even if IDs drift.

UPDATE clubs
SET scraping_url = 'https://www.ticketmaster.com/venue/' || ticketmaster_id
WHERE id IN (308, 317, 323, 1026, 1027, 1028, 1030, 1034, 1050)
  AND scraper = 'live_nation'
  AND ticketmaster_id IS NOT NULL
  AND scraping_url LIKE '%etix.com%';
