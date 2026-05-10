-- Backfill Comedy Cellar New York titles after scraper-side normalization.
-- Scope is restricted to the Comedy Cellar scraper/source so other venues that
-- intentionally encode the time in the title are not touched.
UPDATE shows AS s
SET name = regexp_replace(
    s.name,
    '^[[:space:]]*[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)[[:space:]]+',
    '',
    'i'
)
FROM clubs AS c
WHERE s.club_id = c.id
  AND s.name ~* '^[[:space:]]*[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)[[:space:]]+'
  AND (
    c.website ILIKE '%comedycellar.com%'
    OR c.name IN ('Comedy Cellar', 'Comedy Cellar New York')
    OR EXISTS (
      SELECT 1
      FROM scraping_sources AS ss
      WHERE ss.club_id = c.id
        AND (
          ss.scraper_key IN ('comedy_cellar', 'comedy_cellar_email')
          OR ss.source_url ILIKE '%comedycellar.com%'
        )
    )
  );
