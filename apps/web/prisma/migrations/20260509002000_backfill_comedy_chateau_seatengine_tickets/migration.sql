-- Backfill three stale The Comedy Chateau SeatEngine rows that were scraped before
-- SeatEngine detail-ticket enrichment/fallbacks populated ticket rows.
--
-- Current upstream detail endpoints still return sold-out inventories for these
-- shows, but venue 432's list endpoint no longer includes the show IDs, so the
-- normal scraper run does not revisit them.
WITH backfill(show_id, purchase_url, price, sold_out, type) AS (
    VALUES
        (357077, 'https://comedychateau.seatengine.com/shows/338095', 35.00::numeric, TRUE, 'General Admission'),
        (357077, 'https://comedychateau.seatengine.com/shows/338095', 45.00::numeric, TRUE, 'VIP Seating'),
        (357078, 'https://comedychateau.seatengine.com/shows/338098', 35.00::numeric, TRUE, 'General Admission'),
        (357078, 'https://comedychateau.seatengine.com/shows/338098', 45.00::numeric, TRUE, 'VIP Seating'),
        (357106, 'https://comedychateau.seatengine.com/shows/354594', 25.00::numeric, TRUE, 'General Admission'),
        (357106, 'https://comedychateau.seatengine.com/shows/354594', 30.00::numeric, TRUE, 'Gold Circle')
)
INSERT INTO tickets (show_id, purchase_url, price, sold_out, type)
SELECT b.show_id, b.purchase_url, b.price, b.sold_out, b.type
FROM backfill b
JOIN shows s ON s.id = b.show_id
JOIN clubs c ON c.id = s.club_id
WHERE c.id = 68
  AND c.name = 'The Comedy Chateau'
ON CONFLICT (show_id, type) DO UPDATE SET
    purchase_url = EXCLUDED.purchase_url,
    price = EXCLUDED.price,
    sold_out = EXCLUDED.sold_out;
