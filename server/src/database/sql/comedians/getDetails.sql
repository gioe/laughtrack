WITH lineups as (
    SELECT
        s.id,
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
        INNER JOIN show_comedians sc ON s.id = sc.show_id
        INNER JOIN comedians c ON c.id = sc.comedian_id
    GROUP BY
        s.id
),
full_data as (
    SELECT
    	c.id as comedian_id,
        c.name as comedian_name,
        l.id as show_id,
        l.lineup_names as lineup_names,
        lineup_details as lineup_details,
        date_time,
        ticket_link,
        city,
        cl.name as club_name,
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
        lineups l
        INNER JOIN show_comedians sc ON l.id = sc.show_id
        INNER JOIN comedians c ON c.id = sc.comedian_id
        INNER JOIN clubs cl ON cl.id = l.club_id
)
SELECT
f.comedian_id as id,
f.comedian_name as name,
f.social_data,
           jsonb_agg(
            DISTINCT jsonb_build_object(
                'show_id',
                f.show_id,
                'city',
                f.city,
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