CREATE TABLE podcast_discovery_snapshots (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ,
    payload JSONB
);
INSERT INTO podcast_discovery_snapshots (id) VALUES (1);

-- Invalidation lives beside the data, covering both admin and scraper writes.
-- Revision fencing also covers moderation racing with a background refresh.
CREATE FUNCTION invalidate_podcast_discovery_snapshot() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    -- Routine ingestion often writes unchanged review/identity fields. Do not
    -- evict a valid selection for those no-op updates.
    IF TG_OP = 'UPDATE' THEN
        IF TG_TABLE_NAME = 'comedians' THEN
            IF (OLD.visible, OLD.parent_comedian_id, OLD.name) IS NOT DISTINCT FROM
               (NEW.visible, NEW.parent_comedian_id, NEW.name) THEN RETURN NULL; END IF;
        ELSIF TG_TABLE_NAME = 'podcasts' THEN
            IF (OLD.source, OLD.source_podcast_id, OLD.feed_url) IS NOT DISTINCT FROM
               (NEW.source, NEW.source_podcast_id, NEW.feed_url) THEN RETURN NULL; END IF;
        ELSIF TG_TABLE_NAME = 'episode_appearances' THEN
            IF (OLD.review_status, OLD.comedian_id, OLD.episode_id) IS NOT DISTINCT FROM
               (NEW.review_status, NEW.comedian_id, NEW.episode_id) THEN RETURN NULL; END IF;
        END IF;
    END IF;
    UPDATE podcast_discovery_snapshots
    SET payload = NULL, generated_at = NULL, revision = revision + 1
    WHERE id = 1;
    RETURN NULL;
END;
$$;

CREATE TRIGGER podcast_discovery_comedian_visibility
AFTER UPDATE OF visible, parent_comedian_id, name OR DELETE ON comedians
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();

CREATE TRIGGER podcast_discovery_comedian_denial
AFTER INSERT OR UPDATE OR DELETE ON comedian_deny_list
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();

CREATE TRIGGER podcast_discovery_podcast_denial
AFTER INSERT OR UPDATE OR DELETE ON podcast_deny_list
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();

CREATE TRIGGER podcast_discovery_appearance_review
AFTER UPDATE OF review_status, comedian_id, episode_id OR DELETE ON episode_appearances
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();

CREATE TRIGGER podcast_discovery_podcast_identity
AFTER UPDATE OF source, source_podcast_id, feed_url OR DELETE ON podcasts
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();

CREATE TRIGGER podcast_discovery_episode_removal
AFTER DELETE ON podcast_episodes
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_discovery_snapshot();
