WITH shows_with_details as (
    SELECT
        s.id as id,
        s.popularity_score as popularity_score,
        s.date_time as date_time,
        s.ticket_link as ticket_link,
        club_id,
        cl.city as city,
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name,
                'popularity_score',
                c.popularity_score
            )
        ) as lineup_details
    FROM
        shows s
        INNER JOIN lineups l ON s.id = l.show_id
        INNER JOIN comedians c ON c.id = l.comedian_id
        INNER JOIN clubs cl on s.club_id = cl.id
    WHERE
    cl.city = ${location}
    AND s.date_time < ${end_date}
    AND s.date_time > ${start_date}
    GROUP BY
        cl.city,
        s.id
),
full_data as (
    SELECT
        cl.id as club_id,
        cl.name as club_name,
        l.id as show_id,
        lineup_details as lineup_details,
        date_time,
        ticket_link,
        sd.city,
        sd.popularity_score
    FROM
        shows_with_details sd
        INNER JOIN lineups l ON sd.id = l.show_id
        INNER JOIN comedians c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = sd.club_id
)
SELECT
    f.city,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'id',
            f.show_id,
            'city',
            f.city,
            'club_id',
            f.club_id,
            'popularity_score',
            f.popularity_score,
            'club_name',
            f.club_name,
            'lineup',
            f.lineup_details,
            'date_time',
            f.date_time,
            'ticket_link',
            f.ticket_link
        )
    ) as shows
from
    full_data f
GROUP BY
    f.city