INSERT INTO comedians(name, uuid) 
VALUES(${name}, ${uuid})
ON CONFLICT DO NOTHING
RETURNING id;
