SELECT id, name, image_name, base_url as url, popularity_score
FROM clubs 
ORDER BY popularity_score DESC LIMIT 5;