-- Fix Portland Comedy Club (club 833) — stored seatengine_id=275 returns 0 shows.
-- Inspected live SeatEngine events page (https://theportlandcomedyclub-com.seatengine.com/events),
-- the logo path `/logos/260/` reveals the real venue_id, and
-- GET services.seatengine.com/api/v1/venues/260/shows returns 5 legitimate comedy
-- shows (Harland Williams, Dean DelRay). Update metadata (the venue is "formerly
-- Harvey's Comedy Club, under new management" at 436 NW 6th Ave, Portland OR 97209)
-- and flip visible=true.
UPDATE clubs
SET
    seatengine_id = '260',
    address = '436 NW 6th Avenue',
    city = 'Portland',
    state = 'OR',
    zip_code = '97209',
    country = 'US',
    timezone = 'America/Los_Angeles',
    phone_number = '(971) 270-0451',
    website = 'https://theportlandcomedyclub.com',
    scraping_url = 'https://theportlandcomedyclub-com.seatengine.com',
    visible = true
WHERE id = 833;
