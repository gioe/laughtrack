-- Remove stale future rows from the previous Venetian Ticketmaster source after
-- the venue-owned scraper has been run for both active Venetian theatre clubs.
DELETE FROM shows
WHERE club_id IN (4826, 4870)
  AND last_scraped_by = 'ticketmaster_comedy'
  AND date >= NOW();
