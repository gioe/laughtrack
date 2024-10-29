/*
 Creates table show_tags.
 */
CREATE TABLE IF NOT EXISTS show_tags (
    id SERIAL,
    show_id integer REFERENCES shows(id),
    tag_id integer REFERENCES tags(id),
    CONSTRAINT show_tag_pkey PRIMARY KEY (show_id, tag_id)
);