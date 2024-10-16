CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    tag_name text,
    type text,
    user_facing boolean DEFAULT false
);