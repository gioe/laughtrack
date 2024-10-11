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
        s.club_id,
        cl.name as club_name,
        cl.city,
        s.popularity_score as popularity_score,
        s.date_time as date_time,
        s.ticket_link as ticket_link,
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
        INNER JOIN lineups l ON s.id = l.show_id
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
    city,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'id',
            full_lineup_data.id,
            'club_id',
            full_lineup_data.club_id,
            'club_name',
            full_lineup_data.club_name,
            'date_time',
            full_lineup_data.date_time,
            'ticket_link',
            full_lineup_data.ticket_link,
            'popularity_score',
            full_lineup_data.popularity_score,
            'lineup',
            full_lineup_data.lineup
        )
    ) as dates,
    COALESCE(jsonb_agg(distinct full_lineup_data.club_name)) as clubs
from
    full_lineup_data
WHERE
    city = ${location}
GROUP BY
    city