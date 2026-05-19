ALTER TABLE podcast_candidate_reviews
    DROP CONSTRAINT podcast_candidate_reviews_candidate_status_check,
    ADD CONSTRAINT podcast_candidate_reviews_candidate_status_check
        CHECK (candidate_status IN ('pending', 'accepted', 'rejected', 'ignored'));

ALTER TABLE episode_appearance_reviews
    DROP CONSTRAINT episode_appearance_reviews_candidate_status_check,
    ADD CONSTRAINT episode_appearance_reviews_candidate_status_check
        CHECK (candidate_status IN ('pending', 'accepted', 'rejected', 'ignored'));
