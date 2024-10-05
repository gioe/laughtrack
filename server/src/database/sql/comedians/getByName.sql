WITH future_shows_with_lineup_details as (
    SELECT
        s.id,
        s.popularity_score,
        s.date_time,
        s.ticket_link,
        club_id,
        array_agg(c.name) as lineup_names,
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
    WHERE s.date_time > NOW()
    GROUP BY
        s.id
),
full_data as (
    SELECT
    	c.id as comedian_id,
        c.name as comedian_name,
        fs.id as show_id,
        fs.popularity_score as popularity_score,
        lineup_names,
        lineup_details,
        date_time,
        ticket_link,
        city,
        cl.name as club_name,
        cl.id as club_id,
        jsonb_build_object(
            'instagram_account',
            c.instagram_account,
            'instagram_followers',
            c.instagram_followers,
            'tiktok_account',
            c.tiktok_account,
            'tiktok_followers',
            c.tiktok_followers,
            'website',
            c.website,
            'popularity_score',
            c.popularity_score
        ) AS social_data
    FROM
        future_shows_with_lineup_details fs
        INNER JOIN lineups l ON fs.id = l.show_id
        INNER JOIN comedians c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = fs.club_id
)
SELECT
f.comedian_id as id,
f.comedian_name as name,
f.social_data,
           jsonb_agg(
            DISTINCT jsonb_build_object(
                'id', f.show_id,
                'city',
                f.city,
                'club_id', f.club_id,
                'popularity_score', f.popularity_score,
                'club_name', f.club_name,
               	'lineup', f.lineup_details,
               	'date_time', f.date_time,
               	'ticket_link', f.ticket_link
            )
        ) as dates
from
    full_data f
where
    ${name} = ANY(lineup_names)
    AND comedian_name = ${name}
GROUP BY f.comedian_id, f.comedian_name, f.social_data