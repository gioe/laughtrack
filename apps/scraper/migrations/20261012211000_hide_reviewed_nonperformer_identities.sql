-- TASK-4173: reviewed productions and biography fragments; preserve all relations.
UPDATE comedians c SET visible=false,block_reason='non_performer_identity',block_added_by='TASK-4173',block_added_at=now()
FROM (VALUES
 (2003397,'df4d05f04840ffe5506ac689f63c36d6','A Charlie Brown Christmas'),
 (2147696,'d2d7d2cbeb0dda3f73d3558931a6abbe','A Dreadful...'),
 (2225251,'bb69f0a8aa7875f19197677d3ccaa6cb','a first-generation Pakistani-Chilean'),
 (2404566,'b0f00a3cc550805c447e9f50c5259a85','A Magical Cirque Christmas (Touring)'),
 (2468634,'c64a6053fe56181f538d1084e67c93e9','A BOOMER CHRISTMAS CAROL')
) reviewed(id,uuid,name)
WHERE c.id=reviewed.id AND c.uuid=reviewed.uuid AND c.name=reviewed.name
 AND c.visible=true AND c.parent_comedian_id IS NULL
 AND c.block_reason IS NULL AND c.block_added_by IS NULL AND c.block_added_at IS NULL;
