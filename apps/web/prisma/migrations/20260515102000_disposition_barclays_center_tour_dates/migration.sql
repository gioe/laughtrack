-- Disposition Barclays Center (club 2464) from the tour_dates onboarding queue.
--
-- Investigation on 2026-05-15:
--   * Official site is https://www.barclayscenter.com.
--   * Official comedy category page is
--     https://www.barclayscenter.com/events/category/comedy.
--   * Ticketmaster Discovery venue search returns KovZ917AtP3 for Barclays
--     Center at 620 Atlantic Ave, Brooklyn, NY.
--   * Ticketmaster events API returned 110 total upcoming venue events.
--   * A read-only TicketmasterScraper run with ticketmaster_id=KovZ917AtP3
--     transformed 36 shows, including non-comedy Barclays Center Tours and
--     sports-related tour products, so the venue-wide live_nation source is not
--     safe to enable.
--   * Follow-up TASK-2234 tracks a focused Barclays/Carbonhouse comedy-category
--     scraper that can replace this temporary discovery source safely.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2464
          AND c.name = 'Barclays Center'
          AND c.city = 'Brooklyn'
          AND c.state = 'NY'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1472
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot disposition Barclays Center tour_dates source: expected active club 2464/source 1472 is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.barclayscenter.com',
    address = '620 Atlantic Ave',
    zip_code = '11217',
    timezone = 'America/New_York'
WHERE id = 2464
  AND name = 'Barclays Center'
  AND city = 'Brooklyn'
  AND state = 'NY'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    source_url = 'https://www.barclayscenter.com/events/category/comedy',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'needs_focused_carbonhouse_comedy_scraper',
        'followup_task_id', 2234,
        'official_url', 'https://www.barclayscenter.com',
        'official_comedy_category_url', 'https://www.barclayscenter.com/events/category/comedy',
        'ticketmaster_venue_id', 'KovZ917AtP3',
        'ticketmaster_venue_url', 'https://www.ticketmaster.com/barclays-center-tickets-brooklyn/venue/393376',
        'sample_event_url', 'https://www.barclayscenter.com/events/detail/nick-cannon-wild-n-out-live-no-filter-2026',
        'sample_ticket_url', 'https://www.ticketmaster.com/event/3000648FD9FB7F6A',
        'disabled_reason', 'generic_ticketmaster_source_overingests_non_comedy_arena_events',
        'verification', 'Ticketmaster venue KovZ917AtP3 returned 110 total events; read-only live_nation scrape transformed 36 shows including Barclays Center Tours, so TASK-2234 must add a focused comedy-category scraper before enabling a replacement source.',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE id = 1472
  AND club_id = 2464
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;
