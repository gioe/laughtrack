-- Consolidate exact normalized duplicate club rows found by the club audit.
--
-- Live DB verification before writing this migration:
--   * The Bellhouse (23) keeps The Bell House (6755)
--   * Laugh It Up Comedy Club (485) keeps LAUGH IT UP COMEDY CLUB (4962)
--   * Del Lago Resort & Casino (2415) keeps del Lago Resort & Casino (6875)
--   * Hart Theatre at the Egg (4697) keeps Hart Theatre at The Egg (5400)
--
-- The duplicate rows are all active and visible. Their duplicate shows mostly
-- collide with the canonical (club_id, date, room) unique key, so conflicting
-- duplicate shows are merged into the existing canonical shows while the two
-- non-conflicting Bell House shows move intact to club 23.

CREATE TEMP TABLE duplicate_club_merges (
    old_id integer PRIMARY KEY,
    new_id integer NOT NULL,
    old_name text NOT NULL,
    new_name text NOT NULL,
    city text NOT NULL,
    state text NOT NULL
) ON COMMIT DROP;

INSERT INTO duplicate_club_merges (old_id, new_id, old_name, new_name, city, state)
VALUES
    (6755, 23, 'The Bell House', 'The Bellhouse', 'Brooklyn', 'NY'),
    (4962, 485, 'LAUGH IT UP COMEDY CLUB', 'Laugh It Up Comedy Club', 'Poughkeepsie', 'NY'),
    (6875, 2415, 'del Lago Resort & Casino', 'Del Lago Resort & Casino', 'Waterloo', 'NY'),
    (5400, 4697, 'Hart Theatre at The Egg', 'Hart Theatre at the Egg', 'Albany', 'NY');

DO $$
DECLARE
    unexpected_count integer;
BEGIN
    SELECT count(*)
    INTO unexpected_count
    FROM duplicate_club_merges m
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

    IF unexpected_count <> 4 THEN
        RAISE EXCEPTION 'Cannot consolidate duplicate clubs: expected 4 active visible duplicate pairs, found %', unexpected_count;
    END IF;
END $$;

CREATE TEMP TABLE duplicate_show_merges AS
SELECT
    old_show.id AS old_show_id,
    new_show.id AS new_show_id,
    m.old_id AS old_club_id,
    m.new_id AS new_club_id
FROM duplicate_club_merges m
JOIN shows old_show ON old_show.club_id = m.old_id
JOIN shows new_show
  ON new_show.club_id = m.new_id
 AND new_show.date = old_show.date
 AND new_show.room IS NOT DISTINCT FROM old_show.room;

DO $$
DECLARE
    conflict_count integer;
BEGIN
    SELECT count(*) INTO conflict_count FROM duplicate_show_merges;

    IF conflict_count <> 79 THEN
        RAISE EXCEPTION 'Cannot consolidate duplicate clubs: expected 79 conflicting duplicate shows, found %', conflict_count;
    END IF;
END $$;

-- Preserve canonical lookup for the duplicate spellings/casing.
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
    'TASK-3015',
    TRUE,
    NOW(),
    NOW()
FROM duplicate_club_merges m
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;

-- Keep non-conflicting duplicate shows by moving the show rows themselves.
UPDATE shows s
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE s.club_id = m.old_id
  AND NOT EXISTS (
      SELECT 1
      FROM duplicate_show_merges dsm
      WHERE dsm.old_show_id = s.id
  );

-- Preserve click attribution before deleting conflicting duplicate show rows.
UPDATE ticket_purchase_click_events tpce
SET
    show_id = dsm.new_show_id,
    club_id = dsm.new_club_id
FROM duplicate_show_merges dsm
WHERE tpce.show_id = dsm.old_show_id;

UPDATE ticket_purchase_click_events tpce
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE tpce.club_id = m.old_id;

-- Move user-facing club references. Conflict-safe inserts preserve references
-- if the same user already follows the canonical club.
INSERT INTO favorite_clubs (profile_id, club_id)
SELECT fc.profile_id, m.new_id
FROM favorite_clubs fc
JOIN duplicate_club_merges m ON m.old_id = fc.club_id
ON CONFLICT (profile_id, club_id) DO NOTHING;

DELETE FROM favorite_clubs fc
USING duplicate_club_merges m
WHERE fc.club_id = m.old_id;

INSERT INTO tagged_clubs (club_id, tag_id)
SELECT m.new_id, tc.tag_id
FROM tagged_clubs tc
JOIN duplicate_club_merges m ON m.old_id = tc.club_id;

DELETE FROM tagged_clubs tc
USING duplicate_club_merges m
WHERE tc.club_id = m.old_id;

UPDATE club_image_assets cia
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE cia.club_id = m.old_id;

UPDATE processed_emails pe
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE pe.club_id = m.old_id;

UPDATE production_company_venues pcv
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE pcv.club_id = m.old_id
  AND NOT EXISTS (
      SELECT 1
      FROM production_company_venues existing
      WHERE existing.production_company_id = pcv.production_company_id
        AND existing.club_id = m.new_id
  );

