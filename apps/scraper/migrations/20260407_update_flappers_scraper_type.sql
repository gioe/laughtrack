-- Update Flappers Comedy Club to use dedicated PHP calendar scraper
-- instead of tour_dates. The tour_dates scraper will still pick up
-- shows independently via Bandsintown artist lookups.

UPDATE "clubs"
SET scraper = 'flappers',
    scraping_url = 'https://www.flapperscomedy.com/site/calendar_test_2025.php'
WHERE name = 'Flappers Comedy Club And Restaurant Burbank';
