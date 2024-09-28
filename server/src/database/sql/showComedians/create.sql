/*
 Creates table ShowComedians.
 */
CREATE TABLE IF NOT EXISTS show_comedians (
    id SERIAL,
    show_id INTEGER,
    comedian_id INTEGER,
    CONSTRAINT fk_shows FOREIGN KEY(show_id) REFERENCES shows(id),
    CONSTRAINT fk_comedians FOREIGN KEY(comedian_id) REFERENCES comedians(id),
    CONSTRAINT show_comedian_pkey PRIMARY KEY (show_id, comedian_id)
);