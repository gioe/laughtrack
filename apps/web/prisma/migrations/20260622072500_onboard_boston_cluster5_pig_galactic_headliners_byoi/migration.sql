-- Onboard four more Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (fifth batch).
--
-- 10. Providence Improv Guild (95 Empire St, Providence, RI 02903) — improv
--     theater on Shopify; the schedule collection's products ARE the shows. Wired
--     via the shopify scraper (collection /collections/schedule). Verified
--     2026-06-22: 3 shows for club 10955.
--
-- 11. Galactic Theatre (440 Main St, Warren, RI 02885) — mixed-use music/comedy
--     venue. Its own Bandzoogle site has no structured feed and we have no
--     Bandsintown scraper, but the recurring "Comedy Night at The Galactic Theatre
--     presents:" series is published on the Eventbrite organizer "Aaron Leidecker"
--     (id 117097094791), which naturally isolates the comedy nights. Verified
--     2026-06-22: 1 comedy show for club 10956.
--
-- 12. Headliners Comedy Club (700 Elm St, Manchester, NH 03103) — long-running
--     weekly stand-up club. headlinerscomedyclub.com 301-redirects to
--     headlinersnh.com; both resolve to OvationTix client 35936 (ONE operation).
--     Wired via the ovationtix scraper. NOTE: client 35936 is the Headliners brand
--     calendar and also lists the brand's other NH locations (Old Orchard Beach,
--     Lobster in the Rough), so shows from sibling locations attach to this club
--     until a venue filter is added. Verified 2026-06-22: 12 shows for club 10957.
--
-- 13. Bring Your Own Improv (3259 Post Rd / Warwick Center for the Arts, Warwick,
--     RI 02886) — improv troupe at a single host venue. Tickets via SimpleTix; the
--     two weekly series are each a single season-long SimpleTix event that the
--     scraper expands into dated occurrences, so TWO simpletix sources are wired
--     (priority 0 = Family Friendly 253398, priority 1 = Caffeinated Insomniacs
--     253400). Verified 2026-06-22: 22 shows for club 10958.

-- ---- Providence Improv Guild (Shopify) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Providence Improv Guild', '95 Empire St', 'https://www.improvpig.com/', 'Providence', 'RI', '02903', 'America/New_York', 'US', 'club', 'ChIJ_-4t63BF5IkR9PTMFNHvHAU', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJ_-4t63BF5IkR9PTMFNHvHAU' OR name = 'Providence Improv Guild');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'shopify'::"ScrapingPlatform", 'shopify', 'https://improvpig.com/collections/schedule', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ_-4t63BF5IkR9PTMFNHvHAU' OR c.name = 'Providence Improv Guild')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'shopify');

-- ---- Galactic Theatre (Eventbrite organizer) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Galactic Theatre', '440 Main St', 'http://galactictheatre.com/', 'Warren', 'RI', '02885', 'America/New_York', 'US', 'club', 'ChIJ-ywc3c1W5IkR_d1tHlm5hrk', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJ-ywc3c1W5IkR_d1tHlm5hrk' OR name = 'Galactic Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/117097094791', '117097094791', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ-ywc3c1W5IkR_d1tHlm5hrk' OR c.name = 'Galactic Theatre')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

-- ---- Headliners Comedy Club (OvationTix) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Headliners Comedy Club', '700 Elm St', 'https://www.headlinersnh.com/', 'Manchester', 'NH', '03103', 'America/New_York', 'US', 'club', 'ChIJc5g_dTRP4okRnFdXb_kBGF0', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJc5g_dTRP4okRnFdXb_kBGF0' OR name = 'Headliners Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'ovationtix'::"ScrapingPlatform", 'ovationtix', 'https://web.ovationtix.com/trs/cal/35936', '35936', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJc5g_dTRP4okRnFdXb_kBGF0' OR c.name = 'Headliners Comedy Club')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix');

-- ---- Bring Your Own Improv (SimpleTix, two season-long series) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Bring Your Own Improv', '3259 Post Rd', 'http://www.bringyourownimprov.com/', 'Warwick', 'RI', '02886', 'America/New_York', 'US', 'club', 'ChIJ07d98mZM5IkRi_2XsbqPczo', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJ07d98mZM5IkRi_2XsbqPczo' OR name = 'Bring Your Own Improv');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'simpletix'::"ScrapingPlatform", 'simpletix', 'https://www.simpletix.com/e/bring-your-own-improv-s-family-friendly-co-tickets-253398', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ07d98mZM5IkRi_2XsbqPczo' OR c.name = 'Bring Your Own Improv')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'simpletix' AND s.source_url LIKE '%253398%');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'simpletix'::"ScrapingPlatform", 'simpletix', 'https://www.simpletix.com/e/bring-your-own-improv-s-caffeinated-insomn-tickets-253400', TRUE, 1, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ07d98mZM5IkRi_2XsbqPczo' OR c.name = 'Bring Your Own Improv')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'simpletix' AND s.source_url LIKE '%253400%');
