-- Rebrand Southcoast Comedy Series → Newport Comedy Series (Newport, RI)
-- Venue rebranded to "Joe Rocco's Newport Comedy Series" and moved from
-- SeatEngine to Punchup platform (newportcomedyseries.punchup.live).
-- Shows at Newport Elks Lodge #104, 141 Pelham Street, Newport, RI 02840.
UPDATE "clubs"
SET
    name = 'Newport Comedy Series',
    website = 'https://southcoastcomedy.com',
    scraping_url = 'https://newportcomedyseries.punchup.live/',
    scraper = 'newport_comedy_series',
    address = '141 Pelham Street',
    city = 'Newport',
    state = 'RI',
    zip_code = '02840',
    timezone = 'America/New_York',
    seatengine_id = NULL
WHERE id = 383;
