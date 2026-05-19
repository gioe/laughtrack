-- Disposition the five visible active clubs that had no enabled scraping source
-- after TASK-1950 disabled their stale SeatEngine rows.
--
-- Source verification on 2026-05-09:
--   * 82 Wicked Funny Comedy Club North Andover:
--       SeatEngine venue 487 returns 0 shows; public site says "Closed for
--       Renovations". Hide until a working source exists again.
--   * 521 The Royal Comedy Theatre:
--       SeatEngine venue 497 returns 0 shows; public site renders an empty
--       upcoming-shows widget. Hide until a working source exists.
--   * 568 The Brick Room:
--       SeatEngine v3 UUID c5595eca-1589-485a-9488-e01d4d455d76 and classic
--       venue 548 both return 0 shows; public site renders an empty
--       upcoming-shows widget. Hide until a working source exists.
--   * 589 Midtown Comedy Lounge:
--       SeatEngine v3 UUID 364f13ff-86b9-479f-9720-bd191e285ac3 and classic
--       venue 569 both return 0 shows; current SeatEngine-hosted shell has no
--       events. Hide until a working source exists.
--   * 1438 The Comedy Scene:
--       Stale duplicate of club 332. The canonical row was renamed to Laugh
--       Patriot Place in 20260414101706 after thecomedyscene.club redirected to
--       laughpatriotplace.com; club 332 has the active Etix source. Hide the
--       duplicate row.
--
-- After hiding these rows, delete their disabled scraping_sources. Audit history
-- belongs in migrations/tasks, not stale relationship rows.

UPDATE clubs
SET visible = false
WHERE id IN (82, 521, 568, 589, 1438)
  AND visible = true
  AND status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources ss
      WHERE ss.club_id = clubs.id
        AND ss.enabled = true
  );

DELETE FROM scraping_sources
WHERE club_id IN (82, 521, 568, 589, 1438)
  AND enabled = false;
