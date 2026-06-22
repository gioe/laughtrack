-- Onboard four more Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (sixth batch).
--
-- 14. McCues Comedy Club (580 Portsmouth Traffic Cir, Portsmouth, NH 03801) —
--     weekly stand-up at the Roundabout Diner (founder Jim McCue). Eventbrite
--     organizer 33618422103, single-venue all-comedy. Wired but 0 upcoming at
--     onboard time (last show was 2026-06-20; organizer posts dates in batches) —
--     correct id, will populate on the nightly.
--
-- 15. Blend Comedy (82 Fleet St / BLEND.603 gallery, Portsmouth, NH 03801) —
--     weekly stand-up in the BLEND.603 art gallery. Eventbrite organizer
--     61076996003, single-venue all-comedy. Wired but 0 upcoming at onboard time
--     (organizer feed currently empty between batches).
--
-- 16. The Music Hall Lounge (131 Congress St, Portsmouth, NH 03801) — nonprofit
--     arts venue running "Comedy in the Lounge" / "Comedy in the Historic Theater".
--     PatronManager (Salesforce-sites) host themusichall.my.salesforce-sites.com,
--     two comedy-bearing venue ids (Lounge a0T1P00000OjhxiUAB + Historic Theater
--     a0T1a000000wDPcEAM). The patron_ticket scraper's default Comedy category
--     filter isolates comedy from the mixed music/film/literary calendar. Verified
--     2026-06-22: 16 comedy shows for club 10961.
--
-- 17. The Leavitt Theatre (259 Main St, Ogunquit, ME 03907) — historic mixed-use
--     theater (films/music/drag/trivia + a recurring "Thursday Night Stand-Up").
--     Wix Events widget comp-mngrhtd93 with comedy_filter ON (essential — the
--     calendar is mostly non-comedy). Verified 2026-06-22: 19 comedy shows for
--     club 10962 (all stand-up; trivia/bingo/films correctly excluded).

-- ---- McCues Comedy Club (Eventbrite) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'McCues Comedy Club', '580 Portsmouth Traffic Cir', 'https://www.mccuescomedyclub.com/', 'Portsmouth', 'NH', '03801', 'America/New_York', 'US', 'club', 'ChIJtYpveEu_4okRnyGeqKAtwb4', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJtYpveEu_4okRnyGeqKAtwb4' OR name = 'McCues Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/33618422103', '33618422103', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJtYpveEu_4okRnyGeqKAtwb4' OR c.name = 'McCues Comedy Club')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

-- ---- Blend Comedy (Eventbrite) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Blend Comedy', '82 Fleet St', 'https://www.blend603.com/', 'Portsmouth', 'NH', '03801', 'America/New_York', 'US', 'club', 'ChIJFafGuOC_4okReb7zCjDowjo', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJFafGuOC_4okReb7zCjDowjo' OR name = 'Blend Comedy');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/61076996003', '61076996003', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJFafGuOC_4okReb7zCjDowjo' OR c.name = 'Blend Comedy')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

-- ---- The Music Hall Lounge (PatronManager / patron_ticket) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Music Hall Lounge', '131 Congress St', 'http://www.themusichall.org/', 'Portsmouth', 'NH', '03801', 'America/New_York', 'US', 'club', 'ChIJLWKZEgu_4okRoaNjqVstZ5Q', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJLWKZEgu_4okRoaNjqVstZ5Q' OR name = 'The Music Hall Lounge');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'patron_ticket'::"ScrapingPlatform", 'patron_ticket', 'https://themusichall.my.salesforce-sites.com/ticket', TRUE, 0,
    '{"patronticket_host":"themusichall.my.salesforce-sites.com","patronticket_venue_id":["a0T1P00000OjhxiUAB","a0T1a000000wDPcEAM"]}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJLWKZEgu_4okRoaNjqVstZ5Q' OR c.name = 'The Music Hall Lounge')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'patron_ticket');

-- ---- The Leavitt Theatre (Wix Events + comedy_filter) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Leavitt Theatre', '259 Main St', 'https://www.leavittheatre.com/', 'Ogunquit', 'ME', '03907', 'America/New_York', 'US', 'club', 'ChIJczXx40qv4okR40z3IDdoTmY', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJczXx40qv4okR40z3IDdoTmY' OR name = 'The Leavitt Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, wix_event_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'wix_events'::"ScrapingPlatform", 'wix_events', 'https://www.leavittheatre.com', 'comp-mngrhtd93', TRUE, 0, '{"comedy_filter":true}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJczXx40qv4okR40z3IDdoTmY' OR c.name = 'The Leavitt Theatre')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'wix_events');
