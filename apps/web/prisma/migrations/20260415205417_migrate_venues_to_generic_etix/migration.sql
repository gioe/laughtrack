-- [TASK-1454] Migrate venue-specific scrapers to generic etix scraper
-- Switches venues that have working Etix venue pages from their custom
-- scraper implementations (the_moon, zanies, funny_bone) to the generic
-- 'etix' scraper with the Etix venue URL as scraping_url.
--
-- NOT migrated (Etix venue page returns 0 events despite active shows):
--   - Revolution Hall (id=1045) — 33 Etix ticket links on site, 0 on venue page
--   - Zanies Chicago (id=179) — 47 Etix ticket links on site, 0 on venue page
--   - Comedy & Magic Club (id=161) — 38 Etix ticket links on site, 0 on venue page
--   - McCurdy's (id=1025) — uses ColdFusion ticketing, not direct Etix

-- The Moon (Tallahassee, FL)
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/14500/the-moon'
WHERE id = 1048;

-- Zanies Nashville
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/21745/zanies-comedy-club'
WHERE id = 1029;

-- Des Moines Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/28453/funny-bone-comedy-club-des-moines'
WHERE id = 1030;

-- Dayton Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31595/funny-bone-comedy-club-dayton'
WHERE id = 317;

-- Omaha Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31598/funny-bone-comedy-club-omaha'
WHERE id = 1026;

-- Orlando Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31599/funny-bone-comedy-club-orlando'
WHERE id = 1027;

-- Funny Bone Columbus
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31594/funny-bone-comedy-club-columbus'
WHERE id = 308;

-- Virginia Beach Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31602/funny-bone-comedy-club-virginia-beach'
WHERE id = 1033;

-- Cleveland Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31603/funny-bone-comedy-club-cleveland'
WHERE id = 1050;

-- Tampa Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31600/funny-bone-comedy-club-tampa'
WHERE id = 1053;

-- Syracuse Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31436/funny-bone-comedy-club-syracuse'
WHERE id = 1028;

-- Richmond Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31601/funny-bone-comedy-club-richmond'
WHERE id = 1034;

-- Albany Funny Bone
UPDATE clubs
SET scraper = 'etix',
    scraping_url = 'https://www.etix.com/ticket/v/31591/funny-bone-comedy-club-albany'
WHERE id = 323;
