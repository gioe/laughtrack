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
    ORDER BY s.date_time ASC
),
full_data as (
    SELECT
        l.comedian_id as comedian_id,
        cl.name as club_name,
        cl.id as club_id,
        cl.city as city,
        fs.id as show_id,
        fs.lineup_details,
        fs.popularity_score as popularity_score,
        fs.date_time,
        fs.ticket_link
    FROM
        future_shows_with_lineup_details fs
        INNER JOIN lineups l ON fs.id = l.show_id
        INNER JOIN clubs cl ON cl.id = fs.club_id
        WHERE ${name} = ANY(fs.lineup_names)
) 
SELECT 
c.id,
c.name, 
jsonb_build_object(
            'instagram_account',
            c.instagram_account,
            'instagram_followers',
            c.instagram_followers,
            'tiktok_account',
            c.tiktok_account,
            'tiktok_followers',
            c.tiktok_followers,
            'youtube_account',
            c.youtube_account,
            'youtube_followers',
            c.youtube_followers,
            'website',
            c.website
        ) AS social_data,
c.popularity_score,
COALESCE(jsonb_agg(
            DISTINCT jsonb_build_object(
                'id', fd.show_id,
                'city', fd.city,
                'club_id', fd.club_id,
                'popularity_score', fd.popularity_score,
                'club_name', fd.club_name,
               	'lineup', fd.lineup_details,
               	'date_time', fd.date_time,
               	'ticket_link', fd.ticket_link
            ) )FILTER (WHERE fd.show_id IS NOT NULL), '[]') as dates
FROM full_data fd RIGHT JOIN comedians c on c.id = fd.comedian_id where c.name = ${name} GROUP BY c.id, c.name