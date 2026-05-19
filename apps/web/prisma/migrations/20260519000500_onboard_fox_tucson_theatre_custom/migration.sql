-- Onboard Fox Tucson Theatre (club 2573) from temporary tour_dates discovery
-- to a focused venue-owned custom scraper.
--
-- Verification on 2026-05-18:
--   * Official calendar: https://foxtucson.com/events/
--   * Calendar event cards are server-rendered WordPress HTML and tag comedy
--     events with outburst-comedy / comedy classes.
--   * Ticket pages embed Spektrix under:
--     https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx
--   * Generic json_ld returned 0 shows, and Ticketmaster venue KovZpZAFkJeA
--     missed the listed comedy events.
--   * Focused fox_tucson_theatre scraper verified listed comedy cards including
--     Leslie Jones, Piff the Magic Dragon, Marlon Wayans, Michael Blaustein,
--     Henry Cho, and #IMOMSOHARD.

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
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Fox Tucson Theatre club 2573: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2573
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2573
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2573
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2573
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2573
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Fox Tucson Theatre club 2573: dependent rows exist';
    END IF;
END $$;

UPDATE clubs
SET
    address = '17 W Congress St',
    website = 'https://foxtucson.com',
    zip_code = '85701',
    country = 'US',
    timezone = 'America/Phoenix'
WHERE id = 2573
  AND name = 'Fox Tucson Theatre'
  AND city = 'Tucson'
  AND state = 'AZ'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'fox_tucson_theatre',
            'rationale', 'Temporary tour_dates source replaced after verified focused Fox Tucson Theatre scraper produced comedy shows from the official calendar.'
        )
    ),
    updated_at = NOW()
WHERE id = 1581
  AND club_id = 2573
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
    2573,
    'custom'::"ScrapingPlatform",
    'fox_tucson_theatre',
    'https://foxtucson.com/events/',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-18',
            'official_site', 'https://foxtucson.com',
            'official_calendar_url', 'https://foxtucson.com/events/',
            'spektrix_base_url', 'https://tickets.foxtucson.com/foxtucsontheatre',
            'sample_event_detail', 'https://foxtucson.com/event/leslie-jones/',
            'sample_ticket_url', 'https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx?WebEventId=leslie-jones&resize=true',
            'verification', 'Focused scraper parses official comedy-tagged cards and extracts Leslie Jones, Piff the Magic Dragon, Marlon Wayans, Michael Blaustein, Henry Cho, and #IMOMSOHARD when listed.'
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
