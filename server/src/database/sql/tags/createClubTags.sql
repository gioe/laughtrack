CREATE TABLE IF NOT EXISTS club_tags (
    id SERIAL,
    club_id integer REFERENCES clubs(id),
    tag_id integer REFERENCES comedians(id),
    CONSTRAINT club_tag_jd PRIMARY KEY (club_id, tag_id)
);