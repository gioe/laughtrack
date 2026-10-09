-- TASK-4145: reuse Hartford's canonical venue and public Rockhouse calendar.
-- Preserve the disabled per-venue Ticketmaster source and national-feed identity.
UPDATE clubs
SET website = 'https://hartford.funnybone.com', timezone = 'America/New_York'
WHERE id = 4904;

-- The sole upcoming aggregate show was interpreted as GMT. The official
-- calendar confirms October 29 at 7pm Eastern (23:00 UTC). Repair in place
-- before direct ingestion so its existing ticket/click/lineup references survive.
UPDATE shows
SET date = TIMESTAMPTZ '2026-10-29 23:00:00+00'
WHERE id = 4942927 AND club_id = 4904
  AND show_page_url = 'https://www.ticketmaster.com/event/Z7r9jZ1A70z79'
  AND date = TIMESTAMPTZ '2026-10-29 19:00:00+00';

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT id, 'etix'::"ScrapingPlatform", 'etix',
       'https://hartford.funnybone.com/shows/', 0, TRUE,
       '{"excluded_event_titles":["Hocus Pocus Tribute Drag Brunch","Dolly Parton Hard Candy Christmas Tribute Drag Brunch"]}'::jsonb
FROM clubs WHERE id = 4904
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();
