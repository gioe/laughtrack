DELETE FROM tickets
WHERE id IN (
    SELECT t.id
    FROM tickets t
    JOIN shows s ON s.id = t.show_id
    JOIN clubs c ON c.id = s.club_id
    WHERE c.scraper = 'improv'
      AND (
          t.type LIKE 'http://schema.org/%'
          OR t.type LIKE 'https://schema.org/%'
      )
);
