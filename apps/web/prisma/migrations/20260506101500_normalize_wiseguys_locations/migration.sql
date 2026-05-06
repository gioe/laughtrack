-- Normalize Wiseguys chain membership to the six locations listed on
-- https://www.wiseguyscomedy.com/locations:
-- Jordan Landing, The Showroom, The Cabaret, Historic Ogden, The Rickles Room,
-- and Town Square.

UPDATE clubs
SET
    name = 'Wiseguys - Jordan Landing',
    address = '3763 West Center Park Dr',
    city = 'West Jordan',
    state = 'UT',
    zip_code = '84084',
    website = 'https://www.wiseguyscomedy.com/utah/west-jordan',
    timezone = 'America/Denver',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 389;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/utah/west-jordan',
    enabled = true
WHERE club_id = 389
  AND platform = 'seatengine'
  AND priority = 0;

UPDATE clubs
SET
    name = 'Wiseguys - The Showroom',
    address = '190 South 400 West',
    city = 'Salt Lake City',
    state = 'UT',
    zip_code = '84101',
    website = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom',
    timezone = 'America/Denver',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 390;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom',
    enabled = true
WHERE club_id = 390
  AND platform = 'seatengine'
  AND priority = 0;

UPDATE clubs
SET
    name = 'Wiseguys - Historic Ogden',
    address = '269 Historic 25th St',
    city = 'Ogden',
    state = 'UT',
    zip_code = '84401',
    website = 'https://www.wiseguyscomedy.com/utah/ogden',
    timezone = 'America/Denver',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 391;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/utah/ogden',
    enabled = true
WHERE club_id = 391
  AND platform = 'seatengine'
  AND priority = 0;

UPDATE clubs
SET
    name = 'Wiseguys - The Rickles Room',
    address = '190 South 400 West',
    city = 'Salt Lake City',
    state = 'UT',
    zip_code = '84101',
    website = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-rickles-room',
    timezone = 'America/Denver',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 404;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-rickles-room',
    enabled = true
WHERE club_id = 404
  AND platform = 'seatengine'
  AND priority = 0;

UPDATE clubs
SET
    name = 'Wiseguys - Town Square',
    address = '6593 S. Las Vegas Blvd Suite B-222',
    city = 'Las Vegas',
    state = 'NV',
    zip_code = '89119',
    website = 'https://www.wiseguyscomedy.com/nevada/las-vegas/town-square',
    timezone = 'America/Los_Angeles',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 546;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/nevada/las-vegas/town-square',
    enabled = true
WHERE club_id = 546
  AND platform = 'seatengine'
  AND priority = 0;

UPDATE clubs
SET
    name = 'Wiseguys - The Cabaret',
    address = '190 South 400 West',
    city = 'Salt Lake City',
    state = 'UT',
    zip_code = '84101',
    website = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-cabaret',
    timezone = 'America/Denver',
    status = 'active',
    visible = true,
    closed_at = NULL
WHERE id = 605;

UPDATE scraping_sources
SET
    source_url = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-cabaret',
    enabled = true
WHERE club_id = 605
  AND platform = 'seatengine'
  AND priority = 0;

-- These are historical/dormant SeatEngine stubs that are not present on the
-- current Wiseguys locations page and have no dependent shows or user data.
DELETE FROM clubs
WHERE id IN (448, 586)
  AND name IN ('Wiseguys Las Vegas', 'Wiseguys - Westgate')
  AND NOT EXISTS (SELECT 1 FROM shows WHERE shows.club_id = clubs.id)
  AND NOT EXISTS (SELECT 1 FROM tagged_clubs WHERE tagged_clubs.club_id = clubs.id)
  AND NOT EXISTS (SELECT 1 FROM email_subscriptions WHERE email_subscriptions.club_id = clubs.id)
  AND NOT EXISTS (SELECT 1 FROM processed_emails WHERE processed_emails.club_id = clubs.id)
  AND NOT EXISTS (
      SELECT 1
      FROM production_company_venues
      WHERE production_company_venues.club_id = clubs.id
  );
