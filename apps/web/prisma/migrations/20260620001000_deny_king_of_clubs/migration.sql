-- Deny-list The KING of CLUBS (Columbus, OH) — TASK-2895.
--
-- Discovered via discover-comedy-venues near 44622 with a "comedy" hint, but
-- verification against the venue's OWN calendar disproved it: tkoc.live self-
-- describes as a "Live Music Venue" / "all inclusive concert venue that hosts
-- artists of every genre and style", Google primary_type=live_music_venue, and
-- its live Wix Events API returned 34 upcoming events that are 100% music
-- (rock/metal/tribute bands, rappers) with zero stand-up comedy. Aggregator
-- pages (comedy.tickets etc.) list it speculatively, but the club's own site is
-- authoritative and shows no comedy.
--
-- So we record the club (visible=false, no scraping_sources row → never
-- scraped) AND add a venue_deny_list entry. The club row makes discover-nearby
-- treat the place_id as known; the deny-list entry makes the exclusion explicit
-- so a future zero-show triage / adopt-scraper pass does not re-investigate it.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The KING of CLUBS', '6252 Busch Blvd, Columbus, OH 43229, USA', 'https://www.tkoc.live/', 'Columbus', 'OH', '43229', 'America/New_York', 'US', 'club', 'ChIJyQ32QGWLOIgRssW0o6eTGc0', FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE name = 'The KING of CLUBS' OR google_place_id = 'ChIJyQ32QGWLOIgRssW0o6eTGc0'
);

INSERT INTO venue_deny_list (google_place_id, name, reason, added_by, denied_at)
SELECT 'ChIJyQ32QGWLOIgRssW0o6eTGc0', 'The KING of CLUBS',
       'Live music venue (self-described "all inclusive concert venue"); Google primary_type=live_music_venue. Own Wix Events calendar = 100% music (rock/metal/tribute/rap), zero stand-up comedy. Not a comedy venue — excluded from scraper onboarding. TASK-2895.',
       'discovery_triage', now()
WHERE NOT EXISTS (
    SELECT 1 FROM venue_deny_list WHERE google_place_id = 'ChIJyQ32QGWLOIgRssW0o6eTGc0'
);
