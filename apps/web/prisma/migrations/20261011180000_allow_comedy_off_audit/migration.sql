BEGIN;
ALTER TABLE comedy_event_decisions DROP CONSTRAINT comedy_event_decisions_gate_mode_check;
ALTER TABLE comedy_event_decisions ADD CONSTRAINT comedy_event_decisions_gate_mode_check
  CHECK (gate_mode IN ('off', 'shadow', 'enforce'));
-- Audit observations are durable review evidence, never publication authority.
CREATE FUNCTION reject_comedy_off_audit_publication() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM comedy_event_decisions
             WHERE id=NEW.decision_id AND candidate_id=NEW.candidate_id AND gate_mode='off') THEN
    RAISE EXCEPTION 'Off-mode audit decisions cannot authorize publication';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER comedy_event_publications_reject_off_audit
  BEFORE INSERT OR UPDATE ON comedy_event_publications
  FOR EACH ROW EXECUTE FUNCTION reject_comedy_off_audit_publication();
COMMIT;
