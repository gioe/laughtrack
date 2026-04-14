-- Switch SuperNova Comedy (club 456) from generic "tixr" scraper to custom "supernova_comedy" scraper.
-- The custom scraper uses TixrClient._fetch_tixr_page() to bypass DataDome bot-detection.
UPDATE clubs SET scraper = 'supernova_comedy' WHERE id = 456;
