-- TASK-1977: schema-level fail-fast guard against the priority-collision drift
-- recorded in apps/scraper/docs/audits/task-1967-duplicate-priorities.md. The
-- existing UNIQUE(club_id, platform, priority) lets two DIFFERENT platforms
-- co-exist enabled at the same priority for one club, so the scraper has no
-- deterministic primary/fallback ordering in that group. TASK-1979 dispositioned
-- the 21 (club_id, priority=0) duplicate groups documented in the audit, and
-- TASK-1968 made UPSERT_CLUB_BY_SEATENGINE(_V3)_VENUE preserve enabled when a
-- task_*_disposition metadata key is present, so the disable bits survive the
-- nightly seatengine_national sweep. Precondition reverified at the start of
-- this migration's task: check_duplicate_scraping_priorities.py exits 0 — zero
-- enabled (club_id, priority) duplicate groups remain.
--
-- The partial unique index converts the next attempted collision from silent
-- drift into a constraint violation that fails the scraper run loud and early,
-- so on-call sees it instead of the data layer absorbing it.
CREATE UNIQUE INDEX IF NOT EXISTS scraping_sources_club_priority_enabled_unique
    ON scraping_sources (club_id, priority)
    WHERE enabled = true;
