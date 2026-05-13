-- TASK-2168: Fold The Lost Church (club_id=1047) onto generic PatronTicketScraper.
--
-- The bespoke LostChurchScraper hardcoded both the apexremote URL and the SF
-- venue ID. The new PatronTicketScraper (key='patron_ticket') reads source_url
-- from scraping_sources and the venue ID(s) from metadata.patronticket_venue_id,
-- which lets multiple PatronTicket venues share one implementation. The Lost
-- Church's previous title-cleanup behavior (stripping a trailing " - San
-- Francisco" / " - SF" / " - sf" suffix from event names) is preserved via
-- metadata.patronticket_name_strip_suffixes so the fold is title-equivalent.
--
-- Match enabled and disabled rows alike: a disabled row left behind would still
-- point at the deleted scraper_key='lost_church' code path and become an
-- unknown-scraper landmine if ever re-enabled (per scraping_sources migration
-- convention #93).
UPDATE scraping_sources
SET
    platform = 'patron_ticket'::"ScrapingPlatform",
    scraper_key = 'patron_ticket',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'patronticket_venue_id', 'a0T6A000002eYckUAE',
        'patronticket_name_strip_suffixes', ' - San Francisco, - SF, - sf'
    ),
    updated_at = NOW()
WHERE club_id = 1047
  AND scraper_key = 'lost_church';
