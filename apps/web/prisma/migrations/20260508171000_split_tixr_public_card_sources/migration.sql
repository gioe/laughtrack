-- Split Tixr detail-page scraping from venue-owned public-card parsing.
--
-- `tixr` remains the DataDome-sensitive detail/group-page scraper that fetches
-- Tixr-hosted event pages. `tixr_public_card` is for venue-owned pages where
-- cards already contain title, date/time, and a Tixr ticket URL.

INSERT INTO scrapers (key, use_residential_proxy, notes, updated_at)
VALUES (
    'tixr_public_card',
    false,
    'Venue-owned public cards with Tixr ticket URLs; does not fetch Tixr detail pages',
    CURRENT_TIMESTAMP
)
ON CONFLICT (key) DO UPDATE
SET use_residential_proxy = EXCLUDED.use_residential_proxy,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

UPDATE scrapers
SET notes = 'Tixr-hosted detail/group pages; DataDome-sensitive and may require residential proxy',
    updated_at = CURRENT_TIMESTAMP
WHERE key = 'tixr';

UPDATE scraping_sources ss
SET
    scraper_key = 'tixr_public_card',
    source_url = CASE
        WHEN c.name = 'St. Marks Comedy Club' THEN 'https://www.stmarkscomedyclub.com/calendar'
        WHEN c.name = 'House of Comedy Bloomington' THEN 'https://moa.houseofcomedy.net/'
        ELSE ss.source_url
    END,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'tixr_source_type', 'venue_public_card',
        'detail_fetch_required', false,
        'datadome_dependent', false,
        'audit_note', 'Venue-owned public cards provide title/date/time/ticket URL; Tixr is only the ticket provider.',
        'audited_at', '2026-05-08'
    ),
    updated_at = CURRENT_TIMESTAMP
FROM clubs c
WHERE ss.club_id = c.id
  AND ss.platform = 'tixr'::"ScrapingPlatform"
  AND ss.scraper_key = 'tixr'
  AND ss.enabled = true
  AND (
      c.id = 16
      OR c.name IN ('St. Marks Comedy Club', 'House of Comedy Bloomington')
      OR c.website IN ('https://moa.houseofcomedy.net/', 'https://moa.houseofcomedy.net')
  );

UPDATE scraping_sources ss
SET
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'tixr_source_type', 'detail_page',
        'detail_fetch_required', true,
        'datadome_dependent', true
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE ss.platform = 'tixr'::"ScrapingPlatform"
  AND ss.scraper_key = 'tixr'
  AND ss.enabled = true;
