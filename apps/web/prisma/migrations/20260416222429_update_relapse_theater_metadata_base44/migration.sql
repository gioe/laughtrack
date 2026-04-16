-- Update The Relapse Theater (club 821) metadata — venue migrating off SeatEngine
-- to a new base44-powered site at https://relapsecomedy.com. The old domain
-- therelapsetheater.com is dead (ECONNREFUSED) and SeatEngine venue 254 returns
-- 0 events. The new site currently publishes 0 shows ("We're just getting
-- started!") via a base44 getPublicShows function. Clear stale seatengine_id,
-- point scraping_url/website at the new domain, update verified address/zip/
-- timezone from the venue's own SeatEngine header (380 14th St NW, Atlanta GA
-- 30318) and Yelp. Scraper set to NULL pending a base44 scraper (follow-up
-- task). Keep visible=false until shows are published.
UPDATE clubs
SET website        = 'https://relapsecomedy.com',
    scraping_url   = 'https://relapsecomedy.com',
    scraper        = NULL,
    seatengine_id  = NULL,
    address        = '380 14th Street NW',
    city           = 'Atlanta',
    state          = 'GA',
    zip_code       = '30318',
    timezone       = 'America/New_York',
    phone_number   = '404-791-8663'
WHERE id = 821;
