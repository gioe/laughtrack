-- TASK-848: Fix CSz Philadelphia scraper — VBO Tickets returning HTTP 401
-- Root cause: VBO Tickets rotated the session key (s= parameter).
-- Old key: 4610c334-6cb9-4033-b991-1c1a89918a19 (returns 401)
-- New key: c75a73ef-782c-44de-a954-6777056f4b03 (confirmed 200, 19 shows scraped)
-- New key discovered via Playwright network inspection of comedysportzphilly.com/calendar.

UPDATE clubs
SET scraping_url = 'https://plugin.vbotickets.com/Plugin/events?s=c75a73ef-782c-44de-a954-6777056f4b03'
WHERE name = 'CSz Philadelphia';
