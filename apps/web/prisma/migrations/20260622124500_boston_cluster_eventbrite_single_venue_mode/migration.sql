-- TASK-3151 correction: switch three Boston-cluster Eventbrite sources from
-- organizer mode (source_url contains /o/) to SINGLE-VENUE mode (source_url =
-- https://www.eventbrite.com, organizer id kept in eventbrite_id).
--
-- The eventbrite scraper treats an "/o/<id>" source_url as an ORGANIZER feed and
-- fans every event out to an auto-created per-venue club keyed on the event's
-- venue name. For these three single-physical-venue organizers that produced
-- duplicate/split clubs (e.g. "The White Bull Tavern" + "The White Bull Tavern
-- Comedy Club Boston"; "Providence Comedy Underground" + "The George on
-- Washington St."). Single-venue mode attaches every Show to the one onboarded
-- club instead. The duplicate auto-clubs were removed on the live DB; on a fresh
-- DB this UPDATE runs before any scrape so the split never happens.
--
--   26813798849 = The White Bull Tavern (Hideout Comedy)
--   59005476163 = Stand Up Stick Up Comedy Club (Lynn Music Foundation / Vault Theatre)
--   31203223233 = Providence Comedy Underground (The George / Hide Speakeasy)

UPDATE scraping_sources
SET source_url = 'https://www.eventbrite.com'
WHERE scraper_key = 'eventbrite'
  AND eventbrite_id IN ('26813798849', '59005476163', '31203223233')
  AND source_url LIKE '%/o/%';
