CREATE TABLE IF NOT EXISTS comedian_group (
    id SERIAL,
    show_id integer REFERENCES shows(id)
);