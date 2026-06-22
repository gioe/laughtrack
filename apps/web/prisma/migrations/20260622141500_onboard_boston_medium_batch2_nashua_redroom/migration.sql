-- Onboard medium-likelihood Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3152 (batch 2 of 45, venues 11-20).
--
-- Of venues 11-20, 2 qualify; 8 dropped (see task notes):
--   - The Cut (Gloucester): ShoWare, but only 1 annual comedy special, no series.
--   - Off The Rails (Worcester): TicketWeb, 0 comedy on calendar (music/BBQ).
--   - Center City Underground (Worcester): phantom/mistagged — no such venue.
--   - The Jake Speakeasy (Providence): private-rental lounge, FB-only, 1 past show.
--   - Kilburn Comedy Cove (New Bedford): no public structured calendar.
--   - Narrows Center (Fall River): ShoWare, 0 upcoming comedy (music-only).
--   - The Palace Theatre / Rex (Manchester): 0 populated upcoming comedy +
--     unsupported Salesforce-Sites ticketing backend.
--   - The Greenwich Odeum (East Greenwich): OvationTix, only 1-2 occasional comedy
--     dates among ~23 music/theater events; no dedicated comedy calendar and the
--     ovationtix scraper has no comedy isolation — "occasional comedy" DROP.
--
-- 11. Nashua Center for the Arts (201 Main Street, Nashua, NH 03060) — mixed-use
--     performing-arts theater on Etix (venue 17050). Books recurring touring
--     stand-up (Lucas Zelnick, Natalie Cuomo, Nurse Blake) among mostly music, so
--     the source opts into comedy isolation via metadata.comedy_filter. Wired to the
--     existing etix scraper. NOTE: etix is DataDome-blocked from non-residential IPs
--     (capsolver cannot solve etix's interstitial), so a local scrape returns 0; the
--     venue id + comedy presence were confirmed on the live Etix venue page and the
--     row scrapes on the residential-proxy nightly GHA run.
--
-- 12. Red Room (Provincetown) (258 Commercial Street, Provincetown, MA 02657) —
--     P-town cabaret/drag/comedy room on SeatEngine (venue 436). It was ALREADY
--     being scraped, but under a club row mislabeled "Red Room / New York, NY"
--     (wrong city/state/place_id) with NO comedy isolation, so its drag/disco/
--     cabaret events leaked in as comedy. This migration (a) corrects that club's
--     geographic identity to Provincetown, and (b) enables metadata.comedy_filter on
--     its SeatEngine source. Comedy isolation for the seatengine scraper is added in
--     the same task's scraper commit. Verified 2026-06-22: a real scrape with the
--     filter kept 131/185 events (dropped 54 non-comedy) for the venue.

-- ---- Nashua Center for the Arts (Etix, comedy_filter) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Nashua Center for the Arts', '201 Main Street', 'http://nashuacenterforthearts.com/',
    'Nashua', 'NH', '03060', 'America/New_York', 'US', 'club',
    'ChIJsdEvSyKx44kRVrWQoeiWpuc', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJsdEvSyKx44kRVrWQoeiWpuc'
       OR name = 'Nashua Center for the Arts'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://www.etix.com/ticket/v/17050/nashua-center-for-the-arts',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJsdEvSyKx44kRVrWQoeiWpuc' OR c.name = 'Nashua Center for the Arts')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'etix'
  );

-- ---- Red Room (Provincetown) (SeatEngine venue 436, comedy_filter) ----
-- (a) Correct the existing mislabeled "Red Room / New York, NY" club that already
--     carries the Provincetown SeatEngine source (seatengine_id 436). Guarded by the
--     stale NYC place_id so it no-ops once corrected / on fresh DBs.
UPDATE clubs
SET name = 'Red Room (Provincetown)',
    address = '258 Commercial Street',
    website = 'https://redroom.club/',
    city = 'Provincetown',
    state = 'MA',
    zip_code = '02657',
    google_place_id = 'ChIJqbgqyVOn_IkRIAI-jRz2eak'
WHERE google_place_id = 'ChIJLwbjozJbwokRdOy-qZTr8-k'
  AND id IN (SELECT club_id FROM scraping_sources WHERE seatengine_id = 436);

-- (b) On a fresh DB (no auto-discovered SeatEngine-436 club), insert it so the
--     venue is reproducible. No-ops on prod where the corrected club already exists.
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Red Room (Provincetown)', '258 Commercial Street', 'https://redroom.club/',
    'Provincetown', 'MA', '02657', 'America/New_York', 'US', 'club',
    'ChIJqbgqyVOn_IkRIAI-jRz2eak', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJqbgqyVOn_IkRIAI-jRz2eak'
       OR name = 'Red Room (Provincetown)'
)
AND NOT EXISTS (
    SELECT 1 FROM scraping_sources WHERE seatengine_id = 436
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, seatengine_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'seatengine'::"ScrapingPlatform",
    'seatengine',
    'https://redroomatvelvet.seatengine.com',
    436,
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE c.google_place_id = 'ChIJqbgqyVOn_IkRIAI-jRz2eak'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources WHERE seatengine_id = 436);

-- (c) Ensure comedy isolation is enabled on the existing SeatEngine-436 source
--     (the prod row pre-dates this migration with metadata '{}').
UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('comedy_filter', true)
WHERE seatengine_id = 436;
