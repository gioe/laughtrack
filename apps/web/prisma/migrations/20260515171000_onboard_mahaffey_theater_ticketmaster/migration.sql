-- Onboard Mahaffey Theater - Duke Energy Center for the Arts FL (club 2507)
-- from temporary tour_dates discovery to the existing generic Ticketmaster
-- scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-saint-petersburg-mahaffey-theater---duke-energy-center-for-the-arts-fl-10-9-2026/production/7024316
--
-- Verification on 2026-05-15:
--   * No existing active canonical duplicate found by Mahaffey name or
--     source/domain in Saint Petersburg, FL.
--   * Official site https://themahaffey.com/ lists Duke Energy Center for the
--     Arts - Mahaffey Theater at 400 First Street South, St. Petersburg, FL
--     33701 and links event tickets to Ticketmaster.
--   * Ticketmaster Discovery venue search returns KovZpZAdE1eA for Duke
--     Energy Center for the Arts - Mahaffey Theater, St Petersburg, FL.
--   * Ticketmaster events API returned 25 upcoming venue events, including
--     comedy events for Nurse John and Josh Johnson.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAdE1eA
--     produced 1 transformed in-window comedy show after the Ticketmaster
--     classifier was tightened to exclude Music/Undefined events.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2507
          AND c.name = 'Mahaffey Theater - Duke Energy Center for the Arts FL'
          AND c.city = 'Saint Petersburg'
          AND c.state = 'FL'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mahaffey Theater: expected active tour_dates stub club 2507 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAdE1eA'
          AND club_id <> 2507
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Mahaffey Theater: Ticketmaster venue KovZpZAdE1eA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://themahaffey.com/',
    address = '400 First Street South',
    zip_code = '33701',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2507
  AND name = 'Mahaffey Theater - Duke Energy Center for the Arts FL'
  AND city = 'Saint Petersburg'
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
            'replacement_ticketmaster_id', 'KovZpZAdE1eA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2507
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
    2507,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAdE1eA',
    'https://www.ticketmaster.com/duke-energy-center-for-the-arts-tickets-st-petersburg/venue/106761',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://themahaffey.com/',
            'official_calendar', 'https://themahaffey.com/shows-and-events/',
            'ticketmaster_venue_id', 'KovZpZAdE1eA',
            'ticketmaster_public_venue_id', '106761',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-st-petersburg-florida-10-09-2026/event/0D0064A6D98526C9',
            'verification', 'Ticketmaster Discovery API returned 25 total venue events; existing live_nation scraper transformed 1 in-window comedy show after excluding Music/Undefined events.'
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
                2507,
                'Mahaffey Theater',
                'mahaffey theater',
                'Saint Petersburg',
                'FL',
                'saint petersburg',
                'fl',
                '20260515171000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2507,
                'Duke Energy Center for the Arts - Mahaffey Theater',
                'duke energy center for the arts mahaffey theater',
                'Saint Petersburg',
                'FL',
                'saint petersburg',
                'fl',
                '20260515171000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2507,
                'Mahaffey Theater at the Duke Energy Center for the Arts',
                'mahaffey theater at the duke energy center for the arts',
                'Saint Petersburg',
                'FL',
                'saint petersburg',
                'fl',
                '20260515171000: Ticketmaster venue onboarding',
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
