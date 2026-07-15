-- Combine The PIT's authoritative PatronTicket inventory with WordPress-only
-- cash, jam, and open-mic events from its existing events feed.
UPDATE scraping_sources AS source
SET scraper_key = 'the_pit',
    source_url = 'https://thepit-nyc.com/events/feed/',
    metadata = COALESCE(source.metadata, '{}'::jsonb) || jsonb_build_object(
        'patronticket_source_url', 'https://thepit.my.salesforce-sites.com/ticket',
        'patronticket_venue_id', 'a0T1I000009YHXGUA4',
        'patronticket_categories', '*'
    ),
    updated_at = NOW()
FROM clubs AS club
WHERE source.club_id = club.id
  AND (
      club.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
      OR (club.name = 'The PIT' AND club.city = 'New York' AND club.state = 'NY')
  )
  AND source.platform = 'custom'::"ScrapingPlatform"
  AND source.priority = 0
  AND source.scraper_key IN ('json_ld', 'the_pit');
