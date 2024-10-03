/*
 Creates table Comedians.
 */
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL,
    comedian_id integer REFERENCES comedians(id),
    user_id integer REFERENCES users(id),
    CONSTRAINT user_comedian_pkey PRIMARY KEY (user_id, comedian_id)
);