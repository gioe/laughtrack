-- Switch Laugh Patriot Place from dr_grins scraper to etix
-- The venue sells tickets through Etix directly; dr_grins only worked
-- because DrGrinsScraper inherits from EtixScraper.
UPDATE clubs SET scraper = 'etix' WHERE id = 332;
