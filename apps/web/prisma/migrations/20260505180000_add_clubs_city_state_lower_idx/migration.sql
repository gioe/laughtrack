-- CreateIndex
-- Partial expression index matching the WHERE shape of GET_CLUBS_BY_LOCATION
-- (apps/scraper/sql/club_queries.py): LOWER(TRIM(city)) = ? AND LOWER(TRIM(state)) = ?
-- AND visible = TRUE AND status = 'active'. The expression list mirrors the query
-- exactly so the planner can use this index without falling back to a Seq Scan;
-- the partial predicate keeps the index small (only the active+visible subset
-- the fuzzy-match path ever queries). Used by ClubHandler.upsert_for_eventbrite_venue
-- on every distinct organizer-feed venue spelling per nightly run (TASK-1933).
CREATE INDEX "clubs_city_state_lower_idx"
    ON "clubs" (LOWER(TRIM(city)), LOWER(TRIM(state)))
    WHERE visible = TRUE AND status = 'active';
