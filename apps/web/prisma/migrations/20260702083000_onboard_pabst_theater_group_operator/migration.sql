-- Onboard Pabst Theater Group as an operator-level source target.
--
-- Pabst Theater Group is not a physical venue. Its /events page lists shows
-- across multiple distinct Milwaukee theaters, so the scraper runs from a
-- source_targets row and routes each event to the physical clubs row named in
-- the event card.

INSERT INTO source_targets (
    name,
    slug,
    target_type,
    platform,
    source_url,
    visible,
    enabled,
    status,
    metadata
)
VALUES (
    'Pabst Theater Group',
    'pabst-theater-group',
    'operator',
    'custom'::"ScrapingPlatform",
    'https://www.pabsttheatergroup.com/events',
    FALSE,
    TRUE,
    'active',
    jsonb_build_object(
        'comedy_filter', TRUE,
        'default_show_time', '19:00',
        'comedy_title_allowlist', ARRAY[
            'anthony jeselnik',
            'ben schwartz',
            'derrick stroup',
            'daniel sloss',
            'hasan',
            'josh johnson',
            'jonathan van ness',
            'kevin smith',
            'matt mathews',
            'mojo brookzz',
            'ron funches',
            'ronny chieng',
            'small town murder',
            'steve hofstetter',
            'wait wait',
            'zarna garg'
        ],
        'rationale', 'Operator calendar across multiple physical theaters; events are routed to venue clubs'
    )
)
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    target_type = EXCLUDED.target_type,
    platform = EXCLUDED.platform,
    source_url = EXCLUDED.source_url,
    visible = EXCLUDED.visible,
    enabled = EXCLUDED.enabled,
    status = EXCLUDED.status,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO scraping_sources (
    source_target_id,
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    st.id,
    NULL,
    'custom'::"ScrapingPlatform",
    'pabst_theater_group',
    'https://www.pabsttheatergroup.com/events',
    0,
    TRUE,
    '{}'::jsonb
FROM source_targets st
WHERE st.slug = 'pabst-theater-group'
ON CONFLICT (source_target_id, platform, priority) DO UPDATE
SET club_id = NULL,
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = EXCLUDED.enabled,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- Mixed-purpose physical theater, not a comedy-first club.
UPDATE clubs
SET club_type = 'venue',
    website = 'https://www.pabsttheatergroup.com/venues/detail/the-pabst-theater'
WHERE id = 5096
  AND name = 'Pabst Theater';

-- The aggregate source supersedes the overlapping per-venue Pabst pages. Keep
-- their config as historical context, but prevent duplicate ingestion.
UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'disabled_by', '20260702083000_onboard_pabst_theater_group_operator',
        'replacement_source_target_slug', 'pabst-theater-group',
        'replacement_scraper_key', 'pabst_theater_group',
        'reason', 'operator calendar routes Pabst events to physical venues'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE scraper_key = 'pabst_axs'
  AND club_id IN (5096, 9120, 9123)
  AND enabled = TRUE;

-- Fold duplicate Live Nation-created Riverside Theatre row into the canonical
-- Pabst Theater Group venue row.
CREATE TEMP TABLE pabst_duplicate_club_merges (
    old_id integer PRIMARY KEY,
    new_id integer NOT NULL,
    old_name text NOT NULL,
    new_name text NOT NULL,
    city text NOT NULL,
    state text NOT NULL
) ON COMMIT DROP;

INSERT INTO pabst_duplicate_club_merges (old_id, new_id, old_name, new_name, city, state)
VALUES (11395, 9123, 'Riverside Theatre - WI', 'The Riverside Theater', 'Milwaukee', 'WI');

DO $$
DECLARE
    valid_pair_count integer;
    old_show_count integer;
    dependent_ref_count integer;
BEGIN
    SELECT count(*)
    INTO valid_pair_count
    FROM pabst_duplicate_club_merges m
    JOIN clubs old_club ON old_club.id = m.old_id
    JOIN clubs new_club ON new_club.id = m.new_id
    WHERE old_club.name = m.old_name
      AND new_club.name = m.new_name
      AND old_club.city = m.city
      AND new_club.city = m.city
      AND old_club.state = m.state
      AND new_club.state = m.state
      AND old_club.visible = TRUE
      AND new_club.visible = TRUE
      AND old_club.status = 'active'
      AND new_club.status = 'active';

    IF valid_pair_count <> 1 THEN
        RAISE EXCEPTION 'Cannot consolidate Pabst Riverside duplicate: expected one active duplicate pair, found %', valid_pair_count;
    END IF;

    SELECT count(*) INTO old_show_count
    FROM shows
    WHERE club_id = 11395;

    IF old_show_count <> 3 THEN
        RAISE EXCEPTION 'Cannot consolidate Pabst Riverside duplicate: expected 3 shows on old club, found %', old_show_count;
    END IF;

    SELECT
        (SELECT count(*) FROM favorite_clubs WHERE club_id = 11395)
      + (SELECT count(*) FROM tagged_clubs WHERE club_id = 11395)
      + (SELECT count(*) FROM club_image_assets WHERE club_id = 11395)
      + (SELECT count(*) FROM processed_emails WHERE club_id = 11395)
      + (SELECT count(*) FROM production_company_venues WHERE club_id = 11395)
      + (SELECT count(*) FROM eventbrite_organizer_venues WHERE club_id = 11395)
      + (SELECT count(*) FROM email_subscriptions WHERE club_id = 11395)
      + (SELECT count(*) FROM ticket_purchase_click_events WHERE club_id = 11395)
    INTO dependent_ref_count;

    IF dependent_ref_count <> 0 THEN
        RAISE EXCEPTION 'Cannot consolidate Pabst Riverside duplicate: expected 0 dependent refs, found %', dependent_ref_count;
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
    verified,
    created_at,
    updated_at
)
SELECT
    m.new_id,
    m.old_name,
    btrim(regexp_replace(replace(lower(m.old_name), '&', ' and '), '[^a-z0-9]+', ' ', 'g')),
    m.city,
    m.state,
    btrim(regexp_replace(lower(m.city), '[^a-z0-9]+', ' ', 'g')),
    lower(m.state),
    '20260702083000_onboard_pabst_theater_group_operator',
    TRUE,
    NOW(),
    NOW()
