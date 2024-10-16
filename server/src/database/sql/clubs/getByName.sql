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
        s.name,
        cl.name as club_name,
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
        LEFT JOIN lineups l ON s.id = l.show_id
        LEFT JOIN comedian_social_data c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = s.club_id
    WHERE s.date_time > NOW()
    GROUP BY
        s.id,
        cl.name
    ORDER BY
        s.date_time ASC
)
SELECT
    club_name,
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
            'name',
            full_lineup_data.name,
            'ticket_link',
            full_lineup_data.ticket_link,
            'popularity_score',
            full_lineup_data.popularity_score,
            'lineup',
            full_lineup_data.lineup
        )
    ) as dates
from
    full_lineup_data
WHERE
    club_name = ${name}
GROUP BY
    club_name