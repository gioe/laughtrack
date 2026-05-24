-- Drop the legacy comedian_podcast_appearances table.
-- Replaced by the normalized podcast graph (podcasts, podcast_episodes,
-- episode_appearances, episode_appearance_reviews). All reads were migrated
-- to episode_appearances in prior changes; writers were already orphaned.

DROP TABLE IF EXISTS "comedian_podcast_appearances";
