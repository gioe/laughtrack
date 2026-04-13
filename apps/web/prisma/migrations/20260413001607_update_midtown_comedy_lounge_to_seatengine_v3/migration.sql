-- Update Midtown Comedy Lounge (club 589) from SeatEngine v1 to v3
-- Old seatengine_id 569 returns 404; venue migrated to v3 UUID.
-- Original website midtowncomedylounge.com is down (ECONNREFUSED).
-- SeatEngine v3 sites page is live; GraphQL API returns 0 events (genuinely empty).
-- Location: 301 S El Paso St, El Paso, TX 79901

UPDATE "clubs"
SET
    scraper = 'seatengine_v3',
    seatengine_id = '364f13ff-86b9-479f-9720-bd191e285ac3',
    website = 'https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine-sites.com/',
    scraping_url = 'https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine-sites.com/',
    address = '301 S El Paso St',
    city = 'El Paso',
    state = 'TX',
    zip_code = '79901',
    timezone = 'America/Denver'
WHERE id = 589;
