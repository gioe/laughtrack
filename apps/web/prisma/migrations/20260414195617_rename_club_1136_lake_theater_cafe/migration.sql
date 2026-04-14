-- Rename club 1136 from 'Helium' to 'Lake Theater & Cafe'
-- This is an independent cinema/comedy venue in Lake Oswego, OR — not part of the Helium chain.
-- Populate address, city, state, zip, timezone, and country.

UPDATE "clubs"
SET name = 'Lake Theater & Cafe',
    address = '106 N State St',
    city = 'Lake Oswego',
    state = 'OR',
    zip_code = '97034',
    timezone = 'America/Los_Angeles',
    country = 'US'
WHERE id = 1136;
