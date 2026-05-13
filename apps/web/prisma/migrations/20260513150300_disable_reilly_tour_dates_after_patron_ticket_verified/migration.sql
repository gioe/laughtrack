-- TASK-2168: Disable Reilly Arts Center's tour_dates source now that
-- patron_ticket has produced verified comedy shows.
--
-- The previous migration (20260513150200) inserted the patron_ticket source
-- at priority=0 and demoted tour_dates to priority=1 as a passive fallback.
-- A real scrape of Reilly Arts Center via patron_ticket on 2026-05-13
-- returned 2 upcoming comedy shows (Jim Breuer 2026-05-15, Jamie Lissow
-- 2026-08-30) — both stamped last_scraped_by='patron_ticket'. With the
-- dedicated PatronTicket source confirmed working, the tour_dates discovery
-- row no longer adds value here (it surfaced this venue via Steve-O's tour
-- page; the patron_ticket source covers Reilly's full upcoming comedy slate
-- directly). Disabling it stops scrape_shows from falling back to a less
-- precise source if patron_ticket has a transient failure, and removes the
-- comedian-tour ↔ club crosswalk that would otherwise keep counting toward
-- the club's tour_date_onboarding signals.
UPDATE scraping_sources
SET
    enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-13',
            'replacement_platform', 'patron_ticket',
            'replacement_scraper_key', 'patron_ticket',
            'replacement_patronticket_venue_id', 'a0TV100000GFLfpMAH',
            'rationale', 'Verified patron_ticket scrape returned 2 upcoming comedy shows; tour_dates fallback no longer needed.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2368
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
