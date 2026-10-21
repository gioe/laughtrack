-- Billing credits are source-scoped labels, never canonical comedian identities.
ALTER TABLE comedian_identity_candidates DROP CONSTRAINT comedian_identity_candidates_status_check;
ALTER TABLE comedian_identity_candidates ADD CONSTRAINT comedian_identity_candidates_status_check
 CHECK(status IN ('pending','accepted','rejected','resolved'));
CREATE TABLE billing_credits (
 id text PRIMARY KEY,
 candidate_uuid text NOT NULL REFERENCES comedian_identity_candidates(uuid) ON DELETE RESTRICT,
 club_id integer NOT NULL REFERENCES clubs(id) ON DELETE RESTRICT,
 source_key text NOT NULL CHECK(btrim(source_key) NOT IN ('','unknown')),
 raw_name text NOT NULL CHECK(btrim(raw_name)<>''),
 active boolean NOT NULL DEFAULT true,
 reviewed_by text NOT NULL,
 reason text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX billing_credits_active_source_name ON billing_credits(source_key,club_id,raw_name) WHERE active;
CREATE INDEX billing_credits_source_name ON billing_credits(source_key,club_id,raw_name);
CREATE INDEX billing_credits_candidate ON billing_credits(candidate_uuid);
CREATE TABLE billing_credit_members (
 credit_id text NOT NULL REFERENCES billing_credits(id) ON DELETE RESTRICT,
 comedian_id integer NOT NULL REFERENCES comedians(id) ON DELETE RESTRICT,
 PRIMARY KEY(credit_id,comedian_id)
);
CREATE TABLE show_billing_credits (
 credit_id text NOT NULL REFERENCES billing_credits(id) ON DELETE RESTRICT,
 show_id integer NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
 PRIMARY KEY(credit_id,show_id)
);
-- Resolve the entire group or nothing. Later blocks, hiding, unvalidation and
-- alias changes must not leave a partially attributed joint credit.
CREATE FUNCTION resolve_billing_credit(input_source text,input_name text,input_club integer)
RETURNS TABLE(credit_id text,comedian_id integer) LANGUAGE sql STABLE AS $$
 SELECT b.id,m.comedian_id FROM billing_credits b
 JOIN billing_credit_members m ON m.credit_id=b.id
 WHERE b.active AND b.source_key=input_source AND b.raw_name=input_name AND b.club_id=input_club
 AND (SELECT count(*) FROM billing_credit_members WHERE credit_id=b.id)>=2
 AND NOT EXISTS(SELECT 1 FROM curation_comedian_policy(b.candidate_uuid,b.raw_name) p WHERE p.disposition='blocked')
 AND NOT EXISTS(
  SELECT 1 FROM billing_credit_members bm JOIN comedians c ON c.id=bm.comedian_id
  CROSS JOIN LATERAL curation_comedian_policy(c.uuid,c.name,c.id) p
  WHERE bm.credit_id=b.id AND (NOT c.visible OR c.parent_comedian_id IS NOT NULL OR c.identity_validated_at IS NULL
    OR p.disposition<>'approved' OR p.comedian_id IS DISTINCT FROM c.id)
 )
$$;
