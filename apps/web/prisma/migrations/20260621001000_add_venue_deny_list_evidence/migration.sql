-- Persist structured evidence for venue denials and discovery classification.
--
-- google_primary_type carries Google Places primaryType when known. evidence
-- stores machine-readable triage details so callers do not need to parse the
-- freeform reason text.

ALTER TABLE venue_deny_list
    ADD COLUMN IF NOT EXISTS google_primary_type TEXT;

ALTER TABLE venue_deny_list
    ADD COLUMN IF NOT EXISTS evidence JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE venue_deny_list
   SET google_primary_type = substring(reason from 'Google primary_type=([a-z0-9_]+)')
 WHERE google_primary_type IS NULL
   AND reason LIKE '%Google primary_type=%';

UPDATE venue_deny_list
   SET evidence = jsonb_strip_nulls(
        jsonb_build_object(
            'google_primary_type', google_primary_type,
            'legacy_reason', reason,
            'source', added_by
        )
    )
 WHERE evidence = '{}'::jsonb;

INSERT INTO venue_deny_list (
    google_place_id,
    name,
    reason,
    google_primary_type,
    evidence,
    added_by,
    denied_at
)
SELECT
    c.google_place_id,
    c.name,
    'Hidden active non-comedy club placeholder linked to venue taxonomy. TASK-3038.',
    NULL,
    jsonb_build_object(
        'club_id', c.id,
        'club_type', c.club_type,
        'visible', c.visible,
        'status', c.status,
        'source', 'hidden_active_non_comedy_backfill'
    ),
    'discovery_triage',
    now()
  FROM clubs c
 WHERE c.google_place_id IS NOT NULL
   AND c.visible = FALSE
   AND c.status = 'active'
   AND c.club_type = 'non_comedy'
   AND NOT EXISTS (
       SELECT 1
         FROM venue_deny_list v
        WHERE v.google_place_id = c.google_place_id
   );
