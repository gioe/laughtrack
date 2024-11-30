UPDATE comedians
SET instagram_account = ${instagram_account}, instagram_followers = ${instagram_followers},
tiktok_account = ${tiktok_account}, tiktok_followers = ${tiktok_followers}, 
youtube_account = ${youtube_account}, youtube_followers = ${youtube_followers},
website = ${website}
WHERE name = ${name};
