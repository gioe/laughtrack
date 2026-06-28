-- TASK-3469: Hide duplicate club "Improv Boulder" (11301) and alias it to the
-- canonical venue "The Louisville Underground" (11302).
--
-- Cleanup from TASK-3409/3410. Improv Boulder (club 11301, improvboulder.com,
-- 640 Main St, Louisville CO) was discovered at the SAME address as The
-- Louisville Underground (club 11302, 640 Main Street). Investigation on
-- 2026-06-28 confirmed Improv Boulder is the improv-show BRAND performing AT The
-- Louisville Underground, not a distinct venue:
--   * Same physical address (640 Main St, Louisville CO).
--   * improvboulder.com's only live ticketed event ("Improvarama",
--     eventbrite.com/e/improvarama-tickets-1989963666896) is organized by the
--     Eventbrite organizer the-louisville-underground-33945441325 — the SAME
--     organizer canonical club 11302 already scrapes (source 6953). So Improv
--     Boulder's shows are already captured under 11302; re-onboarding 11301
--     would duplicate them.
--   * improvboulder.com/events is an empty WordPress "The Events Calendar" with
--     a single past "Test January Show" whose venue is "Louisville Underground".
--   * Club 11301's own source 6952 was already neutralized by TASK-3410
--     (disabled) — it has 0 shows and no dependent rows.
--
-- Disposition (criterion 11411, duplicate branch — criterion 11410 N/A):
--   * Seed "Improv Boulder" as a verified club_alias on canonical club 11302 so
--     future discovery resolves the brand to the supported venue (no re-onboard).
--   * Mark club 11301 closed + hidden (already visible=false) and tag it as a
--     duplicate of 11302.
--   * Stamp the disposition onto the disabled source 6952 metadata.
--
-- Idempotent: guarded by expected current-state; the alias upserts on its unique
-- key; the club/source UPDATEs only fire while the pre-state still matches.

DO $$
DECLARE
    bad_count integer;
BEGIN
    -- Duplicate club 11301 must still be the active "Improv Boulder" row with no
    -- dependent rows, and canonical club 11302 must be the visible/active
    -- venue with an enabled Eventbrite source. Abort if reality has drifted.
    SELECT COUNT(*)
    INTO bad_count
    FROM (SELECT 1) x
    LEFT JOIN clubs dup
        ON dup.id = 11301
       AND dup.name = 'Improv Boulder'
       AND dup.city = 'Louisville'
       AND dup.state = 'CO'
       AND dup.status = 'active'
    LEFT JOIN clubs canon
        ON canon.id = 11302
       AND canon.visible = TRUE
       AND canon.status = 'active'
    LEFT JOIN scraping_sources canon_src
        ON canon_src.id = 6953
       AND canon_src.club_id = 11302
       AND canon_src.platform = 'eventbrite'::"ScrapingPlatform"
       AND canon_src.enabled = TRUE
    WHERE dup.id IS NULL
       OR canon.id IS NULL
       OR canon_src.id IS NULL;

    IF bad_count > 0 THEN
        RAISE EXCEPTION 'TASK-3469: expected Improv Boulder/Louisville Underground rows missing or changed — aborting';
    END IF;

    IF EXISTS (SELECT 1 FROM shows WHERE club_id = 11301)
       OR EXISTS (SELECT 1 FROM tagged_clubs WHERE club_id = 11301)
       OR EXISTS (SELECT 1 FROM email_subscriptions WHERE club_id = 11301)
       OR EXISTS (SELECT 1 FROM processed_emails WHERE club_id = 11301)
       OR EXISTS (SELECT 1 FROM production_company_venues WHERE club_id = 11301) THEN
        RAISE EXCEPTION 'TASK-3469: duplicate club 11301 has dependent rows — aborting';
    END IF;
END $$;

-- Seed the brand name as a verified alias on the canonical venue (normalized_*
-- columns are maintained DB-side by the club_aliases_set_normalized trigger;
-- the values supplied here are overwritten on INSERT, per TASK-3462).
INSERT INTO club_aliases (
    club_id, alias_name, normalized_alias_name, city, state,
    normalized_city, normalized_state, source, verified
)
VALUES (
    11302, 'Improv Boulder', 'improv boulder', 'Louisville', 'CO',
    'louisville', 'co', '20260628120000: duplicate brand of club 11302 (TASK-3469)', TRUE
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

-- Close + hide the duplicate club (visible is already FALSE from TASK-3410).
UPDATE clubs
SET name = 'Improv Boulder (duplicate of club 11302)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 11301
  AND name = 'Improv Boulder'
  AND status = 'active';

-- Stamp the duplicate disposition onto the already-disabled source 6952.
UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'disposition', 'duplicate_of_club_11302',
        'canonical_club_id', 11302,
        'canonical_source_id', 6953,
        'disabled_reason', 'improv_boulder_is_brand_at_the_louisville_underground',
        'verified_at', '2026-06-28',
        'task', 'TASK-3469'
    ),
    updated_at = NOW()
WHERE id = 6952
  AND club_id = 11301;
