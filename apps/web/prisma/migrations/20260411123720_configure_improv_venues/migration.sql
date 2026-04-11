-- Configure null-scraper Improv venues to use improv scraper
-- All use improv.com or improvtx.com platform (proven by Arlington Improv in TASK-1116)

-- Hollywood Improv (club 32) — Hollywood, CA
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improv.com/hollywood/',
    address = '8162 Melrose Avenue',
    city = 'Hollywood',
    state = 'CA',
    website = 'https://improv.com/hollywood/'
WHERE id = 32;

-- Milwaukee Improv (club 34) — Brookfield, WI
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improv.com/milwaukee/',
    address = '20110 Lower Union Street',
    city = 'Brookfield',
    state = 'WI',
    website = 'https://improv.com/milwaukee/'
WHERE id = 34;

-- Ontario Improv (club 35) — Ontario, CA
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improv.com/ontario/',
    address = '4555 Mills Circle',
    city = 'Ontario',
    state = 'CA',
    website = 'https://improv.com/ontario/'
WHERE id = 35;

-- San Jose Improv (club 38) — San Jose, CA
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improv.com/sanjose/',
    address = '62 South 2nd Street',
    city = 'San Jose',
    state = 'CA',
    website = 'https://improv.com/sanjose/'
WHERE id = 38;

-- Houston Improv (club 40) — Houston, TX
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improvtx.com/houston/calendar/',
    address = '7620 Katy Freeway Space 455',
    city = 'Houston',
    state = 'TX',
    website = 'https://improvtx.com/houston/'
WHERE id = 40;

-- LOL San Antonio (club 41) — San Antonio, TX
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improvtx.com/sanantonio/calendar/',
    address = '618 NW Loop 410',
    city = 'San Antonio',
    state = 'TX',
    website = 'https://improvtx.com/sanantonio/'
WHERE id = 41;

-- Denver Improv (club 56) — already has location from TASK-1180, switch to improv scraper for consistency
UPDATE "clubs"
SET scraper = 'improv',
    scraping_url = 'improv.com/denver/'
WHERE id = 56;
