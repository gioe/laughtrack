SELECT
    s.id,
    s.date_time,
    s.ticket_link,
    cl.name as club_name,
    cl.base_url as club_url,
    s.popularity_score,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'id',
            c.id,
            'name',
            c.name,
            'popularity_score',
            c.popularity_score
        )
    ) AS lineup,
       jsonb_agg(
        DISTINCT jsonb_build_object(
            'longitude',
            cl.longitude,
            'latitude',
            cl.latitude
        )
    ) as coordinates
from shows s
inner join show_comedians sc on s.id = sc.show_id
inner join comedians c on c.id = sc.comedian_id
inner join clubs cl on cl.id = s.club_id
WHERE cl.city = ${location} AND s.date_time < ${endDate} AND s.date_time > ${startDate}
GROUP BY
    s.id,
    s.date_time, 
    cl.name,
    cl.base_url
ORDER BY s.popularity_score DESC, s.date_time ASC