FROM pabst_duplicate_club_merges m
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;

UPDATE shows s
SET club_id = m.new_id
FROM pabst_duplicate_club_merges m
WHERE s.club_id = m.old_id
  AND NOT EXISTS (
      SELECT 1
      FROM shows existing
      WHERE existing.club_id = m.new_id
        AND existing.date = s.date
        AND existing.room IS NOT DISTINCT FROM s.room
  );

DELETE FROM shows s
USING pabst_duplicate_club_merges m
WHERE s.club_id = m.old_id;

UPDATE scraping_sources ss
SET enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'duplicate_club_consolidation', jsonb_build_object(
            'migration', '20260702083000_onboard_pabst_theater_group_operator',
            'canonical_club_id', m.new_id,
            'canonical_club_name', m.new_name,
            'disabled_at', NOW(),
            'reason', 'Riverside Theatre - WI duplicate consolidated into The Riverside Theater'
        )
    ),
    updated_at = NOW()
FROM pabst_duplicate_club_merges m
WHERE ss.club_id = m.old_id;

UPDATE clubs old_club
SET visible = FALSE,
    status = 'closed',
    closed_at = NOW(),
    total_shows = 0,
    club_type = 'venue',
    description = concat_ws(
        E'\n\n',
        NULLIF(old_club.description, ''),
        'Duplicate row consolidated into club 9123 (The Riverside Theater) by migration 20260702083000_onboard_pabst_theater_group_operator.'
    )
FROM pabst_duplicate_club_merges m
WHERE old_club.id = m.old_id;

UPDATE clubs canonical
SET total_shows = counts.show_count
FROM (
    SELECT club_id, count(*)::integer AS show_count
    FROM shows
    WHERE club_id IN (9123)
    GROUP BY club_id
) counts
WHERE canonical.id = counts.club_id;

DO $$
DECLARE
    enabled_source_count integer;
    duplicate_visible_count integer;
BEGIN
    SELECT count(*)
    INTO enabled_source_count
    FROM scraping_sources ss
    JOIN source_targets st ON st.id = ss.source_target_id
    WHERE st.slug = 'pabst-theater-group'
      AND ss.club_id IS NULL
      AND ss.scraper_key = 'pabst_theater_group'
      AND ss.enabled = TRUE;

    IF enabled_source_count <> 1 THEN
        RAISE EXCEPTION 'Expected one enabled Pabst Theater Group source target source, found %', enabled_source_count;
    END IF;

    SELECT count(*)
    INTO duplicate_visible_count
    FROM clubs
    WHERE id = 11395
      AND visible = TRUE;

    IF duplicate_visible_count <> 0 THEN
        RAISE EXCEPTION 'Expected Riverside Theatre - WI duplicate to be hidden';
    END IF;
END $$;
