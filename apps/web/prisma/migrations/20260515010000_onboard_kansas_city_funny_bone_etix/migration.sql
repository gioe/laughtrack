-- Onboard Kansas City Funny Bone (club 2462) from tour_dates to the generic
-- Etix scraper using the venue-owned Funny Bone/Rockhouse public listing.
--
-- Verification on 2026-05-15:
--   * Official site: https://kc.funnybone.com/
--   * Address/phone from https://kc.funnybone.com/contact-us/
--   * The public Funny Bone page exposes Etix ticket links and the shared
--     Rockhouse event widget. The generic Etix scraper's Funny Bone public
--     source path extracted 31 upcoming events in a live in-memory check.
--   * Club 2462 had no dependent rows in shows, tagged_clubs,
--     email_subscriptions, processed_emails, or production_company_venues.

DO $$
DECLARE
    expected_tour_source_id integer := 1470;
    bad_count integer;
BEGIN
    SELECT COUNT(*)
    INTO bad_count
    FROM clubs c
    LEFT JOIN scraping_sources ss
        ON ss.id = expected_tour_source_id
       AND ss.club_id = c.id
       AND ss.platform = 'tour_dates'::"ScrapingPlatform"
       AND ss.scraper_key = 'tour_dates'
       AND ss.enabled = TRUE
    WHERE c.id = 2462
      AND c.name = 'Funny Bone Comedy Club (formerly Kansas City Improv)'
      AND c.city = 'Kansas City'
      AND c.state = 'MO'
      AND c.visible = TRUE
      AND c.status = 'active'
      AND ss.id IS NOT NULL;

    IF bad_count <> 1 THEN
        RAISE EXCEPTION 'Cannot onboard Kansas City Funny Bone: expected club/source rows are missing or changed';
    END IF;
END $$;

UPDATE clubs
SET name = 'Kansas City Funny Bone',
    address = '7260 NW 87th St, Kansas City, MO 64153',
    website = 'https://kc.funnybone.com',
    zip_code = '64153',
    phone_number = '(816) 759-5233',
    timezone = 'America/Chicago',
    chain_id = (SELECT id FROM chains WHERE slug = 'funny-bone')
WHERE id = 2462
  AND name = 'Funny Bone Comedy Club (formerly Kansas City Improv)'
  AND city = 'Kansas City'
  AND state = 'MO';

UPDATE scraping_sources
SET priority = 10,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'replaced_by_etix_public_source',
        'replacement_platform', 'etix',
        'replacement_source_url', 'https://kc.funnybone.com/',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
WHERE id = 1470
  AND club_id = 2462
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND enabled = TRUE;

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
VALUES (
    2462,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://kc.funnybone.com/',
    0,
    TRUE,
    jsonb_build_object(
        'verified_at', '2026-05-15',
        'official_site', 'https://kc.funnybone.com/',
        'ticketing_backend', 'etix',
        'source_note', 'Funny Bone/Rockhouse public listing with Etix ticket links'
    )
)
ON CONFLICT (club_id, platform, priority)
DO UPDATE SET
    scraper_key = EXCLUDED.scraper_key,
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
        2462,
        'Funny Bone Comedy Club (formerly Kansas City Improv)',
        'funny bone comedy club (formerly kansas city improv)',
        'Kansas City',
        'MO',
        'kansas city',
        'mo',
        '20260515010000: onboard Kansas City Funny Bone Etix',
        TRUE
    ),
    (
        2462,
        'Kansas City Improv',
        'kansas city improv',
        'Kansas City',
        'MO',
        'kansas city',
        'mo',
        '20260515010000: onboard Kansas City Funny Bone Etix',
        TRUE
    ),
    (
        2462,
        'Funny Bone Comedy Club',
        'funny bone comedy club',
        'Kansas City',
        'MO',
        'kansas city',
        'mo',
        '20260515010000: onboard Kansas City Funny Bone Etix',
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
