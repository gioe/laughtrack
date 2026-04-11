-- Fix Delirious Comedy Club (club 407) — correct website typo, fill missing location,
-- clear dead SeatEngine config (venue 382 returns HTTP 404); venue moved to FriendlySky
-- ticketing at tickets.deliriouscomedyclub.com (new scraper needed — tracked separately)
UPDATE "clubs"
SET
    website = 'https://www.deliriouscomedyclub.com',
    scraping_url = 'https://tickets.deliriouscomedyclub.com/event?e=EKR',
    city = 'Las Vegas',
    state = 'NV',
    zip_code = '89169',
    timezone = 'America/Los_Angeles',
    address = '4100 Paradise Rd, Las Vegas, NV 89169',
    seatengine_id = NULL,
    scraper = 'disabled'
WHERE id = 407;
