-- Onboard Union Colony Civic Center (Greeley, CO) via the generic showare scraper - TASK-3427.
--
-- The Union Colony Civic Center is a City-of-Greeley municipal performing-arts
-- venue (Monfort Concert Hall + Hensel Phelps Theatre). Its season is mostly
-- concerts, touring Broadway (The Book of Mormon, Waitress), ballet, and family
-- shows, but it also hosts touring stand-up comedy (e.g. "JOHN CRIST LIVE!",
-- Oct 10 2026 — described on the venue's own listing as "tactfully-unhinged
-- stand-up", a Pollstar Top-10 Global Touring Comedian).
--
-- It tickets through accesso ShoWare at ucstars.showare.com (its own box office;
-- NOT Ticketmaster, so ticketmaster_national does not cover it), so this wires to
-- the generic `showare` scraper (source_url = the ShoWare default.asp). The
-- scraper derives the JSON performance-list endpoint
-- (/include/widgets/events/performancelist.asp?action=perf...) from the host —
-- verified live to return the John Crist comedy performance with date, price
-- ($37.75-$157.75), and ShoWare ticket URL.
--
-- Because the host is multi-purpose, metadata.include_title_patterns scopes the
-- feed to comedy so the concert/Broadway/ballet season does not surface. The
-- ShoWare performance-list `Event` field (which the scraper filters on) carries
-- the act name, not always the word "comedy" (touring comics are titled by
-- performer, e.g. "JOHN CRIST LIVE!"), so the include set combines generic comedy
-- keywords with the known touring comedian's name. As future comedy acts are
-- listed they can be added to the pattern set (Fox Theatre RWC / Clayton Club
-- precedent, TASK-3220 / TASK-3192). A 0-show scrape when no comedy is currently
-- on the calendar is expected, not a failure, for a comedy-filtered mixed-use source.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Union Colony Civic Center', '701 10th Ave, Greeley, CO 80631, USA',
    'https://greeleyco.gov/ucstars/',
    'Greeley', 'CO', '80631', 'America/Denver', 'US', 'club',
    'ChIJBdiRvS-ibocR0cHe_x77BaE', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJBdiRvS-ibocR0cHe_x77BaE'
       OR name = 'Union Colony Civic Center'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'showare',
    'https://ucstars.showare.com/default.asp',
    TRUE,
    0,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array(
            'comedy', 'comedian', 'stand.?up', 'improv', 'sketch',
            'open mic', 'roast', 'john crist'
        )
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJBdiRvS-ibocR0cHe_x77BaE' OR c.name = 'Union Colony Civic Center')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'showare'
  );
