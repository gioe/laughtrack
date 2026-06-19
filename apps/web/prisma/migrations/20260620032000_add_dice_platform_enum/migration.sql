-- Add 'dice' to ScrapingPlatform enum for venues using DICE event-list widgets.
--
-- The generic DICE scraper is configured from scraping_sources.metadata
-- (dice_api_key plus venue/promoter filters), matching other generic platform
-- scrapers that are selected by scraper_key.
ALTER TYPE "ScrapingPlatform" ADD VALUE 'dice';
