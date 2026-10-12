-- TASK-4172: program title and incomplete title fragment, verified against show titles.
-- Preserve every row and relation. Before-image and rollback live under
-- docs/audits/2026-10-12-program-fragments/.
UPDATE comedians c
SET visible=false, block_reason='non_performer_title', block_added_by='TASK-4172',
    block_added_at=CURRENT_TIMESTAMP
FROM (VALUES
    (2451732, '27853bd97517814ee2faf1ca08b35646', 'Jimmy Kimmel Live'),
    (2666168, 'c57a278ad78e6ce807d36481c549d69f', 'Live from')
) reviewed(id, uuid, name)
WHERE c.id=reviewed.id AND c.uuid=reviewed.uuid AND c.name=reviewed.name
  AND c.parent_comedian_id IS NULL AND c.visible=true
  AND c.block_reason IS NULL AND c.block_added_by IS NULL AND c.block_added_at IS NULL;
