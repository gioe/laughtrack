INSERT INTO favorite_comedians(comedian_id, user_id) 
VALUES(${comedian_id}, ${user_id})
RETURNING 1;