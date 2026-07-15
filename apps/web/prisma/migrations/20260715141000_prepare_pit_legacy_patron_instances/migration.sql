-- Make a fresh, consecutive migration deploy deterministic. Legacy PIT
-- JSON-LD rows store the WordPress detail page as show_page_url even when
-- their ticket points at a stable PatronTicket instance. Promote that ticket
-- URL so ShowHandler's existing instance-id reconciliation moves the row to
-- PatronTicket's authoritative timestamp during the first composite scrape,
-- instead of inserting a timezone-shifted duplicate under a retired key.
UPDATE shows AS show
SET show_page_url = ticket.purchase_url
FROM clubs AS club, tickets AS ticket
WHERE show.club_id = club.id
  AND ticket.show_id = show.id
  AND show.last_scraped_by = 'json_ld'
  AND ticket.purchase_url LIKE '%/ticket/#/instances/%'
  AND (
      club.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
      OR (club.name = 'The PIT' AND club.city = 'New York' AND club.state = 'NY')
  );
