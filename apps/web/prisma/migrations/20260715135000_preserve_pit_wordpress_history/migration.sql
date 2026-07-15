-- The WordPress feed exposes only ten parent events, so historical rows from
-- earlier feed windows cannot safely participate in stale reconciliation.
-- Restore their retired-key attribution unless a composite scrape refreshed
-- them after the adoption migration was applied.
WITH adoption AS (
    SELECT finished_at
    FROM _prisma_migrations
    WHERE migration_name = '20260715133000_adopt_pit_json_ld_scrapes'
      AND finished_at IS NOT NULL
)
UPDATE shows AS show
SET last_scraped_by = 'json_ld'
FROM clubs AS club, adoption
WHERE show.club_id = club.id
  AND show.last_scraped_by = 'the_pit'
  AND show.last_scraped_date < adoption.finished_at
  AND (
      club.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
      OR (club.name = 'The PIT' AND club.city = 'New York' AND club.state = 'NY')
  );

-- Remove only legacy online rows that can be proven to duplicate a current
-- composite row by their stable Salesforce performance instance URL. Leave
-- WordPress-only history intact because it may no longer be in the capped feed.
DELETE FROM shows AS legacy
USING clubs AS club, tickets AS legacy_ticket
WHERE legacy.club_id = club.id
  AND legacy_ticket.show_id = legacy.id
  AND legacy.last_scraped_by = 'json_ld'
  AND legacy_ticket.purchase_url LIKE '%/ticket/#/instances/%'
  AND (
      club.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
      OR (club.name = 'The PIT' AND club.city = 'New York' AND club.state = 'NY')
  )
  AND EXISTS (
      SELECT 1
      FROM shows AS current_show
      JOIN tickets AS current_ticket ON current_ticket.show_id = current_show.id
      WHERE current_show.club_id = legacy.club_id
        AND current_show.id <> legacy.id
        AND current_show.last_scraped_by = 'the_pit'
        AND current_ticket.purchase_url = legacy_ticket.purchase_url
  );
