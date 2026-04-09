-- Fix Helium Comedy Club scraping URLs after site migration from
-- path-based (heliumcomedy.com/<city>/events) to subdomain
-- (<city>.heliumcomedy.com/events) URLs. Also switch scraper type
-- from seatengine/live_nation to seatengine_classic to match
-- the working St. Louis (#108) and Atlanta (#134) clubs.

-- Philadelphia #110
UPDATE "clubs"
SET "scraping_url" = 'https://philadelphia.heliumcomedy.com/events',
    "scraper" = 'seatengine_classic'
WHERE "id" = 110;

-- Buffalo #132
UPDATE "clubs"
SET "scraping_url" = 'https://buffalo.heliumcomedy.com/events',
    "scraper" = 'seatengine_classic'
WHERE "id" = 132;

-- Portland #133
UPDATE "clubs"
SET "scraping_url" = 'https://portland.heliumcomedy.com/events',
    "scraper" = 'seatengine_classic'
WHERE "id" = 133;

-- Indianapolis #139 (was on Ticketmaster, now uses Helium subdomain)
UPDATE "clubs"
SET "scraping_url" = 'https://indianapolis.heliumcomedy.com/events',
    "scraper" = 'seatengine_classic'
WHERE "id" = 139;
