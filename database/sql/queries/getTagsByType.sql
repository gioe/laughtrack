with all_data as (
SELECT tc.id, tc.name, tc.type, tc.param_value, jsonb_agg(json_build_object('id', t.id, 'name', t.display_name)) as options FROm tags t JOIN tag_category tc ON t.category = tc.id GROUP BY tc.id
)
SELECT * from all_data where all_data.type = ${type} GROUP BY all_data.name, all_data.id, all_data.options, all_data.type, all_data.param_value
