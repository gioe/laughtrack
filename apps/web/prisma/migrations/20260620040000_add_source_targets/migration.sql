-- TASK-3028: first-class non-venue scraper targets.
--
-- source_targets hold platform/national/aggregate scraper trigger identity that
-- is not a physical venue. Physical venues remain in clubs; producers remain in
-- production_companies; festivals remain clubs.club_type='festival'.
--
-- Only Ticketmaster National is migrated here because it has no dependent
-- shows/user data and can be moved without changing show attribution.

CREATE TABLE source_targets (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    target_type TEXT NOT NULL,
    platform "ScrapingPlatform",
    source_url TEXT,
    visible BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX source_targets_name_key
    ON source_targets(name);

CREATE UNIQUE INDEX source_targets_slug_key
    ON source_targets(slug);

CREATE INDEX source_targets_target_type_enabled_idx
    ON source_targets(target_type, enabled);

CREATE INDEX source_targets_platform_enabled_idx
    ON source_targets(platform, enabled);

ALTER TABLE scraping_sources
    ADD COLUMN source_target_id INTEGER;

ALTER TABLE scraping_sources
    ALTER COLUMN club_id DROP NOT NULL;

ALTER TABLE scraping_sources
    ADD CONSTRAINT scraping_sources_source_target_id_fkey
    FOREIGN KEY (source_target_id) REFERENCES source_targets(id)
    ON DELETE CASCADE ON UPDATE CASCADE;

CREATE UNIQUE INDEX scraping_sources_source_target_platform_priority_key
    ON scraping_sources(source_target_id, platform, priority);

CREATE INDEX scraping_sources_source_target_id_enabled_priority_idx
    ON scraping_sources(source_target_id, enabled, priority);

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
SELECT
    'Ticketmaster National',
    'ticketmaster-national',
    'platform',
    'ticketmaster'::"ScrapingPlatform",
    COALESCE(ss.source_url, 'www.ticketmaster.com'),
    FALSE,
    TRUE,
    'active',
    jsonb_build_object(
        'migrated_from_club_id', c.id,
        'migrated_by', 'TASK-3028',
        'rationale', 'National Ticketmaster platform trigger, not a physical venue'
    )
FROM clubs c
JOIN scraping_sources ss ON ss.club_id = c.id
WHERE c.id = 4036
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    target_type = EXCLUDED.target_type,
    platform = EXCLUDED.platform,
    source_url = EXCLUDED.source_url,
    visible = EXCLUDED.visible,
    enabled = EXCLUDED.enabled,
    status = EXCLUDED.status,
    metadata = source_targets.metadata || EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

UPDATE scraping_sources ss
SET source_target_id = st.id,
    club_id = NULL,
    metadata = COALESCE(ss.metadata, '{}'::jsonb) || jsonb_build_object(
        'migrated_from_club_id', 4036,
        'migrated_by', 'TASK-3028'
    ),
    updated_at = CURRENT_TIMESTAMP
FROM source_targets st
WHERE st.slug = 'ticketmaster-national'
  AND ss.club_id = 4036
  AND ss.platform = 'ticketmaster'
  AND ss.scraper_key = 'ticketmaster_national';

DO $$
DECLARE
    unsafe_count integer;
    moved_source_count integer;
BEGIN
    SELECT count(*) INTO moved_source_count
    FROM scraping_sources
    WHERE source_target_id = (
        SELECT id FROM source_targets WHERE slug = 'ticketmaster-national'
    )
      AND club_id IS NULL;

    IF moved_source_count <> 1 THEN
        RAISE EXCEPTION 'TASK-3028 expected 1 moved Ticketmaster National source, found %', moved_source_count;
    END IF;

    SELECT count(*) INTO unsafe_count
    FROM clubs c
    WHERE c.id = 4036
      AND (
        EXISTS (SELECT 1 FROM shows s WHERE s.club_id = c.id)
        OR EXISTS (SELECT 1 FROM tagged_clubs tc WHERE tc.club_id = c.id)
        OR EXISTS (SELECT 1 FROM favorite_clubs fc WHERE fc.club_id = c.id)
        OR EXISTS (SELECT 1 FROM email_subscriptions es WHERE es.club_id = c.id)
        OR EXISTS (SELECT 1 FROM processed_emails pe WHERE pe.club_id = c.id)
        OR EXISTS (SELECT 1 FROM production_company_venues pcv WHERE pcv.club_id = c.id)
        OR EXISTS (SELECT 1 FROM eventbrite_organizer_venues eov WHERE eov.club_id = c.id)
        OR EXISTS (SELECT 1 FROM club_aliases ca WHERE ca.club_id = c.id)
        OR EXISTS (SELECT 1 FROM club_image_assets cia WHERE cia.club_id = c.id)
        OR EXISTS (SELECT 1 FROM ticket_purchase_click_events tpce WHERE tpce.club_id = c.id)
        OR EXISTS (SELECT 1 FROM scraping_sources ss WHERE ss.club_id = c.id)
      );

    IF unsafe_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3028 refused to delete clubs.id=4036 because dependent rows remain';
    END IF;
END $$;

DELETE FROM clubs WHERE id = 4036;

ALTER TABLE scraping_sources
    ADD CONSTRAINT scraping_sources_exactly_one_owner_chk CHECK (
        (club_id IS NOT NULL AND source_target_id IS NULL)
        OR (club_id IS NULL AND source_target_id IS NOT NULL)
    );
