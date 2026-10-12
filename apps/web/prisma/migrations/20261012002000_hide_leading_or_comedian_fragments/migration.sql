-- TASK-4168: description fragments are not comedian identities.
-- Preserve rows and relations; only touch the reviewed, still-active identities.
-- Their pre-cleanup visibility was true and all three block fields were NULL.
-- To reverse this cleanup, restore those four values only where block_added_by
-- is still TASK-4168 and both the ID and name still match the pairs below.
UPDATE comedians AS c
SET visible = false,
    block_reason = 'leading_or_fragment',
    block_added_by = 'TASK-4168',
    block_added_at = CURRENT_TIMESTAMP
FROM (VALUES
    (2381441, '/or queer performers'),
    (2241373, '/or trans')
) AS reviewed(id, name)
WHERE c.id = reviewed.id
  AND c.name = reviewed.name
  AND c.visible = true
  AND c.block_reason IS NULL
  AND c.block_added_by IS NULL
  AND c.block_added_at IS NULL;
