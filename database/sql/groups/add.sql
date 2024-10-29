INSERT INTO comedian_group(parent_id, child_id) 
VALUES(${parent_id}, ${child_id})
ON CONFLICT (parent_id, child_id) DO NOTHING
RETURNING id;