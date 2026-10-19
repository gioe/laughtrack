-- Index each seed lookup independently instead of scanning every entity and its
-- keys for every row in a bulk enrichment update. Alias traversal is unchanged.
CREATE OR REPLACE FUNCTION curation_comedian_matches(input_uuid text, input_name text, input_id integer DEFAULT NULL, input_keys jsonb DEFAULT '[]')
RETURNS TABLE(id text) LANGUAGE sql STABLE AS $$
 WITH RECURSIVE seed(id) AS (
 SELECT e.id FROM curation_entities e WHERE e.kind='comedian' AND e.comedian_id=input_id
 UNION
 SELECT e.id FROM curation_entities e WHERE e.kind='comedian' AND curation_exact_name(e.label)=curation_exact_name(input_name)
 UNION
 SELECT e.id FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id
 WHERE e.kind='comedian' AND k.entity_kind='comedian' AND k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=input_uuid
 UNION
 SELECT e.id FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id
 WHERE e.kind='comedian' AND k.entity_kind='comedian' AND k.value=input_uuid
 AND (k.namespace LIKE 'legacy:%:comedian_uuid:v1' OR k.namespace LIKE 'legacy:%:comedian_identity_candidates:v1')
 UNION
 SELECT e.id FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id
 WHERE e.kind='comedian' AND k.entity_kind='comedian' AND k.namespace='exact-name:v1' AND k.scope='global' AND k.value=curation_exact_name(input_name)
 UNION
 SELECT e.id FROM jsonb_array_elements(input_keys) j JOIN curation_identity_keys k
 ON k.entity_kind='comedian' AND k.namespace=j->>'namespace' AND k.scope=j->>'scope' AND k.value=j->>'value'
 JOIN curation_entities e ON e.id=k.entity_id WHERE e.kind='comedian'
 ), matched(id) AS (
 SELECT id FROM seed
 UNION
 SELECT CASE WHEN r.source_id=m.id THEN r.target_id ELSE r.source_id END
 FROM matched m JOIN curation_relationships r ON (r.source_id=m.id OR r.target_id=m.id)
 WHERE r.kind='alias_of' AND r.disposition='confirmed'
 ) SELECT id FROM matched
$$;
CREATE INDEX IF NOT EXISTS curation_comedian_legacy_key_value
 ON curation_identity_keys(value) WHERE entity_kind='comedian'
 AND (namespace LIKE 'legacy:%:comedian_uuid:v1' OR namespace LIKE 'legacy:%:comedian_identity_candidates:v1');

-- Resolve matching names once; correlated OR subqueries otherwise prevent the
-- name indexes from bounding denial checks for every row in a bulk statement.
CREATE INDEX IF NOT EXISTS curation_rejected_candidate_name
 ON comedian_identity_candidates(curation_exact_name(name)) WHERE status='rejected';
CREATE OR REPLACE FUNCTION curation_comedian_policy(input_uuid text, input_name text, input_id integer DEFAULT NULL, input_keys jsonb DEFAULT '[]')
RETURNS TABLE(disposition text, entity_id text, comedian_id integer) LANGUAGE plpgsql STABLE AS $$
DECLARE ids text[]; roots text[]; selected_id text; names text[]; public_ids integer[];
BEGIN
 SELECT array_agg(m.id) INTO ids FROM curation_comedian_matches(input_uuid,input_name,input_id,input_keys) m;
 SELECT array_append(array_agg(curation_exact_name(e.label)),curation_exact_name(input_name)),array_agg(e.comedian_id)
 INTO names,public_ids FROM curation_entities e WHERE e.id=ANY(ids);
 IF EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked')
 OR EXISTS(SELECT 1 FROM comedian_deny_list d WHERE curation_exact_name(d.name)=ANY(names))
 OR EXISTS(SELECT 1 FROM comedians c WHERE NOT c.visible AND
   (c.id=input_id OR c.uuid=input_uuid OR curation_exact_name(c.name)=ANY(names) OR c.id=ANY(public_ids)))
 OR EXISTS(SELECT 1 FROM comedian_identity_candidates c WHERE c.status='rejected' AND
   (c.uuid=input_uuid OR curation_exact_name(c.name)=curation_exact_name(input_name))) THEN
   RETURN QUERY SELECT 'blocked'::text, (SELECT e.id FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked' ORDER BY e.id LIMIT 1), NULL::integer; RETURN;
 END IF;
 SELECT array_agg(e.id) INTO roots FROM curation_entities e WHERE e.id=ANY(ids) AND e.identity_scope='entity'
 AND NOT EXISTS(SELECT 1 FROM curation_relationships r WHERE r.source_id=e.id AND r.kind='alias_of' AND r.disposition='confirmed');
 IF cardinality(roots)=1 THEN selected_id:=roots[1]; END IF;
 RETURN QUERY SELECT CASE WHEN selected_id IS NOT NULL
   AND NOT EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.identity_scope='entity' AND e.disposition<>'approved')
   AND NOT EXISTS(SELECT 1 FROM comedians c WHERE (c.uuid=input_uuid OR c.id=input_id) AND c.parent_comedian_id IS NOT NULL
     AND NOT EXISTS(SELECT 1 FROM curation_entities e JOIN curation_relationships r ON r.source_id=e.id
       JOIN curation_entities p ON p.id=r.target_id WHERE e.comedian_id=c.id AND p.comedian_id=c.parent_comedian_id AND r.kind='alias_of' AND r.disposition='confirmed'))
 THEN 'approved' ELSE 'pending' END,
 selected_id, (SELECT e.comedian_id FROM curation_entities e WHERE e.id=selected_id);
END $$;

