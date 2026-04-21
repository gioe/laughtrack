-- [TASK-1693] Extract scraper configuration from clubs into scraping_sources.
-- Adds a normalized per-club source table, backfills it from the current club
-- columns, and keeps club identity data on clubs.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'ScrapingPlatform'
    ) THEN
        CREATE TYPE "ScrapingPlatform" AS ENUM (
            'custom',
            'crowdwork',
            'etix',
            'eventbrite',
            'jetbook',
            'ninkashi',
            'opendate',
            'ovationtix',
            'seatengine',
            'seatengine_v3',
            'shopify',
            'showpass',
            'showslinger',
            'simpletix',
            'squarespace',
            'squadup',
            'stagetime',
            'ticketleap',
            'ticketmaster',
            'ticketsource',
            'ticketweb',
            'tixr',
            'tockify',
            'tour_dates',
            'tribe_events',
            'vivenu',
            'wix_events'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS scraping_sources (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    platform "ScrapingPlatform" NOT NULL,
    scraper_key TEXT NOT NULL,
    external_id TEXT,
    source_url TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_club_platform_priority_key
    ON scraping_sources (club_id, platform, priority);

CREATE INDEX IF NOT EXISTS scraping_sources_club_enabled_priority_idx
    ON scraping_sources (club_id, enabled, priority);

CREATE INDEX IF NOT EXISTS scraping_sources_platform_enabled_idx
    ON scraping_sources (platform, enabled);

CREATE OR REPLACE FUNCTION set_scraping_sources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scraping_sources_set_updated_at ON scraping_sources;

CREATE TRIGGER scraping_sources_set_updated_at
BEFORE UPDATE ON scraping_sources
FOR EACH ROW
EXECUTE FUNCTION set_scraping_sources_updated_at();

WITH source_seed AS (
    SELECT
        c.id AS club_id,
        COALESCE(c.scraper, 'disabled') AS scraper_key,
        NULLIF(c.scraping_url, '') AS source_url,
        c.scraper IS NOT NULL AS enabled,
        CASE
            WHEN c.scraper = 'wix_events' THEN 'wix_events'::"ScrapingPlatform"
            WHEN c.scraper = 'ovationtix' THEN 'ovationtix'::"ScrapingPlatform"
            WHEN c.scraper = 'squadup' THEN 'squadup'::"ScrapingPlatform"
            WHEN c.scraper = 'eventbrite' THEN 'eventbrite'::"ScrapingPlatform"
            WHEN c.scraper IN ('live_nation', 'ticketmaster_national') THEN 'ticketmaster'::"ScrapingPlatform"
            WHEN c.scraper IN ('seatengine_v3', 'seatengine_v3_national') THEN 'seatengine_v3'::"ScrapingPlatform"
            WHEN c.scraper IN ('seatengine', 'seatengine_classic', 'seatengine_web', 'seatengine_national') THEN 'seatengine'::"ScrapingPlatform"
            WHEN c.scraper IN ('etix', 'dr_grins', 'zanies') THEN 'etix'::"ScrapingPlatform"
            WHEN c.scraper IN ('the_backline', 'philly_improv_theater', 'logan_square_improv', 'io_theater', 'rails_comedy') THEN 'crowdwork'::"ScrapingPlatform"
            WHEN c.scraper = 'the_rockwell' THEN 'tribe_events'::"ScrapingPlatform"
            WHEN c.scraper = 'show_slinger' THEN 'showslinger'::"ScrapingPlatform"
            WHEN c.scraper IN ('setup', 'comedy_corner_underground') THEN 'stagetime'::"ScrapingPlatform"
            WHEN c.scraper = 'ticketleap' THEN 'ticketleap'::"ScrapingPlatform"
            WHEN c.scraper = 'simpletix' THEN 'simpletix'::"ScrapingPlatform"
            WHEN c.scraper = 'shopify' THEN 'shopify'::"ScrapingPlatform"
            WHEN c.scraper = 'showpass' THEN 'showpass'::"ScrapingPlatform"
            WHEN c.scraper IN ('ticketweb', 'off_cabot') THEN 'ticketweb'::"ScrapingPlatform"
            WHEN c.scraper = 'tixr' THEN 'tixr'::"ScrapingPlatform"
            WHEN c.scraper = 'tockify' THEN 'tockify'::"ScrapingPlatform"
            WHEN c.scraper = 'tour_dates' THEN 'tour_dates'::"ScrapingPlatform"
            WHEN c.scraper = 'squarespace' THEN 'squarespace'::"ScrapingPlatform"
            WHEN c.scraper = 'ninkashi' THEN 'ninkashi'::"ScrapingPlatform"
            WHEN c.scraper = 'vivenu' THEN 'vivenu'::"ScrapingPlatform"
            WHEN c.scraper = 'jetbook' THEN 'jetbook'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND (c.wix_comp_id IS NOT NULL OR c.wix_category_id IS NOT NULL) THEN 'wix_events'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.ovationtix_client_id IS NOT NULL THEN 'ovationtix'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.squadup_user_id IS NOT NULL THEN 'squadup'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.eventbrite_id IS NOT NULL THEN 'eventbrite'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.ticketmaster_id IS NOT NULL THEN 'ticketmaster'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.seatengine_id IS NOT NULL AND c.seatengine_id ~ '^[0-9a-fA-F-]{36}$' THEN 'seatengine_v3'::"ScrapingPlatform"
            WHEN c.scraper IS NULL AND c.seatengine_id IS NOT NULL THEN 'seatengine'::"ScrapingPlatform"
            ELSE 'custom'::"ScrapingPlatform"
        END AS platform,
        jsonb_strip_nulls(
            jsonb_build_object(
                'category_id', c.wix_category_id
            )
        ) AS metadata,
        c.ticketmaster_id,
        c.seatengine_id,
        c.eventbrite_id,
        c.ovationtix_client_id,
        c.wix_comp_id,
        c.squadup_user_id
    FROM clubs c
    WHERE
        c.scraper IS NOT NULL
        OR c.scraping_url IS NOT NULL
        OR c.ticketmaster_id IS NOT NULL
        OR c.seatengine_id IS NOT NULL
        OR c.eventbrite_id IS NOT NULL
        OR c.ovationtix_client_id IS NOT NULL
        OR c.wix_comp_id IS NOT NULL
        OR c.wix_category_id IS NOT NULL
        OR c.squadup_user_id IS NOT NULL
)
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    external_id,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    s.club_id,
    s.platform,
    s.scraper_key,
    CASE
        WHEN s.platform = 'wix_events'::"ScrapingPlatform" THEN s.wix_comp_id
        WHEN s.platform = 'ovationtix'::"ScrapingPlatform" THEN s.ovationtix_client_id
        WHEN s.platform = 'squadup'::"ScrapingPlatform" THEN s.squadup_user_id
        WHEN s.platform = 'eventbrite'::"ScrapingPlatform" THEN s.eventbrite_id
        WHEN s.platform = 'ticketmaster'::"ScrapingPlatform" THEN s.ticketmaster_id
        WHEN s.platform IN ('seatengine'::"ScrapingPlatform", 'seatengine_v3'::"ScrapingPlatform") THEN s.seatengine_id
        ELSE NULL
    END AS external_id,
    s.source_url,
    0 AS priority,
    s.enabled,
    s.metadata
FROM source_seed s
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    external_id = EXCLUDED.external_id,
    source_url = EXCLUDED.source_url,
    enabled = EXCLUDED.enabled,
    metadata = EXCLUDED.metadata;
