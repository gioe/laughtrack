-- TASK-787: Switch Cheaper Than Therapy to the Ninkashi scraper
-- CTT's primary ticketing is Ninkashi (tickets.cttcomedy.com).
-- Ninkashi now has its own scraper (key='ninkashi'), so scraping_url stores
-- the url_site value used by the Ninkashi public API.
-- Eventbrite remains as a fallback (eventbrite_id preserved).

UPDATE clubs
SET
    scraper     = 'ninkashi',
    scraping_url = 'tickets.cttcomedy.com'
WHERE name = 'Cheaper Than Therapy';
