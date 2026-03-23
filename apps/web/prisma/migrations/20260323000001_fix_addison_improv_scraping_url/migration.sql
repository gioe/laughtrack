-- Fix Addison Improv (club 29) scraping_url to point to /calendar/ page
-- The homepage (improvtx.com/addison/) uses class="promo type-event" links which the
-- improv scraper does not recognise. The calendar page uses class="item" links which
-- match the existing HtmlScraper.find_links_by_class("item") logic.
UPDATE "clubs"
SET "scraping_url" = 'improvtx.com/addison/calendar/'
WHERE id = 29
  AND "scraping_url" = 'improvtx.com/addison/';
