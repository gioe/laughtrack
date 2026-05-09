-- Add 'thundertix' to ScrapingPlatform enum.
--
-- The two existing ThunderTix venues (annoyance, post_office_cafe) currently
-- live on platform='custom' with venue-specific scraper_keys. TASK-2070 folds
-- both onto a single GenericThunderTixScraper keyed by scraping_sources, which
-- requires a first-class enum value matching the platform identity convention
-- already used for tixr, eventbrite, seatengine, etc. Subsequent migrations in
-- this task switch the existing rows over.
ALTER TYPE "ScrapingPlatform" ADD VALUE 'thundertix';
