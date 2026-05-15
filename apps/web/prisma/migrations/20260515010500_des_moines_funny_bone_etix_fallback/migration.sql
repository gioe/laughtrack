-- Switch canonical Des Moines Funny Bone back to Etix with the public
-- funnybone.com fallback enabled in scraper code, and hide the duplicate
-- tour_dates stub discovered for the same venue.
--
-- Verification on 2026-05-15:
--   * Canonical club 1030 is visible/active in West Des Moines, IA.
--   * Existing canonical source 560 is the stale Ticketmaster source
--     (ticketmaster_id Z7r9jZa7pC) now returning 0 events.
--   * Duplicate club 2461 has 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * Duplicate source 1469 is an enabled tour_dates source.
--   * No Des Moines aliases currently exist for club 1030.

CREATE TEMP TABLE _des_moines_funny_bone_repair (
    canonical_id integer PRIMARY KEY,
    canonical_name text NOT NULL,
    canonical_city text NOT NULL,
    canonical_state text NOT NULL,
    canonical_source_id integer NOT NULL,
    stale_ticketmaster_id text NOT NULL,
    etix_source_url text NOT NULL,
    duplicate_id integer NOT NULL,
    duplicate_name text NOT NULL,
    duplicate_city text NOT NULL,
    duplicate_state text NOT NULL,
    duplicate_source_id integer NOT NULL,
    alias_name text NOT NULL
) ON COMMIT DROP;

INSERT INTO _des_moines_funny_bone_repair (
    canonical_id,
    canonical_name,
    canonical_city,
    canonical_state,
    canonical_source_id,
    stale_ticketmaster_id,
    etix_source_url,
    duplicate_id,
    duplicate_name,
    duplicate_city,
    duplicate_state,
    duplicate_source_id,
    alias_name
)
VALUES (
    1030,
    'Des Moines Funny Bone',
    'West Des Moines',
    'IA',
    560,
    'Z7r9jZa7pC',
    'https://www.etix.com/ticket/v/28453/funny-bone-comedy-club-des-moines',
    2461,
    'Funny Bone Comedy Club - Des Moines',
    'West Des Moines',
    'IA',
    1469,
    'Funny Bone Comedy Club - Des Moines'
);

DO $$
DECLARE
    bad_count integer;
BEGIN
    SELECT COUNT(*)
    INTO bad_count
    FROM _des_moines_funny_bone_repair m
    LEFT JOIN clubs canonical_club
        ON canonical_club.id = m.canonical_id
       AND canonical_club.name = m.canonical_name
       AND canonical_club.city = m.canonical_city
       AND canonical_club.state = m.canonical_state
       AND canonical_club.visible = TRUE
       AND canonical_club.status = 'active'
       AND canonical_club.chain_id = 3
    LEFT JOIN scraping_sources canonical_source
        ON canonical_source.id = m.canonical_source_id
       AND canonical_source.club_id = m.canonical_id
       AND canonical_source.platform = 'ticketmaster'::"ScrapingPlatform"
       AND canonical_source.scraper_key = 'live_nation'
       AND canonical_source.ticketmaster_id = m.stale_ticketmaster_id
       AND canonical_source.enabled = TRUE
    LEFT JOIN clubs duplicate_club
        ON duplicate_club.id = m.duplicate_id
       AND duplicate_club.name = m.duplicate_name
       AND duplicate_club.city = m.duplicate_city
       AND duplicate_club.state = m.duplicate_state
       AND duplicate_club.visible = TRUE
       AND duplicate_club.status = 'active'
    LEFT JOIN scraping_sources duplicate_source
        ON duplicate_source.id = m.duplicate_source_id
       AND duplicate_source.club_id = m.duplicate_id
       AND duplicate_source.platform = 'tour_dates'::"ScrapingPlatform"
       AND duplicate_source.scraper_key = 'tour_dates'
       AND duplicate_source.enabled = TRUE
    WHERE canonical_club.id IS NULL
       OR canonical_source.id IS NULL
       OR duplicate_club.id IS NULL
       OR duplicate_source.id IS NULL;

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot repair Des Moines Funny Bone: expected canonical or duplicate rows are missing or changed';
    END IF;

    SELECT COUNT(*)
    INTO bad_count
    FROM _des_moines_funny_bone_repair m
    WHERE EXISTS (SELECT 1 FROM shows WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM tagged_clubs WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM email_subscriptions WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM processed_emails WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM production_company_venues WHERE club_id = m.duplicate_id);

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate Des Moines Funny Bone: duplicate club has dependent rows';
    END IF;
END $$;

UPDATE scraping_sources ss
SET platform = 'etix'::"ScrapingPlatform",
    scraper_key = 'etix',
    source_url = m.etix_source_url,
    ticketmaster_id = NULL,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2233_source_repair', 'ticketmaster_to_etix_fallback',
        'previous_platform', 'ticketmaster',
        'previous_scraper_key', 'live_nation',
        'previous_ticketmaster_id', m.stale_ticketmaster_id,
        'etix_venue_id', '28453',
        'fallback_url', 'https://desmoines.funnybone.com/shows/',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
FROM _des_moines_funny_bone_repair m
WHERE ss.id = m.canonical_source_id
  AND ss.club_id = m.canonical_id
  AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
  AND ss.scraper_key = 'live_nation'
  AND ss.ticketmaster_id = m.stale_ticketmaster_id
  AND ss.enabled = TRUE;

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
SELECT
    canonical_id,
    alias_name,
    lower(alias_name),
    duplicate_city,
    duplicate_state,
    lower(duplicate_city),
    lower(duplicate_state),
    '20260515010500: duplicate tour_dates stub ' || duplicate_id,
    TRUE
FROM _des_moines_funny_bone_repair
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    alias_name = EXCLUDED.alias_name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();

UPDATE clubs c
SET name = m.duplicate_name || ' (duplicate of club ' || m.canonical_id || ')',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
FROM _des_moines_funny_bone_repair m
WHERE c.id = m.duplicate_id
  AND c.name = m.duplicate_name
  AND c.city = m.duplicate_city
  AND c.state = m.duplicate_state
  AND c.visible = TRUE
  AND c.status = 'active';

UPDATE scraping_sources ss
SET enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2233_tour_date_onboarding_disposition', 'duplicate_of_club_' || m.canonical_id,
        'canonical_club_id', m.canonical_id,
        'canonical_source_id', m.canonical_source_id,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
FROM _des_moines_funny_bone_repair m
WHERE ss.id = m.duplicate_source_id
  AND ss.club_id = m.duplicate_id
  AND ss.platform = 'tour_dates'::"ScrapingPlatform"
  AND ss.scraper_key = 'tour_dates';
