-- Backfill missing metadata for Desert Ridge Improv (club 104)
-- Address: 21001 N. Tatum Blvd, Phoenix, AZ 85050

UPDATE "clubs"
SET city = 'Phoenix', state = 'AZ', country = 'US'
WHERE id = 104;
