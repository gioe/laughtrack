-- TASK-790: Add The Setup other city locations (LA, Seattle, Chicago)
-- Same Google Sheets CSV backend as The Setup SF (TASK-748).
-- Each city has its own sheet tab with a distinct gid parameter.
-- gid values sourced from the published spreadsheet HTML (pubhtml):
--   Los Angeles: gid=783484107
--   Seattle:     gid=38419123
--   Chicago:     gid=0 (default/first sheet)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Setup LA',
    '4519 Santa Monica Blvd',
    'Los Angeles',
    'CA',
    '90029',
    'America/Los_Angeles',
    'setup_sf',
    TRUE,
    'https://setupcomedy.com',
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku/pub?gid=783484107&single=true&output=csv'
),
(
    'The Setup Seattle',
    '85 Pike St',
    'Seattle',
    'WA',
    '98101',
    'America/Los_Angeles',
    'setup_sf',
    TRUE,
    'https://setupcomedy.com',
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku/pub?gid=38419123&single=true&output=csv'
),
(
    'The Setup Chicago',
    '948 W Fulton Market',
    'Chicago',
    'IL',
    '60607',
    'America/Chicago',
    'setup_sf',
    TRUE,
    'https://setupcomedy.com',
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku/pub?gid=0&single=true&output=csv'
);
