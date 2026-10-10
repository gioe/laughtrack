BEGIN;
-- All existing and new sources start without reviewed trust or filtering.
CREATE TYPE "ComedyIngestionPolicy" AS ENUM ('unreviewed', 'comedy_only', 'mixed');
CREATE TYPE "ComedyGateMode" AS ENUM ('off', 'shadow', 'enforce');
ALTER TABLE scraping_sources
  ADD COLUMN comedy_policy "ComedyIngestionPolicy" NOT NULL DEFAULT 'unreviewed',
  ADD COLUMN comedy_gate_mode "ComedyGateMode" NOT NULL DEFAULT 'off',
  ADD COLUMN comedy_policy_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN comedy_reviewed_by TEXT,
  ADD COLUMN comedy_reviewed_at TIMESTAMPTZ,
  ADD COLUMN comedy_review_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD CONSTRAINT scraping_sources_comedy_version_positive CHECK (comedy_policy_version > 0),
  ADD CONSTRAINT scraping_sources_comedy_evidence_object CHECK (jsonb_typeof(comedy_review_evidence) = 'object');

CREATE FUNCTION maintain_source_comedy_policy() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE changed BOOLEAN;
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.comedy_policy_version := 1;
    changed := NEW.comedy_policy <> 'unreviewed' OR NEW.comedy_gate_mode <> 'off'
      OR NEW.comedy_reviewed_by IS NOT NULL OR NEW.comedy_review_evidence <> '{}'::jsonb;
    NEW.comedy_reviewed_at := NULL;
  ELSE
    changed := (NEW.comedy_policy, NEW.comedy_gate_mode, NEW.comedy_reviewed_by, NEW.comedy_review_evidence)
      IS DISTINCT FROM
      (OLD.comedy_policy, OLD.comedy_gate_mode, OLD.comedy_reviewed_by, OLD.comedy_review_evidence);
    NEW.comedy_policy_version := OLD.comedy_policy_version;
    NEW.comedy_reviewed_at := OLD.comedy_reviewed_at;
    IF changed THEN
      NEW.comedy_policy_version := OLD.comedy_policy_version + 1;
    END IF;
  END IF;
  IF changed THEN
    IF NULLIF(btrim(NEW.comedy_reviewed_by), '') IS NULL OR NEW.comedy_review_evidence = '{}'::jsonb THEN
      RAISE EXCEPTION 'Comedy policy changes require reviewer and evidence';
    END IF;
    NEW.comedy_reviewed_at := clock_timestamp();
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER scraping_sources_comedy_policy_revision
  BEFORE INSERT OR UPDATE ON scraping_sources
  FOR EACH ROW EXECUTE FUNCTION maintain_source_comedy_policy();
COMMIT;
