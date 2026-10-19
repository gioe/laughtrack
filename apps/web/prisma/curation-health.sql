-- Post-activation reconciliation. Run with psql -v ON_ERROR_STOP=1 -f ...
BEGIN READ ONLY;
SELECT kind,identity_scope,disposition,count(*) FROM curation_entities GROUP BY 1,2,3 ORDER BY 1,2,3;
SELECT kind,disposition,count(*) FROM curation_relationships GROUP BY 1,2 ORDER BY 1,2;
SELECT status,count(*),min(created_at) oldest FROM curation_requests GROUP BY status;
SELECT count(*) AS pending_over_five_minutes FROM curation_requests WHERE status='pending' AND created_at<now()-interval '5 minutes';
SELECT status,count(*) FROM curation_requests WHERE created_at>=now()-interval '1 hour' GROUP BY status;
SELECT count(*) AS parent_projection_mismatches FROM comedians c WHERE c.parent_comedian_id IS DISTINCT FROM curation_confirmed_parent(c.id);
SELECT count(*) AS visible_denied_shows FROM shows s CROSS JOIN LATERAL curation_show_policy(to_jsonb(s)) p WHERE s.visible AND NOT p.allowed;
SELECT count(*) AS blocked_visible_clubs FROM clubs c JOIN curation_entities e ON e.club_id=c.id WHERE c.visible AND e.disposition='blocked';
-- Comedian visibility is a presentation flag, not identity approval. Report it
-- separately; public read predicates must still require approved curation.
SELECT count(*) AS visible_unapproved_comedians FROM comedians c CROSS JOIN LATERAL curation_comedian_policy(c.uuid,c.name,c.id) p WHERE c.visible AND p.disposition<>'approved';
SELECT count(*) AS negative_host_projection_mismatches FROM comedian_podcasts cp
JOIN curation_entities c ON c.comedian_id=cp.comedian_id
JOIN curation_entities p ON p.podcast_id=cp.podcast_id
JOIN curation_relationships r ON r.source_id=c.id AND r.target_id=p.id
WHERE cp.review_status='accepted' AND ((r.kind='host_of' AND cp.association_type='host') OR (r.kind='cohost_of' AND cp.association_type='cohost')) AND r.disposition IN ('rejected','severed');
SELECT count(*) AS unresolved_host_identity_holds FROM curation_host_reconciliations WHERE resolved_at IS NULL;
ROLLBACK;
