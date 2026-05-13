CREATE TABLE club_aliases (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    alias_name TEXT NOT NULL,
    normalized_alias_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    normalized_city TEXT NOT NULL,
    normalized_state TEXT NOT NULL,
    source TEXT,
    verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX club_aliases_normalized_location_key
    ON club_aliases (normalized_alias_name, normalized_city, normalized_state);

CREATE INDEX club_aliases_club_id_idx
    ON club_aliases (club_id);

INSERT INTO club_aliases (
    club_id,
    alias_name,
    normalized_alias_name,
    city,
    state,
    normalized_city,
    normalized_state,
    source
)
SELECT
    id,
    'Mesquite Street',
    'mesquite street',
    'Corpus Christi',
    'TX',
    'corpus christi',
    'tx',
    'TASK-2165'
FROM clubs
WHERE name = 'Mesquite St. Comedy Club'
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;
