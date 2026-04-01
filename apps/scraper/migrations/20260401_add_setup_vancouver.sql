-- TASK-865: Add The Setup Vancouver city location
-- Same Google Sheets CSV backend as The Setup SF (TASK-748).
-- Vancouver sheet tab gid sourced from the published spreadsheet pubhtml.
--   Vancouver: gid=1575830989
-- Venue: Little Mountain Gallery, 110 Water St, Vancouver BC (Gastown)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Setup Vancouver',
    '110 Water St',
    'Vancouver',
    'BC',
    'V6B 1A7',
    'America/Vancouver',
    'setup_sf',
    TRUE,
    'https://setupcomedy.com',
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku/pub?gid=1575830989&single=true&output=csv'
);
