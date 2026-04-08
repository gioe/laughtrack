-- Purge all shows for Gramercy Theatre (club_id=1042) (TASK-1083)
-- 51 of the 69 persisted shows are non-comedy events (concerts, metal, rap, etc.)
-- that were scraped before the Ticketmaster genre filter was added (TASK-1082).
-- Deleting all shows and re-scraping — the genre filter now ensures only comedy
-- events are persisted on subsequent scrapes.
-- Cascades to tickets, lineup_items, tagged_shows via ON DELETE CASCADE.

DELETE FROM shows
WHERE club_id = 1042;
