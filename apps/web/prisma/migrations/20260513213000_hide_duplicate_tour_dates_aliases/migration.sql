-- Hide duplicate tour_dates stubs that alias already-supported clubs.
--
-- Verification on 2026-05-13:
--   * Each duplicate club below has 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * Each canonical club is visible, active, and has the expected enabled
--     non-tour_dates source.
--   * The duplicate names are seeded as club_aliases on their canonical clubs
--     so future tour-date discovery resolves to the supported venue.

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
    (2522, 'Cobbs Comedy Club', 'San Francisco', 'CA', 1530, 191, 'Cobb''s Comedy Club', 539, 'Cobbs Comedy Club'),
    (2910, 'Off the Hook Comedy Club', 'Naples', 'FL', 1918, 122, 'Off The Hook Comedy Club', 225, 'Off the Hook Comedy Club'),
    (2923, 'DC Comedy Loft', 'Washington', 'DC', 1931, 71, 'The Comedy Loft of DC', 371, 'DC Comedy Loft'),
    (3012, 'Funny Bone', 'Orlando', 'FL', 2020, 1027, 'Orlando Funny Bone', 105, 'Funny Bone'),
    (2544, 'Funny Bone - Tampa', 'Tampa', 'FL', 1552, 1053, 'Tampa Funny Bone', 550, 'Funny Bone - Tampa'),
    (2626, 'Magooby''s Joke House', 'Lutherville Timonium', 'MD', 1634, 118, 'Magoobys Joke House', 415, 'Magooby''s Joke House'),
    (2548, 'Funny Bone - Omaha', 'Omaha', 'NE', 1556, 1026, 'Omaha Funny Bone', 48, 'Funny Bone - Omaha'),
    (2440, 'Wiseguys Comedy Cafe - Town Square', 'Las Vegas', 'NV', 1448, 546, 'Wiseguys - Town Square', 126, 'Wiseguys Comedy Cafe - Town Square'),
    (2559, 'Hilarities 4th Street Theatre At Pickwick & Frolic', 'Cleveland', 'OH', 1567, 113, 'Hilarities 4th Street Theatre', 29, 'Hilarities 4th Street Theatre At Pickwick & Frolic'),
    (2431, 'Funny Bone Comedy Club - Columbus', 'Columbus', 'OH', 1439, 308, 'Funny Bone Columbus', 191, 'Funny Bone Comedy Club - Columbus'),
    (2451, 'Bricktown Comedy Club - OKC', 'Oklahoma City', 'OK', 1459, 90, 'Bricktown Comedy Club', 584, 'Bricktown Comedy Club - OKC'),
    (2475, 'Stress Factory Comedy Club - Valley Forge', 'King Of Prussia', 'PA', 1483, 130, 'Stress Factory - Valley Forge', 598, 'Stress Factory Comedy Club - Valley Forge'),
    (2514, 'Parking Mic Drop Comedy Plano Parking', 'Plano', 'TX', 1522, 119, 'Mic Drop Comedy Plano', 39, 'Parking Mic Drop Comedy Plano Parking'),
    (2517, 'Parking Chicago Improv Parking', 'Schaumburg', 'IL', 1525, 31, 'Chicago Improv', 607, 'Parking Chicago Improv Parking');

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
       AND canonical_source.platform <> 'tour_dates'::"ScrapingPlatform"
       AND canonical_source.enabled = TRUE
    WHERE duplicate_club.id IS NULL
       OR duplicate_source.id IS NULL
       OR canonical_club.id IS NULL
       OR canonical_source.id IS NULL;

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate tour_dates aliases: % expected duplicate/canonical rows are missing or changed', bad_count;
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
        RAISE EXCEPTION 'Cannot hide duplicate tour_dates aliases: % duplicate clubs have dependent rows', bad_count;
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
    '20260513213000: duplicate tour_dates stub ' || duplicate_id,
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
        'verified_at', '2026-05-13'
    ),
    updated_at = NOW()
FROM _duplicate_tour_dates_aliases m
WHERE ss.id = m.duplicate_source_id
  AND ss.club_id = m.duplicate_id
  AND ss.platform = 'tour_dates'::"ScrapingPlatform"
  AND ss.scraper_key = 'tour_dates';
