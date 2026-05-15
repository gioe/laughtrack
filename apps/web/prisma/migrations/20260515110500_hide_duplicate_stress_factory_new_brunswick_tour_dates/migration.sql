-- Hide duplicate tour_dates stub for Stress Factory New Brunswick (club 2470).
--
-- Verification on 2026-05-15:
--   * Duplicate club 2470 has 0 shows and no tagged/subscription/email/
--     production-company dependent rows.
--   * Canonical club 45 ("Stress Factory", New Brunswick NJ, chain 5) is
--     visible, active, and has enabled SeatEngine Classic source 246
--     (source_url 'newbrunswick.stressfactory.com/events').
--   * A targeted scrape of canonical club 45 with source 246 extracted 173
--     shows from https://newbrunswick.stressfactory.com/events and persisted
--     157 valid shows after ticket-price validation filtered 16 rows.
--   * No New Brunswick Stress Factory aliases currently exist in club_aliases.

CREATE TEMP TABLE _stress_factory_new_brunswick_duplicate (
    duplicate_id integer PRIMARY KEY,
    duplicate_name text NOT NULL,
    duplicate_city text NOT NULL,
    duplicate_state text NOT NULL,
    duplicate_source_id integer NOT NULL,
    canonical_id integer NOT NULL,
    canonical_name text NOT NULL,
    canonical_source_id integer NOT NULL
) ON COMMIT DROP;

INSERT INTO _stress_factory_new_brunswick_duplicate (
    duplicate_id,
    duplicate_name,
    duplicate_city,
    duplicate_state,
    duplicate_source_id,
    canonical_id,
    canonical_name,
    canonical_source_id
)
VALUES (
    2470,
    'Stress Factory Comedy Club',
    'New Brunswick',
    'NJ',
    1478,
    45,
    'Stress Factory',
    246
);

DO $$
DECLARE
    bad_count integer;
BEGIN
    SELECT COUNT(*)
    INTO bad_count
    FROM _stress_factory_new_brunswick_duplicate m
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
       AND canonical_club.city = m.duplicate_city
       AND canonical_club.state = m.duplicate_state
       AND canonical_club.visible = TRUE
       AND canonical_club.status = 'active'
       AND canonical_club.chain_id = 5
    LEFT JOIN scraping_sources canonical_source
        ON canonical_source.id = m.canonical_source_id
       AND canonical_source.club_id = m.canonical_id
       AND canonical_source.platform = 'seatengine'::"ScrapingPlatform"
       AND canonical_source.scraper_key = 'seatengine_classic'
       AND canonical_source.source_url = 'newbrunswick.stressfactory.com/events'
       AND canonical_source.enabled = TRUE
    WHERE duplicate_club.id IS NULL
       OR duplicate_source.id IS NULL
       OR canonical_club.id IS NULL
       OR canonical_source.id IS NULL;

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate Stress Factory New Brunswick: expected duplicate/canonical rows are missing or changed';
    END IF;

    SELECT COUNT(*)
    INTO bad_count
    FROM _stress_factory_new_brunswick_duplicate m
    WHERE EXISTS (SELECT 1 FROM shows WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM tagged_clubs WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM email_subscriptions WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM processed_emails WHERE club_id = m.duplicate_id)
       OR EXISTS (SELECT 1 FROM production_company_venues WHERE club_id = m.duplicate_id);

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Cannot hide duplicate Stress Factory New Brunswick: duplicate club has dependent rows';
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
    m.canonical_id,
    aliases.alias_name,
    lower(aliases.alias_name),
    m.duplicate_city,
    m.duplicate_state,
    lower(m.duplicate_city),
    lower(m.duplicate_state),
    '20260515110500: duplicate tour_dates stub ' || m.duplicate_id,
    TRUE
FROM _stress_factory_new_brunswick_duplicate m
CROSS JOIN (
    VALUES
        ('Stress Factory Comedy Club'),
        ('The Stress Factory Comedy Club'),
        ('Stress Factory Comedy Club New Brunswick')
) AS aliases(alias_name)
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
FROM _stress_factory_new_brunswick_duplicate m
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
FROM _stress_factory_new_brunswick_duplicate m
WHERE ss.id = m.duplicate_source_id
  AND ss.club_id = m.duplicate_id
  AND ss.platform = 'tour_dates'::"ScrapingPlatform"
  AND ss.scraper_key = 'tour_dates';
