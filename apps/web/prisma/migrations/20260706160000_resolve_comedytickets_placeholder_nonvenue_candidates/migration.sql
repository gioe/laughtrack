-- TASK-3591: Resolve ComedyTickets placeholder and non-venue candidates.
--
-- ComedyTickets is only a discovery signal. The rows below either become hidden
-- non-routeable shells with disabled "none" sources, aliases to existing
-- canonical clubs, or documented no-op physical-address merges.

WITH hidden_candidates (
    name,
    address,
    website,
    timezone,
    city,
    state,
    country,
    club_type,
    comedytickets_id,
    comedytickets_url,
    event_count,
    disposition,
    reason
) AS (
    VALUES
        (
            'Bert Kreischer''s Fully Loaded at Sea 2026',
            'Miami, FL',
            '',
            'America/New_York',
            'Miami',
            'FL',
            'US',
            'festival',
            8304,
            'https://www.comedytickets.com/events/bert-kreischers-fully-loaded-at-sea-2026',
            5,
            'hidden_event_specific_cruise',
            'Cruise/festival package, not a standing comedy venue.'
        ),
        (
            'Chattanooga, TN',
            'Chattanooga, TN',
            '',
            'America/New_York',
            'Chattanooga',
            'TN',
            'US',
            'non_comedy',
            2264,
            'https://www.comedytickets.com/events/chattanooga-tn',
            6,
            'hidden_city_placeholder',
            'City-only placeholder; no canonical venue can be inferred safely.'
        ),
        (
            'FUNY Stand Up Classes',
            'New York, NY',
            '',
            'America/New_York',
            'New York',
            'NY',
            'US',
            'non_comedy',
            4156,
            'https://www.comedytickets.com/events/funy-stand-up-classes',
            6,
            'hidden_class_listing',
            'Class product, not a public venue calendar.'
        ),
        (
            'L.A. Comedy Club''s Dragon Room',
            'Las Vegas, NV',
            '',
            'America/Los_Angeles',
            'Las Vegas',
            'NV',
            'US',
            'non_comedy',
            1126,
            'https://www.comedytickets.com/events/la-comedy-clubs-dragon-room',
            7,
            'hidden_room_without_verified_parent',
            'Room-level listing with no verified canonical LaughTrack parent in the audit.'
        ),
        (
            'Martha Vineyard Comedy Fest - Week 2',
            'Oak Bluffs, MA',
            '',
            'America/New_York',
            'Oak Bluffs',
            'MA',
            'US',
            'festival',
            1458,
            'https://www.comedytickets.com/events/martha-vineyard-comedy-fest-week-2',
            5,
            'hidden_festival_listing',
            'Festival/week listing, not a standing venue.'
        ),
        (
            'Open Mic at FUNY Stand Up Classes',
            'New York, NY',
            '',
            'America/New_York',
            'New York',
            'NY',
            'US',
            'non_comedy',
            731,
            'https://www.comedytickets.com/events/open-mic-at-funy-stand-up-classes',
            14,
            'hidden_open_mic_class_listing',
            'Open-mic/class listing, not a venue calendar.'
        ),
        (
            'Room 52',
            'New York, NY',
            '',
            'America/New_York',
            'New York',
            'NY',
            'US',
            'non_comedy',
            4155,
            'https://www.comedytickets.com/events/room-52',
            26,
            'hidden_room_without_verified_parent',
            'Room/stage-level listing with no verified canonical LaughTrack parent in the audit.'
        ),
        (
            'Seattle',
            'Seattle, WA',
            '',
            'America/Los_Angeles',
            'Seattle',
            'WA',
            'US',
            'non_comedy',
            14202,
            'https://www.comedytickets.com/events/seattle',
            6,
            'hidden_city_placeholder',
            'City-only placeholder; no canonical venue can be inferred safely.'
        ),
        (
            'Skankfest New Orleans',
            'New Orleans, LA',
            '',
            'America/Chicago',
            'New Orleans',
            'LA',
            'US',
            'festival',
            8193,
            'https://www.comedytickets.com/events/skankfest-new-orleans',
            7,
            'hidden_festival_listing',
            'Festival listing, not a standing venue.'
        ),
        (
            'St. Louis',
            'St. Louis, MO',
            '',
            'America/Chicago',
            'St. Louis',
            'MO',
            'US',
            'non_comedy',
            1091,
            'https://www.comedytickets.com/events/st-louis',
            5,
            'hidden_city_placeholder',
            'City-only placeholder; multiple St. Louis venues exist, so no safe canonical merge.'
        ),
        (
            'Tampa, FL',
            'Tampa, FL',
            '',
            'America/New_York',
            'Tampa',
            'FL',
            'US',
            'non_comedy',
            1141,
            'https://www.comedytickets.com/events/tampa-fl',
            7,
            'hidden_city_placeholder',
            'City-only placeholder; no canonical venue can be inferred safely.'
        )
)
INSERT INTO clubs (
    name,
    address,
    website,
    phone_number,
    timezone,
    visible,
    city,
    state,
    country,
    status,
    club_type
)
SELECT
    hc.name,
    hc.address,
    hc.website,
    '',
    hc.timezone,
    FALSE,
    hc.city,
    hc.state,
    hc.country,
    'active',
    hc.club_type
FROM hidden_candidates hc
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs c
     WHERE lower(c.name) = lower(hc.name)
);

