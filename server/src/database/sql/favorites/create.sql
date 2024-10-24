/*
 Creates table favorite_comedians.
 */
CREATE TABLE IF NOT EXISTS favorite_comedians (
    id SERIAL,
    comedian_id integer REFERENCES comedians(id),
    user_id integer REFERENCES users(id),
    CONSTRAINT user_comedian_pkey PRIMARY KEY (user_id, comedian_id)
);