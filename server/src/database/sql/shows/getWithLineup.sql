SELECT
    s.id,
    s.date_time,
    s.ticket_link,
    cl.name,
    cl.base_url,
    s.popularity_score,
    jsonb_agg(
        jsonb_build_object(
            'id',
            c.id,
            'name',
            c.name,
            'popularity_score',
            c.popularity_score
        )
    ) AS lineup
from shows s
inner join show_comedians sc on s.id = sc.show_id
inner join comedians c on c.id = sc.comedian_id
inner join clubs cl on cl.id = s.club_id
WHERE s.id = ${showId} AND s.date_time > NOW()
GROUP BY
    s.id,
    s.date_time, 
    cl.name,
    cl.base_url
ORDER BY s.date_time ASC