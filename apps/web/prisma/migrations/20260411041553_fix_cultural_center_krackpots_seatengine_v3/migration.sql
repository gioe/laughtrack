-- Fix Cultural Center for the Arts with Krackpots Comedy Club (club 583)
-- Old SeatEngine v1 venue 563 is dead (HTTP 404, subdomain redirects to homepage).
-- Venue is now on SeatEngine v3 (UUID 58a56237-0902-40c0-8e4b-e592e782aec0).
-- Also fill in missing city/state/zip.

UPDATE "clubs"
SET scraper = 'seatengine_v3',
    seatengine_id = '58a56237-0902-40c0-8e4b-e592e782aec0',
    city = 'Canton',
    state = 'OH',
    zip_code = '44702',
    address = '1001 Market Ave N'
WHERE id = 583;
