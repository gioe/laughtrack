-- Onboard Royal Oak Music Theatre (club 2582) from temporary tour_dates
-- discovery to the existing focused Ticketmaster comedy scraper.
--
-- Discovered from Akaash Singh tour-page evidence:
--   https://concerts50.com/buy/akaash-singh-in-royal-oak-tickets-mar-28-2026
--
-- Verification on 2026-05-19:
--   * No existing active canonical duplicate found by Royal Oak venue name,
--     Royal Oak location, official website domain, or Ticketmaster source URL.
--   * https://www.royaloakmusictheatre.com is the official venue site; its
--     calendar and ticketing pages route ticket purchases to AXS.
--   * No generic AXS scraper exists in SCRAPERS.md or scraper implementations.
--   * Ticketmaster public venue page is
--     https://www.ticketmaster.com/royal-oak-music-theatre-tickets-royal-oak/venue/65564.
--   * Ticketmaster Discovery venue search returns KovZpZA1IFeA for Royal Oak
--     Music Theatre, 318 West Fourth St., Royal Oak, MI.
--   * Discovery API returned 39 upcoming venue events and 6 comedy-classified
--     events.
--   * Read-only FocusedTicketmasterComedyScraper run with
--     ticketmaster_id=KovZpZA1IFeA produced 5 transformed comedy shows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2582
          AND c.name = 'Royal Oak Music Theatre'
          AND c.city = 'Royal Oak'
          AND c.state = 'MI'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
          AND ss.id = 1590
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Royal Oak Music Theatre club 2582: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2582
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2582
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2582
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2582
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2582
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Royal Oak Music Theatre club 2582: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZA1IFeA'
          AND club_id <> 2582
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Royal Oak Music Theatre: Ticketmaster venue KovZpZA1IFeA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '318 W 4th St',
    website = 'https://www.royaloakmusictheatre.com',
    zip_code = '48067',
    country = 'US',
    timezone = 'America/Detroit'
WHERE id = 2582
  AND name = 'Royal Oak Music Theatre'
  AND city = 'Royal Oak'
  AND state = 'MI'
  AND COALESCE(visible, TRUE) = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-19',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpZA1IFeA',
            'rationale', 'Temporary tour_dates source replaced after verified focused Ticketmaster comedy scrape produced comedy shows; official AXS calendar has no implemented generic scraper.'
        )
    ),
    updated_at = NOW()
WHERE id = 1590
  AND club_id = 2582
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;

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
    2582,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpZA1IFeA',
    'https://www.ticketmaster.com/royal-oak-music-theatre-tickets-royal-oak/venue/65564',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-19',
            'official_site', 'https://www.royaloakmusictheatre.com',
            'official_calendar_url', 'https://www.royaloakmusictheatre.com/events',
            'official_ticketing_platform', 'axs',
            'ticketmaster_venue_id', 'KovZpZA1IFeA',
            'ticketmaster_public_venue_id', '65564',
            'sample_event_detail', 'https://www.ticketmaster.com/event/Z7r9jZ1A7xfZP',
            'verification', 'Ticketmaster Discovery API returned 39 total venue events and 6 comedy-classified events; existing ticketmaster_comedy scraper transformed 5 comedy shows.'
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
                2582,
                'Royal Oak Music Theatre',
                'royal oak music theatre',
                'Royal Oak',
                'MI',
                'royal oak',
                'mi',
                '20260519161000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2582,
                'Royal Oak Music Theater',
                'royal oak music theater',
                'Royal Oak',
                'MI',
                'royal oak',
                'mi',
                '20260519161000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2582,
                'Royal Oak Music Theatre Royal Oak',
                'royal oak music theatre royal oak',
                'Royal Oak',
                'MI',
                'royal oak',
                'mi',
                '20260519161000: Ticketmaster venue onboarding',
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
