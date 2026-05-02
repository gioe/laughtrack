-- Hide Laugh And Enjoy (club 602) while the venue is pending grand opening.
-- The official site is live and powered by SeatEngine v3, but its rendered
-- EventsList GraphQL response returns no events and the page says
-- "*** GRAND OPENING COMING SOON ***".
UPDATE clubs
SET visible = false,
    status = 'active',
    country = 'US'
WHERE id = 602;

-- Keep the verified SeatEngine v3 source enabled; disable the stale classic
-- fallback to avoid noisy zero-show retries.
UPDATE scraping_sources
SET enabled = false,
    updated_at = NOW()
WHERE club_id = 602
  AND platform = 'seatengine'::"ScrapingPlatform"
  AND priority = 0;

UPDATE scraping_sources
SET scraper_key = 'seatengine_v3',
    external_id = 'c91f790c-4cb1-41cd-84fc-bee3b91a0b61',
    source_url = 'https://www.laughandenjoy.com',
    enabled = true,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 602
  AND platform = 'seatengine_v3'::"ScrapingPlatform"
  AND priority = 0;
