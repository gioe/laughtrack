-- Hide The Conway Muse (club 811) as non-comedy rebrand
-- The Conway Muse rebranded to Arcadian Public House (conwaymuse.com now 301-redirects to arcadianpublichouse.com).
-- Arcadian Public House is a 21+ live music venue at 18444 Spruce St, Conway, WA 98238 — not a comedy venue.
-- Clear stale seatengine_id (240, 0 shows), null out the scraper, and keep visible=false.
-- Update metadata (address, city, state, zip, timezone, website) to reflect the current venue.
UPDATE clubs
SET website = 'https://arcadianpublichouse.com',
    scraping_url = 'https://arcadianpublichouse.com',
    address = '18444 Spruce St',
    city = 'Conway',
    state = 'WA',
    zip_code = '98238',
    timezone = 'America/Los_Angeles',
    seatengine_id = NULL,
    scraper = NULL,
    visible = false
WHERE id = 811;
