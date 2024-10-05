INSERT INTO comedians(name) 
VALUES(${name})
ON CONFLICT (name) DO UPDATE
SET name = EXCLUDED.name
RETURNING id;