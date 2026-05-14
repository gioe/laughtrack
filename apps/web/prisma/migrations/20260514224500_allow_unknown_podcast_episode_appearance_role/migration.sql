ALTER TABLE episode_appearances
    DROP CONSTRAINT IF EXISTS episode_appearances_appearance_role_check;

ALTER TABLE episode_appearances
    ADD CONSTRAINT episode_appearances_appearance_role_check
        CHECK (appearance_role IN ('guest', 'host', 'mention', 'other', 'unknown'));

ALTER TABLE episode_appearance_reviews
    DROP CONSTRAINT IF EXISTS episode_appearance_reviews_appearance_role_check;

ALTER TABLE episode_appearance_reviews
    ADD CONSTRAINT episode_appearance_reviews_appearance_role_check
        CHECK (appearance_role IN ('guest', 'host', 'mention', 'other', 'unknown'));

ALTER TABLE episode_appearance_reviews
    DROP CONSTRAINT IF EXISTS episode_appearance_reviews_candidate_status_check;

ALTER TABLE episode_appearance_reviews
    ADD CONSTRAINT episode_appearance_reviews_candidate_status_check
        CHECK (candidate_status IN ('pending', 'accepted', 'rejected', 'ignored'));
