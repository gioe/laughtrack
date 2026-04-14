-- Rename The Comedy Scene (club 332) to Laugh Patriot Place
-- Venue rebranded; thecomedyscene.club 301-redirects to laughpatriotplace.com
-- Old SeatEngine venue 129 returns 404; tickets now sold via Etix (venue 32411)
UPDATE "clubs"
SET
    name = 'Laugh Patriot Place',
    website = 'https://laughpatriotplace.com',
    scraping_url = 'https://www.etix.com/ticket/v/32411/laugh-patriot-place',
    scraper = 'dr_grins',
    address = '23 Patriot Place',
    city = 'Foxborough',
    state = 'MA',
    zip_code = '02035',
    timezone = 'America/New_York',
    seatengine_id = NULL,
    country = 'US'
WHERE id = 332;
