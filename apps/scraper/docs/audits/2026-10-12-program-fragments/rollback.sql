-- Manual rollback. Retain the migration ledger entry to prevent nightly reapplication.
-- Only reverse records still carrying this task's suppression marker.
UPDATE comedians c
SET visible=true, block_reason=NULL, block_added_by=NULL, block_added_at=NULL
FROM (VALUES
    (2451732, '27853bd97517814ee2faf1ca08b35646', 'Jimmy Kimmel Live'),
    (2666168, 'c57a278ad78e6ce807d36481c549d69f', 'Live from')
) reviewed(id, uuid, name)
WHERE c.id=reviewed.id AND c.uuid=reviewed.uuid AND c.name=reviewed.name
  AND c.parent_comedian_id IS NULL AND c.visible=false
  AND c.block_reason='non_performer_title' AND c.block_added_by='TASK-4172';
