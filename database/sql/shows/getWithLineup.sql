SELECT
    s.id,
    s.date_time,
    jsonb_build_object(
        'id', s.id,
        'website',
        s.ticket_link
    ) as social_data,
    s.name as name,
    cl.name as club_name,
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
    ) AS lineup,
        COALESCE(jsonb_agg(
    json_build_object(
    'id', 
    st.tag_id
    )) FILTER (WHERE st.tag_id IS NOT NULL), '[]') as tags
from shows s
left join show_tags st on st.show_id = s.id
left join lineups l on s.id = l.show_id
left join comedians c on c.id = l.comedian_id
inner join clubs cl on cl.id = s.club_id
WHERE s.id = ${showId} AND s.date_time > NOW()
GROUP BY
    s.id,
    s.date_time, 
    cl.name,
    cl.base_url
ORDER BY s.date_time ASC