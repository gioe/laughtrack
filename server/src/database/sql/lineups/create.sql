/*
 Creates table Comedians.
 */
CREATE TABLE IF NOT EXISTS lineups (
    id SERIAL,
    show_id integer REFERENCES shows(id),
    comedian_id integer REFERENCES comedians(id),
    CONSTRAINT show_comedian_pkey PRIMARY KEY (show_id, comedian_id)
);