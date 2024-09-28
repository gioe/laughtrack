SELECT
    s.id,
    jsonb_agg(
        jsonb_build_object(
            'popularity_score',
            c.popularity_score
        )
    ) AS scores
from shows s
inner join show_comedians sc on s.id = sc.show_id
inner join comedians c on c.id = sc.comedian_id
GROUP BY
    s.id