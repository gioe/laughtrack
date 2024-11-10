/*
 Creates table lineup_items.
 */
CREATE TABLE IF NOT EXISTS lineup_items (
    id SERIAL,
    show_id integer NOT NULL,
    FOREIGN KEY(show_id) REFERENCES shows(id) ON DELETE CASCADE,
    comedian_id integer NOT NULL,
    FOREIGN KEY(comedian_id) REFERENCES comedians(id) ON DELETE CASCADE,
    CONSTRAINT show_comedian_pkey PRIMARY KEY (show_id, comedian_id)
);
