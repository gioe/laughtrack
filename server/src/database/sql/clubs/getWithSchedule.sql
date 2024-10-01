SELECT
    c.id,
    c.name,
    c.popularity_score,
    jsonb_agg(
        jsonb_build_object(
            'id',
            s.id,
            'date_time',
            s.date_time,
            'ticket_link',
            s.ticket_link,
            'popularity_score',
            s.popularity_score
        )
    ) AS shows
from
    clubs c
    join shows s on s.club_id = c.id
WHERE c.id = ${clubId} and s.date_time > NOW()
GROUP BY
    c.id,
    c.name
ORDER BY s.date_time ASC