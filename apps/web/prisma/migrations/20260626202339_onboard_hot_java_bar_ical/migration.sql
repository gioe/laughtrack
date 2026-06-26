-- Onboard JAVA / Hot Java Bar (St. Louis, MO) — TASK-3310,
-- objective #7 discover-comedy-venues near St. Louis 63101.
--
-- Hot Java Bar (hotjava.bar) is a bar that hosts a weekly WordUp! comedy +
-- spoken-word open mic plus recurring stand-up nights (e.g. "Morgan Casey
-- presents Dark Comedy", "Dark Ass Humor Comedy Show"). A prior session flagged
-- its posh.vip (Posh Kickback) ticketing as an unscrapable SPA, but the venue's
-- own /events page embeds a PUBLIC GOOGLE CALENDAR whose ICS feed is the clean,
-- no-auth datasource:
--   https://calendar.google.com/calendar/ical/hotjavaevents%40gmail.com/public/basic.ics
--
-- Onboards on the net-new generic `ical` scraper (scraper_key = 'ical'), which
-- parses the ICS VEVENTs. Because the calendar is mixed-use (R&B, club nights,
-- private Calendly meetings + comedy), comedy is isolated via the shared
-- title-pattern metadata (include_title_patterns). Past events are dropped by
-- default; event_page_url sets the per-show fallback link to the venue page.
--
-- The venue-identity club (11259) already exists from the objective-7 batch but
-- was hidden (visible=false); flip it visible now that it has a working source.
--
-- Verification: the `ical` scraper was validated end-to-end against the LIVE
-- feed (comedy filter kept the upcoming "Morgan Casey presents Dark Comedy";
-- a junk messages:// event URL was correctly rejected to the venue page) plus a
-- recorded-fixture unit suite. Upcoming comedy count fluctuates with the feed
-- window (WordUp instances roll off as they pass), so a low count is expected.
--
-- Idempotent: guarded with NOT EXISTS / keyed UPDATE so it no-ops where rows
-- already exist and reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (create on a fresh DB; no-op where it already exists).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Hot Java Bar',
       '4193 Manchester Ave',
       'https://hotjava.bar/',
       'St. Louis', 'MO', '63110',
       'America/Chicago', 'US', 'club',
       'ChIJhT_Nq9612IcRwgwqWUHIWW4',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Hot Java Bar'
     OR google_place_id = 'ChIJhT_Nq9612IcRwgwqWUHIWW4'
);

-- 2. Ensure the (possibly pre-existing, hidden) venue club is visible.
UPDATE clubs SET visible = true
WHERE google_place_id = 'ChIJhT_Nq9612IcRwgwqWUHIWW4'
  AND visible = false;

-- 3. The ical scraping source (Google Calendar ICS feed for this venue) with a
--    comedy title filter and a venue-page fallback link.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'ical',
       'https://calendar.google.com/calendar/ical/hotjavaevents%40gmail.com/public/basic.ics',
       0, true,
       '{"include_title_patterns": ["comedy", "open mic", "stand-?up", "word ?up"], "event_page_url": "https://hotjava.bar/events/"}'::jsonb
FROM clubs c
WHERE c.google_place_id = 'ChIJhT_Nq9612IcRwgwqWUHIWW4'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'ical'
  );
