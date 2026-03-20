-- TASK-494: Discover comedy venues supported by Ticketmaster API
-- Queried Ticketmaster Discovery API venues endpoint for known comedy clubs.
-- Cross-referenced with existing clubs in DB, added ticketmaster_id for 36 clubs
-- that have a Ticketmaster presence, and inserted 1 net-new venue (Carolines on Broadway).
--
-- API query examples used:
--   GET /discovery/v2/venues.json?keyword=<venue_name>&countryCode=US
--   GET /discovery/v2/venues.json?classificationName=comedy&stateCode=NY&countryCode=US
--
-- Venues NOT found on Ticketmaster (no match returned):
--   Stand-Up NY (id=25), Comedy Village (id=14), Helium Comedy Club - Atlanta (id=134)

-- ─── Update ticketmaster_id for existing clubs ──────────────────────────────

UPDATE clubs SET ticketmaster_id = 'Z7r9jZaA05'   WHERE id = 1;    -- Comedy Cellar New York
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7tk'   WHERE id = 5;    -- The Stand
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7pv'   WHERE id = 13;   -- Eastville Comedy Club Brooklyn
UPDATE clubs SET ticketmaster_id = 'ZFr9jZ6Fk7'   WHERE id = 18;   -- Gotham Comedy Club
UPDATE clubs SET ticketmaster_id = 'KovZpZAFntEA' WHERE id = 20;   -- The Broadway Comedy Club
UPDATE clubs SET ticketmaster_id = 'KovZpZAknElA' WHERE id = 26;   -- West Nyack Levity Live
UPDATE clubs SET ticketmaster_id = 'KovZpZAknAaA' WHERE id = 27;   -- Oxnard Levity Live
UPDATE clubs SET ticketmaster_id = 'KovZ917ARMI'  WHERE id = 28;   -- Huntsville Levity Live
UPDATE clubs SET ticketmaster_id = 'KovZpZAdFvIA' WHERE id = 29;   -- Addison Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZAknAkA' WHERE id = 30;   -- Brea Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZAknIvA' WHERE id = 31;   -- Chicago Improv (Schaumburg, IL)
UPDATE clubs SET ticketmaster_id = 'KovZ917ANvF'  WHERE id = 32;   -- Hollywood Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZAknEtA' WHERE id = 33;   -- Irvine Improv
UPDATE clubs SET ticketmaster_id = 'KovZ917AJ4Z'  WHERE id = 34;   -- Milwaukee Improv (Brookfield, WI)
UPDATE clubs SET ticketmaster_id = 'KovZpZAknA1A' WHERE id = 35;   -- Ontario Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZA1nEEA' WHERE id = 36;   -- Pittsburgh Improv (Homestead, PA)
UPDATE clubs SET ticketmaster_id = 'KovZpZA67IAA' WHERE id = 37;   -- Raleigh Improv (Cary, NC)
UPDATE clubs SET ticketmaster_id = 'KovZpZAknA6A' WHERE id = 38;   -- San Jose Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZA67EnA' WHERE id = 39;   -- Arlington Improv
UPDATE clubs SET ticketmaster_id = 'KovZpZA67IeA' WHERE id = 40;   -- Houston Improv
UPDATE clubs SET ticketmaster_id = 'Z7r9jZaenD'   WHERE id = 45;   -- Stress Factory (New Brunswick, NJ)
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7Fj'   WHERE id = 46;   -- Stress Factory Bridgeport
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7R1'   WHERE id = 53;   -- Dania Improv Comedy Theatre
UPDATE clubs SET ticketmaster_id = 'KovZpZAknEJA' WHERE id = 54;   -- Tempe Improv
UPDATE clubs SET ticketmaster_id = 'Z7r9jZadzs'   WHERE id = 55;   -- Miami Improv (Doral, FL)
UPDATE clubs SET ticketmaster_id = 'KovZpZAknAFA' WHERE id = 56;   -- Denver Improv
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa74I'   WHERE id = 57;   -- Comedy Zone Greensboro
UPDATE clubs SET ticketmaster_id = 'ZFr9jZaFe6'   WHERE id = 58;   -- The Comedy Zone - Charlotte
UPDATE clubs SET ticketmaster_id = 'Z7r9jZaA1e'   WHERE id = 61;   -- Goodnights Comedy Club
UPDATE clubs SET ticketmaster_id = 'ZFr9jZFak6'   WHERE id = 102;  -- DC Improv
UPDATE clubs SET ticketmaster_id = 'Z7r9jZaAfs'   WHERE id = 104;  -- Desert Ridge Improv (Phoenix, AZ)
UPDATE clubs SET ticketmaster_id = 'Z7r9jZaA6w'   WHERE id = 108;  -- Helium & Elements Restaurant - St. Louis
UPDATE clubs SET ticketmaster_id = 'Z7r9jZaeS-'   WHERE id = 110;  -- Helium Comedy Club (Philadelphia)
UPDATE clubs SET ticketmaster_id = 'KovZpZAknAdA' WHERE id = 129;  -- StandUpLive Phoenix
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7tA'   WHERE id = 132;  -- Helium & Elements Restaurant - Buffalo
UPDATE clubs SET ticketmaster_id = 'Z7r9jZa7Kh'   WHERE id = 133;  -- Helium Comedy Club - Portland

-- ─── Net-new venues (scraper=live_nation) ───────────────────────────────────

-- Carolines on Broadway: major NYC comedy club not previously in DB
INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Carolines on Broadway',
    '1626 Broadway',
    'New York',
    'NY',
    '10036',
    'America/New_York',
    'KovZpZAdI77A',
    'live_nation',
    TRUE,
    'https://www.carolines.com',
    'ticketmaster/KovZpZAdI77A'
);
