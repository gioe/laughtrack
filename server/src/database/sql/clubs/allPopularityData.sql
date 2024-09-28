SELECT
    c.id,
    jsonb_agg(
        jsonb_build_object(
            'popularity_score',
            c.popularity_score
        )
    ) AS scores
from clubs c
inner join shows s on s.club_id = c.id
GROUP BY
    c.id