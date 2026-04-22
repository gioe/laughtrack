-- Switch Improv Asylum (club 141) from the specialized improv_asylum scraper
-- to the shared tixr scraper.
--
-- Keep the Tixr group page as scraping_url because the current site links users
-- to that group page, and a future DataDome fix in the generic scraper should
-- let this club benefit without needing venue-specific code.
UPDATE clubs
SET scraper = 'tixr'
WHERE id = 141
  AND name = 'Improv Asylum'
  AND scraper = 'improv_asylum';
