-- Switch The Moon (club 1048, Tallahassee FL) from Etix direct scrape to the
-- rhp-events scraper against its own WordPress site (moonevents.com/events).
--
-- Context: TASK-1647 documents that etix.com returns a DataDome CAPTCHA to both
-- curl-cffi and Playwright. moonevents.com/events renders the same show list via
-- the rhp-events WordPress plugin and is not DataDome-blocked, so reusing the
-- existing `comedy_magic_club` scraper (which parses rhp-events markup) recovers
-- The Moon without waiting on TASK-1658. Etix remains the ticketing platform —
-- the extractor captures etix.com ticket hrefs from the listing HTML.
UPDATE clubs
SET scraper = 'comedy_magic_club',
    scraping_url = 'https://moonevents.com/events'
WHERE id = 1048
  AND scraper = 'etix';
