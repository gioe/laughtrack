-- Onboard Westside Improv Studio via Squarespace products collection — TASK-2971 / TASK-3012
--
-- Westside Improv Studio (125 W Front St, Wheaton, IL) is an all-comedy improv
-- venue that sells each show as a dated Squarespace STORE product
-- (collection typeName='products', at /tickets) rather than an Events
-- collection — so GetItemsByMonth returns []. The squarespace scraper now
-- supports a products-collection mode (TASK-3012): scraping_url is the
-- collection page and metadata.collection_type='products' opts in. The show
-- date is parsed from each product's fullUrl slug (/tickets/p/june-19-2026)
-- and the time from the title (@8pm).
--
-- Verified: real scrape returned 6 shows.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Westside Improv Studio', '125 W Front St, Wheaton, IL 60187', 'http://westsideimprov.com/', 'Wheaton', 'IL', '60187', 'America/Chicago', 'US', 'club', 'ChIJQ3p9hYpUDogRYn5wAC7dZKc', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Westside Improv Studio');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'squarespace'::"ScrapingPlatform", 'squarespace', 'https://westsideimprov.com/tickets', 0, TRUE, '{"collection_type": "products"}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Westside Improv Studio'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'squarespace');
