-- Disposition Fox Tucson Theatre (club 2573) from the tour_dates onboarding queue.
--
-- Investigation on 2026-05-18:
--   * Official site is https://foxtucson.com.
--   * Official event calendar is https://foxtucson.com/events/.
--   * Ticket pages embed Spektrix iframes from
--     https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx
--     with WebEventId values such as "leslie-jones".
--   * Generic json_ld returned 0 shows from the event calendar.
--   * Ticketmaster Discovery found venue KovZpZAFkJeA, but a comedy-only query
--     returned 0 events and the venue-wide feed missed the listed comedy shows,
--     so Ticketmaster is not a safe replacement source.
--   * Follow-up TASK-2280 tracks a focused Fox Tucson Theatre scraper that can
--     parse the venue-owned calendar and filter the multipurpose theatre to
--     comedy events.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2573
          AND c.name = 'Fox Tucson Theatre'
          AND c.city = 'Tucson'
          AND c.state = 'AZ'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
          AND ss.id = 1581
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot disposition Fox Tucson Theatre tour_dates source: expected active club 2573/source 1581 is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://foxtucson.com',
    address = '17 W Congress St',
    zip_code = '85701',
    timezone = 'America/Phoenix'
WHERE id = 2573
  AND name = 'Fox Tucson Theatre'
  AND city = 'Tucson'
  AND state = 'AZ'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    source_url = 'https://foxtucson.com/events/',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'needs_focused_fox_tucson_theatre_spektrix_scraper',
        'followup_task_id', 2280,
        'official_url', 'https://foxtucson.com',
        'official_calendar_url', 'https://foxtucson.com/events/',
        'ticketing_platform', 'spektrix',
        'spektrix_base_url', 'https://tickets.foxtucson.com/foxtucsontheatre',
        'sample_event_url', 'https://foxtucson.com/event/leslie-jones/',
        'sample_ticket_url', 'https://foxtucson.com/event/leslie-jones/tickets',
        'sample_spektrix_url', 'https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx?WebEventId=leslie-jones&resize=true',
        'ticketmaster_venue_id', 'KovZpZAFkJeA',
        'ticketmaster_venue_url', 'https://www.ticketmaster.com/fox-tucson-theatre-tickets-tucson/venue/205132',
        'disabled_reason', 'requires_focused_custom_scraper_for_multipurpose_spektrix_calendar',
        'verification', 'Official calendar is Spektrix-backed; generic json_ld returned 0 shows. Ticketmaster comedy-only query for venue KovZpZAFkJeA returned 0 events and venue-wide feed missed listed comedy events, so TASK-2280 must add a focused venue scraper before enabling a replacement source.',
        'verified_at', '2026-05-18'
    ),
    updated_at = NOW()
WHERE id = 1581
  AND club_id = 2573
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;
