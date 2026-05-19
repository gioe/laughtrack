-- Onboard Fox Tucson Theatre (club 2573) from temporary tour_dates discovery
-- to a focused custom WordPress/Spektrix scraper.
--
-- Verification on 2026-05-18:
--   * Official calendar: https://foxtucson.com/events/
--   * Official event cards expose comedy via event-card classes such as
--     outburst-comedy/comedy, with /event/<slug>/ and /event/<slug>/tickets
--     links plus all-in price text.
--   * WordPress ticket pages embed Spektrix EventDetails iframe URLs, e.g.
--     https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx?WebEventId=leslie-jones&resize=true
--   * Leslie Jones Spektrix EventDatesList exposes instance id 165401.
--   * Read-only fox_tucson_theatre scraper run returned 7 comedy shows:
--     Leslie Jones, Piff the Magic Dragon, Marlon Wayans, Michael Blaustein,
--     Henry Cho (2 performances), and #IMOMSOHARD.
--   * Ticketmaster venue KovZpZAFkJeA is not a sufficient replacement source:
--     Discovery API comedy query returned 0 events, and venue-wide Discovery
--     returned 13 total events while missing Leslie Jones.
--   * Generic json_ld extraction from the official calendar returned 0 Event
--     objects because the page only exposes non-event structured data.

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
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1581
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.source_url = 'https://foxtucson.com/events/'
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

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE scraper_key = 'fox_tucson_theatre'
          AND club_id <> 2573
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Fox Tucson Theatre: scraper_key fox_tucson_theatre is already assigned to another club';
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
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'fox_tucson_theatre',
            'replacement_source_url', 'https://foxtucson.com/events/',
            'replacement_scrape_show_count', 7,
            'rationale', 'Temporary tour_dates source replaced after verified fox_tucson_theatre scrape produced comedy shows from the official WordPress/Spektrix calendar.'
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
            'ticketing_platform', 'spektrix',
            'spektrix_base_url', 'https://tickets.foxtucson.com/foxtucsontheatre',
            'sample_event_url', 'https://foxtucson.com/event/leslie-jones/',
            'sample_ticket_url', 'https://foxtucson.com/event/leslie-jones/tickets',
            'sample_spektrix_url', 'https://tickets.foxtucson.com/foxtucsontheatre/website/EventDetails.aspx?WebEventId=leslie-jones&resize=true',
            'sample_spektrix_instance_id', '165401',
            'verified_show_count', 7,
            'ticketmaster_venue_id_checked', 'KovZpZAFkJeA',
            'ticketmaster_comedy_event_count', 0,
            'ticketmaster_venue_event_count', 13,
            'json_ld_event_count', 0,
            'verification', 'Focused scraper returned 7 comedy shows from official event cards; Ticketmaster and json_ld were insufficient replacement sources.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
        INSERT INTO club_aliases (
            club_id,
            alias_name,
            normalized_alias_name,
            city,
            state,
            normalized_city,
            normalized_state,
            source,
            verified
        )
        VALUES
            (
                2573,
                'Fox Tucson Theatre',
                'fox tucson theatre',
                'Tucson',
                'AZ',
                'tucson',
                'az',
                '20260518201000: Spektrix venue onboarding',
                TRUE
            ),
            (
                2573,
                'Fox Tucson',
                'fox tucson',
                'Tucson',
                'AZ',
                'tucson',
                'az',
                '20260518201000: Spektrix venue onboarding',
                TRUE
            )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
        DO UPDATE SET
            club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW();
    END IF;
END $$;
