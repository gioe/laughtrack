-- TASK-789: Update The Setup SF address to reflect multi-venue producer
-- The Setup SF is a roving comedy producer, not a fixed venue. It runs shows
-- at both The Palace Theater (630 Broadway) and The Lost Church (65 Capp St).
-- Per-event venue is stored correctly in the room field; the club address is
-- display metadata only. Clearing the venue-specific address avoids implying
-- the club is tied to a single location.

UPDATE clubs
SET address = 'Multiple SF venues'
WHERE name = 'The Setup SF';

-- Revert accidental over-update: LA, Seattle, and Chicago share scraper='setup_sf'
-- but have their own single-venue addresses. Restore their originals.
UPDATE clubs SET address = '4519 Santa Monica Blvd' WHERE name = 'The Setup LA';
UPDATE clubs SET address = '85 Pike St'             WHERE name = 'The Setup Seattle';
UPDATE clubs SET address = '948 W Fulton Market'    WHERE name = 'The Setup Chicago';
