ALTER TABLE shows
ADD COLUMN show_type TEXT;

CREATE INDEX shows_show_type_idx ON shows(show_type);
