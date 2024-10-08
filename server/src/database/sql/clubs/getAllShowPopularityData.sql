SELECT
    c.id,
    COALESCE(jsonb_agg(
        jsonb_build_object(
        	'id', s.id,
            'popularity_score',
            s.popularity_score
        )) FILTER (WHERE s.id IS NOT NULL), '[]') as scores
from clubs c
left join shows s on s.club_id = c.id
GROUP BY
    c.id