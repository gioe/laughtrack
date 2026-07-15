-- Preserve stale-show reconciliation when PIT's scraper key changes. Without
-- adopting the old attribution, JSON-LD rows that overlap PatronTicket by a
-- timezone-shifted timestamp remain indefinitely under the retired key.
UPDATE shows AS show
SET last_scraped_by = 'the_pit'
FROM clubs AS club
WHERE show.club_id = club.id
  AND show.last_scraped_by = 'json_ld'
  AND (
      club.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
      OR (club.name = 'The PIT' AND club.city = 'New York' AND club.state = 'NY')
  );
