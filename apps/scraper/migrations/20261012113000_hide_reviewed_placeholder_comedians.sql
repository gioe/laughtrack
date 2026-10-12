-- TASK-4171: whole-label guest/headliner placeholders, verified against show titles.
-- Preserve every row and relation. Before-image and rollback live under
-- docs/audits/2026-10-12-placeholder-names/.
UPDATE comedians c
SET visible=false, block_reason='placeholder_name', block_added_by='TASK-4171',
    block_added_at=CURRENT_TIMESTAMP
FROM (VALUES
    (767126, 'aae535f676afae53721bb708fe3c48bd', 'Secret Headliner'),
    (1649281, '56cfdc00a908b3e08dd30f7de843e385', 'Top Secret Headliner'),
    (1685152, '8b0e7325c2b7ac37211b0e775bfce2c8', 'Surprise Guest!'),
    (2304564, '8cb2259787bb2ff9ddd5fa42d0f3a3f9', 'Surprise Guests!'),
    (2430722, 'f9b1e6214047c390478dec6ad882b555', 'Surprise Headliner')
) reviewed(id, uuid, name)
WHERE c.id=reviewed.id AND c.uuid=reviewed.uuid AND c.name=reviewed.name
  AND c.parent_comedian_id IS NULL AND c.visible=true
  AND c.block_reason IS NULL AND c.block_added_by IS NULL AND c.block_added_at IS NULL;
