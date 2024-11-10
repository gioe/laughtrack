with comedian_social_data as (
    SELECT
        id,
        name,
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'popularity_score',
                popularity_score
            )
        ) as social_data
    FROM
        comedians c
    GROUP BY
        id
),
full_lineup_data as (
    SELECT
        s.id as id,
        s.name,
        s.price,
        s.club_id,
        s.date_time as date_time,
        s.ticket_link as ticket_link,
        jsonb_agg(
        DISTINCT jsonb_build_object(
            'id', 
            s.id,
            'popularity_score',
            s.popularity_score
        )) as social_data,
        COALESCE(jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name,
                'social_data',
                c.social_data
            ))FILTER (WHERE c.id IS NOT NULL), '[]') as lineup
    FROM
        shows s
        LEFT JOIN lineup_items l ON s.id = l.show_id
        LEFT JOIN comedian_social_data c ON c.id = l.comedian_id
    WHERE s.date_time > NOW()
    GROUP BY
        s.id
    ORDER BY
        s.date_time ASC
)
SELECT
     c.id,
     c.name,
        jsonb_build_object( 
                        'id',
            c.id,
            'website',
            c.base_url
        ) as social_data,
            COALESCE(jsonb_agg(
                DISTINCT jsonb_build_object(
            'id',
            fld.id,
            'date_time',
            fld.date_time,
            'name',
            fld.name,
            'social_data',
            fld.social_data,
            'price',
            fld.price,
            'ticket_link', 
            fld.ticket_link,
            'lineup',
            fld.lineup
        )) FILTER (WHERE fld.id IS NOT NULL), '[]') as dates
from
    clubs c
LEFT JOIN full_lineup_data fld ON c.id = fld.club_id
WHERE
    c.id  = ${id}
GROUP BY
    c.id, c.name
