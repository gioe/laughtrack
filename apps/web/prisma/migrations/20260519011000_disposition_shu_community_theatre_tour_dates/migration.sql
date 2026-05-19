-- Disposition SHU Community Theatre (club 2578) from the tour_dates onboarding queue.
--
-- Investigation on 2026-05-19:
--   * Official site is https://www.shucommunitytheatre.org/.
--   * Official all-events page is https://www.shucommunitytheatre.org/allevents.
--   * Live-performance buy links point to accesso ShoWare at
--     https://shucommunitytheatre.showare.com/.
--   * Sample ShoWare event detail:
--     https://shucommunitytheatre.showare.com/eventperformances.asp?evt=386.
--   * The all-events page also links film tickets through Veezi, so a replacement
--     source must target live performances rather than the whole mixed calendar.
--   * No existing ShoWare or AXS scraper exists in SCRAPERS.md or
--     apps/scraper/src.
--   * Ticketmaster Discovery found venue Z7r9jZaAvN, but events.json returned
--     0 total events both with and without classificationName=Comedy.
--   * Eventbrite searches did not find a usable organizer or venue feed.
--   * Follow-up TASK-2299 tracks adding a generic ShoWare scraper, or a deliberate
--     AXS scraper if ShoWare cannot expose the official inventory reliably.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2578
          AND c.name = 'SHU Community Theatre'
          AND c.city = 'Fairfield'
          AND c.state = 'CT'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
          AND ss.id = 1586
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot disposition SHU Community Theatre tour_dates source: expected active club 2578/source 1586 is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.shucommunitytheatre.org/',
    address = '1420 Post Rd',
    zip_code = '06824',
    timezone = 'America/New_York'
WHERE id = 2578
  AND name = 'SHU Community Theatre'
  AND city = 'Fairfield'
  AND state = 'CT'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    source_url = 'https://shucommunitytheatre.showare.com/',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'needs_generic_showare_or_axs_scraper',
        'followup_task_id', 2299,
        'official_url', 'https://www.shucommunitytheatre.org/',
        'official_calendar_url', 'https://www.shucommunitytheatre.org/allevents',
        'ticketing_platform', 'accesso_showare',
        'showare_base_url', 'https://shucommunitytheatre.showare.com/',
        'sample_event_url', 'https://shucommunitytheatre.showare.com/eventperformances.asp?evt=386',
        'sample_axs_venue_url', 'https://www.axs.com/us/venues/133980/shu-community-theatre-fairfield-tickets',
        'sample_axs_event_url', 'https://www.axs.com/events/1417334/leslie-jones-tickets',
        'ticketmaster_venue_id', 'Z7r9jZaAvN',
        'disabled_reason', 'requires_new_generic_scraper_for_showare_or_axs_live_performance_inventory',
        'verification', 'Official live-performance ticketing is accesso ShoWare; no existing ShoWare/AXS scraper is implemented. Ticketmaster venue Z7r9jZaAvN returned 0 events with and without classificationName=Comedy, and Eventbrite had no usable organizer or venue feed. TASK-2299 must add a replacement scraper before enabling a non-tour_dates source.',
        'verified_at', '2026-05-19'
    ),
    updated_at = NOW()
WHERE id = 1586
  AND club_id = 2578
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;
