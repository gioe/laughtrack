-- Onboard Color Club (Chicago, IL) to the generic DICE scraper.
--
-- colorclub.events is a Squarespace site that embeds the public DICE event-list
-- widget. A browser network capture of /comedy found the widget config:
--   partnerId = d285d692
--   apiKey    = tquIxOdW272IdLJ3Ycry9Sa6g3KmwsNGg5BSDXFA1vxpDLOb
--   venues    = ["Color Club"]
--   tags      = ["type:comedy"]
-- A direct DICE partner API response on 2026-06-19 returned venue id 14681 and
-- promoter id 14931 with upcoming events.

INSERT INTO clubs (
    name,
    address,
    website,
    city,
    state,
    zip_code,
    country,
    timezone,
    club_type,
    google_place_id,
    visible,
    status
)
SELECT
    'Color Club',
    '4146 N Elston Ave, Chicago, IL 60618, USA',
    'https://www.colorclub.events',
    'Chicago',
    'IL',
    '60618',
    'US',
    'America/Chicago',
    'club',
    'ChIJAYFuSgbND4gRvZdEssM2FF4',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE name = 'Color Club'
       OR google_place_id = 'ChIJAYFuSgbND4gRvZdEssM2FF4'
);

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
SELECT
    c.id,
    'dice'::"ScrapingPlatform",
    'dice',
    'https://www.colorclub.events/comedy',
    0,
    TRUE,
    jsonb_build_object(
        'dice_api_key', 'tquIxOdW272IdLJ3Ycry9Sa6g3KmwsNGg5BSDXFA1vxpDLOb',
        'dice_partner_id', 'd285d692',
        'dice_venue_id', '14681',
        'dice_venue_name', 'Color Club',
        'dice_promoter_id', '14931',
        'dice_promoter_name', 'Color Club LLC dba Color Club',
        'dice_tags', 'type:comedy',
        'onboarded_via', 'TASK-3013 browser capture of https://www.colorclub.events/comedy DICE widget; direct DICE API verified >0 upcoming comedy events on 2026-06-19'
    ),
    now(),
    now()
FROM clubs c
WHERE (c.name = 'Color Club' OR c.google_place_id = 'ChIJAYFuSgbND4gRvZdEssM2FF4')
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.scraper_key = 'dice'
  );
