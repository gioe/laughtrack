/*
 Creates table comedian_tags.
 */
CREATE TABLE IF NOT EXISTS tagged_comedians (
    id SERIAL,
    comedian_id integer REFERENCES comedians(id),
    tag_id integer REFERENCES tags(id),
    CONSTRAINT comedian_tag_pkey PRIMARY KEY (comedian_id, tag_id)
);
