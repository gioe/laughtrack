-- Drop the legacy comedian_podcast_identity_links table.
-- The source identity workflow has moved onto the normalized podcast graph
-- (Podcast, ComedianPodcast, PodcastCandidateReview). No writers remain; the
-- two scraper scripts that populated this table were deleted in the prior
-- ComedianPodcastAppearance cleanup.

DROP TABLE IF EXISTS "comedian_podcast_identity_links";