DELETE FROM production_company_venues pcv
USING duplicate_club_merges m
WHERE pcv.club_id = m.old_id;

UPDATE eventbrite_organizer_venues eov
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE eov.club_id = m.old_id
  AND NOT EXISTS (
      SELECT 1
      FROM eventbrite_organizer_venues existing
      WHERE existing.production_company_id = eov.production_company_id
        AND existing.club_id = m.new_id
  );

DELETE FROM eventbrite_organizer_venues eov
USING duplicate_club_merges m
WHERE eov.club_id = m.old_id;

UPDATE email_subscriptions es
SET club_id = m.new_id
FROM duplicate_club_merges m
WHERE es.club_id = m.old_id
  AND NOT EXISTS (
      SELECT 1
      FROM email_subscriptions existing
      WHERE existing.club_id = m.new_id
  );

DELETE FROM email_subscriptions es
USING duplicate_club_merges m
WHERE es.club_id = m.old_id;

-- Preserve duplicate scraping source records without letting inactive duplicate
-- clubs continue to scrape. Moving them would violate canonical source
-- priority uniqueness for Hart and Laugh It Up.
UPDATE scraping_sources ss
SET
    enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'duplicate_club_consolidation', jsonb_build_object(
            'task', 'TASK-3015',
            'canonical_club_id', m.new_id,
            'canonical_club_name', m.new_name,
            'disabled_at', NOW(),
            'reason', 'source belonged to a duplicate club row consolidated into the canonical club'
        )
    ),
    updated_at = NOW()
FROM duplicate_club_merges m
WHERE ss.club_id = m.old_id;

-- Conflicting duplicate shows can now be removed. Non-conflicting shows were
-- moved above, and click events have been repointed to canonical show rows.
DELETE FROM shows s
USING duplicate_show_merges dsm
WHERE s.id = dsm.old_show_id;

DO $$
DECLARE
    remaining_direct_refs integer;
BEGIN
    SELECT
        (SELECT count(*) FROM shows s JOIN duplicate_club_merges m ON m.old_id = s.club_id)
      + (SELECT count(*) FROM favorite_clubs fc JOIN duplicate_club_merges m ON m.old_id = fc.club_id)
      + (SELECT count(*) FROM tagged_clubs tc JOIN duplicate_club_merges m ON m.old_id = tc.club_id)
      + (SELECT count(*) FROM club_image_assets cia JOIN duplicate_club_merges m ON m.old_id = cia.club_id)
      + (SELECT count(*) FROM processed_emails pe JOIN duplicate_club_merges m ON m.old_id = pe.club_id)
      + (SELECT count(*) FROM production_company_venues pcv JOIN duplicate_club_merges m ON m.old_id = pcv.club_id)
      + (SELECT count(*) FROM eventbrite_organizer_venues eov JOIN duplicate_club_merges m ON m.old_id = eov.club_id)
      + (SELECT count(*) FROM email_subscriptions es JOIN duplicate_club_merges m ON m.old_id = es.club_id)
      + (SELECT count(*) FROM ticket_purchase_click_events tpce JOIN duplicate_club_merges m ON m.old_id = tpce.club_id)
    INTO remaining_direct_refs;

    IF remaining_direct_refs <> 0 THEN
        RAISE EXCEPTION 'Cannot deactivate duplicate clubs: % direct dependent references remain', remaining_direct_refs;
    END IF;
END $$;

UPDATE clubs old_club
SET
    visible = FALSE,
    status = 'closed',
    closed_at = NOW(),
    total_shows = 0,
    description = concat_ws(
        E'\n\n',
        NULLIF(old_club.description, ''),
        'Duplicate row consolidated into club ' || m.new_id || ' (' || m.new_name || ') by TASK-3015.'
    )
FROM duplicate_club_merges m
WHERE old_club.id = m.old_id;

UPDATE clubs canonical
SET total_shows = counts.show_count
FROM (
    SELECT m.new_id, count(s.id)::integer AS show_count
    FROM duplicate_club_merges m
    LEFT JOIN shows s ON s.club_id = m.new_id
    GROUP BY m.new_id
) counts
WHERE canonical.id = counts.new_id;

DO $$
DECLARE
    remaining_duplicate_groups integer;
BEGIN
    SELECT count(*)
    INTO remaining_duplicate_groups
    FROM (
        SELECT
            regexp_replace(lower(name), '[^a-z0-9]+', '', 'g') AS normalized_name,
            lower(coalesce(city, '')) AS normalized_city,
            upper(coalesce(state, '')) AS normalized_state
        FROM clubs
        WHERE visible = TRUE
          AND status = 'active'
          AND id IN (23, 6755, 485, 4962, 2415, 6875, 4697, 5400)
        GROUP BY 1, 2, 3
        HAVING count(*) > 1
    ) duplicate_groups;

    IF remaining_duplicate_groups <> 0 THEN
        RAISE EXCEPTION 'Duplicate club consolidation left % active visible audited duplicate groups', remaining_duplicate_groups;
    END IF;
END $$;
