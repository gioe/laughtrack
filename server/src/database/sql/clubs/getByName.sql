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
        cl.base_url as club_website,
        cl.id as club_id,
        cl.name as club_name,
        s.date_time as date_time,
        jsonb_agg(
        DISTINCT jsonb_build_object(
            'id', 
            s.id,
            'ticket_link', 
            s.ticket_link,
            'popularity_score',
            s.popularity_score
        )) as social_data,
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
        LEFT JOIN lineups l ON s.id = l.show_id
        LEFT JOIN comedian_social_data c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = s.club_id
    WHERE s.date_time > NOW()
    GROUP BY
        s.id,
        cl.name,
        cl.base_url,
        cl.id
    ORDER BY
        s.date_time ASC
)
SELECT
    club_name,
        jsonb_build_object( 
                        'id',
            full_lineup_data.club_id,
            'website',
            full_lineup_data.club_website
        ) as social_data,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'id',
            full_lineup_data.id,
            'club_name',
            full_lineup_data.club_name,
            'date_time',
            full_lineup_data.date_time,
            'name',
            full_lineup_data.name,
            'social_data',
            full_lineup_data.social_data,
            'lineup',
            full_lineup_data.lineup
        )
    ) as dates
from
    full_lineup_data
WHERE
    club_name = ${name}
GROUP BY
    club_name,
    full_lineup_data.club_id,
    full_lineup_data.club_website