/*
 Creates table Shows.
 */
CREATE TABLE IF NOT EXISTS shows (
    id SERIAL PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,
    ticket_link TEXT NOT NULL,
    club_id INTEGER,
    score FLOAT,
    UNIQUE (club_id, date_time),
    CONSTRAINT fk_club FOREIGN KEY(club_id) REFERENCES clubs(id)
);