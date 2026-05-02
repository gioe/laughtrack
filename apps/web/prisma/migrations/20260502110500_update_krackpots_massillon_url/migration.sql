-- Update Krackpots Comedy Club, Massillon (club 548) to canonical live SeatEngine site.
-- The previous krackpotscomedyclub.com domain no longer resolves; krackpotscomedy.com
-- serves the active public schedule.

UPDATE clubs
SET website = 'https://www.krackpotscomedy.com/'
WHERE id = 548;

UPDATE scraping_sources
SET source_url = 'https://www.krackpotscomedy.com/'
WHERE club_id = 548
  AND enabled IS TRUE;
