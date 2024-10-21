CREATE TABLE IF NOT EXISTS comedian_group (
    id SERIAL,
    comedian_id integer REFERENCES shows(id)
);