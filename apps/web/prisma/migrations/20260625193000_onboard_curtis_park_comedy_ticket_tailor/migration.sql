-- Onboard Curtis Park Comedy (Denver, CO) via the existing ticket_tailor scraper - TASK-3393.
--
-- Curtis Park Comedy is a weekly Sunday-night stand-up series hosted at The Savoy
-- (a multi-use social hall at 2700 Arapahoe St, Denver CO 80205). Its own GoDaddy
-- site (curtisparkcomedy.com) is a "Launching Soon" placeholder with no calendar,
-- so it is not the datasource. The series' OWN ticketing now runs on Ticket Tailor:
-- box office https://www.tickettailor.com/events/thesavoy/ (account slug `thesavoy`),
-- whose page title is literally "Buy tickets – Curtis Park Comedy" and whose entire
-- description is the Curtis Park Comedy stand-up series. The series previously sold
-- via TicketsCandy (organizer ticketscandy.com/ec/bar-savoy-54, "Bar Savoy") and
-- Eventbrite, but both are RETIRED — the TicketsCandy organizer page now states
-- "We have changed our ticketing platform. Please purchase tickets at:
-- https://www.tickettailor.com/events/thesavoy".
--
-- DEDICATED box office (NOT mixed-use): this Ticket Tailor account carries ONLY
-- Curtis Park Comedy stand-up shows. The Savoy's other programming (burlesque/drag,
-- children's theatre, plays, jazz bands) is sold separately on savoydenver.com
-- (Squarespace) + Eventbrite, NOT on this box office. So single_venue mode attaches
-- every listing event to this club and NO include_title_patterns filter is needed.
--
-- 0-show-today is EXPECTED, not a failure: the box office currently shows "No events
-- currently listed" — the weekly series is between bookings ("Check back soon for
-- upcoming events!"). This club's comedy shows auto-populate when the next Sunday
-- show is listed (Continental Club / Clayton Club precedent, TASK-3216 / TASK-3192).
-- The Ticket Tailor listing sits behind Cloudflare and clears via the ticket_tailor
-- scraper's curl_cffi chrome impersonation + venue-website Referer.
--
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Curtis Park Comedy', '2700 Arapahoe St, Denver, CO 80205, USA',
    'https://curtisparkcomedy.com/',
    'Denver', 'CO', '80205', 'America/Denver', 'US', 'club',
    'ChIJQ0JOTEx5bIcR03IXgEPuQGU', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJQ0JOTEx5bIcR03IXgEPuQGU'
       OR name = 'Curtis Park Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticket_tailor',
    'https://www.tickettailor.com/events/thesavoy/',
    TRUE,
    0,
    '{
        "account_slug": "thesavoy",
        "single_venue": true,
        "cloudflare_bypass": {
            "strategy": "ticket_tailor_curl_cffi_referer",
            "referer": "https://curtisparkcomedy.com/",
            "reason": "Ticket Tailor listing HTML clears Cloudflare via curl_cffi chrome impersonation plus the venue website Referer."
        },
        "onboarded_via": "TASK-3393: Curtis Park Comedy weekly Sunday stand-up at The Savoy; own ticketing is the dedicated Ticket Tailor box office (account thesavoy, title \"Buy tickets – Curtis Park Comedy\"). TicketsCandy + Eventbrite retired (organizer page redirects to Ticket Tailor). Box office currently lists 0 upcoming (between bookings); single_venue mode, no title filter needed (box office is comedy-only). Auto-populates when next Sunday show lists."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJQ0JOTEx5bIcR03IXgEPuQGU' OR c.name = 'Curtis Park Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ticket_tailor'
  );
