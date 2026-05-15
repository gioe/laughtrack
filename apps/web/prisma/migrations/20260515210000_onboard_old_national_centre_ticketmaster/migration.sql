-- Onboard Murat Egyptian Room at Old National Centre (club 2510)
-- from temporary tour_dates discovery to the existing generic Ticketmaster
-- scraper.
--
-- Discovered from Nurse John tour-page evidence:
--   https://www.vividseats.com/nurse-john-tickets-indianapolis-murat-egyptian-room-at-old-national-centre-10-22-2026--theater-comedy/production/7024685
--
-- Verification on 2026-05-15:
--   * No existing active canonical duplicate found by Murat/Egyptian Room/Old
--     National Centre name, source domain, or candidate Ticketmaster venue IDs.
--   * https://www.oldnationalcentre.com redirects to the official Live Nation
--     venue page for Old National Centre.
--   * Ticketmaster Discovery venue search returns KovZpZAEAkvA / public venue
--     42026 for Old National Centre, Indianapolis, IN.
--   * Ticketmaster also returns room-style candidate IDs for Egyptian Room and
--     Murat Theatre, but those IDs returned zero or unrelated events; the Nurse
--     John event is on the parent Old National Centre venue ID.
--   * Discovery API returned 84 upcoming parent-venue events, including Nurse
--     John: Against Medical Advice Tour on October 22, 2026.
--   * Read-only TicketmasterScraper run with ticketmaster_id=KovZpZAEAkvA
--     produced 6 transformed comedy shows, including Bill Engvall, Jonathan
--     Van Ness, and Nurse John.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2510
          AND c.name = 'Murat Egyptian Room at Old National Centre'
          AND c.city = 'Indianapolis'
          AND c.state = 'IN'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1518
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Old National Centre club 2510: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2510
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2510
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2510
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2510
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2510
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Old National Centre club 2510: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpZAEAkvA'
          AND club_id <> 2510
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Old National Centre: Ticketmaster venue KovZpZAEAkvA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '502 N. New Jersey',
    website = 'https://www.oldnationalcentre.com',
    zip_code = '46204',
    country = 'US',
    timezone = 'America/Indiana/Indianapolis'
WHERE id = 2510
  AND name = 'Murat Egyptian Room at Old National Centre'
  AND city = 'Indianapolis'
  AND state = 'IN'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAEAkvA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1518
  AND club_id = 2510
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
    2510,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAEAkvA',
    'https://www.ticketmaster.com/old-national-centre-tickets-indianapolis/venue/42026',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://www.oldnationalcentre.com',
            'official_calendar_url', 'https://www.livenation.com/venue/KovZpZAEAkvA/old-national-centre-events',
            'ticketmaster_venue_id', 'KovZpZAEAkvA',
            'ticketmaster_public_venue_id', '42026',
            'sample_event_detail', 'https://www.ticketmaster.com/nurse-john-against-medical-advice-tour-indianapolis-indiana-10-22-2026/event/050064A7A2C7C354',
            'verification', 'Ticketmaster Discovery API returned 84 total venue events; existing live_nation scraper transformed 6 comedy shows.'
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
                2510,
                'Old National Centre',
                'old national centre',
                'Indianapolis',
                'IN',
                'indianapolis',
                'in',
                '20260515210000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2510,
                'Old National Center',
                'old national center',
                'Indianapolis',
                'IN',
                'indianapolis',
                'in',
                '20260515210000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2510,
                'Egyptian Room at Old National',
                'egyptian room at old national',
                'Indianapolis',
                'IN',
                'indianapolis',
                'in',
                '20260515210000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2510,
                'Murat Egyptian Room at Old National Centre',
                'murat egyptian room at old national centre',
                'Indianapolis',
                'IN',
                'indianapolis',
                'in',
                '20260515210000: Ticketmaster venue onboarding',
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
