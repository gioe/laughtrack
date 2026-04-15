-- Onboard Comedy Works South (Greenwood Village, CO)
-- Shares the comedyworks.com Rails platform with Comedy Works Downtown (club 1036)
INSERT INTO clubs (
    name, address, website, scraping_url, timezone, scraper, city, state,
    zip_code, phone_number, visible, popularity, total_shows, status,
    has_image, country
) VALUES (
    'Comedy Works South',
    '5345 Landmark Pl, Greenwood Village, CO 80111',
    'https://comedyworks.com',
    'https://comedyworks.com/events?south=1',
    'America/Denver',
    'comedy_works_south',
    'Greenwood Village',
    'CO',
    '80111',
    '',
    true,
    0,
    0,
    'active',
    false,
    'US'
);
