-- TASK-754: Add Villain Theater as a new venue
-- Website: https://www.villaintheater.com
-- Located at 5865 NE 2nd Avenue, Miami, FL 33137
-- Improv and stand-up comedy venue in Miami's Little Haiti neighborhood.
-- Show listing powered by Squarespace events collection (collectionId: 5b99c27d1ae6cfe40edce851).
-- Tickets sold via Eventbrite (embedded widget on show page; show page URL used as ticket fallback).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Villain Theater',
    '5865 NE 2nd Avenue',
    'Miami',
    'FL',
    '33137',
    'America/New_York',
    'squarespace',
    TRUE,
    'https://www.villaintheater.com',
    'https://www.villaintheater.com/api/open/GetItemsByMonth?collectionId=5b99c27d1ae6cfe40edce851'
);
