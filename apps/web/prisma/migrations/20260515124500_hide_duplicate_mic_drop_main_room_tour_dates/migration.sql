-- Hide duplicate tour_dates stubs for Mic Drop Comedy San Diego.
--
-- Verification on 2026-05-15:
--   * Duplicate clubs 2482 and 3004 have 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * Canonical club 486 ("Mic Drop Comedy") is visible, active, and has an
--     enabled SeatEngine source (id 530, scraper_key 'seatengine',
--     seatengine_id 462).
--   * A targeted scrape of club 486 on 2026-05-15 returned 322 shows from
--     SeatEngine venue 462.
--   * The official site is https://www.micdropcomedysandiego.com/ and its
--     footer is powered by Seat Engine.
--   * Club 3004's evidence URL is the official event page
--     https://www.micdropcomedysandiego.com/events/120087 for DERAY DAVIS;
--     canonical club 486 already has five DERAY DAVIS shows from SeatEngine.
--   * The duplicate display names are seeded as club_aliases on the canonical
--     club so future tour-date discovery resolves to the supported venue.

CREATE TEMP TABLE _duplicate_tour_dates_aliases (
    duplicate_id integer PRIMARY KEY,
    duplicate_name text NOT NULL,
    duplicate_city text NOT NULL,
    duplicate_state text NOT NULL,
    duplicate_source_id integer NOT NULL,
    canonical_id integer NOT NULL,
    canonical_name text NOT NULL,
    canonical_source_id integer NOT NULL,
    alias_name text NOT NULL
) ON COMMIT DROP;

INSERT INTO _duplicate_tour_dates_aliases (
    duplicate_id,
    duplicate_name,
    duplicate_city,
    duplicate_state,
    duplicate_source_id,
    canonical_id,
    canonical_name,
    canonical_source_id,
    alias_name
)
VALUES
    (2482, 'Main Room at Mic Drop Comedy', 'San Diego', 'CA', 1490, 486, 'Mic Drop Comedy', 530, 'Main Room at Mic Drop Comedy'),
    (3004, 'Mic Drop', 'San Diego', 'CA', 2012, 486, 'Mic Drop Comedy', 530, 'Mic Drop');

DO $$
DECLARE
    bad_count integer;
BEGIN
    SELECT COUNT(*)
    INTO bad_count
    FROM _duplicate_tour_dates_aliases m
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
    LEFT JOIN clubs canonical_club
        ON canonical_club.id = m.canonical_id
       AND canonical_club.name = m.canonical_name
       AND canonical_club.visible = TRUE
       AND canonical_club.status = 'active'
    LEFT JOIN scraping_sources canonical_source
        ON canonical_source.id = m.canonical_source_id
       AND canonical_source.club_id = m.canonical_id
       AND canonical_source.platform = 'seatengine'::"ScrapingPlatform"
       AND canonical_source.scraper_key = 'seatengine'
       AND canonical_source.seatengine_id = 462
       AND canonical_source.enabled = TRUE
    WHERE duplicate_club.id IS NULL
       OR duplicate_source.id IS NULL
       OR canonical_club.id IS NULL
       OR canonical_source.id IS NULL;

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate Mic Drop tour_dates stubs: % expected duplicate/canonical rows are missing or changed', bad_count;
    END IF;

    SELECT COUNT(*)
    INTO bad_count
    FROM _duplicate_tour_dates_aliases m
    WHERE EXISTS (SELECT 1 FROM shows WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM tagged_clubs WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM email_subscriptions WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM processed_emails WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM production_company_venues WHERE club_id = m.duplicate_id);

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate Mic Drop tour_dates stubs: % duplicate clubs have dependent rows', bad_count;
    END IF;
END $$;

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
    '20260515124500: duplicate tour_dates stub ' || duplicate_id,
    TRUE
FROM _duplicate_tour_dates_aliases
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
SET address = '8878 Clairemont Mesa Blvd',
    city = 'San Diego',
    state = 'CA',
    website = 'https://www.micdropcomedysandiego.com'
WHERE c.id = 486
  AND c.name = 'Mic Drop Comedy'
  AND c.visible = TRUE
  AND c.status = 'active';

UPDATE clubs c
SET name = m.duplicate_name || ' (duplicate of club ' || m.canonical_id || ')',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
FROM _duplicate_tour_dates_aliases m
WHERE c.id = m.duplicate_id
  AND c.name = m.duplicate_name
  AND c.city = m.duplicate_city
  AND c.state = m.duplicate_state
  AND c.visible = TRUE
  AND c.status = 'active';

UPDATE scraping_sources ss
SET enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_' || m.canonical_id,
        'canonical_club_id', m.canonical_id,
        'canonical_source_id', m.canonical_source_id,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-15'
    ),
    updated_at = NOW()
FROM _duplicate_tour_dates_aliases m
WHERE ss.id = m.duplicate_source_id
  AND ss.club_id = m.duplicate_id
  AND ss.platform = 'tour_dates'::"ScrapingPlatform"
  AND ss.scraper_key = 'tour_dates';
