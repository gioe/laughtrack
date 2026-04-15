-- Migrate Laugh Factory Covina from venue-specific scraper to generic Tixr scraper.
-- The laugh_factory_covina scraper is functionally identical to the generic tixr
-- scraper — both extract Tixr event URLs from an HTML page and batch-fetch JSON-LD.
-- Consolidating eliminates duplicate code with no behavioral change.
UPDATE clubs
SET scraper = 'tixr'
WHERE id = 171
  AND scraper = 'laugh_factory_covina';
