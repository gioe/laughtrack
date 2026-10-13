-- Restore only untouched TASK-4173 suppressions; preserve later admin decisions.
UPDATE comedians c SET visible=true,block_reason=NULL,block_added_by=NULL,block_added_at=NULL
FROM (VALUES
 (2003397,'df4d05f04840ffe5506ac689f63c36d6','A Charlie Brown Christmas'),
 (2147696,'d2d7d2cbeb0dda3f73d3558931a6abbe','A Dreadful...'),
 (2225251,'bb69f0a8aa7875f19197677d3ccaa6cb','a first-generation Pakistani-Chilean'),
 (2404566,'b0f00a3cc550805c447e9f50c5259a85','A Magical Cirque Christmas (Touring)'),
 (2468634,'c64a6053fe56181f538d1084e67c93e9','A BOOMER CHRISTMAS CAROL')
) reviewed(id,uuid,name)
WHERE c.id=reviewed.id AND c.uuid=reviewed.uuid AND c.name=reviewed.name
 AND c.visible=false AND c.block_reason='non_performer_identity' AND c.block_added_by='TASK-4173';
