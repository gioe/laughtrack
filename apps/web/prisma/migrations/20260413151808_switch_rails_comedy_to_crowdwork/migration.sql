-- Switch Rails Comedy (club 506) from broken SeatEngine to Crowdwork scraper
-- SeatEngine venue 482 returns 404 (v1 and v2); subdomain redirects to seatengine.com
-- Website redirects railscomedy.com -> rails-comedy.com; venue is active in Washington DC
-- CrowdWork API (crowdwork.com/api/v2/railscomedy/shows) returns 3 upcoming shows
UPDATE "clubs"
SET
    scraper = 'rails_comedy',
    scraping_url = 'https://crowdwork.com/api/v2/railscomedy/shows',
    website = 'https://www.rails-comedy.com',
    address = '2438 18th St NW',
    city = 'Washington',
    state = 'DC',
    zip_code = '20009',
    timezone = 'America/New_York',
    seatengine_id = NULL
WHERE id = 506;
