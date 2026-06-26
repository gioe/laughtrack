-- Filter BABS Comedy Club operational closure placeholders.
--
-- SeatEngine emits one daily event titled "*CLOSED FOR CONSTRUCTION 6/22-8/26*".
-- These are not shows, so block future scrape ingestion and remove the rows
-- already persisted from the current run.

UPDATE scraping_sources s
   SET metadata = COALESCE(s.metadata, '{}'::jsonb)
       || '{"exclude_title_patterns": ["closed\\s+for\\s+construction"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.name = 'BABS Comedy Club'
   AND s.platform = 'seatengine'
   AND s.scraper_key = 'seatengine';

DELETE FROM shows sh
 USING clubs c
 WHERE sh.club_id = c.id
   AND c.name = 'BABS Comedy Club'
   AND sh.name ~* 'closed\s+for\s+construction';
