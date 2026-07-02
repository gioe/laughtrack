-- Correct Hennepin Arts taxonomy.
--
-- Hennepin Arts is a mixed-purpose performing arts operator/venue presenter,
-- not a comedy-first club. The scraper still stores individual theatres in
-- Show.room.

UPDATE clubs
SET club_type = 'venue'
WHERE name = 'Hennepin Arts'
  AND website = 'https://hennepinarts.org'
  AND club_type = 'club';
