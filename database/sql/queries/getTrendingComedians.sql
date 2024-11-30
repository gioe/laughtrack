with comedian_dict as (
SELECT
	c.id,
	c.name, 
	jsonb_agg(jsonb_build_object('id', s.id, 'name', s.name, 'date', s.date)) as shows,
	count (distinct li.id) as show_count FROM
	comedians c
	JOIN lineup_items li ON li.comedian_id = c.uuid
	JOIN shows s ON li.show_id = s.id
	WHERE s.date > NOW()
	GROUP BY c.id
)

SELECT id, name, shows from comedian_dict where show_count > 3 ORDER BY
	random()
LIMIT 5
