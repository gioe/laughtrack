with parent_ids as ( 
SELECT c.id, cg.parent_id from comedians c Left JOIN comedian_group cg on c.id = cg.child_id WHERE c.id in ($1:csv)
)
SELECT
case when parent_id is null then id else parent_id end as id
FROM
  parent_ids