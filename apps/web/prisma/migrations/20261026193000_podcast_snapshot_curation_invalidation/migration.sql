-- Review decisions must invalidate the public snapshot just as legacy denials do.
CREATE FUNCTION invalidate_podcast_snapshot_curation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM curation_entities WHERE id = NEW.entity_id AND kind IN ('podcast', 'comedian'))
       OR EXISTS (SELECT 1 FROM curation_relationships WHERE id = NEW.relationship_id AND kind IN ('host_of', 'cohost_of', 'alias_of')) THEN
        UPDATE podcast_discovery_snapshots
        SET payload = NULL, generated_at = NULL, revision = revision + 1
        WHERE id = 1;
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER podcast_discovery_curation_decision
AFTER INSERT ON curation_decisions
FOR EACH ROW EXECUTE FUNCTION invalidate_podcast_snapshot_curation();
