-- TASK-3375: Onboard One Night Stans Comedy Club (Waterford Township, MI) via
-- the net-new Standing Room Only (SRO) scraper.
--
-- One Night Stans is a 300-seat dedicated stand-up club. Its own site
-- (onenightstans.club) is a thin front-end over Standing Room Only Tickets
-- (standingroomonlytickets.com, "sromedia"), an ASP.NET box-office platform.
-- The venue's full live calendar is served by one Kendo-UI endpoint:
--
--     POST https://www.standingroomonlytickets.com/Event/ReadLiveEvents
--     (empty body) -> {"Data": [ {Id, EventTitle, Shows:[{Start, ...}]}, ... ]}
--
-- Each feed entry is a headliner residency carrying a Shows array (Thu/Fri/Sat
-- runs), so the scraper fans each event out to one Show per showtime. The whole
-- feed is comedy (stand-up headliners, roasts, comedy class showcases, season
-- pass) so no title filter is needed.
--
-- platform = 'custom' because Standing Room Only is not a ScrapingPlatform enum
-- value; scraper_key = 'standing_room_only' selects the new scraper. source_url
-- is the ReadLiveEvents endpoint; the scraper derives both the POST target and
-- each show's public page (WebOffice/EventList/{id}) from its host.
--
-- Idempotent (re-runs nightly via bin/migrate): INSERT ... WHERE NOT EXISTS +
-- guarded UPDATE, matched on google_place_id OR (lower(name)).

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    status,
    club_type,
    google_place_id
)
SELECT
    'One Night Stans Comedy Club',
    '4761 Highland Rd',
    'https://www.onenightstans.club/',
    '48328',
    'America/Detroit',
    TRUE,
    'Waterford Township',
    'MI',
    'active',
    'club',
    'ChIJ0fvSRuG9JIgRtBFo4npwVsU'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ0fvSRuG9JIgRtBFo4npwVsU'
        OR lower(name) = lower('One Night Stans Comedy Club')
);

UPDATE clubs
   SET address = '4761 Highland Rd',
       website = 'https://www.onenightstans.club/',
       zip_code = '48328',
       timezone = 'America/Detroit',
       visible = TRUE,
       city = 'Waterford Township',
       state = 'MI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJ0fvSRuG9JIgRtBFo4npwVsU')
 WHERE google_place_id = 'ChIJ0fvSRuG9JIgRtBFo4npwVsU'
    OR lower(name) = lower('One Night Stans Comedy Club');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'standing_room_only',
    'https://www.standingroomonlytickets.com/Event/ReadLiveEvents',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ0fvSRuG9JIgRtBFo4npwVsU'
        OR lower(c.name) = lower('One Night Stans Comedy Club'))
   AND NOT EXISTS (
       -- Guard on the real (club_id, platform, priority) unique constraint so a
       -- nightly re-run can't pass NOT EXISTS and then hit the constraint.
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'standing_room_only',
       source_url = 'https://www.standingroomonlytickets.com/Event/ReadLiveEvents',
       enabled = TRUE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJ0fvSRuG9JIgRtBFo4npwVsU'
        OR lower(c.name) = lower('One Night Stans Comedy Club'));
