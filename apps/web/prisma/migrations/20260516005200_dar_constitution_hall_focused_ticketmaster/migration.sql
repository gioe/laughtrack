-- Switch DAR Constitution Hall (club 2503) from the venue-wide Ticketmaster
-- scraper to the focused comedy-only Ticketmaster scraper.
--
-- Verification on 2026-05-16:
--   * Ticketmaster Discovery API venue KovZpaKdYe returned 12 total upcoming
--     venue events unfiltered, including non-comedy Averly Morillo and a
--     ticketless Josh Johnson VIP add-on.
--   * The same endpoint with classificationName=Comedy returned 6 comedy
--     events: The Best of Steve Martin & Martin Short, Nurse John, and four
--     Josh Johnson Comedy Band Camp performances.
--   * Read-only FocusedTicketmasterComedyScraper run with ticketmaster_id
--     KovZpaKdYe produced those 6 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2503
          AND c.name = 'DAR Constitution Hall'
          AND c.city = 'Washington'
          AND c.state = 'DC'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 2339
          AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
          AND ss.scraper_key = 'live_nation'
          AND ss.ticketmaster_id = 'KovZpaKdYe'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot switch DAR Constitution Hall club 2503: expected active live_nation Ticketmaster source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE id = 1511
          AND club_id = 2503
          AND platform = 'tour_dates'::"ScrapingPlatform"
          AND scraper_key = 'tour_dates'
          AND enabled = FALSE
    ) THEN
        RAISE EXCEPTION 'Cannot switch DAR Constitution Hall club 2503: expected disabled temporary tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpaKdYe'
          AND club_id <> 2503
    ) THEN
        RAISE EXCEPTION 'Cannot switch DAR Constitution Hall: Ticketmaster venue KovZpaKdYe is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '1776 D Street NW',
    website = 'https://www.dar.org/conthall',
    zip_code = '20006',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2503
  AND name = 'DAR Constitution Hall'
  AND city = 'Washington'
  AND state = 'DC'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpaKdYe',
            'rationale', 'Temporary tour_dates source remains disabled after verified focused Ticketmaster comedy scrape produced 6 comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1511
  AND club_id = 2503
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

UPDATE scraping_sources
SET scraper_key = 'ticketmaster_comedy',
    ticketmaster_id = 'KovZpaKdYe',
    source_url = 'https://www.ticketmaster.com/dar-constitution-hall-tickets-washington/venue/172054',
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'focused_ticketmaster_comedy', jsonb_build_object(
            'verified_at', '2026-05-16',
            'ticketmaster_venue_id', 'KovZpaKdYe',
            'ticketmaster_public_venue_id', '172054',
            'classification_name', 'Comedy',
            'excluded_examples', jsonb_build_array(
                'Averly Morillo',
                'JOSH JOHNSON''S COMEDY BAND CAMP - Ticketless VIP'
            ),
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-washington-district-of-columbia-09-20-2026/event/150064A9CDD1A8DD',
            'verification', 'Ticketmaster Discovery API returned 12 total venue events unfiltered and 6 events with classificationName=Comedy; FocusedTicketmasterComedyScraper transformed the 6 comedy events and excluded Averly Morillo plus the ticketless VIP add-on.'
        )
    ),
    updated_at = NOW()
WHERE id = 2339
  AND club_id = 2503
  AND platform = 'ticketmaster'::"ScrapingPlatform"
  AND ticketmaster_id = 'KovZpaKdYe';
