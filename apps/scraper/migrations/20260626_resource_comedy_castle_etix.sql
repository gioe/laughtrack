-- TASK-3379: Re-source Mark Ridley's Comedy Castle (club 4756) from etix.
--
-- Club 4756 (Royal Oak, MI — a major long-running Detroit comedy club) had only
-- 3 upcoming shows because its sole source was ticketmaster_comedy
-- (ticketmaster_id ZFr9jZFF6v), which catches only the handful of TM-listed
-- shows. The venue's own site (comedycastle.com) is an rhp-events WordPress
-- site, but its public /events/ HTML is unreliable to scrape (headliner runs
-- live on per-series pages, like the zanies layout; the generic rhp list
-- mis-aligns title↔ticket). Every "Buy Tickets" button on comedycastle.com
-- routes to etix — etix is the venue's actual ticketing partner.
--
-- The etix venue id is 3536 (https://www.etix.com/ticket/v/3536/...), verified
-- via a real browser: the upcomingEvents/venue endpoint returns the full
-- headliner calendar (Gianmarco Soresi, Christopher Titus, Joe DeVito, Ben
-- Bailey, Mark Normand, Steve Hofstetter, ... — far more than 3). This mirrors
-- the Cleveland Funny Bone (club 1050) ticketmaster->etix re-source.
--
-- The generic etix scraper (scraper_key='etix') needs only a DB row: it parses
-- the venue id out of source_url. We make etix the priority-0 primary and DEMOTE
-- (not delete) ticketmaster_comedy to priority 1, so it remains a fallback if
-- etix is ever unreachable (scrape orchestration runs the lowest-priority
-- enabled source that returns shows, falling through to the next on error/zero).
--
-- Idempotent: re-running demotes the TM row again and inserts-or-updates the
-- single etix priority-0 source.

-- 1. Demote the ticketmaster_comedy source to a priority-1 fallback (keep enabled).
UPDATE scraping_sources s
   SET priority = 1,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 4756
   AND s.platform = 'ticketmaster'::"ScrapingPlatform"
   AND s.scraper_key = 'ticketmaster_comedy';

-- 2. Add the etix source as the primary (priority 0).
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://www.etix.com/ticket/v/3536/mark-ridleys-comedy-castle',
    0,
    TRUE,
    jsonb_build_object(
        'etix_venue_id', '3536',
        'note', 'TASK-3379 re-source: comedycastle.com sells via etix; etix venue 3536 returns the full headliner calendar. ticketmaster_comedy (ZFr9jZFF6v) demoted to priority-1 fallback.'
    )
  FROM clubs c
 WHERE c.id = 4756
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'etix'::"ScrapingPlatform"
   );

UPDATE scraping_sources s
   SET scraper_key = 'etix',
       source_url = 'https://www.etix.com/ticket/v/3536/mark-ridleys-comedy-castle',
       priority = 0,
       enabled = TRUE,
       metadata = jsonb_build_object(
           'etix_venue_id', '3536',
           'note', 'TASK-3379 re-source: comedycastle.com sells via etix; etix venue 3536 returns the full headliner calendar. ticketmaster_comedy (ZFr9jZFF6v) demoted to priority-1 fallback.'
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 4756
   AND s.platform = 'etix'::"ScrapingPlatform";