WITH hidden_candidates (
    name,
    comedytickets_id,
    comedytickets_url,
    event_count,
    disposition,
    reason
) AS (
    VALUES
        ('Bert Kreischer''s Fully Loaded at Sea 2026', 8304, 'https://www.comedytickets.com/events/bert-kreischers-fully-loaded-at-sea-2026', 5, 'hidden_event_specific_cruise', 'Cruise/festival package, not a standing comedy venue.'),
        ('Chattanooga, TN', 2264, 'https://www.comedytickets.com/events/chattanooga-tn', 6, 'hidden_city_placeholder', 'City-only placeholder; no canonical venue can be inferred safely.'),
        ('FUNY Stand Up Classes', 4156, 'https://www.comedytickets.com/events/funy-stand-up-classes', 6, 'hidden_class_listing', 'Class product, not a public venue calendar.'),
        ('L.A. Comedy Club''s Dragon Room', 1126, 'https://www.comedytickets.com/events/la-comedy-clubs-dragon-room', 7, 'hidden_room_without_verified_parent', 'Room-level listing with no verified canonical LaughTrack parent in the audit.'),
        ('Martha Vineyard Comedy Fest - Week 2', 1458, 'https://www.comedytickets.com/events/martha-vineyard-comedy-fest-week-2', 5, 'hidden_festival_listing', 'Festival/week listing, not a standing venue.'),
        ('Open Mic at FUNY Stand Up Classes', 731, 'https://www.comedytickets.com/events/open-mic-at-funy-stand-up-classes', 14, 'hidden_open_mic_class_listing', 'Open-mic/class listing, not a venue calendar.'),
        ('Room 52', 4155, 'https://www.comedytickets.com/events/room-52', 26, 'hidden_room_without_verified_parent', 'Room/stage-level listing with no verified canonical LaughTrack parent in the audit.'),
        ('Seattle', 14202, 'https://www.comedytickets.com/events/seattle', 6, 'hidden_city_placeholder', 'City-only placeholder; no canonical venue can be inferred safely.'),
        ('Skankfest New Orleans', 8193, 'https://www.comedytickets.com/events/skankfest-new-orleans', 7, 'hidden_festival_listing', 'Festival listing, not a standing venue.'),
        ('St. Louis', 1091, 'https://www.comedytickets.com/events/st-louis', 5, 'hidden_city_placeholder', 'City-only placeholder; multiple St. Louis venues exist, so no safe canonical merge.'),
        ('Tampa, FL', 1141, 'https://www.comedytickets.com/events/tampa-fl', 7, 'hidden_city_placeholder', 'City-only placeholder; no canonical venue can be inferred safely.')
)
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
    'none',
    NULL,
    0,
    FALSE,
    jsonb_build_object(
        'task', 'TASK-3591',
        'source', 'comedytickets_audit',
        'comedytickets_id', hc.comedytickets_id,
        'comedytickets_url', hc.comedytickets_url,
        'comedytickets_event_count', hc.event_count,
        'disposition', hc.disposition,
        'reason', hc.reason
    )
FROM hidden_candidates hc
JOIN clubs c
  ON lower(c.name) = lower(hc.name)
WHERE c.visible = FALSE
  AND NOT EXISTS (
      SELECT 1
        FROM scraping_sources s
       WHERE s.club_id = c.id
         AND s.scraper_key = 'none'
  )
ON CONFLICT (club_id, platform, priority) DO NOTHING;

WITH alias_candidates (
    alias_name,
    city,
    state,
    canonical_club_id,
    canonical_name,
    comedytickets_id,
    event_count,
    reason
) AS (
    VALUES
        (
            'Comedy Store - Los Angeles (Belly Room)',
            'West Hollywood',
            'CA',
            158,
            'The Comedy Store',
            3338,
            5,
            'ComedyTickets room-level listing for The Comedy Store Belly Room.'
        ),
        (
            'Neon Room at Helium Comedy Club',
            'Portland',
            'OR',
            133,
            'Helium Comedy Club - Portland',
            639,
            5,
            'ComedyTickets room-level listing for Helium Comedy Club Portland.'
        ),
        (
            'Skyline Comedy Club - 7PM',
            'Appleton',
            'WI',
            1057,
            'Skyline Comedy Club',
            2359,
            21,
            'ComedyTickets time-slot split for Skyline Comedy Club.'
        )
)
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
    c.id,
    ac.alias_name,
    lower(ac.alias_name),
    ac.city,
    ac.state,
    lower(ac.city),
    lower(ac.state),
    'TASK-3591 ComedyTickets id=' || ac.comedytickets_id || ': ' || ac.reason,
    TRUE
FROM alias_candidates ac
JOIN clubs c
  ON c.id = ac.canonical_club_id
 AND c.name = ac.canonical_name
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();

-- "Lexington, KY" (ComedyTickets id 9660) resolves by physical address:
-- 161 Lexington Green Cir # C4 is already Comedy Off Broadway (club 100).
-- Do not add a city-name alias; it would be too broad for duplicate matching.

-- Remove the one enabled route/source URL containing "letscomedytickets". The
-- SeatEngine venue id remains the scraper target; public routing should use the
-- first-party venue events page.
UPDATE scraping_sources s
   SET source_url = 'https://www.letscomedyftw.com/events',
       metadata = COALESCE(s.metadata, '{}'::jsonb)
           || jsonb_build_object(
               'public_show_base_url', 'https://www.letscomedyftw.com/events',
               'source_url_replaced_by_task', 'TASK-3591',
               'source_url_replaced_reason', 'replace_ticketing_host_with_first_party_events_url'
           ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 469
   AND c.name = 'Let''s Comedy'
   AND s.enabled = TRUE
   AND lower(COALESCE(s.source_url, '')) = 'http://letscomedytickets.seatengine.com';
