with user_favorites as ( 
SELECT fc.id as favorite_id, fc.comedian_id from favorite_comedians fc
JOIN users u on fc.user_id = u.id where u.id = ${user_id}
)
SELECT favorite_id, c.id,
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
            'popularity_score',
            c.popularity_score
        ) AS social_data from user_favorites uf RIGHT JOIN comedians c on uf.comedian_id = c.id ORDER BY c.popularity_score DESC