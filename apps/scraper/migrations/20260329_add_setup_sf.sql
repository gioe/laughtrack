-- TASK-748: Add The Setup SF as a new venue
-- Website: https://setupcomedy.com
-- Show listing: https://setupcomedy.com/comedyshow-sanfrancisco
-- Speakeasy comedy producer running shows at The Palace Theater and The Lost Church in SF.
-- Show calendar is a published Google Sheets CSV (gid=495747966 = San Francisco sheet).
-- Ticket URLs link to Squarespace commerce product pages at setupcomedy.com/tickets-3/{slug}.
-- curl_cffi follows the Google Sheets 307 redirect to googleusercontent.com automatically.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Setup SF',
    '630 Broadway',
    'San Francisco',
    'CA',
    '94133',
    'America/Los_Angeles',
    'setup_sf',
    TRUE,
    'https://setupcomedy.com',
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku/pub?gid=495747966&single=true&output=csv'
);
