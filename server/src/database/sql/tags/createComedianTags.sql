CREATE TABLE IF NOT EXISTS comedian_tags (
    id SERIAL,
    comedian_id integer REFERENCES comedians(id),
    tag_id integer REFERENCES tags(id),
    CONSTRAINT comedian_tag_pkey PRIMARY KEY (comedian_id, tag_id)
);