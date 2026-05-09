-- TASK-2094: backfill future shows whose last_scraped_by stayed NULL after
-- 20260509120000_add_shows_last_scraped_by.
--
-- Root cause: these are legacy rows written before shows.last_scraped_by
-- existed. The newest affected last_scraped_date observed during the audit was
-- 2026-05-08; no future NULL-attributed row had last_scraped_date on or after
-- 2026-05-09 12:00 UTC, when the attribution migration/code path landed.

-- Most rows can be attributed directly: if a club has exactly one enabled
-- scraping source, that source is the only current writer for that club.
WITH eligible_sources AS (
    SELECT
        club_id,
        MIN(scraper_key) AS scraper_key
    FROM scraping_sources
    WHERE enabled = TRUE
      AND scraper_key IS NOT NULL
    GROUP BY club_id
    HAVING COUNT(*) = 1
)
UPDATE shows AS s
SET last_scraped_by = es.scraper_key
FROM eligible_sources AS es
WHERE s.club_id = es.club_id
  AND s.date > NOW()
  AND s.last_scraped_by IS NULL;

-- A handful of pre-scraping_sources organizer venues had no active
-- scraping_sources row, but their original onboarding migrations and URLs make
-- Eventbrite attribution unambiguous.
UPDATE shows AS s
SET last_scraped_by = 'eventbrite'
FROM clubs AS c
WHERE c.id = s.club_id
  AND c.name IN (
      'Backdoor Comedy Club',
      'Big Couch',
      'Comedy At The Comet',
      'Improbable Comedy',
      'The Riot Comedy Club'
  )
  AND s.date > NOW()
  AND s.last_scraped_by IS NULL
  AND s.show_page_url ~* '(?:^|//)(?:www\.)?eventbrite\.com/';

-- Club 826 is the legacy "The Comedy Club On State" row. Its Madison URL
-- was adopted to the json_ld scraper before the duplicate was superseded by
-- the canonical Comedy on State club.
UPDATE shows AS s
SET last_scraped_by = 'json_ld'
FROM clubs AS c
WHERE c.id = s.club_id
  AND c.name = 'The Comedy Club On State'
  AND s.date > NOW()
  AND s.last_scraped_by IS NULL
  AND s.show_page_url ~* '(?:^|//)(?:www\.)?madisoncomedy\.com/';

-- Remaining no-source rows are hidden non-comedy/test/duplicate venues. They
-- are not current scraper output and should not remain as future listings.
DELETE FROM shows AS s
USING clubs AS c
WHERE c.id = s.club_id
  AND c.visible = FALSE
  AND c.name IN (
      'All American Magic Theater',
      'BoatYard Lake Norman',
      'Chris'' Jazz Cafe',
      'Comedy in Harlem',
      'Lotus Education & Arts Foundation',
      'Mobile Test Venue',
      'Rosa''s Lounge'
  )
  AND s.date > NOW()
  AND s.last_scraped_by IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources AS ss
      WHERE ss.club_id = c.id
        AND ss.enabled = TRUE
        AND ss.scraper_key IS NOT NULL
  );
