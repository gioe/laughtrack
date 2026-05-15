-- Onboard Wang Theatre / Boch Center Wang Theatre from tour_dates-only discovery.
--
-- Investigation on 2026-05-15 found the official Boch Center events listing:
--   https://www.bochcenter.org/events/all
-- and Ticketmaster venue:
--   https://www.ticketmaster.com/boch-center-wang-theatre-tickets-boston/venue/8248
-- Ticketmaster Discovery venue id KovZpZAJd6FA returned upcoming comedy events,
-- including Nurse John: Against Medical Advice Tour on 2026-09-25.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2505
          AND name = 'Wang Theatre'
          AND city = 'Boston'
          AND state = 'MA'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Wang Theatre: club 2505 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE club_id <> 2505
          AND ticketmaster_id = 'KovZpZAJd6FA'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Wang Theatre: Ticketmaster venue KovZpZAJd6FA is already assigned to another club';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.bochcenter.org/',
    address = '270 Tremont Street',
    zip_code = '02116',
    timezone = 'America/New_York'
WHERE id = 2505
  AND name = 'Wang Theatre'
  AND city = 'Boston'
  AND state = 'MA';

UPDATE scraping_sources
SET priority = 1,
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_dates_preserved_as_fallback', TRUE,
        'fallback_after_source', 'ticketmaster',
        'onboarded_platform', 'ticketmaster',
        'onboarded_scraper_key', 'live_nation',
        'onboarded_ticketmaster_id', 'KovZpZAJd6FA',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE club_id = 2505
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND priority = 0;

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    ticketmaster_id,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2505,
    'ticketmaster',
    'live_nation',
    'KovZpZAJd6FA',
    'https://www.ticketmaster.com/boch-center-wang-theatre-tickets-boston/venue/8248',
    TRUE,
    0,
    jsonb_build_object(
        'official_events_url', 'https://www.bochcenter.org/events/all',
        'official_venue_name', 'Boch Center Wang Theatre',
        'ticketmaster_venue_numeric_id', '8248',
        'tour_dates_seed_event_url', 'https://www.vividseats.com/nurse-john-tickets-boston-wang-theatre-9-25-2026/production/7024444',
        'verified_sample_event', 'Nurse John: Against Medical Advice Tour',
        'verified_sample_event_date', '2026-09-25'
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    ticketmaster_id = EXCLUDED.ticketmaster_id,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
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
        2505,
        'Wang Theatre',
        'wang theatre',
        'Boston',
        'MA',
        'boston',
        'ma',
        'tour_dates onboarding 2026-05-15',
        TRUE
    ),
    (
        2505,
        'Boch Center Wang Theatre',
        'boch center wang theatre',
        'Boston',
        'MA',
        'boston',
        'ma',
        'ticketmaster venue KovZpZAJd6FA',
        TRUE
    ),
    (
        2505,
        'Wang Theatre at the Boch Center',
        'wang theatre at the boch center',
        'Boston',
        'MA',
        'boston',
        'ma',
        'official venue alias',
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
