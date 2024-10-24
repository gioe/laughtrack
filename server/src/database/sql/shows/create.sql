/*
 Creates table shows.
 */
CREATE TABLE IF NOT EXISTS shows (
    id SERIAL PRIMARY KEY,
    name text,
    date_time timestamp without time zone NOT NULL,
    ticket_link text NOT NULL,
    club_id integer NOT NULL,
    FOREIGN KEY(club_id)
       REFERENCES clubs(id)
       ON DELETE CASCADE,
    price text,
    currency text DEFAULT 'USD'::text CHECK (currency = 'USD'::text),
    popularity_score double precision DEFAULT '0'::double precision,
    CONSTRAINT shows_club_id_date_time_key UNIQUE (club_id, date_time)
);