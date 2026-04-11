-- Update Empire Comedy House: rebranded to Empire Comedy Club,
-- moved from SeatEngine to Tixologi/Punchup platform.
-- Old website (empirecomedyhouse.com) is dead; new site is empirecomedyme.com.
-- Location: 575 Congress St, 2nd Floor, Portland, ME 04101.
UPDATE "clubs"
SET
    name = 'Empire Comedy Club',
    website = 'https://www.empirecomedyme.com',
    scraping_url = 'https://www.empirecomedyme.com/shows/',
    scraper = 'pending',
    seatengine_id = NULL,
    address = '575 Congress St, 2nd Floor',
    city = 'Portland',
    state = 'ME',
    zip_code = '04101',
    timezone = 'America/New_York'
WHERE id = 819;
