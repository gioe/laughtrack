SELECT
    s.id,
    jsonb_agg(
        jsonb_build_object(
            'popularity_score',
            c.popularity_score
        )
    ) AS scores
from shows s
inner join lineup_items l on s.id = l.show_id
inner join comedians c on c.id = l.comedian_id
GROUP BY
    s.id
