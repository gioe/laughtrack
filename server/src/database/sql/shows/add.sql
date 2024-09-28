/*
    Inserts a new User record.
*/
INSERT INTO shows(name)
VALUES($1)
RETURNING *