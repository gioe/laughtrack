-- TASK-749: Add Nashville Improv as a new venue
-- Website: https://www.nashvilleimprov.com
-- Located at 2007 Belmont Blvd, Nashville, TN 37203
-- Woman-owned improv comedy company performing at various Nashville venues.
-- Show listing powered by Squarespace events collection (collectionId: 69af0d8e38f8403f319d32d8).
-- Tickets sold via Squarespace Commerce (show page URL used as ticket fallback).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Nashville Improv',
    '2007 Belmont Blvd',
    'Nashville',
    'TN',
    '37203',
    'America/Chicago',
    'squarespace',
    TRUE,
    'https://www.nashvilleimprov.com',
    'https://www.nashvilleimprov.com/api/open/GetItemsByMonth?collectionId=69af0d8e38f8403f319d32d8'
);
