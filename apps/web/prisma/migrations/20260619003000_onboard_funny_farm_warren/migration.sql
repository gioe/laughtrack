-- TASK-2867: Onboard Funny Farm Comedy Club (Warren, OH) — identity only, NULL scraper.
--
-- Discovered via the discover-comedy-venues skill (objective #2, near ZIP 44622).
-- Funny Farm is a confirmed-active comedy club (37-yr venue, touring stand-up on
-- weekends; Yelp hours current as of May 2026), but it has NO scrapable online
-- calendar right now:
--   * its own Squarespace site is up, but the /tickets page (the only shows page,
--     linked from the nav + homepage CTA + third-party tour pages) returns a hard
--     404 — the page was removed/broken;
--   * its branded Freshtix org (321f5207-cacd-45bb-8b29-f3973aa2a368,
--     funnyfarmcomedyclub.freshtix.com) renders an EMPTY calendar (window.events
--     === {}, "no upcoming");
--   * its ShowSlinger listing (app.showslinger.com/e1/385) is login-walled and the
--     public combo_widget needs a secure_code that only lived in the now-404
--     /tickets embed (no Wayback snapshot to recover it).
--
-- So we insert the venue identity only and DELIBERATELY add NO scraping_sources
-- row. A club with no scraping_sources row is skipped by the scraper (0-show, no
-- errors). The club is inserted visible=FALSE so it does not surface an empty
-- club page; flip it to visible=TRUE once a working source is wired and shows land.
-- Revisit to wire a scraper (show_slinger, or a net-new freshtix scraper) once the
-- venue restores its /tickets embed. The insert is idempotent (guarded by NOT
-- EXISTS) so it is a no-op where the row already exists (prod) while reproducing
-- the state on a fresh database.

INSERT INTO clubs (
    name, address, website, city, state, zip_code, timezone, country,
    club_type, google_place_id, latitude, longitude, visible, status
)
SELECT
    'Funny Farm Comedy Club',
    '4422 Youngstown Rd SE, Warren, OH 44484, USA',
    'http://funnyfarmcomedyclub.com/',
    'Warren', 'OH', '44484', 'America/New_York', 'US',
    'club', 'ChIJg3aY1u3iM4gRD_hPjb8cUV4', 41.212481, -80.764926, FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs WHERE name = 'Funny Farm Comedy Club'
);
