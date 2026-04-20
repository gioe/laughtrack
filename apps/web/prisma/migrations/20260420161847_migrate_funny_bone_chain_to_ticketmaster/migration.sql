-- Migrate the remaining 10 Funny Bone chain venues (chain_id=3) off the
-- DataDome-blocked Etix scraper to Ticketmaster (live_nation). Follow-up to
-- TASK-1661, which migrated Funny Bone Columbus (id 308) on the same pattern.
--
-- Etix blanket-blocks the scraper behind a DataDome visible CAPTCHA
-- (TASK-1647 audit — apps/scraper/docs/audits/task-1647-etix-datadome-block.md);
-- every funnybone.com city subdomain inherits the same block. Each venue was
-- located on the Ticketmaster Discovery API by keyword+state lookup and
-- confirmed by address/zip match against the chain's published locations.
--
-- Per-venue TM venueId lookups (verified via app.ticketmaster.com/discovery/v2):
--   317  Dayton           → Z7r9jZa7KA  (7 upcoming)
--   323  Albany           → Z7r9jZa7eK  (10 upcoming)
--   1026 Omaha            → Z7r9jZaelh  (35 upcoming)
--   1027 Orlando          → ZFr9jZaA61  (16 upcoming)
--   1028 Syracuse         → Z7r9jZa7e4  (15 upcoming)
--   1030 Des Moines       → Z7r9jZa7pC  (5 upcoming)
--   1033 Virginia Beach   → Z7r9jZadLz  (0 upcoming — listed, none scheduled)
--   1034 Richmond         → Z7r9jZadVa  (88 upcoming)
--   1050 Cleveland        → Z7r9jZaAhN  (31 upcoming)
--   1053 Tampa            → Z7r9jZa7pj  (0 upcoming — listed, none scheduled)
--
-- Also enriches previously-missing address/zip/country fields from the TM
-- venue metadata. Existing non-empty values are left untouched.

-- 317 Dayton Funny Bone — backfill country
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZa7KA',
    country = 'US'
WHERE id = 317;

-- 323 Albany Funny Bone — backfill empty address + country
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZa7eK',
    address = '1 Crossgate Mall Rd',
    country = 'US'
WHERE id = 323;

-- 1026 Omaha Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZaelh'
WHERE id = 1026;

-- 1027 Orlando Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'ZFr9jZaA61'
WHERE id = 1027;

-- 1028 Syracuse Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZa7e4'
WHERE id = 1028;

-- 1030 Des Moines Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZa7pC'
WHERE id = 1030;

-- 1033 Virginia Beach Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZadLz'
WHERE id = 1033;

-- 1034 Richmond Funny Bone — backfill sparse address + empty zip
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZadVa',
    address = '11800 W Broad St, #1090',
    zip_code = '23233'
WHERE id = 1034;

-- 1050 Cleveland Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZaAhN'
WHERE id = 1050;

-- 1053 Tampa Funny Bone
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZa7pj'
WHERE id = 1053;
