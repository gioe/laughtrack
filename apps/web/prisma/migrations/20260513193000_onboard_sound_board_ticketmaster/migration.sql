-- Onboard Sound Board Theater (club 2414) from temporary tour_dates discovery
-- to the existing generic Ticketmaster scraper, and hide duplicate tour_dates
-- stub club 2832.
--
-- Verification on 2026-05-13:
--   * Official venue pages:
--       https://www.soundboarddetroit.com/default.aspx
--       https://www.313presents.com/venue/sound-board-at-motorcity-casino-hotel
--   * Official/venue pages point ticketing to Ticketmaster.
--   * Ticketmaster Discovery venue: KovZpZAFAE1A / public venue 66095.
--   * Discovery API returned 14 upcoming events for the venue.
--   * Existing live_nation scraper transformed 3 comedy-eligible shows:
--       D.L. Hughley, Maz Jobrani, Rickey Smiley.
--   * Clubs 2414 and 2832 have 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * club_aliases had no existing Detroit Sound Board aliases.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2414
          AND c.name = 'Sound Board Theater'
          AND c.city = 'Detroit'
          AND c.state = 'MI'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1422
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Sound Board club 2414: expected tour_dates source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2832
          AND c.name = 'Sound Board at MotorCity Casino Hotel'
          AND c.city = 'Detroit'
          AND c.state = 'MI'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1840
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate Sound Board club 2832: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id IN (2414, 2832)
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id IN (2414, 2832)
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id IN (2414, 2832)
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id IN (2414, 2832)
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id IN (2414, 2832)
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Sound Board: dependent rows exist on club 2414 or duplicate club 2832';
    END IF;
END $$;

UPDATE clubs
SET name = 'Sound Board at MotorCity Casino Hotel (duplicate of club 2414)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2832
  AND name = 'Sound Board at MotorCity Casino Hotel'
  AND city = 'Detroit'
  AND state = 'MI'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_2414',
        'canonical_club_id', 2414,
        'canonical_ticketmaster_id', 'KovZpZAFAE1A',
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    ),
    updated_at = NOW()
WHERE club_id = 2832
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

UPDATE clubs
SET
    name = 'Sound Board at MotorCity Casino Hotel',
    address = '2901 Grand River Ave',
    website = 'https://www.soundboarddetroit.com/default.aspx',
    city = 'Detroit',
    state = 'MI',
    zip_code = '48201',
    country = 'US',
    phone_number = '313-309-4700',
    timezone = 'America/Detroit'
WHERE id = 2414;

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-13',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAFAE1A',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy-eligible shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2414
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
    2414,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAFAE1A',
    'https://www.ticketmaster.com/sound-board-at-motorcity-casino-hotel-tickets-detroit/venue/66095',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-13',
            'official_site', 'https://www.soundboarddetroit.com/default.aspx',
            'secondary_venue_page', 'https://www.313presents.com/venue/sound-board-at-motorcity-casino-hotel',
            'ticketmaster_venue_id', 'KovZpZAFAE1A',
            'ticketmaster_public_venue_id', '66095',
            'verification', 'Ticketmaster Discovery API returned 14 total venue events; existing live_nation scraper transformed 3 comedy-eligible shows.'
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
        EXECUTE $alias_sql$
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
                    2414,
                    'Sound Board Theater',
                    'sound board theater',
                    'Detroit',
                    'MI',
                    'detroit',
                    'mi',
                    '20260513193000: tour_dates onboarding and duplicate club 2832',
                    TRUE
                ),
                (
                    2414,
                    'Sound Board at MotorCity Casino Hotel',
                    'sound board at motorcity casino hotel',
                    'Detroit',
                    'MI',
                    'detroit',
                    'mi',
                    '20260513193000: tour_dates onboarding and duplicate club 2832',
                    TRUE
                ),
                (
                    2414,
                    'Sound Board',
                    'sound board',
                    'Detroit',
                    'MI',
                    'detroit',
                    'mi',
                    '20260513193000: tour_dates onboarding and duplicate club 2832',
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
                updated_at = NOW()
        $alias_sql$;
    END IF;
END $$;
