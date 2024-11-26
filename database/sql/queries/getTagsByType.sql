WITH all_data AS (
	SELECT
		tc.id,
		tc.display_name,
		tc.value,
		tc.type,
		jsonb_agg(json_build_object('id', t.id, 'display_name', t.display_name, 'value', t.value)) AS options
	FROM
		tags t
		JOIN tag_category tc ON t.category = tc.id
	GROUP BY
		tc.id
)
SELECT
	*
FROM
	all_data
WHERE all_data.type = ${type}
GROUP BY
	all_data.display_name,
	all_data.id,
	all_data.options,
	all_data.type,
	all_data.value
