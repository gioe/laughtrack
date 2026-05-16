-- Onboard Pearl Concert Theater at Palms Casino Resort (club 2567) from
-- temporary tour_dates discovery to the existing focused Ticketmaster comedy
-- scraper.
--
-- Discovered from Leslie Jones tour-page evidence:
--   https://concerts50.com/buy/leslie-jones-in-las-vegas-tickets-jul-31-2026
--
-- Verification on 2026-05-16:
--   * No existing active canonical duplicate found by Pearl/Palms name,
--     official website domain, or Ticketmaster Discovery venue id.
--   * https://www.palms.com/index.php/entertainment/pearl-theater is the
--     official venue calendar. Ticketmaster lists the same venue and links
--     ticket purchases to AXS as partner-site tickets.
--   * Ticketmaster Discovery venue search returns KovZpaKAZe / public venue
--     189126 for Pearl Concert Theater at Palms Casino Resort, Las Vegas, NV.
--   * Discovery API returned 41 upcoming venue events and 1 Comedy-classified
--     event: Leslie Jones.
--   * Read-only FocusedTicketmasterComedyScraper run with ticketmaster_id
--     KovZpaKAZe produced 1 transformed comedy show.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2567
          AND c.name = 'Pearl Concert Theater at Palms Casino Resort'
          AND c.city = 'Las Vegas'
          AND c.state = 'NV'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1575
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Pearl Concert Theater club 2567: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM shows
        WHERE club_id = 2567
        UNION ALL
        SELECT 1
        FROM tagged_clubs
        WHERE club_id = 2567
        UNION ALL
        SELECT 1
        FROM email_subscriptions
        WHERE club_id = 2567
        UNION ALL
        SELECT 1
        FROM processed_emails
        WHERE club_id = 2567
        UNION ALL
        SELECT 1
        FROM production_company_venues
        WHERE club_id = 2567
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Pearl Concert Theater club 2567: dependent rows exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZpaKAZe'
          AND club_id <> 2567
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Pearl Concert Theater: Ticketmaster venue KovZpaKAZe is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET
    address = '4321 West Flamingo Road',
    website = 'https://www.palms.com/index.php/entertainment/pearl-theater',
    zip_code = '89103',
    country = 'US',
    timezone = 'America/Los_Angeles'
WHERE id = 2567
  AND name = 'Pearl Concert Theater at Palms Casino Resort'
  AND city = 'Las Vegas'
  AND state = 'NV'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-16',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'ticketmaster_comedy',
            'replacement_ticketmaster_id', 'KovZpaKAZe',
            'rationale', 'Temporary tour_dates source replaced after verified ticketmaster_comedy scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1575
  AND club_id = 2567
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
    2567,
    'ticketmaster'::"ScrapingPlatform",
    'ticketmaster_comedy',
    'KovZpaKAZe',
    'https://www.ticketmaster.com/pearl-concert-theater-at-palms-casino-tickets-las-vegas/venue/189126',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-16',
            'official_site', 'https://www.palms.com',
            'official_calendar_url', 'https://www.palms.com/index.php/entertainment/pearl-theater',
            'ticketmaster_venue_id', 'KovZpaKAZe',
            'ticketmaster_public_venue_id', '189126',
            'sample_event_detail', 'https://www.axs.com/events/1338353/leslie-jones-tickets?skin=palmscasinoresort',
            'verification', 'Ticketmaster Discovery API returned 41 total venue events and 1 Comedy-classified event; existing ticketmaster_comedy scraper transformed 1 comedy show.'
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
                2567,
                'Pearl Concert Theater at Palms Casino Resort',
                'pearl concert theater at palms casino resort',
                'Las Vegas',
                'NV',
                'las vegas',
                'nv',
                '20260516113000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2567,
                'Pearl Theater',
                'pearl theater',
                'Las Vegas',
                'NV',
                'las vegas',
                'nv',
                '20260516113000: Ticketmaster venue onboarding',
                TRUE
            ),
            (
                2567,
                'Pearl Concert Theater',
                'pearl concert theater',
                'Las Vegas',
                'NV',
                'las vegas',
                'nv',
                '20260516113000: Ticketmaster venue onboarding',
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
