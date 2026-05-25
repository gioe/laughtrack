CREATE UNIQUE INDEX comedian_podcasts_one_accepted_role_key
    ON comedian_podcasts(comedian_id, podcast_id, association_type)
    WHERE review_status = 'accepted';
