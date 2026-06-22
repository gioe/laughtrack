-- Onboard the final Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (seventh/final batch).
--
-- 18. Happier Valley Comedy (1 Mill Valley Rd Ste b, Hadley, MA 01035) — dedicated
--     comedy org on Crowdwork (slug happiervalleycomedy, theatre id 550). Verified
--     2026-06-22: 10 shows for club 10963.
--
-- 19. Sea Tea Comedy Theater (15 Asylum St, Hartford, CT 06103) — dedicated comedy
--     theater, single-venue all-comedy on Eventbrite organizer 10965010523.
--     Verified 2026-06-22: 15 shows for club 10964.
--
-- 20. Loft Comedy Club (99 Springfield Rd, Westfield, MA 01085) — SeatEngine venue
--     312 (confirmed via the authenticated SeatEngine API, NOT the asset-path id 297
--     which belongs to Bananas Comedy Club NJ). Wired but 0 shows at onboard time
--     (venue provisioned, no published calendar yet) — correct id, will populate on
--     the nightly once they post shows. Live page: events.loftcomedyclub.com.
--
-- Also: backfill google_place_id on the pre-existing Great Cedar Showroom club
-- (already onboarded via ticketmaster_comedy KovZpZAEkFlA) so future
-- discover-nearby runs dedupe it instead of re-proposing it as new.

-- ---- Backfill Great Cedar Showroom place_id (idempotent) ----
UPDATE clubs
SET google_place_id = 'ChIJ-f_fVoR15okRztNTqLNmGks'
WHERE name = 'Great Cedar Showroom at Foxwoods Resort Casino'
  AND google_place_id IS NULL;

-- ---- Happier Valley Comedy (Crowdwork) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Happier Valley Comedy', '1 Mill Valley Rd Ste b', 'http://www.happiervalley.com/', 'Hadley', 'MA', '01035', 'America/New_York', 'US', 'club', 'ChIJresGmCnR5okRc7zAUxrR57c', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJresGmCnR5okRc7zAUxrR57c' OR name = 'Happier Valley Comedy');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'crowdwork'::"ScrapingPlatform", 'crowdwork', 'https://crowdwork.com/api/v2/happiervalleycomedy/shows', TRUE, 0,
    '{"rails_to_iana":true,"default_timezone":"America/New_York"}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJresGmCnR5okRc7zAUxrR57c' OR c.name = 'Happier Valley Comedy')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork');

-- ---- Sea Tea Comedy Theater (Eventbrite) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Sea Tea Comedy Theater', '15 Asylum St', 'https://seateaimprov.com/theater/', 'Hartford', 'CT', '06103', 'America/New_York', 'US', 'club', 'ChIJxwwiT3tT5okR2zCe1XjXP1g', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJxwwiT3tT5okR2zCe1XjXP1g' OR name = 'Sea Tea Comedy Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/10965010523', '10965010523', TRUE, 0, '{}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJxwwiT3tT5okR2zCe1XjXP1g' OR c.name = 'Sea Tea Comedy Theater')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

-- ---- Loft Comedy Club (SeatEngine venue 312) ----
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Loft Comedy Club', '99 Springfield Rd', 'https://events.loftcomedyclub.com', 'Westfield', 'MA', '01085', 'America/New_York', 'US', 'club', 'ChIJU-OVAVbn5okRb4GQk7K1NMI', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE google_place_id = 'ChIJU-OVAVbn5okRb4GQk7K1NMI' OR name = 'Loft Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, seatengine_id, enabled, priority, metadata, created_at, updated_at)
SELECT c.id, 'seatengine'::"ScrapingPlatform", 'seatengine', 'https://events.loftcomedyclub.com', 312, TRUE, 0,
    '{"public_show_base_url":"https://events.loftcomedyclub.com"}'::jsonb, NOW(), NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJU-OVAVbn5okRb4GQk7K1NMI' OR c.name = 'Loft Comedy Club')
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'seatengine');
