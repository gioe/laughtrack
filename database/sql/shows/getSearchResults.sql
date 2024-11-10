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
        s.price,
        s.name,
        cl.city,
        cl.name as club_name,
        s.ticket_link as ticket_link,
        s.date_time as date_time,
                jsonb_build_object(
                'popularity_score',
                s.popularity_score
            ) as social_data,
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name,
                'social_data',
                c.social_data
            )
        ) as lineup
    FROM
        shows s
        INNER JOIN lineup_items l ON s.id = l.show_id
        INNER JOIN comedian_social_data c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = s.club_id
    WHERE
        s.date_time < ${end_date}
        AND s.date_time > ${start_date}
    GROUP BY
        s.id,
        cl.name,
        cl.city
    ORDER BY
        s.date_time ASC
)
SELECT
*
from
    full_lineup_data
WHERE
    city = ${location}
