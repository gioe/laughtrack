-- Switch Toledo Funny Bone from Ticketmaster national discovery to its
-- venue-owned Funny Bone / Rockhouse public Etix listing.
--
-- Ticketmaster only exposes sparse inventory for this venue. The official
-- https://toledo.funnybone.com/shows/ page exposes the full Rockhouse Partners
-- event list with Etix ticket URLs, including Preacher Lawson's October 2026
-- run. The generic etix scraper handles this public-source shape directly.

UPDATE clubs
   SET website = 'https://toledo.funnybone.com',
       visible = TRUE,
       status = 'active',
       club_type = 'club',
       timezone = 'America/New_York'
 WHERE id = 4504
    OR lower(name) = lower('Toledo Funny Bone');

UPDATE scraping_sources s
   SET platform = 'etix'::"ScrapingPlatform",
       scraper_key = 'etix',
       source_url = 'https://toledo.funnybone.com/shows/',
       ticketmaster_id = NULL,
       enabled = TRUE,
       priority = 0,
       metadata = '{}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND (c.id = 4504 OR lower(c.name) = lower('Toledo Funny Bone'))
   AND s.priority = 0;
