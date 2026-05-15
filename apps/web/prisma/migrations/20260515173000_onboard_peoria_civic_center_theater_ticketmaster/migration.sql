-- Onboard Peoria Civic Center - Prairie Home Alliance Theater (club 2508)
-- from temporary tour_dates discovery to the existing generic Ticketmaster
-- scraper, and hide duplicate tour_dates stub club 2859.
--
-- Verification on 2026-05-15:
--   * Official site https://theater.peoriaciviccenter.com/ has an event
--     calendar at https://theater.peoriaciviccenter.com/events-tickets/.
--   * Ticketmaster venue page
--     https://www.ticketmaster.com/prairie-home-alliance-theater-tickets-peoria/venue/57937
--     lists 201 SW Jefferson Ave, Peoria, IL 61602.
--   * Ticketmaster Discovery venue search returns KovZ917ARXp / public venue
--     57937 for Prairie Home Alliance Theater, Peoria, IL.
--   * Discovery API returned 32 upcoming venue events.
--   * Existing live_nation scraper transformed 6 comedy shows, including
--     Whose Live Anyway?, Gary Owen, Michael Blaustein, and Nurse John.
--   * Clubs 2508 and 2859 have 0 shows and no tagged/subscription/email/
--     production-company dependent rows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2508
          AND c.name = 'Peoria Civic Center - Prairie Home Alliance Theater'
          AND c.city = 'Peoria'
          AND c.state = 'IL'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1516
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Peoria Civic Center theater club 2508: expected tour_dates source is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2859
          AND c.name = 'Prairie Home Alliance Theater'
          AND c.city = 'Peoria'
          AND c.state = 'IL'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1867
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate Prairie Home Alliance Theater club 2859: expected tour_dates source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id IN (2508, 2859)
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id IN (2508, 2859)
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id IN (2508, 2859)
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id IN (2508, 2859)
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id IN (2508, 2859)
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Peoria Civic Center theater: dependent rows exist on club 2508 or duplicate club 2859';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ticketmaster'::"ScrapingPlatform"
          AND ticketmaster_id = 'KovZ917ARXp'
          AND club_id <> 2508
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Peoria Civic Center theater: Ticketmaster venue KovZ917ARXp is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET name = 'Prairie Home Alliance Theater (duplicate of club 2508)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2859
  AND name = 'Prairie Home Alliance Theater'
  AND city = 'Peoria'
  AND state = 'IL'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_2508',
        'canonical_club_id', 2508,
        'canonical_ticketmaster_id', 'KovZ917ARXp',
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE id = 1867
  AND club_id = 2859
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

UPDATE clubs
SET
    name = 'Peoria Civic Center - Prairie Home Alliance Theater',
    address = '201 SW Jefferson Ave',
    website = 'https://theater.peoriaciviccenter.com',
    city = 'Peoria',
    state = 'IL',
    zip_code = '61602',
    country = 'US',
    timezone = 'America/Chicago'
WHERE id = 2508
  AND name = 'Peoria Civic Center - Prairie Home Alliance Theater'
  AND city = 'Peoria'
  AND state = 'IL';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-15',
            'replacement_platform', 'ticketmaster',
            'replacement_scraper_key', 'live_nation',
            'replacement_ticketmaster_id', 'KovZ917ARXp',
            'rationale', 'Temporary tour_dates source replaced after verified live_nation scrape produced comedy shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1516
  AND club_id = 2508
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
    2508,
    'ticketmaster'::"ScrapingPlatform",
    'live_nation',
    'KovZ917ARXp',
    'https://www.ticketmaster.com/prairie-home-alliance-theater-tickets-peoria/venue/57937',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-15',
            'official_site', 'https://theater.peoriaciviccenter.com',
            'official_calendar_url', 'https://theater.peoriaciviccenter.com/events-tickets/',
            'ticketmaster_venue_id', 'KovZ917ARXp',
            'ticketmaster_public_venue_id', '57937',
            'verification', 'Ticketmaster Discovery API returned 32 total venue events; existing live_nation scraper transformed 6 comedy shows.'
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
        2508,
        'Peoria Civic Center - Prairie Home Alliance Theater',
        'peoria civic center - prairie home alliance theater',
        'Peoria',
        'IL',
        'peoria',
        'il',
        '20260515173000: tour_dates onboarding and duplicate club 2859',
        TRUE
    ),
    (
        2508,
        'Prairie Home Alliance Theater',
        'prairie home alliance theater',
        'Peoria',
        'IL',
        'peoria',
        'il',
        '20260515173000: tour_dates onboarding and duplicate club 2859',
        TRUE
    ),
    (
        2508,
        'Peoria Civic Center Theatre',
        'peoria civic center theatre',
        'Peoria',
        'IL',
        'peoria',
        'il',
        '20260515173000: tour_dates onboarding and duplicate club 2859',
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
