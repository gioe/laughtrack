-- Mark Jokesters Comedy Club (club 406) as on hiatus.
-- The official site states Jokesters is currently on hiatus and directs visitors
-- to Delirious Comedy Club instead, so the stale SeatEngine source should not
-- continue to run in nightly scraping.
UPDATE clubs
SET website = 'https://www.jokesterslasvegas.com',
    visible = false,
    status = 'hiatus'
WHERE id = 406;

UPDATE scraping_sources
SET enabled = false,
    source_url = 'https://edea24db-12b3-47f8-9132-fe8cb8b9433b.seatengine.com',
    updated_at = NOW()
WHERE club_id = 406
  AND platform = 'seatengine'::"ScrapingPlatform"
  AND priority = 0;
