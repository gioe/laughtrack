-- Migrate SuperNova Comedy from venue-specific scraper to generic Tixr scraper.
-- The supernova_comedy scraper is functionally identical to the generic tixr
-- scraper — both extract Tixr event URLs from an HTML page, filter by Org JSON-LD,
-- and batch-fetch event details via TixrClient. Consolidating eliminates duplicate
-- code with no behavioral change.
UPDATE clubs
SET scraper = 'tixr'
WHERE id = 456 AND scraper = 'supernova_comedy';
