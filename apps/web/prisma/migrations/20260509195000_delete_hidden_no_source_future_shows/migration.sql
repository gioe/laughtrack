-- TASK-2095: remove future inventory from hidden clubs that have no enabled
-- scraping_sources row. Big Couch was the triggering case: hidden club 2287
-- had 81 future Eventbrite shows while the canonical visible "Big Couch New
-- Orleans" row had the enabled Eventbrite source and matching future URLs.
--
-- The same invariant surfaced five other hidden legacy/duplicate rows. Hidden
-- no-source clubs are not a valid durable home for future listings; after this
-- cleanup, any club with future shows and no enabled scraping_sources row is
-- actionable drift rather than expected legacy inventory.

DELETE FROM shows AS orphan
USING clubs AS hidden_club
WHERE hidden_club.id = orphan.club_id
  AND hidden_club.visible = FALSE
  AND orphan.date > NOW()
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources AS hidden_source
      WHERE hidden_source.club_id = hidden_club.id
        AND hidden_source.enabled = TRUE
  );
