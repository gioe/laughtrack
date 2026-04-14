-- Backfill missing metadata across Helium locations
-- Adds city, state, country where missing; updates http:// website URLs to https://

-- Helium Comedy Club - Atlanta (club 134) — city/state from address
UPDATE "clubs"
SET city = 'Alpharetta', state = 'GA', country = 'US'
WHERE id = 134;

-- Helium Comedy Club - Portland (club 133) — city/state, website http→https
UPDATE "clubs"
SET city = 'Portland', state = 'OR', country = 'US',
    website = 'https://portland.heliumcomedy.com'
WHERE id = 133;

-- Helium Comedy Club Philadelphia (club 110) — city/state, website http→https
UPDATE "clubs"
SET city = 'Philadelphia', state = 'PA', country = 'US',
    website = 'https://philadelphia.heliumcomedy.com'
WHERE id = 110;

-- Helium & Elements Restaurant - Buffalo (club 132) — city/state, website http→https
UPDATE "clubs"
SET city = 'Buffalo', state = 'NY', country = 'US',
    website = 'https://buffalo.heliumcomedy.com'
WHERE id = 132;

-- Helium & Elements Restaurant - St. Louis (club 108) — city/state only (website already https)
UPDATE "clubs"
SET city = 'St Louis', state = 'MO', country = 'US'
WHERE id = 108;
