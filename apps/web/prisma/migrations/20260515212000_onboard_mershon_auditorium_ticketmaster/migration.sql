-- Onboard Wexner Center for the Arts - Mershon Auditorium (club 2511)
-- from temporary tour_dates discovery to the existing generic Ticketmaster
-- scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-columbus-wexner-center-for-the-arts---mershon-auditorium-10-23-2026/production/7024384
--
-- Verification on 2026-05-15:
--   * No existing active canonical duplicate found by Mershon/Wexner name,
--     source domain, or candidate website domains.
--   * https://www.mershonauditorium.com is the official Mershon Auditorium
--     site, and its ticket information page states Ticketmaster is the
--     exclusive ticketing partner.
--   * Ticketmaster Discovery venue search returns KovZpaoyie / public venue
--     41024 for Mershon Auditorium, Columbus, OH.
--   * The sibling Ticketmaster venue ID for "Wexner Center for the Arts"
--     (KovZpZAFdt7A / public venue 41280) returned zero events for the same
--     date window; the Nurse John event is on the Mershon Auditorium venue ID.
--   * Discovery API returned 8 upcoming Mershon events through 2026-12-31,
--     including 4 comedy events: Derrick Stroup, Killers of Kill Tony,
--     Nurse John, and Jordan Klepper.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpaoyie
--     produced 4 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2511
          AND c.name = 'Wexner Center for the Arts - Mershon Auditorium'
          AND c.city = 'Columbus'
          AND c.state = 'OH'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1519
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mershon Auditorium club 2511: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2511
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2511
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2511
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2511
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2511
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mershon Auditorium club 2511: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpaoyie'
          AND club_id <> 2511
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mershon Auditorium: Ticketmaster venue KovZpaoyie is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '1871 N High St',
    website = 'https://www.mershonauditorium.com',
    zip_code = '43210',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2511
  AND name = 'Wexner Center for the Arts - Mershon Auditorium'
  AND city = 'Columbus'
  AND state = 'OH'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpaoyie',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1519
  AND club_id = 2511
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
    2511,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpaoyie',
    'https://www.ticketmaster.com/mershon-auditorium-tickets-columbus/venue/41024',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.mershonauditorium.com',
            'official_calendar_url', 'https://www.mershonauditorium.com/events',
            'ticket_information_url', 'https://www.mershonauditorium.com/events/ticket-information',
            'ticketmaster_venue_id', 'KovZpaoyie',
            'ticketmaster_public_venue_id', '41024',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-columbus-ohio-10-23-2026/event/050064A79EDFB911',
            'verification', 'Ticketmaster Discovery API returned 8 total venue events; existing live_nation scraper transformed 4 comedy shows.'
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
                2511,
                'Mershon Auditorium',
                'mershon auditorium',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260515212000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2511,
                'Wexner Center for the Arts Mershon Auditorium',
                'wexner center for the arts mershon auditorium',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260515212000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2511,
                'Mershon Auditorium at Wexner Center for the Arts',
                'mershon auditorium at wexner center for the arts',
                'Columbus',
                'OH',
                'columbus',
                'oh',
                '20260515212000: Ticketmaster venue onboarding',
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
