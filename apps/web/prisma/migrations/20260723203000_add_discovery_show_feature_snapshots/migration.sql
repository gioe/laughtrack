CREATE TABLE discovery_show_feature_snapshots (
    id BIGSERIAL PRIMARY KEY,
    show_id INTEGER NOT NULL,
    feature_version TEXT NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    prominence DOUBLE PRECISION NOT NULL,
    momentum DOUBLE PRECISION NOT NULL,
    growth DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    availability TEXT NOT NULL,
    evidence JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT discovery_show_feature_snapshots_show_id_fkey
        FOREIGN KEY (show_id) REFERENCES shows(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT discovery_show_feature_snapshot_identity_key
        UNIQUE (show_id, feature_version, as_of),
    CONSTRAINT discovery_show_feature_snapshots_feature_version_check
        CHECK (feature_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
    CONSTRAINT discovery_show_feature_snapshots_prominence_check
        CHECK (prominence BETWEEN 0 AND 1),
    CONSTRAINT discovery_show_feature_snapshots_momentum_check
        CHECK (momentum BETWEEN 0 AND 1),
    CONSTRAINT discovery_show_feature_snapshots_growth_check
        CHECK (growth BETWEEN 0 AND 1),
    CONSTRAINT discovery_show_feature_snapshots_confidence_check
        CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT discovery_show_feature_snapshots_availability_check
        CHECK (availability IN ('available', 'unknown', 'unavailable'))
);

CREATE INDEX discovery_show_feature_snapshots_version_as_of_idx
    ON discovery_show_feature_snapshots(feature_version, as_of);
