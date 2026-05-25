UPDATE podcast_candidate_reviews AS pcr
SET
    candidate_status = 'rejected',
    reviewed_at = COALESCE(cp.reviewed_at, pcr.reviewed_at),
    reviewed_by = COALESCE(cp.reviewed_by, pcr.reviewed_by)
FROM comedian_podcasts AS cp
WHERE cp.review_status = 'rejected'
    AND pcr.comedian_id = cp.comedian_id
    AND pcr.podcast_id = cp.podcast_id
    AND pcr.source = cp.source;

DELETE FROM comedian_podcasts
WHERE review_status = 'rejected';
