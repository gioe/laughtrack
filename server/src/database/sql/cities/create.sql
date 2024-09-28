/*
    Creates table Cities.
*/

CREATE TABLE IF NOT EXISTS cities 
(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
)