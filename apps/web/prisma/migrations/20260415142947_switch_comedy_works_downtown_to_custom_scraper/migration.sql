-- Switch Comedy Works Downtown (id=1036) from tour_dates to custom comedy_works_downtown scraper
UPDATE clubs
SET scraper = 'comedy_works_downtown'
WHERE id = 1036;
