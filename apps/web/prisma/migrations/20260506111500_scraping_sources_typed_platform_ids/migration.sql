-- TASK-1958: replace polymorphic scraping_sources.external_id with
-- per-platform typed identifier columns.

ALTER TABLE scraping_sources
    ADD COLUMN seatengine_id integer,
    ADD COLUMN eventbrite_id text,
    ADD COLUMN ticketmaster_id text,
    ADD COLUMN wix_event_id text,
    ADD COLUMN ovationtix_id text,
    ADD COLUMN squadup_id text,
    ADD COLUMN seatengine_v3_id text;

UPDATE scraping_sources
SET seatengine_id = external_id::integer
WHERE platform = 'seatengine'::"ScrapingPlatform"
  AND external_id ~ '^[0-9]+$';

UPDATE scraping_sources
SET eventbrite_id = external_id
WHERE platform = 'eventbrite'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

UPDATE scraping_sources
SET ticketmaster_id = external_id
WHERE platform = 'ticketmaster'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

UPDATE scraping_sources
SET wix_event_id = external_id
WHERE platform = 'wix_events'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

UPDATE scraping_sources
SET ovationtix_id = external_id
WHERE platform = 'ovationtix'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

UPDATE scraping_sources
SET squadup_id = external_id
WHERE platform = 'squadup'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

UPDATE scraping_sources
SET seatengine_v3_id = external_id
WHERE platform = 'seatengine_v3'::"ScrapingPlatform"
  AND external_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_seatengine_id_unique
    ON scraping_sources (seatengine_id)
    WHERE platform = 'seatengine'::"ScrapingPlatform"
      AND enabled = true
      AND seatengine_id IS NOT NULL
      -- TASK-1956 left these as documented same-venue duplicate-club follow-ups.
      AND seatengine_id NOT IN (21, 424, 428, 464, 493, 508, 556);

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_eventbrite_id_unique
    ON scraping_sources (eventbrite_id)
    WHERE platform = 'eventbrite'::"ScrapingPlatform"
      AND enabled = true
      AND eventbrite_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_ticketmaster_id_unique
    ON scraping_sources (ticketmaster_id)
    WHERE platform = 'ticketmaster'::"ScrapingPlatform"
      AND enabled = true
      AND ticketmaster_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_wix_event_id_unique
    ON scraping_sources (wix_event_id)
    WHERE platform = 'wix_events'::"ScrapingPlatform"
      AND enabled = true
      AND wix_event_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_ovationtix_id_unique
    ON scraping_sources (ovationtix_id)
    WHERE platform = 'ovationtix'::"ScrapingPlatform"
      AND enabled = true
      AND ovationtix_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_squadup_id_unique
    ON scraping_sources (squadup_id)
    WHERE platform = 'squadup'::"ScrapingPlatform"
      AND enabled = true
      AND squadup_id IS NOT NULL
      -- TASK-1956 Pattern SQ: same-venue duplicate-club follow-up.
      AND squadup_id <> '9086799';

CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_seatengine_v3_id_unique
    ON scraping_sources (seatengine_v3_id)
    WHERE platform = 'seatengine_v3'::"ScrapingPlatform"
      AND enabled = true
      AND seatengine_v3_id IS NOT NULL;

ALTER TABLE scraping_sources
    DROP COLUMN external_id;
