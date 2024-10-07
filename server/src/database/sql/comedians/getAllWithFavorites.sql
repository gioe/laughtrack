with user_favorites as ( 
SELECT fc.id as favorite_id, fc.comedian_id from favorite_comedians fc
JOIN users u on fc.user_id = u.id where u.id = ${user_id}
)
SELECT favorite_id, c.* from user_favorites uf RIGHT JOIN comedians c on uf.comedian_id = c.id ORDER BY c.popularity_score DESC