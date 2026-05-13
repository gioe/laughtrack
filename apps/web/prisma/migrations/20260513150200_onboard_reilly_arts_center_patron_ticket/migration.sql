-- TASK-2168: Onboard Reilly Arts Center (club_id=2368) onto PatronTicketScraper.
--
-- Verification on 2026-05-13:
--   Official site: https://reillyartscenter.org
--   Ticketing host: https://reillyartscenter.my.salesforce-sites.com/ticket
--   Live fetchEvents API call returned 83 total events; filtering "Comedy" in
--   the category field yielded 11 upcoming comedy events across two Salesforce
--   venue IDs run by the same Ocala-FL ticketing org:
--     a0TV100000GFLfpMAH — Reilly Arts Center Mainstage (this club)
--     a0T4T0000005C4gUAE — Marion Theatre (separate physical venue;
--                          onboarded as its own club in a follow-up task).
--
-- Insert the new patron_ticket source at priority=0 and demote the existing
-- tour_dates discovery source (id=1376) to priority=1. Demotion (not disable)
-- preserves the tour_dates row as a passive fallback until the patron_ticket
-- source has produced shows in a real scrape run — at which point a follow-up
-- migration will disable tour_dates per the task's acceptance criteria.
UPDATE scraping_sources
SET
    priority = 1,
    updated_at = NOW()
WHERE club_id = 2368
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2368,
    'patron_ticket'::"ScrapingPlatform",
    'patron_ticket',
    'https://reillyartscenter.my.salesforce-sites.com/ticket',
    0,
    TRUE,
    jsonb_build_object(
        'patronticket_venue_id', 'a0TV100000GFLfpMAH',
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-13',
            'official_site', 'https://reillyartscenter.org',
            'patronticket_host', 'reillyartscenter.my.salesforce-sites.com',
            'salesforce_venue_id', 'a0TV100000GFLfpMAH',
            'verification', 'Live fetchEvents API returned 83 events; 11 upcoming comedy events at the Mainstage venue ID.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
