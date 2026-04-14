-- Consolidate duplicate club entries found during chain backfill analysis (TASK-1426)
-- Four duplicate pairs identified; for each pair we keep the canonical entry,
-- migrate any unique shows/tickets, and hide the duplicate.
--
-- FK cascades: tickets and tagged_shows both CASCADE on show deletion,
-- so deleting shows automatically removes their tickets and tag associations.

-- ============================================================================
-- 1. Comedy Zone Jacksonville: keep id=59, hide id=492
--    Club 59 has address + timezone but wrong website and typo in name.
--    Club 492 has 169 unique shows (no URL overlap) to migrate.
-- ============================================================================

-- Fix name typo and website on canonical entry
UPDATE clubs
SET name = 'Comedy Zone Jacksonville',
    website = 'https://www.comedyzone.com'
WHERE id = 59;

-- Migrate all shows from 492 → 59 (all 169 are unique — no URL overlap)
UPDATE shows
SET club_id = 59
WHERE club_id = 492;

-- Hide duplicate
UPDATE clubs
SET visible = false,
    status = 'closed'
WHERE id = 492;

-- ============================================================================
-- 2. Funny Bone Columbus: keep id=308, hide id=1037
--    Club 1037 has 0 shows, tour_dates scraper — pure duplicate stub.
-- ============================================================================

UPDATE clubs
SET visible = false,
    status = 'closed'
WHERE id = 1037;

-- ============================================================================
-- 3. Greenville Comedy Zone: keep id=73, hide id=488
--    Same SeatEngine ID (464). All 169 shows from 488 have matching URLs in 73.
--    Delete the duplicate shows (tickets + tagged_shows cascade).
-- ============================================================================

-- Delete duplicate shows (all 169 match shows in club 73 by URL)
DELETE FROM shows
WHERE club_id = 488;

-- Fix website to HTTPS on canonical entry
UPDATE clubs
SET website = 'https://greenvillecomedyzone.com'
WHERE id = 73;

-- Hide duplicate
UPDATE clubs
SET visible = false,
    status = 'closed'
WHERE id = 488;

-- ============================================================================
-- 4. Stress Factory - Valley Forge: keep id=130, hide id=623
--    27 shows overlap (same URL except http vs https), 21 unique in 623.
--    Delete overlapping shows, then migrate the 21 unique ones to 130.
-- ============================================================================

-- Delete overlapping shows from 623 (where normalized URL matches a show in 130)
DELETE FROM shows
WHERE id IN (
    SELECT s623.id FROM shows s623
    JOIN shows s130 ON REPLACE(s623.show_page_url, 'http://', 'https://') = s130.show_page_url
    WHERE s623.club_id = 623 AND s130.club_id = 130
);

-- Migrate remaining 21 unique shows from 623 → 130
UPDATE shows
SET club_id = 130
WHERE club_id = 623;

-- Fix website to HTTPS on canonical entry
UPDATE clubs
SET website = 'https://valleyforge.stressfactory.com'
WHERE id = 130;

-- Hide duplicate
UPDATE clubs
SET visible = false,
    status = 'closed'
WHERE id = 623;
