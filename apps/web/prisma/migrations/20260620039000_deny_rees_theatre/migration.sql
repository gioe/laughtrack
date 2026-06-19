-- Deny-list The REES Theatre (Plymouth, IN) -- TASK-3004.
--
-- Discovered via discover-comedy-venues near 60601 with an Eventbrite hint.
-- Verification on 2026-06-19 found the venue is a mixed performing-arts
-- theater, not a recurring stand-up/improv comedy venue:
--   - reestheatre.org links tickets to its Eventbrite organizer:
--     https://www.eventbrite.com/o/rees-theatre-47108969493
--   - The live Eventbrite organizer feed returned 16 events: youth theater,
--     film series, music/blues/country/reggae/80s tribute shows, and chamber
--     ensemble programming.
--   - No live organizer event was stand-up or improv comedy, and Eventbrite
--     organizer mode would ingest the full mixed calendar with no comedy filter.
--
-- So we record the club identity (visible=false, no scraping_sources row -> not
-- scraped) AND add a venue_deny_list entry. The club row makes the discovered
-- Google place_id known; the deny-list row prevents future discover-nearby runs
-- from re-filing the same non-comedy venue.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (
    name,
    address,
    website,
    city,
    state,
    zip_code,
    timezone,
    country,
    club_type,
    google_place_id,
    visible,
    status
)
SELECT
    'The REES Theatre',
    '100 N Michigan St, Plymouth, IN 46563',
    'https://reestheatre.org/',
    'Plymouth',
    'IN',
    '46563',
    'America/Indiana/Indianapolis',
    'US',
    'club',
    'ChIJHVT19ZhTEYgRLFpsdB84qRQ',
    FALSE,
    'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE google_place_id = 'ChIJHVT19ZhTEYgRLFpsdB84qRQ'
       OR name = 'The REES Theatre'
);

INSERT INTO venue_deny_list (google_place_id, name, reason, added_by, denied_at)
SELECT
    'ChIJHVT19ZhTEYgRLFpsdB84qRQ',
    'The REES Theatre',
    'Mixed performing-arts theater, not a recurring stand-up/improv venue. Live Eventbrite organizer 47108969493 returned 16 mixed events (youth theater, film series, music, chamber ensemble) and zero stand-up/improv comedy; organizer mode would ingest the full non-comedy calendar. TASK-3004.',
    'discovery_triage',
    now()
WHERE NOT EXISTS (
    SELECT 1
    FROM venue_deny_list
    WHERE google_place_id = 'ChIJHVT19ZhTEYgRLFpsdB84qRQ'
);
