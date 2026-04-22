-- Remove historical cross-venue Improv rows traced to the 2026-03-23 scrape.
--
-- Investigation findings:
-- - Addison Improv (club 29) had shows saved under club_id=29 whose TicketWeb
--   URLs pointed at Houston / Arlington / LOL San Antonio.
-- - Brea Improv (club 30) had shows saved under club_id=30 whose TicketWeb
--   URLs pointed at Hollywood / Pittsburgh / Irvine / Denver / Milwaukee and
--   other non-Brea Improv venues.
-- - These rows were all written on 2026-03-23, before the later April rollout
--   that standardized more Improv venues onto the dedicated `improv` scraper.
--
-- Delete only rows from that historical scrape day where the TicketWeb `pl`
-- query param does not match the club the show is stored under.
--
-- `shows` cascades to tickets / lineup_items / tagged_shows / sent_notifications.

WITH contaminated_shows AS (
    SELECT DISTINCT s.id
    FROM shows s
    JOIN tickets t ON t.show_id = s.id
    WHERE s.club_id = 29
      AND s.last_scraped_date::date = DATE '2026-03-23'
      AND t.purchase_url ILIKE '%ticketweb.com%'
      AND lower(COALESCE(substring(t.purchase_url from '[?&]pl=([^&]+)'), '')) <> 'addisonimprov'

    UNION

    SELECT DISTINCT s.id
    FROM shows s
    JOIN tickets t ON t.show_id = s.id
    WHERE s.club_id = 30
      AND s.last_scraped_date::date = DATE '2026-03-23'
      AND t.purchase_url ILIKE '%ticketweb.com%'
      AND lower(COALESCE(substring(t.purchase_url from '[?&]pl=([^&]+)'), '')) <> 'breaimprov'
)
DELETE FROM shows
WHERE id IN (SELECT id FROM contaminated_shows);
