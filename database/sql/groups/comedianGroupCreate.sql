CREATE TABLE IF NOT EXISTS comedian_group (
    id SERIAL,
    parent_id integer REFERENCES comedians(id),
    child_id integer REFERENCES comedians(id),
    CONSTRAINT parent_child_pkey PRIMARY KEY (parent_id, child_id)
);