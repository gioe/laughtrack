INSERT INTO favorite_comedians(comedian_id, user_id) 
VALUES(${comedianId}, ${userId})
RETURNING id;
