-- Switch Sunset Strip (club 571) from seatengine to squadup scraper
-- SeatEngine venue 551 returns 404; venue now uses SquadUP (user_id=9086799)
-- Also populate missing address, city, state, zip, and timezone fields

UPDATE "clubs"
SET
    scraper = 'squadup',
    squadup_user_id = '9086799',
    seatengine_id = NULL,
    scraping_url = 'https://www.sunsetstripatx.com/events',
    address = '214 E 6th St, Unit C',
    city = 'Austin',
    state = 'TX',
    zip_code = '78701',
    timezone = 'America/Chicago',
    visible = true
WHERE id = 571;
