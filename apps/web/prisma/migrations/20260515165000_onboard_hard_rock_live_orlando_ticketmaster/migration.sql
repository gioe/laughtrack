-- Onboard Hard Rock Live - Orlando (club 2506) from temporary tour_dates
-- discovery to the existing generic Ticketmaster scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-orlando-hard-rock-live---orlando-10-8-2026/production/7024400
--
-- Verification on 2026-05-15:
--   * No existing active canonical duplicate found by Hard Rock Live name or
--     source/domain in Orlando, FL.
--   * Official site https://entertainment.hardrock.com/hard-rock-live-orlando
--     lists Hard Rock Live Orlando at 6050 Universal Blvd, Orlando, FL 32819
--     and links event tickets to Ticketmaster.
--   * Ticketmaster Discovery venue search returns KovZpZAEkJeA for Hard Rock
--     Live Orlando, Orlando, FL.
--   * Ticketmaster events API returned 31 upcoming venue events.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAEkJeA
--     produced 3 transformed comedy shows: Adam Ray, John Crist, and Nurse John.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2506
          AND c.name = 'Hard Rock Live - Orlando'
          AND c.city = 'Orlando'
          AND c.state = 'FL'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hard Rock Live Orlando: expected active tour_dates stub club 2506 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAEkJeA'
          AND club_id <> 2506
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Hard Rock Live Orlando: Ticketmaster venue KovZpZAEkJeA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://entertainment.hardrock.com/hard-rock-live-orlando',
    address = '6050 Universal Blvd',
    zip_code = '32819',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2506
  AND name = 'Hard Rock Live - Orlando'
  AND city = 'Orlando'
  AND state = 'FL'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAEkJeA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2506
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
    2506,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAEkJeA',
    'https://www.ticketmaster.com/hard-rock-live-orlando-tickets-orlando/venue/278539',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://entertainment.hardrock.com/hard-rock-live-orlando',
            'official_calendar', 'https://entertainment.hardrock.com/hard-rock-live-orlando',
            'ticketmaster_venue_id', 'KovZpZAEkJeA',
            'ticketmaster_public_venue_id', '278539',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-orlando-florida-10-08-2026/event/220064A4E16A5F3B',
            'verification', 'Ticketmaster Discovery API returned 31 total venue events; existing live_nation scraper transformed 3 comedy shows.'
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
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
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
                2506,
                'Hard Rock Live Orlando',
                'hard rock live orlando',
                'Orlando',
                'FL',
                'orlando',
                'fl',
                '20260515165000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2506,
                'Hard Rock Live at Universal Orlando',
                'hard rock live at universal orlando',
                'Orlando',
                'FL',
                'orlando',
                'fl',
                '20260515165000: Ticketmaster venue onboarding',
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
