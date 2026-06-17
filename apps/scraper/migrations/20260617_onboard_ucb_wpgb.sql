-- Onboard Upright Citizens Brigade's WP Grid Builder show listing.
--
-- The current UCB site exposes LA show cards under location facets
-- la-franklin and la-annex. TASK-2951's 8823 row was discovered as UCB
-- Sunset at 2829 Sunset, but ucbcomedy.com no longer exposes a Sunset facet;
-- the live second LA venue is UCB Annex, so keep the existing club row and
-- bind it to the non-Franklin LA facet rather than importing Franklin shows
-- into both clubs.

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
VALUES
    (8823, 'custom'::"ScrapingPlatform", 'ucb', 'https://ucbcomedy.com/shows/', 0, TRUE, '{"location_slug":"la-annex"}'::jsonb),
    (8834, 'custom'::"ScrapingPlatform", 'ucb', 'https://ucbcomedy.com/shows/', 0, TRUE, '{"location_slug":"la-franklin"}'::jsonb)
ON CONFLICT DO NOTHING;

UPDATE clubs
   SET visible = TRUE,
       website = 'https://ucbcomedy.com',
       scraping_url = 'https://ucbcomedy.com/shows/'
 WHERE id IN (8823, 8834);
