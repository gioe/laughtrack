-- The global Discover date window cannot efficiently use the podcast-first index.
-- Keep this as one statement: CONCURRENTLY must run outside a transaction.
CREATE INDEX CONCURRENTLY "podcast_episodes_release_date_idx"
ON "podcast_episodes" ("release_date");
