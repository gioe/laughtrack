-- TASK-2893: Onboard City Winery Pittsburgh (Pittsburgh, PA), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). City Winery is a national
-- chain that programs "Intimate Concerts & Comedy"; the Pittsburgh location hosts
-- comedy (e.g. Cocoa Brown). It is scraped by the existing generic `city_winery`
-- scraper, which reads the chain's awsapi.citywinery.com/events API filtered by the
-- per-location metadata below (same pattern as the already-onboarded NYC /
-- Philadelphia / St. Louis / Boston locations). Fixed venue → visible=true.
-- Verified 13 comedy shows scraped in prod.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- City Winery Pittsburgh
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'City Winery Pittsburgh', '1627 Smallman St, Pittsburgh, PA 15222, USA', 'https://citywinery.com/pages/locations/pittsburgh', 'Pittsburgh', 'PA', '15222', 'America/New_York', 'US', 'club', 'ChIJB6QRph7zNIgRBnXqHdZ8Onk', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'City Winery Pittsburgh');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'city_winery', 'https://citywinery.com/pages/events/pittsburgh', 0, TRUE,
  jsonb_build_object(
    'genre', 'Comedy',
    'api_url', 'https://awsapi.citywinery.com/events',
    'location', 'Pittsburgh',
    'pagination', 'top=16; increment skip by 16 until total_events exhausted; 404 beyond end is expected',
    'listing_url', 'https://citywinery.com/pages/genre/pittsburgh-comedy',
    'ticket_url_template', 'https://tickets.citywinery.com/event/{url}'
  ),
  now(), now()
FROM clubs c WHERE c.name = 'City Winery Pittsburgh'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'city_winery');
