/*
    Creates table Users.
*/
CREATE TABLE IF NOT EXISTS users 
(
id SERIAL PRIMARY KEY,
email TEXT NOT NULL UNIQUE,
password VARCHAR NOT NULL,
role TEXT NOT NULL DEFAULT 'user'
);