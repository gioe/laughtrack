-- Update CAPA's configured scrape/discovery URL to the public comedy-filtered
-- calendar page supplied during follow-up onboarding review. The generic
-- tessitura scraper derives the WordPress REST API origin from this URL, so the
-- filtered calendar URL remains a stable human-facing source pointer while the
-- scraper continues to fetch /wp-json/wp/v2 genre-filtered comedy productions.

UPDATE scraping_sources
SET source_url = 'https://www.capa.com/event-calendar/?term_genre%5B%5D=comedy&start_date=2026-07-01&end_date=',
    updated_at = now()
WHERE scraper_key = 'tessitura'
  AND source_url = 'https://www.capa.com'
  AND club_id IN (
      SELECT id
      FROM clubs
      WHERE name = 'CAPA (Columbus)'
        AND website = 'https://www.capa.com'
  );
