/*
    Inserts a new City record.
*/
INSERT INTO cities(name)
VALUES($1)
RETURNING *