SELECT 	jsonb_build_object(
        'data', jsonb_build_object('name', c.name,
		'id', c.id,
        'social_data', jsonb_build_object(
                'instagram_account', instagram_account, 'instagram_followers', 
                instagram_followers, 'tiktok_account', tiktok_account, 
                'tiktok_followers', tiktok_followers, 'youtube_account', 
                youtube_account, 'youtube_followers', youtube_followers,
                'website', website, 'popularity', popularity), 
        'tags', array_agg(tc.id))) from comedians c JOIN tagged_comedians tc on c.id = tc.comedian_id where name = ${name} GROUP BY c.name, c.id
