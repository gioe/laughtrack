-- TASK-4148: publish only after native ingestion has persisted future tickets.
UPDATE clubs c SET visible = TRUE
WHERE c.id = 17393
  AND EXISTS (SELECT 1 FROM scraping_sources ss
              WHERE ss.club_id = c.id AND ss.scraper_key = 'stir_crazy' AND ss.enabled)
  AND EXISTS (SELECT 1 FROM shows s JOIN tickets t ON t.show_id = s.id
              WHERE s.club_id = c.id AND s.date > NOW()
                AND s.last_scraped_by = 'stir_crazy'
                AND t.purchase_url LIKE 'https://stircrazycomedyclub.com/%');
