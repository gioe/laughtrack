WITH future_shows_with_lineup_details as (
    SELECT
        s.id,
        s.popularity_score,
        s.date_time,
        s.ticket_link,
        s.price,
        s.name,
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
        INNER JOIN lineup_items l ON s.id = l.show_id
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
        fs.date_time,
        fs.name,
        fs.price,
        fs.ticket_link,
        jsonb_agg(
        DISTINCT jsonb_build_object(
            'id', 
            fs.id,
            'popularity_score',
            fs.popularity_score
        )) as social_data
    FROM
        future_shows_with_lineup_details fs
        INNER JOIN lineup_items l ON fs.id = l.show_id
        INNER JOIN clubs cl ON cl.id = fs.club_id
        WHERE ${name} = ANY(fs.lineup_names)
        GROUP BY l.comedian_id, cl.name, cl.id, fs.id, fs.lineup_details, fs.date_time, fs.name, fs.price, fs.ticket_link
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
            c.website, 
            'popularity_score', c.popularity_score
        ) AS social_data,
COALESCE(jsonb_agg(
            DISTINCT jsonb_build_object(
                'id', fd.show_id,
                'city', fd.city,
                'club_id', fd.club_id,
                'club_name', fd.club_name,
               	'lineup', fd.lineup_details,
               	'date_time', fd.date_time,
                'ticket_link', fd.ticket_link,
               	'social_data', fd.social_data,
                'price', fd.price,
                'name', fd.name
            ) )FILTER (WHERE fd.show_id IS NOT NULL), '[]') as dates
FROM full_data fd RIGHT JOIN comedians c on c.id = fd.comedian_id where c.name = ${name} GROUP BY c.id, c.name
