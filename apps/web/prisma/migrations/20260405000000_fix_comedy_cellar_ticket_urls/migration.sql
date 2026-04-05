-- Fix Comedy Cellar ticket URLs: convert relative paths to absolute URLs
-- The scraper extracted href attributes from HTML as-is, which were relative
-- paths like /reservations-newyork/?showid=... instead of full URLs.

UPDATE tickets
SET purchase_url = 'https://www.comedycellar.com' || purchase_url
WHERE purchase_url LIKE '/reservations%'
  AND show_id IN (
    SELECT s.id FROM shows s
    JOIN clubs c ON s.club_id = c.id
    WHERE c.name LIKE 'Comedy Cellar%'
  );
