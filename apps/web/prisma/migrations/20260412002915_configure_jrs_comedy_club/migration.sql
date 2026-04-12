-- Configure J.R.'s Comedy Club (club 567)
-- Venue moved from Ventura to Simi Valley (inside The Junkyard Cafe)
-- Old SeatEngine venue ID 547 returns 404; new venue ID is 428
-- Website changed from venturalaughs.com to tocomedy.com
UPDATE "clubs"
SET
    seatengine_id = '428',
    website = 'https://www.tocomedy.com',
    scraping_url = 'https://www.tocomedy.com',
    address = '2585 Cochran St.',
    city = 'Simi Valley',
    state = 'CA',
    zip_code = '93065'
WHERE id = 567;
