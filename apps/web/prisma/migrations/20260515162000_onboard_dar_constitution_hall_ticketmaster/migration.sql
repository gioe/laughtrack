-- Onboard DAR Constitution Hall (club 2503) from temporary tour_dates
-- discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-washington-dar-constitution-hall-9-20-2026/production/7024286
--
-- Verification on 2026-05-15:
--   * No existing canonical duplicate found by DAR Constitution Hall name/domain
--     in Washington, DC, or by Ticketmaster Discovery venue ID.
--   * Official DAR pages identify the venue as DAR Constitution Hall at
--     1776 D Street NW, Washington, DC 20006 and direct ticket purchases to
--     Ticketmaster or the event sponsor.
--   * Ticketmaster venue search returns KovZpaKdYe for DAR Constitution Hall,
--     Washington, DC.
--   * Ticketmaster events API returned 12 upcoming venue events, including
--     Nurse John: Against Medical Advice Tour on September 20, 2026.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpaKdYe
--     produced 8 transformed shows, including Nurse John, Steve Martin/Martin
--     Short, and Josh Johnson dates.

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
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard DAR Constitution Hall: expected active tour_dates stub club 2503 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpaKdYe'
          AND club_id <> 2503
    ) THEN
        RAISE EXCEPTION 'Cannot onboard DAR Constitution Hall: Ticketmaster venue KovZpaKdYe is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.dar.org/conthall',
    address = '1776 D Street NW',
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
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpaKdYe',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2503
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    ticketmaster_id,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2503,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpaKdYe',
    'https://www.ticketmaster.com/dar-constitution-hall-tickets-washington/venue/172054',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.dar.org/conthall',
            'official_calendar', 'https://www.dar.org/events/constitution-hall/schedule',
            'ticketmaster_venue_id', 'KovZpaKdYe',
            'ticketmaster_public_venue_id', '172054',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-washington-district-of-columbia-09-20-2026/event/150064A9CDD1A8DD',
            'verification', 'Ticketmaster Discovery API returned 12 total venue events; existing live_nation scraper transformed 8 shows.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    ticketmaster_id = EXCLUDED.ticketmaster_id,
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
        VALUES (
            2503,
            'DAR Constitution Hall',
            'dar constitution hall',
            'Washington',
            'DC',
            'washington',
            'dc',
            '20260515162000_onboard_dar_constitution_hall_ticketmaster',
            TRUE
        )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO UPDATE
        SET club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW();
    END IF;
END $$;
