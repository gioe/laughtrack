-- Add 'patron_ticket' to ScrapingPlatform enum.
--
-- The Lost Church currently lives on platform='custom' with scraper_key='lost_church',
-- which hardcodes both the ticket URL and the Salesforce venue ID. TASK-2168 folds
-- that bespoke scraper onto a generic PatronTicketScraper (key='patron_ticket') so
-- multiple venues hosted on '<subdomain>.my.salesforce-sites.com/ticket' (Lost Church,
-- Reilly Arts Center, Marion Theatre) can share one implementation keyed by
-- scraping_sources. A first-class enum value matches the platform-identity convention
-- already used for thundertix, wix_events, seatengine, etc.
ALTER TYPE "ScrapingPlatform" ADD VALUE 'patron_ticket';
