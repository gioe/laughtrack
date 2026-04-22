-- Switch The Stand (club 5) from the specialized the_stand_nyc scraper to the
-- shared tixr scraper. Keep the existing venue page as scraping_url so the
-- generic Tixr scraper can paginate The Stand's owned calendar pages before
-- resolving Tixr event links.
UPDATE clubs
SET scraper = 'tixr'
WHERE id = 5
  AND name = 'The Stand'
  AND scraper = 'the_stand_nyc';
