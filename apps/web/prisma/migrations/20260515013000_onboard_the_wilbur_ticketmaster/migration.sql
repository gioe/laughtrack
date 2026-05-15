-- Onboard The Wilbur (club 2463) from temporary tour_dates discovery to the
-- existing generic Ticketmaster scraper, and hide duplicate tour_dates stub
-- club 3025.
--
-- Verification on 2026-05-15:
--   * Official site https://thewilbur.com/ has a calendar at
--     https://thewilbur.com/calendar/ and event pages link to Ticketmaster.
--   * Ticketmaster Discovery venue search returns KovZpZAEAIvA / public venue 8252.
--   * Discovery API returned 85 upcoming events for the venue.
--   * Existing live_nation scraper transformed 54 comedy-eligible shows,
--     including Robby Hoffman, Dave Attell, Michael Blackson, and Aziz Ansari.
--   * Clubs 2463 and 3025 have 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * club_aliases had no existing Boston Wilbur aliases.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2463
          AND c.name = 'The Wilbur'
          AND c.city = 'Boston'
          AND c.state = 'MA'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1471
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard The Wilbur club 2463: expected tour_dates source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 3025
          AND c.name = 'Wilbur Theatre'
          AND c.city = 'Boston'
          AND c.state = 'MA'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 2033
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate Wilbur Theatre club 3025: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id IN (2463, 3025)
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id IN (2463, 3025)
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id IN (2463, 3025)
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id IN (2463, 3025)
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id IN (2463, 3025)
    ) THEN
        RAISE EXCEPTION 'Cannot onboard The Wilbur: dependent rows exist on club 2463 or duplicate club 3025';
    END IF;
END $$;

UPDATE clubs
SET name = 'Wilbur Theatre (duplicate of club 2463)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 3025
  AND name = 'Wilbur Theatre'
  AND city = 'Boston'
  AND state = 'MA'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_2463',
        'canonical_club_id', 2463,
        'canonical_ticketmaster_id', 'KovZpZAEAIvA',
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE club_id = 3025
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

UPDATE clubs
SET
    name = 'The Wilbur',
    address = '246 Tremont St.',
    website = 'https://thewilbur.com',
    city = 'Boston',
    state = 'MA',
    zip_code = '02116',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2463
  AND name = 'The Wilbur'
  AND city = 'Boston'
  AND state = 'MA';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZpZAEAIvA',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy-eligible shows.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 2463
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
    2463,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZpZAEAIvA',
    'https://www.ticketmaster.com/the-wilbur-tickets-boston/venue/8252',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://thewilbur.com',
            'official_calendar_url', 'https://thewilbur.com/calendar/',
            'ticketmaster_venue_id', 'KovZpZAEAIvA',
            'ticketmaster_public_venue_id', '8252',
            'verification', 'Ticketmaster Discovery API returned 85 total venue events; existing live_nation scraper transformed 54 comedy-eligible shows.'
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
        2463,
        'The Wilbur',
        'the wilbur',
        'Boston',
        'MA',
        'boston',
        'ma',
        '20260515013000: tour_dates onboarding and duplicate club 3025',
        TRUE
    ),
    (
        2463,
        'Wilbur Theatre',
        'wilbur theatre',
        'Boston',
        'MA',
        'boston',
        'ma',
        '20260515013000: tour_dates onboarding and duplicate club 3025',
        TRUE
    ),
    (
        2463,
        'The Wilbur Theatre',
        'the wilbur theatre',
        'Boston',
        'MA',
        'boston',
        'ma',
        '20260515013000: tour_dates onboarding and duplicate club 3025',
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
