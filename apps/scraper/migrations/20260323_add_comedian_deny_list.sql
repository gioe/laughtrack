-- TASK-641: Add comedian_deny_list table to prevent re-insertion of deleted false positives
-- Names deleted by audit_false_positive_comedians.py --delete --confirm are recorded here
-- so that lineup ingestion skips them on future scrapes.

CREATE TABLE IF NOT EXISTS comedian_deny_list (
    name       TEXT        NOT NULL,
    reason     TEXT        NOT NULL DEFAULT '',
    deleted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    added_by   TEXT        NOT NULL DEFAULT 'audit_script',
    CONSTRAINT comedian_deny_list_name_unique UNIQUE (name)
);
