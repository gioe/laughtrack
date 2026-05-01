-- Broadway Comedy Club moved its Tessera-backed listing from /shows to /calendar/.
UPDATE scraping_sources ss
SET source_url = 'https://www.broadwaycomedyclub.com/calendar/'
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'The Broadway Comedy Club'
  AND ss.platform = 'custom'
  AND ss.scraper_key = 'broadway';
