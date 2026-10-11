-- Parameter 1: mapping-query-ids.json. Run in a READ ONLY REPEATABLE READ transaction.
SELECT wanted.show_id, s.id IS NOT NULL AS present_in_database,
 s.club_id, s.source_performance_id, s.show_page_url, s.last_scraped_by,
 s.scraped_by_organizer_id,
 COALESCE((SELECT jsonb_agg(jsonb_build_object(
   'candidate_id', c.id, 'source_id', c.source_id, 'event_key', c.event_key,
   'decision_id', p.decision_id, 'published_at', p.published_at)
   ORDER BY c.id, p.decision_id)
 FROM comedy_event_publications p
 JOIN comedy_event_candidates c ON c.id = p.candidate_id
 WHERE p.show_id = s.id), '[]'::jsonb) AS publication_candidates
FROM unnest(%s::integer[]) AS wanted(show_id)
LEFT JOIN shows s ON s.id = wanted.show_id
ORDER BY wanted.show_id;
