-- Onboard 硅谷脱口秀 Silicomedy (San Jose, CA) via the existing eventbrite scraper - TASK-3196.
--
-- Silicomedy is a Mandarin-language stand-up comedy producer ("South Bay
-- Standup!"), ticketed through its own Eventbrite organizer (28300962631). It is a
-- ROVING producer: its shows run at varying rented venues (1054 S De Anza Blvd and
-- 1522 S Winchester Blvd in San Jose, Cubberley Theatre in Palo Alto, ...), so this
-- wires the producer to the generic `eventbrite` scraper in ORGANIZER mode. Organizer
-- mode groups the feed's events by Eventbrite venue and attaches each show to the
-- matching per-venue club, auto-creating a per-venue club where none exists.
--
-- Because the shows surface under the auto-created per-venue clubs (not under this
-- producer row), the producer is inserted as a HIDDEN synthetic proxy (visible=FALSE)
-- that only carries the organizer scraping_sources row. The discovered Google
-- comedy_club listing (place_id ChIJxS-PWA-1j4AR3TgnwfibhT0, 1522 S Winchester Blvd)
-- is recorded as the proxy's identity for dedupe/idempotency.
--
-- NOTE (verified 2026-06-23): the organizer feed scrapes cleanly — 1 upcoming show
-- ("FUN飞一夏 | 硅谷脱口秀夏季精品秀", 2026-07-18) routed to an auto-created visible
-- per-venue club "Cubberley Theatre" (Palo Alto). N>0; verification green.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    '硅谷脱口秀 Silicomedy', '1522 S Winchester Blvd, San Jose, CA 95128, USA',
    'https://silicomedy.com/',
    'San Jose', 'CA', '95128', 'America/Los_Angeles', 'US', 'club',
    'ChIJxS-PWA-1j4AR3TgnwfibhT0', FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJxS-PWA-1j4AR3TgnwfibhT0'
       OR name = '硅谷脱口秀 Silicomedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/silicomedy-28300962631',
    '28300962631',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJxS-PWA-1j4AR3TgnwfibhT0' OR c.name = '硅谷脱口秀 Silicomedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
