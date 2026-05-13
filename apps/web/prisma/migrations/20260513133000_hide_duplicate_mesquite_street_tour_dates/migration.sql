-- Hide duplicate tour_dates stub for Mesquite Street (club 2360).
--
-- Club 2360 was auto-created from comedian tour-page discovery using the
-- TicketLeap URL https://events.ticketleap.com/tickets/funny/steve-o-the-crash-and-burn-tour#/.
-- That TicketLeap org is already represented by canonical club 837,
-- "Mesquite St. Comedy Club", with enabled source 479:
--   platform='ticketleap', scraper_key='ticketleap',
--   source_url='https://events.ticketleap.com/events/funny'
--
-- Verification on 2026-05-13:
--   * club 2360 has 0 shows, so there is nothing to migrate
--   * make scrape-club CLUB="Mesquite St. Comedy Club" scraped 5 TicketLeap shows

UPDATE clubs
SET name = 'Mesquite Street (duplicate of club 837)',
    visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2360
  AND name = 'Mesquite Street'
  AND visible = true
  AND status = 'active';

UPDATE scraping_sources
SET enabled = false,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_837',
        'canonical_club_id', 837,
        'canonical_source_id', 479,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2360
  AND platform = 'tour_dates'
  AND scraper_key = 'tour_dates';
